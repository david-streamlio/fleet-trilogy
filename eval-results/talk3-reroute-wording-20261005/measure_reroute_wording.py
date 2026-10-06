"""How often does Tier 2's spoken warning state a recommended reroute as already done?

Takes 6 and 7 of the Talk 3 demo both said "Traffic is (being) rerouted" where the
decision only recommends a reroute (reroute_recommended: true). This compares the
published prompt (PUBLISHED_SYNTHESIS_WARNING_PROMPT) with the current one, which adds
one instruction about it, on the demo's runtime and settings: GlobalSynthesisFunction's
in-process backend, CPU only, Gemma-3-4B-it Q4_K_M, the default LlmGenerationConfig
(temperature 0.7, 256 tokens). Each prompt gets a fresh backend with the same seed.

Scenarios: the demo's three cards (deploy/talk3-demo-cards.jsonl, with the synthesizer's
own scope and reroute decision) and tests/model/tier2_eval_lib.py's three. Per warning:
stated-as-done reroute (regex below), the demo's fact check (fact_check.check_warning:
any problem means a regeneration in the Function), and the eval's speakability and
grounding checks.

    uv run --no-sync python eval-results/talk3-reroute-wording-20261005/measure_reroute_wording.py \
        [--demo-n 20] [--eval-n 10] [--threads 12] [--seed 7]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from fleet_telemetry_model import EnrichmentCard, from_json
from llm_inference import InProcessLlmBackend, LlmGenerationConfig
from llm_inference.structured import extract_json_object
from talk3_pulsar_speaks_english import prompting
from talk3_pulsar_speaks_english.fact_check import check_warning
from talk3_pulsar_speaks_english.synthesizer import (
    decide_reroute,
    decide_scope,
)

from tests.model.tier2_eval_lib import (
    TIER2_SCENARIOS,
    Tier2Scenario,
    Tier2Trial,
    check_speakability,
    check_tier2_grounding,
)

MODEL = Path.home() / "tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf"
OUT = Path(__file__).resolve().parent

# A reroute described as in effect: "is/are/being/has been rerouted (diverted, ...)",
# "we're rerouting", "traffic rerouted". "A reroute is recommended" / "consider
# rerouting" don't match.
STATED_AS_DONE = re.compile(
    r"\b(?:is|are|was|were|has been|have been|being)\s+(?:being\s+|now\s+)?"
    r"(?:rerouted|diverted|detoured|redirected)\b"
    r"|\bwe(?:'re|\s+are)\s+(?:now\s+)?(?:rerouting|diverting|redirecting)\b"
    r"|\b(?:traffic|trucks|vehicles)\s+(?:rerouted|diverted|detoured)\b",
    re.IGNORECASE,
)


def demo_scenario() -> Tier2Scenario:
    lines = (REPO / "deploy/talk3-demo-cards.jsonl").read_text().splitlines()
    cards = [from_json(EnrichmentCard, line) for line in lines if line.strip()]
    scope = decide_scope(cards)
    reroute_recommended, reroute_detail = decide_reroute(cards, scope)
    return Tier2Scenario(
        name="demo-cards",
        corridor=cards[0].corridor,
        cards=cards,
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail,
    )


def run(template_name: str, template: str, scenarios: list[tuple[Tier2Scenario, int]], args) -> list[dict]:
    backend = InProcessLlmBackend(MODEL, threads=args.threads, gpu_layers=args.gpu_layers, seed=args.seed)
    backend.start()
    config = LlmGenerationConfig(threads=1)  # what the demo's Function passes (threads=1)
    rows = []
    try:
        for scenario, n in scenarios:
            prompt = prompting.render_synthesis_prompt(
                corridor=scenario.corridor,
                cards=scenario.cards,
                scope=scenario.scope,
                reroute_recommended=scenario.reroute_recommended,
                reroute_detail=scenario.reroute_detail,
                template=template,
            )
            for i in range(n):
                start = time.monotonic()
                raw = backend.generate(prompt, config)
                latency = time.monotonic() - start
                try:
                    warning = extract_json_object(raw).get("spoken_warning") or raw
                    structured = True
                except ValueError:
                    warning, structured = raw, False
                warning = str(warning).strip()
                problems = check_warning(
                    warning,
                    corridor=scenario.corridor,
                    cards=scenario.cards,
                    reroute_recommended=scenario.reroute_recommended,
                )
                rows.append(
                    {
                        "template": template_name,
                        "scenario": scenario.name,
                        "i": i,
                        "reroute_recommended": scenario.reroute_recommended,
                        "stated_as_done": bool(STATED_AS_DONE.search(warning)),
                        "fact_check_problems": problems,
                        "structured": structured,
                        "latency_s": round(latency, 2),
                        "spoken_warning": warning,
                    }
                )
                print(f"{template_name:9} {scenario.name:26} {i:2} done={rows[-1]['stated_as_done']!s:5} "
                      f"fact_ok={not problems!s:5} {warning[:110]!r}", flush=True)
    finally:
        backend.close()
    return rows


def summarize(rows: list[dict], scenarios: list[tuple[Tier2Scenario, int]]) -> list[dict]:
    summary = []
    for template_name in dict.fromkeys(r["template"] for r in rows):
        for scenario, _ in scenarios:
            sel = [r for r in rows if r["template"] == template_name and r["scenario"] == scenario.name]
            trials = [Tier2Trial(raw_output=r["spoken_warning"], latency_seconds=r["latency_s"],
                                 spoken_warning=r["spoken_warning"], structured=r["structured"]) for r in sel]
            summary.append(
                {
                    "template": template_name,
                    "scenario": scenario.name,
                    "n": len(sel),
                    "stated_as_done": sum(r["stated_as_done"] for r in sel),
                    "fact_check_failed": sum(bool(r["fact_check_problems"]) for r in sel),
                    "structured": sum(r["structured"] for r in sel),
                    "speakability_violations": check_speakability(trials)["violations"],
                    "grounding_violations": check_tier2_grounding(trials, scenario)["violations"],
                }
            )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-n", type=int, default=20)
    parser.add_argument("--eval-n", type=int, default=10)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--gpu-layers", type=int, default=0, help="0 = CPU only (the demo default); 99 = the whole model on the GPU")
    parser.add_argument("--templates", default="published,current", help="comma-separated: published, current")
    parser.add_argument("--tag", default="", help="suffix for warnings/summary file names")
    args = parser.parse_args()
    scenarios = [(demo_scenario(), args.demo_n)] + [(s, args.eval_n) for s in TIER2_SCENARIOS.values()]
    rows = []
    templates = {"published": prompting.PUBLISHED_SYNTHESIS_WARNING_PROMPT, "current": prompting.SYNTHESIS_WARNING_PROMPT}
    for name in args.templates.split(","):
        rows += run(name, templates[name], scenarios, args)
    summary = summarize(rows, scenarios)
    tag = f"-{args.tag}" if args.tag else ""
    (OUT / f"warnings{tag}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (OUT / f"summary{tag}.json").write_text(json.dumps({"args": vars(args), "model": str(MODEL), "summary": summary}, indent=2))
    print("\n| Prompt | Scenario | n | Reroute stated as done | Fact check failed | Structured | Speakability | Grounding |")
    print("|---|---|---|---|---|---|---|---|")
    for s in summary:
        print(f"| {s['template']} | {s['scenario']} | {s['n']} | {s['stated_as_done']} | {s['fact_check_failed']} | "
              f"{s['structured']} | {s['speakability_violations']} | {s['grounding_violations']} |")


if __name__ == "__main__":
    main()
