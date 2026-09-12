# Canon

Locked facts for the fleet-trilogy monorepo. Every talk and every shared package must
conform to this document. If code and canon disagree, canon wins — fix the code.

## Model

- **Microsoft BitNet b1.58-2B**, ~1.2GB quantized, run via **bitnet.cpp**.
- **CPU-only.** No GPU anywhere in the architecture — not on the edge device, not in the
  cloud tier. This is the whole point of a 1-bit model: it's cheap enough to run
  everywhere without one.
- Target edge device: **Raspberry Pi 5**. In demos, a Pi (or a container throttled to
  Pi-like resources) simulates on-truck compute.

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

## Architecture — two tiers, both 1-bit, both CPU

```
        TRUCK 47 (edge / Pi)                      CLOUD (hive)
   ┌───────────────────────────┐          ┌───────────────────────────┐
   │ raw telemetry samples     │          │  many trucks' enrichment  │
   │        │                  │          │  cards arrive on Pulsar   │
   │        v                  │          │        │                  │
   │  cheap math detection     │          │        v                  │
   │  (thresholds, oscillation │          │  TIER 2: 1-bit LLM        │
   │   variance, ETA delta)    │          │  GLOBAL SYNTHESIS +       │
   │        │                  │          │  LANGUAGE                 │
   │        v                  │  Pulsar  │   - one truck vs many?    │
   │  TIER 1: 1-bit LLM        │ ───────> │   - reroute decision      │
   │  LOCAL INTERPRETATION     │  topic   │   - spoken warning text   │
   │  -> "enrichment card"     │          │                           │
   └───────────────────────────┘          └───────────────────────────┘
```

- **Tier 1 (edge)**: a 1-bit LLM runs inline inside a Pulsar Function on the truck/Pi.
  Detection is done by cheap math, **not** the LLM — thresholds, sustained-duration
  checks, oscillation/variance on the speed series, and ETA delta. The LLM's only job is
  **interpretation**: turn the correlated raw signals into a structured, human-readable
  **enrichment card**. The LLM interprets; it never detects.
- **Tier 2 (cloud/hive)**: a second 1-bit LLM runs inline inside a Pulsar Function in the
  cloud tier. It performs **global synthesis and language generation**: aggregate
  enrichment cards from many trucks, decide whether this is one truck's local problem or
  a corridor-wide incident, decide on a reroute, and generate the spoken proactive
  warning text.

Neither tier ever uses a GPU. Neither tier skips the cheap-math detection step and asks
the LLM to "notice" the anomaly from raw numbers — the LLM only ever sees signals that
math has already decided are worth interpreting.

## Language and libraries

- **Python 3.11+** throughout, no exceptions.
- Pulsar via the official `pulsar-client` package and Python Pulsar Functions.
- `bitnet.cpp` is accessed by **subprocess** for now (shell out to the compiled
  `llama-cli`-style binary). An in-process binding (e.g. via `ctypes`/pybind) is a known
  future path — the code should leave that door open (an abstract backend interface) but
  must **not** implement it yet.

## One shared codebase

- There is exactly **one** telemetry schema, **one** enrichment-card schema, **one**
  incident-synthesis schema, and **one** simulator. They live in `shared/` and nowhere
  else.
- Talk packages (`talks/talk1-*`, `talk2-*`, `talk3-*`) depend on `shared/` packages.
  Talk packages **never** depend on each other. If two talks need the same thing, that
  thing belongs in `shared/`, not copied.
- This session scaffolds `shared/` only. Talk packages are stubs (empty package + README)
  until their own build sessions.
