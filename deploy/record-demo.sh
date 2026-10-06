#!/usr/bin/env bash
# deploy/record-demo.sh -- Automated screen recording + export of Talk 1's
# manual multi-window Edge Triage Pipeline demo (deploy/windows/*.sh,
# deploy/RUNBOOK-EDGE-TRIAGE-MANUAL.md), for embedding in slides.
#
# This script is fully self-contained: it opens all 6 demo windows itself
# (one Terminal.app window per pipeline stage), arranges the 4 OUTPUT
# windows -- telemetry, coprocessor-output, uplink, local-only -- on the
# external/secondary monitor, starts the simulator once that layout is
# settled, and records only those 4 windows. Three modes:
#
# - spotlight (default): each output window fills the external display at a
#   28pt font, the 4 are captured as separate clips, and the export composes
#   one 1920x1080 video that shows one terminal at a time, full frame,
#   switching whenever a window prints a new message (deploy/spotlight_edit.py),
#   at real speed, with a pause on each window before it switches away, a stage
#   label burned into the top-left corner, and a sidecar .txt listing every
#   switch. The defaults (2 events/s, 5 s holds, 3 s pauses) come to about 120 s.
# - --grid: the original 2x2 grid of the 4 windows at 12pt, recorded as one
#   rectangle.
# - --per-window: the 4 windows full-display at 28pt, exported as 4 separate
#   clips (no composition).
#
# Why spotlight: reviewers found the 2x2 grid at 12pt unreadable from the back
# of a room. The bar is text about the size of a hand held at arm's length:
# terminal text at 28px or more in the final 1080p frame. A quarter of a
# 1080p screen can't hold a full message at that size, so the video shows one
# window at a time instead, and --compact (spotlight's default) trims each
# message to the fields the slides point at, so one fits in ~12 rows at 28pt
# without wrapping.
#
# Spotlight and per-window stack the 4 full-display windows on top of each
# other, so they're captured by WINDOW (screencapture -l<window id>: Terminal's
# AppleScript window id is the CGWindow number), which records a window's own
# content even while another window covers it. The grid keeps its original
# screen-rectangle capture.
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
#                         In spotlight mode the switch list is written beside
#                         it as <name>.txt. In --per-window mode this is used
#                         as a basename: each window's clip gets -<role>
#                         inserted before the extension (e.g. ...-telemetry.mp4).
#   --spotlight           The default (see above).
#   --grid                The original single 2x2 grid recording.
#   --per-window          Instead of one combined recording, capture
#                         each of the 4 output windows into its OWN clip
#                         (4 separate .mp4 files) -- for dropping individual
#                         windows into individual slides rather than one
#                         big composite shot. Each window's own title bar
#                         (which shows the macOS account name) is cropped
#                         out of its clip.
#   --speed N             Spotlight only: speed-up applied after the
#                         composition (setpts=PTS/N), so --hold and --pause
#                         are measured in output time (default: 1, real
#                         speed). No speed label is burned in; if you speed
#                         it up, the slide should say so.
#   --hold SEC            Spotlight only: minimum output seconds a window is
#                         shown before switching away (default: 5)
#   --pause SEC           Spotlight only: the window freezes on its last frame
#                         for this many output seconds before each switch, so
#                         the audience can read it (default: 3; 0 for none)
#   --fade SEC            Spotlight only: cross-fade between windows, output
#                         seconds (default: 0.3)
#   --compact / --compact=off
#                         Short messages in the output windows (the fields the
#                         slides point at, ~12 rows at 28pt) or the full JSON
#                         (default: on in spotlight, off otherwise; off is for
#                         troubleshooting)
#   --rate EPS            The simulator's events/sec, slower than
#                          deploy/demo-scenario.env's live-demo 4 so each
#                          pretty-printed message is readable before the
#                          next arrives (default: 2). The scenario's 120
#                          ticks are kept, so the simulator runs 120/EPS
#                          seconds (60 s at 2, 120 s at 1).
#   --font-size N         Output windows' terminal font size, points
#                         (default: 28 in spotlight and per-window, where each
#                         window fills the display; in --grid, 12 -- TODO-DEMO-RECORDING.md's ">= 20pt"
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
# H.264 export step (spotlight also needs python3 and ffprobe). Set
# LLM_BINARY_PATH / LLM_MODEL_PATH before running for real -- see
# deploy/run_edge_triage_llm_localrun.sh. The windows' shells don't inherit
# this one's environment, so LLM_BACKEND, LLM_BINARY_PATH, LLM_MODEL_PATH,
# LLM_THREADS, LLM_GPU_LAYERS and UPLINK_MIN_SEVERITY are passed through to the
# setup window explicitly (e.g. LLM_BACKEND=server for llama-server on a Mac's
# GPU, as the 2026-10-02 take ran).
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
MODE="spotlight"
PER_WINDOW=""
SIM_RATE="2"
FONT_SIZE=""  # set below from MODE unless --font-size is given
SPEED="1"
HOLD="5"
PAUSE="3"
FADE="0.3"
COMPACT=""  # on/off; set below from MODE unless --compact[=off] is given
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
# Spotlight: the 1080p frame keeps a 96px band at the top for the stage label
# (spotlight_edit.py's LABEL_BAND), so a window's content is at most 1080-96-16.
SPOTLIGHT_CONTENT_H=968

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_PATH="${2:?--output requires a value}"; shift 2 ;;
    --output=*) OUTPUT_PATH="${1#*=}"; shift ;;
    --spotlight) MODE="spotlight"; shift ;;
    --grid) MODE="grid"; shift ;;
    --per-window) MODE="per-window"; shift ;;
    --speed) SPEED="${2:?--speed requires a value}"; shift 2 ;;
    --speed=*) SPEED="${1#*=}"; shift ;;
    --hold) HOLD="${2:?--hold requires a value}"; shift 2 ;;
    --hold=*) HOLD="${1#*=}"; shift ;;
    --pause) PAUSE="${2:?--pause requires a value}"; shift 2 ;;
    --pause=*) PAUSE="${1#*=}"; shift ;;
    --fade) FADE="${2:?--fade requires a value}"; shift 2 ;;
    --fade=*) FADE="${1#*=}"; shift ;;
    --compact|--compact=on) COMPACT="on"; shift ;;
    --compact=off) COMPACT="off"; shift ;;
    --rate) SIM_RATE="${2:?--rate requires a value}"; shift 2 ;;
    --rate=*) SIM_RATE="${1#*=}"; shift ;;
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

[[ "$MODE" == "per-window" ]] && PER_WINDOW="1"
# Spotlight and per-window give each window the whole display, which is what
# makes a 28pt font fit; the grid's quarter-screen cells top out at 12pt.
if [[ -z "$FONT_SIZE" ]]; then
  if [[ "$MODE" == "grid" ]]; then FONT_SIZE="12"; else FONT_SIZE="28"; fi
fi
if [[ -z "$COMPACT" ]]; then
  if [[ "$MODE" == "spotlight" ]]; then COMPACT="on"; else COMPACT="off"; fi
fi
COMPACT_ARG="--compact=${COMPACT}"
if ! awk -v r="$SIM_RATE" 'BEGIN { exit !(r + 0 > 0) }'; then
  echo "[record-demo] --rate must be a positive number of events/sec, got '${SIM_RATE}'" >&2
  exit 1
fi

if [[ "$(uname)" != "Darwin" ]]; then
  echo "[record-demo] this script is macOS-only (osascript/screencapture)" >&2
  exit 1
fi

for tool in pulsar-admin pulsar-client curl uv jq osascript screencapture ffmpeg ffprobe python3; do
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
# The scenario is its RATE x DURATION ticks (4 x 30 = 120: 25 of warmup, then the
# incident), not its seconds. --rate stretches those same ticks over more time, so
# the simulator gets a matching duration; at the scenario's 30 s, a slower rate
# would stop it a few ticks into the incident.
SIM_DURATION="$(awk -v r="$RATE" -v d="$DURATION" -v n="$SIM_RATE" 'BEGIN { printf "%g", r * d / n }')"
TOTAL_WAIT="$(awk -v d="$SIM_DURATION" -v w="$WAIT_EXTRA" 'BEGIN { printf "%d", d + w + 0.999 }')"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RECORDINGS_DIR="${REPO_ROOT}/deploy/recordings"
mkdir -p "$RECORDINGS_DIR"
: "${OUTPUT_PATH:="${RECORDINGS_DIR}/edge-triage-demo-${TIMESTAMP}.mp4"}"
RAW_MOV="${RECORDINGS_DIR}/.raw-${TIMESTAMP}.mov"
# Spotlight: every output window appends "epoch<TAB>role<TAB>truck_id<TAB>summary"
# here as it prints a message; deploy/spotlight_edit.py switches on those times.
EVENT_LOG="${RECORDINGS_DIR}/.events-${TIMESTAMP}.tsv"
WIN_ENV=""
if [[ "$MODE" != "grid" ]]; then
  # Window captures are variable-frame-rate and end at a window's last changed
  # frame; the windows' title heartbeat keeps every clip running to the stop.
  WIN_ENV="HEARTBEAT=1 "
fi
if [[ "$MODE" == "spotlight" ]]; then
  : > "$EVENT_LOG"
  WIN_ENV+="EVENT_LOG='${EVENT_LOG}' "
fi
# The setup window's shell doesn't inherit this one's environment: pass the
# LLM settings through explicitly (same fix as record-talk3-demo.sh's Tier 2 window).
SETUP_ENV=""
for var in LLM_BACKEND LLM_BINARY_PATH LLM_MODEL_PATH LLM_THREADS LLM_GPU_LAYERS UPLINK_MIN_SEVERITY; do
  val="${!var:-}"
  [[ -n "$val" ]] && SETUP_ENV+="${var}='${val}' "
done
[[ -n "$SETUP_ENV" ]] && echo "[record-demo] setup window settings: ${SETUP_ENV}"

now() { perl -MTime::HiRes=time -e 'printf "%.3f\n", time'; }

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
read -r MAIN_W MAIN_H EXT_X EXT_Y EXT_W EXT_H EXT_VIS_Y EXT_VIS_H <<EOF
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
  var mf = main.frame, ef = ext.frame, ev = ext.visibleFrame;
  result = [mf.size.width, mf.size.height, ef.origin.x, mf.size.height - (ef.origin.y + ef.size.height), ef.size.width, ef.size.height,
            mf.size.height - (ev.origin.y + ev.size.height), ev.size.height].join(" ");
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
# finishes printing.
#
# ROW1_H is a fixed value, not a formula: it was tuned by hand (launch via
# this script, drag row 1's windows to the desired height, read the
# result back with `bounds of window`) until there was a clearly visible
# gap to row 2 on this exact external display (1920x1080). If the display
# geometry ever changes, re-tune it the same way rather than guessing a
# new formula from scratch.
MARGIN=15
GAP=15
CELL_W=$(( (EXT_W - 3 * MARGIN) / 2 ))
ROW1_H=562
COL1_X=$(( EXT_X + MARGIN ))
COL2_X=$(( COL1_X + CELL_W + GAP ))
ROW1_Y=$(( EXT_Y + MARGIN ))
# ROW2_Y and ROW2_H are NOT precomputed here -- see the row-1-placement
# loop below, which derives ROW2_Y from row 1's actual bottom edge and
# then sizes ROW2_H to leave a MARGIN-sized gap above the display's
# physical bottom edge (a row 2 ending flush with it was observed to let
# Terminal's own on-screen repositioning push the whole window upward
# into row 1 whenever its row-snapping landed even 1pt taller).

# Setup + simulator windows, side by side near the top of the MAIN display
# -- small and never recorded.
EXCL_Y=$(( MAIN_H / 10 ))
EXCL_H=$(( MAIN_H / 2 ))
EXCL_W=$(( (MAIN_W - 3 * MARGIN) / 2 ))
SETUP_X=$MARGIN
SIM_X=$(( SETUP_X + EXCL_W + GAP ))

RECORD_PIDS=()
WINDOW_IDS=()
WATCHDOG_PID=""
cleanup() {
  local exit_code=$?
  trap - EXIT
  [[ -n "$WATCHDOG_PID" ]] && kill "$WATCHDOG_PID" 2>/dev/null
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

# Clear the 4 output windows' subscriptions first, as record-talk3-demo.sh does:
# a durable subscription resumes where it left off, so -p Latest doesn't stop a
# window replaying leftovers (one take's uplink window opened on 26 old cards,
# Talk 3's demo cards included -- they share the enrichment-cards topic).
for sub in "truck-telemetry manual-demo-telemetry" "triage-payloads manual-demo-coproc" \
           "enrichment-cards manual-demo-uplink" "triage-local-only manual-demo-local"; do
  set -- $sub
  pulsar-admin --admin-url "$ADMIN_URL" topics clear-backlog -s "$2" "persistent://public/default/$1" >/dev/null 2>&1 || true
done

echo "[record-demo] opening setup window (coprocessor + triage, not recorded)..."
SETUP_WID="$(open_window "cd '${REPO_ROOT}' && ${SETUP_ENV}bash deploy/windows/setup.sh '${BROKER_URL}' '${ADMIN_URL}'")"
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
if [[ "$MODE" == "grid" ]]; then
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
    wid="$(open_window "cd '${REPO_ROOT}' && ${WIN_ENV}bash deploy/windows/${script} '${BROKER_URL}' ${COMPACT_ARG}")"
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
  ROW2_H=$(( EXT_Y + EXT_H - ROW2_Y - MARGIN ))
  echo "[record-demo] row 1 actual bottom edge: ${ROW1_MAX_Y2} -> row 2 at ${ROW2_Y}, height ${ROW2_H} (bottom edge $(( ROW2_Y + ROW2_H )), display bottom edge $(( EXT_Y + EXT_H )))"
  GRID_CELLS_ROW2=(
    "${COL1_X} ${ROW2_Y} $(( COL1_X + CELL_W )) $(( ROW2_Y + ROW2_H ))"
    "${COL2_X} ${ROW2_Y} $(( COL2_X + CELL_W )) $(( ROW2_Y + ROW2_H ))"
  )

  for i in 2 3; do
    script="${GRID_SCRIPTS[$i]}"
    wid="$(open_window "cd '${REPO_ROOT}' && ${WIN_ENV}bash deploy/windows/${script} '${BROKER_URL}' ${COMPACT_ARG}")"
    WINDOW_IDS+=("$wid")
    read -r cx1 cy1 cx2 cy2 <<< "${GRID_CELLS_ROW2[$((i - 2))]}"
    # Row 2's windows sit entirely within [0, main-display-height], the
    # vertical band both displays share -- an observed macOS quirk silently
    # shifts a window placed there by ~98pt (= -EXT_Y on this geometry,
    # i.e. exactly the two displays' vertical offset), and it can race our
    # own read-back (sometimes the first read already reflects the shifted
    # position, sometimes not), so a single read-and-trust isn't reliable.
    # Converge instead: if the actual Y lands off from what we asked, shift
    # the NEXT request by that same delta to cancel it out, and repeat
    # until it settles near the intended value (a few pt of slop is normal
    # row-quantization, not this bug).
    req_y1="$cy1"
    req_y2="$cy2"
    ay1="$cy1"
    for attempt in 1 2 3 4; do
      place_window "$wid" "$FONT_SIZE" "$cx1" "$req_y1" "$cx2" "$req_y2"
      read -r ax1 ay1 ax2 ay2 <<< "$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" | tr -d ',')"
      drift=$(( cy1 - ay1 ))
      [[ "$drift" -lt 0 ]] && drift=$(( -drift ))
      [[ "$drift" -le 10 ]] && break
      echo "[record-demo] ${GRID_ROLES[$i]} landed at y1=${ay1}, wanted ${cy1} (attempt ${attempt}) -- retrying"
      req_y1=$(( req_y1 + (cy1 - ay1) ))
      req_y2=$(( req_y2 + (cy1 - ay1) ))
    done
    PW_BOUNDS+=("${ax1} ${ay1} ${ax2} ${ay2}")
    [[ -z "$MIN_X" || "$ax1" -lt "$MIN_X" ]] && MIN_X="$ax1"
    [[ -z "$MIN_Y" || "$ay1" -lt "$MIN_Y" ]] && MIN_Y="$ay1"
    [[ -z "$MAX_X" || "$ax2" -gt "$MAX_X" ]] && MAX_X="$ax2"
    [[ -z "$MAX_Y" || "$ay2" -gt "$MAX_Y" ]] && MAX_Y="$ay2"
  done
else
  # Spotlight / per-window: every output window gets the whole external
  # display (minus MARGIN on each side), stacked on top of each other. They're
  # captured by window id below, so being covered by another window doesn't
  # matter. Same placement safeguards as the grid: font before bounds and
  # bounds applied twice (place_window), the bottom edge kept MARGIN above the
  # display's physical bottom (a window flush with it gets pushed up), and the
  # converge-on-drift loop the grid's row 2 uses, in case the shared-band
  # shift described there hits these too.
  # From the display's VISIBLE frame: an external display with its own menu
  # bar won't let a window above it (one take landed every window 15pt low and
  # burned 4 retries each). In spotlight, the window is also kept short enough
  # that its content fits under the video's label band at 1 pixel per point,
  # so a 28pt font is 28px in the 1080p frame (spotlight_edit.py's LABEL_BAND).
  FULL_X1=$(( EXT_X + MARGIN ))
  FULL_Y1=$(( EXT_VIS_Y + MARGIN ))
  FULL_X2=$(( EXT_X + EXT_W - MARGIN ))
  FULL_Y2=$(( EXT_VIS_Y + EXT_VIS_H - MARGIN ))
  if [[ "$MODE" == "spotlight" && $(( FULL_Y2 - FULL_Y1 )) -gt $(( TITLE_BAR_HEIGHT + SPOTLIGHT_CONTENT_H )) ]]; then
    FULL_Y2=$(( FULL_Y1 + TITLE_BAR_HEIGHT + SPOTLIGHT_CONTENT_H ))
  fi
  for i in 0 1 2 3; do
    script="${GRID_SCRIPTS[$i]}"
    wid="$(open_window "cd '${REPO_ROOT}' && ${WIN_ENV}bash deploy/windows/${script} '${BROKER_URL}' ${COMPACT_ARG}")"
    WINDOW_IDS+=("$wid")
    req_y1="$FULL_Y1"
    req_y2="$FULL_Y2"
    ay1="$FULL_Y1"
    prev_ay1=""
    for attempt in 1 2 3 4; do
      place_window "$wid" "$FONT_SIZE" "$FULL_X1" "$req_y1" "$FULL_X2" "$req_y2"
      read -r ax1 ay1 ax2 ay2 <<< "$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" | tr -d ',')"
      drift=$(( FULL_Y1 - ay1 ))
      [[ "$drift" -lt 0 ]] && drift=$(( -drift ))
      [[ "$drift" -le 10 ]] && break
      if [[ "$ay1" == "$prev_ay1" ]]; then
        # The request moved but the window didn't: a hard limit, not the drift
        # quirk. (This external display keeps windows below y=-68, 30pt under
        # its top, even though its visibleFrame reports the full height.)
        # Adopt it for this window and the rest, keeping the planned height.
        echo "[record-demo] ${GRID_ROLES[$i]} can't go above y1=${ay1}; using that for every window"
        FULL_Y2=$(( ay1 + FULL_Y2 - FULL_Y1 ))
        FULL_Y1="$ay1"
        place_window "$wid" "$FONT_SIZE" "$FULL_X1" "$FULL_Y1" "$FULL_X2" "$FULL_Y2"
        read -r ax1 ay1 ax2 ay2 <<< "$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" | tr -d ',')"
        break
      fi
      prev_ay1="$ay1"
      echo "[record-demo] ${GRID_ROLES[$i]} landed at y1=${ay1}, wanted ${FULL_Y1} (attempt ${attempt}) -- retrying"
      req_y1=$(( req_y1 + (FULL_Y1 - ay1) ))
      req_y2=$(( req_y2 + (FULL_Y1 - ay1) ))
    done
    echo "[record-demo]   ${GRID_ROLES[$i]}: ${ax1},${ay1} -> ${ax2},${ay2}"
    PW_BOUNDS+=("${ax1} ${ay1} ${ax2} ${ay2}")
  done
fi

# Watchdog: row 2's windows (whose Y-range falls entirely within
# [0, main-display-height], the vertical band both displays share) have
# been observed to silently drift away from their placed bounds -- NOT
# immediately, but sometime after the fact (minutes into a run, not at
# placement), so a one-time re-check after a fixed delay isn't reliable.
# This keeps re-asserting every output window's intended bounds for as
# long as the recording runs, correcting any drift whenever it happens.
WATCHDOG_IDS=()
WATCHDOG_BOUNDS=()
for i in 0 1 2 3; do
  WATCHDOG_IDS+=("${WINDOW_IDS[$(( i + 2 ))]}")
  WATCHDOG_BOUNDS+=("${PW_BOUNDS[$i]}")
done
(
  while true; do
    for i in 0 1 2 3; do
      wid="${WATCHDOG_IDS[$i]}"
      read -r ix1 iy1 ix2 iy2 <<< "${WATCHDOG_BOUNDS[$i]}"
      cur="$(osascript -e "tell application \"Terminal\" to bounds of window id ${wid}" 2>/dev/null | tr -d ',')"
      [[ -z "$cur" ]] && continue
      read -r cx1 cy1 cx2 cy2 <<< "$cur"
      if [[ "$cx1" != "$ix1" || "$cy1" != "$iy1" || "$cx2" != "$ix2" || "$cy2" != "$iy2" ]]; then
        osascript -e "tell application \"Terminal\" to set bounds of window id ${wid} to {${ix1}, ${iy1}, ${ix2}, ${iy2}}" >/dev/null 2>&1
      fi
    done
    sleep 2
  done
) &
WATCHDOG_PID=$!

RECORD_PIDS=()
PW_RAW_MOVS=()
STOP_EPOCHS=()
START_EPOCHS=()
if [[ "$MODE" != "grid" ]]; then
  # By window id (-l), not by screen rectangle: the 4 windows overlap, and
  # window capture records each one's own content even while it's covered.
  # -o leaves out the window shadow; the title bar (which shows the macOS
  # account name) is cropped out at export.
  echo "[record-demo] recording 4 separate clips (one per output window, by window id)..."
  for i in 0 1 2 3; do
    role="${GRID_ROLES[$i]}"
    wid="${WINDOW_IDS[$(( i + 2 ))]}"
    raw="${RECORDINGS_DIR}/.raw-${TIMESTAMP}-${role}.mov"
    PW_RAW_MOVS+=("$raw")
    echo "[record-demo]   ${role}: window ${wid} -> ${raw}"
    START_EPOCHS+=("$(now)")
    screencapture -v -o -l"${wid}" "$raw" &
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
osascript -e "tell application \"Terminal\" to do script \"cd '${REPO_ROOT}' && bash deploy/windows/simulator.sh '${BROKER_URL}' '${SIM_RATE}' '${SIM_DURATION}'\" in window id ${SIM_WID}" >/dev/null

echo "[record-demo] scenario at ${SIM_RATE} events/s: ${SIM_DURATION}s + ${WAIT_EXTRA}s trailing-card wait => recording ~${TOTAL_WAIT}s after lead-in..."
sleep "$TOTAL_WAIT"

echo "[record-demo] stopping recording..."
kill "$WATCHDOG_PID" 2>/dev/null || true
WATCHDOG_PID=""
for pid in "${RECORD_PIDS[@]}"; do
  STOP_EPOCHS+=("$(now)")
  kill -INT "$pid" 2>/dev/null || true
done
for pid in "${RECORD_PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done
RECORD_PIDS=()
sleep 2

export_clip() {
  # export_clip <raw-mov> <output-mp4> <label> [video-filter]
  local raw="$1" out="$2" label="$3" vf="${4:-null}"
  if [[ ! -s "$raw" ]]; then
    echo "[record-demo] ERROR: ${raw} is empty or missing -- ${label} recording likely failed." >&2
    echo "[record-demo] Check System Settings > Privacy & Security > Screen Recording for Terminal." >&2
    return 1
  fi
  echo "[record-demo] trimming lead-in, exporting H.264 mp4 -> ${out}"
  ffmpeg -y -ss "$LEAD_IN" -i "$raw" -vf "$vf" -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -an "$out" \
    < /dev/null > "${RECORDINGS_DIR}/.ffmpeg-${TIMESTAMP}-${label}.log" 2>&1
  rm -f "$raw"
}

# title_bar_crop <raw-mov> <window-height-pt> -- an ffmpeg crop that removes
# the window's title bar from a window-id capture, scaled from points to the
# clip's pixels (2x on a Retina display, 1x on the usual external one).
title_bar_crop() {
  local clip_h
  clip_h="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$1")"
  echo "crop=iw:ih-$(( TITLE_BAR_HEIGHT * clip_h / $2 )):0:$(( TITLE_BAR_HEIGHT * clip_h / $2 ))"
}

# check_clip_lengths -- a window capture much shorter than the time it was
# recording stopped early. One take's 4 clips all ended at 10s of a 52s take (the
# recording was stopped from outside the script), and the edit then failed obscurely.
check_clip_lengths() {
  local i dur wall short=""
  for i in 0 1 2 3; do
    [[ -s "${PW_RAW_MOVS[$i]}" ]] || continue
    dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "${PW_RAW_MOVS[$i]}" | cut -d. -f1)"
    wall="$(python3 -c "print(int(${STOP_EPOCHS[$i]} - ${START_EPOCHS[$i]}))")"
    if [[ "$(( wall - dur ))" -gt 5 ]]; then
      echo "[record-demo] ERROR: the ${GRID_ROLES[$i]} capture stopped early: ${dur}s of ${wall}s." >&2
      short="1"
    fi
  done
  if [[ -n "$short" ]]; then
    echo "[record-demo] Was screen recording stopped from the menu bar, or a key pressed during the take? Re-run." >&2
    return 1
  fi
}

if [[ "$MODE" != "grid" ]]; then
  check_clip_lengths || exit 1
fi

if [[ "$MODE" == "spotlight" ]]; then
  CLIP_ARGS=()
  for i in 0 1 2 3; do
    raw="${PW_RAW_MOVS[$i]}"
    if [[ ! -s "$raw" ]]; then
      echo "[record-demo] ERROR: ${raw} is empty or missing -- ${GRID_ROLES[$i]} recording likely failed." >&2
      echo "[record-demo] Check System Settings > Privacy & Security > Screen Recording for Terminal." >&2
      exit 1
    fi
    read -r bx1 by1 bx2 by2 <<< "${PW_BOUNDS[$i]}"
    CLIP_ARGS+=(--clip "${GRID_ROLES[$i]}=${raw}:${STOP_EPOCHS[$i]}:$(( by2 - by1 ))")
  done
  echo "[record-demo] composing the spotlight edit (${SPEED}x, hold ${HOLD}s, pause ${PAUSE}s, fade ${FADE}s) -> ${OUTPUT_PATH}"
  EDIT_CMD=(python3 "${SCRIPT_DIR}/spotlight_edit.py" --events "$EVENT_LOG" --output "$OUTPUT_PATH" "${CLIP_ARGS[@]}"
            --title-bar "$TITLE_BAR_HEIGHT" --speed "$SPEED" --hold "$HOLD" --pause "$PAUSE" --fade "$FADE")
  # The raw clips are kept (gitignored, like record-talk3-demo.sh's raw capture), with
  # the exact command, so the edit can be re-run -- e.g. at another --speed -- without
  # a new take: the LLM's decisions differ from take to take.
  printf '%q ' "${EDIT_CMD[@]}" > "${RECORDINGS_DIR}/.spotlight-edit-${TIMESTAMP}.sh"
  echo >> "${RECORDINGS_DIR}/.spotlight-edit-${TIMESTAMP}.sh"
  "${EDIT_CMD[@]}" || exit 1
  echo "[record-demo] done: ${OUTPUT_PATH}"
  echo "[record-demo] switches: ${OUTPUT_PATH%.*}.txt (raw clips and event log kept; re-edit: bash ${RECORDINGS_DIR}/.spotlight-edit-${TIMESTAMP}.sh)"
  ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt:format=duration -of default=noprint_wrappers=1 "$OUTPUT_PATH" 2>/dev/null || true
  out_s="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTPUT_PATH" 2>/dev/null | cut -d. -f1)"
  if [[ -n "$out_s" && ( "$out_s" -gt 150 || "$out_s" -lt 90 ) ]]; then
    echo "[record-demo] WARNING: ${out_s}s is far from the ~120s target -- adjust --rate, --pause or --hold" >&2
  fi
elif [[ -n "$PER_WINDOW" ]]; then
  FAILED=""
  for i in 0 1 2 3; do
    role="${GRID_ROLES[$i]}"
    out="$(output_for_role "$role")"
    read -r bx1 by1 bx2 by2 <<< "${PW_BOUNDS[$i]}"
    crop="null"
    [[ -s "${PW_RAW_MOVS[$i]}" ]] && crop="$(title_bar_crop "${PW_RAW_MOVS[$i]}" "$(( by2 - by1 ))")"
    export_clip "${PW_RAW_MOVS[$i]}" "$out" "$role" "$crop" || FAILED="1"
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
