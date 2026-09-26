"""Shared harness for Tier 3 model evals — real llama.cpp-family runtime, real GGUF model.

These are behavioral evals, not equality tests: a small quantized model is stochastic,
so every function here measures a rate/distribution and returns it for the caller to
assert against a configurable floor. Reuses llm_inference.structured's prompt
rendering and JSON extraction directly — no inference/parsing logic is duplicated here.
"""

from __future__ import annotations

import json
import platform
import time
from dataclasses import dataclass, field

from fleet_telemetry_model import EnrichmentCard, TelemetryEvent, to_json
from fleet_telemetry_model.detection import evaluate_signals, is_probable_slowdown
from llm_inference import LlmBackend, LlmGenerationConfig
from llm_inference.structured import extract_json_object, render_enrichment_prompt

ETA_IMPACT_ABSOLUTE_TOLERANCE_MIN = 2.0
ETA_IMPACT_RELATIVE_TOLERANCE = 0.5

# (e) SEVERITY CALIBRATION thresholds, tied to the fleet simulator's own incident
# ramp rate (shared/fleet-simulator/src/fleet_simulator/scenario.py):
# SLOWDOWN_ETA_SLIP_PER_TICK_MINUTES=0.6, MIN_INCIDENT_TICKS=24/MAX_INCIDENT_TICKS=48
# — a fully-played-out incident accumulates 14.4-28.8min of slip. Detection itself
# fires as early as eta_slip_min=2.0 (detection.ETA_SLIP_THRESHOLD_MINUTES). So:
#   low:    [2, 5)   just crossed the detection floor, early in an incident
#   medium: [5, 15)  spans the width where most incidents cross (min length alone is 14.4min)
#   high:   [15, inf) already past a full minimum-length incident: a genuinely prolonged delay
# No ground-truth severity exists anywhere else in this repo (severity is otherwise an
# ungraded free-text field from the LLM) — this scheme is a deliberate, documented
# choice, not a discovered fact; see docs/TALK2-MODEL-SPECTRUM-ACCURACY-PLAN.md.
SEVERITY_LOW_MAX_ETA_SLIP_MIN = 5.0
SEVERITY_MEDIUM_MAX_ETA_SLIP_MIN = 15.0

# LlmGenerationConfig's own default (60s) is tuned for nothing in particular; on a Pi 4
# CPU-only backend, a full max_tokens completion for these prompt lengths routinely
# exceeds it, which silently turns "format reliability"/"latency" measurements into a
# measurement of the timeout instead of the model. Evals need a floor generous enough
# to let a real completion finish.
DEFAULT_EVAL_TIMEOUT_SECONDS = 180.0


@dataclass
class Trial:
    raw_output: str
    latency_seconds: float
    parsed: dict | None
    error: str | None = None


def run_enrichment_trials(
    backend: LlmBackend,
    event: TelemetryEvent,
    n: int,
    timeout_seconds: float = DEFAULT_EVAL_TIMEOUT_SECONDS,
) -> list[Trial]:
    """Call the real Tier 1 enrichment prompt against `event` n times. Never raises —
    a failing call (timeout, bad exit, unparseable output) is recorded as a Trial, not
    an exception, so one flaky run doesn't abort the whole eval."""
    triggered_signals = evaluate_signals(event)
    prompt = render_enrichment_prompt(event, triggered_signals)
    config = LlmGenerationConfig(timeout_seconds=timeout_seconds)
    trials: list[Trial] = []
    for _ in range(n):
        start = time.monotonic()
        try:
            # Deliberately blind: a real LLM subprocess call can fail in ways
            # beyond LlmInferenceError (timeouts, bad exits), and a failure here is a
            # measurement (a format-reliability miss), not a bug to propagate.
            raw = backend.generate(prompt, config)
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


def expected_severity(eta_slip_min: float) -> str:
    """Deterministic severity tier for a given eta_slip_min, per the thresholds above."""
    if eta_slip_min < SEVERITY_LOW_MAX_ETA_SLIP_MIN:
        return "low"
    if eta_slip_min < SEVERITY_MEDIUM_MAX_ETA_SLIP_MIN:
        return "medium"
    return "high"


def check_severity_calibration(events_and_trials: list[tuple[TelemetryEvent, list[Trial]]]) -> dict:
    """(e) SEVERITY CALIBRATION: does the model's "severity" match the tier implied by
    the input's own eta_slip_min (see expected_severity), rather than being a plausible-
    looking but ungrounded guess. Only checks parsed trials — format_reliability already
    covers unparseable output. Takes (event, trials) pairs so the caller can exercise
    multiple tiers in one aggregated result, unlike the single-event grounding check."""
    mismatches = []
    checked = 0
    for event, trials in events_and_trials:
        expected = expected_severity(event.signals.eta_slip_min)
        for trial in trials:
            if trial.parsed is None:
                continue
            checked += 1
            actual = str(trial.parsed.get("severity", "")).strip().lower()
            if actual != expected:
                mismatches.append(
                    {
                        "input_eta_slip_min": event.signals.eta_slip_min,
                        "expected_severity": expected,
                        "actual_severity": actual,
                        "output": trial.parsed,
                    }
                )
    return {
        "total": checked,
        "mismatches": len(mismatches),
        "mismatch_rate": (len(mismatches) / checked) if checked else 0.0,
        "sample_mismatches": mismatches[:5],
    }


@dataclass
class LabeledEvent:
    event: TelemetryEvent
    ground_truth_is_slowdown: bool


def run_directional_accuracy(
    backend: LlmBackend,
    labeled_events: list[LabeledEvent],
    timeout_seconds: float = DEFAULT_EVAL_TIMEOUT_SECONDS,
) -> tuple[dict, list[float]]:
    """(c) DIRECTIONAL ACCURACY: detection is cheap math, not the LLM (per docs/CANON.md), so
    this measures whether that math's flag/no-flag decision matches _ground_truth in the real
    world — while exercising a real LLM call for every event math actually flags, the
    same as the Tier 1 pipeline does live."""
    config = LlmGenerationConfig(timeout_seconds=timeout_seconds)
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
                backend.generate(prompt, config)
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
    severity_calibration: dict = field(default_factory=dict)
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
            "severity_calibration": self.severity_calibration,
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
        if self.severity_calibration:
            sc = self.severity_calibration
            lines.append(
                f"severity calibration mismatches: {sc['mismatch_rate']:.1%} "
                f"({sc['mismatches']}/{sc['total']})"
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


# ---------------------------------------------------------------------------
# Flow B: TelemetryCoprocessorFunction -> LlmTriageFunction (see
# talk1_edge_intelligence.coprocessor / .triage_function). A separate, currently
# unwired pipeline from Flow A above — same cheap-math detection
# (is_probable_slowdown/evaluate_signals), different downstream shape and a
# grammar-constrained LLM step instead of free-text JSON.
#
# Unlike Flow A's EnrichmentCard, the triage card's severity is grammar-forced to
# exactly one of "low"/"medium"/"high" (see triage_function.build_grammar) and its
# eta_impact/truck_id are hardcoded from the input after generation, not model
# output. So here, format reliability measures whether the model's actual
# free-text job (event_label/dispatch_action) came back non-empty and the
# grammar-forced severity parsed as one of its three legal values — a mismatch on
# eta_impact/truck_id would mean the JSON-extraction/grammar-injection plumbing
# broke, not that the model guessed wrong. Severity calibration reuses the exact
# same tiers/thresholds as Flow A's check_severity_calibration (expected_severity
# above) — a shared definition of "matches the input", not a second judgment call.
# ---------------------------------------------------------------------------


@dataclass
class FlowBTrial:
    raw_output: str
    latency_seconds: float
    parsed: dict | None
    error: str | None = None


def run_flow_b_trials(coprocessor, triage, context, event: TelemetryEvent, n: int) -> list[FlowBTrial]:
    """Runs `event` through the real coprocessor once (its output is deterministic
    per event, same as Flow A renders its prompt once) and the real triage step n
    times. If the coprocessor's own gate (is_probable_slowdown / eta_slip_min
    bounds) filters `event` out, returns an empty list rather than raising —
    callers should assert len(trials) == n to catch a badly-chosen test event."""
    payload = coprocessor.process(to_json(event), context)
    trials: list[FlowBTrial] = []
    if payload is None:
        return trials
    for _ in range(n):
        start = time.monotonic()
        try:
            # Deliberately blind, same as Flow A's run_enrichment_trials: a real
            # subprocess call can fail beyond LlmInferenceError, and a failure
            # here is a measurement (a format-reliability miss), not a bug.
            raw = triage.process(payload, context)
        except Exception as exc:  # noqa: BLE001
            trials.append(
                FlowBTrial(raw_output="", latency_seconds=time.monotonic() - start, parsed=None, error=str(exc))
            )
            continue
        latency = time.monotonic() - start
        if raw is None:
            trials.append(
                FlowBTrial(raw_output="", latency_seconds=latency, parsed=None, error="process() returned None")
            )
            continue
        try:
            parsed = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            trials.append(FlowBTrial(raw_output=raw, latency_seconds=latency, parsed=None, error=str(exc)))
            continue
        trials.append(FlowBTrial(raw_output=raw, latency_seconds=latency, parsed=parsed, error=None))
    return trials


def flow_b_format_reliability(event: TelemetryEvent, trials: list[FlowBTrial]) -> dict:
    """(a) FORMAT RELIABILITY for Flow B: a trial only counts as valid if severity
    is one of the three grammar-forced values, event_label/dispatch_action are
    non-empty strings, and eta_impact/truck_id match the input exactly (hardcoded
    post-generation, so a mismatch means the pipeline's plumbing broke, not that
    the model guessed wrong)."""
    valid = 0
    sample_failures = []
    for trial in trials:
        if trial.parsed is None:
            sample_failures.append({"raw_output": trial.raw_output, "error": trial.error})
            continue
        card = trial.parsed
        problems = []
        if card.get("severity") not in ("low", "medium", "high"):
            problems.append(f"severity {card.get('severity')!r} not one of low/medium/high")
        if not isinstance(card.get("event_label"), str) or not card["event_label"].strip():
            problems.append("event_label missing or empty")
        if not isinstance(card.get("dispatch_action"), str) or not card["dispatch_action"].strip():
            problems.append("dispatch_action missing or empty")
        if card.get("eta_impact") != event.signals.eta_slip_min:
            problems.append(f"eta_impact {card.get('eta_impact')!r} != input {event.signals.eta_slip_min}")
        if card.get("truck_id") != event.truck_id:
            problems.append(f"truck_id {card.get('truck_id')!r} != input {event.truck_id!r}")
        if problems:
            sample_failures.append({"raw_output": trial.raw_output, "error": "; ".join(problems)})
        else:
            valid += 1
    return {
        "total": len(trials),
        "parsed": valid,
        "rate": (valid / len(trials)) if trials else 0.0,
        "sample_failures": sample_failures[:5],
    }


def check_flow_b_severity_calibration(events_and_trials: list[tuple[TelemetryEvent, list[FlowBTrial]]]) -> dict:
    """(e) SEVERITY CALIBRATION for Flow B — same tiers/thresholds as Flow A's
    check_severity_calibration above. Only checks trials whose severity parsed as
    one of the three grammar-legal values; a trial that failed format entirely is
    already counted by flow_b_format_reliability, not double-counted here."""
    mismatches = []
    checked = 0
    for event, trials in events_and_trials:
        expected = expected_severity(event.signals.eta_slip_min)
        for trial in trials:
            if trial.parsed is None:
                continue
            actual = trial.parsed.get("severity")
            if actual not in ("low", "medium", "high"):
                continue
            checked += 1
            if actual != expected:
                mismatches.append(
                    {
                        "input_eta_slip_min": event.signals.eta_slip_min,
                        "expected_severity": expected,
                        "actual_severity": actual,
                        "output": trial.parsed,
                    }
                )
    return {
        "total": checked,
        "mismatches": len(mismatches),
        "mismatch_rate": (len(mismatches) / checked) if checked else 0.0,
        "sample_mismatches": mismatches[:5],
    }


@dataclass
class FlowBReport:
    """Same accumulate-then-dump-one-artifact convention as Tier3Report, kept
    separate (own dataclass, own artifact file) rather than reusing Tier3Report's
    fields, since Flow A and Flow B tests can run in the same pytest session and
    would otherwise silently overwrite each other's results."""

    config: dict
    format_reliability: dict = field(default_factory=dict)
    severity_calibration: dict = field(default_factory=dict)
    latency_samples_seconds: list[float] = field(default_factory=list)

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
            "severity_calibration": self.severity_calibration,
            "latency": self.latency_percentiles(),
        }

    def render_summary(self, artifact_path) -> str:
        lat = self.latency_percentiles()
        lines = [
            "",
            "=== Flow B (coprocessor -> triage) eval summary ===",
            f"artifact: {artifact_path}",
            f"model: {self.config.get('model_path')} via {self.config.get('binary_path')}",
        ]
        if self.format_reliability:
            fr = self.format_reliability
            lines.append(f"format reliability: {fr['rate']:.1%} ({fr['parsed']}/{fr['total']} parsed)")
        if self.severity_calibration:
            sc = self.severity_calibration
            lines.append(
                f"severity calibration mismatches: {sc['mismatch_rate']:.1%} "
                f"({sc['mismatches']}/{sc['total']})"
            )
        if lat["n"]:
            lines.append(f"latency: p50={lat['p50_seconds']:.2f}s p95={lat['p95_seconds']:.2f}s (n={lat['n']})")
        return "\n".join(lines)
