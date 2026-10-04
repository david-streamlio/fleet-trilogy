import json, glob, os, collections
d = sorted(glob.glob(os.path.expanduser("~/phoneproxy/results/Q-confirm-*")))[-1]
art = {l.split()[0]: l.split()[1] for l in open(f"{d}/artifacts.txt") if len(l.split()) > 1}
agg = collections.defaultdict(lambda: [0, 0, 0, 0, [], 0])
for lab, f in art.items():
    m = list(json.load(open(os.path.expanduser(f"~/fleet-trilogy/eval-results/{f}")))["models"].values())[0]
    key = lab.rsplit("_r", 1)[0].replace("edge_triage_", "")
    e, fr = m["escalation_calibration"], m["format_reliability"]
    a = agg[key]; a[0] += e["total"] - e["matched"]; a[1] += e["total"]; a[2] += fr["parsed"]; a[3] += fr["total"]; a[4].append(m["latency"]["p50_seconds"])
    for s, v in e.get("per_scenario", {}).items():
        pass
for k, (mis, tot, p, ft, lat, _) in agg.items():
    print(f"{k:42s} mismatch {mis:3d}/{tot} ({mis/tot:.1%})  format {p}/{ft}  p50 {sum(lat)/len(lat):.2f}s")
