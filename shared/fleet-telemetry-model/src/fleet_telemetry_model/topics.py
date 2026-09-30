"""Canonical Pulsar topic names. Defined once so every talk agrees on the wire format."""

DEFAULT_TELEMETRY_TOPIC = "persistent://public/default/truck-telemetry"
ENRICHMENT_CARDS_TOPIC = "persistent://public/default/enrichment-cards"
INCIDENTS_TOPIC = "persistent://public/default/incidents"

# Flow B (talk1_edge_intelligence.coprocessor -> .triage_function) intermediate
# topic: TelemetryCoprocessorFunction's output, LlmTriageFunction's input.
TRIAGE_PAYLOADS_TOPIC = "persistent://public/default/triage-payloads"

# Where LlmTriageFunction publishes cards that don't meet uplink_min_severity
# (see triage_function.py) — held on the edge broker rather than reaching
# ENRICHMENT_CARDS_TOPIC, which is what actually crosses the cellular link.
LOCAL_TRIAGE_TOPIC = "persistent://public/default/triage-local-only"
