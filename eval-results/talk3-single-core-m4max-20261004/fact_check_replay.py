"""Run fact_check.check_warning over every distinct warning in this folder's runs.
Run from the repo root:
    uv run --no-sync python eval-results/talk3-single-core-m4max-20261004/fact_check_replay.py
"""
import json
from pathlib import Path

from fleet_telemetry_model import EnrichmentCard, from_json
from talk3_pulsar_speaks_english.fact_check import check_warning

here = Path(__file__).parent
raw = [json.loads(l) for l in open("deploy/talk3-demo-cards.jsonl") if l.strip()]
seen = {}
for name in ("runs.jsonl", "runs_inprocess.jsonl", "smoke.jsonl"):
    for line in open(here / name):
        row = json.loads(line)
        if row.get("warning"):
            seen.setdefault((row["warning"], row.get("corridor", "I-95N")), name)

flagged = 0
for (warning, corridor), name in seen.items():
    cards = [from_json(EnrichmentCard, json.dumps({**c, "corridor": corridor})) for c in raw]
    problems = check_warning(warning, corridor=corridor, cards=cards, reroute_recommended=True)
    if problems:
        flagged += 1
        print(f"[{name}] {'; '.join(problems)}\n    {warning}\n")
print(f"{flagged} of {len(seen)} distinct warnings fail the check")
