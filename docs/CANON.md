# Canon

Locked facts for the fleet-trilogy monorepo. Every talk and every shared package must
conform to this document. If code and canon disagree, canon wins — fix the code.

## Model

- **Small, quantized instruct models (Q4_K_M GGUF)**, run via **mainline llama.cpp**
  (subprocess). Not BitNet: a literal 1-bit BitNet b1.58-2B model was the original
  plan and was abandoned after producing garbage output on ARM — see
  `docs/BITNET-POSTMORTEM.md` for the full record. The "1-bit" framing in the talk
  titles now refers to that story, not to the literal quantization of the models
  actually shipped.
- **CPU-only.** No GPU anywhere in the core architecture — not on the edge device, not
  in the cloud tier. Talk 2's efficiency story ("The Greenest Token") separately
  contrasts this CPU-only approach against a full-precision GPU comparison point
  (`docs/TALK2-GPU-BENCHMARK-PLAN.md`) — that's a deliberate side-by-side for the talk,
  not a second production path.
- Target edge device: **Raspberry Pi 4**, 8GB RAM (`docs/PI4-RUNBOOK.md`). In demos, a
  Pi (or a container throttled to Pi-like resources) simulates on-truck compute.
- The specific model per task is decided by real accuracy/latency/RAM gates run on the
  Pi, not fixed here — that pick has changed more than once as the candidate pool and
  gate metrics evolved, and hardcoding a name in this file is exactly how it went stale
  last time (it named BitNet long after BitNet was dropped). Current picks and the full
  decision trail live in `docs/TALK2-OUTLINE.md` ("Final model recommendation") and
  `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`.

## Use case

- Domain: connected delivery fleet telemetry.
- Canonical vehicle: **Truck 47**.
- Canonical corridor: **I-95N** (I-95 north of Atlanta).
- Canonical anomaly: a **SLOWDOWN**, defined as the co-occurrence of three signals:
  1. sustained speed of roughly **35mph** on an interstate (well below flow),
  2. a **stop/go oscillation** in speed (wavy, not a clean drop),
  3. a **slipping ETA window** (ETA getting worse across samples).

  Any one alone is noise. The combination is the incident.
- The stop/go oscillation signal is corroborated by **braking and downshift events**,
  not speed alone. A truck holding a steady low speed (e.g. stuck behind a slow lead
  vehicle) doesn't brake or downshift; a truck in real stop-and-go traffic does. Raw
  telemetry carries per-sample `brake_events` / `downshift_events` counts, and cheap-math
  detection treats a burst of these as an alternate, more direct confirmation of
  stop-and-go — it doesn't require the wavy speed amplitude to also cross its threshold.

  Any one of these alone is noise. The combination is the incident.

## Architecture — two tiers, both small quantized models, both CPU

```
        TRUCK 47 (edge / Pi 4)                     CLOUD (hive)
   ┌───────────────────────────┐          ┌───────────────────────────┐
   │ raw telemetry samples     │          │  many trucks' enrichment  │
   │        │                  │          │  cards arrive on Pulsar   │
   │        v                  │          │        │                  │
   │  cheap math detection     │          │        v                  │
   │  (thresholds, oscillation │          │  TIER 2: small quantized  │
   │   variance, ETA delta)    │          │  LLM — GLOBAL SYNTHESIS + │
   │        │                  │          │  LANGUAGE                 │
   │        v                  │  Pulsar  │   - one truck vs many?    │
   │  TIER 1: small quantized  │ ───────> │   - reroute decision      │
   │  LLM — LOCAL INTERPRETATION│ topic   │   - spoken warning text   │
   │  -> "enrichment card"     │          │                           │
   └───────────────────────────┘          └───────────────────────────┘
```

- **Tier 1 (edge)**: a small quantized instruct LLM runs inline inside a Pulsar
  Function on the truck/Pi. Detection is done by cheap math, **not** the LLM —
  thresholds, sustained-duration checks, oscillation/variance on the speed series, and
  ETA delta. The LLM's only job is **interpretation**: turn the correlated raw signals
  into a structured, human-readable **enrichment card**. The LLM interprets; it never
  detects.
- **Tier 2 (cloud/hive)**: a second small quantized instruct LLM runs inline inside a
  Pulsar Function in the cloud tier. It performs **global synthesis and language
  generation**: aggregate enrichment cards from many trucks, decide whether this is one
  truck's local problem or a corridor-wide incident, decide on a reroute, and generate
  the spoken proactive warning text.

Neither tier ever uses a GPU. Neither tier skips the cheap-math detection step and asks
the LLM to "notice" the anomaly from raw numbers — the LLM only ever sees signals that
math has already decided are worth interpreting.

## Language and libraries

- **Python 3.11+** throughout, no exceptions.
- Pulsar via the official `pulsar-client` package and Python Pulsar Functions.
- Mainline **llama.cpp** is accessed through `shared/llm-inference` — a generic
  wrapper package, originally named `shared/bitnet-inference` before the BitNet-to-
  llama.cpp pivot (`docs/BITNET-POSTMORTEM.md`) — behind the abstract `LlmBackend`
  interface, two ways:
  - **by subprocess** (`SubprocessLlmBackend`): shell out to the compiled
    `llama-completion`-style binary, one process per call. The original path, and
    still what the eval harness and Talk 1/2 use.
  - **in-process** (`InProcessLlmBackend`, decided 2026-10-04): llama.cpp inside the
    Python process via `llama-cpp-python` (MIT, the root `inprocess` dependency
    group). A Pulsar Function holding it loads the model once and keeps it, and each
    call reuses the prompt prefix the last one read. This is how Talk 3's
    `GlobalSynthesisFunction` runs on stage (`llm_backend=inprocess`), because the
    accepted abstract promises an LLM *embedded* in the stream processing function.
    Measured against the subprocess path in
    `eval-results/talk3-single-core-m4max-20261004/`.

## One shared codebase

- There is exactly **one** telemetry schema, **one** enrichment-card schema, **one**
  incident-synthesis schema, and **one** simulator. They live in `shared/` and nowhere
  else.
- Talk packages (`talks/talk1-*`, `talk2-*`, `talk3-*`) depend on `shared/` packages.
  Talk packages **never** depend on each other. If two talks need the same thing, that
  thing belongs in `shared/`, not copied.
- `shared/` and all three talk packages (`talk1-edge-intelligence`,
  `talk2-greenest-token`, `talk3-pulsar-speaks-english`) are built, not stubs — see
  each package's own README and `deploy/README.md` for the runnable end-to-end local
  demo. What's still open: a slide deck (not started yet) and the handful of items in
  `docs/TALK2-OUTLINE.md`'s "Not yet decided" section; talk1 and talk3 don't have their
  own outline docs yet.
