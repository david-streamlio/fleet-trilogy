#!/usr/bin/env python3
"""Summarize a proxy's latest run in eval-results/phone-proxies/<name>/ as Markdown tables.

    summarize.py <proxy-dir> [<run-id>]

Speed comes from llama-bench's JSON (avg tok/s over the repetitions). On macOS runs, energy
comes from powermetrics: each llama-bench test runs at the tail of its window (after model
load and a tiny warm-up), so its interval is reconstructed backwards from the window end
using the JSON's per-repetition times. Energy is above idle (mean of the idle windows), the
same convention as the Pi meter and M4 Max rows in the impact track. powermetrics covers
CPU + GPU + ANE package power only: no DRAM, no rest-of-system.
"""
import datetime
import gzip
import json
import re
import sys
from pathlib import Path


def load_bench(path):
    try:
        rows = json.loads(path.read_text() or "[]")
    except json.JSONDecodeError:  # llama-bench still writing it: the model in progress
        return []
    out = []
    for r in rows:
        kind = "pp" if r["n_prompt"] > 0 else "tg"
        tokens = r["n_prompt"] if kind == "pp" else r["n_gen"]
        out.append({
            "kind": kind, "threads": r["n_threads"], "tps": r["avg_ts"], "sd": r["stddev_ts"],
            "busy_s": sum(r["samples_ns"]) / 1e9, "tokens": tokens * len(r["samples_ns"]),
            "params_b": r["model_n_params"] / 1e9, "size_gb": r["model_size"] / 1e9,
        })
    return out


def powermetrics_path(rdir):
    """The run's trace: raw powermetrics.txt, or the .gz committed in its place (None if neither)."""
    for name in ("powermetrics.txt", "powermetrics.txt.gz"):
        if (rdir / name).exists():
            return rdir / name
    return None


def load_powermetrics(path):
    """[(start, end, combined_mW)] with sub-second times rebuilt from cumulative 'elapsed'."""
    heads, combined = [], []
    fh = gzip.open(path, "rt", errors="replace") if path.suffix == ".gz" else path.open(errors="replace")
    for line in fh:
        m = re.match(r"\*\*\* Sampled system activity \((.+?)\) \(([\d.]+)ms elapsed\)", line)
        if m:
            t = datetime.datetime.strptime(m.group(1), "%a %b %d %H:%M:%S %Y %z").timestamp()
            heads.append((t, float(m.group(2)) / 1000))
            combined.append(None)
            continue
        m = re.match(r"^Combined Power \(CPU \+ GPU \+ ANE\): (\d+) mW", line)
        if m and combined:
            combined[-1] = int(m.group(1))
    # Header times have 1 s resolution and mark the end of each sample. Within a run of
    # back-to-back samples, find the offset that puts every cumulative end time inside its
    # header's second, and take the middle. powermetrics stops while a Mac sleeps, so a header
    # jump much larger than its sample's elapsed time starts a new run with its own offset (a
    # single offset across a sleep misaligned a whole trace by over an hour).
    out, seg = [], []

    def flush():
        if not seg:
            return
        cum, ends = 0.0, []
        for _, dt, _ in seg:
            cum += dt
            ends.append(cum)
        lo = max(t - e for (t, _, _), e in zip(seg, ends))
        hi = min(t + 1 - e for (t, _, _), e in zip(seg, ends))
        off = (lo + hi) / 2
        out.extend((off + e - dt, off + e, mw) for (_, dt, mw), e in zip(seg, ends) if mw is not None)
        seg.clear()

    prev = None
    for (t, dt), mw in zip(heads, combined):
        if prev is not None and t - prev > dt + 2:
            flush()
        seg.append((t, dt, mw))
        prev = t
    flush()
    return out


def energy_j(samples, t0, t1, idle_mw):
    """Energy above idle in [t0, t1], each sample weighted by its overlap with the interval."""
    j = 0.0
    for s, e, mw in samples:
        ov = min(e, t1) - max(s, t0)
        if ov > 0:
            j += (mw - idle_mw) / 1000 * ov
    return j


def main():
    pdir = Path(sys.argv[1])
    run = sys.argv[2] if len(sys.argv) > 2 else (pdir / "LATEST").read_text().strip()
    rdir = pdir / run
    print(f"# {pdir.name} — run {run}\n")
    sysinfo = (rdir / "system.txt").read_text()
    print("```\n" + "\n".join(sysinfo.splitlines()[:3]) + "\n```\n")

    order = []
    for ln in (rdir / "bench.log").read_text().splitlines():
        if ln.startswith("== "):
            order.append(ln[3:].strip())

    if powermetrics_path(rdir):
        windows = {}
        for ln in (rdir / "windows.log").read_text().splitlines():
            label, s, e, _ = ln.split()
            windows[label] = (float(s.split("=")[1]), float(e.split("=")[1]))
        samples = load_powermetrics(powermetrics_path(rdir))
        idle = [w for k, w in windows.items() if k.startswith("idle")]
        idle_vals = [mw for s, e, mw in samples for (a, b) in idle if s >= a and e <= b]
        idle_mw = sum(idle_vals) / len(idle_vals)
        print(f"Idle (package): {idle_mw:.0f} mW over {len(idle_vals)} samples. Energy is above idle, per generated/processed token.\n")
        print("| Model | Params (B) | GB | Metal pp512 tok/s | Metal tg128 tok/s | CPU pp512 tok/s | CPU tg128 tok/s | Metal pp mJ/tok | Metal tg mJ/tok | CPU pp mJ/tok | CPU tg mJ/tok |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for name in order:
            row, epp = {}, {}
            for label, fname in (("metal-pp", f"llama-bench_metal-pp_{name}.json"), ("metal-tg", f"llama-bench_metal-tg_{name}.json"), ("cpu", f"llama-bench_cpu_{name}.json")):
                tests = load_bench(rdir / fname)
                end = windows[f"{label}_{name}"][1]
                # Tests ran in JSON order and the last one ends at the window end: walk back.
                t1 = end
                for t in reversed(tests):
                    t0 = t1 - t["busy_s"]
                    key = ("metal-" if label.startswith("metal") else "cpu-") + t["kind"]
                    row[key] = t
                    epp[key] = energy_j(samples, t0, t1, idle_mw) / t["tokens"] * 1000
                    t1 = t0
            any_t = next(iter(row.values()))
            f = lambda k: f"{row[k]['tps']:.1f}" if k in row else "–"
            g = lambda k: f"{epp[k]:.0f}" if k in epp else "–"
            print(f"| {name} | {any_t['params_b']:.2f} | {any_t['size_gb']:.2f} | {f('metal-pp')} | {f('metal-tg')} | {f('cpu-pp')} | {f('cpu-tg')} | {g('metal-pp')} | {g('metal-tg')} | {g('cpu-pp')} | {g('cpu-tg')} |")
    else:
        streams = {}
        for p in sorted(rdir.glob("stream_t*.txt")):
            m = re.search(r"^Triad:\s+([\d.]+)", p.read_text(), re.M)
            if m:
                streams[int(p.stem.removeprefix("stream_t"))] = float(m.group(1)) / 1000
        print("STREAM Triad GB/s by threads: " + ", ".join(f"t={t}: {v:.0f}" for t, v in sorted(streams.items())) + "\n")
        threads = sorted(streams)
        print("| Model | Params (B) | GB | " + " | ".join(f"pp512 t={t}" for t in threads) + " | " + " | ".join(f"tg128 t={t}" for t in threads) + " |")
        print("|---|---|---|" + "---|" * (2 * len(threads)))
        for name in order:
            p = rdir / f"llama-bench_{name}.json"
            tests = load_bench(p) if p.exists() else []
            if not tests:
                print(f"| {name} | – | – | " + " | ".join("–" for _ in range(2 * len(threads))) + " |")
                continue
            by = {(t["kind"], t["threads"]): t["tps"] for t in tests}
            cells = [f"{by[('pp', t)]:.1f}" if ('pp', t) in by else "–" for t in threads] + [f"{by[('tg', t)]:.1f}" if ('tg', t) in by else "–" for t in threads]
            print(f"| {name} | {tests[0]['params_b']:.2f} | {tests[0]['size_gb']:.2f} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
