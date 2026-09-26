import json
import logging

from talk1_edge_intelligence.triage_function import (
    LlmTriageFunction,
    _gbnf_quoted_literal,
    build_grammar,
)


class _FakeContext:
    """Minimal stand-in for a Pulsar Functions Context: get_logger() and
    get_user_config_value(key), the two methods LlmTriageFunction calls.
    """

    def __init__(self, user_config: dict | None = None) -> None:
        self._user_config = user_config or {}
        self._logger = logging.getLogger("test")

    def get_logger(self) -> logging.Logger:
        return self._logger

    def get_user_config_value(self, key: str) -> str | None:
        return self._user_config.get(key)


def _payload(*, truck_id: str = "truck-03", eta_slip_min: float = 13.8) -> str:
    return json.dumps(
        {
            "truck_id": truck_id,
            "corridor": "I-95N (Near Exit 4)",
            "signals": ["sustained_low_speed", "stop_go_index"],
            "metrics": {
                "rolling_avg_speed": "12 mph",
                "eta_slip_min": eta_slip_min,
                "traffic_pattern": "high velocity variance (stop-and-go spikes)",
            },
            "contextual_triggers": {
                "local_time": "17:15 (Friday Rush Hour)",
                "historical_baseline_speed": "55 mph",
            },
        }
    )


def test_build_grammar_quotes_severity_alternation_and_truck_id():
    grammar = build_grammar(13.8, "truck-03")
    # Every backslash-quote token must sit inside a "..." literal — no bare
    # `\"low\"`-style token outside quotes, which is the bug this replaces.
    assert '("\\"low\\"" | "\\"medium\\"" | "\\"high\\"")' in grammar
    # The truck_id term must be its own self-delimited GBNF literal (not
    # concatenated directly against the preceding term with no separator,
    # which is the second bug this replaces — verified by an actual
    # llama-completion run that otherwise raised "expecting newline or end").
    assert f' {_gbnf_quoted_literal("truck-03")} ' in grammar
    assert "13.8" in grammar


def test_gbnf_quoted_literal_round_trips_through_json_escaping():
    # The term's *decoded* content (unescape \\ and \") must equal the real
    # JSON-quoted value, for both a plain id and one containing a quote —
    # i.e. what the model is forced to emit is exactly json.dumps(raw_value).
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
    # SubprocessLlmBackend's mock-mode content-sniffing heuristic, which
    # keys off phrases our DEFAULT_PROMPT_TEMPLATE doesn't happen to contain.
    from llm_inference.client import SubprocessLlmBackend

    monkeypatch.setattr(
        SubprocessLlmBackend,
        "generate",
        lambda self, prompt, config=None: (
            '{"severity": "medium", "event_label": "traffic_incident_suspected", '
            '"dispatch_action": "monitor", "eta_impact": 0.0, "truck_id": "placeholder"}'
        ),
    )
    function = LlmTriageFunction()
    context = _FakeContext()  # empty user config -> falls back to defaults
    result = function.process(_payload(eta_slip_min=4.0), context)

    assert result is not None
    card = json.loads(result)
    # eta_impact/truck_id are grammar-hardcoded from the input, regardless of
    # what the (mocked) model actually returned for them.
    assert card["eta_impact"] == 4.0
    assert card["truck_id"] == "truck-03"
