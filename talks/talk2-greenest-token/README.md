# Talk 2 — The Greenest Token

The efficiency story of small-model inference at fleet scale. Contrasts the
CPU-only small-model approach this project actually ships — a quantized
instruct model (Qwen2.5-1.5B/0.5B, Q4_K_M GGUF) run via mainline llama.cpp, per
[docs/BITNET-POSTMORTEM.md](../../docs/BITNET-POSTMORTEM.md) and
[docs/CANON.md](../../docs/CANON.md) — against a traditional
full-precision-model-plus-GPU approach for the same Tier 1 edge interpretation
workload, in cost, latency, and power, using `fleet-simulator`'s fleet-scale
mode to show what "one LLM call per flagged event" looks like at hundreds of
trucks instead of one.

Depends only on `shared/*` packages (`fleet-telemetry-model`, `fleet-simulator`,
`llm-inference`). See [../../docs/CANON.md](../../docs/CANON.md).

## The key point

Per CANON.md, cheap math runs on every truck every tick; the LLM is only
invoked when cheap math flags a probable slowdown (exactly like Tier 1's
`process_event` in `talk1-edge-intelligence`). So the number of LLM calls a
fleet makes scales with the **flagged-event rate**, not with fleet size
directly. A fleet of 200 trucks at a low incident rate can make *fewer* LLM
calls than a handful of trucks all in trouble at once — the cheap-math gate is
what keeps the LLM off the hot path for the other 97%+ of ticks.

## Layout

- `efficiency.py` — the pure core, no Pulsar import, no I/O:
  - `count_flagged_events(events) -> int` — how many events cheap math would
    hand to the LLM (one call per flagged event).
  - `ApproachProfile` / `SMALL_MODEL_CPU` / `FULL_PRECISION_GPU` — named,
    labeled per-call latency/power/cost assumptions for the two approaches.
    **These are illustrative assumptions for telling this story, not
    benchmarked numbers** — see the comments next to each constant. Real,
    benchmarked numbers live in `tests/model/`'s opt-in evals, never here.
  - `compare_approaches(flagged_event_count, approaches) -> dict[str, ApproachResult]`
    — scores every approach against the same call count.
  - `savings_factor(baseline, contender) -> dict[str, float]` — how many times
    cheaper/greener one approach is versus another, per metric.
- `report.py` — the I/O shell: runs `FleetSimulator` for some fleet size and
  tick count, counts flagged events, calls `compare_approaches`, and prints a
  report. This is the only module that touches `FleetSimulator` or stdout.

## Running it

```bash
uv run greenest-token-report --fleet-size 200 --ticks 200
```

or in Python:

```python
from talk2_greenest_token.report import run_fleet_efficiency_report, format_report

results = run_fleet_efficiency_report(fleet_size=200, ticks=200, seed=7)
print(format_report(results, fleet_size=200, ticks=200))
```
