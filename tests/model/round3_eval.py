"""Round 3 of the hardware-spectrum study: a harder Edge Triage task, and reasoning on vs off.

Two eval variants, both opt-in and both living entirely in this harness. The production
pipeline (talk1_edge_intelligence.triage_function) is untouched: its prompt, grammar and
deterministic functions are imported and reused, never modified.

1. task="full" -- undo the 2026-09-26 narrowing (impact-track row 5; commits 18b836f,
   754ab57). On the Pi 4, small models asked for severity + action + escalation in one call
   contradicted themselves, so severity moved to classify_severity() and the action to
   recommended_action_for(); the LLM kept only a bounded escalation. Here the LLM gets the
   whole job back: it classifies baseline severity from the same physics fields
   classify_severity uses (stated as rules), decides the escalation from the same
   operational context, then derives the final severity and the recommended action. The
   deterministic code is the answer key, so scoring is exact. task="narrow" is the
   production prompt and grammar, for a like-for-like baseline in the same harness.

2. mode -- how the prompt reaches the model:
   - "raw": exactly as production -- the bare prompt on llama-server's /completion, no chat
     template, grammar starting at "{". Qwen3-family models cannot think in this mode.
   - "chat-budget" (added 2026-10-04, after Qwen3.5-9B's chat-on reasoning ran past its 2,048-token
     budget without closing </think>): budget forcing. Phase 1 lets the model reason with no grammar
     until it closes </think> or reaches the budget; if it didn't close it, "</think>" is appended
     for it; phase 2 generates the card under the usual grammar. Every model then answers within
     the same thinking cap, and think_forced records which calls were cut off.
   - "chat-off" / "chat-on" (Qwen3 / Qwen3.5 chat format only): the prompt as a user turn,
     with the assistant turn pre-filled. Both models' own templates switch thinking off by
     pre-filling an empty "<think>\n\n</think>\n\n" block (enable_thinking=false), and
     Qwen3.5's opens "<think>\n" when it is on; chat-on pre-fills "<think>\n" for both and
     the grammar admits free reasoning up to "</think>" before the same JSON. Everything
     else (prompt text, temperature, scenarios) is identical across modes.

Ground truth: classify_severity / apply_escalation / recommended_action_for for the physics
and the derived fields; ESCALATION_SCENARIOS' documented expected directions for the
escalation (the same hypothesis the production eval uses, same caveat).
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field

from fleet_telemetry_model import TelemetryEvent, to_json
from talk1_edge_intelligence.severity_classifier import classify_severity
from talk1_edge_intelligence.triage_function import (
    DEFAULT_PROMPT_TEMPLATE,
    RECOMMENDED_ACTIONS,
    _gbnf_quoted_literal,
    apply_escalation,
    build_grammar,
    recommended_action_for,
)

from tests.model.eval_lib import ESCALATION_SCENARIOS

TASKS = ("narrow", "full")
MODES = ("raw", "chat-off", "chat-on", "chat-budget")
# The card's own token budget. narrow = production's DEFAULT_MAX_TOKENS. The full card adds three
# fields and a risk_synthesis that names more evidence: Phi-3.5-mini's ran 187-300 tokens in the
# first smoke test, one truncated at 300, so the full task gets 450 rather than scoring
# truncations as wrong answers.
JSON_MAX_TOKENS = {"narrow": 300, "full": 450}

# --- physics profiles for the full task ------------------------------------------------------
# Each passes the coprocessor's slowdown gate (stop_go_index >= 0.5, canonical speed/ETA) and
# hits one branch of classify_severity. 0.72 renders as "elevated velocity variance", 0.85 as
# "severe stop-and-go compaction" -- the coprocessor's text uses classify_severity's own 0.8
# boundary, so the traffic pattern the model reads determines the class exactly.
SEVERITY_PROFILES: dict[str, dict] = {
    "low": {"peak_deceleration_g": 0.15, "abs_engaged": False, "stop_go_index": 0.72},
    "medium-volatile": {"peak_deceleration_g": 0.15, "abs_engaged": False, "stop_go_index": 0.85},
    "medium": {"peak_deceleration_g": 0.30, "abs_engaged": False, "stop_go_index": 0.72},
    "high-volatile": {"peak_deceleration_g": 0.30, "abs_engaged": False, "stop_go_index": 0.85},
    "high-decel": {"peak_deceleration_g": 0.50, "abs_engaged": False, "stop_go_index": 0.72},
    "high-abs": {"peak_deceleration_g": 0.15, "abs_engaged": True, "stop_go_index": 0.72},
}

# --- the full-task prompt -------------------------------------------------------------------------
# Step 2's text is production's DEFAULT_PROMPT_TEMPLATE verbatim (operational context, how to
# weigh each field, the decision rules), so the escalation judgment is the same one the narrow
# task asks for. Step 1 states classify_severity's thresholds; step 3 states apply_escalation and
# RECOMMENDED_ACTIONS.
_OPERATIONAL_START = DEFAULT_PROMPT_TEMPLATE.index("Operational context:")
_OPERATIONAL_END = DEFAULT_PROMPT_TEMPLATE.index("Truck ID: {truck_id}")
_OPERATIONAL_RULES = DEFAULT_PROMPT_TEMPLATE[_OPERATIONAL_START:_OPERATIONAL_END]

FULL_PROMPT_TEMPLATE = (
    "You are a fleet dispatch operational-risk assessor. Assess this slowdown event in three "
    "steps.\n\n"
    "STEP 1 - BASELINE SEVERITY from vehicle physics, using exactly these rules:\n"
    "- high if ABS engaged is yes, or the peak deceleration is above 0.45 g.\n"
    "- Otherwise, if the peak deceleration is 0.22 g or below: medium if the traffic pattern is "
    "severe stop-and-go compaction, else low.\n"
    "- Otherwise (above 0.22 g, up to 0.45 g): high if the traffic pattern is severe "
    "stop-and-go compaction, else medium.\n\n"
    "Vehicle physics:\n"
    "Peak deceleration: {peak_deceleration_g} g\n"
    "ABS engaged: {abs_engaged}\n"
    "Traffic pattern: {traffic_pattern}\n\n"
    "STEP 2 - ESCALATION. Decide whether the operational context is strong enough evidence to "
    "move away from the baseline.\n\n"
    + _OPERATIONAL_RULES  # holds only the {weather_condition}/{cargo_type}/{dispatch_status} placeholders
    + "STEP 3 - FINAL SEVERITY AND ACTION:\n"
    "- severity: the baseline moved one level up for raise and one level down for lower (low "
    "and high are the limits), unchanged for hold.\n"
    f'- recommended_action: exactly "{RECOMMENDED_ACTIONS["raise"]}" for raise, '
    f'"{RECOMMENDED_ACTIONS["hold"]}" for hold, "{RECOMMENDED_ACTIONS["lower"]}" for lower.\n\n'
    "Truck ID: {truck_id}\n"
    "Corridor: {corridor}\n\n"
    "Write baseline_severity first, then risk_synthesis naming the SPECIFIC field(s) that drove "
    "your escalation and why, then escalation, severity and recommended_action -- all five must "
    "agree with each other and with the rules above. "
    "Respond using the validated format template. DO NOT include markdown code boxes or "
    "introductory prose."
)


def build_full_grammar(truck_id: str) -> str:
    """The full task's card: production's field order principle ("reasoning order") extended --
    baseline, then the free-text reasoning, then the decisions that follow from it."""
    sev = '("\\"low\\"" | "\\"medium\\"" | "\\"high\\"")'
    esc = '("\\"raise\\"" | "\\"hold\\"" | "\\"lower\\"")'
    act = " | ".join(_gbnf_quoted_literal(RECOMMENDED_ACTIONS[k]) for k in ("raise", "hold", "lower"))
    return (
        'root ::= "{\\n"'
        f' "  \\"baseline_severity\\": " {sev} ",\\n"'
        ' "  \\"risk_synthesis\\": \\"" [^"]* "\\",\\n"'
        f' "  \\"escalation\\": " {esc} ",\\n"'
        f' "  \\"severity\\": " {sev} ",\\n"'
        f' "  \\"recommended_action\\": " ({act}) ",\\n"'
        f' "  \\"truck_id\\": " {_gbnf_quoted_literal(truck_id)} "\\n"'
        ' "}"'
    )


# --- chat wrapping and thinking control (Qwen3 / Qwen3.5 template) -------------------------------
def wrap_prompt(prompt: str, mode: str) -> str:
    if mode == "raw":
        return prompt
    turn = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    return turn + ("<think>\n" if mode == "chat-on" else "<think>\n\n</think>\n\n")


def wrap_grammar(card_grammar: str, mode: str) -> str:
    """chat-on: free reasoning, then the closing tag, then the unchanged card grammar."""
    if mode != "chat-on":
        return card_grammar
    card = card_grammar.replace("root ::=", "card ::=", 1)
    return 'root ::= think "</think>" [ \\t\\n]* card\nthink ::= [^<]*\n' + card


# --- one call, with the server's own token accounting ---------------------------------------------
@dataclass
class Round3Call:
    scenario: str
    profile: str
    latency_seconds: float
    content: str = ""
    tokens_predicted: int = 0
    tokens_evaluated: int = 0
    think_tokens: int = 0
    stop_type: str = ""
    think_forced: bool = False  # chat-budget: the budget ran out before the model closed </think>
    card: dict | None = None
    error: str | None = None
    scores: dict = field(default_factory=dict)


def _post(base_url: str, path: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        f"{base_url}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def complete(base_url: str, prompt: str, grammar: str, n_predict: int, temperature: float, timeout: float) -> dict:
    """The same request body LlmServerBackend sends (prompt, n_predict, temperature, grammar;
    no stop -- see triage_function's comment), but returning the whole response so token counts,
    stop type and timings are kept."""
    return _post(
        base_url,
        "/completion",
        {"prompt": prompt, "n_predict": n_predict, "temperature": temperature, "grammar": grammar},
        timeout,
    )


def count_tokens(base_url: str, text: str, timeout: float) -> int:
    return len(_post(base_url, "/tokenize", {"content": text}, timeout).get("tokens", []))


def split_card(content: str, mode: str) -> tuple[str, str]:
    """(reasoning, card text). With chat-on the grammar guarantees one "</think>" before the card."""
    if mode == "chat-on" and "</think>" in content:
        think, card = content.split("</think>", 1)
        return think, card.strip()
    return "", content.strip()


# --- payloads ------------------------------------------------------------------------------------
def build_payload(coprocessor, context, event: TelemetryEvent, triggers: dict, baseline_override: str | None) -> dict | None:
    """The real coprocessor's payload, with the scenario's operational context patched in (the
    same post-hoc mechanism as eval_lib.run_edge_triage_trials)."""
    raw = coprocessor.process(to_json(event), context)
    if raw is None:
        return None
    payload = json.loads(raw)
    payload["contextual_triggers"].update(triggers)
    if baseline_override:
        payload["baseline_severity"] = baseline_override
    return payload


def render(task: str, payload: dict) -> tuple[str, str]:
    """(prompt, card grammar) for one payload."""
    t = payload.get("contextual_triggers", {})
    common = {
        "truck_id": payload["truck_id"],
        "corridor": payload["corridor"],
        "weather_condition": t.get("weather_condition", "unknown"),
        "cargo_type": t.get("cargo_type", "unknown"),
        "dispatch_status": t.get("dispatch_status", "unknown"),
    }
    if task == "narrow":
        prompt = DEFAULT_PROMPT_TEMPLATE.format(baseline_severity=payload["baseline_severity"], **common)
        return prompt, build_grammar(payload["truck_id"])
    m = payload["metrics"]
    prompt = FULL_PROMPT_TEMPLATE.format(
        peak_deceleration_g=m["peak_deceleration_g"],
        abs_engaged="yes" if m["abs_engaged"] else "no",
        traffic_pattern=m["traffic_pattern"],
        **common,
    )
    return prompt, build_full_grammar(payload["truck_id"])


# --- scoring ---------------------------------------------------------------------------------------
def allowed_directions(expected: str) -> tuple[str, ...]:
    return ("lower", "hold") if expected == "lower_or_hold" else (expected,)


def score(task: str, card: dict | None, truth_baseline: str, expected_direction: str) -> dict:
    """Per-call booleans. Format = parsed with every field valid (the grammar enforces most of
    it; this also catches a truncated or unparsable completion)."""
    ok_dirs = allowed_directions(expected_direction)
    if not card:
        return {"format_ok": False}
    esc = card.get("escalation")
    s = {
        "format_ok": esc in ("raise", "hold", "lower") and bool(card.get("risk_synthesis", "").strip()),
        "escalation_ok": esc in ok_dirs,
    }
    if task == "full":
        base, sev, act = card.get("baseline_severity"), card.get("severity"), card.get("recommended_action")
        s["format_ok"] = s["format_ok"] and base in ("low", "medium", "high") and sev in ("low", "medium", "high")
        s["baseline_ok"] = base == truth_baseline
        # Internally consistent: severity and action follow from the model's OWN baseline and
        # escalation by the stated rules (the contradiction the 2026-09 narrowing removed).
        s["consistent"] = (
            base in ("low", "medium", "high") and esc in RECOMMENDED_ACTIONS
            and sev == apply_escalation(base, esc) and act == recommended_action_for(esc)
        )
        # Correct end to end: what the deterministic pipeline accepts for this scenario.
        s["severity_ok"] = sev in {apply_escalation(truth_baseline, d) for d in ok_dirs}
        s["action_ok"] = act in {recommended_action_for(d) for d in ok_dirs}
        s["all_ok"] = all(s[k] for k in ("format_ok", "baseline_ok", "escalation_ok", "consistent", "severity_ok", "action_ok"))
    else:
        s["all_ok"] = s["format_ok"] and s["escalation_ok"]
    return s


def summarize(calls: list[Round3Call]) -> dict:
    keys = sorted({k for c in calls for k in c.scores})
    n = len(calls)
    rates = {k: sum(1 for c in calls if c.scores.get(k)) / n for k in keys} if n else {}
    lat = sorted(c.latency_seconds for c in calls)
    pct = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))] if lat else None  # noqa: E731
    by_scenario: dict[str, dict] = {}
    for c in calls:
        b = by_scenario.setdefault(c.scenario, {"n": 0, "escalations": {}, "all_ok": 0})
        b["n"] += 1
        e = (c.card or {}).get("escalation", "unparsed")
        b["escalations"][e] = b["escalations"].get(e, 0) + 1
        b["all_ok"] += int(bool(c.scores.get("all_ok")))
    by_profile: dict[str, dict] = {}
    for c in calls:
        b = by_profile.setdefault(c.profile, {"n": 0, "baseline_ok": 0, "all_ok": 0})
        b["n"] += 1
        b["baseline_ok"] += int(bool(c.scores.get("baseline_ok")))
        b["all_ok"] += int(bool(c.scores.get("all_ok")))
    return {
        "n": n,
        "rates": rates,
        "latency_p50_seconds": pct(0.5),
        "latency_p95_seconds": pct(0.95),
        "tokens_predicted_mean": sum(c.tokens_predicted for c in calls) / n if n else None,
        "think_tokens_mean": sum(c.think_tokens for c in calls) / n if n else None,
        "truncated": sum(1 for c in calls if c.stop_type == "limit"),
        "errors": sum(1 for c in calls if c.error),
        "by_scenario": by_scenario,
        "by_profile": by_profile,
    }


def call_once(base_url: str, task: str, mode: str, payload: dict, scenario: str, profile: str,
              truth_baseline: str, n_predict: int, temperature: float, timeout: float) -> Round3Call:
    prompt, card_grammar = render(task, payload)
    expected = ESCALATION_SCENARIOS[scenario]["expected_direction"]
    if mode == "chat-budget":
        return _call_budget(base_url, task, prompt, card_grammar, scenario, profile, truth_baseline, expected,
                            n_predict - JSON_MAX_TOKENS[task], temperature, timeout)
    start = time.monotonic()
    try:
        resp = complete(base_url, wrap_prompt(prompt, mode), wrap_grammar(card_grammar, mode), n_predict, temperature, timeout)
    except Exception as exc:  # noqa: BLE001 - a failed call is a measurement, as in eval_lib
        call = Round3Call(scenario, profile, time.monotonic() - start, error=str(exc))
        call.scores = score(task, None, truth_baseline, expected)
        return call
    call = Round3Call(
        scenario, profile, time.monotonic() - start,
        content=resp.get("content", ""), tokens_predicted=int(resp.get("tokens_predicted", 0)),
        tokens_evaluated=int(resp.get("tokens_evaluated", 0)), stop_type=str(resp.get("stop_type", "")),
    )
    think, card_text = split_card(call.content, mode)
    if think:
        try:
            call.think_tokens = count_tokens(base_url, think, timeout)
        except Exception:  # noqa: BLE001
            call.think_tokens = -1
    try:
        call.card = json.loads(card_text)
    except Exception as exc:  # noqa: BLE001
        call.error = f"unparsable card: {exc}"
    call.scores = score(task, call.card, truth_baseline, expected)
    return call


def _call_budget(base_url: str, task: str, prompt: str, card_grammar: str, scenario: str, profile: str,
                 truth_baseline: str, expected: str, budget: int, temperature: float, timeout: float) -> Round3Call:
    """chat-budget: think (no grammar, stop at </think>, at most `budget` tokens), then the card."""
    start = time.monotonic()
    first = wrap_prompt(prompt, "chat-on")  # ends with "<think>\n"
    try:
        think = _post(base_url, "/completion", {"prompt": first, "n_predict": budget, "temperature": temperature,
                                                "stop": ["</think>"]}, timeout)
        thought = think.get("content", "")
        second = first + thought.rstrip("\n") + "\n</think>\n\n"
        card = complete(base_url, second, card_grammar, JSON_MAX_TOKENS[task], temperature, timeout)
    except Exception as exc:  # noqa: BLE001 - a failed call is a measurement
        call = Round3Call(scenario, profile, time.monotonic() - start, error=str(exc))
        call.scores = score(task, None, truth_baseline, expected)
        return call
    call = Round3Call(
        scenario, profile, time.monotonic() - start, content=thought + "\n</think>\n\n" + card.get("content", ""),
        tokens_predicted=int(think.get("tokens_predicted", 0)) + int(card.get("tokens_predicted", 0)),
        tokens_evaluated=int(think.get("tokens_evaluated", 0)) + int(card.get("tokens_evaluated", 0)),
        think_tokens=int(think.get("tokens_predicted", 0)), stop_type=str(card.get("stop_type", "")),
        think_forced=str(think.get("stop_type", "")) == "limit",
    )
    try:
        call.card = json.loads(card.get("content", "").strip())
    except Exception as exc:  # noqa: BLE001
        call.error = f"unparsable card: {exc}"
    call.scores = score(task, call.card, truth_baseline, expected)
    return call


def truth_for(profile: str) -> str:
    p = SEVERITY_PROFILES[profile]
    return classify_severity(peak_deceleration_g=p["peak_deceleration_g"], abs_engaged=p["abs_engaged"], stop_go_index=p["stop_go_index"])
