"""Regression coverage for extract_json_object's echoed-prompt/fenced-block boundary.

Each raw string below is a real, byte-for-byte completion captured from
`SubprocessLlmBackend` running Qwen2.5-1.5B/0.5B-Instruct (Q4_K_M) via mainline
llama.cpp's `llama-completion -no-cnv` during a Tier 3 `make compare-models` run —
NOT synthetic. `-no-cnv` puts the binary in raw completion mode: it echoes the whole
prompt (including the prompt's own inline JSON example) before continuing it, and
these small quantized instruct models routinely restate that example before (or
instead of) producing their own answer. The original extractor did
`find("{")`/`rfind("}")` across the whole string, which spliced the echoed example
and the real answer into one span and raised `json.JSONDecodeError: Extra data` even
though a valid answer was present in the text.
"""

from __future__ import annotations

import pytest

from llm_inference.structured import extract_json_object

# Captured from Qwen2.5-1.5B-Instruct: echoed prompt + echoed example, then the real
# answer inside a ```json fenced block, followed by prose explaining it.
FENCED_AFTER_ECHOED_PROMPT = (
    'You are generating a structured enrichment card for fleet dispatch. Cheap math '
    'has already detected the signals below — do not re-derive detection, just '
    'classify severity and describe the ETA impact.\n\n'
    'Respond with ONLY a single JSON object with exactly these keys: "event", '
    '"severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no '
    'markdown fences.\n\nTruck: truck-47\nCorridor: I-95N\n'
    "Signals detected by cheap math: ['sustained_low_speed', 'stop_go_index', 'eta_slip']\n"
    'Rolling average speed: 35.0 mph\nETA slip: 6.0 minutes\n\n'
    'Example shape: {"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": '
    '4.0, "corridor": "I-95N", "truck_id": "truck-47"} '
    "Here's the JSON object with the required keys:\n\n"
    '```json\n{\n  "event": "traffic_incident_suspected",\n  "severity": "high",\n'
    '  "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"],\n'
    '  "eta_impact": 4.0,\n  "corridor": "I-95N",\n  "truck_id": "truck-47"\n}\n``` \n\n'
    'This object reflects the detected signals and the calculated ETA impact, as '
    'requested. The severity is considered high due to the presence of multiple '
    'traffic anomalies, and the ETA impact is 4 minutes, indicating a significant delay.'
)

# Captured from Qwen2.5-1.5B-Instruct: echoed prompt + echoed example TWICE, then a
# bare (unfenced) real answer, ending with llama.cpp's "[end of text]" marker.
BARE_ANSWER_AFTER_DOUBLE_ECHO = (
    'You are generating a structured enrichment card for fleet dispatch.\n\n'
    'Respond with ONLY a single JSON object with exactly these keys: "event", '
    '"severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no '
    'markdown fences.\n\nTruck: truck-47\nCorridor: I-95N\n\n'
    'Example shape: {"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": '
    '4.0, "corridor": "I-95N", "truck_id": "truck-47"} '
    '{"event": "traffic_incident_suspected", "severity": "high", "signals": '
    '["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": 4.0, '
    '"corridor": "I-95N", "truck_id": "truck-47"}\n\n'
    '{\n  "event": "traffic_incident_suspected",\n  "severity": "high",\n'
    '  "signals": [\n    "sustained_low_speed",\n    "stop_go_index",\n    "eta_slip"\n  ],\n'
    '  "eta_impact": 4.0,\n  "corridor": "I-95N",\n  "truck_id": "truck-47"\n} [end of text]'
)

# Captured from Qwen2.5-0.5B-Instruct: echoed prompt + echoed example, then prose,
# then the real (bare) answer, then more prose that runs past a truncated max_tokens.
BARE_ANSWER_FOLLOWED_BY_TRUNCATED_PROSE = (
    'You are generating a structured enrichment card for fleet dispatch.\n\n'
    'Respond with ONLY a single JSON object with exactly these keys: "event", '
    '"severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no '
    'markdown fences.\n\nTruck: truck-47\nCorridor: I-95N\n\n'
    'Example shape: {"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": '
    '4.0, "corridor": "I-95N", "truck_id": "truck-47"} '
    'The truck has detected sustained low-speed, stop-go index, and eta slip signals. '
    'The rolling average speed is 35.0 mph.\n\n'
    '{"event": "traffic_incident_suspected", "severity": "high", "signals": '
    '["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": 6.0, '
    '"corridor": "I-95N", "truck_id": "truck-47"} The truck has detected sustained '
    'low-speed, stop-go index, and eta slip signals. The rolling average speed is '
    '35.0 mph, which is below the expected average speed of 50.0 mph. The ETA slip '
    'is 6.0 minutes, which is not a critical factor for the truck\'s journey. The '
    "signal of 'sustained_low_speed' indicates a potential hazard, while 'stop_go_"
)

# Captured from Qwen2.5-0.5B-Instruct: echoed prompt + echoed example TWICE (as
# "Example shape:" both times), and NO real answer produced at all.
DOUBLE_ECHO_WITH_NO_REAL_ANSWER = (
    'You are generating a structured enrichment card for fleet dispatch.\n\n'
    'Respond with ONLY a single JSON object with exactly these keys: "event", '
    '"severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no '
    'markdown fences.\n\nTruck: truck-47\nCorridor: I-95N\n\n'
    'Example shape: {"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": '
    '4.0, "corridor": "I-95N", "truck_id": "truck-47"} '
    'Example shape: {"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], "eta_impact": '
    '6.0, "corridor": "I-95N", "truck_id": "truck-47"} [end of text]'
)


def test_extracts_fenced_answer_after_echoed_prompt_and_example():
    card = extract_json_object(FENCED_AFTER_ECHOED_PROMPT)
    assert card["eta_impact"] == 4.0
    assert card["truck_id"] == "truck-47"


def test_extracts_last_bare_answer_after_doubly_echoed_example():
    card = extract_json_object(BARE_ANSWER_AFTER_DOUBLE_ECHO)
    assert card == {
        "event": "traffic_incident_suspected",
        "severity": "high",
        "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"],
        "eta_impact": 4.0,
        "corridor": "I-95N",
        "truck_id": "truck-47",
    }


def test_extracts_bare_answer_even_when_trailing_prose_is_truncated_mid_sentence():
    card = extract_json_object(BARE_ANSWER_FOLLOWED_BY_TRUNCATED_PROSE)
    assert card["eta_impact"] == 6.0


def test_double_echoed_example_with_no_real_answer_returns_the_last_echo_verbatim():
    """Known heuristic limit: when a model never produces anything beyond restating
    the prompt's own example, "last complete JSON object in the text" is indistinguishable
    from a real answer that happens to equal the last echo — there's no reliable
    signal to detect "no real answer was given" from the raw string alone. This is
    accepted, not silently treated as a parse failure (this reflects the raw output
    the eval-harness's grounding check will separately catch as ungrounded, since
    eta_impact=6.0 wasn't derived from an eta_slip_min the model was ever given here)."""
    card = extract_json_object(DOUBLE_ECHO_WITH_NO_REAL_ANSWER)
    assert card["eta_impact"] == 6.0


def test_still_parses_a_clean_unwrapped_json_completion():
    raw = (
        '{"event": "traffic_incident_suspected", "severity": "high", '
        '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], '
        '"eta_impact": 4.0, "corridor": "I-95N", "truck_id": "truck-47"}'
    )
    assert extract_json_object(raw)["truck_id"] == "truck-47"


def test_raises_when_no_json_object_is_present_at_all():
    with pytest.raises(ValueError, match="did not contain a JSON object"):
        extract_json_object("[mock llm completion] Truck 47 has slowed down.")


# Captured from Qwen2.5-1.5B-Instruct during the 2026-09-25 Pi 4 decision-grade run
# (eval-results/compare-edge-node00-20260925T030826Z.json): the model copies the
# prompt's own "Signals detected by cheap math: [...]" line verbatim into its real
# fenced answer, single-quoted Python-repr list syntax and all — otherwise-valid
# JSON that plain json.loads rejects outright. See docs/TALK2-0.5B-CAPABILITY-CLIFF.md.
FENCED_ANSWER_WITH_SINGLE_QUOTED_SIGNALS_LIST = (
    'You are generating a structured enrichment card for fleet dispatch. Cheap math '
    'has already detected the signals below — do not re-derive detection, just '
    'classify severity and describe the ETA impact.\n\n'
    'Respond with ONLY a single JSON object with exactly these keys: "event", '
    '"severity", "signals", "eta_impact", "corridor", "truck_id". No prose, no '
    'markdown fences.\n\nTruck: truck-47\nCorridor: I-95N\n'
    "Signals detected by cheap math: ['sustained_low_speed', 'stop_go_index', 'eta_slip']\n"
    'Rolling average speed: 35.0 mph\nETA slip: 6.0 minutes\n\n'
    '"eta_impact" MUST be the ETA slip value given above (6.0) — copy it exactly, do '
    'not invent or estimate a different number. "truck_id" and "corridor" MUST be '
    'copied exactly from above. Do not reuse any value from the shape below —\n'
    'it is a structure template, not a real answer.\n\n'
    'Shape (placeholders only, not real values): {"event": "<event_name>", '
    '"severity": "<low|medium|high>", "signals": '
    "['sustained_low_speed', 'stop_go_index', 'eta_slip'], "
    '"eta_impact": <copy the ETA slip value above>, "corridor": "<copy the corridor '
    'above>", "truck_id": "<copy the truck id above>"} '
    "Here is the JSON object:\n\n"
    '```json\n{\n  "event": "ETA slip",\n  "severity": "high",\n'
    "  \"signals\": ['sustained_low_speed', 'stop_go_index', 'eta_slip'],\n"
    '  "eta_impact": 6.0,\n  "corridor": "I-95N",\n  "truck_id": "truck-47"\n}\n``` \n\n'
    'This object is now ready for use in generating the structured enrichment card.'
)


def test_extracts_fenced_answer_with_single_quoted_signals_list():
    card = extract_json_object(FENCED_ANSWER_WITH_SINGLE_QUOTED_SIGNALS_LIST)
    assert card == {
        "event": "ETA slip",
        "severity": "high",
        "signals": ["sustained_low_speed", "stop_go_index", "eta_slip"],
        "eta_impact": 6.0,
        "corridor": "I-95N",
        "truck_id": "truck-47",
    }


def test_normalization_does_not_touch_prose_apostrophes():
    raw = (
        "The truck's ETA has slipped. "
        '{"event": "traffic_incident_suspected", "severity": "high", '
        '"signals": ["sustained_low_speed"], "eta_impact": 4.0, "corridor": "I-95N", '
        '"truck_id": "truck-47"}'
    )
    assert extract_json_object(raw)["truck_id"] == "truck-47"
