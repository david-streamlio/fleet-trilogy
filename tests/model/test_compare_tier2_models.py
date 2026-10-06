"""Tier 3 model COMPARISON harness for Tier 2 (talk3_pulsar_speaks_english —
see synthesizer.py / prompting.py). Same idea as test_compare_edge_triage_models.py
(run the full eval set for every model in models.toml, on identical seeded
inputs, one combined side-by-side artifact + printed table) but for a task
shape that has no Flow A or Edge Triage Pipeline analog — see tier2_eval_lib.py's module docstring.

No gate-1/gate-2 two-stage promotion here, unlike Flow A and the Edge Triage Pipeline: those exist to fix
a low-parse-rate model starving a downstream axis of samples, but each of
Tier 2's three scenarios already gets a full, adequate sample directly (no
axis here depends on another axis's sample size the way Flow A's and the Edge Triage Pipeline's severity
confirmation depended on format_parse_rate).

Opt-in (@pytest.mark.model), run via `make compare-tier2-models`. Auto-skips
if the manifest has zero available models, same as the other comparison
harnesses.

`--model-backend` picks in-process (the default since 2026-10-05, what
GlobalSynthesisFunction now runs) or llama-server, which every Talk 2
hardware-spectrum run before that date used.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import (
    InProcessLlmBackend,
    LlmBackend,
    LlmGenerationConfig,
    LlmServerBackend,
)

from tests.model.models_manifest import (
    ModelEntry,
    load_models_manifest,
    parse_model_ids,
)
from tests.model.test_compare_edge_triage_models import _server_binary_path
from tests.model.tier2_eval_lib import (
    DEFAULT_THREADS,
    TIER2_PROMPTS,
    TIER2_SCENARIOS,
    _percentile,
    check_speakability,
    check_tier2_format_reliability,
    check_tier2_grounding,
    run_tier2_trials,
)

pytestmark = pytest.mark.model

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_DIR = REPO_ROOT / "eval-results"

AXES: list[tuple[str, tuple[str, ...], str]] = [
    ("nonempty_rate", ("format_reliability", "nonempty_rate"), "higher"),
    ("structured_rate", ("format_reliability", "structured_rate"), "higher"),
    ("speakability_violation_rate", ("speakability", "violation_rate"), "lower"),
    ("max_grounding_violation_rate", ("grounding", "max_violation_rate"), "lower"),
    ("latency_p50_seconds", ("latency", "p50_seconds"), "lower"),
    ("latency_p95_seconds", ("latency", "p95_seconds"), "lower"),
    ("tokens_per_sec_approx", ("tokens_per_sec_approx",), "higher"),
    ("load_time_seconds", ("load_time_seconds",), "lower"),
    ("resident_ram_mb_after", ("resident_ram_mb_after",), "lower"),
]
QUALITY_AXES = {"nonempty_rate", "structured_rate", "speakability_violation_rate", "max_grounding_violation_rate"}


def _decision_grade() -> str:
    if platform.system() == "Linux" and platform.machine().lower() in {"aarch64", "armv7l", "armv6l"}:
        return "full (Pi 4 target)"
    return "quality-only (non-target hardware)"


def _get_path(d: dict, path: tuple[str, ...]):
    for key in path:
        if d is None:
            return None
        d = d.get(key)
    return d


def _peak_rss_mb(backend_kind: str) -> float | None:
    from tests.model.eval_lib import peak_child_rss_mb, peak_self_rss_mb

    # In-process, the model lives in this test process, not in a llama-server child.
    return peak_self_rss_mb() if backend_kind == "inprocess" else peak_child_rss_mb()


def _build_backend(entry: ModelEntry, threads: int, backend_kind: str, gpu_layers: int) -> LlmBackend:
    if backend_kind == "inprocess":
        # GlobalSynthesisFunction's own in-process settings (its default context size).
        return InProcessLlmBackend(entry.model_path, threads=threads, gpu_layers=gpu_layers)
    return LlmServerBackend(
        binary_path=_server_binary_path(entry.binary_path), model_path=entry.model_path, threads=threads
    )


def _start_and_time_in_process(backend: InProcessLlmBackend) -> float | None:
    """Load time for the in-process backend, measured on the backend the trials then
    use. Includes a one-token generation to match llama-server's load time, which
    includes its start-up warm-up pass (see test_compare_edge_triage_models.py's
    _measure_in_process_load_time_seconds)."""
    start = time.monotonic()
    try:
        backend.start()
        backend.generate("Hello", LlmGenerationConfig(max_tokens=1, timeout_seconds=1800.0))
    except Exception:  # noqa: BLE001 - a failed load is "no reading"; the trials then record the error
        return None
    return time.monotonic() - start


def _measure_load_time_seconds(entry: ModelEntry, threads: int) -> float | None:
    backend = LlmServerBackend(
        binary_path=_server_binary_path(entry.binary_path), model_path=entry.model_path, threads=threads
    )
    start = time.monotonic()
    try:
        backend.start()
    except Exception:  # noqa: BLE001 - a failed warmup call is "no reading", not a bug
        return None
    finally:
        backend.close()
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
    format_threshold = request.config.getoption("--model-format-threshold")
    threads = request.config.getoption("--model-threads") or DEFAULT_THREADS
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    per_scenario_n = max(1, n // 3)
    backend_kind = request.config.getoption("--model-backend")
    gpu_layers = request.config.getoption("--model-gpu-layers")

    ram_before_mb = _peak_rss_mb(backend_kind)
    backend = _build_backend(entry, threads, backend_kind, gpu_layers)
    if backend_kind == "inprocess":
        load_time_seconds = _start_and_time_in_process(backend)
    else:
        load_time_seconds = _measure_load_time_seconds(entry, threads)
    try:
        backend.start()
        all_trials = []
        grounding_by_scenario = {}
        for name, scenario in TIER2_SCENARIOS.items():
            trials = run_tier2_trials(
                backend,
                scenario,
                per_scenario_n,
                timeout_seconds=timeout_seconds,
                prompt_template=TIER2_PROMPTS[request.config.getoption("--tier2-prompt")],
            )
            all_trials.extend(trials)
            grounding_by_scenario[name] = check_tier2_grounding(trials, scenario)
    finally:
        # Before close(): in-process, that frees the model this reading should include.
        ram_after_mb = _peak_rss_mb(backend_kind)
        backend.close()

    format_result = check_tier2_format_reliability(all_trials)
    speakability_result = check_speakability(all_trials)
    max_grounding_violation_rate = max((gr["violation_rate"] for gr in grounding_by_scenario.values()), default=0.0)

    ordered = sorted(t.latency_seconds for t in all_trials)
    latency = {
        "p50_seconds": _percentile(ordered, 0.50) if ordered else None,
        "p95_seconds": _percentile(ordered, 0.95) if ordered else None,
        "n": len(ordered),
    }

    tokens_per_sec_samples = [
        len(t.raw_output.split()) / t.latency_seconds for t in all_trials if t.error is None and t.latency_seconds > 0
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
        "backend": backend_kind,
        "gpu_layers": gpu_layers if backend_kind == "inprocess" else None,
        "format_reliability": format_result,
        "speakability": speakability_result,
        "grounding": {"by_scenario": grounding_by_scenario, "max_violation_rate": max_grounding_violation_rate},
        "latency": latency,
        "tokens_per_sec_approx": tokens_per_sec_approx,
        "tokens_per_sec_note": (
            "approximate — whitespace word count / latency over trials with no error, "
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
        "_format_threshold_for_pass": format_threshold,
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
        # it is None -- e.g. every axis here when the only model in a run errors
        # out entirely. A bare truthiness check on the dict misses that and
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


def _production_candidates(results: dict[str, dict], format_threshold: float, grounding_threshold: float) -> dict:
    """A model has an evidence-backed case for Tier 2 production use when it
    produces usable text reliably (nonempty_rate) AND that text doesn't
    violate speakability or grounding beyond grounding_threshold — no
    gate-1/gate-2 split (see module docstring), all three axes are measured
    on the same full sample."""
    passed = []
    rejected = []
    for mid, r in results.items():
        if not r.get("available"):
            continue
        fr = r.get("format_reliability", {})
        sp = r.get("speakability", {})
        gr = r.get("grounding", {})
        entry = {
            "id": mid,
            "display_name": r["display_name"],
            "nonempty_rate": fr.get("nonempty_rate"),
            "speakability_violation_rate": sp.get("violation_rate"),
            "max_grounding_violation_rate": gr.get("max_violation_rate"),
            "sample_n": fr.get("total"),
        }
        ok = (
            fr.get("nonempty_rate") is not None
            and fr["nonempty_rate"] >= format_threshold
            and sp.get("violation_rate") is not None
            and sp["violation_rate"] <= grounding_threshold
            and gr.get("max_violation_rate") is not None
            and gr["max_violation_rate"] <= grounding_threshold
        )
        (passed if ok else rejected).append(entry)
    return {
        "format_threshold": format_threshold,
        "grounding_threshold": grounding_threshold,
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
        "=== Tier 3 Tier-2-synthesis model COMPARISON ===",
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
        f"--- production candidates (nonempty_rate>={pc['format_threshold']:.0%}, "
        f"speakability & grounding violation rate<={pc['grounding_threshold']:.0%}) ---"
    )
    if pc["passed"]:
        for e in pc["passed"]:
            lines.append(
                f"  PASS   {e['display_name']}: nonempty={e['nonempty_rate']:.1%}, "
                f"speakability_viol={e['speakability_violation_rate']:.1%}, "
                f"grounding_viol={e['max_grounding_violation_rate']:.1%} (n={e['sample_n']})"
            )
    else:
        lines.append(
            "  NONE of the tested models met this bar. See rejected reasons below — "
            "that is a real finding, not a reason to lower the bar quietly."
        )
    for e in pc["rejected"]:
        lines.append(
            f"  reject {e['display_name']}: nonempty={e['nonempty_rate']:.1%}, "
            f"speakability_viol={e['speakability_violation_rate']:.1%}, "
            f"grounding_viol={e['max_grounding_violation_rate']:.1%} (n={e['sample_n']})"
        )
    lines.append(
        "Evidence for/against production use on THIS task — not a final pick. Pi 4 "
        "latency/RAM footprint still applies to any PASS entry before it ships."
    )
    return "\n".join(lines)


def test_compare_tier2_models(request: pytest.FixtureRequest) -> None:
    manifest = load_models_manifest(
        include_ids=parse_model_ids(request.config.getoption("--include-model-ids")),
        only_ids=parse_model_ids(request.config.getoption("--only-model-ids")),
    )
    available = [e for e in manifest if e.is_available()]
    if not available:
        pytest.skip(
            "No models.toml entries are available (missing binary/model paths). Set "
            "the env vars named in models.toml, or run `make compare-tier2-models` on "
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
        grounding_threshold=request.config.getoption("--model-grounding-max-violation-rate"),
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
            "tier2_prompt": request.config.getoption("--tier2-prompt"),
        },
        "models": results,
        "comparison": comparison,
        "recommendation": recommendation,
        "production_candidates": production_candidates,
    }

    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = EVAL_RESULTS_DIR / f"compare-tier2-{platform.node()}-{timestamp}.json"
    artifact_path.write_text(json.dumps(report, indent=2))

    print(_render_table(report, artifact_path))
