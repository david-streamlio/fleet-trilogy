"""Tier 3 model COMPARISON harness — runs the full existing Tier 3 eval set (format
reliability, grounding, severity calibration, directional accuracy, latency, load
time, resident RAM) for EVERY model in models.toml, on identical seeded inputs, and
produces one combined side-by-side artifact + printed table.

This file adds no new eval logic. It wraps the existing eval *definitions* —
run_enrichment_trials / format_reliability / check_grounding /
check_severity_calibration / run_directional_accuracy from eval_lib.py, and the same
event/labeled-batch builders the single-model Tier 3 tests already use
(_truck_47_slowdown_event, _known_value_event, test_severity_calibration._event,
_labeled_batch) — in a loop over models.toml, plus the aggregation/reporting that
reuse doesn't give you for free. Reusing those builders (rather than re-deriving them)
is what guarantees every model in a given run sees byte-identical prompts and the same
labeled batch.

Opt-in (@pytest.mark.model), run via `make compare-models`. Auto-skips if the manifest
has zero available models, same as the single-model Tier 3 tests. If only SOME
manifest models are available, the run proceeds and reports the rest as unavailable
rather than skipping the whole comparison — that's a data point too, not a reason to
hide the ones that ARE available.

GATE 2 (severity confirmation): a model whose gate-1 format_parse_rate clears
--model-format-threshold gets a second, bigger severity-calibration-only run (see
--model-confirm-multiplier in conftest.py) — fixing the case where a low parse rate
starves severity_calibration of samples. `_production_candidates()` then applies
--model-severity-max-mismatch-rate to the gate-2-confirmed numbers to answer directly
whether any model is reliable enough for production use on this task, printed as a
PASS/reject list rather than left implicit in the per-axis comparison table.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import LlmGenerationConfig, SubprocessLlmBackend

from tests.model.eval_lib import (
    _percentile,
    check_grounding,
    check_severity_calibration,
    format_reliability,
    peak_child_rss_mb,
    run_directional_accuracy,
    run_enrichment_trials,
)
from tests.model.models_manifest import ModelEntry, load_models_manifest
from tests.model.test_directional_accuracy import _labeled_batch
from tests.model.test_format_reliability import _truck_47_slowdown_event
from tests.model.test_grounding import _known_value_event
from tests.model.test_severity_calibration import _event as _severity_tier_event

pytestmark = pytest.mark.model

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_DIR = REPO_ROOT / "eval-results"
COHERENCE_PROMPT = "The capital of France is"

# (report key, path to the value inside a per-model result dict, "higher"/"lower" is better)
AXES: list[tuple[str, tuple[str, ...], str]] = [
    ("format_parse_rate", ("format_reliability", "rate"), "higher"),
    ("grounding_violation_rate", ("grounding", "violation_rate"), "lower"),
    ("severity_mismatch_rate", ("severity_calibration", "mismatch_rate"), "lower"),
    ("precision", ("directional_accuracy", "precision"), "higher"),
    ("recall", ("directional_accuracy", "recall"), "higher"),
    ("f1", ("directional_accuracy", "f1"), "higher"),
    ("latency_p50_seconds", ("latency", "p50_seconds"), "lower"),
    ("latency_p95_seconds", ("latency", "p95_seconds"), "lower"),
    ("tokens_per_sec_approx", ("tokens_per_sec_approx",), "higher"),
    ("load_time_seconds", ("load_time_seconds",), "lower"),
    ("resident_ram_mb_after", ("resident_ram_mb_after",), "lower"),
]
QUALITY_AXES = {
    "format_parse_rate",
    "grounding_violation_rate",
    "severity_mismatch_rate",
    "precision",
    "recall",
    "f1",
}


def _decision_grade() -> str:
    """Labels whether THIS run's numbers should be used to pick the stage model.

    Per the pivot decision: only a Pi 4 (the actual target) run is decision-grade for
    speed/RAM. A dev-machine (M4) run is still decision-grade for the *quality* axes
    (format/grounding/accuracy don't depend on which CPU ran them), just not for
    latency/tokens-per-sec/RAM/load-time.
    """
    if platform.system() == "Linux" and platform.machine().lower() in {"aarch64", "armv7l", "armv6l"}:
        return "full (Pi 4 target)"
    return "quality-only (non-target hardware)"


def _get_path(d: dict, path: tuple[str, ...]):
    for key in path:
        if d is None:
            return None
        d = d.get(key)
    return d


def _measure_load_time_seconds(backend: SubprocessLlmBackend) -> float | None:
    """Approximate: wall time for a single 1-token completion, which necessarily
    includes process startup + model load + first-token latency (there's no separate
    "load only" flag exposed through our CLI wrapping). Not a precise model-load-only
    number — treat it as an upper bound on load time, dominated by load for any model
    this small relative to a single token's generation cost."""
    start = time.monotonic()
    try:
        backend.generate(COHERENCE_PROMPT, LlmGenerationConfig(max_tokens=1))
    except Exception:  # noqa: BLE001 - a failed warmup call is "no reading", not a bug
        return None
    return time.monotonic() - start


def _run_one_model(entry: ModelEntry, request: pytest.FixtureRequest, labeled_events) -> dict:
    if not entry.is_available():
        return {
            "id": entry.id,
            "display_name": entry.display_name,
            "available": False,
            "binary_path": str(entry.binary_path) if entry.binary_path else None,
            "model_path": str(entry.model_path) if entry.model_path else None,
        }

    backend = SubprocessLlmBackend(
        binary_path=entry.binary_path,
        model_path=entry.model_path,
        mock=False,
        extra_args=entry.extra_args,
    )

    ram_before_mb = peak_child_rss_mb()
    load_time_seconds = _measure_load_time_seconds(backend)

    n = request.config.getoption("--model-eval-runs")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    format_threshold = request.config.getoption("--model-format-threshold")
    confirm_multiplier = request.config.getoption("--model-confirm-multiplier")

    fr_event = _truck_47_slowdown_event()
    fr_trials = run_enrichment_trials(backend, fr_event, n, timeout_seconds)
    fr_result = format_reliability(fr_trials)

    gr_event = _known_value_event()
    gr_trials = run_enrichment_trials(backend, gr_event, n, timeout_seconds)
    gr_result = check_grounding(gr_event, gr_trials)

    # 3.0/10.0/20.0 -> low/medium/high per eval_lib's severity thresholds; same split as
    # the single-model test_severity_calibration.py so this comparison run and a
    # standalone `make test-model` run measure identically.
    per_tier_n = max(1, n // 3)
    sc_events_and_trials = []
    sc_latencies: list[float] = []
    for eta_slip_min in (3.0, 10.0, 20.0):
        sc_event = _severity_tier_event(eta_slip_min)
        sc_trials = run_enrichment_trials(backend, sc_event, per_tier_n, timeout_seconds)
        sc_events_and_trials.append((sc_event, sc_trials))
        sc_latencies.extend(t.latency_seconds for t in sc_trials)
    sc_result_gate1 = check_severity_calibration(sc_events_and_trials)
    sc_result_gate1["gate2_confirmed"] = False

    # GATE 2: a model that parses reliably (gate 1's format_parse_rate clears the same
    # bar test_format_reliability.py gates on) gets its severity check re-run at a much
    # bigger sample, severity-axis only. This exists because a low parse rate silently
    # starves severity_calibration of samples (e.g. a 0.4 format rate with n=10/tier
    # leaves as few as 8 parsed cards total to judge severity on) — not reliable enough
    # to call a model good or bad on this axis. Format/grounding/directional are NOT
    # re-run here: they already have a full n-sample at gate 1, and re-running everything
    # at 3x would roughly triple total runtime for every model that passes gate 1, most of
    # which parse fine already.
    gate2_promoted = fr_result["rate"] >= format_threshold
    sc2_latencies: list[float] = []
    sc2_trials_flat = []
    if gate2_promoted:
        confirm_per_tier_n = max(per_tier_n, round(per_tier_n * confirm_multiplier))
        sc2_events_and_trials = []
        for eta_slip_min in (3.0, 10.0, 20.0):
            sc2_event = _severity_tier_event(eta_slip_min)
            sc2_trials = run_enrichment_trials(backend, sc2_event, confirm_per_tier_n, timeout_seconds)
            sc2_events_and_trials.append((sc2_event, sc2_trials))
            sc2_latencies.extend(t.latency_seconds for t in sc2_trials)
        sc_result = check_severity_calibration(sc2_events_and_trials)
        sc_result["gate2_confirmed"] = True
        sc_result["gate2_per_tier_n"] = confirm_per_tier_n
        sc_result["gate2_format_threshold"] = format_threshold
        sc2_trials_flat = [t for _event, trials in sc2_events_and_trials for t in trials]
    else:
        sc_result = sc_result_gate1

    da_result, da_latencies = run_directional_accuracy(backend, labeled_events, timeout_seconds)

    ram_after_mb = peak_child_rss_mb()

    all_latencies = (
        [t.latency_seconds for t in fr_trials]
        + [t.latency_seconds for t in gr_trials]
        + sc_latencies
        + sc2_latencies
        + da_latencies
    )
    ordered = sorted(all_latencies)
    latency = {
        "p50_seconds": _percentile(ordered, 0.50) if ordered else None,
        "p95_seconds": _percentile(ordered, 0.95) if ordered else None,
        "n": len(ordered),
    }

    sc_trials_flat = [t for _event, trials in sc_events_and_trials for t in trials]
    tokens_per_sec_samples = [
        len(t.raw_output.split()) / t.latency_seconds
        for t in (fr_trials + gr_trials + sc_trials_flat + sc2_trials_flat)
        if t.parsed is not None and t.latency_seconds > 0
    ]
    tokens_per_sec_approx = (
        sum(tokens_per_sec_samples) / len(tokens_per_sec_samples) if tokens_per_sec_samples else None
    )

    return {
        "id": entry.id,
        "display_name": entry.display_name,
        "available": True,
        "binary_path": str(entry.binary_path),
        "model_path": str(entry.model_path),
        "extra_args": list(entry.extra_args),
        "format_reliability": fr_result,
        "grounding": gr_result,
        "severity_calibration": sc_result,
        "severity_calibration_gate1": sc_result_gate1,
        "directional_accuracy": da_result,
        "latency": latency,
        "tokens_per_sec_approx": tokens_per_sec_approx,
        "tokens_per_sec_note": (
            "approximate — whitespace word count / latency over parsed trials, "
            "not an exact tokenizer count"
        ),
        "load_time_seconds": load_time_seconds,
        "resident_ram_mb_before": ram_before_mb,
        "resident_ram_mb_after": ram_after_mb,
        "resident_ram_mb_note": (
            "RUSAGE_CHILDREN ru_maxrss is a cumulative max for the whole test session "
            "and isn't resettable per model; this is exact for the first model in a "
            "run (or when a model is run alone) and otherwise a floor — not a true "
            "peak — for models measured later in the same run."
        ),
    }


def _build_comparison(results: dict[str, dict]) -> dict:
    comparison: dict[str, dict] = {}
    for axis_name, path, direction in AXES:
        values = {}
        for model_id, result in results.items():
            if not result.get("available"):
                continue
            values[model_id] = _get_path(result, path)
        present = {k: v for k, v in values.items() if v is not None}
        best = None
        if present:
            best = max(present, key=present.get) if direction == "higher" else min(present, key=present.get)
        comparison[axis_name] = {"direction": direction, "values": values, "best": best}
    return comparison


def _build_recommendation(results: dict[str, dict], comparison: dict, decision_grade: str) -> str:
    unavailable = [r["display_name"] for r in results.values() if not r.get("available")]
    lines = []
    if unavailable:
        lines.append(f"Not measured (unavailable on this host): {', '.join(unavailable)}.")

    def _fmt_value(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)

    for axis_name, path, direction in AXES:
        axis = comparison[axis_name]
        # axis["values"] can be non-empty (a real dict entry) while every value in
        # it is None -- e.g. severity_mismatch_rate when the only model in a run
        # never reached gate 2. A bare truthiness check on the dict misses that and
        # crashes below on results[None] -- checking axis["best"] (only set when
        # _build_comparison found at least one non-None value) is the real signal.
        if axis["best"] is None:
            lines.append(f"{axis_name}: no data.")
            continue
        best_id = axis["best"]
        best_name = results[best_id]["display_name"]
        others = ", ".join(
            f"{results[mid]['display_name']}={_fmt_value(v)}" for mid, v in axis["values"].items() if mid != best_id
        )
        informational = axis_name not in QUALITY_AXES and decision_grade != "full (Pi 4 target)"
        prefix = "[informational — non-target hardware] " if informational else ""
        lines.append(
            f"{prefix}{axis_name}: {best_name} leads ({_fmt_value(axis['values'][best_id])})"
            + (f" vs {others}" if others else "")
        )

    lines.append(
        "This note does not pick a stage model. Quality axes above are decision-relevant "
        "on any host; speed/RAM axes only count when measured on the Pi 4 target."
    )
    return "\n".join(lines)


def _production_candidates(
    results: dict[str, dict], format_threshold: float, severity_threshold: float
) -> dict:
    """Models with an evidence-backed case for production use on THIS task: gate 1's
    format_parse_rate cleared the bar (so gate 2 ran, giving a trustworthy severity
    sample size) AND the gate-2-confirmed severity mismatch rate is at or below
    severity_threshold. Answers "does anything here actually work" directly, rather
    than leaving it implicit in a table of per-axis leaders — a model can "lead" an
    axis among 9 bad options without being good enough to ship. Still not a final
    pick: Pi 4 latency/RAM footprint applies to any PASS entry same as always."""
    passed = []
    rejected = []
    for mid, r in results.items():
        if not r.get("available"):
            continue
        sc = r.get("severity_calibration", {})
        entry = {
            "id": mid,
            "display_name": r["display_name"],
            "format_parse_rate": r.get("format_reliability", {}).get("rate"),
            "gate2_confirmed": sc.get("gate2_confirmed", False),
            "severity_mismatch_rate": sc.get("mismatch_rate"),
            "severity_sample_n": sc.get("total"),
        }
        if (
            sc.get("gate2_confirmed")
            and sc.get("mismatch_rate") is not None
            and sc["mismatch_rate"] <= severity_threshold
        ):
            passed.append(entry)
        else:
            rejected.append(entry)
    return {
        "format_threshold": format_threshold,
        "severity_threshold": severity_threshold,
        "passed": passed,
        "rejected": rejected,
    }


def _render_table(report: dict, artifact_path: Path) -> str:
    model_ids = list(report["models"].keys())
    headers = ["axis"] + [report["models"][mid]["display_name"] for mid in model_ids]
    rows = []
    for axis_name, _path, _direction in AXES:
        row = [axis_name]
        for mid in model_ids:
            result = report["models"][mid]
            if not result.get("available"):
                row.append("unavailable")
                continue
            value = report["comparison"][axis_name]["values"].get(mid)
            row.append("n/a" if value is None else (f"{value:.3f}" if isinstance(value, float) else str(value)))
        rows.append(row)

    widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(len(headers))]
    lines = [
        "",
        "=== Tier 3 model COMPARISON ===",
        f"artifact: {artifact_path}",
        f"host: {report['host']} ({report['arch']}, {report['platform']})",
        f"decision_grade: {report['decision_grade']}",
        "  ".join(h.ljust(w) for h, w in zip(headers, widths)),
        "  ".join("-" * w for w in widths),
    ]
    for row in rows:
        lines.append("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
    lines.append("")
    lines.append("--- recommendation (does not auto-pick — human decides) ---")
    lines.append(report["recommendation"])

    pc = report["production_candidates"]
    lines.append("")
    lines.append(
        f"--- production candidates (format_parse_rate>={pc['format_threshold']:.0%}, "
        f"gate-2-confirmed severity_mismatch_rate<={pc['severity_threshold']:.0%}) ---"
    )
    if pc["passed"]:
        for e in pc["passed"]:
            lines.append(
                f"  PASS   {e['display_name']}: severity_mismatch={e['severity_mismatch_rate']:.1%} "
                f"(n={e['severity_sample_n']}, gate-2 confirmed)"
            )
    else:
        lines.append(
            "  NONE of the tested models met this bar. See rejected reasons below — "
            "that is a real finding, not a reason to lower the bar quietly."
        )
    for e in pc["rejected"]:
        if not e["gate2_confirmed"]:
            reason = f"format_parse_rate={e['format_parse_rate']:.3f} below threshold — never reached gate 2"
        else:
            reason = f"severity_mismatch={e['severity_mismatch_rate']:.1%} (n={e['severity_sample_n']}) exceeds bar"
        lines.append(f"  reject {e['display_name']}: {reason}")
    lines.append(
        "Evidence for/against production use on THIS task — not a final pick. Pi 4 "
        "latency/RAM footprint still applies to any PASS entry before it ships."
    )
    return "\n".join(lines)


def test_compare_models(request: pytest.FixtureRequest) -> None:
    manifest = load_models_manifest()
    available = [e for e in manifest if e.is_available()]
    if not available:
        pytest.skip(
            "No models.toml entries are available (missing binary/model paths). Set "
            "the env vars named in models.toml, or run `make compare-models` on a "
            "host with the models present. Skipped, not failed — `make test`/"
            "`make test-integration` are unaffected."
        )

    labeled_events = _labeled_batch(request)

    results = {entry.id: _run_one_model(entry, request, labeled_events) for entry in manifest}
    comparison = _build_comparison(results)
    decision_grade = _decision_grade()
    recommendation = _build_recommendation(results, comparison, decision_grade)
    production_candidates = _production_candidates(
        results,
        format_threshold=request.config.getoption("--model-format-threshold"),
        severity_threshold=request.config.getoption("--model-severity-max-mismatch-rate"),
    )

    report = {
        "host": platform.node(),
        "arch": platform.machine(),
        "platform": platform.platform(),
        "decision_grade": decision_grade,
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed_config": {
            "model_eval_runs": request.config.getoption("--model-eval-runs"),
            "model_timeout_seconds": request.config.getoption("--model-timeout-seconds"),
            "accuracy_fleet_size": request.config.getoption("--model-accuracy-fleet-size"),
            "accuracy_incident_trucks": request.config.getoption("--model-accuracy-incident-trucks"),
            "accuracy_ticks": request.config.getoption("--model-accuracy-ticks"),
            "accuracy_seed": request.config.getoption("--model-accuracy-seed"),
        },
        "models": results,
        "comparison": comparison,
        "recommendation": recommendation,
        "production_candidates": production_candidates,
    }

    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = EVAL_RESULTS_DIR / f"compare-{platform.node()}-{timestamp}.json"
    artifact_path.write_text(json.dumps(report, indent=2))

    # Printed directly (not via a pytest_terminal_summary hook, which only conftest.py
    # plugins can register) — `make compare-models` passes -s so this isn't captured.
    print(_render_table(report, artifact_path))
