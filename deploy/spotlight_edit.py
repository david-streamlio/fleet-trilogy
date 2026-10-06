#!/usr/bin/env python3
"""deploy/spotlight_edit.py -- the spotlight edit for deploy/record-demo.sh.

Takes the four per-window clips of one take (telemetry, coprocessor output, uplink,
local-only) and composes one 1920x1080 video that shows one terminal at a time, full
frame, switching to a window when it prints a new message:

- Switch times come from the take's event log: every deploy/windows/*.sh appends
  "epoch<TAB>role<TAB>truck_id<TAB>summary" as it prints a message (EVENT_LOG).
- Each shown window is held at least --hold seconds of OUTPUT time (after the
  --speed speed-up) before another switch. When several windows have new messages,
  an uplinked card goes first (the climax, and rare), then the next window in
  pipeline order (telemetry -> co-processor -> uplink -> local-only), with
  telemetry last; no window appears before the stage feeding it has been shown.
- A --fade second cross-fade (output time) between windows, and a stage label in the
  top-left corner ("1 · Telemetry" ...), rendered by macOS (this Homebrew ffmpeg has
  no drawtext) and overlaid.
- The speed-up is applied after the composition (setpts=PTS/N), so the hold rule is
  measured in output time.
- A sidecar .txt lists every switch as "mm:ss  stage  truck_id  summary".

Clips are aligned on wall-clock time: each clip's first frame is its stop time minus
its duration (screencapture starts with a variable lag, so its launch time isn't).
That needs every clip to run to its stop: screencapture's video is variable-frame-rate
and ends at the window's last changed frame, so the window scripts' HEARTBEAT keeps
changing each title bar (cropped out here) 4 times a second.

    python3 deploy/spotlight_edit.py --events EVENTS.tsv --output OUT.mp4 \
        --clip telemetry=RAW.mov:STOP_EPOCH:WINDOW_HEIGHT_PT ... (all four roles) \
        [--title-bar 32] [--speed 4] [--hold 3] [--fade 0.3]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Pipeline order, and the label burned into the frame for each window.
STAGES = [
    ("telemetry", "1 · Telemetry"),
    ("coproc-out", "2 · Co-processor"),
    ("uplink", "3 · LLM → uplink"),
    ("local-only", "4 · Stays on truck"),
]
ROLES = [role for role, _ in STAGES]
LABELS = dict(STAGES)
FRAME_W, FRAME_H = 1920, 1080
LABEL_FONT_PX = 40
LABEL_BAND = 96  # px at the top of the frame for the stage label, clear of the terminal
LABEL_XY = (36, 10)


@dataclass
class Clip:
    role: str
    path: Path
    stop: float  # wall-clock epoch when recording stopped
    window_h_pt: float  # the window's height in points (for the title-bar crop)
    duration: float = 0.0
    width: int = 0
    height: int = 0

    @property
    def first(self) -> float:
        return self.stop - self.duration


@dataclass
class Event:
    t: float
    role: str
    truck_id: str
    summary: str


@dataclass
class Segment:
    role: str
    start: float
    end: float
    trigger: Event | None


def probe(clip: Clip) -> None:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(clip.path)],
        check=True, capture_output=True, text=True,
    ).stdout
    info = json.loads(out)
    clip.duration = float(info["format"]["duration"])
    clip.width = int(info["streams"][0]["width"])
    clip.height = int(info["streams"][0]["height"])


def read_events(path: Path) -> list[Event]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[1] in ROLES:
            events.append(Event(float(parts[0]), parts[1], parts[2], parts[3]))
    return sorted(events, key=lambda e: e.t)


def plan(events: list[Event], start: float, end: float, hold_in: float) -> list[Segment]:
    """Switch to a window when it has a new message, holding each one hold_in
    seconds of input time; ties go to the next window in pipeline order."""
    events = [e for e in events if start <= e.t <= end]
    if not events:
        return [Segment("telemetry", start, end, None)]
    cur = events[0].role
    seg_start = start
    trigger = events[0]
    shown_until = {role: -1.0 for role in ROLES}
    segments: list[Segment] = []
    # Causality: a window can't appear before the stage feeding it has been shown
    # (the LLM windows after the co-processor, the co-processor after telemetry), or
    # an early uplinked card would show the decision before the flag behind it.
    upstream = {"telemetry": None, "coproc-out": "telemetry", "uplink": "coproc-out", "local-only": "coproc-out"}
    shown = {cur}

    def fresh_roles(at: float) -> dict[str, int]:
        """Windows other than the current one with unseen messages, and how many."""
        counts: dict[str, int] = {}
        for e in events:
            if e.role != cur and shown_until[e.role] < e.t <= at:
                counts[e.role] = counts.get(e.role, 0) + 1
        return counts

    def next_in_order(cands: dict[str, int]) -> str:
        # An uplinked card pre-empts: it's the story's climax and rare (a take's only
        # one was otherwise skipped for telemetry). Then pipeline order from the
        # current window, with telemetry last, so the edit doesn't go back to raw
        # telemetry while a downstream window has news.
        i = ROLES.index(cur)
        order = {ROLES[(i + k) % len(ROLES)]: k for k in range(1, len(ROLES) + 1)}
        eligible = [r for r in cands if upstream[r] is None or upstream[r] in shown] or list(cands)
        return min(eligible, key=lambda r: (r != "uplink", r == "telemetry", order[r]))

    while True:
        decide = seg_start + hold_in
        if decide + hold_in > end:  # the next window couldn't be held long enough
            break
        cands = fresh_roles(decide)
        if cands:
            switch_at = decide
        else:
            later = [e for e in events if e.t > decide and e.role != cur]
            if not later or later[0].t + hold_in > end:
                break
            switch_at = later[0].t
            cands = fresh_roles(switch_at)
        new = next_in_order(cands)
        shown.add(new)
        segments.append(Segment(cur, seg_start, switch_at, trigger))
        shown_until[cur] = switch_at
        cur, seg_start = new, switch_at
        trigger = max((e for e in events if e.role == new and e.t <= switch_at), key=lambda e: e.t)
    segments.append(Segment(cur, seg_start, end, trigger))
    return segments


def render_labels(outdir: Path) -> dict[str, Path]:
    """Each stage label as a PNG: white SF Pro Semibold on a dark translucent bar,
    drawn by AppKit at 1 px per point."""
    paths = {role: outdir / f"label-{i + 1}.png" for i, role in enumerate(ROLES)}
    jxa = """
ObjC.import("AppKit");
function render(text, path) {
  var font = $.NSFont.systemFontOfSizeWeight(%d, $.NSFontWeightSemibold);
  var attrs = $.NSMutableDictionary.alloc.init;
  attrs.setObjectForKey(font, $.NSFontAttributeName);
  attrs.setObjectForKey($.NSColor.whiteColor, $.NSForegroundColorAttributeName);
  var str = $(text);
  var size = str.sizeWithAttributes(attrs);
  var padX = 26, padY = 14;
  var w = Math.ceil(size.width + 2 * padX), h = Math.ceil(size.height + 2 * padY);
  var rep = $.NSBitmapImageRep.alloc.initWithBitmapDataPlanesPixelsWidePixelsHighBitsPerSampleSamplesPerPixelHasAlphaIsPlanarColorSpaceNameBytesPerRowBitsPerPixel(null, w, h, 8, 4, true, false, $.NSDeviceRGBColorSpace, 0, 0);
  $.NSGraphicsContext.saveGraphicsState;
  $.NSGraphicsContext.setCurrentContext($.NSGraphicsContext.graphicsContextWithBitmapImageRep(rep));
  $.NSColor.colorWithSRGBRedGreenBlueAlpha(0.04, 0.05, 0.07, 0.72).setFill;
  $.NSBezierPath.bezierPathWithRoundedRectXRadiusYRadius($.NSMakeRect(0, 0, w, h), 10, 10).fill;
  str.drawAtPointWithAttributes($.NSMakePoint(padX, padY), attrs);
  $.NSGraphicsContext.restoreGraphicsState;
  rep.representationUsingTypeProperties($.NSBitmapImageFileTypePNG, $()).writeToFileAtomically($(path), true);
}
""" % LABEL_FONT_PX
    jxa += "".join(f"render({json.dumps(LABELS[role])}, {json.dumps(str(path))});\n" for role, path in paths.items())
    script = outdir / "labels.js"
    script.write_text(jxa, encoding="utf-8")
    subprocess.run(["osascript", "-l", "JavaScript", str(script)], check=True, capture_output=True, text=True)
    for path in paths.values():
        if not path.exists():
            sys.exit(f"[spotlight] label rendering failed: {path}")
    return paths


def background_color(clip: Clip, tb_px: int) -> str:
    """The terminal's own background, sampled from the clip, for the letterbox."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", "1", "-i", str(clip.path), "-frames:v", "1",
         "-vf", f"crop=1:1:8:{tb_px + 8}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
    ).stdout
    return "0x%02X%02X%02X" % tuple(raw[:3]) if len(raw) >= 3 else "0x1E2128"


def mmss(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--events", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--clip", action="append", required=True, help="role=path:stop_epoch:window_height_pt")
    ap.add_argument("--title-bar", type=float, default=32.0, help="title bar height, points (cropped out)")
    ap.add_argument("--speed", type=float, default=4.0)
    ap.add_argument("--hold", type=float, default=3.0, help="minimum seconds per window, output time")
    ap.add_argument("--fade", type=float, default=0.3, help="cross-fade, seconds of output time")
    ap.add_argument("--pre-roll", type=float, default=0.5, help="input seconds shown before the first message")
    ap.add_argument("--tail", type=float, default=2.0, help="output seconds kept after the last message")
    args = ap.parse_args()

    clips: dict[str, Clip] = {}
    for spec in args.clip:
        role, rest = spec.split("=", 1)
        path, stop, win_h = rest.rsplit(":", 2)
        clips[role] = Clip(role, Path(path), float(stop), float(win_h))
    missing = [r for r in ROLES if r not in clips]
    if missing:
        sys.exit(f"[spotlight] missing clips for: {missing}")
    for clip in clips.values():
        probe(clip)

    hold_in, fade_in = args.hold * args.speed, args.fade * args.speed
    events = read_events(args.events)
    avail_start = max(c.first for c in clips.values())
    avail_end = min(c.stop for c in clips.values())
    in_window = [e for e in events if avail_start <= e.t <= avail_end]
    if not in_window:
        sys.exit("[spotlight] no messages fell inside the recorded clips; nothing to edit")
    start = max(avail_start, in_window[0].t - args.pre_roll)
    # Room after the last message for every window with news to get its hold.
    end = min(avail_end, in_window[-1].t + (len(ROLES) - 1) * hold_in + args.tail * args.speed)
    segments = plan(events, start, end, hold_in)

    tb = {r: round(args.title_bar * c.height / c.window_h_pt) for r, c in clips.items()}
    bg = background_color(clips["telemetry"], tb["telemetry"])
    work = Path(tempfile.mkdtemp(prefix="spotlight-"))
    labels = render_labels(work)

    # One ffmpeg graph: split each clip and label once per segment that uses it.
    uses = {r: [i for i, s in enumerate(segments) if s.role == r] for r in ROLES}
    lines = []
    for idx, role in enumerate(ROLES):
        n = len(uses[role])
        if not n:
            continue
        outs = "".join(f"[c{idx}_{k}]" for k in range(n))
        lbls = "".join(f"[l{idx}_{k}]" for k in range(n))
        lines.append(f"[{idx}:v]{'split=' + str(n) if n > 1 else 'null'}{outs}")
        lines.append(f"[{idx + 4}:v]{'split=' + str(n) if n > 1 else 'null'}{lbls}")
    seen = {r: 0 for r in ROLES}
    durations = []
    for k, seg in enumerate(segments):
        idx, clip = ROLES.index(seg.role), clips[seg.role]
        j = seen[seg.role]
        seen[seg.role] += 1
        last = k == len(segments) - 1
        a = seg.start - clip.first
        b = seg.end - clip.first + (0 if last else fade_in)
        durations.append(seg.end - seg.start)
        # The content at 1 pixel per point (so a 28pt font is 28px), under the label band;
        # shrunk only if it wouldn't fit.
        pt = clip.window_h_pt / clip.height
        w = min(round(clip.width * pt), FRAME_W)
        h = min(round((clip.height - tb[seg.role]) * pt), FRAME_H - LABEL_BAND)
        lines.append(
            f"[c{idx}_{j}]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,"
            f"crop=iw:ih-{tb[seg.role]}:0:{tb[seg.role]},"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:{LABEL_BAND}:color={bg},fps=60,setsar=1[b{k}]"
        )
        lines.append(f"[b{k}][l{idx}_{j}]overlay=x={LABEL_XY[0]}:y={LABEL_XY[1]}:eof_action=repeat,format=yuv420p,settb=AVTB[s{k}]")
    if len(segments) == 1:
        lines.append("[s0]null[x]")
    else:
        prev, offset = "s0", 0.0
        for k in range(1, len(segments)):
            offset += durations[k - 1]
            out = "x" if k == len(segments) - 1 else f"x{k}"
            lines.append(f"[{prev}][s{k}]xfade=transition=fade:duration={fade_in:.3f}:offset={offset:.3f}[{out}]")
            prev = out
    lines.append(f"[x]setpts=PTS/{args.speed},fps=30,format=yuv420p[out]")
    graph = work / "graph.txt"
    graph.write_text(";\n".join(lines) + "\n")

    cmd = ["ffmpeg", "-y", "-v", "error"]
    for role in ROLES:
        cmd += ["-i", str(clips[role].path)]
    for role in ROLES:
        cmd += ["-i", str(labels[role])]
    cmd += ["-/filter_complex", str(graph), "-map", "[out]",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-an", str(args.output)]
    print(f"[spotlight] {len(segments)} segments, {sum(durations):.1f}s of input -> ~{sum(durations) / args.speed:.1f}s at {args.speed:g}x")
    subprocess.run(cmd, check=True)

    sidecar = args.output.with_suffix(".txt")
    rows, t_out = [], 0.0
    for seg, d in zip(segments, durations):
        trig = seg.trigger
        rows.append(f"{mmss(t_out)}  {LABELS[seg.role]}  {trig.truck_id if trig else '-'}  {trig.summary if trig else '(waiting for the first message)'}")
        t_out += d / args.speed
    sidecar.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"[spotlight] wrote {args.output} and {sidecar}")


if __name__ == "__main__":
    main()
