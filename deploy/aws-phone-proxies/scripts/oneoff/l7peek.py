import json, glob
f = sorted(glob.glob("/opt/phoneproxy/results/L7-*/artifacts.txt"))[-1]
for line in open(f):
    p = line.split()
    if len(p) < 2: continue
    m = list(json.load(open("/home/ubuntu/fleet-trilogy/eval-results/" + p[1]))["models"].values())[0]
    L = m["latency"]; fr = m["format_reliability"]; esc = m.get("escalation_calibration", {}).get("mismatch_rate")
    rate = fr.get("rate", fr.get("structured_rate"))
    print(f"{p[0]:42s} p50 {L['p50_seconds']:6.2f}  p95 {L['p95_seconds']:6.2f}  n={L['n']}  format {rate:.0%}" + ("" if esc is None else f"  mismatch {esc:.1%}"))
