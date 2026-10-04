"""Preliminary cross-platform report (eval-results/phone-proxies/PRELIMINARY-20261003.md).

One-off, written mid-run on 2026-10-03: the run IDs below are the Phase 1 runs and the
test-C run as they were then. Sections: generation and prompt speed per platform, the
real-workload energy and latency on M1 (test C), RAM capacity (L1), ARM quants (L3),
12-14B models (L4), the Cortex-X1 build (L2, partial at the time), and run-to-run
variance (mac2 Phase 1 vs its first repeat).

    python3 prelim_report.py > ../../eval-results/phone-proxies/PRELIMINARY-<date>.md
"""
import glob, json, os, re, statistics as st, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from summarize import load_bench, load_powermetrics, energy_j, powermetrics_path

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../eval-results/phone-proxies")
P1 = {"pi5": "pi5/20261003T184429Z", "c7g": "android-mainstream/20261003T184425Z", "c9g": "android-flagship/20261003T184418Z", "m1": "iphone-older/20261003T191829Z"}

def linux_tps(run, name, kind, t):
    p = f"{R}/{run}/llama-bench_{name}.json"
    if not os.path.exists(p): return None
    for x in load_bench(Path(p)):
        if x["kind"] == kind and x["threads"] == t: return x["tps"]

def mac_tps(run, name, label, kind):
    p = f"{R}/{run}/llama-bench_{label}_{name}.json"
    if not os.path.exists(p): return None
    for x in load_bench(Path(p)):
        if x["kind"] == kind: return x["tps"]

order = [l[3:].strip() for l in open(f"{R}/{P1['c9g']}/bench.log") if l.startswith("== ")]
pub = {"Qwen3.5-2B-Q4_K_M": "39.1", "gemma-4-E2B-it-Q4_K_M": "38.8"}
f = lambda v: f"{v:.1f}" if v else "–"

print("## 1. Generation speed, tg128 tok/s (Q4_K_M unless noted)\n")
print("| Model | Pi 5 proxy t=4 | c7g t=8 | c9g t=8 | M1 CPU t=4 | M1 Metal | iPhone 17 Pro (pub.) |")
print("|---|---|---|---|---|---|---|")
for n in order:
    print(f"| {n} | {f(linux_tps(P1['pi5'], n, 'tg', 4))} | {f(linux_tps(P1['c7g'], n, 'tg', 8))} | {f(linux_tps(P1['c9g'], n, 'tg', 8))} | {f(mac_tps(P1['m1'], n, 'cpu', 'tg'))} | {f(mac_tps(P1['m1'], n, 'metal-tg', 'tg'))} | {pub.get(n, '')} |")

print("\n## 2. Prompt processing, pp512 tok/s\n")
print("| Model | Pi 5 proxy t=4 | c7g t=8 | c9g t=8 | M1 CPU t=4 | M1 Metal |")
print("|---|---|---|---|---|---|")
for n in order:
    print(f"| {n} | {f(linux_tps(P1['pi5'], n, 'pp', 4))} | {f(linux_tps(P1['c7g'], n, 'pp', 8))} | {f(linux_tps(P1['c9g'], n, 'pp', 8))} | {f(mac_tps(P1['m1'], n, 'cpu', 'pp'))} | {f(mac_tps(P1['m1'], n, 'metal-pp', 'pp'))} |")

# --- C: real workload on M1 ------------------------------------------------------------------
c = f"{R}/iphone-older/C-workload-20261003T203147Z"
win = {}
for l in open(f"{c}/windows.log"):
    lab, s, e, _ = l.split(); win[lab] = (float(s.split("=")[1]), float(e.split("=")[1]))
S = load_powermetrics(powermetrics_path(Path(c)))
idle = [mw for s0, e0, mw in S for k, (a, b) in win.items() if k.startswith("idle") and s0 >= a and e0 <= b]
idle_mw = st.mean(idle)
art = {l.split()[0]: l.split()[1] for l in open(f"{c}/artifacts.txt") if len(l.split()) > 1}
rows = {}
for lab, (a, b) in win.items():
    if lab.startswith("idle"): continue
    key = lab.rsplit("_r", 1)[0]
    d = json.load(open(f"{R}/iphone-older/C-artifacts/{art[lab]}")); m = list(d["models"].values())[0]
    ej = energy_j(S, a, b, idle_mw); calls = m["latency"]["n"]
    q = m.get("escalation_calibration") or {}
    rows.setdefault(key, []).append((ej / calls, b - a, m["latency"]["p50_seconds"], m["latency"]["p95_seconds"], m["format_reliability"].get("rate", m["format_reliability"].get("structured_rate")), q.get("mismatch_rate"), calls, ej / (b - a)))
print(f"\n## 3. Talk 2 real workload on M1 (Metal), mean of 3 reps; idle {idle_mw:.0f} mW subtracted\n")
print("| Task / model | Calls/rep | J/call above idle (range) | Avg power W | p50 / p95 s | Format | Mismatch |")
print("|---|---|---|---|---|---|---|")
for k, v in rows.items():
    jc = [x[0] for x in v]
    print(f"| {k} | {v[0][6]} | **{st.mean(jc):.1f}** ({min(jc):.1f}-{max(jc):.1f}) | {st.mean(x[7] for x in v):.1f} | {st.mean(x[2] for x in v):.2f} / {st.mean(x[3] for x in v):.2f} | {st.mean(x[4] for x in v):.0%} | {'' if v[0][5] is None else f'{st.mean(x[5] for x in v):.1%}'} |")

# --- L1, L3, L4, L2, E ----------------------------------------------------------------------------
print("\n## 4. L1 RAM capacity (c9g, cgroup caps, weights resident)\n")
print(open(glob.glob(f"{R}/android-flagship/L1-ram-capacity-*/fits.csv")[0]).read())

print("## 5. L3 ARM quants on c9g, t=8 (vs Phase 1 Q4_K_M)\n")
l3 = glob.glob(f"{R}/android-flagship/L3-arm-quants-*")[0]
print("| File | pp512 | tg128 |"); print("|---|---|---|")
for p in sorted(glob.glob(f"{l3}/llama-bench_*.json")):
    n = os.path.basename(p)[12:-5]
    pp = next((x["tps"] for x in load_bench(Path(p)) if x["kind"] == "pp" and x["threads"] == 8), None)
    tg = next((x["tps"] for x in load_bench(Path(p)) if x["kind"] == "tg" and x["threads"] == 8), None)
    print(f"| {n} | {f(pp)} | {f(tg)} |")
print("\nPhase 1 Q4_K_M at t=8 for reference: " + ", ".join(f"{n}: pp {f(linux_tps(P1['c9g'], n, 'pp', 8))} / tg {f(linux_tps(P1['c9g'], n, 'tg', 8))}" for n in ("gemma-3-1b-it-Q4_K_M", "Phi-3.5-mini-instruct-Q4_K_M", "gemma-3-4b-it-Q4_K_M", "Llama-3.1-8B-Instruct-Q4_K_M", "GLM-4-9B-0414-Q4_K_M", "qwen3-8b-q4_k_m")))

print("\n## 6. L4 12-14B on c9g\n")
l4 = glob.glob(f"{R}/android-flagship/L4-phase2-preview-*")[0]
print("| Model | pp512 t=4 | pp512 t=8 | tg128 t=4 | tg128 t=8 |"); print("|---|---|---|---|---|")
for p in sorted(glob.glob(f"{l4}/llama-bench_*.json")):
    xs = load_bench(Path(p)); by = {(x["kind"], x["threads"]): x["tps"] for x in xs}
    print(f"| {os.path.basename(p)[12:-5]} | {f(by.get(('pp',4)))} | {f(by.get(('pp',8)))} | {f(by.get(('tg',4)))} | {f(by.get(('tg',8)))} |")

print("\n## 7. L2 Cortex-X1 ISA build vs native on c7g, t=8 (partial)\n")
l2 = glob.glob(f"{R}/android-mainstream/L2-phone-isa-x1-*")[0]
print("| Model | native pp / tg | x1 pp / tg | x1/native pp | x1/native tg |"); print("|---|---|---|---|---|")
for p in sorted(glob.glob(f"{l2}/llama-bench_*.json"), key=os.path.getmtime):
    n = os.path.basename(p)[12:-5]
    xs = load_bench(Path(p)); by = {(x["kind"], x["threads"]): x["tps"] for x in xs}
    npp, ntg = linux_tps(P1["c7g"], n, "pp", 8), linux_tps(P1["c7g"], n, "tg", 8)
    if by.get(("tg", 8)) and npp:
        print(f"| {n} | {npp:.1f} / {ntg:.1f} | {by[('pp',8)]:.1f} / {by[('tg',8)]:.1f} | {by[('pp',8)]/npp:.2f} | {by[('tg',8)]/ntg:.2f} |")

print("\n## 8. Repeatability: mac2 Phase 1 vs its first repeat (E)\n")
e1 = f"{R}/iphone-older/20261003T200756Z"
d = []
for n in order:
    for lab, kind in (("metal-tg", "tg"), ("metal-pp", "pp"), ("cpu", "tg")):
        a, b = mac_tps(P1["m1"], n, lab, kind), mac_tps("iphone-older/20261003T200756Z", n, lab, kind)
        if a and b: d.append((lab + "-" + kind, n, (b - a) / a))
for lab in ("metal-tg-tg", "metal-pp-pp", "cpu-tg"):
    xs = [abs(x[2]) for x in d if x[0] == lab]
    print(f"- {lab}: median |Δ| {st.median(xs):.1%}, max {max(xs):.1%} over {len(xs)} models")
