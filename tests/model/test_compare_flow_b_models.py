"""Tier 3 model COMPARISON harness for Flow B (TelemetryCoprocessorFunction ->
LlmTriageFunction — see talk1_edge_intelligence.coprocessor / .triage_function).
Same idea as test_compare_models.py (run the full eval set for every model in
models.toml, on identical seeded inputs, one combined side-by-side artifact +
printed table) but for the OTHER pipeline: grammar-constrained triage cards,
not free-text EnrichmentCard JSON.

Deliberately narrower axis set than Flow A's comparison: no grounding or
directional_accuracy axes. Grounding doesn't apply here (eta_impact/truck_id
are hardcoded post-generation, not model output — see eval_lib.py's Flow B
section), and directional accuracy would just be re-measuring the exact same
is_probable_slowdown/evaluate_signals cheap math Flow A's comparison already
covers, since TelemetryCoprocessorFunction reuses it verbatim rather than
duplicating a second detection path.

Opt-in (@pytest.mark.model), run via `make compare-flow-b-models`. Auto-skips
if the manifest has zero available models, same as test_compare_models.py.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import LlmGenerationConfig, SubprocessLlmBackend
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import LlmTriageFunction

from tests.model.conftest import _FlowBEvalContext
from tests.model.eval_lib import (
    _percentile,
    check_flow_b_severity_calibration,
    flow_b_format_reliability,
    peak_child_rss_mb,
    run_flow_b_trials,
)
from tests.model.models_manifest import ModelEntry, load_models_manifest
from tests.model.test_flow_b_triage import _event as _flow_b_tier_event

pytestmark = pytest.mark.model

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_DIR = REPO_ROOT / "eval-results"
COHERENCE_PROMPT = "The capital of France is"

AXES: list[tuple[str, tuple[str, ...], str]] = [
    ("format_parse_rate", ("format_reliability", "rate"), "higher"),
    ("severity_mismatch_rate", ("severity_calibration", "mismatch_rate"), "lower"),
    ("latency_p50_seconds", ("latency", "p50_seconds"), "lower"),
    ("latency_p95_seconds", ("latency", "p95_seconds"), "lower"),
    ("tokens_per_sec_approx", ("tokens_per_sec_approx",), "higher"),
    ("load_time_seconds", ("load_time_seconds",), "lower"),
    ("resident_ram_mb_after", ("resident_ram_mb_after",), "lower"),
]
QUALITY_AXES = {"format_parse_rate", "severity_mismatch_rate"}


def _decision_grade() -> str:
    """Same rule as test_compare_models.py: only a Pi 4 (the actual target) run is
    decision-grade for speed/RAM; format/severity don't depend on which CPU ran them."""
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
    """Same approximation as test_compare_models.py's helper, on a standalone
    backend (not the pipeline's internal one) so this warmup call is identical
    across both comparison harnesses."""
    start = time.monotonic()
    try:
        backend.generate(COHERENCE_PROMPT, LlmGenerationConfig(max_tokens=1))
    except Exception:  # noqa: BLE001 - a failed warmup call is "no reading", not a bug
        return None
    return time.monotonic() - start


def _run_one_model(entry: ModelEntry, request: pytest.FixtureRequest) -> dict:
    if not entry.is_available():
        return {
            "id": entry.id,
            "display_name": entry.display_name,
            "available": False,
            "binary_path": str(entry.binary_path) if entry.binary_path else None,
            "model_path": str(entry.model_path) if entry.model_path else None,
        }

    n = request.config.getoption("--model-eval-runs")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    format_threshold = request.config.getoption("--model-format-threshold")
    confirm_multiplier = request.config.getoption("--model-confirm-multiplier")

    warmup_backend = SubprocessLlmBackend(
        binary_path=entry.binary_path,
        model_path=entry.model_path,
        mock=False,
        extra_args=entry.extra_args,
    )
    ram_before_mb = peak_child_rss_mb()
    load_time_seconds = _measure_load_time_seconds(warmup_backend)

    context = _FlowBEvalContext(
        {
            "llm_binary_path": str(entry.binary_path),
            "llm_model_path": str(entry.model_path),
            "timeout_seconds": str(timeout_seconds),
        }
    )
    coprocessor = TelemetryCoprocessorFunction()
    triage = LlmTriageFunction()

    # 4.0/10.0/20.0 -> low/medium/high per eval_lib's severity thresholds — same
    # tiers test_flow_b_triage.py's single-model test already exercises, so a
    # comparison run and a standalone `make test-model` run measure identically.
    per_tier_n = max(1, n // 3)
    events_and_trials = []
    for eta_slip_min in (4.0, 10.0, 20.0):
        event = _flow_b_tier_event(eta_slip_min)
        trials = run_flow_b_trials(coprocessor, triage, context, event, per_tier_n)
        events_and_trials.append((event, trials))

    fr_result = {"total": 0, "parsed": 0, "sample_failures": []}
    for event, trials in events_and_trials:
        tier_result = flow_b_format_reliability(event, trials)
        fr_result["total"] += tier_result["total"]
        fr_result["parsed"] += tier_result["parsed"]
        fr_result["sample_failures"].extend(tier_result["sample_failures"])
    fr_result["rate"] = (fr_result["parsed"] / fr_result["total"]) if fr_result["total"] else 0.0
    fr_result["sample_failures"] = fr_result["sample_failures"][:5]

    sc_result_gate1 = check_flow_b_severity_calibration(events_and_trials)
    sc_result_gate1["gate2_confirmed"] = False

    # GATE 2: same rationale as test_compare_models.py — a model that parses
    # reliably gets its severity check re-run at a much bigger sample,
    # severity-axis only, so a low parse rate can't starve the severity sample.
    gate2_promoted = fr_result["rate"] >= format_threshold
    gate2_events_and_trials = []
    if gate2_promoted:
        confirm_per_tier_n = max(per_tier_n, round(per_tier_n * confirm_multiplier))
        for eta_slip_min in (4.0, 10.0, 20.0):
            event = _flow_b_tier_event(eta_slip_min)
            trials = run_flow_b_trials(coprocessor, triage, context, event, confirm_per_tier_n)
            gate2_events_and_trials.append((event, trials))
        sc_result = check_flow_b_severity_calibration(gate2_events_and_trials)
        sc_result["gate2_confirmed"] = True
        sc_result["gate2_per_tier_n"] = confirm_per_tier_n
        sc_result["gate2_format_threshold"] = format_threshold
    else:
        sc_result = sc_result_gate1

    ram_after_mb = peak_child_rss_mb()

    all_trials = [t for _event, trials in (events_and_trials + gate2_events_and_trials) for t in trials]
    ordered = sorted(t.latency_seconds for t in all_trials)
    latency = {
        "p50_seconds": _percentile(ordered, 0.50) if ordered else None,
        "p95_seconds": _percentile(ordered, 0.95) if ordered else None,
        "n": len(ordered),
    }

    tokens_per_sec_samples = [
        len(t.raw_output.split()) / t.latency_seconds
        for t in all_trials
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
        "severity_calibration": sc_result,
        "severity_calibration_gate1": sc_result_gate1,
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

    for axis_name, _path, _direction in AXES:
        axis = comparison[axis_name]
        if not axis["values"]:
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


def _production_candidates(results: dict[str, dict], format_threshold: float, severity_threshold: float) -> dict:
    """Same evidence-backed-case rule as test_compare_models.py's version, scoped
    to Flow B's two quality axes (format_parse_rate, gate-2-confirmed
    severity_mismatch_rate)."""
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
        "=== Tier 3 Flow B model COMPARISON ===",
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


def test_compare_flow_b_models(request: pytest.FixtureRequest) -> None:
    manifest = load_models_manifest()
    available = [e for e in manifest if e.is_available()]
    if not available:
        pytest.skip(
            "No models.toml entries are available (missing binary/model paths). Set "
            "the env vars named in models.toml, or run `make compare-flow-b-models` on "
            "a host with the models present. Skipped, not failed — `make test`/"
            "`make test-integration` are unaffected."
        )

    results = {entry.id: _run_one_model(entry, request) for entry in manifest}
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
        },
        "models": results,
        "comparison": comparison,
        "recommendation": recommendation,
        "production_candidates": production_candidates,
    }

    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = EVAL_RESULTS_DIR / f"compare-flow-b-{platform.node()}-{timestamp}.json"
    artifact_path.write_text(json.dumps(report, indent=2))

    # Printed directly (not via pytest_terminal_summary), same as test_compare_models.py
    # — `make compare-flow-b-models` passes -s so this isn't captured.
    print(_render_table(report, artifact_path))
