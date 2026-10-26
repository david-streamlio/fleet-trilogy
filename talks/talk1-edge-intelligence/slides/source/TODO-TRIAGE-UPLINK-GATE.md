# TODO: add the LLM uplink gate (triage → cellular)

**Status:** not implemented. The Talk 1 deck presents it as the design (slides 20–21: "What the LLM Decides", "The LLM Decides What Crosses the Cellular Link").

## What the deck says
- The co-processor (`TelemetryCoprocessorFunction`) gates what reaches the LLM: `is_probable_slowdown()` plus the `eta_slip_min` magnitude gate [3.0, 60.0].
- The LLM (`LlmTriageFunction`) gates what goes over cellular. **Only enrichment cards with a final `severity == "high"` are sent to the control center.** Everything else is logged on the truck.

## What the code does today
`talks/talk1-edge-intelligence/src/talk1_edge_intelligence/triage_function.py` → `LlmTriageFunction.process()` returns a card for **every** payload that clears the co-processor. There's no severity check before egress, so medium and low cards also reach `enrichment-cards` (`fleet_telemetry_model/topics.py`).

## Change needed
- In `LlmTriageFunction.process()`, after `card["severity"] = apply_escalation(...)`: if the severity isn't in the uplink set, log the card locally and return `None` (Pulsar Functions drops `None` outputs).
- Make the threshold configurable through user config, e.g. `uplink_min_severity` (default `"high"`), following the same lazy `_configure()` pattern as the other settings.
- Decide where non-uplinked cards go: a local-only topic on the edge broker, or just the function log.
- Tests: extend `talks/talk1-edge-intelligence/tests/test_triage_function.py`:
  - raise → high → emitted
  - lower → medium → `None`
  - hold → low → `None`
  - the config override works
- Talk 2 / eval impact: `tests/model/eval_lib.py` and the Edge Triage Pipeline comparison assume one card per payload. Check they read cards before the gate, or score the gate separately.

## Why
This is the deck's answer to the cloud observability bottleneck: raw readings never leave the truck, and only high-severity, ETA-impacting cards use the cellular link. Until the gate exists, the claim on slide 21 is design, not behavior.
