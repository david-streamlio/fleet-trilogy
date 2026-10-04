from tests.model import round3_ablation as a
payload = {"truck_id": "truck-47", "corridor": "I-95N", "baseline_severity": "high",
  "metrics": {"peak_deceleration_g": 0.3, "abs_engaged": False, "traffic_pattern": "severe stop-and-go compaction (repeated hard braking)"},
  "contextual_triggers": {"weather_condition": "Heavy rain, wet asphalt", "cargo_type": "Liquids / Chemical Tanker", "dispatch_status": "Running 20 minutes behind schedule"}}
for v in a.VARIANTS:
    c = a.call_variant("http://localhost:18124", v, payload, "escalate-worthy", "high-volatile", "high", 0.2, 120)
    print(f"{v:9s} err={str(c.error)[:70]:70s} prompt_toks={c.tokens_evaluated:5d} out={c.tokens_predicted:4d} "
          f"fields={len(c.card or {})} all_ok={c.scores.get('all_ok')} consistent={c.scores.get('consistent')} facts_ok={c.scores.get('facts_ok')}")
