from talk1_edge_intelligence.trip_context import get_trip_context


def test_known_truck_returns_real_context():
    context = get_trip_context("truck-47")
    assert context is not None
    assert context.weather_condition
    assert context.cargo_type
    assert context.dispatch_status


def test_unknown_truck_returns_none_not_a_fabricated_default():
    assert get_trip_context("truck-does-not-exist") is None
