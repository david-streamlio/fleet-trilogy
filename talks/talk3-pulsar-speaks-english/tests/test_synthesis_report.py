from talk3_pulsar_speaks_english.report import format_report, run_fleet_synthesis_report
from talk3_pulsar_speaks_english.synthesizer import SCOPE_CORRIDOR_WIDE


def test_run_fleet_synthesis_report_produces_a_corridor_wide_incident():
    syntheses = run_fleet_synthesis_report(
        fleet_size=6,
        ticks=60,
        seed=7,
        incident_corridor="I-95N",
        incident_trucks=3,
    )

    assert syntheses
    corridor_incident = next((s for s in syntheses if s.corridor == "I-95N"), None)
    assert corridor_incident is not None
    assert corridor_incident.scope == SCOPE_CORRIDOR_WIDE
    assert len(corridor_incident.affected_truck_ids) > 1
    assert corridor_incident.spoken_warning


def test_format_report_handles_empty_and_nonempty_results():
    assert format_report([]) == "No incidents synthesized this run."

    syntheses = run_fleet_synthesis_report(
        fleet_size=6, ticks=60, seed=7, incident_corridor="I-95N", incident_trucks=3
    )
    text = format_report(syntheses)
    assert "I-95N" in text
    assert "spoken warning:" in text
