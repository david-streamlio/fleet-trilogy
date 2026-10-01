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
                                          │
                                          ▼
[cloud/hive host]                 Tier 2 cloud function
  localrun / GlobalSynthesisFunction   (talk3_pulsar_speaks_english.function)
  synthesize() ──▶ SubprocessLlmBackend ──▶ llama.cpp-family subprocess
                                          │
                                          ▼
                                     incidents topic
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
- The Tier 2 cloud function runs wherever the demo's "cloud/hive" host is
  (never the Pi — see Broker placement below), consuming `enrichment-cards`
  from every truck's Tier 1 function and publishing `IncidentSynthesis` records
  to the `incidents` topic. `synthesize()` itself
  (`talks/talk3-pulsar-speaks-english/src/talk3_pulsar_speaks_english/synthesizer.py`)
  has no Pulsar dependency either; `pulsar_adapter.py` and `function.py` are
  the same two interchangeable runtime-shell shapes as Tier 1, adapted for
  Tier 2's need to aggregate multiple trucks' cards per corridor before it can
  decide scope/reroute (see those files' docstrings for the batching/windowing
  approach and its known simplifications).

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

Tier 2 is explicitly cloud-side (per `docs/CANON.md` / `docs/ARCHITECTURE.md`),
so this Pi-headroom tradeoff doesn't apply to it — it never runs on a Pi, and
whatever host runs it (laptop, VM, real cloud instance) is assumed to have
plenty of CPU to spare for both brokering (if colocated) and its own
llama.cpp-family subprocess.

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

## Running the Tier 2 cloud function

```bash
./deploy/run_tier2_localrun.sh pulsar://localhost:6650 http://localhost:8080
```

Pointed at a broker on another host (the common case — Tier 2 runs on a
laptop/VM/cloud host, not the Pi):

```bash
./deploy/run_tier2_localrun.sh pulsar://<broker-host>:6650 http://<broker-host>:8080
```

Set `LLM_BINARY_PATH` and `LLM_MODEL_PATH` the same way as Tier 1. The function
consumes `enrichment-cards`, accumulates cards per corridor, and publishes an
`IncidentSynthesis` to `incidents` once a corridor has accumulated enough cards
to synthesize — see `talk3_pulsar_speaks_english.function.GlobalSynthesisFunction`'s
docstring for exactly how that threshold works and why (Pulsar Functions are
per-message, but Tier 2 needs multiple trucks' cards before it can decide
anything).

## Flow B: co-processor + LLM triage with an uplink gate

Flow B is the pivot architecture later slides describe (see
`docs/TALK1-SLIDE-PLAN.md` / `talks/talk1-edge-intelligence/slides`) — a
two-stage pipeline in place of Tier 1's single `EdgeEnrichmentFunction`,
with a severity-based gate on what actually leaves the edge broker:

```
truck-telemetry
      │
      ▼
TelemetryCoprocessorFunction        (talk1_edge_intelligence.coprocessor)
  cheap-math gate: is_probable_slowdown + an eta_slip_min magnitude window
  -- no LLM runtime at this stage
      │
      ▼
triage-payloads
      │
      ▼
LlmTriageFunction                   (talk1_edge_intelligence.triage_function)
  build_card() ──▶ SubprocessLlmBackend/LlmServerBackend ──▶ llama.cpp-family
  subprocess ──▶ apply_escalation(baseline_severity, escalation)
      │
      ├── severity meets uplink_min_severity (default "high")
      │     └──▶ enrichment-cards           (crosses the cellular link)
      │
      └── severity below uplink_min_severity
            └──▶ triage-local-only          (held on the edge broker)
```

- `uplink_min_severity` is a `LlmTriageFunction` user-config value (one of
  `low`/`medium`/`high`, default `"high"`) — see
  `talks/talk1-edge-intelligence/TODO-TRIAGE-UPLINK-GATE.md` for the full
  design and `test_triage_function.py` for the gate's test coverage.
- `process()` is the gated Pulsar Functions entry point; `build_card()` is
  the same card-generation logic, ungated — `tests/model/eval_lib.py`'s
  `run_flow_b_trials` calls `build_card()` directly so eval scoring isn't
  affected by cards the gate would otherwise hold.
- Topic names (`TRIAGE_PAYLOADS_TOPIC`, `LOCAL_TRIAGE_TOPIC`, plus the
  existing `ENRICHMENT_CARDS_TOPIC`) are defined once in
  `fleet_telemetry_model.topics` — nothing in Flow B hardcodes a topic
  string.

### Running Flow B by hand

Two localrun scripts, one per function, mirroring `run_tier1_localrun.sh`'s
conventions:

```bash
./deploy/run_flowb_coprocessor_localrun.sh pulsar://localhost:6650 http://localhost:8080
./deploy/run_flowb_triage_localrun.sh pulsar://localhost:6650 http://localhost:8080
```

`run_flowb_triage_localrun.sh` needs `LLM_BINARY_PATH` / `LLM_MODEL_PATH`
the same way Tier 1 does, plus an optional `UPLINK_MIN_SEVERITY` override.
`run_flowb_coprocessor_localrun.sh` takes optional
`COPROCESSOR_MIN_ETA_SLIP_MIN` / `COPROCESSOR_MAX_ETA_SLIP_MIN` overrides.

### The one-shot demo: `deploy/demo.sh`

`deploy/demo.sh` runs the whole Flow B take in one script — broker check,
both functions, a fixed simulator scenario, and a live side-by-side view of
what got uplinked vs. what stayed local — so the "See It Running" recording
(`talks/talk1-edge-intelligence/TODO-DEMO-RECORDING.md`) can be repeated
identically. It deliberately launches Flow B, not
`run_tier1_localrun.sh`'s `EdgeEnrichmentFunction`: Tier 1 has no
co-processor gate, no severity escalation, and no local-only topic, so it
can't produce the "raised to high and uplinked" + "stays local" pair the
recording needs.

Local dev / rehearsal (broker + functions + simulator all on this machine):

```bash
docker compose -f deploy/docker-compose.yml up -d   # or let demo.sh start it
./deploy/demo.sh
```

Recording take, broker on the Pi (this take's documented placement — see
"Broker placement" above), `fleet-simulator` on the laptop:

```bash
# on the Pi:
./deploy/demo.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>
# demo.sh prints the exact fleet-simulate command to paste on the laptop,
# then waits — Ctrl-C on the Pi tears everything down once the take is done.
```

The scenario is fixed and checked in at `deploy/demo-scenario.env`
(`--fleet-size 1 --incident-corridor I-95N --incident-trucks 1 --seed 4747
--rate 4 --duration 30`) — truck-47 forced onto I-95N with an early,
deterministic incident start. See that file's comments for why this
scenario is expected to produce both a card raised to `"high"` (uplinked)
and at least one card lowered/held (stays local), and for the honest
caveat that the raise itself is a real model decision each run, not
scripted.

Output is labelled, not raw log spam: one-line `[co-processor]`/`[llm]`
startup banners (full logs go to a temp dir printed at startup), then a
live `[uplink]`/`[local]` stream of whatever actually lands on
`enrichment-cards` / `triage-local-only`. Requires `pulsar-admin` and
`pulsar-client` on `PATH` in addition to Tier 1's requirements.

### Multi-pane recording: `deploy/demo-tmux.sh`

Same Flow B pipeline and scenario as `demo.sh` above, but each stage gets its
own tmux pane instead of one labelled-prefix stream — useful when the
recording should show distinct terminals per step rather than one
multiplexed one:

```bash
./deploy/demo-tmux.sh                              # local rehearsal
./deploy/demo-tmux.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>  # on the Pi
```

Panes: `telemetry` (raw `truck-telemetry` events), `coprocessor`
(`TelemetryCoprocessorFunction`'s forwarded payload, consumed straight off
`triage-payloads`), `llm-input` (the exact prompt text handed to the model
for that event, consumed off a dedicated log topic), `outcome`
(`enrichment-cards` vs `triage-local-only`, same pair `demo.sh` tails), and
`simulator`. Neither `coprocessor` nor `llm-input` grep a pane's own log
output: Pulsar routes a function's `logger.info()` calls to a per-function
log file on disk, never to `localrun`'s own stdout, so both panes sidestep
that entirely — `coprocessor` by consuming the real `triage-payloads` output
topic directly, `llm-input` by having `run_flowb_triage_localrun.sh` publish
its log lines to a dedicated topic via `pulsar-admin functions localrun
--log-topic` (set `LOG_TOPIC` to enable it), since the prompt text itself
isn't published to any domain topic the way `coprocessor`'s payload is.
Requires `tmux` on `PATH` in addition to `demo.sh`'s requirements. Detach
(`prefix` + `d`, default `Ctrl-b d`) to tear the whole session down — see
the script's header for why plain `Ctrl-C` doesn't do that here the way it
does in `demo.sh`.

## Raspberry Pi provisioning

See [PI4-RUNBOOK.md](../docs/PI4-RUNBOOK.md) for building mainline llama.cpp on
ARM and pulling the candidate GGUF weights onto a Pi 4.
