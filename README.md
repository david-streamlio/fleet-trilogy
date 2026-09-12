# fleet-trilogy

A three-talk conference trilogy about running 1-bit LLMs (Microsoft BitNet) inside
Apache Pulsar for connected-fleet telemetry. One monorepo, one shared core, three talks.

Locked facts live in [docs/CANON.md](docs/CANON.md) — read that first. The two-tier
architecture diagram is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## The story

A delivery fleet's trucks (canonically **Truck 47**, on corridor **I-95N**) stream raw
telemetry. Cheap math on each truck flags a possible **SLOWDOWN** — sustained ~35mph +
a stop/go speed oscillation + a slipping ETA. A **1-bit BitNet model, CPU-only,
Raspberry Pi 5**, running inline in a Pulsar Function on the truck, turns that into a
structured enrichment card. In the cloud, a second 1-bit BitNet model — also CPU-only,
no GPU anywhere in this architecture — aggregates enrichment cards across the fleet,
decides whether this is one truck's problem or a corridor-wide incident, decides on a
reroute, and speaks a proactive warning.

Three talks, one underlying system, told from three angles:

1. **Edge Intelligence** (`talks/talk1-edge-intelligence`) — Tier 1: the edge, the Pi,
   local interpretation.
2. **The Greenest Token** (`talks/talk2-greenest-token`) — the efficiency story of
   1-bit inference at fleet scale.
3. **Pulsar Speaks English** (`talks/talk3-pulsar-speaks-english`) — Tier 2: global
   synthesis, reroutes, and the spoken warning.

**This repo is scaffolded talk-by-talk.** `shared/` is built, and Talk 1's Tier 1
edge pipeline (`process_event` + its Pulsar adapter/Function) is built as the
foundation for the demo deployment — see `deploy/README.md`. Talks 2 and 3 remain
stubs (empty package + README) until their own sessions.

## One shared codebase

There is exactly **one** telemetry schema, **one** enrichment-card schema, **one**
incident schema, and **one** simulator — all in `shared/`. Talk packages depend on
`shared/*` and **never** on each other. If two talks need the same thing, it belongs in
`shared/`, not copied between talks.

```
fleet-trilogy/
  docs/                     canon + architecture — read before writing code
  shared/
    fleet-telemetry-model/  TruckTelemetry / EnrichmentCard / IncidentSynthesis schemas,
                             cheap-math anomaly detection, Pulsar topic names
    fleet-simulator/        the one fleet telemetry generator (incl. Truck 47 scenario)
    llm-inference/          subprocess wrapper around a llama.cpp-family runtime + tier1/tier2 prompts
  talks/
    talk1-edge-intelligence/       Tier 1 edge: process_event() + Pulsar adapter/Function
    talk2-greenest-token/          stub
    talk3-pulsar-speaks-english/   stub
  deploy/                   docker-compose (local Pulsar), localrun script, topology docs
```

## Running it

This is a [uv](https://docs.astral.sh/uv/) workspace.

```bash
cd fleet-trilogy
uv sync                 # installs the whole workspace in one venv
make test               # unit tests only — no Pulsar, no LLM runtime, no Docker
make test-integration   # opt-in: real Pulsar standalone via testcontainers (needs Docker)
```

Each `shared/*` and `talks/*` directory is its own installable package with its own
`pyproject.toml`; the root `pyproject.toml` just wires them together as a workspace.

Nothing in this repo talks to a GPU. Model inference (BitNet b1.58-2B via `bitnet.cpp`)
is CPU-only by design, targeting a Raspberry Pi 5 at the edge and ordinary CPU hosts in
the cloud tier.
