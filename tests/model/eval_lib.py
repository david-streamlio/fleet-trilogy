"""Shared harness for Tier 3 model evals — real llama.cpp-family runtime, real GGUF model.

These are behavioral evals, not equality tests: a small quantized model is stochastic,
so every function here measures a rate/distribution and returns it for the caller to
assert against a configurable floor. Reuses llm_inference.structured's prompt
rendering and JSON extraction directly — no inference/parsing logic is duplicated here.
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass, field

from fleet_telemetry_model import EnrichmentCard, TelemetryEvent
from fleet_telemetry_model.detection import evaluate_signals, is_probable_slowdown
from llm_inference import LlmBackend
from llm_inference.structured import extract_json_object, render_enrichment_prompt

ETA_IMPACT_ABSOLUTE_TOLERANCE_MIN = 2.0
ETA_IMPACT_RELATIVE_TOLERANCE = 0.5


@dataclass
class Trial:
    raw_output: str
    latency_seconds: float
    parsed: dict | None
    error: str | None = None


def run_enrichment_trials(backend: LlmBackend, event: TelemetryEvent, n: int) -> list[Trial]:
    """Call the real Tier 1 enrichment prompt against `event` n times. Never raises —
    a failing call (timeout, bad exit, unparseable output) is recorded as a Trial, not
    an exception, so one flaky run doesn't abort the whole eval."""
    triggered_signals = evaluate_signals(event)
    prompt = render_enrichment_prompt(event, triggered_signals)
    trials: list[Trial] = []
    for _ in range(n):
        start = time.monotonic()
        try:
            # Deliberately blind: a real LLM subprocess call can fail in ways
            # beyond LlmInferenceError (timeouts, bad exits), and a failure here is a
            # measurement (a format-reliability miss), not a bug to propagate.
            raw = backend.generate(prompt)
        except Exception as exc:  # noqa: BLE001
            trials.append(
                Trial(raw_output="", latency_seconds=time.monotonic() - start, parsed=None, error=str(exc))
            )
            continue
        latency = time.monotonic() - start
        try:
            parsed = extract_json_object(raw)
            EnrichmentCard(**parsed)
        except Exception as exc:  # noqa: BLE001 - unparseable/invalid output is a measurement, not a bug
            trials.append(Trial(raw_output=raw, latency_seconds=latency, parsed=None, error=str(exc)))
            continue
        trials.append(Trial(raw_output=raw, latency_seconds=latency, parsed=parsed, error=None))
    return trials


def format_reliability(trials: list[Trial]) -> dict:
    """(a) FORMAT RELIABILITY: fraction of trials that returned a parseable EnrichmentCard."""
    parsed = sum(1 for t in trials if t.parsed is not None)
    sample_failures = [{"raw_output": t.raw_output, "error": t.error} for t in trials if t.parsed is None][:5]
    return {
        "total": len(trials),
        "parsed": parsed,
        "rate": (parsed / len(trials)) if trials else 0.0,
        "sample_failures": sample_failures,
    }


def check_grounding(event: TelemetryEvent, trials: list[Trial]) -> dict:
    """(b) GROUNDING: a card is grounded if truck_id/corridor are copied verbatim from the
    input and eta_impact is traceable to the input's eta_slip_min (within a tolerance),
    rather than an invented number. Only checks parsed trials — format_reliability already
    covers unparseable output."""
    violations = []
    checked = 0
    for trial in trials:
        if trial.parsed is None:
            continue
        checked += 1
        card = trial.parsed
        problems = []
        if card.get("truck_id") != event.truck_id:
            problems.append(f"truck_id {card.get('truck_id')!r} != input {event.truck_id!r}")
        if card.get("corridor") != event.corridor:
            problems.append(f"corridor {card.get('corridor')!r} != input {event.corridor!r}")
        eta_impact = card.get("eta_impact")
        tolerance = max(
            ETA_IMPACT_ABSOLUTE_TOLERANCE_MIN, ETA_IMPACT_RELATIVE_TOLERANCE * event.signals.eta_slip_min
        )
        if not isinstance(eta_impact, (int, float)) or abs(eta_impact - event.signals.eta_slip_min) > tolerance:
            problems.append(
                f"eta_impact {eta_impact!r} not within {tolerance:.1f}min of input "
                f"eta_slip_min {event.signals.eta_slip_min}"
            )
        if problems:
            violations.append(
                {"input_eta_slip_min": event.signals.eta_slip_min, "output": card, "problems": problems}
            )
    return {
        "total": checked,
        "violations": len(violations),
        "violation_rate": (len(violations) / checked) if checked else 0.0,
        "sample_violations": violations[:5],
    }


@dataclass
class LabeledEvent:
    event: TelemetryEvent
    ground_truth_is_slowdown: bool


def run_directional_accuracy(
    backend: LlmBackend, labeled_events: list[LabeledEvent]
) -> tuple[dict, list[float]]:
    """(c) DIRECTIONAL ACCURACY: detection is cheap math, not the LLM (per docs/CANON.md), so
    this measures whether that math's flag/no-flag decision matches _ground_truth in the real
    world — while exercising a real LLM call for every event math actually flags, the
    same as the Tier 1 pipeline does live."""
    tp = fp = fn = tn = 0
    latencies: list[float] = []
    for labeled in labeled_events:
        predicted_slowdown = is_probable_slowdown(labeled.event)
        if predicted_slowdown:
            triggered = evaluate_signals(labeled.event)
            prompt = render_enrichment_prompt(labeled.event, triggered)
            start = time.monotonic()
            try:
                # This eval only scores the flag/no-flag decision, not card content, so a
                # failed call is still a real latency sample and doesn't invalidate the row.
                backend.generate(prompt)
            except Exception:  # noqa: BLE001, S110
                pass
            latencies.append(time.monotonic() - start)

        if predicted_slowdown and labeled.ground_truth_is_slowdown:
            tp += 1
        elif predicted_slowdown and not labeled.ground_truth_is_slowdown:
            fp += 1
        elif not predicted_slowdown and labeled.ground_truth_is_slowdown:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    result = {
        "total": len(labeled_events),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
    return result, latencies


def peak_child_rss_mb() -> float | None:
    """(d) best-effort resident RAM of LLM subprocess children, cumulative peak
    across the whole test session. POSIX only; returns None if unavailable (e.g. Windows)."""
    try:
        import resource

        usage_kb_or_bytes = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    except (ImportError, AttributeError):
        return None
    # Linux reports ru_maxrss in KB; macOS reports it in bytes.
    return usage_kb_or_bytes / 1024 if platform.system() == "Linux" else usage_kb_or_bytes / (1024 * 1024)


def _percentile(ordered: list[float], fraction: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


@dataclass
class Tier3Report:
    """Accumulates results across all Tier 3 eval tests in one session, so a single JSON
    artifact + printed summary covers the whole run (format reliability, grounding,
    directional accuracy, latency, RAM) instead of one artifact per test file."""

    config: dict
    format_reliability: dict = field(default_factory=dict)
    grounding: dict = field(default_factory=dict)
    directional_accuracy: dict = field(default_factory=dict)
    latency_samples_seconds: list[float] = field(default_factory=list)
    resident_ram_mb: float | None = None

    def add_latencies(self, samples: list[float]) -> None:
        self.latency_samples_seconds.extend(samples)

    def latency_percentiles(self) -> dict:
        if not self.latency_samples_seconds:
            return {"p50_seconds": None, "p95_seconds": None, "n": 0}
        ordered = sorted(self.latency_samples_seconds)
        return {
            "p50_seconds": _percentile(ordered, 0.50),
            "p95_seconds": _percentile(ordered, 0.95),
            "n": len(ordered),
        }

    def to_dict(self) -> dict:
        return {
            "config": self.config,
            "format_reliability": self.format_reliability,
            "grounding": self.grounding,
            "directional_accuracy": self.directional_accuracy,
            "latency": self.latency_percentiles(),
            "resident_ram_mb": self.resident_ram_mb,
        }

    def render_summary(self, artifact_path) -> str:
        lat = self.latency_percentiles()
        lines = [
            "",
            "=== Tier 3 model eval summary ===",
            f"artifact: {artifact_path}",
            f"host: {self.config.get('host')} ({self.config.get('platform')})",
            f"model: {self.config.get('model_path')} via {self.config.get('binary_path')}",
        ]
        if self.format_reliability:
            fr = self.format_reliability
            lines.append(f"format reliability: {fr['rate']:.1%} ({fr['parsed']}/{fr['total']} parsed)")
        if self.grounding:
            gr = self.grounding
            lines.append(
                f"grounding violations: {gr['violation_rate']:.1%} ({gr['violations']}/{gr['total']})"
            )
        if self.directional_accuracy:
            da = self.directional_accuracy
            lines.append(
                f"directional accuracy: precision={da['precision']:.2f} recall={da['recall']:.2f} "
                f"f1={da['f1']:.2f} confusion={da['confusion_matrix']}"
            )
        if lat["n"]:
            lines.append(f"latency: p50={lat['p50_seconds']:.2f}s p95={lat['p95_seconds']:.2f}s (n={lat['n']})")
        if self.resident_ram_mb is not None:
            lines.append(f"peak child RSS: {self.resident_ram_mb:.1f} MB")
        return "\n".join(lines)
