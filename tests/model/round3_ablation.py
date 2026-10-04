"""Prompt-engineering ablation for round 3's full task (round3_eval.py), on the same scenarios
and scorer. The variants are cumulative and were fixed before any ablation result was seen
(no per-variant tuning on the test set):

  base      round 3's full prompt and grammar, exactly
  facts     + the grammar makes the model write three physics facts before the baseline
            (abs_engaged, deceleration_band, severe_stop_and_go), and the prompt asks for them
  tables    + the severity rules, the final-severity shift and the actions as lookup tables
  template  + each model's own chat template (llama-server /apply-template); for Qwen3/Qwen3.5
            the assistant turn is pre-filled with the empty think block (thinking off)
  examples  + three worked examples with values and contexts that differ from the test cells
  temp0     + temperature 0 (production uses 0.2)
  grammar   a separate tier on top of `examples`: the grammar enforces severity and action from
            the model's own baseline and escalation ("the model judges, the grammar computes"),
            so the contradiction class is removed by construction rather than by prompting

Scored with round3_eval.score, plus per-fact accuracy for the variants that emit facts.
"""
from __future__ import annotations

import json
import time

from talk1_edge_intelligence.triage_function import RECOMMENDED_ACTIONS, apply_escalation

from tests.model import round3_eval as r
from tests.model.eval_lib import ESCALATION_SCENARIOS

VARIANTS: dict[str, dict] = {
    "base": {"style": "base", "facts": False, "native": False, "examples": False, "temperature": None, "consistent": False},
    "facts": {"style": "base", "facts": True, "native": False, "examples": False, "temperature": None, "consistent": False},
    "tables": {"style": "tables", "facts": True, "native": False, "examples": False, "temperature": None, "consistent": False},
    "template": {"style": "tables", "facts": True, "native": True, "examples": False, "temperature": None, "consistent": False},
    "examples": {"style": "tables", "facts": True, "native": True, "examples": True, "temperature": None, "consistent": False},
    "temp0": {"style": "tables", "facts": True, "native": True, "examples": True, "temperature": 0.0, "consistent": False},
    "grammar": {"style": "tables", "facts": True, "native": True, "examples": True, "temperature": None, "consistent": True},
}
LEVELS = ("low", "medium", "high")
BANDS = ("at or below 0.22 g", "0.22 to 0.45 g", "above 0.45 g")


# --- the physics facts -----------------------------------------------------------------------------
def band_for(g: float) -> str:
    return BANDS[0] if g <= 0.22 else BANDS[1] if g <= 0.45 else BANDS[2]


def facts_for(profile: str) -> dict:
    p = r.SEVERITY_PROFILES[profile]
    return {
        "abs_engaged": "yes" if p["abs_engaged"] else "no",
        "deceleration_band": band_for(p["peak_deceleration_g"]),
        "severe_stop_and_go": "yes" if p["stop_go_index"] > 0.8 else "no",
    }


# --- prompts -----------------------------------------------------------------------------------------
_FACTS_INSTRUCTION = (
    "Before baseline_severity, write three physics facts: abs_engaged (yes or no), "
    'deceleration_band ("at or below 0.22 g", "0.22 to 0.45 g" or "above 0.45 g") and '
    "severe_stop_and_go (yes only if the traffic pattern is severe stop-and-go compaction, "
    "otherwise no). "
)
FACTS_PROMPT_TEMPLATE = r.FULL_PROMPT_TEMPLATE.replace("Write baseline_severity first,", _FACTS_INSTRUCTION + "Then write baseline_severity,", 1)

_STEP1_TABLE = (
    "STEP 1 - BASELINE SEVERITY. Read three facts from the vehicle physics, then look the baseline "
    "up in the table:\n"
    "- abs_engaged: yes or no.\n"
    '- deceleration_band: "at or below 0.22 g", "0.22 to 0.45 g" (above 0.22 up to 0.45) or '
    '"above 0.45 g".\n'
    "- severe_stop_and_go: yes only if the traffic pattern is severe stop-and-go compaction, "
    "otherwise no.\n\n"
    "| abs_engaged | deceleration_band | severe_stop_and_go | baseline |\n"
    "|---|---|---|---|\n"
    "| yes | any | any | high |\n"
    "| no | above 0.45 g | any | high |\n"
    "| no | 0.22 to 0.45 g | yes | high |\n"
    "| no | 0.22 to 0.45 g | no | medium |\n"
    "| no | at or below 0.22 g | yes | medium |\n"
    "| no | at or below 0.22 g | no | low |\n\n"
)
_STEP3_TABLE = (
    "STEP 3 - FINAL SEVERITY AND ACTION, from these tables:\n"
    "| baseline | raise | hold | lower |\n"
    "|---|---|---|---|\n"
    + "".join(f"| {b} | " + " | ".join(apply_escalation(b, e) for e in ("raise", "hold", "lower")) + " |\n" for b in LEVELS)
    + "\n| escalation | recommended_action |\n|---|---|\n"
    + "".join(f"| {e} | {RECOMMENDED_ACTIONS[e]} |\n" for e in ("raise", "hold", "lower"))
    + "\n"
)
_FT = r.FULL_PROMPT_TEMPLATE
TABLES_PROMPT_TEMPLATE = (
    _FT[: _FT.index("STEP 1")]
    + _STEP1_TABLE
    + _FT[_FT.index("Vehicle physics:") : _FT.index("STEP 3")]
    + _STEP3_TABLE
    + _FT[_FT.index("Truck ID: {truck_id}") : _FT.index("Write baseline_severity first,")]
    + "Write abs_engaged, deceleration_band and severe_stop_and_go first, then baseline_severity "
    "from the table, then risk_synthesis naming the SPECIFIC field(s) that drove your escalation "
    "and why, then escalation, then severity and recommended_action from the tables -- all of them "
    "must agree with each other. "
    + _FT[_FT.index("Respond using the validated format template.") :]
)


def card_text(fields: list[tuple[str, str]]) -> str:
    """A card exactly as the grammar lays it out (two-space indent, one field per line)."""
    return "{\n" + ",\n".join(f'  "{k}": {json.dumps(v)}' for k, v in fields) + "\n}"


# Values and contexts deliberately unlike the test cells (0.15/0.30/0.50 g; the three
# ESCALATION_SCENARIOS), one per escalation direction and one per severity rule family.
_EXAMPLES = [
    ("truck-08", "I-80W", 0.40, "no", "mild speed oscillations (intermittent deceleration)",
     "Freezing rain, icy ramps", "Propane tanker", "Running 35 minutes behind schedule",
     "no", "0.22 to 0.45 g", "no", "medium",
     "Propane is hazardous cargo and freezing rain degrades traction, with the driver behind schedule: three risk multipliers.",
     "raise"),
    ("truck-21", "I-70E", 0.10, "no", "severe stop-and-go compaction (repeated hard braking)",
     "Overcast, dry roads", "Palletized dry goods", "Running to plan; no exceptions logged",
     "no", "at or below 0.22 g", "yes", "medium",
     "Dry roads, general freight and a driver running to plan: no risk multiplier and nothing positively indicating extra control.",
     "hold"),
    ("truck-33", "US-101S", 0.20, "yes", "elevated velocity variance (frequent speed cycling)",
     "Clear, dry", "Empty flatbed", "Ahead of schedule; driver pulled over for a documented tire inspection",
     "yes", "at or below 0.22 g", "no", "high",
     "Clear weather and an empty trailer are not risk factors, and the documented inspection shows the driver in control.",
     "lower"),
]


def examples_block() -> str:
    out = ["Worked examples (other trucks; your answer must follow the same format):"]
    for (tid, corr, g, abs_, traffic, weather, cargo, dispatch, f_abs, f_band, f_sng, base, synth, esc) in _EXAMPLES:
        out.append(
            f"\nInput: Truck {tid} on {corr}. Peak deceleration: {g} g. ABS engaged: {abs_}. Traffic pattern: {traffic}. "
            f"Weather: {weather}. Cargo: {cargo}. Dispatch status: {dispatch}.\nAnswer:\n"
            + card_text([
                ("abs_engaged", f_abs), ("deceleration_band", f_band), ("severe_stop_and_go", f_sng),
                ("baseline_severity", base), ("risk_synthesis", synth), ("escalation", esc),
                ("severity", apply_escalation(base, esc)), ("recommended_action", RECOMMENDED_ACTIONS[esc]),
                ("truck_id", tid),
            ])
        )
    return "\n".join(out) + "\n\nNow assess this event.\n\n"


def render(variant: str, payload: dict) -> tuple[str, str]:
    """(user prompt, grammar) for one payload under one variant."""
    v = VARIANTS[variant]
    template = {"base": r.FULL_PROMPT_TEMPLATE, "tables": TABLES_PROMPT_TEMPLATE}[v["style"]]
    if v["style"] == "base" and v["facts"]:
        template = FACTS_PROMPT_TEMPLATE
    t, m = payload.get("contextual_triggers", {}), payload["metrics"]
    prompt = template.format(
        truck_id=payload["truck_id"], corridor=payload["corridor"],
        weather_condition=t.get("weather_condition", "unknown"), cargo_type=t.get("cargo_type", "unknown"),
        dispatch_status=t.get("dispatch_status", "unknown"),
        peak_deceleration_g=m["peak_deceleration_g"], abs_engaged="yes" if m["abs_engaged"] else "no",
        traffic_pattern=m["traffic_pattern"],
    )
    if v["examples"]:
        prompt = examples_block() + prompt
    if not v["facts"] and not v["consistent"]:
        return prompt, r.build_full_grammar(payload["truck_id"])
    return prompt, build_grammar(payload["truck_id"], facts=v["facts"], consistent=v["consistent"])


# --- grammar -----------------------------------------------------------------------------------------
def g(text: str) -> str:
    """A GBNF string literal matching `text` exactly."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _alt(values) -> str:
    return "(" + " | ".join(g(json.dumps(v)) for v in values) + ")"


def build_grammar(truck_id: str, facts: bool, consistent: bool) -> str:
    """The full card with optional facts lines; `consistent` makes severity and action literals that
    follow from the generated baseline and escalation (one branch per pair)."""

    def key(name: str) -> str:
        return g('  "' + name + '": ')

    comma = g(",\n")
    parts = [g("{\n")]
    if facts:
        parts += [key("abs_engaged"), _alt(("yes", "no")), comma,
                  key("deceleration_band"), _alt(BANDS), comma,
                  key("severe_stop_and_go"), _alt(("yes", "no")), comma]
    parts.append(key("baseline_severity"))
    synth = " ".join([g('  "risk_synthesis": "'), '[^"]*', g('",\n')])
    tail = " ".join([key("truck_id"), g(json.dumps(truck_id)), g("\n}")])
    actions = [RECOMMENDED_ACTIONS[e] for e in ("raise", "hold", "lower")]
    if not consistent:
        parts += [_alt(LEVELS), comma, synth,
                  key("escalation"), _alt(("raise", "hold", "lower")), comma,
                  key("severity"), _alt(LEVELS), comma,
                  key("recommended_action"), _alt(actions), comma, tail]
        return "root ::= " + " ".join(parts)
    branches = []
    for b in LEVELS:
        escs = " | ".join(
            g('  "escalation": "' + e + '",\n  "severity": "' + apply_escalation(b, e) + '",\n'
              '  "recommended_action": ' + json.dumps(RECOMMENDED_ACTIONS[e]) + ",\n")
            for e in ("raise", "hold", "lower")
        )
        branches.append(" ".join([g(json.dumps(b) + ",\n"), synth, "(" + escs + ")"]))
    parts += ["(" + " | ".join(branches) + ")", tail]
    return "root ::= " + " ".join(parts)


# --- the model's own chat template ----------------------------------------------------------------
def native_prompt(base_url: str, user_text: str, timeout: float) -> str:
    """llama-server's /apply-template with one user turn. For the Qwen3 / Qwen3.5 templates, close
    the reasoning block the way their enable_thinking=false path does."""
    prompt = r._post(base_url, "/apply-template", {"messages": [{"role": "user", "content": user_text}]}, timeout)["prompt"]
    if prompt.endswith("<|im_start|>assistant\n"):
        prompt += "<think>\n\n</think>\n\n"
    elif prompt.endswith("<|im_start|>assistant\n<think>\n"):
        prompt += "\n</think>\n\n"
    return prompt


# --- one call ----------------------------------------------------------------------------------------
def score(card: dict | None, profile: str, truth_baseline: str, expected: str, facts: bool) -> dict:
    s = r.score("full", card, truth_baseline, expected)
    if facts:
        want = facts_for(profile)
        for k in want:
            s[f"{k}_ok"] = bool(card) and card.get(k) == want[k]
        s["facts_ok"] = all(s[f"{k}_ok"] for k in want)
    return s


def call_variant(base_url: str, variant: str, payload: dict, scenario: str, profile: str, truth_baseline: str,
                 temperature: float, timeout: float) -> r.Round3Call:
    v = VARIANTS[variant]
    user_text, grammar = render(variant, payload)
    expected = ESCALATION_SCENARIOS[scenario]["expected_direction"]
    temp = v["temperature"] if v["temperature"] is not None else temperature
    start = time.monotonic()
    try:
        prompt = native_prompt(base_url, user_text, timeout) if v["native"] else user_text
        resp = r.complete(base_url, prompt, grammar, r.JSON_MAX_TOKENS["full"] + (60 if v["facts"] else 0), temp, timeout)
    except Exception as exc:  # noqa: BLE001 - a failed call is a measurement
        call = r.Round3Call(scenario, profile, time.monotonic() - start, error=str(exc))
        call.scores = score(None, profile, truth_baseline, expected, v["facts"])
        return call
    call = r.Round3Call(
        scenario, profile, time.monotonic() - start, content=resp.get("content", ""),
        tokens_predicted=int(resp.get("tokens_predicted", 0)), tokens_evaluated=int(resp.get("tokens_evaluated", 0)),
        stop_type=str(resp.get("stop_type", "")),
    )
    try:
        call.card = json.loads(call.content.strip())
    except Exception as exc:  # noqa: BLE001
        call.error = f"unparsable card: {exc}"
    call.scores = score(call.card, profile, truth_baseline, expected, v["facts"])
    return call
