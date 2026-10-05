import json, statistics as st, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
peaks = {r["setup"]: r["peak_rss_mb"] for r in rows if "peak_rss_mb" in r}
calls = [r for r in rows if "wall_s" in r]
for s in dict.fromkeys(r["setup"] for r in calls):
    rs = [r for r in calls if r["setup"] == s]
    first, timed = rs[0], [r for r in rs if not r["warmup"]]
    w = sorted(r["wall_s"] for r in timed)
    print(f"{s}: first call {first['wall_s']:.2f}s | timed n={len(timed)} median {st.median(w):.2f}s [{w[0]:.2f}-{w[-1]:.2f}]"
          f" | cores {st.median(r['cpu_s']/r['wall_s'] for r in timed):.2f}"
          f" | prompt {timed[0]['prompt_tokens']} tok, reused {st.median(r['prefix_reused_tokens'] for r in timed):.0f}"
          f" | out {st.median(r['output_tokens'] for r in timed):.0f} tok | peak RSS {peaks.get(s)} MB"
          f" | no-JSON {sum(1 for r in timed if not r['warning'])}")
