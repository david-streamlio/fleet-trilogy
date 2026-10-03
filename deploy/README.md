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
anything). Two optional settings pass through `--user-config`: `LLM_EXTRA_ARGS`
(the model's one-shot flags from `models.toml` — `-no-cnv` for Gemma-3-4B-it,
otherwise llama.cpp wraps the prompt in its chat template) and
`CORRIDOR_THRESHOLD` (cards per corridor before synthesizing; default 2).

**Every `*localrun*.sh` script needs the `functions` dependency group** — the
imports of `pulsar-admin functions localrun`'s Python instance (protobuf 6.x,
grpcio, prometheus_client, ratelimit, the BookKeeper client). It's in
`pyproject.toml`'s default groups, so a plain `uv sync` installs it; before that it
was only ever installed by hand, and `uv sync` silently removed it, failing every
localrun with `No module named 'google'`.

## Talk 3 demo: edge cards → Tier 2 Function → spoken warning

Checked-in input (`deploy/talk3-demo-cards.jsonl`: three trucks' cards on I-95N,
two high-severity, one medium) replayed onto `enrichment-cards`; everything after
that is live on every take — the real `GlobalSynthesisFunction` via localrun
(Gemma-3-4B-it), its plain-code scope/reroute decision, the LLM's wording, and the
speaker voicing it with Piper TTS (setup and licensing:
`talks/talk3-pulsar-speaks-english/README.md`). Replay rather than Talk 1's live
upstream, because the Edge Triage Pipeline's uplinked cards carry no
`corridor`/`event`/`signals` (which Tier 2's `EnrichmentCard` requires) and only
truck-47 has trip context that escalates past the `high` uplink gate.

By hand, one window per script (`deploy/talk3-windows/`), in this order:

```bash
./deploy/talk3-windows/tier2.sh      # Tier 2 Function (log; defaults: Gemma, -no-cnv, threshold 3)
./deploy/talk3-windows/cards.sh      # cards arriving
./deploy/talk3-windows/decision.sh   # "[Decided by code]" + "[Worded by the LLM]"
./deploy/talk3-windows/spoken.sh     # the voice (norman); WAVs + playback.log -> $DEMO_AUDIO_DIR
./deploy/talk3-windows/replay.sh     # publishes the three cards, 3s apart -- start this last
```

### Automated screen recording: `deploy/record-talk3-demo.sh`

```bash
./deploy/record-talk3-demo.sh --teardown   # -> deploy/recordings/talk3-demo-<timestamp>.mp4
```

Opens all five windows (three recorded, on the external display; the Tier 2 log
and the replay on the main display), clears the demo subscriptions' backlog so a
take never replays leftovers, records, and exports H.264 + AAC. Differences from
`record-demo.sh`, each forced by a real take:

- **One `ffmpeg -f avfoundation` capture of the external display**, not one
  `screencapture` per window — `screencapture` writes variable-frame-rate video
  whose duration ends at the last *changed* frame, which put the windows seconds
  apart. The ffmpeg capture is constant 30 fps, so first-frame time = stop time −
  duration (measured within ~40 ms of a timed on-screen change).
- **Only each window's content area is in the video**, composed onto a black
  canvas: Terminal's title bar shows the working directory (the macOS account
  name) and can't be turned off from AppleScript, and gaps between windows showed
  other apps. Crops are read after the windows settle and clamped so one never
  reaches into another's title bar.
- **Sound is added after the fact** — macOS screen capture can't record system
  audio. The speaker stamps `playback.log` the instant each WAV starts playing, and
  the export lays each WAV onto the video at that offset (with 1.5 dB of headroom:
  Piper peaks right at 0 dBFS).
- The mouse pointer is parked on the main display first (avfoundation's
  `-capture_cursor 0` isn't honoured on this macOS).

## Edge Triage Pipeline: co-processor + LLM triage with an uplink gate

The Edge Triage Pipeline is the pivot architecture later slides describe (see
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
  `run_edge_triage_trials` calls `build_card()` directly so eval scoring isn't
  affected by cards the gate would otherwise hold.
- Topic names (`TRIAGE_PAYLOADS_TOPIC`, `LOCAL_TRIAGE_TOPIC`, plus the
  existing `ENRICHMENT_CARDS_TOPIC`) are defined once in
  `fleet_telemetry_model.topics` — nothing in the Edge Triage Pipeline
  hardcodes a topic string.

### Running the Edge Triage Pipeline by hand

Two localrun scripts, one per function, mirroring `run_tier1_localrun.sh`'s
conventions:

```bash
./deploy/run_edge_triage_coprocessor_localrun.sh pulsar://localhost:6650 http://localhost:8080
./deploy/run_edge_triage_llm_localrun.sh pulsar://localhost:6650 http://localhost:8080
```

`run_edge_triage_llm_localrun.sh` needs `LLM_BINARY_PATH` / `LLM_MODEL_PATH`
the same way Tier 1 does, plus an optional `UPLINK_MIN_SEVERITY` override.
`run_edge_triage_coprocessor_localrun.sh` takes optional
`COPROCESSOR_MIN_ETA_SLIP_MIN` / `COPROCESSOR_MAX_ETA_SLIP_MIN` overrides.

### The one-shot demo: `deploy/demo.sh`

`deploy/demo.sh` runs the whole Edge Triage Pipeline take in one script —
broker check, both functions, a fixed simulator scenario, and a live
side-by-side view of what got uplinked vs. what stayed local — so the "See
It Running" recording
(`talks/talk1-edge-intelligence/TODO-DEMO-RECORDING.md`) can be repeated
identically. It deliberately launches the Edge Triage Pipeline, not
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

Same Edge Triage Pipeline and scenario as `demo.sh` above, but each stage
gets its own tmux pane instead of one labelled-prefix stream — useful when
the recording should show distinct terminals per step rather than one
multiplexed one:

```bash
./deploy/demo-tmux.sh                              # local rehearsal
./deploy/demo-tmux.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>  # on the Pi
```

Panes, stacked top-to-bottom in a single equal-height column: `telemetry` (raw
`truck-telemetry` events), `coprocessor` (`TelemetryCoprocessorFunction`'s
forwarded payload, consumed straight off `triage-payloads`), `outcome`
(`enrichment-cards` vs `triage-local-only`, same pair `demo.sh` tails —
this pane also launches `LlmTriageFunction` itself in the background, the
same way `coprocessor`'s pane launches its own function), and `simulator`.
`coprocessor` doesn't grep its own pane's log output: Pulsar routes a
function's `logger.info()` calls to a per-function log file on disk, never
to `localrun`'s own stdout, so it sidesteps that entirely by consuming the
real `triage-payloads` output topic directly instead. Every pane's
`pulsar-client consume` output is filtered down to just each message's
JSON (`content:` field) — the `----- got message -----` framing, periodic
`ConsumerStatsRecorderImpl` stats lines, and `pulsar-client`'s one-time
OpenTelemetry auto-configuration banner (printed on stderr, merged into
the filtered stream with `2>&1`) are all stripped. Each pane
also gets its own background tint (`window-style`, scoped per-pane) so the
stages stay visually distinct in a recording. Requires `tmux` on `PATH` in
addition to `demo.sh`'s requirements. Detach (`prefix` + `d`, default
`Ctrl-b d`) to tear the whole session down — see the script's header for
why plain `Ctrl-C` doesn't do that here the way it does in `demo.sh`.

### Automated screen recording: `deploy/record-demo.sh`

Watch a `demo-tmux.sh` take first (rehearse it, or `tmux attach -t
edge-triage-demo`) before recording the one you'll actually keep — once you're
happy with it, this script automates the capture end to end: it opens a
fresh, sized Terminal.app window, runs `demo-tmux.sh` inside it with a real
tty (so its own `tmux attach` works, unlike running the script from a
non-interactive context), records exactly that window with `screencapture
-v` for the scenario's duration plus an LLM-catch-up buffer, then trims the
lead-in and exports a clean H.264 `.mp4` via `ffmpeg` — satisfying
`talks/talk1-edge-intelligence/TODO-DEMO-RECORDING.md`'s resolution/codec
spec.

```bash
./deploy/record-demo.sh                              # local rehearsal
./deploy/record-demo.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>
```

macOS-only (`osascript` + `screencapture`); needs `ffmpeg` on `PATH`
(`brew install ffmpeg`) for the export step, and one-time Screen Recording +
Automation permission grants for Terminal.app (System Settings > Privacy &
Security) — a blank/black export almost always means one of those two is
missing. Output lands in `deploy/recordings/` (gitignored). See the
script's header for all flags (`--output`, `--window-size`, `--font-size`,
`--wait-extra`, `--fullscreen`, `--teardown`).

## Raspberry Pi provisioning

See [PI4-RUNBOOK.md](../docs/PI4-RUNBOOK.md) for building mainline llama.cpp on
ARM and pulling the candidate GGUF weights onto a Pi 4.
