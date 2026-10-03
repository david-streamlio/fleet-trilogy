"""Uplink data budget for the Edge Triage Pipeline: raw telemetry bytes vs. what
actually leaves the truck, plus LLM calls per incident (docs/TALK2-DATA-ENGINEERING-
IMPACT-TRACK.md row 28). Real fleet simulator, real coprocessor gate, real
LlmTriageFunction with Phi-3.5-mini, so escalation decisions and card sizes are real
model output. Ad hoc measurement, not a pytest test:

    uv run python -m tests.model.uplink_budget

Needs llama-server + the Phi-3.5-mini GGUF at the ~/tools paths below (~2 min on an
M4). The simulator's default incident_rate is demo-tuned (a truck would spend about
half its time in incidents), so normal driving and incidents are measured separately
and the per-day figure is left to an explicit incidents-per-day assumption.
"""

import json
import logging
import statistics
import time
from pathlib import Path

from fleet_simulator import FleetSimulator
from fleet_telemetry_model import to_json
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import SEVERITY_LEVELS, LlmTriageFunction

logging.basicConfig(level=logging.WARNING)
PHI = {
    "llm_binary_path": str(
        Path("~/tools/llama.cpp/build/bin/llama-server").expanduser()
    ),
    "llm_model_path": str(
        Path(
            "~/tools/models/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf"
        ).expanduser()
    ),
}


class Ctx:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.log = logging.getLogger("budget")

    def get_logger(self):
        return self.log

    def get_user_config_value(self, key):
        return self.cfg.get(key)

    def publish(self, topic, data):
        pass


def events_of(sim, ticks):
    out = []
    for _ in range(ticks):
        out += sim.tick()
    return out


def gate(events):
    copro, ctx = TelemetryCoprocessorFunction(), Ctx()
    payloads = []
    for e in events:
        p = copro.process(to_json(e), ctx)
        if p is not None:
            payloads.append(p)
    return payloads


# 1. Normal driving: incidents off -> cheap math's false-trigger rate.
normal = events_of(FleetSimulator(fleet_size=20, seed=11, incident_rate=0.0), 2000)
event_bytes = [len(to_json(e).encode()) for e in normal]
false_payloads = gate(normal)
print(
    f"NORMAL: {len(normal)} events ({len(normal) * 5 / 86400:.2f} truck-days), "
    f"event size mean {statistics.mean(event_bytes):.0f} B (min {min(event_bytes)}, max {max(event_bytes)}); "
    f"gate passes (false triggers): {len(false_payloads)}"
)

# 2. Incidents: one forced incident per truck, random onsets off.
cases = {
    "truck-47 (escalate-worthy trip context)": [
        FleetSimulator(
            fleet_size=1,
            seed=s,
            incident_rate=0.0,
            incident_corridor="I-95N",
            incident_trucks=1,
        )
        for s in range(1, 6)
    ],
    "trucks with no trip context": [
        FleetSimulator(
            fleet_size=5,
            seed=21,
            incident_rate=0.0,
            incident_corridor="I-95N",
            incident_trucks=5,
        )
    ],
}
triage = LlmTriageFunction()
tctx = Ctx(PHI)
for name, sims in cases.items():
    incidents = 0
    per_incident_calls, payload_bytes, card_bytes, uplinked_bytes, final = (
        [],
        [],
        [],
        [],
        [],
    )
    t0 = time.monotonic()
    for sim in sims:
        events = events_of(
            sim, 70
        )  # incidents last 24-48 ticks; 70 covers onset jitter + full incident
        by_truck = {}
        for p in gate(events):
            by_truck.setdefault(json.loads(p)["truck_id"], []).append(p)
        incidents += len({e.truck_id for e in events})
        for payloads in by_truck.values():
            per_incident_calls.append(len(payloads))
            for p in payloads:
                payload_bytes.append(len(p.encode()))
                card = triage.build_card(p, tctx)
                if card is None:
                    final.append("error")
                    continue
                c = json.loads(card)
                card_bytes.append(len(card.encode()))
                final.append(c["severity"])
                if SEVERITY_LEVELS.index(c["severity"]) >= SEVERITY_LEVELS.index(
                    "high"
                ):
                    uplinked_bytes.append(len(card.encode()))
    sev = {k: final.count(k) for k in ("low", "medium", "high", "error")}
    print(
        f"\nINCIDENTS, {name}: {incidents} incidents, LLM calls per incident {per_incident_calls} "
        f"(mean {statistics.mean(per_incident_calls):.1f}); payload {statistics.mean(payload_bytes):.0f} B; "
        f"card {statistics.mean(card_bytes):.0f} B; final severity {sev}; "
        f"uplinked {len(uplinked_bytes)} cards = {sum(uplinked_bytes)} B "
        f"({len(uplinked_bytes) / incidents:.1f} cards, {sum(uplinked_bytes) / incidents:.0f} B per incident); "
        f"Mac LLM time {time.monotonic() - t0:.0f}s"
    )
triage._backend.close()
