"""The whole-card enrichment comparison (test_compare_models.py's measurements and
sample sizes) against a model that an OpenAI-compatible server already hosts, e.g.
the Mac Studio's vllm-mlx engine behind LiteLLM, through HttpLlmBackend.

Asks the question the September runs left open: is the whole-card prompt's poor
severity accuracy a small-model problem, or would a much larger model get it right?
Same prompt (structured.ENRICHMENT_CARD_PROMPT, thresholds stated), same events
(format: truck-47's slowdown; grounding: the 18-minute known-value event; severity:
3.0 / 10.0 / 20.0 minutes), same defaults (temperature 0.7, 256 tokens, no grammar),
same gates (30 format trials; 10 severity trials per tier, then 30 per tier when the
format rate reaches 80%).

Three differences from those runs: the server applies the model's chat template (they
sent raw completions); the runtime is the server's (MLX on the Studio, llama.cpp
then); and every prompt starts with a unique "Request <hex>" line (see
_UniquePrefixBackend). Calls run CONCURRENCY at a time, so latencies are not
comparable either.

    LLM_HTTP_BASE_URL=http://<host>:4000/v1 LLM_HTTP_MODEL=reasoner \\
    LLM_HTTP_MODEL_LABEL="Llama-3.3-70B-Instruct (MLX 4-bit)" \\
    LLM_HTTP_API_KEY_FILE=~/.config/fleet-trilogy/studio-llm.key \\
    uv run python -m tests.model.enrichment_http_check

The key is read from the file and sent as a Bearer token; it is never printed or
written to the results.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from llm_inference import HttpLlmBackend, LlmBackend, LlmGenerationConfig

from tests.model.eval_lib import (
    _percentile,
    check_grounding,
    check_severity_calibration,
    format_reliability,
    run_enrichment_trials,
)
from tests.model.test_format_reliability import _truck_47_slowdown_event
from tests.model.test_grounding import _known_value_event
from tests.model.test_severity_calibration import _event as _severity_tier_event

RUNS = 30  # --model-eval-runs default
CONFIRM_MULTIPLIER = 3.0  # --model-confirm-multiplier default
FORMAT_THRESHOLD = 0.8  # --model-format-threshold default
TIMEOUT_SECONDS = 300.0
CONCURRENCY = 4
REPO_ROOT = Path(__file__).resolve().parents[2]


class _UniquePrefixBackend(LlmBackend):
    """Starts every prompt with a unique line, so a server's prefix cache can't match an
    earlier prompt. The Studio's vllm-mlx cache (2026-10-07) spliced a token from a cached
    prompt into new prompts that shared its opening: after the 6.0-minute format trials,
    a 3.0-minute slip reached the model as 63.0 and a 20.0-minute one as 620.0, and every
    3.0-minute severity call came back wrong. With a unique first line, 16 of 16 were
    right (eval-results/compare-enrichment-http-reasoner-20261007T164924Z.json is that
    invalid first run)."""

    def __init__(self, inner: LlmBackend) -> None:
        self._inner = inner

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        return self._inner.generate(f"Request {uuid.uuid4().hex}\n\n{prompt}", config)


def _trials(backend, event, n):
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        return list(pool.map(lambda _: run_enrichment_trials(backend, event, 1, TIMEOUT_SECONDS)[0], range(n)))


def _severity(backend, per_tier_n):
    pairs = [(e, _trials(backend, e, per_tier_n)) for e in (_severity_tier_event(m) for m in (3.0, 10.0, 20.0))]
    return pairs, check_severity_calibration(pairs)


def main() -> int:
    base_url = os.environ["LLM_HTTP_BASE_URL"]
    model = os.environ["LLM_HTTP_MODEL"]
    label = os.environ.get("LLM_HTTP_MODEL_LABEL", model)
    key = Path(os.path.expanduser(os.environ["LLM_HTTP_API_KEY_FILE"])).read_text().strip()
    backend = _UniquePrefixBackend(HttpLlmBackend(base_url=base_url, model=model, api_key=key, mock=False))

    print(f"[http-check] {label}: warm-up call (loads the model if the engine evicted it)...", flush=True)
    backend.generate("Reply with the single word: ready", LlmGenerationConfig(max_tokens=8, timeout_seconds=900.0))

    fr_trials = _trials(backend, _truck_47_slowdown_event(), RUNS)
    fr = format_reliability(fr_trials)
    print(f"[http-check] format: {fr['parsed']}/{fr['total']} parsed", flush=True)

    gr_event = _known_value_event()
    gr = check_grounding(gr_event, _trials(backend, gr_event, RUNS))
    print(f"[http-check] grounding: {json.dumps({k: v for k, v in gr.items() if k != 'sample_violations'})}", flush=True)

    per_tier_n = max(1, RUNS // 3)
    gate1_pairs, sc = _severity(backend, per_tier_n)
    sc["gate2_confirmed"] = False
    print(f"[http-check] severity gate 1: {sc['mismatches']}/{sc['total']} wrong", flush=True)
    all_pairs = list(gate1_pairs)
    if fr["rate"] >= FORMAT_THRESHOLD:
        confirm_n = max(per_tier_n, round(per_tier_n * CONFIRM_MULTIPLIER))
        gate2_pairs, sc = _severity(backend, confirm_n)
        sc.update(gate2_confirmed=True, gate2_per_tier_n=confirm_n, gate2_format_threshold=FORMAT_THRESHOLD)
        print(f"[http-check] severity gate 2: {sc['mismatches']}/{sc['total']} wrong", flush=True)
        all_pairs += gate2_pairs

    latencies = sorted([t.latency_seconds for t in fr_trials] + [t.latency_seconds for _, ts in all_pairs for t in ts])
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    result = {
        "timestamp": stamp,
        "harness": "tests/model/enrichment_http_check.py",
        "git_commit": commit,
        "server": "OpenAI-compatible chat completions (the model's chat template applied by the server)",
        "model_route": model,
        "model": label,
        "settings": {"temperature": 0.7, "max_tokens": 256, "grammar": None, "concurrency": CONCURRENCY,
                     "runs": RUNS, "confirm_multiplier": CONFIRM_MULTIPLIER, "format_threshold": FORMAT_THRESHOLD,
                     "unique_prefix": "every prompt starts with 'Request <uuid4 hex>' to defeat the server's prefix cache"},
        "format_reliability": fr,
        "grounding": gr,
        "severity_calibration": sc,
        "latency_note": f"{CONCURRENCY} concurrent calls; not comparable to the sequential September runs",
        "latency": {"p50_seconds": _percentile(latencies, 0.5), "p95_seconds": _percentile(latencies, 0.95), "n": len(latencies)},
    }
    out = REPO_ROOT / "eval-results" / f"compare-enrichment-http-{model}-{stamp}.json"
    out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"[http-check] wrote {out.relative_to(REPO_ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
