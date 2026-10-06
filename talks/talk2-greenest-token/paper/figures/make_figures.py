#!/usr/bin/env python3
"""Figures for the Talk 2 paper (main.tex) and its web edition, from the study's raw data.

    uv run --no-project --with matplotlib==3.11.2 python talks/talk2-greenest-token/paper/figures/make_figures.py [--slides]

(an ephemeral environment: the project's own venv, which the benchmarks import, is untouched).
Writes fig<N>_<name>.{pdf,svg,png} next to this file: PDF for LaTeX (fonts embedded), SVG with text as
paths for the web edition, PNG at 300 dpi for slides.

Sources, per figure:
  1 speed     Phase 1 llama-bench JSONs (c7g X1 build = L2, c9g, M1 and M4 Metal); iPhone 17 Pro
              points are published figures (apple-silicon-llm-bench, [verify] in the paper).
  2 energy    (a) per-decision energy: test log / impact track (Pi 4 inline meter, row 24; test C on
              M1 and M4; M4 Max row 24), entered below with their sources; (b) M1 per-token energy,
              recomputed from the Phase 1 trace with summarize.py's loaders and windowing.
  3 thinking  round-3 eval artifacts via round3_report.rows_for (clustered intervals), M4 Max round-3 run
              plus its budget-forcing run (capped points).
  4 energy/day impact track row 28 (calls per incident, uplink sizes, radio energy) and the
              per-call energies of figure 2a.
  5 task scope round-3 eval artifacts (raw mode, narrow vs full), M4 Max run; clustered intervals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PP = REPO / "eval-results" / "phone-proxies"
sys.path.insert(0, str(REPO / "deploy" / "aws-phone-proxies" / "scripts"))
from round3_report import rows_for, wilson  # noqa: E402
from summarize import energy_j, load_bench, load_powermetrics, powermetrics_path  # noqa: E402

# IEEE single column: 3.5 in wide, Times-like type at 8 pt.
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.0,
    "pdf.fonttype": 42, "svg.fonttype": "path", "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})
W = 3.5
# Okabe-Ito, one color per platform across all figures (colorblind-safe; markers differ too).
PLAT = {
    "pi4": ("Raspberry Pi 4 (CPU)", "#D55E00", "s"),
    "c7g": ("Android mainstream proxy (c7g CPU)", "#999999", "^"),
    "c9g": ("Android flagship proxy (c9g CPU)", "#56B4E9", "D"),
    "m1": ("Apple M1 GPU", "#0072B2", "o"),
    "m4": ("Apple M4 GPU", "#009E73", "P"),
    "m4max": ("Apple M4 Max GPU", "#CC79A7", "X"),
}

# Paper by default; `--slides` writes slide editions to talks/talk2-greenest-token/slides/charts/ (slide_*.png/svg):
# a 16:9-friendly canvas, sans-serif type at slide sizes, and the DATADOG_MARKETING_DECK accent palette
# (Roboto isn't installed here, so Helvetica Neue stands in; the slide plan carries every chart's data if
# the design tool prefers to redraw natively).
SLIDES = "--slides" in sys.argv
OUT, PREFIX = HERE, ""
K, KL, FS = 1.0, 1.0, 1.0  # marker area, line/marker length, annotation font scales
C = {"prompt": "#0072B2", "gen": "#E69F00", "q1": "#0072B2", "q2": "#009E73", "q3": "#D55E00", "q4": "#CC79A7",
     "narrow": "#0072B2", "full": "#D55E00"}


def H(h: float) -> float:
    return h


if SLIDES:
    OUT, PREFIX = REPO / "talks/talk2-greenest-token/slides/charts", "slide_"
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 17, "axes.titlesize": 17, "axes.labelsize": 17, "xtick.labelsize": 15, "ytick.labelsize": 15,
        "legend.fontsize": 14, "axes.linewidth": 1.2, "xtick.major.width": 1.2, "ytick.major.width": 1.2,
        "lines.linewidth": 2.0, "savefig.pad_inches": 0.12,
    })
    W, K, KL, FS = 11.0, 3.2, 1.8, 2.2

    def H(h: float) -> float:  # noqa: F811
        return h * 2.15

    PLAT = {
        "pi4": ("Raspberry Pi 4 (CPU)", "#FF5E00", "s"),
        "c7g": ("Android mainstream proxy (c7g CPU)", "#00CAFF", "^"),
        "c9g": ("Android flagship proxy (c9g CPU)", "#0060FF", "D"),
        "m1": ("Apple M1 GPU", "#5C00EF", "o"),
        "m4": ("Apple M4 GPU", "#00B765", "P"),
        "m4max": ("Apple M4 Max GPU", "#FF0080", "X"),
    }
    C = {"prompt": "#5C00EF", "gen": "#FF9B00", "q1": "#0060FF", "q2": "#00B765", "q3": "#FF5E00", "q4": "#D32D96",
         "narrow": "#5C00EF", "full": "#FF5E00"}


def save(fig, name: str) -> None:
    for ext in (("svg",) if SLIDES else ("pdf", "svg")):
        fig.savefig(OUT / f"{PREFIX}{name}.{ext}")
    fig.savefig(OUT / f"{PREFIX}{name}.png", dpi=200 if SLIDES else 300)
    plt.close(fig)
    print("wrote", PREFIX + name)


# --- Figure 1: generation speed across the spectrum -------------------------------------------
def tg(path: Path, threads: int | None = None) -> float | None:
    if not path.exists():
        return None
    for t in load_bench(path):
        if t["kind"] == "tg" and (threads is None or t["threads"] == threads):
            return t["tps"]
    return None


def fig1() -> None:
    models = [("Qwen3.5-2B-Q4_K_M", "Qwen3.5-2B"), ("gemma-4-E2B-it-Q4_K_M", "Gemma-4-E2B"),
              ("gemma-3-4b-it-Q4_K_M", "Gemma-3-4B"), ("Phi-3.5-mini-instruct-Q4_K_M", "Phi-3.5-mini (3.8B)"),
              ("Llama-3.1-8B-Instruct-Q4_K_M", "Llama-3.1-8B")]
    src = {
        "c7g": lambda n: tg(PP / "android-mainstream/L2-phone-isa-x1-20261003T210854Z" / f"llama-bench_{n}.json", 8),
        "c9g": lambda n: tg(PP / "android-flagship/20261003T184418Z" / f"llama-bench_{n}.json", 8),
        "m1": lambda n: tg(PP / "iphone-older/20261003T191829Z" / f"llama-bench_metal-tg_{n}.json"),
        "m4": lambda n: tg(PP / "iphone-flagship/20261004T045158Z" / f"llama-bench_metal-tg_{n}.json"),
    }
    iphone = {"Qwen3.5-2B-Q4_K_M": 39.1, "gemma-4-E2B-it-Q4_K_M": 38.8}
    fig, ax = plt.subplots(figsize=(W, H(2.9)))
    ys = list(range(len(models)))[::-1]
    offs = {k: (i - 1.5) * 0.15 for i, k in enumerate(src)}
    for k, get in src.items():
        label, color, marker = PLAT[k]
        xs, yy = [], []
        for (n, _), y in zip(models, ys):
            v = get(n)
            if v:
                xs.append(v); yy.append(y + offs[k])
        ax.scatter(xs, yy, s=16 * K, color=color, marker=marker, label=label, zorder=3, edgecolors="none")
    ix = [(iphone[n], y) for (n, _), y in zip(models, ys) if n in iphone]
    ax.scatter([v for v, _ in ix], [y for _, y in ix], s=34 * K, facecolors="none", edgecolors="black",
               marker="o", linewidths=0.9 * KL, label="iPhone 17 Pro (published)", zorder=4)
    ax.set_yticks(ys, [lab for _, lab in models])
    ax.set_xlabel("Generation speed, tg128 (tokens/s)")
    ax.set_xlim(0, None)
    ax.grid(axis="x", linewidth=0.4, alpha=0.4)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.2), ncol=2, frameon=False, handletextpad=0.3, columnspacing=0.8)
    save(fig, "fig1_speed")


# --- Figure 2: energy per decision, and CPU vs GPU on one chip ---------------------------------
def m1_energy_per_token(names: list[str]) -> dict[str, dict[str, float]]:
    """mJ/token above idle on the M1, Phase 1 run; the same windowing as summarize.py (llama-bench
    tests ran in JSON order and the last ends at its window's end, so walk back by busy time)."""
    rdir = PP / "iphone-older/20261003T191829Z"
    windows = {}
    for ln in (rdir / "windows.log").read_text().splitlines():
        lab, s, e, _ = ln.split()
        windows[lab] = (float(s.split("=")[1]), float(e.split("=")[1]))
    samples = load_powermetrics(powermetrics_path(rdir))
    idle = [mw for s, e, mw in samples for k, (a, b) in windows.items() if k.startswith("idle") and s >= a and e <= b]
    idle_mw = sum(idle) / len(idle)
    out = {}
    for n in names:
        epp = {}
        for label in ("metal-pp", "metal-tg", "cpu"):
            tests = load_bench(rdir / f"llama-bench_{label}_{n}.json")
            t1 = windows[f"{label}_{n}"][1]
            for t in reversed(tests):
                t0 = t1 - t["busy_s"]
                key = ("gpu-" if label.startswith("metal") else "cpu-") + t["kind"]
                epp[key] = energy_j(samples, t0, t1, idle_mw) / t["tokens"] * 1000
                t1 = t0
        out[n] = epp
    return out


def fig2() -> None:
    # (a) Phi-3.5-mini on the Edge Triage Pipeline: p50 latency (s) and energy above idle per call (J).
    # Pi 4: inline USB-C meter, whole board at the wall (impact track rows 24, 26). M1, M4: test C
    # (test log, round 2 headline table). M4 Max: impact track row 24 (chip, upper bound).
    per_call = [("pi4", 31.7, 154.0), ("m1", 1.91, 20.0), ("m4", 1.18, 15.2), ("m4max", 0.36, 15.3)]
    names = [("Qwen3.5-2B-Q4_K_M", "Qwen3.5-2B"), ("Phi-3.5-mini-instruct-Q4_K_M", "Phi-3.5"),
             ("gemma-3-4b-it-Q4_K_M", "Gemma-3-4B"), ("Llama-3.1-8B-Instruct-Q4_K_M", "Llama-3.1-8B")]
    e = m1_energy_per_token([n for n, _ in names])

    fig, (a, b) = plt.subplots(1, 2, figsize=(W, H(1.9)), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.55})
    for k, lat, j in per_call:
        label, color, marker = PLAT[k]
        a.scatter(lat, j, s=26 * K, color=color, marker=marker, zorder=3, edgecolors="none")
        short = {"pi4": "Pi 4\n(CPU, wall)", "m1": "M1", "m4": "M4", "m4max": "M4 Max"}[k]
        dx, dy, ha = {"pi4": (0.8, 1.0, "right"), "m1": (1.3, 1.08, "left"), "m4": (1.3, 0.8, "left"), "m4max": (1.0, 1.32, "center")}[k]
        a.annotate(short, (lat * dx, j * dy), fontsize=6.5 * FS, ha=ha, va="center")
    a.set_xscale("log"); a.set_yscale("log")
    a.set_xlim(0.2, 60); a.set_ylim(8, 300)
    a.set_xticks([0.3, 1, 3, 10, 30], ["0.3", "1", "3", "10", "30"])
    a.set_yticks([10, 30, 100, 300], ["10", "30", "100", "300"])
    a.minorticks_off()
    a.set_xlabel("Median latency per call (s)")
    a.set_ylabel("Energy per call (J)")
    a.set_title("(a) One triage decision, Phi-3.5", loc="left")
    a.grid(linewidth=0.4, alpha=0.4, which="major")

    x = range(len(names)); wbar = 0.2
    series = [("gpu-pp", "GPU, prompt", C["prompt"], None), ("cpu-pp", "CPU, prompt", C["prompt"], "////"),
              ("gpu-tg", "GPU, generate", C["gen"], None), ("cpu-tg", "CPU, generate", C["gen"], "////")]
    for i, (key, lab, color, hatch) in enumerate(series):
        vals = [e[n][key] for n, _ in names]
        b.bar([xi + (i - 1.5) * wbar for xi in x], vals, wbar, label=lab,
              color="white" if hatch else color, edgecolor=color, hatch=hatch, linewidth=0.6 * KL)
    b.set_xticks(list(x), [lab for _, lab in names], rotation=30, ha="right")
    b.set_ylabel("Energy per token (mJ)")
    b.set_title("(b) Same chip (M1), CPU vs GPU", loc="left")
    b.legend(frameon=False, ncol=1, loc="upper left", handlelength=1.2)
    b.grid(axis="y", linewidth=0.4, alpha=0.4)
    save(fig, "fig2_energy")


# --- Figure 3: what reasoning buys, round 3 full task --------------------------------------------
def fig3() -> None:
    run = PP / "m4max-macbook/20261004T153710Z-round3"
    rows = [r for r in rows_for(run, None) if r["task"] == "full"]
    budget = [r for r in rows_for(PP / "m4max-macbook/20261004T225651Z-round3-budget", None) if r["task"] == "full"]
    qwen = [("qwen3-8b", "Qwen3-8B", C["q1"]), ("qwen3-14b", "Qwen3-14B", C["q2"]),
            ("qwen3.5-9b", "Qwen3.5-9B", C["q3"]), ("qwen3.8-27b", "Qwen3.8-27B", C["q4"])]
    modes = [("raw", "s", "raw (production)"), ("chat-off", "o", "chat format, thinking off"), ("chat-on", "^", "thinking on (2,048 tokens)")]
    fig, ax = plt.subplots(figsize=(W, H(2.5)))
    for m, label, color in qwen:
        pts = []
        for mode, marker, _ in modes:
            r = next((r for r in rows if r["model"] == m and r["mode"] == mode), None)
            # Qwen3.5-9B's thinking-on run is a harness artifact, not a measurement: the thinking
            # grammar (think ::= [^<]*) closed the thought at the first "<" the model wrote, then it
            # emitted whitespace to the limit, so 32 of 36 calls had no card (test log incident 27).
            if not r or (m == "qwen3.5-9b" and mode == "chat-on"):
                continue
            p = r["all_ok"] / r["n"]
            lo, hi = wilson(p * r["n_eff"], r["n_eff"])
            pts.append((r["p50"], 100 * p))
            ax.errorbar(r["p50"], 100 * p, yerr=[[100 * (p - lo)], [100 * (hi - p)]], fmt=marker, color=color,
                        ms=4.5 * KL, elinewidth=0.6 * KL, capsize=1.5 * KL, zorder=3)
        ax.plot([x for x, _ in pts], [y for _, y in pts], color=color, linewidth=0.7 * KL, alpha=0.6, zorder=2)
        # Qwen3.5-9B's last point is now its chat-off one, which sits beside Qwen3-14B's: label it to the left.
        offset, ha = ((-6, 0), "right") if m == "qwen3.5-9b" else ((4, 0), "left")
        ax.annotate(label, pts[-1], xytext=offset, textcoords="offset points", fontsize=6.5 * FS, color=color,
                    va="center", ha=ha)
        rb = next((r for r in budget if r["model"] == m), None)  # thinking capped at 1,024 tokens (budget forcing)
        off = next((r for r in rows if r["model"] == m and r["mode"] == "chat-off"), None)
        if rb and off:
            p = rb["all_ok"] / rb["n"]
            lo, hi = wilson(p * rb["n_eff"], rb["n_eff"])
            ax.errorbar(rb["p50"], 100 * p, yerr=[[100 * (p - lo)], [100 * (hi - p)]], fmt="D", color=color, mfc="white",
                        ms=4.0 * KL, elinewidth=0.6 * KL, capsize=1.5 * KL, zorder=3)
            ax.plot([off["p50"], rb["p50"]], [100 * off["all_ok"] / off["n"], 100 * p], color=color,
                    linewidth=0.7 * KL, alpha=0.6, linestyle=(0, (2, 2)), zorder=2)
    for mode, marker, lab in modes:
        ax.plot([], [], marker, color="black", ms=4 * KL, label=lab)
    ax.plot([], [], "D", color="black", mfc="white", ms=4 * KL, label="thinking capped (1,024 tokens)")
    ax.set_xscale("log")
    ax.set_xlim(0.9, 200)
    ax.set_ylim(-5, 100)
    ax.set_xlabel("Median latency per call (s), M4 Max")
    ax.set_ylabel("Correct end to end (%)")
    ax.set_xticks([1, 3, 10, 30, 100], ["1", "3", "10", "30", "100"])
    ax.minorticks_off()
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, handletextpad=0.2, columnspacing=0.8)
    ax.grid(linewidth=0.4, alpha=0.4)
    save(fig, "fig3_thinking")


# --- Figure 4: where the energy goes: calls x joules per call ------------------------------------
def fig4() -> None:
    events_per_day = 24 * 3600 // 5  # one telemetry event every 5 s: 17,280
    calls_per_incident = 23           # row 28: 17-28 LLM calls per incident, mean 21.6-24.2
    policies = [("Every event\n(no gate)", events_per_day), ("Gated,\n1 incident/day", calls_per_incident), ("Once per\nincident", 1)]
    devices = [("pi4", 154.0), ("m1", 20.0), ("m4max", 15.3)]
    fig, ax = plt.subplots(figsize=(W, H(2.6)))
    wbar = 0.24
    for i, (k, j) in enumerate(devices):
        label, color, _ = PLAT[k]
        xs = [p + (i - 1) * wbar for p in range(len(policies))]
        vals = [calls * j / 1000 for _, calls in policies]
        bars = ax.bar(xs, vals, wbar, color=color, linewidth=0)
        ax.bar([], [], color=color, label=label)  # solid legend swatch (the first Pi bar is hatched)
        if k == "pi4":  # 31.7 s per call can't keep up with an event every 5 s
            bars[0].set_hatch("////"); bars[0].set_edgecolor("white")
    refs = [(294, "Pi 4 idle, 24 h (294 kJ)"), (92, "Streaming, 2012 LTE radio (92 kJ)"), (2.5, "Streaming, LTE-M modem (2.5 kJ)")]
    for v, lab in refs:
        ax.axhline(v, color="black", linewidth=0.5 * KL, linestyle=(0, (3, 2)), zorder=1)
        ax.annotate(lab, (2.45, v), xytext=(0, 1.5), textcoords="offset points", fontsize=6 * FS, ha="right", va="bottom")
    ax.set_yscale("log")
    ax.set_ylim(0.01, 5000)
    ax.set_xticks(range(len(policies)), [p for p, _ in policies])
    ax.set_ylabel("LLM energy per truck-day (kJ)")
    ax.set_yticks([0.01, 0.1, 1, 10, 100, 1000], ["0.01", "0.1", "1", "10", "100", "1,000"])
    ax.minorticks_off()
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3, handlelength=1.0, columnspacing=0.8)
    ax.grid(axis="y", linewidth=0.4, alpha=0.3, which="major")
    save(fig, "fig4_energy_per_day")


# --- Figure 5: one bounded judgment vs the whole job (round 3, raw mode) -------------------------
def fig5() -> None:
    run = PP / "m4max-macbook/20261004T153710Z-round3"
    rows = [r for r in rows_for(run, None) if r["mode"] == "raw"]
    models = [("phi-3.5-mini", "Phi-3.5-mini"), ("gemma-3-4b", "Gemma-3-4B"), ("llama-3.1-8b", "Llama-3.1-8B"),
              ("glm-4-9b", "GLM-4-9B"), ("qwen3-8b", "Qwen3-8B"), ("gemma-3-12b", "Gemma-3-12B"),
              ("gemma-4-12b", "Gemma-4-12B"), ("qwen3-14b", "Qwen3-14B")]
    fig, ax = plt.subplots(figsize=(W, H(2.3)))
    wbar = 0.38
    for i, (task, label, color) in enumerate([("narrow", "One bounded judgment (production)", C["narrow"]), ("full", "The whole job in one call", C["full"])]):
        xs, ys, lo_e, hi_e = [], [], [], []
        for j, (m, _) in enumerate(models):
            r = next((r for r in rows if r["model"] == m and r["task"] == task), None)
            if not r:
                continue
            p = r["all_ok"] / r["n"]
            lo, hi = wilson(p * r["n_eff"], r["n_eff"])
            xs.append(j + (i - 0.5) * wbar); ys.append(100 * p); lo_e.append(100 * (p - lo)); hi_e.append(100 * (hi - p))
        ax.bar(xs, ys, wbar, color=color, label=label, linewidth=0)
        ax.errorbar(xs, ys, yerr=[lo_e, hi_e], fmt="none", ecolor="black", elinewidth=0.5 * KL, capsize=1.2 * KL)
    ax.set_xticks(range(len(models)), [lab for _, lab in models], rotation=35, ha="right")
    ax.set_ylabel("Correct end to end (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=2, handlelength=1.0)
    ax.grid(axis="y", linewidth=0.4, alpha=0.4)
    save(fig, "fig5_task_scope")


# --- Slide 7: the dice question (probability, not study data) -----------------------------------
def fig_dice() -> None:
    sums = list(range(2, 13))
    expected = [100 * (6 - abs(7 - k)) / 36 for k in sums]  # expected count per sum in 100 rolls of two dice
    fig, ax = plt.subplots(figsize=(W, H(2.2)))
    colors = [C["narrow"] if k == 7 else "#C9CFD7" for k in sums]
    ax.bar(sums, expected, 0.7, color=colors, linewidth=0)
    for k, v in zip(sums, expected):
        ax.annotate(f"{v:.1f}", (k, v), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=6 * FS)
    ax.annotate("7: about 17 times; anywhere from ~10 to 24 is normal", (7, 16.7), xytext=(40, -6),
                textcoords="offset points", fontsize=6.5 * FS, ha="left", va="center", color=C["narrow"])
    ax.set_xticks(sums)
    ax.set_xlabel("Sum of two six-sided dice")
    ax.set_ylabel("Expected count in 100 rolls")
    ax.set_ylim(0, 21)
    ax.grid(axis="y", linewidth=0.4, alpha=0.3)
    save(fig, "dice")


# --- Slide 19: a repeated prompt vs a changed one (the paper's Table IV) -------------------------
def fig_changed_prompt() -> None:
    # Phi-3.5-mini, Edge Triage, J/call above idle and p50. Pi 4: inline meter, whole board
    # (eval-results/edge-triage-event-last-pi4-20261005/: runs A and B; repeated = Table II).
    # M4 Max: powermetrics, chip only (eval-results/edge-triage-event-last-m4max-20261005/,
    # run 2; repeated = Table II's ~15 J).
    cases = ["Repeated\nprompt", "Changed,\nas built", "Changed,\nfields last"]
    colors = ["#C9CFD7", C["full"], C["narrow"]]
    # Inside each changed bar: as built vs repeated, fields last vs as built.
    panels = [
        ("Raspberry Pi 4 (CPU, at the wall)", [154, 772, 416], ["154 J · 31.7 s", "772 J · 160 s", "416 J · 82 s"], "5×", "−46%"),
        ("M4 Max (GPU, chip only)", [15.2, 25.0, 18.5], ["~15 J · 0.36 s", "25.0 J · 0.70 s", "18.5 J · 0.49 s"], "1.6×", "−26%"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(W, H(2.3)))
    for ax, (title, vals, labels, ratio, saving) in zip(axes, panels):
        ax.bar(range(3), vals, 0.62, color=colors, linewidth=0)
        for x, (v, lab) in enumerate(zip(vals, labels)):
            ax.annotate(lab, (x, v), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=6.5 * FS)
        for x, text in ((1, ratio), (2, saving)):
            ax.annotate(text, (x, vals[x] * 0.5), ha="center", va="center", fontsize=9 * FS, fontweight="bold", color="white")
        ax.set_xticks(range(3), cases)
        ax.set_ylim(0, max(vals) * 1.22)
        ax.set_title(title, loc="left")
        ax.set_ylabel("Energy per call above idle (J)")
        ax.grid(axis="y", linewidth=0.4, alpha=0.3)
    fig.tight_layout(w_pad=2.0)
    save(fig, "changed_prompt")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
    if SLIDES:
        fig_dice()
        fig_changed_prompt()
