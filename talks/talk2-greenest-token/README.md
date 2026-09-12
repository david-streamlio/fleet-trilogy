# Talk 2 — The Greenest Token

Stub package. Not yet built — this is a future session.

Planned scope: the efficiency story of 1-bit inference at fleet scale. Contrasts
BitNet b1.58-2B's CPU-only, sub-watt-class inference (per docs/CANON.md) against a
traditional full-precision-model-plus-GPU approach for the same Tier 1 edge workload
— cost, latency, and power, using `fleet-simulator`'s fleet-scale mode to show what
"one BitNet call per flagged event, on a Raspberry Pi 5" looks like at hundreds of
trucks instead of one.

Depends only on `shared/*` packages (`fleet-telemetry-model`, `fleet-simulator`,
`bitnet-inference`). See [../../docs/CANON.md](../../docs/CANON.md).
