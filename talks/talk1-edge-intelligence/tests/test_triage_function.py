import json
import logging

from fleet_telemetry_model import LOCAL_TRIAGE_TOPIC
from talk1_edge_intelligence.triage_function import (
    RECOMMENDED_ACTIONS,
    LlmTriageFunction,
    _gbnf_quoted_literal,
    apply_escalation,
    build_grammar,
    recommended_action_for,
)


class _FakeContext:
    """Minimal stand-in for a Pulsar Functions Context: get_logger(),
    get_user_config_value(key), and publish(topic, data) -- the methods
    LlmTriageFunction calls.
    """

    def __init__(self, user_config: dict | None = None) -> None:
        self._user_config = user_config or {}
        self._logger = logging.getLogger("test")
        self.published: list[tuple[str, bytes]] = []

    def get_logger(self) -> logging.Logger:
        return self._logger

    def get_user_config_value(self, key: str) -> str | None:
        return self._user_config.get(key)

    def publish(self, topic: str, data: bytes) -> None:
        self.published.append((topic, data))


def _payload(*, truck_id: str = "truck-03", eta_slip_min: float = 13.8, baseline_severity: str = "medium") -> str:
    return json.dumps(
        {
            "truck_id": truck_id,
            "corridor": "I-95N (Near Exit 4)",
            "signals": ["sustained_low_speed", "stop_go_index"],
            "metrics": {
                "rolling_avg_speed": "12 mph",
                "eta_slip_min": eta_slip_min,
                "traffic_pattern": "high velocity variance (stop-and-go spikes)",
                "peak_deceleration_g": 0.30,
                "abs_engaged": False,
            },
            "baseline_severity": baseline_severity,
            "contextual_triggers": {
                "local_time": "17:15 (Friday Rush Hour)",
                "weather_condition": "Heavy rain, wet asphalt",
                "cargo_type": "Liquids / Chemical Tanker",
                "dispatch_status": "Running 20 minutes behind schedule",
            },
        }
    )


def test_apply_escalation_moves_one_level_and_clamps_at_the_ends():
    assert apply_escalation("medium", "raise") == "high"
    assert apply_escalation("medium", "lower") == "low"
    assert apply_escalation("medium", "hold") == "medium"
    # Clamped, not wrapped, at either end.
    assert apply_escalation("high", "raise") == "high"
    assert apply_escalation("low", "lower") == "low"


def test_recommended_action_for_covers_every_escalation_value_and_falls_back_to_hold():
    assert set(RECOMMENDED_ACTIONS) == {"raise", "hold", "lower"}
    for value in RECOMMENDED_ACTIONS:
        assert recommended_action_for(value) == RECOMMENDED_ACTIONS[value]
    # Anything unexpected falls back to "hold"'s action rather than raising.
    assert recommended_action_for("unexpected") == RECOMMENDED_ACTIONS["hold"]


def test_build_grammar_quotes_escalation_alternation_and_truck_id():
    grammar = build_grammar("truck-03")
    # Every backslash-quote token must sit inside a "..." literal — no bare
    # `\"raise\"`-style token outside quotes, the bug this pattern replaces.
    assert '("\\"raise\\"" | "\\"hold\\"" | "\\"lower\\"")' in grammar
    # The truck_id term must be its own self-delimited GBNF literal (not
    # concatenated directly against the preceding term with no separator,
    # which is the second bug this pattern replaces — verified by an actual
    # llama-completion run that otherwise raised "expecting newline or end").
    assert f' {_gbnf_quoted_literal("truck-03")} ' in grammar
    # severity is no longer part of the grammar at all -- see module docstring.
    assert "severity" not in grammar
    # Neither is recommended_action -- it's a deterministic template on
    # escalation now (RECOMMENDED_ACTIONS), not model output. This removes the
    # escalation/recommended_action contradiction by construction, after a
    # vocabulary rename alone (see docstring) failed to fix it.
    assert "recommended_action" not in grammar


def test_gbnf_quoted_literal_round_trips_through_json_escaping():
    # The term's *decoded* content (unescape \\ and \") must equal the real
    # JSON-quoted value, for both a plain id and one containing a quote —
    # i.e. what the model is forced to emit is exactly json.dumps(raw_value)
    for raw_value in ["truck-03", 'truck"03', "back\\slash"]:
        term = _gbnf_quoted_literal(raw_value)
        assert term.startswith('"') and term.endswith('"')
        decoded = term[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        assert decoded == json.dumps(raw_value)


def test_process_configures_lazily_from_user_config():
    function = LlmTriageFunction()
    assert function._configured is False

    context = _FakeContext({"llm_binary_path": "/nonexistent/bin", "llm_model_path": "/nonexistent/model"})
    result = function.process(_payload(), context)

    # Config is read from the context, not hardcoded — a missing binary means
    # inference fails, but configuration itself must have happened.
    assert function._configured is True
    assert function._backend is not None
    assert result is None  # LlmInferenceError from a missing binary is caught, not raised


def test_process_only_configures_once():
    function = LlmTriageFunction()
    context = _FakeContext({"llm_binary_path": "/nonexistent/bin", "llm_model_path": "/nonexistent/model"})

    function.process(_payload(), context)
    first_backend = function._backend

    # Second call must not re-run _configure even if user config changes —
    # that's the lazy-init contract: setup runs once per instance lifetime.
    context._user_config["llm_binary_path"] = "/some/other/bin"
    function.process(_payload(), context)
    assert function._backend is first_backend


def test_process_returns_grammar_shaped_card_via_mock_backend(monkeypatch):
    # LlmBackend.generate is stubbed directly rather than relying on
    # LlmServerBackend's mock-mode content-sniffing heuristic, which keys off
    # phrases our DEFAULT_PROMPT_TEMPLATE doesn't happen to contain. start() is
    # also stubbed -- process() calls it unconditionally now (see triage_function
    # module docstring on the SubprocessLlmBackend -> LlmServerBackend switch), and
    # the real one would try to launch a real llama-server binary that doesn't
    # exist at DEFAULT_BINARY_PATH on a generic test machine.
    from llm_inference.client import LlmServerBackend

    monkeypatch.setattr(LlmServerBackend, "start", lambda self: self)
    monkeypatch.setattr(
        LlmServerBackend,
        "generate",
        lambda self, prompt, config=None: (
            '{"risk_synthesis": "wet roads plus liquid cargo raises real risk", '
            '"escalation": "raise", "truck_id": "placeholder"}'
        ),
    )
    function = LlmTriageFunction()
    context = _FakeContext()  # empty user config -> falls back to defaults
    result = function.process(_payload(eta_slip_min=4.0, baseline_severity="medium"), context)

    assert result is not None
    card = json.loads(result)
    # truck_id/eta_impact are grammar-hardcoded from the input, regardless of what
    # the (mocked) model actually returned for truck_id.
    assert card["truck_id"] == "truck-03"
    assert card["eta_impact"] == 4.0
    # severity is computed, never model output: baseline "medium" + escalation
    # "raise" (from the mocked completion above) -> "high".
    assert card["baseline_severity"] == "medium"
    assert card["severity"] == "high"
    assert card["escalation"] == "raise"
    # recommended_action is derived from escalation, not model output -- the mocked
    # completion above doesn't even include it, and the card still gets one, always
    # in agreement with escalation by construction.
    assert card["recommended_action"] == RECOMMENDED_ACTIONS["raise"]


def _mock_backend_returning(monkeypatch, escalation: str) -> None:
    """Stubs LlmServerBackend the same way test_process_returns_grammar_shaped_card_
    via_mock_backend does, but parameterized on escalation so the uplink-gate tests
    below can drive process() to a specific final severity via apply_escalation.
    """
    from llm_inference.client import LlmServerBackend

    monkeypatch.setattr(LlmServerBackend, "start", lambda self: self)
    monkeypatch.setattr(
        LlmServerBackend,
        "generate",
        lambda self, prompt, config=None: json.dumps(
            {
                "risk_synthesis": "scenario reasoning",
                "escalation": escalation,
                "truck_id": "placeholder",
            }
        ),
    )


def test_process_uplinks_a_card_raised_to_high(monkeypatch):
    _mock_backend_returning(monkeypatch, "raise")
    function = LlmTriageFunction()
    context = _FakeContext()  # default uplink_min_severity: "high"

    result = function.process(_payload(baseline_severity="medium"), context)

    assert result is not None
    card = json.loads(result)
    assert card["severity"] == "high"  # medium + raise
    assert context.published == []  # uplinked, not held locally


def test_process_holds_a_card_lowered_to_medium(monkeypatch):
    _mock_backend_returning(monkeypatch, "lower")
    function = LlmTriageFunction()
    context = _FakeContext()

    result = function.process(_payload(baseline_severity="high"), context)

    assert result is None  # "medium" doesn't meet the default "high" gate
    assert len(context.published) == 1
    topic, data = context.published[0]
    assert topic == LOCAL_TRIAGE_TOPIC
    published_card = json.loads(data.decode("utf-8"))
    assert published_card["severity"] == "medium"  # high + lower


def test_process_holds_a_card_held_at_low(monkeypatch):
    _mock_backend_returning(monkeypatch, "hold")
    function = LlmTriageFunction()
    context = _FakeContext()

    result = function.process(_payload(baseline_severity="low"), context)

    assert result is None
    assert len(context.published) == 1
    topic, data = context.published[0]
    assert topic == LOCAL_TRIAGE_TOPIC
    published_card = json.loads(data.decode("utf-8"))
    assert published_card["severity"] == "low"  # low + hold, unchanged


def test_uplink_min_severity_config_override(monkeypatch):
    _mock_backend_returning(monkeypatch, "hold")
    function = LlmTriageFunction()
    context = _FakeContext({"uplink_min_severity": "medium"})

    result = function.process(_payload(baseline_severity="medium"), context)

    # A "medium" card is held under the default gate ("high"), but this override
    # lowers the bar to "medium" -- so the same card is uplinked instead.
    assert result is not None
    card = json.loads(result)
    assert card["severity"] == "medium"
    assert context.published == []


def test_build_card_is_ungated(monkeypatch):
    # build_card (used directly by tests/model/eval_lib.py's run_flow_b_trials) must
    # return every card regardless of severity -- the uplink gate lives in process()
    # only, so eval scoring isn't corrupted by cards the gate would otherwise hold.
    _mock_backend_returning(monkeypatch, "hold")
    function = LlmTriageFunction()
    context = _FakeContext()

    result = function.build_card(_payload(baseline_severity="low"), context)

    assert result is not None
    card = json.loads(result)
    assert card["severity"] == "low"
    assert context.published == []  # build_card never touches the local topic
