# Prompt: make the Talk 1 demo recording readable on a projector

Copy everything below the line into Claude (Claude Code, run from the `fleet-trilogy` repo root).

---

I need to change how `deploy/record-demo.sh` produces the Talk 1 demo video (`edge-triage-demo-*.mp4`, shown on the "See It Running" slide). Reviewers said the current 2x2 grid of four Terminal windows at 12pt is unreadable from the back of a room.

Read these first:
- `deploy/record-demo.sh`, especially the header comments. They explain the geometry quirks: Terminal row-snapping, the row-2 drift watchdog, and the cascade override on `bounds`.
- `deploy/windows/telemetry.sh`, `coproc_out.sh`, `uplink.sh`, `local_only.sh`
- `deploy/demo-scenario.env`
- `deploy/README.md`

Preserve all of the existing workarounds. Don't simplify them away.

## Goal

Produce one 1920x1080 H.264 MP4 that the audience can read. The test: text must be legible at roughly the size of your hand held at arm's length. In practice, terminal text should render at 28px or more in the final 1080p frame.

## Changes

1. **New `--spotlight` mode (make it the default; keep the old grid behind `--grid`).**
   - Record the four output windows as separate clips. This reuses the existing `--per-window` capture path.
   - In the ffmpeg export step, compose them into one 1080p video that shows one terminal at a time, full frame, in pipeline order: telemetry, then co-processor output, then LLM uplink, then local-only.
   - Switch the visible terminal whenever that window prints a new message. Use the message timestamps already in each window's output, or log `(role, wall-clock time)` from the window scripts to a sidecar file during the take.
   - Hold each new message for at least 3 seconds of output time before allowing another switch.
   - Add a short cross-fade (about 0.3 s) between windows.
   - Burn a stage label into the top-left corner of the frame: `1 · Telemetry`, `2 · Co-processor`, `3 · LLM → uplink`, `4 · Stays on truck`. Use white, semi-bold, 36px or larger, on a dark translucent bar.

2. **Larger terminal font.**
   - In spotlight and per-window modes, default `--font-size` to 28.
   - Each window gets a full display cell, not a quarter of the screen. Size each window to fill the external display, minus margins.
   - Keep the excluded setup and simulator windows at their current small font.

3. **Shorter on-screen messages so they fit at 28pt.**
   - Add a `--compact` flag, default on in spotlight mode, to each `deploy/windows/*.sh`.
   - `telemetry.sh`: show only `truck_id`, `speed_mph`, `brake_events`, `downshift_events`, `peak_deceleration_g` and `abs_engaged`, followed by a dim line like `… +N more fields`. Don't show the full 26-line pretty-printed JSON.
   - `coproc_out.sh`: show `truck_id`, `baseline_severity`, and the three `contextual_triggers` (`weather_condition`, `cargo_type`, `dispatch_status`).
   - `uplink.sh` / `local_only.sh`: show `truck_id`, `escalation`, `severity`, and the first sentence of `risk_synthesis`.
   - Each message must fit in about 12 rows at 28pt, with no wrapping at the window width.
   - Keep the full JSON available behind `--compact=off` for troubleshooting.

4. **Speed-up option.**
   - Add `--speed N`, defaulting to 4 for this take, applied in the ffmpeg export with `setpts=PTS/N`.
   - Apply it after the spotlight composition, so the 3-second hold rule is measured in output time.
   - Don't burn a speed label into the video. The slide already shows "4× speed".

5. **Output.**
   - Write `deploy/recordings/edge-triage-demo-<timestamp>.mp4` at 1920x1080, H.264, yuv420p, with no audio. Keep the current `-crf 18 -preset slow`.
   - Also write a `.txt` sidecar listing each window switch as `mm:ss  stage  truck_id  summary`, so I can match speaker notes to the video.
   - Target length is under 90 seconds after the speed-up.

## Constraints

- macOS `/bin/bash` 3.2: no associative arrays, the same constraint the script already respects.
- Don't change the pipeline itself: functions, topics, scenario, or seeds. This is presentation only.
- The scenario has to show the same story as the slides:
  - truck-47 / I-95N slowdown: the co-processor gates it, the LLM raises it to high, and the card is uplinked;
  - at least one event that the LLM lowers or holds, so it stays local.
- Update the script's header comment and `deploy/README.md` with the new flags and the readability rationale.

## Done when

- `./deploy/record-demo.sh pulsar://<pi-host>:6650 --teardown` produces a single spotlight MP4 that meets the size and length targets above.
- The `--grid` and `--per-window` modes still work as before.
- Paste me the sidecar `.txt`, and the ffprobe output for the final file.
