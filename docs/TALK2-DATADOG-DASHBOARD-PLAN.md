# Plan: watching the energy of an AI workload in Datadog (Talk 2 demo)

**Status:** plan only, 2026-10-04. Nothing has been sent to Datadog. Requested by the user together with the paper's new section VI ("Observing the Energy of AI Workloads", `talks/talk2-greenest-token/paper/main.tex`).

**Goal:** make the paper's §VI concrete on stage. Show per-decision energy, completion, thermal state and invocation rate for the edge triage pipeline on a Datadog dashboard, ideally live, and change one setting to show the effect: thinking on/off, or the cheap-math gate on/off.

**Why it fits the talk:** it closes the "do this, not that" section with "here's how you'd watch for it". Every row of the paper's Table VI (signal → the failure it would have caught) becomes a dashboard widget.

[verify] marks a Datadog behaviour to confirm against current docs before building.

## Two modes

### A. Live on the MacBook (recommended for the talk)
- **What runs:** the fleet simulator → the cheap-math gate → `llama-server` (Metal) with the triage prompt, all on the laptop; `powermetrics` sampling power and thermal state every 500 ms.
- **What a sidecar does:**
  1. tails the powermetrics output and parses samples incrementally (the parser in `deploy/aws-phone-proxies/scripts/summarize.py`);
  2. attributes energy to decisions with the paper's method: integrate power over a short window (10-30 s), subtract the idle baseline measured at start-up, divide by the decisions in that window;
  3. emits metrics (below).
- **The toggles on stage:**
  - **thinking on:** energy per decision jumps ~4-7×, accuracy doesn't move;
  - **gate off:** the decision rate jumps from a few per incident to one per event;
  - **sustained load:** thermal pressure climbs and power drops as the laptop throttles.

### B. Replay of the study's recorded runs (history and charts)
- Replay recorded runs (power traces, `windows.log`, eval artifacts) as metrics with *current* timestamps, time-compressed and tagged `run_id`. That shows e.g. the round-3 thinking sessions, or the M4 Max cool vs throttled runs, as dashboard history.
- The metrics intake doesn't accept points far in the past, so history has to be replayed, not backfilled [verify the accepted age of past timestamps].
- A useful fallback if conference Wi-Fi fails during the live demo: replay a recorded live run.

## Metrics (proposed)

| Metric | Type | What |
|---|---|---|
| `edge_ai.decision.energy_j` | distribution | energy above idle per decision (window-attributed) |
| `edge_ai.decision.latency_s` | distribution | time per decision |
| `edge_ai.decision.tokens` | distribution | generated tokens; tag `kind:reasoning` / `kind:answer` |
| `edge_ai.decisions` | count | decisions; tag `outcome:completed` / `outcome:truncated` |
| `edge_ai.events` | count | telemetry events seen (with `edge_ai.decisions`, gives the gate's pass rate) |
| `edge_ai.power.package_w` | gauge | CPU+GPU+ANE power from powermetrics |
| `edge_ai.thermal.pressure` | gauge | 0 = Nominal … 4 = Critical |
| `edge_ai.tokens_per_joule` | gauge | per window |

**Tags:** `model`, `quant`, `device`, `prompt_mode` (raw / chat-off / chat-on / chat-budget), `gate` (on / off), `task`, `run_id`.

## Dashboard (one screen, mirrors Table VI)
1. **Energy per decision** by `prompt_mode`: timeseries, p50 and p95.
2. **Decisions per minute vs events per minute:** the gate's effect.
3. **Package power with thermal pressure overlaid.**
4. **Completion rate:** truncated vs completed.
5. **Tokens per joule** by model / quant.
6. **LLM energy per truck-day,** a query value: decisions per day × mean energy per decision (the paper's Fig. 4 as a number).

Build it as dashboard JSON in the repo (`deploy/datadog/edge-ai-energy-dashboard.json`), created through the dashboards API or imported by hand.

## Optional: LLM Observability
Instrument each LLM call with the Datadog LLM Observability SDK, so every decision is a trace with tokens and latency, and attach the window-attributed energy to the span [verify how to attach a custom numeric metric to LLM Observability spans]. Prompts would contain only simulator data. Off by default: metrics alone carry the demo.

## Pieces to build (~half a day to a day)
1. **Streaming powermetrics reader:** incremental version of `load_powermetrics`.
2. **Window energy attributor:** idle baseline at start-up, window integration, division by decisions.
3. **Emitter:** DogStatsD via a local Datadog Agent, or the HTTP metrics API directly (no Agent install).
4. **Demo driver:** simulator + gate + llama-server, with the three toggles as flags or keys.
5. **Dashboard JSON.**
6. **Replay script** (mode B).

## Decisions needed from the user
1. **Datadog org and site** (e.g. US1 `datadoghq.com` or EU).
2. **Credentials:** an API key, plus an application key if the dashboard is created through the API. They go in environment variables only, never in the repo or a commit.
3. **Emitter:** a local Datadog Agent on the MacBook (DogStatsD), or the HTTP API without installing the Agent?
4. **Live demo, replay, or both?**
5. **LLM Observability spans:** yes or no?

## Constraints
- **Timing:** don't build or run any of this on the MacBook while benchmarks are running (until ~01:45 UTC, 2026-10-05).
- **Data:** send aggregate metrics only; no prompts or outputs unless LLM Observability is switched on, and then only simulator data.
- **Live-demo risk:** keep a recorded replay as the fallback.
