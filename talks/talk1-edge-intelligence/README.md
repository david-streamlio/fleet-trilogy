# Talk 1 — Edge Intelligence

Tier 1 edge demo: cheap-math detection (in `fleet-telemetry-model`) plus the 1-bit
LLM's local interpretation step, producing an `EnrichmentCard` for a probable
slowdown. Depends only on `shared/*` packages (`fleet-telemetry-model`,
`bitnet-inference`). See [../../docs/CANON.md](../../docs/CANON.md).

## Layout

- `processor.py` — `process_event(event, backend) -> EnrichmentCard | None`. The
  entire pipeline core. No Pulsar import, no I/O. Unit-tested directly with a mock
  `BitNetBackend`.
- `pulsar_adapter.py` — thin consumer → `process_event` → producer loop. Runs as a
  plain Python process; this is what the integration tests drive end-to-end.
- `function.py` — the same `process_event` wrapped to match the Pulsar Functions
  Python API (`process(self, input, context)`), for `pulsar-admin functions
  localrun` (and later, managed mode). See `deploy/run_tier1_localrun.sh`.

## Running it

As a plain app against a broker:

```bash
uv run python -c "
from bitnet_inference import SubprocessBitNetBackend
from talk1_edge_intelligence.pulsar_adapter import run
run(service_url='pulsar://localhost:6650', backend=SubprocessBitNetBackend(mock=True))
"
```

Via `pulsar-admin functions localrun` on the Pi, pointed at a broker anywhere:

```bash
./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650
```
