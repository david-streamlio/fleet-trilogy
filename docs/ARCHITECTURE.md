# Architecture

See [CANON.md](CANON.md) for the locked facts this diagram must stay consistent with.

## Data flow

```
 ┌────────────────────────────────────────────────────────────────────┐
 │ Truck 47 — I-95N — Raspberry Pi 5 (edge compute, CPU-only)          │
 │                                                                      │
 │  fleet-simulator                                                    │
 │       │ TruckTelemetry samples (speed, lat/lon, eta, ...)           │
 │       v                                                              │
 │  Pulsar topic: telemetry.raw.<truck_id>                             │
 │       │                                                              │
 │       v                                                              │
 │  Pulsar Function: tier1-edge-interpreter                            │
 │       ├─ cheap-math detection (shared/fleet-telemetry-model)        │
 │       │     - sustained low speed?                                  │
 │       │     - speed oscillation (stop/go)?                          │
 │       │     - ETA slip trend?                                       │
 │       │                                                              │
 │       └─ if all three correlate -> ask the 1-bit LLM to INTERPRET   │
 │            (llm-inference, subprocess call to a llama.cpp-family runtime)│
 │                │                                                     │
 │                v                                                     │
 │          EnrichmentCard  (structured, human-readable)               │
 └───────────────┬────────────────────────────────────────────────────┘
                  │ Pulsar topic: telemetry.enrichment-cards
                  v
 ┌────────────────────────────────────────────────────────────────────┐
 │ Cloud / hive (CPU-only — no GPU here either)                        │
 │                                                                      │
 │  Pulsar Function: tier2-global-synthesizer                          │
 │       ├─ aggregates enrichment cards across trucks + corridor       │
 │       ├─ decides: isolated truck issue vs. corridor-wide incident   │
 │       ├─ decides: reroute recommendation                            │
 │       └─ 1-bit LLM generates the spoken proactive warning           │
 │                │                                                     │
 │                v                                                     │
 │          IncidentSynthesis (reroute + spoken warning text)          │
 └───────────────┬────────────────────────────────────────────────────┘
                  │ Pulsar topic: telemetry.incidents
                  v
            downstream consumers (talk demos, dashboards, TTS, etc.)
```

## Package map

| Package | Location | Owns |
|---|---|---|
| `fleet-telemetry-model` | `shared/fleet-telemetry-model` | `TruckTelemetry`, `EnrichmentCard`, `IncidentSynthesis` schemas; cheap-math anomaly detection; Pulsar topic name constants |
| `fleet-simulator` | `shared/fleet-simulator` | The one fleet telemetry generator, including the Truck 47 / I-95N slowdown scenario |
| `llm-inference` | `shared/llm-inference` | Subprocess wrapper around a llama.cpp-family CLI runtime; tier1/tier2 prompt templates; abstract backend interface (in-process binding reserved for later) |
| `talk1-edge-intelligence` | `talks/talk1-edge-intelligence` | Stub — Tier 1 demo, future session |
| `talk2-greenest-token` | `talks/talk2-greenest-token` | Stub — future session |
| `talk3-pulsar-speaks-english` | `talks/talk3-pulsar-speaks-english` | Stub — Tier 2 / full-loop demo, future session |

Talk packages depend on `shared/*` only, never on each other.
