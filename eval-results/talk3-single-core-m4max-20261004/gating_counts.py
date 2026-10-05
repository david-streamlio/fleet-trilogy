"""Count how many simulated telemetry readings pass Talk 1's two cheap-math gates
(is_probable_slowdown, then the coprocessor's 3-60 min ETA-slip gate) -- i.e. how
many would ever reach an LLM. Same scenario as report.py's defaults: 12 trucks,
60 ticks, an incident forced on I-95N for 3 trucks. Run from the repo root:
    uv run --no-sync python eval-results/talk3-single-core-m4max-20261004/gating_counts.py
"""
from fleet_simulator import FleetSimulator
from talk3_pulsar_speaks_english.report import is_probable_slowdown

for seed in (7, 1, 2, 3, 4):
    sim = FleetSimulator(fleet_size=12, seed=seed, incident_corridor="I-95N", incident_trucks=3)
    readings = slowdown = gated = 0
    for _ in range(60):
        for event in sim.tick():
            readings += 1
            if is_probable_slowdown(event):
                slowdown += 1
                if 3.0 <= event.signals.eta_slip_min <= 60.0:
                    gated += 1
    print(f"seed {seed}: {readings} readings -> {slowdown} pass is_probable_slowdown -> {gated} pass the ETA-slip gate")
