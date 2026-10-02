#!/usr/bin/env bash
# deploy/record-demo.sh -- Automated screen recording + export of Talk 1's
# manual multi-window Edge Triage Pipeline demo (deploy/windows/*.sh,
# deploy/RUNBOOK-EDGE-TRIAGE-MANUAL.md), for embedding in slides.
#
# This script is fully self-contained: it opens all 6 demo windows itself
# (one Terminal.app window per pipeline stage), arranges the 4 OUTPUT
# windows -- telemetry, coprocessor-output, uplink, local-only -- in a 2x2
# grid on the external/secondary monitor, starts the simulator once that
# layout is settled, and records ONLY that 2x2 grid's bounding rectangle.
#
# The other 2 windows -- "Setup: Coprocessor + LLM Triage (combined log)"
# (troubleshooting output, not meant for the audience) and the fleet
# simulator itself -- run on the main/built-in display and are deliberately
# EXCLUDED from the recording.
#
# Usage:
#   ./deploy/record-demo.sh [broker-url] [options]
#
# Options:
#   --output PATH        Final exported .mp4 path
#                         (default: deploy/recordings/edge-triage-demo-<timestamp>.mp4)
#                         In --per-window mode this is used as a basename:
#                         each window's clip gets -<role> inserted before
#                         the extension (e.g. ...-telemetry.mp4).
#   --per-window          Instead of one combined grid recording, capture
#                         each of the 4 output windows into its OWN clip
#                         (4 separate .mp4 files) -- for dropping individual
#                         windows into individual slides rather than one
#                         big composite shot. Each window's own title bar
#                         (which shows the macOS account name) is cropped
#                         out of its clip as a side effect.
#   --rate EPS            Events/sec override for the simulator, slower
#                          than deploy/demo-scenario.env's live-demo default
#                          so each pretty-printed message is readable
#                          before the next arrives (default: 1)
#   --font-size N         Output windows' terminal font size, points
#                         (default: 12 -- TODO-DEMO-RECORDING.md's ">= 20pt"
#                         spec assumed one single-window recording. With 4
#                         windows tiled 2x2 on a 1080pt-tall external
#                         display, a full telemetry event (the longest
#                         pretty-printed payload -- label + JSON body is 26
#                         lines) needs ~30 rows of headroom per cell to
#                         never scroll its own label off the top; 12pt is
#                         the largest font that still clears that bar on
#                         this geometry. Going bigger means either a
#                         shorter message or losing some of a longer one's
#                         top every time a new message arrives). The 2
#                         excluded windows always use a smaller fixed font,
#                         since they never appear on camera.
#   --lead-in SEC         Settle time recorded before the simulator starts
#                         (default: 2)
#   --wait-extra SEC      Extra seconds to record after the scenario's
#                         --duration finishes, for trailing cards (default:
#                         20 -- the LLM is already warm by the time
#                         recording starts, unlike a cold-start take)
#   --teardown            Kill everything this script started and close all
#                         6 windows once the recording is exported (default:
#                         left running, so you can rewatch or rerun)
#
# One-time macOS permissions this needs (System Settings > Privacy &
# Security): Screen Recording and Automation, both for Terminal.app (it is
# recording and scripting itself). If the exported video is black/blank,
# this is almost always why -- grant the permission and re-run.
#
# Requires a second display connected (the recorded 2x2 grid always goes on
# the non-main NSScreen) -- this script exits early if only one display is
# detected rather than guessing a layout. Also requires everything
# deploy/demo.sh requires (pulsar-admin, pulsar-client, curl, uv, docker for
# a local broker), plus jq (pretty-printed JSON in the output windows),
# osascript, screencapture, and ffmpeg (brew install ffmpeg) for the trim +
# H.264 export step. Set LLM_BINARY_PATH / LLM_MODEL_PATH before running for
# real -- see deploy/run_edge_triage_llm_localrun.sh.
#
# Unlike deploy/demo.sh, this script has no --simulator-host option: the
# simulator is one of its own managed windows, started at a precise moment
# relative to the recording, so it always runs on this machine. For a
# Pi-hosted broker with the simulator on a separate laptop, use demo.sh
# directly instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WINDOWS_DIR="${SCRIPT_DIR}/windows"
SCENARIO_FILE="${SCRIPT_DIR}/demo-scenario.env"

BROKER_URL="pulsar://localhost:6650"
OUTPUT_PATH=""
PER_WINDOW=""
RATE="1"
FONT_SIZE="12"
EXCLUDED_FONT_SIZE="12"
PROFILE="Clear Dark"
LEAD_IN="2"
WAIT_EXTRA="20"
TEARDOWN=""
# macOS's titled-window chrome, measured directly from a screenshot (not
# inferred from row counts, which gave a misleading value) -- used only in
# --per-window mode to crop each window's own title bar (and the account
# name it shows) out of that window's clip.
TITLE_BAR_HEIGHT=32

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_PATH="${2:?--output requires a value}"; shift 2 ;;
    --output=*) OUTPUT_PATH="${1#*=}"; shift ;;
    --per-window) PER_WINDOW="1"; shift ;;
    --rate) RATE="${2:?--rate requires a value}"; shift 2 ;;
    --rate=*) RATE="${1#*=}"; shift ;;
    --font-size) FONT_SIZE="${2:?--font-size requires a value}"; shift 2 ;;
    --font-size=*) FONT_SIZE="${1#*=}"; shift ;;
    --lead-in) LEAD_IN="${2:?--lead-in requires a value}"; shift 2 ;;
    --lead-in=*) LEAD_IN="${1#*=}"; shift ;;
    --wait-extra) WAIT_EXTRA="${2:?--wait-extra requires a value}"; shift 2 ;;
    --wait-extra=*) WAIT_EXTRA="${1#*=}"; shift ;;
    --teardown) TEARDOWN="1"; shift ;;
    *) BROKER_URL="$1"; shift ;;
  esac
done

if [[ "$(uname)" != "Darwin" ]]; then
  echo "[record-demo] this script is macOS-only (osascript/screencapture)" >&2
  exit 1
fi

for tool in pulsar-admin pulsar-client curl uv jq osascript screencapture ffmpeg; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[record-demo] required tool not found on PATH: ${tool}" >&2
    exit 1
  fi
done

BROKER_HOST="${BROKER_URL#pulsar://}"
BROKER_HOST="${BROKER_HOST%%:*}"
ADMIN_URL="http://${BROKER_HOST}:8080"

if [[ "$BROKER_HOST" == "localhost" || "$BROKER_HOST" == "127.0.0.1" ]]; then
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[record-demo] broker not reachable at ${ADMIN_URL}, starting via docker compose..."
    (cd "${REPO_ROOT}" && docker compose -f deploy/docker-compose.yml up -d)
    ready=""
    for _ in $(seq 1 30); do
      if curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
        ready="1"
        break
      fi
      sleep 1
    done
    if [[ -z "$ready" ]]; then
      echo "[record-demo] broker still not reachable after 30s, aborting" >&2
      exit 1
    fi
  fi
else
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[record-demo] broker not reachable at ${ADMIN_URL} -- start it there first" >&2
    exit 1
  fi
fi
echo "[record-demo] broker reachable."

# shellcheck source=demo-scenario.env
. "${SCENARIO_FILE}"
TOTAL_WAIT=$(( DURATION + WAIT_EXTRA ))

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RECORDINGS_DIR="${REPO_ROOT}/deploy/recordings"
mkdir -p "$RECORDINGS_DIR"
: "${OUTPUT_PATH:="${RECORDINGS_DIR}/edge-triage-demo-${TIMESTAMP}.mp4"}"
RAW_MOV="${RECORDINGS_DIR}/.raw-${TIMESTAMP}.mov"

# output_for_role <role> -- inserts -<role> before OUTPUT_PATH's extension,
# e.g. edge-triage-demo.mp4 -> edge-triage-demo-telemetry.mp4. Used only in
# --per-window mode.
output_for_role() {
  local role="$1"
  if [[ "$OUTPUT_PATH" == *.* ]]; then
    echo "${OUTPUT_PATH%.*}-${role}.${OUTPUT_PATH##*.}"
  else
    echo "${OUTPUT_PATH}-${role}"
  fi
}

# Screen geometry: the 2x2 recorded grid always goes on the non-main
# NSScreen, converted from Cocoa (origin bottom-left, y-up) to the
# AppleScript/Carbon screen-coordinate system `bounds of window` uses
# (origin top-left of the main screen, y-down) -- same space screencapture
# -R expects, matching this repo's own prior Terminal-bounds-based capture.
read -r MAIN_W MAIN_H EXT_X EXT_Y EXT_W EXT_H <<EOF
$(osascript -l JavaScript <<'JXA'
ObjC.import("AppKit");
var screens = $.NSScreen.screens;
var mainJs = $.NSScreen.mainScreen.js;
var main = null, ext = null;
for (var i = 0; i < screens.count; i++) {
  var s = screens.objectAtIndex(i);
  if (s.js === mainJs) { main = s; } else if (!ext) { ext = s; }
}
var result = "";
if (main && ext) {
  var mf = main.frame, ef = ext.frame;
  result = [mf.size.width, mf.size.height, ef.origin.x, mf.size.height - (ef.origin.y + ef.size.height), ef.size.width, ef.size.height].join(" ");
}
result
JXA
)
EOF

if [[ -z "${EXT_W:-}" ]]; then
  echo "[record-demo] only one display detected -- connect a second monitor (the recorded 2x2 grid needs the external display)" >&2
  exit 1
fi
echo "[record-demo] external display: origin (${EXT_X},${EXT_Y}) size ${EXT_W}x${EXT_H}"

# 2x2 grid of the 4 output windows, filling the external display with a
# 15pt margin/gap. The two rows are NOT equal height: telemetry and
# coprocessor-output print a long payload (label + JSON body is 25-26
# lines for a full telemetry event, the longest of the four), while
# local-only and uplink print a short one (~10 lines) -- an even split
# starves row 1 and scrolls its own label off the top before a full event
# finishes printing. These row heights are sized, with headroom, from
# those actual line counts (see the per-role comment below) rather than
# split evenly, and then inflated further to absorb Terminal's own
# row-quantization (observed to round a requested height down by several
# percent rather than up).
MARGIN=15
GAP=15
CELL_W=$(( (EXT_W - 3 * MARGIN) / 2 ))
ROW1_H=$(( (EXT_H - 3 * MARGIN) * 65 / 100 ))
ROW2_H=$(( EXT_H - 3 * MARGIN - ROW1_H ))
COL1_X=$(( EXT_X + MARGIN ))
COL2_X=$(( COL1_X + CELL_W + GAP ))
ROW1_Y=$(( EXT_Y + MARGIN ))
# ROW2_Y is NOT precomputed here -- see the row-1-placement loop below,
# which derives it from row 1's actual achieved bottom edge.

# Setup + simulator windows, side by side near the top of the MAIN display
# -- small and never recorded.
EXCL_Y=$(( MAIN_H / 10 ))
EXCL_H=$(( MAIN_H / 2 ))
EXCL_W=$(( (MAIN_W - 3 * MARGIN) / 2 ))
SETUP_X=$MARGIN
SIM_X=$(( SETUP_X + EXCL_W + GAP ))

RECORD_PIDS=()
WINDOW_IDS=()
cleanup() {
  local exit_code=$?
  trap - EXIT
  for pid in "${RECORD_PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill -INT "$pid" 2>/dev/null
  done
  [[ "${#RECORD_PIDS[@]:-0}" -gt 0 ]] && sleep 2
  if [[ -n "$TEARDOWN" ]]; then
    echo "[record-demo] tearing down..."
    # Includes deploy/windows/*.sh's own bash + tail processes (the
    # wrapper scripts' foreground `tail -f` and shell), not just the things
    # they launch -- leaving those alive was observed to leave "bash, tail"
    # as still-running when Terminal tries to close the window, which pops
    # its own blocking confirmation sheet despite everything else already
    # being dead.
    TEARDOWN_PATTERN='talk1_edge_intelligence\.coprocessor\.TelemetryCoprocessorFunction|talk1_edge_intelligence\.triage_function\.LlmTriageFunction|PulsarAdminTool.*functions localrun|llama-server|fleet_simulator.cli|bin/fleet-simulate|PulsarClientTool.*consume|deploy/windows/.*\.sh|edge-triage-setup-log'
    pkill -9 -f "$TEARDOWN_PATTERN" 2>/dev/null || true
    # Closing a window via AppleScript while it still has a live child
    # process pops Terminal's own "terminate running processes?" sheet,
    # which blocks waiting for a click that never comes in an automated
    # run -- wait for pkill's SIGKILLs to actually land first.
    for _ in $(seq 1 10); do
      pgrep -f "$TEARDOWN_PATTERN" >/dev/null 2>&1 || break
      sleep 1
    done
    for wid in "${WINDOW_IDS[@]}"; do
      osascript -e "tell application \"Terminal\" to close window id ${wid} saving no" >/dev/null 2>&1 || true
    done
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

open_window() {
  # open_window <command> -- opens a fresh Terminal window running <command>,
  # echoes its window id. Grabbing "front window" immediately after do
  # script is the only reliable id-recovery pattern on this Terminal
  # version; reusing an existing window later via `do script ... in window
  # id` is NOT reliable (observed to silently replace/orphan the window).
  # The 1s settle delay before querying "front window" matters: opening
  # windows back-to-back with no delay has been observed to race Terminal's
  # own window-creation animation, which can make "front window" resolve to
  # the PREVIOUS window -- causing later placements to silently stack
  # multiple windows on top of each other instead of each landing in its
  # own spot.
  osascript -e "tell application \"Terminal\" to do script \"$1\"" >/dev/null
  sleep 1
  osascript -e 'tell application "Terminal" to id of front window'
}

place_window() {
  # place_window <window-id> <font-size> <x1> <y1> <x2> <y2> -- sets profile
  # and font size BEFORE bounds (setting font after bounds has been observed
  # to silently resize the window, undoing the position). Applies bounds
  # TWICE, with a short delay in between: macOS's own new-window cascade
  # placement can override a bounds change made too soon after the window
  # was created, so the first application can get silently clobbered a
  # moment later. The second application lands after that cascade settles.
  local wid="$1" font="$2" x1="$3" y1="$4" x2="$5" y2="$6"
  local script="
tell application \"Terminal\"
  set w to window id ${wid}
  set current settings of selected tab of w to settings set \"${PROFILE}\"
  set font size of current settings of selected tab of w to ${font}
  set bounds of w to {${x1}, ${y1}, ${x2}, ${y2}}
  set visible of w to true
end tell
"
  osascript -e "$script"
  sleep 0.5
  osascript -e "$script"
}

echo "[record-demo] opening setup window (coprocessor + triage, not recorded)..."
SETUP_WID="$(open_window "cd '${REPO_ROOT}' && bash deploy/windows/setup.sh '${BROKER_URL}' '${ADMIN_URL}'")"
WINDOW_IDS+=("$SETUP_WID")
place_window "$SETUP_WID" "$EXCLUDED_FONT_SIZE" "$SETUP_X" "$EXCL_Y" "$(( SETUP_X + EXCL_W ))" "$(( EXCL_Y + EXCL_H ))"

echo "[record-demo] waiting for the coprocessor + triage functions to come up..."
waited=0
until pgrep -f 'talk1_edge_intelligence\.coprocessor\.TelemetryCoprocessorFunction' >/dev/null 2>&1 \
   && pgrep -f 'talk1_edge_intelligence\.triage_function\.LlmTriageFunction' >/dev/null 2>&1; do
  sleep 1
  waited=$(( waited + 1 ))
  if [[ "$waited" -ge 60 ]]; then
    echo "[record-demo] functions did not come up within 60s, aborting" >&2
    exit 1
  fi
done
echo "[record-demo] both functions running."

echo "[record-demo] opening simulator window (not recorded, started later)..."
SIM_WID="$(open_window "cd '${REPO_ROOT}'")"
WINDOW_IDS+=("$SIM_WID")
place_window "$SIM_WID" "$EXCLUDED_FONT_SIZE" "$SIM_X" "$EXCL_Y" "$(( SIM_X + EXCL_W ))" "$(( EXCL_Y + EXCL_H ))"

echo "[record-demo] opening the 4 output windows..."
# No associative arrays here -- macOS's /bin/bash is 3.2 (no Homebrew bash
# installed), which predates bash 4's declare -A.
GRID_SCRIPTS=(telemetry.sh coproc_out.sh local_only.sh uplink.sh)
GRID_ROLES=(telemetry coproc-out local-only uplink)
# telemetry.sh / coproc_out.sh (row 1): label + JSON body is 25-26 lines
# for a full telemetry event. local_only.sh / uplink.sh (row 2): 10-11
# lines for a full triage-outcome event.
#
# Row 2's cells are NOT computed from the precomputed ROW2_Y below -- they
# are anchored to row 1's windows' ACTUAL achieved bottom edge, read back
# after placing row 1. Terminal snaps a requested size to the nearest
# whole row/column at the current font, which was observed to make row 1
# end up taller than requested; row 2 placed at a precomputed Y then
# overlapped up into row 1's real (larger) extent. Reading back and
# re-deriving row 2's position from reality avoids needing to predict that
# snap at all.
GRID_CELLS_ROW1=(
  "${COL1_X} ${ROW1_Y} $(( COL1_X + CELL_W )) $(( ROW1_Y + ROW1_H ))"
  "${COL2_X} ${ROW1_Y} $(( COL2_X + CELL_W )) $(( ROW1_Y + ROW1_H ))"
)

MIN_X=""
MIN_Y=""
MAX_X=""
MAX_Y=""
PW_BOUNDS=()
ROW1_MAX_Y2=""
for i in 0 1; do
  script="${GRID_SCRIPTS[$i]}"
  wid="$(open_window "cd '${REPO_ROOT}' && bash deploy/windows/${script} '${BROKER_URL}'")"
  WINDOW_IDS+=("$wid")
  read -r cx1 cy1 cx2 cy2 <<< "${GRID_CELLS_ROW1[$i]}"
  place_window "$wid" "$FONT_SIZE" "$cx1" "$cy1" "$cx2" "$cy2"
  read -r ax1 ay1 ax2 ay2 <<< "$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" | tr -d ',')"
  PW_BOUNDS+=("${ax1} ${ay1} ${ax2} ${ay2}")
  [[ -z "$ROW1_MAX_Y2" || "$ay2" -gt "$ROW1_MAX_Y2" ]] && ROW1_MAX_Y2="$ay2"
  [[ -z "$MIN_X" || "$ax1" -lt "$MIN_X" ]] && MIN_X="$ax1"
  [[ -z "$MIN_Y" || "$ay1" -lt "$MIN_Y" ]] && MIN_Y="$ay1"
  [[ -z "$MAX_X" || "$ax2" -gt "$MAX_X" ]] && MAX_X="$ax2"
  [[ -z "$MAX_Y" || "$ay2" -gt "$MAX_Y" ]] && MAX_Y="$ay2"
done

ROW2_Y=$(( ROW1_MAX_Y2 + GAP ))
echo "[record-demo] row 1 actual bottom edge: ${ROW1_MAX_Y2} -> row 2 starts at ${ROW2_Y}"
GRID_CELLS_ROW2=(
  "${COL1_X} ${ROW2_Y} $(( COL1_X + CELL_W )) $(( ROW2_Y + ROW2_H ))"
  "${COL2_X} ${ROW2_Y} $(( COL2_X + CELL_W )) $(( ROW2_Y + ROW2_H ))"
)

for i in 2 3; do
  script="${GRID_SCRIPTS[$i]}"
  wid="$(open_window "cd '${REPO_ROOT}' && bash deploy/windows/${script} '${BROKER_URL}'")"
  WINDOW_IDS+=("$wid")
  read -r cx1 cy1 cx2 cy2 <<< "${GRID_CELLS_ROW2[$((i - 2))]}"
  place_window "$wid" "$FONT_SIZE" "$cx1" "$cy1" "$cx2" "$cy2"
  # Read back the ACTUAL applied bounds (Terminal snaps size to whole
  # rows/columns, so the real rectangle can differ slightly from requested)
  # and fold it into the capture region, rather than trusting the request.
  read -r ax1 ay1 ax2 ay2 <<< "$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" | tr -d ',')"
  PW_BOUNDS+=("${ax1} ${ay1} ${ax2} ${ay2}")
  [[ -z "$MIN_X" || "$ax1" -lt "$MIN_X" ]] && MIN_X="$ax1"
  [[ -z "$MIN_Y" || "$ay1" -lt "$MIN_Y" ]] && MIN_Y="$ay1"
  [[ -z "$MAX_X" || "$ax2" -gt "$MAX_X" ]] && MAX_X="$ax2"
  [[ -z "$MAX_Y" || "$ay2" -gt "$MAX_Y" ]] && MAX_Y="$ay2"
done

RECORD_PIDS=()
PW_RAW_MOVS=()
if [[ -n "$PER_WINDOW" ]]; then
  echo "[record-demo] recording 4 separate clips (one per output window, title bar cropped)..."
  for i in 0 1 2 3; do
    role="${GRID_ROLES[$i]}"
    read -r bx1 by1 bx2 by2 <<< "${PW_BOUNDS[$i]}"
    by1=$(( by1 + TITLE_BAR_HEIGHT ))
    bw=$(( bx2 - bx1 ))
    bh=$(( by2 - by1 ))
    raw="${RECORDINGS_DIR}/.raw-${TIMESTAMP}-${role}.mov"
    PW_RAW_MOVS+=("$raw")
    echo "[record-demo]   ${role}: ${bx1},${by1} ${bw}x${bh} -> ${raw}"
    screencapture -v -R "${bx1},${by1},${bw},${bh}" "$raw" &
    RECORD_PIDS+=("$!")
  done
else
  CAP_W=$(( MAX_X - MIN_X ))
  CAP_H=$(( MAX_Y - MIN_Y ))
  echo "[record-demo] recorded region: ${MIN_X},${MIN_Y} ${CAP_W}x${CAP_H} (4 output windows only)"
  echo "[record-demo] recording -> ${RAW_MOV}"
  screencapture -v -R "${MIN_X},${MIN_Y},${CAP_W},${CAP_H}" "$RAW_MOV" &
  RECORD_PIDS+=("$!")
fi

sleep "$LEAD_IN"

echo "[record-demo] starting the simulator..."
osascript -e "tell application \"Terminal\" to do script \"cd '${REPO_ROOT}' && bash deploy/windows/simulator.sh '${BROKER_URL}' '${RATE}'\" in window id ${SIM_WID}" >/dev/null

echo "[record-demo] scenario duration ${DURATION}s + ${WAIT_EXTRA}s trailing-card wait => recording ~${TOTAL_WAIT}s after lead-in..."
sleep "$TOTAL_WAIT"

echo "[record-demo] stopping recording..."
for pid in "${RECORD_PIDS[@]}"; do
  kill -INT "$pid" 2>/dev/null || true
done
for pid in "${RECORD_PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done
RECORD_PIDS=()
sleep 2

export_clip() {
  # export_clip <raw-mov> <output-mp4> <label>
  local raw="$1" out="$2" label="$3"
  if [[ ! -s "$raw" ]]; then
    echo "[record-demo] ERROR: ${raw} is empty or missing -- ${label} recording likely failed." >&2
    echo "[record-demo] Check System Settings > Privacy & Security > Screen Recording for Terminal." >&2
    return 1
  fi
  echo "[record-demo] trimming lead-in, exporting H.264 mp4 -> ${out}"
  ffmpeg -y -ss "$LEAD_IN" -i "$raw" -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -an "$out" \
    < /dev/null > "${RECORDINGS_DIR}/.ffmpeg-${TIMESTAMP}-${label}.log" 2>&1
  rm -f "$raw"
}

if [[ -n "$PER_WINDOW" ]]; then
  FAILED=""
  for i in 0 1 2 3; do
    role="${GRID_ROLES[$i]}"
    out="$(output_for_role "$role")"
    export_clip "${PW_RAW_MOVS[$i]}" "$out" "$role" || FAILED="1"
  done
  [[ -n "$FAILED" ]] && exit 1
  echo "[record-demo] done:"
  for i in 0 1 2 3; do
    out="$(output_for_role "${GRID_ROLES[$i]}")"
    echo "  ${GRID_ROLES[$i]}: ${out}"
    ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=noprint_wrappers=1 "$out" 2>/dev/null || true
  done
else
  export_clip "$RAW_MOV" "$OUTPUT_PATH" "combined" || exit 1
  echo "[record-demo] done: ${OUTPUT_PATH}"
  ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=noprint_wrappers=1 "$OUTPUT_PATH" 2>/dev/null || true
fi
