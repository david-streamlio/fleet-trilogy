"""(c) DIRECTIONAL ACCURACY vs _ground_truth — labeled batch from the shared simulator,
full detection -> process_event path, real llama.cpp-family runtime for every
flagged event. Opt-in; see conftest.py for auto-skip when no real model is configured."""

from __future__ import annotations

import pytest
from fleet_simulator.fleet import FleetSimulator

from tests.model.eval_lib import LabeledEvent, run_directional_accuracy

pytestmark = pytest.mark.model


def _labeled_batch(request: pytest.FixtureRequest) -> list[LabeledEvent]:
    fleet = FleetSimulator(
        fleet_size=request.config.getoption("--model-accuracy-fleet-size"),
        seed=request.config.getoption("--model-accuracy-seed"),
        incident_rate=0.0,
        incident_corridor="I-95N",
        incident_trucks=request.config.getoption("--model-accuracy-incident-trucks"),
    )
    ticks = request.config.getoption("--model-accuracy-ticks")
    labeled: list[LabeledEvent] = []
    for _ in range(ticks):
        for event in fleet.tick():
            # event.ground_truth is the simulator's own label for this exact sample; the
            # model/detection code never reads it — only this test does, to score them.
            labeled.append(
                LabeledEvent(event=event, ground_truth_is_slowdown=event.ground_truth == "slowdown_incident")
            )
    return labeled


def test_directional_accuracy_meets_floor(request, llm_backend, tier3_report):
    floor = request.config.getoption("--model-accuracy-floor")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    labeled_events = _labeled_batch(request)

    result, latencies = run_directional_accuracy(llm_backend, labeled_events, timeout_seconds)
    tier3_report.directional_accuracy = result
    tier3_report.add_latencies(latencies)

    assert result["f1"] >= floor, (
        f"directional accuracy F1 {result['f1']:.2f} over {result['total']} labeled events is "
        f"below floor {floor:.2f}; confusion matrix: {result['confusion_matrix']}"
    )
