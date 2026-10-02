"""Shared harness for Tier 2 (talk3_pulsar_speaks_english) model evals — real
llama.cpp-family runtime, real GGUF model.

Deliberately separate from eval_lib.py (Flow A / Edge Triage Pipeline): Tier 2's task shape is
fundamentally different, not a variant of either. Flow A and the Edge Triage Pipeline ask a model to
classify/decide (severity, escalation) over telemetry signals; Tier 2's model
never decides anything (scope and reroute are plain code in synthesizer.py) —
its only job is to paraphrase already-decided facts into a short spoken-style
warning. That changes what "format reliability" and "grounding" even mean here:

- Tier 2's own contract (prompting.generate_spoken_warning) already falls back
  to raw completion text when no parseable JSON comes back — "valid JSON" is
  not the real bar, "some usable spoken-warning text" is. So format reliability
  here measures structured_rate (did it follow the requested shape) separately
  from nonempty_rate (did SOME usable text come back at all), rather than a
  single parse/fail axis.
- Grounding here is about whether the *prose* stays faithful to already-decided
  facts (corridor name, the reroute call) — not exact-value copying the way
  Flow A and the Edge Triage Pipeline check truck_id/eta_impact equality, because there's no structured
  field to compare, just natural language.
- Speakability is a genuinely new axis with no Flow A or Edge Triage Pipeline analog: this text is
  meant to be read aloud (TTS), so markdown/code-fence/leaked-JSON artifacts
  and runaway length are real failures that "valid JSON" would never catch.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from fleet_telemetry_model import EnrichmentCard
from llm_inference import LlmBackend, LlmGenerationConfig
from llm_inference.structured import extract_json_object
from talk3_pulsar_speaks_english.prompting import render_synthesis_prompt

DEFAULT_EVAL_TIMEOUT_SECONDS = 180.0

# LlmGenerationConfig's own default (256) is far more than this task ever needs and,
# unlike Flow A and the Edge Triage Pipeline, Tier 2 has no grammar/stop sequence to force early termination --
# a model that doesn't stop on its own burns the full budget every time. Real Pi 4
# run (2026-09-28, eval-results/compare-tier2-edge-node00-20260928T000412Z.json):
# Qwen3-8B and Llama-3.1-8B-Instruct collapsed to 10.0%/6.7% nonempty_rate, every
# failure reading exactly "did not respond within 300.0s" -- at their measured Pi
# throughput (~0.455-0.461 tok/s), 256 tokens takes ~555-560s, nearly double the
# 300s budget, while GLM-4-9B (slower per-token at 0.304 tok/s) finished fine because
# it reliably self-terminates well short of 256 tokens for this prompt. Adding an
# actual `stop` sequence was considered and rejected -- llama-server excludes matched
# stop text from the returned content (the same lesson triage_function.py's grammar/
# stop interaction bug already taught this project), and Tier 2 has no grammar to
# fall back on, so a stop match here would strip the JSON's closing brace and break
# extract_json_object for every model, not just these two. Capping max_tokens instead
# sidesteps that trap entirely. 110 is sized off MAX_SPEAKABLE_WORDS' own "generous
# ceiling" below (70 words, already documented as "roughly double a genuinely long
# 3-sentence warning") converted to tokens (~100-101 at ~1.3-1.4 tokens/word) plus a
# few tokens of {"spoken_warning": "..."} JSON overhead -- comfortably covers any
# legitimate answer while bounding worst-case Pi latency to ~239-242s at these two
# models' real measured throughput, well under the 300s timeout.
DEFAULT_MAX_TOKENS = 110

# Mirrors triage_function.DEFAULT_THREADS' own tuning rationale (the M4 dev
# machine's 12 performance cores) -- kept as a separate local constant rather
# than importing across talk packages from a test file; --model-threads
# overrides this on any other host (a Pi 4 has 4 cores total).
DEFAULT_THREADS = 12

# Generous ceiling for a "2-3 sentence" spoken warning (per SYNTHESIS_WARNING_PROMPT's
# own instruction) — not a hard science, just a guard against a model rambling into an
# unspeakable wall of text. Roughly double a genuinely long 3-sentence warning.
MAX_SPEAKABLE_WORDS = 70

# Artifacts that have no business in text meant to be read aloud by TTS. Checked
# case-insensitively against the resolved spoken_warning text, not the raw completion
# (a model that emits markdown around valid JSON still produces clean spoken_warning
# text once extracted — this only catches artifacts that survived into the actual
# text a TTS engine would receive).
SPEAKABILITY_ARTIFACTS = ("```", "**", "##", "- ", "{", "}", '"spoken_warning"', "<html", "http://", "https://")

REROUTE_LANGUAGE = ("reroute", "re-route", "detour", "alternate route", "alternative route")


@dataclass
class Tier2Scenario:
    """One canonical (cards, already-decided facts) input — the LLM never
    derives scope/reroute itself (see synthesizer.py), so these are fixed
    inputs to the prompt, not something the eval computes from the cards."""

    name: str
    corridor: str
    cards: list[EnrichmentCard]
    scope: str
    reroute_recommended: bool
    reroute_detail: str | None


def _card(*, truck_id: str, corridor: str, severity: str, eta_impact: float = 8.0) -> EnrichmentCard:
    return EnrichmentCard(
        event="sustained_slowdown",
        severity=severity,
        signals=["sustained_low_speed", "stop_go_index"],
        eta_impact=eta_impact,
        corridor=corridor,
        truck_id=truck_id,
    )


# Three scenarios spanning the real branches of synthesizer.decide_scope/decide_reroute
# — single_truck (never reroutes, regardless of severity), corridor_wide without any
# high-severity report (still no reroute), and corridor_wide with a high-severity report
# (the only branch that recommends a reroute). Grounding checks below are keyed to
# these three, same spirit as eval_lib.ESCALATION_SCENARIOS.
TIER2_SCENARIOS: dict[str, Tier2Scenario] = {
    "single-truck": Tier2Scenario(
        name="single-truck",
        corridor="I-95N",
        cards=[_card(truck_id="truck-01", corridor="I-95N", severity="medium")],
        scope="single_truck",
        reroute_recommended=False,
        reroute_detail=None,
    ),
    "corridor-wide-no-reroute": Tier2Scenario(
        name="corridor-wide-no-reroute",
        corridor="I-95N",
        cards=[
            _card(truck_id="truck-02", corridor="I-95N", severity="medium"),
            _card(truck_id="truck-03", corridor="I-95N", severity="medium"),
        ],
        scope="corridor_wide",
        reroute_recommended=False,
        reroute_detail=None,
    ),
    "corridor-wide-with-reroute": Tier2Scenario(
        name="corridor-wide-with-reroute",
        corridor="I-95N",
        cards=[
            _card(truck_id="truck-04", corridor="I-95N", severity="high"),
            _card(truck_id="truck-05", corridor="I-95N", severity="medium"),
        ],
        scope="corridor_wide",
        reroute_recommended=True,
        reroute_detail="Reroute traffic around I-95N — 2 trucks reporting a correlated high-severity slowdown.",
    ),
}


@dataclass
class Tier2Trial:
    raw_output: str
    latency_seconds: float
    spoken_warning: str
    structured: bool  # True: parsed as {"spoken_warning": "..."}; False: fell back to raw text
    error: str | None = None


def run_tier2_trials(
    backend: LlmBackend,
    scenario: Tier2Scenario,
    n: int,
    timeout_seconds: float = DEFAULT_EVAL_TIMEOUT_SECONDS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[Tier2Trial]:
    """Calls the real Tier 2 synthesis prompt against `scenario` n times.

    Mirrors prompting.generate_spoken_warning's own extract-or-fall-back-to-raw-text
    logic exactly (reusing extract_json_object rather than reimplementing JSON
    extraction) so this measures the actual production code path — but unlike
    generate_spoken_warning, records *which* path was taken (structured vs.
    fallback) rather than discarding that distinction, since it's exactly the
    signal format-reliability needs here.
    """
    prompt = render_synthesis_prompt(
        corridor=scenario.corridor,
        cards=scenario.cards,
        scope=scenario.scope,
        reroute_recommended=scenario.reroute_recommended,
        reroute_detail=scenario.reroute_detail,
    )
    config = LlmGenerationConfig(timeout_seconds=timeout_seconds, max_tokens=max_tokens)
    trials: list[Tier2Trial] = []
    for _ in range(n):
        start = time.monotonic()
        try:
            raw = backend.generate(prompt, config)
        except Exception as exc:  # noqa: BLE001 - a failed call is a measurement, not a bug
            trials.append(
                Tier2Trial(
                    raw_output="", latency_seconds=time.monotonic() - start, spoken_warning="", structured=False, error=str(exc)
                )
            )
            continue
        latency = time.monotonic() - start
        try:
            parsed = extract_json_object(raw)
            warning = parsed.get("spoken_warning")
            if isinstance(warning, str) and warning.strip():
                trials.append(
                    Tier2Trial(raw_output=raw, latency_seconds=latency, spoken_warning=warning.strip(), structured=True)
                )
                continue
        except ValueError:
            pass
        trials.append(Tier2Trial(raw_output=raw, latency_seconds=latency, spoken_warning=raw.strip(), structured=False))
    return trials


def check_tier2_format_reliability(trials: list[Tier2Trial]) -> dict:
    """(a) FORMAT RELIABILITY, Tier 2 shape: structured_rate (did it follow the
    requested {"spoken_warning": ...} shape) is reported separately from
    nonempty_rate (did SOME usable text come back at all) — see module
    docstring for why a single parse/fail axis would misrepresent this task's
    actual contract."""
    total = len(trials)
    structured = sum(1 for t in trials if t.structured)
    nonempty = sum(1 for t in trials if t.error is None and t.spoken_warning.strip())
    errored = sum(1 for t in trials if t.error is not None)
    return {
        "total": total,
        "structured": structured,
        "structured_rate": (structured / total) if total else 0.0,
        "nonempty": nonempty,
        "nonempty_rate": (nonempty / total) if total else 0.0,
        "errors": errored,
        "sample_errors": [t.error for t in trials if t.error is not None][:5],
    }


def check_speakability(trials: list[Tier2Trial]) -> dict:
    """(b) SPEAKABILITY — no Flow A or Edge Triage Pipeline analog. This text is meant to be read
    aloud by TTS, so markdown/code-fence/leaked-JSON-key artifacts and running
    on far past a "2-3 sentence" spoken warning are real failures a JSON parser
    would never catch."""
    violations = []
    checked = 0
    for t in trials:
        if t.error is not None:
            continue
        checked += 1
        text = t.spoken_warning
        problems = []
        lowered = text.lower()
        for artifact in SPEAKABILITY_ARTIFACTS:
            if artifact in lowered:
                problems.append(f"contains non-speakable artifact {artifact!r}")
        word_count = len(text.split())
        if word_count > MAX_SPEAKABLE_WORDS:
            problems.append(f"{word_count} words exceeds the {MAX_SPEAKABLE_WORDS}-word spoken-length ceiling")
        if not text.strip():
            problems.append("empty")
        if problems:
            violations.append({"spoken_warning": text, "problems": problems})
    return {
        "total": checked,
        "violations": len(violations),
        "violation_rate": (len(violations) / checked) if checked else 0.0,
        "sample_violations": violations[:5],
    }


def _corridor_mention_patterns(corridor: str) -> tuple[str, ...]:
    """A corridor code like "I-95N" is rarely spoken verbatim -- a model
    naturally paraphrases it ("I-95 North", "Interstate 95 North"). The route
    NUMBER is the one part that survives every natural phrasing, so that's
    what grounding checks against, not the literal code string. Verified
    against real model output: Gemma-3-4B-it wrote "I-95 North" in every
    single trial and was scored a 100% grounding violation for it under the
    old exact-string check -- a harness bug, not a real omission."""
    match = re.search(r"\d+", corridor)
    return (match.group(0),) if match else (corridor.lower(),)


# Negation cues checked in the ~20 characters before a REROUTE_LANGUAGE match.
# Without this, "No reroute is recommended" (the CORRECT thing to say when
# reroute_recommended=False) matches the bare keyword "reroute" and gets
# flagged as if it recommended one -- verified against real model output:
# Qwen3-8B wrote exactly that sentence for a reroute_recommended=False
# scenario and was scored as a violation for it, backwards from what happened.
_NEGATION_CUES = ("no ", "not ", "n't ", "without ", "none ")


def _mentions_reroute_affirmatively(text: str) -> bool:
    """True only if reroute/detour language appears without an immediately
    preceding negation cue. See module note above for why a bare substring
    check on REROUTE_LANGUAGE alone is backwards for negated sentences."""
    for keyword in REROUTE_LANGUAGE:
        start = 0
        while True:
            idx = text.find(keyword, start)
            if idx == -1:
                break
            preceding = text[max(0, idx - 20) : idx]
            if not any(cue in preceding for cue in _NEGATION_CUES):
                return True
            start = idx + len(keyword)
    return False


def check_tier2_grounding(trials: list[Tier2Trial], scenario: Tier2Scenario) -> dict:
    """(c) GROUNDING, Tier 2 shape: does the *prose* stay faithful to the
    already-decided corridor/reroute facts? Deliberately asymmetric on
    reroute, same "flag contradictions, not absence" philosophy as
    eval_lib.check_escalation_direction: a model that invents reroute/detour
    language when none was recommended is a real hallucination (it's
    contradicting a decision synthesizer.py already made); a model that
    doesn't explicitly say "reroute" when one WAS recommended might just be
    phrasing it differently (e.g. "an advisory is in effect") and isn't
    flagged as a hard violation, only tallied informationally."""
    corridor_patterns = _corridor_mention_patterns(scenario.corridor)
    violations = []
    checked = 0
    reroute_mentioned_when_recommended = 0
    for t in trials:
        if t.error is not None:
            continue
        checked += 1
        text = t.spoken_warning.lower()
        problems = []
        if not any(p in text for p in corridor_patterns):
            problems.append(f"corridor {scenario.corridor!r} not mentioned (checked for {corridor_patterns})")
        mentions_reroute = _mentions_reroute_affirmatively(text)
        if not scenario.reroute_recommended and mentions_reroute:
            problems.append("mentions reroute/detour language despite reroute_recommended=False")
        if scenario.reroute_recommended and mentions_reroute:
            reroute_mentioned_when_recommended += 1
        if problems:
            violations.append({"spoken_warning": t.spoken_warning, "problems": problems})
    return {
        "total": checked,
        "violations": len(violations),
        "violation_rate": (len(violations) / checked) if checked else 0.0,
        "sample_violations": violations[:5],
        "reroute_mentioned_when_recommended": reroute_mentioned_when_recommended if scenario.reroute_recommended else None,
    }


def _percentile(ordered: list[float], fraction: float) -> float:
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


@dataclass
class Tier2Report:
    """Same accumulate-then-dump-one-artifact convention as EdgeTriageReport/Tier3Report."""

    config: dict
    format_reliability: dict = field(default_factory=dict)
    speakability: dict = field(default_factory=dict)
    grounding_by_scenario: dict = field(default_factory=dict)
    latency_samples_seconds: list[float] = field(default_factory=list)

    def add_latencies(self, samples: list[float]) -> None:
        self.latency_samples_seconds.extend(samples)

    def latency_percentiles(self) -> dict:
        if not self.latency_samples_seconds:
            return {"p50_seconds": None, "p95_seconds": None, "n": 0}
        ordered = sorted(self.latency_samples_seconds)
        return {
            "p50_seconds": _percentile(ordered, 0.50),
            "p95_seconds": _percentile(ordered, 0.95),
            "n": len(ordered),
        }

    def to_dict(self) -> dict:
        return {
            "config": self.config,
            "format_reliability": self.format_reliability,
            "speakability": self.speakability,
            "grounding_by_scenario": self.grounding_by_scenario,
            "latency": self.latency_percentiles(),
        }

    def render_summary(self, artifact_path) -> str:
        lat = self.latency_percentiles()
        lines = [
            "",
            "=== Tier 2 (talk3 synthesis) eval summary ===",
            f"artifact: {artifact_path}",
            f"model: {self.config.get('model_path')} via {self.config.get('binary_path')}",
        ]
        if self.format_reliability:
            fr = self.format_reliability
            lines.append(
                f"format reliability: structured={fr['structured_rate']:.1%}, "
                f"nonempty={fr['nonempty_rate']:.1%} ({fr['nonempty']}/{fr['total']})"
            )
        if self.speakability:
            sp = self.speakability
            lines.append(f"speakability violations: {sp['violation_rate']:.1%} ({sp['violations']}/{sp['total']})")
        for name, gr in self.grounding_by_scenario.items():
            lines.append(f"grounding[{name}] violations: {gr['violation_rate']:.1%} ({gr['violations']}/{gr['total']})")
        if lat["n"]:
            lines.append(f"latency: p50={lat['p50_seconds']:.2f}s p95={lat['p95_seconds']:.2f}s (n={lat['n']})")
        return "\n".join(lines)
