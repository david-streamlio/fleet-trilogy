"""Summarize bench_realstream_m4max.sh's run: J/call above idle, latency, accuracy and the
prompt/generation split per session, with the same energy convention as the published
M4 Max row (summarize.energy_j over each session's window, idle = mean of the run's idle
windows, divided by the session's calls).

    python3 report_realstream.py <run-dir> [<powermetrics trace>]
"""
import json
import os
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "deploy/aws-phone-proxies/scripts"))
from summarize import energy_j, load_powermetrics, powermetrics_path  # noqa: E402

run = Path(sys.argv[1])
trace = Path(sys.argv[2]) if len(sys.argv) > 2 else powermetrics_path(run)
windows = {}
for line in (run / "windows.log").read_text().splitlines():
    label, start, end, _ = line.split()
    windows[label] = (float(start.split("=")[1]), float(end.split("=")[1]))
samples = load_powermetrics(trace)
idle = [mw for s, e, mw in samples for k, (a, b) in windows.items() if k.startswith("idle") and s >= a and e <= b]
idle_mw = st.mean(idle)
artifacts = {ln.split()[0]: ln.split()[1] for ln in (run / "artifacts.txt").read_text().splitlines() if len(ln.split()) > 1}

rows: dict[str, list[dict]] = {}
for label, (a, b) in windows.items():
    if label not in artifacts:
        continue
    path = run / artifacts[label]
    if not path.exists():
        path = REPO / "eval-results" / artifacts[label]
    model = next(iter(json.loads(path.read_text())["models"].values()))
    calls = model["latency"]["n"]
    energy = energy_j(samples, a, b, idle_mw)
    split = model.get("prompt_vs_generation") or {}
    rows.setdefault(label.rsplit("_r", 1)[0], []).append(
        {
            "j_per_call": energy / calls,
            "watts": energy / (b - a) + idle_mw / 1000,
            "p50": model["latency"]["p50_seconds"],
            "p95": model["latency"]["p95_seconds"],
            "format": model["format_reliability"]["rate"],
            "mismatch": model["escalation_calibration"].get("mismatch_rate"),
            "calls": calls,
            "prompt_tokens": split.get("median_prompt_tokens"),
            "evaluated": split.get("median_prompt_tokens_evaluated"),
            "prompt_ms": split.get("median_prompt_ms"),
            "generation_ms": split.get("median_generation_ms"),
        }
    )

print(f"Idle (package): {idle_mw:.0f} mW over {len(idle)} samples; {os.path.basename(trace)}\n")
print("| Session | Calls/rep | J/call above idle (range) | Avg W | p50 / p95 s | Format | Mismatch | Prompt tokens read / total (median) | Prompt ms / gen ms (median) |")
print("|---|---|---|---|---|---|---|---|---|")
for key, reps in rows.items():
    jc = [r["j_per_call"] for r in reps]
    mean = lambda field: st.mean(r[field] for r in reps)  # noqa: E731
    print(
        f"| {key} ({len(reps)} reps) | {reps[0]['calls']} | **{st.mean(jc):.1f}** ({min(jc):.1f}-{max(jc):.1f}) | "
        f"{mean('watts'):.1f} | {mean('p50'):.2f} / {mean('p95'):.2f} | {mean('format'):.0%} | {mean('mismatch'):.1%} | "
        f"{mean('evaluated'):.0f} / {mean('prompt_tokens'):.0f} | {mean('prompt_ms'):.0f} / {mean('generation_ms'):.0f} |"
    )
