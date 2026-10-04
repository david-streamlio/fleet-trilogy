#!/usr/bin/env python3
"""Round 3 report: every round-3 eval artifact behind the given run directories, as Markdown.

    round3_report.py [--trace PATH] <run-dir> [<run-dir> ...] > report.md

A run dir is any round-3-family directory with windows.log + artifacts.txt (bench_round3*.sh,
bench_budget*.sh, bench_ablation_m4max.sh, the thinkbudget4096 run). Its artifacts are found in
<platform>/C-artifacts/ (pulled from a host) or in the repo's eval-results/ (MacBook runs).

Energy per call = the session window's energy above idle (summarize.energy_j; idle = mean power
inside that run's idle-pre / idle-post / idle-gap windows, never cool-wait windows, which follow
hot sessions) / calls. It needs a powermetrics trace covering the window: the run dir's own
powermetrics.txt(.gz) (hosts), or --trace (the MacBook runs, recorded to /tmp by the operator).
A session the trace covers for less than 90% of its window gets no energy figure.

Sections: per-platform detail; narrow vs full (raw); thinking modes; the prompt ablation; and
cross-platform agreement, flagging cells whose 95% Wilson intervals don't overlap (accuracy
should not depend on hardware).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize import energy_j, load_powermetrics, powermetrics_path

REPO = Path(__file__).resolve().parents[3]
# The rates each task scores (round3_eval.score). An unparsed card scores only format_ok=False,
# so a key the task scores but a call lacks counts as a failure, not as not-applicable.
TASK_KEYS = {
    "narrow": ("all_ok", "format_ok", "escalation_ok"),
    "full": ("all_ok", "format_ok", "baseline_ok", "consistent", "escalation_ok", "severity_ok", "action_ok"),
}
MODE_ORDER = ("raw", "chat-off", "chat-on", "chat-budget")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def windows(run: Path) -> dict[str, tuple[float, float, str]]:
    out = {}
    for line in (run / "windows.log").read_text().splitlines():
        lab, s, e, rc = line.split()
        out[lab] = (float(s.split("=")[1]), float(e.split("=")[1]), rc)
    return out


def find_artifact(run: Path, name: str) -> Path | None:
    for p in (run.parent / "C-artifacts" / name, REPO / "eval-results" / name):
        if p.exists():
            return p
    return None


_TRACES: dict[Path, list] = {}
MISSING: list[str] = []


def samples_for(path: Path | None) -> list:
    """Load each trace once: the MacBook runs share one --trace of a few hundred MB."""
    if path is None:
        return []
    if path not in _TRACES:
        _TRACES[path] = load_powermetrics(path)
    return _TRACES[path]


def rows_for(run: Path, trace: Path | None) -> list[dict]:
    win = windows(run)
    samples = samples_for(powermetrics_path(run) or trace)
    idle = [mw for s, e, mw in samples for lab, (a, b, _) in win.items()
            if lab.startswith(("idle-pre", "idle-post", "idle-gap")) and s >= a and e <= b]
    idle_mw = st.mean(idle) if idle else None
    rows = []
    if not (run / "artifacts.txt").exists():  # still running, or stopped before its first session ended
        MISSING.append(f"{run.parent.name}/{run.name} (no artifacts.txt yet)")
        return []
    for line in (run / "artifacts.txt").read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        lab = parts[0]
        path = find_artifact(run, parts[1]) if len(parts) > 1 else None
        if path is None:
            MISSING.append(f"{run.parent.name}/{run.name}/{lab} ({parts[1] if len(parts) > 1 else 'no artifact written'})")
            continue
        art = json.loads(path.read_text())
        cfg, summ, calls = art["config"], art["summary"], art["calls"]
        n = len(calls)
        row = {
            # Every runner labels sessions round3_<model>_<task>_<mode>[...] or ablation_<model>_<variant>.
            "platform": run.parent.name, "run": run.name, "label": lab, "model": lab.split("_")[1],
            "task": cfg.get("task", "full"), "mode": cfg.get("variant") or cfg.get("mode"),
            "kind": "ablation" if "variant" in cfg else "round3", "n": n,
            "think_budget": cfg.get("think_budget", 0),
            "p50": summ.get("latency_p50_seconds"), "p95": summ.get("latency_p95_seconds"),
            "tokens": summ.get("tokens_predicted_mean"), "think": summ.get("think_tokens_mean"),
            "prompt_tokens": sum(c.get("tokens_evaluated", 0) for c in calls) / n if n else None,
            "truncated": summ.get("truncated", 0), "errors": summ.get("errors", 0),
            "forced": sum(1 for c in calls if c.get("think_forced")),
            "exit": win.get(lab, (0, 0, "?"))[2],
        }
        keys = TASK_KEYS[row["task"]] + (("facts_ok",) if any("facts_ok" in c["scores"] for c in calls) else ())
        for k in keys:
            row[k] = sum(1 for c in calls if c["scores"].get(k))
        row["joules_per_call"] = None
        if lab in win and samples and idle_mw is not None and n:
            a, b, _ = win[lab]
            covered = sum(max(0.0, min(e, b) - max(s, a)) for s, e, _ in samples)
            if covered >= 0.9 * (b - a):
                row["joules_per_call"] = energy_j(samples, a, b, idle_mw) / n
        rows.append(row)
    return rows


def pct(r: dict, k: str) -> str:
    return "–" if k not in r else f"{100 * r[k] / r['n']:.0f}%"


def ci(r: dict, k: str = "all_ok") -> str:
    if k not in r:
        return "–"
    lo, hi = wilson(r[k], r["n"])
    return f"{100 * r[k] / r['n']:.0f}% [{100 * lo:.0f}-{100 * hi:.0f}]"


def f(v, fmt: str = "{:.2f}") -> str:
    return "–" if v is None else fmt.format(v)


def mode_key(r: dict) -> tuple:
    return (MODE_ORDER.index(r["mode"]) if r["mode"] in MODE_ORDER else 99, r["think_budget"])


def mode_label(r: dict) -> str:
    return f"{r['mode']} ({r['think_budget']})" if r["mode"] in ("chat-on", "chat-budget") else r["mode"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--trace", type=Path, default=None, help="powermetrics trace for runs without their own (MacBook)")
    a = ap.parse_args()
    rows = [r for run in a.runs for r in rows_for(run, a.trace)]
    r3 = [r for r in rows if r["kind"] == "round3"]
    ab = [r for r in rows if r["kind"] == "ablation"]

    print("# Round 3 report\n")
    print("Runs: " + ", ".join(f"`{p.parent.name}/{p.name}`" + (" (**ABORTED**)" if (p / "ABORTED.txt").exists() else "")
                               for p in a.runs) + "\n")
    print("Rates are per call; `all_ok` carries a 95% Wilson interval. J/call is energy above idle per call, the session window included (an upper bound). `–` = not applicable or no trace.\n")

    print("## 1. Per platform\n")
    for plat in sorted({r["platform"] for r in r3}):
        print(f"### {plat}\n")
        print("| Model | Task | Mode | n | all_ok [95% CI] | baseline | consistent | escalation | format | p50 s | p95 s | out tok | think tok | trunc | J/call |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted((r for r in r3 if r["platform"] == plat), key=lambda r: (r["model"], r["task"], mode_key(r))):
            print(f"| {r['model']} | {r['task']} | {mode_label(r)} | {r['n']} | {ci(r)} | {pct(r, 'baseline_ok')} | {pct(r, 'consistent')} | "
                  f"{pct(r, 'escalation_ok')} | {pct(r, 'format_ok')} | {f(r['p50'])} | {f(r['p95'])} | {f(r['tokens'], '{:.0f}')} | "
                  f"{f(r['think'], '{:.0f}')} | {r['truncated']} | {f(r['joules_per_call'], '{:.1f}')} |")
        print()

    plats = sorted({r["platform"] for r in r3})
    print("## 2. Narrow vs full task (raw mode, the production prompt path): all_ok\n")
    print("| Model | " + " | ".join(f"{p} narrow | {p} full" for p in plats) + " |")
    print("|---|" + "---|---|" * len(plats))
    for m in sorted({r["model"] for r in r3}):
        cells = []
        for p in plats:
            for t in ("narrow", "full"):
                hit = [r for r in r3 if (r["model"], r["platform"], r["task"], r["mode"]) == (m, p, t, "raw")]
                cells.append(ci(hit[0]) if hit else "–")
        print(f"| {m} | " + " | ".join(cells) + " |")
    print()

    print("## 3. Thinking: chat format, off / on / budget-forced (Qwen models)\n")
    print("| Platform | Model | Task | Mode | all_ok [95% CI] | p50 s | think tok | truncated | forced | J/call |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted((r for r in r3 if r["mode"] != "raw"), key=lambda r: (r["model"], r["task"], r["platform"], mode_key(r))):
        print(f"| {r['platform']} | {r['model']} | {r['task']} | {mode_label(r)} | {ci(r)} | {f(r['p50'])} | {f(r['think'], '{:.0f}')} | "
              f"{r['truncated']} | {r['forced']} | {f(r['joules_per_call'], '{:.1f}')} |")
    print()

    if ab:
        print("## 4. Prompt ablation (full task)\n")
        print("| Platform | Model | Variant | all_ok [95% CI] | facts | baseline | consistent | escalation | prompt tok | p50 s | J/call |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        order = ["base", "facts", "tables", "template", "examples", "temp0", "grammar"]
        for r in sorted(ab, key=lambda r: (r["platform"], r["model"], order.index(r["mode"]) if r["mode"] in order else 99)):
            print(f"| {r['platform']} | {r['model']} | {r['mode']} | {ci(r)} | {pct(r, 'facts_ok')} | {pct(r, 'baseline_ok')} | "
                  f"{pct(r, 'consistent')} | {pct(r, 'escalation_ok')} | {f(r['prompt_tokens'], '{:.0f}')} | {f(r['p50'])} | "
                  f"{f(r['joules_per_call'], '{:.1f}')} |")
        print()

    print("## 5. Cross-platform agreement (accuracy should not depend on hardware)\n")
    if len(plats) < 2:
        print("Needs runs from at least two platforms.\n")
    else:
        print("| Model | Task | Mode | " + " | ".join(plats) + " | intervals overlap |")
        print("|---|---|---|" + "---|" * len(plats) + "---|")
        cells = {}
        for r in r3:
            cells.setdefault((r["model"], r["task"], mode_label(r)), {})[r["platform"]] = r
        for key, by in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1], mode_key(next(iter(kv[1].values()))))):
            if len(by) < 2:
                continue
            ivs = [wilson(r["all_ok"], r["n"]) for r in by.values()]
            overlap = max(lo for lo, _ in ivs) <= min(hi for _, hi in ivs)
            print(f"| {key[0]} | {key[1]} | {key[2]} | " + " | ".join(ci(by[p]) if p in by else "–" for p in plats)
                  + f" | {'yes' if overlap else '**no**'} |")
        print()
    bad = [r for r in rows if r["exit"] not in ("exit=0", "?")]
    if bad:
        print("**Sessions with a non-zero exit:** " + ", ".join(f"{r['platform']}/{r['label']} ({r['exit']})" for r in bad) + "\n")
    if MISSING:
        print("**Sessions without an artifact (not in the tables):** " + ", ".join(MISSING) + "\n")


if __name__ == "__main__":
    main()
