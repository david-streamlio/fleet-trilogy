#!/usr/bin/env bash
# deploy/record-demo.sh -- Automated screen recording + export of Talk 1's
# Edge Triage Pipeline tmux demo (deploy/demo-tmux.sh), for embedding in
# slides.
#
# Run this AFTER you've already watched a live take (e.g. via demo-tmux.sh
# itself, or `tmux attach -t edge-triage-demo`) and are happy with what it shows --
# this script does the actual "take": it opens a fresh Terminal.app window,
# runs the real demo in it, records exactly that window for the scenario's
# duration, then trims/exports a clean H.264 .mp4.
#
# Usage:
#   ./deploy/record-demo.sh [broker-url] [--simulator-host HOST] [options]
#
# Options:
#   --output PATH        Final exported .mp4 path
#                         (default: deploy/recordings/edge-triage-demo-<timestamp>.mp4)
#   --app NAME            macOS app to open/record (default: Terminal)
#   --window-size WxH     Logical window size in points (default: 1400x850)
#   --font-size N          Terminal font size, points (default: 20 -- see
#                          talks/talk1-edge-intelligence/TODO-DEMO-RECORDING.md's
#                          ">= 20pt" spec)
#   --lead-in SEC          Settle time recorded before the demo command starts
#                          (default: 2)
#   --wait-extra SEC       Extra seconds to record after the scripted scenario
#                          finishes, for cold-model/LLM catch-up (default: 90 --
#                          sized for a cold-start model; lower it for a second,
#                          warm-model take)
#   --fullscreen           Record the whole screen instead of one window
#   --teardown             Kill the tmux session and close the window once the
#                          recording is exported (default: left running, so
#                          you can rewatch or rerun)
#
# One-time macOS permissions this needs (System Settings > Privacy &
# Security): Screen Recording and Automation, both for Terminal.app (it is
# recording and scripting itself). If the exported video is black/blank,
# this is almost always why -- grant the permission and re-run.
#
# Requires everything deploy/demo-tmux.sh requires, plus osascript and
# screencapture (both macOS-only, always present), and ffmpeg (brew install
# ffmpeg) for the trim + H.264 export step.
#
# Assumes the broker is already reachable -- unlike demo-tmux.sh, this
# script does not budget extra wait time for a cold `docker compose up`; if
# yours needs one, start it first or pass a larger --wait-extra.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCENARIO_FILE="${SCRIPT_DIR}/demo-scenario.env"

BROKER_URL="pulsar://localhost:6650"
SIMULATOR_HOST=""
OUTPUT_PATH=""
APP_NAME="Terminal"
WINDOW_SIZE="1400x850"
FONT_SIZE="20"
LEAD_IN="2"
WAIT_EXTRA="90"
FULLSCREEN=""
TEARDOWN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --simulator-host) SIMULATOR_HOST="${2:?--simulator-host requires a value}"; shift 2 ;;
    --simulator-host=*) SIMULATOR_HOST="${1#*=}"; shift ;;
    --output) OUTPUT_PATH="${2:?--output requires a value}"; shift 2 ;;
    --output=*) OUTPUT_PATH="${1#*=}"; shift ;;
    --app) APP_NAME="${2:?--app requires a value}"; shift 2 ;;
    --app=*) APP_NAME="${1#*=}"; shift ;;
    --window-size) WINDOW_SIZE="${2:?--window-size requires a value}"; shift 2 ;;
    --window-size=*) WINDOW_SIZE="${1#*=}"; shift ;;
    --font-size) FONT_SIZE="${2:?--font-size requires a value}"; shift 2 ;;
    --font-size=*) FONT_SIZE="${1#*=}"; shift ;;
    --lead-in) LEAD_IN="${2:?--lead-in requires a value}"; shift 2 ;;
    --lead-in=*) LEAD_IN="${1#*=}"; shift ;;
    --wait-extra) WAIT_EXTRA="${2:?--wait-extra requires a value}"; shift 2 ;;
    --wait-extra=*) WAIT_EXTRA="${1#*=}"; shift ;;
    --fullscreen) FULLSCREEN="1"; shift ;;
    --teardown) TEARDOWN="1"; shift ;;
    *) BROKER_URL="$1"; shift ;;
  esac
done

if [[ "$(uname)" != "Darwin" ]]; then
  echo "[record-demo] this script is macOS-only (osascript/screencapture)" >&2
  exit 1
fi

for tool in pulsar-admin pulsar-client curl uv tmux osascript screencapture ffmpeg; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[record-demo] required tool not found on PATH: ${tool}" >&2
    exit 1
  fi
done

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RECORDINGS_DIR="${REPO_ROOT}/deploy/recordings"
mkdir -p "$RECORDINGS_DIR"
: "${OUTPUT_PATH:="${RECORDINGS_DIR}/edge-triage-demo-${TIMESTAMP}.mp4"}"
RAW_MOV="${RECORDINGS_DIR}/.raw-${TIMESTAMP}.mov"

# shellcheck source=demo-scenario.env
. "${SCENARIO_FILE}"
STARTUP_GRACE="${FUNCTION_STARTUP_GRACE_SECONDS:-6}"
TOTAL_WAIT=$(( STARTUP_GRACE + DURATION + WAIT_EXTRA ))

echo "[record-demo] scenario duration ${DURATION}s + startup grace ${STARTUP_GRACE}s + ${WAIT_EXTRA}s catch-up => recording ~${TOTAL_WAIT}s of demo activity after lead-in"

DEMO_CMD="cd '${REPO_ROOT}' && ./deploy/demo-tmux.sh '${BROKER_URL}'"
if [[ -n "$SIMULATOR_HOST" ]]; then
  DEMO_CMD="${DEMO_CMD} --simulator-host '${SIMULATOR_HOST}'"
fi
if [[ -n "${LLM_BINARY_PATH:-}" ]]; then
  DEMO_CMD="export LLM_BINARY_PATH='${LLM_BINARY_PATH}'; ${DEMO_CMD}"
fi
if [[ -n "${LLM_MODEL_PATH:-}" ]]; then
  DEMO_CMD="export LLM_MODEL_PATH='${LLM_MODEL_PATH}'; ${DEMO_CMD}"
fi

RECORD_PID=""
cleanup() {
  if [[ -n "$RECORD_PID" ]] && kill -0 "$RECORD_PID" 2>/dev/null; then
    kill -INT "$RECORD_PID" 2>/dev/null || true
    sleep 2
  fi
}
trap cleanup EXIT

if [[ -n "$FULLSCREEN" ]]; then
  echo "[record-demo] opening a ${APP_NAME} window (--fullscreen: not resized)..."
  WIN_ID="$(osascript <<APPLESCRIPT
tell application "${APP_NAME}"
  activate
  do script "cd '${REPO_ROOT}'"
  return id of window 1
end tell
APPLESCRIPT
)"
else
  echo "[record-demo] opening a ${WINDOW_SIZE} ${APP_NAME} window at ${FONT_SIZE}pt..."
  IFS='x' read -r WIN_W WIN_H <<< "$WINDOW_SIZE"
  WIN_ID="$(osascript <<APPLESCRIPT
tell application "${APP_NAME}"
  activate
  do script "cd '${REPO_ROOT}'"
  set bounds of window 1 to {80, 80, 80 + ${WIN_W}, 80 + ${WIN_H}}
  set font size of current settings of window 1 to ${FONT_SIZE}
  return id of window 1
end tell
APPLESCRIPT
)"
fi

sleep 1

if [[ -n "$FULLSCREEN" ]]; then
  CAPTURE_ARGS=()
else
  BOUNDS="$(osascript -e "tell application \"${APP_NAME}\" to bounds of window id ${WIN_ID}" | tr -d ',')"
  read -r X1 Y1 X2 Y2 <<< "$BOUNDS"
  CAP_W=$(( X2 - X1 ))
  CAP_H=$(( Y2 - Y1 ))
  echo "[record-demo] window region: ${X1},${Y1} ${CAP_W}x${CAP_H}"
  CAPTURE_ARGS=(-R "${X1},${Y1},${CAP_W},${CAP_H}")
fi

echo "[record-demo] recording -> ${RAW_MOV}"
screencapture -v ${CAPTURE_ARGS[@]+"${CAPTURE_ARGS[@]}"} "$RAW_MOV" &
RECORD_PID=$!

sleep "$LEAD_IN"

echo "[record-demo] launching the real demo in the recorded window..."
osascript -e "tell application \"${APP_NAME}\" to do script \"${DEMO_CMD}\" in window id ${WIN_ID}"

echo "[record-demo] recording for ~${TOTAL_WAIT}s (scenario + LLM catch-up)..."
sleep "$TOTAL_WAIT"

echo "[record-demo] stopping recording..."
kill -INT "$RECORD_PID" 2>/dev/null || true
wait "$RECORD_PID" 2>/dev/null || true
RECORD_PID=""
sleep 2

if [[ ! -s "$RAW_MOV" ]]; then
  echo "[record-demo] ERROR: ${RAW_MOV} is empty or missing -- screen recording likely failed." >&2
  echo "[record-demo] Check System Settings > Privacy & Security > Screen Recording for ${APP_NAME}." >&2
  exit 1
fi

echo "[record-demo] trimming lead-in, exporting H.264 mp4 -> ${OUTPUT_PATH}"
ffmpeg -y -ss "$LEAD_IN" -i "$RAW_MOV" -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -an "$OUTPUT_PATH" \
  < /dev/null > "${RECORDINGS_DIR}/.ffmpeg-${TIMESTAMP}.log" 2>&1

rm -f "$RAW_MOV"
echo "[record-demo] done: ${OUTPUT_PATH}"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=noprint_wrappers=1 "$OUTPUT_PATH" 2>/dev/null || true

if [[ -n "$TEARDOWN" ]]; then
  echo "[record-demo] tearing down tmux session + window..."
  tmux kill-session -t edge-triage-demo >/dev/null 2>&1 || true
  osascript -e "tell application \"${APP_NAME}\" to close window id ${WIN_ID}" >/dev/null 2>&1 || true
fi
