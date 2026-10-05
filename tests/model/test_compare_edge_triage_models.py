"""Tier 3 model COMPARISON harness for the Edge Triage Pipeline (TelemetryCoprocessorFunction ->
LlmTriageFunction — see talk1_edge_intelligence.coprocessor / .triage_function).
Same idea as test_compare_models.py (run the full eval set for every model in
models.toml, on identical seeded inputs, one combined side-by-side artifact +
printed table) but for the OTHER pipeline: grammar-constrained triage cards,
not free-text EnrichmentCard JSON.

Deliberately narrower axis set than Flow A's comparison: no grounding or
directional_accuracy axes. Grounding doesn't apply here (eta_impact/truck_id
are hardcoded post-generation, not model output — see eval_lib.py's Edge Triage Pipeline
section), and directional accuracy would just be re-measuring the exact same
is_probable_slowdown/evaluate_signals cheap math Flow A's comparison already
covers, since TelemetryCoprocessorFunction reuses it verbatim rather than
duplicating a second detection path.

Opt-in (@pytest.mark.model), run via `make compare-edge-triage-models`. Auto-skips
if the manifest has zero available models, same as test_compare_models.py.

`--model-backend` picks how LlmTriageFunction runs each model: in-process (the
default since 2026-10-05) or llama-server, which every Talk 2 hardware-spectrum run
before that date used. `--vary-events` sends a different event on every call (see
eval_lib.run_edge_triage_trials_interleaved) so latency includes reading the prompt,
not just generating the card. `--triage-prompt event-last` swaps in
EVENT_LAST_PROMPT_TEMPLATE, which lets more of the prompt stay cached across events.
"""

from __future__ import annotations

import json
import platform
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import LlmGenerationConfig, LlmServerBackend
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import DEFAULT_THREADS, LlmTriageFunction

from tests.model.conftest import _EdgeTriageEvalContext, triage_prompt_template
from tests.model.eval_lib import (
    ESCALATION_SCENARIOS,
    _percentile,
    check_escalation_direction,
    edge_triage_format_reliability,
    peak_child_rss_mb,
    peak_self_rss_mb,
    run_edge_triage_trials,
    run_edge_triage_trials_interleaved,
)
from tests.model.models_manifest import (
    ModelEntry,
    load_models_manifest,
    parse_model_ids,
)
from tests.model.test_edge_triage import _canonical_event

pytestmark = pytest.mark.model

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_DIR = REPO_ROOT / "eval-results"

AXES: list[tuple[str, tuple[str, ...], str]] = [
    ("format_parse_rate", ("format_reliability", "rate"), "higher"),
    ("escalation_mismatch_rate", ("escalation_calibration", "mismatch_rate"), "lower"),
    ("latency_p50_seconds", ("latency", "p50_seconds"), "lower"),
    ("latency_p95_seconds", ("latency", "p95_seconds"), "lower"),
    ("tokens_per_sec_approx", ("tokens_per_sec_approx",), "higher"),
    ("load_time_seconds", ("load_time_seconds",), "lower"),
    ("resident_ram_mb_after", ("resident_ram_mb_after",), "lower"),
]
QUALITY_AXES = {"format_parse_rate", "escalation_mismatch_rate"}


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


def _server_binary_path(completion_binary_path: Path | None) -> Path | None:
    """models.toml's binary_path_env/default_binary_path all point at
    llama-completion — correct for Flow A's test_compare_models.py, which still
    uses SubprocessLlmBackend, so that can't just be repointed at llama-server.
    Both binaries are always built side by side in the same llama.cpp build output
    directory in this repo's setup (see docs/PI4-RUNBOOK.md /
    cmake --build build --target llama-server), so llama-server's path is derived
    from llama-completion's sibling rather than needing a second parallel set of
    per-model env vars in models.toml just for this one axis. A real run found out
    the hard way what happens without this: LlmServerBackend launched
    llama-completion with --host/--port, which it doesn't understand, and it
    exited immediately ("llama-server exited during startup (code 1)" — a
    misleading error, since it wasn't actually running llama-server at all).
    """
    if completion_binary_path is None:
        return None
    return completion_binary_path.parent / "llama-server"


def _measure_load_time_seconds(entry: ModelEntry, threads: int, server_args: str = "") -> float | None:
    """Time to start a standalone LlmServerBackend and have it become healthy —
    a real, direct measurement now that the backend is a persistent server, not
    the old one-shot-completion warmup hack (that approach measured a single
    generate() call's wall time as a proxy for load time; starting the actual
    server IS the load). Closed immediately after — this is a throwaway
    measurement, separate from the real backend LlmTriageFunction starts for the
    trials below.

    entry.extra_args (e.g. `-no-cnv`) is deliberately NOT passed here: it's a
    llama-completion-specific one-shot flag, and llama-server rejects it outright
    ("invalid argument: -no-cnv", verified live) — CLI flags are backend-specific,
    not model-specific, so they don't carry over between SubprocessLlmBackend and
    LlmServerBackend.
    """
    backend = LlmServerBackend(
        binary_path=_server_binary_path(entry.binary_path),
        model_path=entry.model_path,
        threads=threads,
        extra_args=tuple(server_args.split()),
    )
    start = time.monotonic()
    try:
        backend.start()
    except Exception:  # noqa: BLE001 - a failed warmup call is "no reading", not a bug
        return None
    finally:
        backend.close()
    return time.monotonic() - start


def _measure_in_process_load_time_seconds(triage: LlmTriageFunction, context: _EdgeTriageEvalContext) -> float | None:
    """The in-process counterpart of _measure_load_time_seconds: loading the model
    into the triage function's own backend IS the load, so this times that once,
    up front, rather than loading a throwaway copy (which on a 4 GB Pi would mean
    two copies' worth of page cache churn for one number). build_card's own start()
    call is then a no-op.

    Includes a one-token generation, to match what llama-server's load time
    includes: llama-server runs a warm-up pass at startup that pulls every weight
    page in from the memory-mapped file, and llama-cpp-python doesn't, so without
    this the first trial would pay for reading the model from disk instead."""
    triage._configure(context)
    start = time.monotonic()
    try:
        triage._backend.start()
        triage._backend.generate("Hello", LlmGenerationConfig(max_tokens=1, timeout_seconds=1800.0))
    except Exception:  # noqa: BLE001 - a failed load is "no reading"; the trials then record the error
        return None
    return time.monotonic() - start


def _timings_summary(trials: list) -> dict | None:
    """Medians over the calls whose backend reported a prompt/generation split (both
    backends' last_timings), plus totals. None if no call reported one."""
    timed = [t.timings for t in trials if t.timings]
    if not timed:
        return None
    keys = ("prompt_tokens", "prompt_tokens_evaluated", "prompt_ms", "generated_tokens", "generation_ms")
    summary = {
        f"median_{key}": statistics.median(t[key] for t in timed if t.get(key) is not None)
        for key in keys
        if any(t.get(key) is not None for t in timed)
    }
    summary["total_prompt_ms"] = sum(t.get("prompt_ms") or 0 for t in timed)
    summary["total_generation_ms"] = sum(t.get("generation_ms") or 0 for t in timed)
    summary["n"] = len(timed)
    return summary


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
    threads = request.config.getoption("--model-threads") or DEFAULT_THREADS
    backend_kind = request.config.getoption("--model-backend")
    gpu_layers = request.config.getoption("--model-gpu-layers")
    vary_events = request.config.getoption("--vary-events")
    triage_prompt = request.config.getoption("--triage-prompt")
    server_args = request.config.getoption("--model-server-args")
    # In-process, the model lives in this test process, not in a child.
    peak_rss_mb = peak_self_rss_mb if backend_kind == "inprocess" else peak_child_rss_mb

    ram_before_mb = peak_rss_mb()
    context = _EdgeTriageEvalContext(
        {
            "llm_backend": backend_kind,
            "llm_binary_path": str(_server_binary_path(entry.binary_path)),
            "llm_model_path": str(entry.model_path),
            "llm_gpu_layers": str(gpu_layers),
            "prompt_template": triage_prompt_template(triage_prompt),
            "llm_extra_args": server_args,
            "timeout_seconds": str(timeout_seconds),
            "threads": str(threads),
        }
    )
    coprocessor = TelemetryCoprocessorFunction()
    triage = LlmTriageFunction()
    if backend_kind == "inprocess":
        load_time_seconds = _measure_in_process_load_time_seconds(triage, context)
    else:
        load_time_seconds = _measure_load_time_seconds(entry, threads, server_args)

    trials_started_utc = datetime.now(tz=UTC)
    trials_started = time.monotonic()
    try:
        # Gate 1: format reliability on one canonical event, full N — see
        # test_edge_triage.py's module docstring for why this is no longer
        # tier-based (severity is cheap math now, identical for every model).
        # --vary-events cycles that event through the three scenarios'
        # operational contexts instead (ceil(n/3) calls each), so consecutive
        # prompts differ from the weather line on; format scoring doesn't depend
        # on the context, only on the event's truck_id/eta_impact, which stay fixed.
        format_event = _canonical_event()
        if vary_events:
            per_variant_n = -(-n // len(ESCALATION_SCENARIOS))
            variants = [
                {"event": format_event, "contextual_trigger_overrides": scenario["contextual_triggers"]}
                for scenario in ESCALATION_SCENARIOS.values()
            ]
            format_trials = [
                t
                for trials in run_edge_triage_trials_interleaved(coprocessor, triage, context, variants, per_variant_n)
                for t in trials
            ]
        else:
            format_trials = run_edge_triage_trials(coprocessor, triage, context, format_event, n)
        fr_result = edge_triage_format_reliability(format_event, format_trials)

        # GATE 2: same two-stage rationale as test_compare_models.py, retargeted at
        # escalation direction (see eval_lib.check_escalation_direction) now that
        # severity itself no longer varies by model. A model that parses reliably
        # gets the three escalation scenarios re-run at a much bigger per-scenario
        # sample so a low parse rate can't starve the escalation-direction sample.
        per_scenario_n = max(1, n // 3)
        gate2_promoted = fr_result["rate"] >= format_threshold
        gate2_scenario_trials: dict[str, list] = {}
        if gate2_promoted:
            confirm_per_scenario_n = max(per_scenario_n, round(per_scenario_n * confirm_multiplier))
            if vary_events:
                # The same scenarios, called round-robin so no two consecutive calls repeat.
                variants = [
                    {
                        "event": _canonical_event(),
                        "contextual_trigger_overrides": scenario["contextual_triggers"],
                        "baseline_severity_override": "medium",
                    }
                    for scenario in ESCALATION_SCENARIOS.values()
                ]
                interleaved = run_edge_triage_trials_interleaved(
                    coprocessor, triage, context, variants, confirm_per_scenario_n
                )
                gate2_scenario_trials = dict(zip(ESCALATION_SCENARIOS, interleaved, strict=True))
            else:
                for scenario_name, scenario in ESCALATION_SCENARIOS.items():
                    scenario_event = _canonical_event()
                    trials = run_edge_triage_trials(
                        coprocessor,
                        triage,
                        context,
                        scenario_event,
                        confirm_per_scenario_n,
                        contextual_trigger_overrides=scenario["contextual_triggers"],
                        baseline_severity_override="medium",
                    )
                    gate2_scenario_trials[scenario_name] = trials
            ec_result = check_escalation_direction(gate2_scenario_trials)
            ec_result["gate2_confirmed"] = True
            ec_result["gate2_per_scenario_n"] = confirm_per_scenario_n
            ec_result["gate2_format_threshold"] = format_threshold
        else:
            ec_result = {"total": 0, "matched": 0, "mismatches": 0, "mismatch_rate": None, "gate2_confirmed": False}
    finally:
        trials_seconds = time.monotonic() - trials_started
        trials_ended_utc = datetime.now(tz=UTC)
        # Before close(): in-process, that frees the model this reading should include.
        ram_after_mb = peak_rss_mb()
        # Must release this model before the manifest loop moves on to the next
        # one, or two llama-server processes (or two in-process models) end up
        # competing for the GPU and memory at once — the exact contention this
        # session already hit once and corrupted two runs (see
        # docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md).
        triage.close()

    all_trials = list(format_trials) + [t for trials in gate2_scenario_trials.values() for t in trials]
    ordered = sorted(t.latency_seconds for t in all_trials)
    latency = {
        "p50_seconds": _percentile(ordered, 0.50) if ordered else None,
        "p95_seconds": _percentile(ordered, 0.95) if ordered else None,
        "mean_seconds": statistics.fmean(ordered) if ordered else None,
        "total_seconds": sum(ordered),
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
        "backend": backend_kind,
        "gpu_layers": gpu_layers if backend_kind == "inprocess" else None,
        "threads": threads,
        "vary_events": vary_events,
        "triage_prompt": triage_prompt,
        "server_args": server_args if backend_kind == "server" else None,
        # For lining the run up against a power meter: every call happens inside
        # this window, after the model load (load_time_seconds) and before release.
        "trial_window": {
            "started_utc": trials_started_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ended_utc": trials_ended_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "wall_seconds": trials_seconds,
            "calls": len(all_trials),
        },
        "prompt_vs_generation": _timings_summary(all_trials),
        "format_reliability": fr_result,
        "escalation_calibration": ec_result,
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
            "ru_maxrss is a cumulative max for the whole test session and isn't "
            "resettable per model; this is exact for the first model in a run (or "
            "when a model is run alone) and otherwise a floor — not a true peak — for "
            "models measured later in the same run. Server backend: RUSAGE_CHILDREN "
            "(llama-server alone). In-process: RUSAGE_SELF, so it also counts the "
            "test process's own Python heap."
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
        # axis["values"] can be non-empty (a real dict entry) while every value in
        # it is None -- e.g. escalation_mismatch_rate when the only model in a run
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


def _production_candidates(results: dict[str, dict], format_threshold: float, escalation_threshold: float) -> dict:
    """Same evidence-backed-case rule as test_compare_models.py's version, scoped
    to the Edge Triage Pipeline's two quality axes (format_parse_rate, gate-2-confirmed
    escalation_mismatch_rate — see eval_lib.check_escalation_direction for why
    this replaced severity_mismatch_rate post-pivot)."""
    passed = []
    rejected = []
    for mid, r in results.items():
        if not r.get("available"):
            continue
        ec = r.get("escalation_calibration", {})
        entry = {
            "id": mid,
            "display_name": r["display_name"],
            "format_parse_rate": r.get("format_reliability", {}).get("rate"),
            "gate2_confirmed": ec.get("gate2_confirmed", False),
            "escalation_mismatch_rate": ec.get("mismatch_rate"),
            "escalation_sample_n": ec.get("total"),
        }
        if (
            ec.get("gate2_confirmed")
            and ec.get("mismatch_rate") is not None
            and ec["mismatch_rate"] <= escalation_threshold
        ):
            passed.append(entry)
        else:
            rejected.append(entry)
    return {
        "format_threshold": format_threshold,
        "escalation_threshold": escalation_threshold,
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
        "=== Tier 3 Edge Triage Pipeline model COMPARISON ===",
        f"artifact: {artifact_path}",
        f"host: {report['host']} ({report['arch']}, {report['platform']})",
        f"decision_grade: {report['decision_grade']}",
        (
            f"backend: {report['seed_config']['model_backend']}, vary_events: {report['seed_config']['vary_events']}, "
            f"triage_prompt: {report['seed_config']['triage_prompt']}, "
            f"server_args: {report['seed_config']['model_server_args'] or '-'}"
        ),
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
        f"gate-2-confirmed escalation_mismatch_rate<={pc['escalation_threshold']:.0%}) ---"
    )
    if pc["passed"]:
        for e in pc["passed"]:
            lines.append(
                f"  PASS   {e['display_name']}: escalation_mismatch={e['escalation_mismatch_rate']:.1%} "
                f"(n={e['escalation_sample_n']}, gate-2 confirmed)"
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
            reason = (
                f"escalation_mismatch={e['escalation_mismatch_rate']:.1%} "
                f"(n={e['escalation_sample_n']}) exceeds bar"
            )
        lines.append(f"  reject {e['display_name']}: {reason}")
    lines.append(
        "Evidence for/against production use on THIS task — not a final pick. Pi 4 "
        "latency/RAM footprint still applies to any PASS entry before it ships."
    )
    return "\n".join(lines)


def test_compare_edge_triage_models(request: pytest.FixtureRequest) -> None:
    manifest = load_models_manifest(
        include_ids=parse_model_ids(request.config.getoption("--include-model-ids")),
        only_ids=parse_model_ids(request.config.getoption("--only-model-ids")),
    )
    available = [e for e in manifest if e.is_available()]
    if not available:
        pytest.skip(
            "No models.toml entries are available (missing binary/model paths). Set "
            "the env vars named in models.toml, or run `make compare-edge-triage-models` on "
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
        escalation_threshold=request.config.getoption("--model-severity-max-mismatch-rate"),
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
            "model_backend": request.config.getoption("--model-backend"),
            "model_gpu_layers": request.config.getoption("--model-gpu-layers"),
            "model_threads": request.config.getoption("--model-threads"),
            "vary_events": request.config.getoption("--vary-events"),
            "triage_prompt": request.config.getoption("--triage-prompt"),
            "model_server_args": request.config.getoption("--model-server-args"),
        },
        "models": results,
        "comparison": comparison,
        "recommendation": recommendation,
        "production_candidates": production_candidates,
    }

    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = EVAL_RESULTS_DIR / f"compare-edge-triage-{platform.node()}-{timestamp}.json"
    artifact_path.write_text(json.dumps(report, indent=2))

    # Printed directly (not via pytest_terminal_summary), same as test_compare_models.py
    # — `make compare-edge-triage-models` passes -s so this isn't captured.
    print(_render_table(report, artifact_path))
