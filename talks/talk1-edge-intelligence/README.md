# Talk 1 — Edge Intelligence

Tier 1 edge demo: cheap-math detection (in `fleet-telemetry-model`) plus the 1-bit
LLM's local interpretation step, producing an `EnrichmentCard` for a probable
slowdown. Depends only on `shared/*` packages (`fleet-telemetry-model`,
`llm-inference`). See [../../docs/CANON.md](../../docs/CANON.md).

## Layout

- `processor.py` — `process_event(event, backend) -> EnrichmentCard | None`. The
  entire pipeline core. No Pulsar import, no I/O. Unit-tested directly with a mock
  `LlmBackend`.
- `pulsar_adapter.py` — thin consumer → `process_event` → producer loop. Runs as a
  plain Python process; this is what the integration tests drive end-to-end.
- `function.py` — the same `process_event` wrapped to match the Pulsar Functions
  Python API (`process(self, input, context)`), for `pulsar-admin functions
  localrun` (and later, managed mode). See `deploy/run_tier1_localrun.sh`.

## Running it

As a plain app against a broker:

```bash
uv run python -c "
from llm_inference import SubprocessLlmBackend
from talk1_edge_intelligence.pulsar_adapter import run
run(service_url='pulsar://localhost:6650', backend=SubprocessLlmBackend(mock=True))
"
```

Via `pulsar-admin functions localrun` on the Pi, pointed at a broker anywhere:

```bash
./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650
```

## Detection: possible improvements (not adopted — for this demo, fixed thresholds stay)

`detection.is_probable_slowdown` — three fixed global thresholds (40mph /
0.5 stop-go / 2.0min slip), ANDed together — is what's actually wired into
`processor.py` today, and what we're keeping for this demo. Two alternatives
were explored and are worth a look if this ever needs to be more than a demo:

- **Rolling per-truck z-score** (`fleet_telemetry_model.zscore_detection.
  RollingZScoreDetector`, still in the repo with its own tests, just not
  wired into `processor.py`). Judges each truck against its own recent
  history instead of one global number — fixes the fact that a fixed
  threshold unfairly flags a truck whose *normal* cruising speed is naturally
  slower (e.g. a mountain corridor). Measured head-to-head against the fixed
  thresholds on the simulator's own labeled data
  (`shared/fleet-simulator/tests/test_detection_comparison.py`):

  | detector | precision | recall | F1 |
  |---|---|---|---|
  | fixed threshold | 0.97 | 0.57 | 0.72 |
  | rolling z-score | 0.85 | 0.14 | 0.24 |

  Recall is far worse. Root cause #1 (baseline contamination — a sustained
  incident's own values get absorbed into the "normal" window, so the
  detector goes blind partway through) was fixed with a freeze-on-anomaly
  guard, which helped (F1 0.04 → 0.21) but didn't close the gap. Root cause
  #2 is structural and unfixed: several incident trucks start their incident
  within the first few ticks, before a live per-truck baseline has enough
  history to judge anything against — a cold-start cost fixed thresholds
  don't pay. Lowering `min_history` (10 → 5) only helped marginally (0.21 →
  0.24 F1), confirming cold-start isn't the whole story.
- **Historical reference table** — a precomputed lookup of average speed by
  `[segment_id, day_of_week, hour_of_day]`, built from historical "normal"
  driving data rather than a truck's own live rolling window. This would fix
  *both* problems above at once: no cold start (the table exists before a
  truck ever reports in) and no contamination (a static table can't be
  polluted by a live incident). Not built — there's no real historical
  corpus to seed it from yet, and seeding it from the simulator's own
  synthetic "normal" ticks first would be a real (if modest) chunk of setup
  work, not a one-line change like the two options above. Worth doing if
  detection accuracy ever actually needs to improve; not worth it for this
  demo, where the fixed-threshold numbers above are already good.
