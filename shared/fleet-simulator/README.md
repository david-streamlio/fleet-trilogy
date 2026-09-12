# fleet-simulator

The one fleet telemetry simulator. Publishes `TelemetryEvent` JSON to Pulsar.
Runs on a laptop — not the Pi. Single-truck mode and fleet-scale mode are the
exact same code path (`FleetSimulator`/`TruckState`); fleet size and correlated
incidents are just constructor arguments.

## Example commands

**1. Dry run** — print sample events to stdout, no Pulsar connection required:

```bash
uv run fleet-simulate --dry-run --seed 7
```

**2. Single-truck mode** — Truck 47 on I-95N, the canonical CANON.md scenario,
streaming to a local broker:

```bash
uv run fleet-simulate --service-url pulsar://localhost:6650
```

**3. Steady 50 events/sec** across the whole fleet, run until stopped (Ctrl-C):

```bash
uv run fleet-simulate --fleet-size 10 --rate 50
```

**4. Fixed 60-second measurement window**, printing a throughput summary on exit:

```bash
uv run fleet-simulate --fleet-size 10 --rate 50 --duration 60
```

**5. Fleet-scale correlated incident** — 50 trucks, 32 of them pinned to I-95N
with an overlapping-window slowdown, to drive Talk 3's aggregation:

```bash
uv run fleet-simulate --fleet-size 50 --incident-corridor I-95N --incident-trucks 32
```

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--service-url` | `pulsar://localhost:6650` | Pulsar broker URL |
| `--topic` | `persistent://public/default/truck-telemetry` | topic to publish to |
| `--token` | none | Pulsar auth token, if required |
| `--fleet-size` | `1` | number of trucks; `1` is single-truck Truck 47 mode |
| `--incident-rate` | `0.03` | per-tick probability a truck starts a background incident |
| `--incident-corridor` | none | corridor for a forced, correlated incident |
| `--incident-trucks` | `0` | number of trucks pinned to `--incident-corridor` |
| `--rate` | realistic pacing | target events/sec across the whole fleet |
| `--duration` | none | stop after N seconds |
| `--total` | none | stop after exactly N events |
| `--seed` | none | deterministic event sequences |
| `--dry-run` | off | print events to stdout, skip Pulsar entirely |

On exit (including Ctrl-C/SIGTERM), the simulator flushes the producer and
prints a one-line JSON summary: events published, achieved rate, elapsed time,
percent slowdown emitted, and how many trucks ended in an incident.
