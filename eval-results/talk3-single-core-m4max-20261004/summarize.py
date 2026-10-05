import json,statistics as st,sys,re
rows=[json.loads(l) for l in open(sys.argv[1])]
for s in dict.fromkeys(r['setup'] for r in rows):
    rs=[r for r in rows if r['setup']==s and not r['warmup']]
    def q(k):
        v=sorted(r[k] for r in rs if r.get(k) is not None)
        return f"{st.median(v):.2f} [{v[0]:.2f}-{v[-1]:.2f}]" if v else '-'
    pp=[r['prompt_eval_n']/r['prompt_eval_ms']*1000 for r in rs]
    tg=[r['eval_n']/r['eval_ms']*1000 for r in rs if r.get('eval_ms')]
    cores=[r['cpu_s']/r['wall_s'] for r in rs]
    bad=[r['warning'] for r in rs if r['warning'] and re.search(r'(three|3|all) trucks?[^.]*high[- ]severity|high[- ]severity[^.]*(three|3|all) trucks',r['warning'],re.I)]
    print(f"\n{s}: n={len(rs)} rc={set(r['rc'] for r in rs)}")
    print(f"  wall s     {q('wall_s')}")
    print(f"  load ms    {q('load_ms')}")
    print(f"  prompt tok/s {st.median(pp):.1f}  gen tok/s {st.median(tg):.1f}  out tokens {q('eval_n')}")
    print(f"  cores busy (cpu/wall) {st.median(cores):.2f}   cpu s {q('cpu_s')}")
    print(f"  peak RSS MB {q('peak_rss_mb')}  footprint MB {q('peak_footprint_mb')}")
    print(f"  no JSON warning: {sum(1 for r in rs if not r['warning'])};  '3 trucks high severity' overstatement: {len(bad)}/{len(rs)}")
