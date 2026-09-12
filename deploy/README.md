# Deploy

Local dev + demo deployment for the trilogy. Nothing here is required for
`make test` — unit tests never touch Docker, Pulsar, or the LLM runtime (see
`docs/CANON.md` and the root `Makefile`).

## Demo topology

```
[laptop]                          [broker: laptop or Pi — see below]
fleet-simulator  ── publishes ──▶  truck-telemetry topic
                                          │
                                          ▼
[Raspberry Pi 5]                  Tier 1 edge function
  localrun / EdgeEnrichmentFunction   (talk1_edge_intelligence.function)
  process_event() ──▶ SubprocessLlmBackend ──▶ llama.cpp-family subprocess
                                          │
                                          ▼
                                  enrichment-cards topic
```

- `fleet-simulator` always runs on the laptop, never the Pi (see
  `shared/fleet-simulator/README.md`).
- The Tier 1 edge function runs on the Pi via `pulsar-admin functions localrun`
  today (managed mode later). It manages its own llama.cpp-family subprocess through
  `llm-inference`'s `SubprocessLlmBackend` — the Pi runs inference, nothing
  else CPU-heavy.
- `process_event()` itself (`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/processor.py`)
  has no Pulsar dependency; `pulsar_adapter.py` and `function.py` are two
  interchangeable runtime shells around the same function.

## Broker placement: on-Pi vs off-Pi

Where the Pulsar broker itself runs is a **per-talk choice** — document whichever
you're using for a given demo:

- **Broker OFF the Pi (default)** — broker runs on the laptop (`docker-compose up`
  below) or a nearby host. The Pi runs `localrun` only and spends its CPU on
  LLM inference, not brokering. Point `run_tier1_localrun.sh` at the
  laptop's `pulsar://<laptop-ip>:6650`. This is the default because a Pi 5 has
  limited headroom to run both a JVM broker and CPU-only LLM inference well.
- **Broker ON the Pi** — useful for a fully self-contained, no-laptop-broker demo
  (e.g. showing the whole stack running on a single Pi). Run Pulsar standalone
  directly on the Pi and point everything at `pulsar://localhost:6650`. Expect
  less headroom for inference latency; only use this when the talk specifically
  wants to show a single-device deployment.

## Local dev: Pulsar standalone via docker-compose

For laptop-only local development (never the Pi):

```bash
docker compose -f deploy/docker-compose.yml up -d
```

This starts `apachepulsar/pulsar:3.2.2` in standalone mode, exposing the broker
on `6650` and the admin API on `8080`. Tear down with:

```bash
docker compose -f deploy/docker-compose.yml down
```

## Running the Tier 1 edge function

```bash
./deploy/run_tier1_localrun.sh pulsar://localhost:6650 http://localhost:8080
```

On the Pi, pointed at a broker elsewhere:

```bash
./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650 http://<broker-host>:8080
```

Set `LLM_BINARY_PATH` and `LLM_MODEL_PATH` to a built llama.cpp-family binary
and a GGUF model's weights before running for real; leave them unset (or
set `LLM_MOCK=1`) to run the function without an LLM runtime installed.

## Raspberry Pi provisioning

See [PI4-RUNBOOK.md](../docs/PI4-RUNBOOK.md) for building mainline llama.cpp on
ARM and pulling the candidate GGUF weights onto a Pi 4.
