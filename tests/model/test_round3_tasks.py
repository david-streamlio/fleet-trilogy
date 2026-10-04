"""Round 3 eval: one model x task x mode per run (see round3_eval.py for the design).

    uv run --no-sync pytest tests/model/test_round3_tasks.py -m model -s -q \
      --round3-server <llama-server> --round3-gguf <model.gguf> \
      --round3-task full|narrow --round3-mode raw|chat-off|chat-on [--round3-n 2] [--model-threads N]

Cells are interleaved (rep -> profile -> scenario), so drift over a run spreads across every
cell instead of landing on the last ones. Writes eval-results/compare-round3-<host>-<ts>.json
with the configuration, a summary and every call (full completion text included, so reasoning
can be read afterwards). A measurement, not a pass/fail gate: the test only asserts that the
artifact was written.
"""
from __future__ import annotations

import dataclasses
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import LlmServerBackend
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import DEFAULT_THREADS

from tests.model import round3_eval as r
from tests.model.conftest import _EdgeTriageEvalContext
from tests.model.eval_lib import ESCALATION_SCENARIOS
from tests.model.test_edge_triage import _canonical_event

pytestmark = pytest.mark.model

EVAL_RESULTS_DIR = Path(__file__).resolve().parents[2] / "eval-results"


def _event_for(profile: str):
    """The canonical event (truck-47, I-95N, 10 min ETA slip) with one profile's physics."""
    event = _canonical_event()
    if profile == "canonical":
        return event
    p = r.SEVERITY_PROFILES[profile]
    signals = event.signals.model_copy(update={"stop_go_index": p["stop_go_index"]})  # pydantic models
    return event.model_copy(update={"signals": signals, "peak_deceleration_g": p["peak_deceleration_g"], "abs_engaged": p["abs_engaged"]})


def _cells(task: str, n: int) -> list[tuple[str, str]]:
    """(profile, scenario) per call, interleaved. narrow: production's gate-2 shape (the
    canonical event, baseline held at medium, three scenarios) at 3n per scenario; full: every
    physics profile x scenario at n."""
    if task == "narrow":
        return [("canonical", s) for _ in range(3 * n) for s in ESCALATION_SCENARIOS]
    return [(p, s) for _ in range(n) for p in r.SEVERITY_PROFILES for s in ESCALATION_SCENARIOS]


def test_round3_tasks(request: pytest.FixtureRequest) -> None:
    opt = request.config.getoption
    server, gguf = opt("--round3-server"), opt("--round3-gguf")
    if not server or not gguf:
        pytest.skip("round 3 needs --round3-server and --round3-gguf")
    task, mode, n = opt("--round3-task"), opt("--round3-mode"), opt("--round3-n")
    threads = opt("--model-threads") or DEFAULT_THREADS
    temperature, think_budget = opt("--round3-temperature"), opt("--round3-think-budget")
    n_predict = r.JSON_MAX_TOKENS[task] + (think_budget if mode in ("chat-on", "chat-budget") else 0)
    timeout = max(opt("--model-timeout-seconds"), 60 + 0.25 * n_predict)

    backend = LlmServerBackend(binary_path=server, model_path=gguf, threads=threads, startup_timeout_seconds=600)
    coprocessor, context = TelemetryCoprocessorFunction(), _EdgeTriageEvalContext({})
    calls: list[r.Round3Call] = []
    try:
        backend.start()
        payloads: dict[tuple[str, str], tuple[dict, str]] = {}
        for profile, scenario in _cells(task, n):
            key = (profile, scenario)
            if key not in payloads:
                truth = "medium" if profile == "canonical" else r.truth_for(profile)
                payload = r.build_payload(
                    coprocessor, context, _event_for(profile),
                    ESCALATION_SCENARIOS[scenario]["contextual_triggers"],
                    baseline_override="medium" if profile == "canonical" else None,
                )
                assert payload is not None, f"the coprocessor gate filtered profile {profile}"
                assert profile == "canonical" or payload["baseline_severity"] == truth
                payloads[key] = (payload, truth)
            payload, truth = payloads[key]
            calls.append(r.call_once(backend.base_url, task, mode, payload, scenario, profile, truth, n_predict, temperature, timeout))
    finally:
        backend.close()

    summary = r.summarize(calls)
    artifact = {
        "host": platform.node(),
        "arch": platform.machine(),
        "platform": platform.platform(),
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "task": task, "mode": mode, "n_per_cell": n, "gguf": gguf, "server": server, "threads": threads,
            "temperature": temperature, "n_predict": n_predict, "think_budget": think_budget if mode in ("chat-on", "chat-budget") else 0,
            "timeout_seconds": timeout,
        },
        "summary": summary,
        "calls": [dataclasses.asdict(c) for c in calls],
    }
    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    out = EVAL_RESULTS_DIR / f"compare-round3-{platform.node()}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(artifact, indent=1))

    rates = summary["rates"]
    print(f"\n=== round 3: {Path(gguf).name} task={task} mode={mode} n={summary['n']} ===")
    print("  " + "  ".join(f"{k}={v:.0%}" for k, v in rates.items()))
    print(f"  p50 {summary['latency_p50_seconds']:.2f}s  p95 {summary['latency_p95_seconds']:.2f}s  "
          f"tokens {summary['tokens_predicted_mean']:.0f}  think {summary['think_tokens_mean']:.0f}  "
          f"truncated {summary['truncated']}  errors {summary['errors']}")
    print(f"artifact: {out}")
    assert out.exists()
