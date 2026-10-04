"""Round 3 prompt-engineering ablation: one model x variant per run, on the full task's cells
(round3_ablation.py has the variants; round3_eval.py the task and scorer).

    uv run --no-sync pytest tests/model/test_round3_ablation.py -m model -s -q \
      --round3-server <llama-server> --round3-gguf <model.gguf> --round3-variant <variant> [--round3-n 2]

Writes eval-results/compare-round3-ablation-<host>-<ts>.json (configuration, summary, every call),
in the same shape as test_round3_tasks.py's artifacts.
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

from tests.model import round3_ablation as a
from tests.model import round3_eval as r
from tests.model.conftest import _EdgeTriageEvalContext
from tests.model.eval_lib import ESCALATION_SCENARIOS
from tests.model.test_round3_tasks import _cells, _event_for

pytestmark = pytest.mark.model

EVAL_RESULTS_DIR = Path(__file__).resolve().parents[2] / "eval-results"


def test_round3_ablation(request: pytest.FixtureRequest) -> None:
    opt = request.config.getoption
    server, gguf, variant = opt("--round3-server"), opt("--round3-gguf"), opt("--round3-variant")
    if not server or not gguf:
        pytest.skip("the ablation needs --round3-server and --round3-gguf")
    assert variant in a.VARIANTS, f"unknown variant {variant}; one of {list(a.VARIANTS)}"
    n, temperature = opt("--round3-n"), opt("--round3-temperature")
    threads = opt("--model-threads") or DEFAULT_THREADS
    timeout = max(opt("--model-timeout-seconds"), 180)

    backend = LlmServerBackend(binary_path=server, model_path=gguf, threads=threads, startup_timeout_seconds=600)
    coprocessor, context = TelemetryCoprocessorFunction(), _EdgeTriageEvalContext({})
    calls: list[r.Round3Call] = []
    try:
        backend.start()
        payloads: dict[tuple[str, str], dict] = {}
        for profile, scenario in _cells("full", n):
            if (profile, scenario) not in payloads:
                payload = r.build_payload(coprocessor, context, _event_for(profile), ESCALATION_SCENARIOS[scenario]["contextual_triggers"], None)
                assert payload is not None and payload["baseline_severity"] == r.truth_for(profile)
                payloads[(profile, scenario)] = payload
            calls.append(a.call_variant(backend.base_url, variant, payloads[(profile, scenario)], scenario, profile,
                                        r.truth_for(profile), temperature, timeout))
    finally:
        backend.close()

    summary = r.summarize(calls)
    summary["prompt_tokens_mean"] = sum(c.tokens_evaluated for c in calls) / len(calls) if calls else None
    artifact = {
        "host": platform.node(), "arch": platform.machine(), "platform": platform.platform(),
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {"task": "full", "variant": variant, "variant_spec": a.VARIANTS[variant], "n_per_cell": n, "gguf": gguf,
                   "server": server, "threads": threads, "temperature": temperature, "timeout_seconds": timeout},
        "summary": summary,
        "calls": [dataclasses.asdict(c) for c in calls],
    }
    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    out = EVAL_RESULTS_DIR / f"compare-round3-ablation-{platform.node()}-{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(artifact, indent=1))
    rates = summary["rates"]
    print(f"\n=== ablation: {Path(gguf).name} variant={variant} n={summary['n']} ===")
    print("  " + "  ".join(f"{k}={v:.0%}" for k, v in sorted(rates.items())))
    print(f"  p50 {summary['latency_p50_seconds']:.2f}s  prompt {summary['prompt_tokens_mean']:.0f} tok  "
          f"out {summary['tokens_predicted_mean']:.0f} tok  errors {summary['errors']}")
    print(f"artifact: {out}")
    assert out.exists()
