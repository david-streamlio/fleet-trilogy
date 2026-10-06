#!/usr/bin/env bash
# deploy/record-talk3-demo.sh -- Automated screen recording + export of Talk 3's
# demo (Pulsar Speaks English): fixed edge cards in -> Tier 2's real Pulsar
# Function (localrun, Gemma-3-4B-it) decides in plain code and has the LLM word
# it -> the speaker voices it with Piper TTS. Same approach as Talk 1's
# deploy/record-demo.sh (Terminal.app windows, screencapture, ffmpeg export) --
# each output window's content area captured separately and composed onto a black
# canvas, like record-demo.sh's --per-window mode -- plus the one thing Talk 1
# never needed: SOUND.
#
# macOS screencapture can't record system audio, so the voice is added after the
# fact: the speaker (deploy/talk3-windows/spoken.sh) keeps every WAV it plays and
# stamps playback.log the instant playback starts, and the export lays each WAV
# onto the video at exactly that offset. The offset is measured from the
# recording's ACTUAL first frame (stop time minus the raw clip's duration), not
# from when screencapture was launched, so its startup lag can't desync the audio.
#
# Windows: 3 recorded, all on the external display --
#   cards (left, full height) | decision (top right) / spoken (bottom right)
# and 2 never recorded, on the main display -- the Tier 2 Function's log and the
# card replay that drives the take (deploy/talk3-windows/replay.sh).
# With only one display, the 3 recorded windows take the right 70% of it and the
# 2 unrecorded ones stack in the left 30%; only the recorded windows' content areas
# are cropped into the video either way.
#
# Usage:
#   ./deploy/record-talk3-demo.sh [broker-url] [options]
#
# Options:
#   --output PATH       exported .mp4 (default: deploy/recordings/talk3-demo-<timestamp>.mp4)
#   --interval SEC      seconds between replayed cards (default: 4)
#   --font-size N       output windows' font size, points (default: 14)
#   --lead-in SEC       settle time recorded before the first card (default: 3)
#   --tail SEC          seconds recorded after the last warning finishes playing (default: 4)
#   --teardown          kill everything this script started and close its windows afterwards
#
# Environment: LLM_GPU_LAYERS and LLM_THREADS pass through to the Tier 2 Function
# (deploy/talk3-windows/tier2.sh: default one CPU thread, no GPU; LLM_GPU_LAYERS=99
# runs the model on a Mac's GPU).
#
# Requires: Docker (local broker) or a reachable broker,
# pulsar-admin/pulsar-client, uv, jq, ffmpeg/ffprobe, Piper + the norman voice
# (talks/talk3-pulsar-speaks-english/README.md), Gemma-3-4B-it under ~/tools
# (or LLM_BINARY_PATH / LLM_MODEL_PATH). Needs Screen Recording + Automation
# permission for the terminal running it, same as record-demo.sh.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WIN_DIR="${REPO_ROOT}/deploy/talk3-windows"

BROKER_URL="pulsar://localhost:6650"
OUTPUT_PATH=""
INTERVAL="4"
FONT_SIZE="14"
EXCLUDED_FONT_SIZE="11"
PROFILE="Clear Dark"
LEAD_IN="3"
TAIL="4"
TEARDOWN=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT_PATH="${2:?--output requires a value}"; shift 2 ;;
    --interval) INTERVAL="${2:?}"; shift 2 ;;
    --font-size) FONT_SIZE="${2:?}"; shift 2 ;;
    --lead-in) LEAD_IN="${2:?}"; shift 2 ;;
    --tail) TAIL="${2:?}"; shift 2 ;;
    --teardown) TEARDOWN="1"; shift ;;
    -*) echo "[record-talk3] unknown option: $1" >&2; exit 1 ;;
    *) BROKER_URL="$1"; shift ;;
  esac
done

log() { echo "[record-talk3] $*"; }
now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }

for tool in pulsar-admin pulsar-client curl uv jq osascript screencapture ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "[record-talk3] required tool not found: ${tool}" >&2; exit 1; }
done

BROKER_HOST="${BROKER_URL#pulsar://}"; BROKER_HOST="${BROKER_HOST%%:*}"
ADMIN_URL="http://${BROKER_HOST}:8080"
if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
  if [[ "$BROKER_HOST" == "localhost" || "$BROKER_HOST" == "127.0.0.1" ]]; then
    log "broker not reachable, starting via docker compose..."
    (cd "$REPO_ROOT" && docker compose -f deploy/docker-compose.yml up -d)
    for _ in $(seq 1 30); do curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters" && break; sleep 1; done
  fi
  curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters" || { echo "[record-talk3] broker unreachable at ${ADMIN_URL}" >&2; exit 1; }
fi
log "broker reachable."

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RECORDINGS_DIR="${REPO_ROOT}/deploy/recordings"
mkdir -p "$RECORDINGS_DIR"
: "${OUTPUT_PATH:="${RECORDINGS_DIR}/talk3-demo-${TIMESTAMP}.mp4"}"
AUDIO_DIR="${RECORDINGS_DIR}/.talk3-audio-${TIMESTAMP}"

# consumers_on <topic> <subscription> -- live consumer count, 0 if none/unknown.
consumers_on() {
  curl -s "${ADMIN_URL}/admin/v2/persistent/public/default/$1/stats" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('subscriptions',{}).get('$2',{}).get('consumers',[])))" 2>/dev/null \
    || echo 0
}
wait_for_consumer() {  # wait_for_consumer <topic> <subscription> <label> <timeout-sec>
  local waited=0
  until [[ "$(consumers_on "$1" "$2")" -ge 1 ]]; do
    sleep 1; waited=$(( waited + 1 ))
    [[ "$waited" -ge "$4" ]] && { echo "[record-talk3] $3 not subscribed within $4s, aborting" >&2; exit 1; }
  done
  log "$3 subscribed (${waited}s)."
}

# Same display geometry as record-demo.sh: recorded windows on the non-main screen,
# converted to the top-left-origin space `bounds of window` and screencapture -R use.
read -r MAIN_W MAIN_H EXT_X EXT_Y EXT_W EXT_H <<EOF
$(osascript -l JavaScript <<'JXA'
ObjC.import("AppKit");
var screens = $.NSScreen.screens, mainJs = $.NSScreen.mainScreen.js, main = null, ext = null;
for (var i = 0; i < screens.count; i++) {
  var s = screens.objectAtIndex(i);
  if (s.js === mainJs) { main = s; } else if (!ext) { ext = s; }
}
var r = "";
if (main && ext) {
  var mf = main.frame, ef = ext.frame;
  r = [mf.size.width, mf.size.height, ef.origin.x, mf.size.height - (ef.origin.y + ef.size.height), ef.size.width, ef.size.height].join(" ");
}
r
JXA
)
EOF
MARGIN=15
GAP=15
if [[ -n "${EXT_W:-}" ]]; then
  SINGLE_DISPLAY=""
  log "external display: origin (${EXT_X},${EXT_Y}) size ${EXT_W}x${EXT_H}"
  # The captured screen is the external display; the layout fills it.
  CAP_X="$EXT_X"; CAP_Y="$EXT_Y"; CAP_W="$EXT_W"; CAP_H="$EXT_H"
else
  SINGLE_DISPLAY="1"
  read -r MAIN_W MAIN_H <<< "$(osascript -l JavaScript -e 'ObjC.import("AppKit"); var f = $.NSScreen.mainScreen.frame; [f.size.width, f.size.height].join(" ")')"
  # Below the menu bar and above the Dock (sizes in points).
  MENU_BAR=40
  DOCK=90
  CAP_X=0; CAP_Y=0; CAP_W="$MAIN_W"; CAP_H="$MAIN_H"
  EXT_X=$(( MAIN_W * 3 / 10 )); EXT_Y="$MENU_BAR"
  EXT_W=$(( MAIN_W - EXT_X )); EXT_H=$(( MAIN_H - MENU_BAR - DOCK ))
  log "one display (${MAIN_W}x${MAIN_H}): recorded windows on its right 70%, the rest on its left 30%"
fi
LEFT_W=$(( (EXT_W - 3 * MARGIN) * 2 / 5 ))
RIGHT_W=$(( EXT_W - 3 * MARGIN - LEFT_W ))
LEFT_X=$(( EXT_X + MARGIN ))
RIGHT_X=$(( LEFT_X + LEFT_W + GAP ))
TOP_Y=$(( EXT_Y + MARGIN ))
BOTTOM_Y=$(( EXT_Y + EXT_H - MARGIN ))
DECISION_H=$(( (EXT_H - 3 * MARGIN) * 11 / 20 ))

if [[ -z "$SINGLE_DISPLAY" ]]; then
  # Side by side on the main display.
  EXCL_Y=$(( MAIN_H / 10 ))
  EXCL_H=$(( MAIN_H / 2 ))
  EXCL_W=$(( (MAIN_W - 3 * MARGIN) / 2 ))
  TIER2_BOUNDS=("$MARGIN" "$EXCL_Y" "$(( MARGIN + EXCL_W ))" "$(( EXCL_Y + EXCL_H ))")
  REPLAY_BOUNDS=("$(( MARGIN + EXCL_W + GAP ))" "$EXCL_Y" "$(( 2 * MARGIN + 2 * EXCL_W ))" "$(( EXCL_Y + EXCL_H ))")
else
  # Stacked in the left column, clear of the recorded area.
  EXCL_W=$(( EXT_X - 2 * MARGIN ))
  EXCL_H=$(( (EXT_H - 3 * MARGIN) / 2 ))
  TIER2_BOUNDS=("$MARGIN" "$(( EXT_Y + MARGIN ))" "$(( MARGIN + EXCL_W ))" "$(( EXT_Y + MARGIN + EXCL_H ))")
  REPLAY_BOUNDS=("$MARGIN" "$(( EXT_Y + 2 * MARGIN + EXCL_H ))" "$(( MARGIN + EXCL_W ))" "$(( EXT_Y + 2 * MARGIN + 2 * EXCL_H ))")
fi

RECORD_PIDS=()
WINDOW_IDS=()
TEARDOWN_PATTERN='talk3_pulsar_speaks_english\.function\.GlobalSynthesisFunction|run_tier2_localrun\.sh|PulsarAdminTool.*functions localrun|pulsar-speaks-english-speak|PulsarClientTool.*consume.*talk3-demo|deploy/talk3-windows/.*\.sh'
cleanup() {
  local code=$?
  trap - EXIT
  for pid in "${RECORD_PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill -INT "$pid" 2>/dev/null
  done
  [[ "${#RECORD_PIDS[@]}" -gt 0 ]] && sleep 2
  if [[ -n "$TEARDOWN" ]]; then
    log "tearing down..."
    pkill -9 -f "$TEARDOWN_PATTERN" 2>/dev/null || true
    for _ in $(seq 1 10); do pgrep -f "$TEARDOWN_PATTERN" >/dev/null 2>&1 || break; sleep 1; done
    for wid in "${WINDOW_IDS[@]:-}"; do
      [[ -n "$wid" ]] && osascript -e "tell application \"Terminal\" to close window id ${wid} saving no" >/dev/null 2>&1
    done
  fi
  exit "$code"
}
trap cleanup EXIT INT TERM

open_window() {  # same id-recovery pattern (and 1s settle) as record-demo.sh
  osascript -e "tell application \"Terminal\" to do script \"$1\"" >/dev/null
  sleep 1
  osascript -e 'tell application "Terminal" to id of front window'
}
place_window() {  # place_window <wid> <font> <x1> <y1> <x2> <y2>; applied twice, as in record-demo.sh
  local script="
tell application \"Terminal\"
  set w to window id $1
  set current settings of selected tab of w to settings set \"${PROFILE}\"
  set font size of current settings of selected tab of w to $2
  set bounds of w to {$3, $4, $5, $6}
  set visible of w to true
end tell"
  osascript -e "$script" >/dev/null; sleep 0.5; osascript -e "$script" >/dev/null
}
bounds_of() { osascript -e "tell application \"Terminal\" to bounds of window id $1" | tr -d ','; }

# Every take starts clean: these subscriptions persist between runs (`-p Latest`
# only applies when one is first created), so leftovers from an aborted take --
# a card, or an incident the speaker would voice -- would replay at the start.
for sub in "enrichment-cards public/default/GlobalSynthesisFunction" "enrichment-cards talk3-demo-cards" \
           "incidents talk3-demo-decision" "incidents talk3-demo-speaker"; do
  set -- $sub
  pulsar-admin --admin-url "$ADMIN_URL" topics clear-backlog -s "$2" "persistent://public/default/$1" >/dev/null 2>&1 || true
done

log "opening the Tier 2 Function window (not recorded)..."
# The window's shell doesn't inherit this one's environment, so pass through the two
# model settings tier2.sh reads (e.g. LLM_GPU_LAYERS=99 runs the model on the GPU).
TIER2_ENV=""
[[ -n "${LLM_GPU_LAYERS:-}" ]] && TIER2_ENV+="LLM_GPU_LAYERS='${LLM_GPU_LAYERS}' "
[[ -n "${LLM_THREADS:-}" ]] && TIER2_ENV+="LLM_THREADS='${LLM_THREADS}' "
[[ -n "$TIER2_ENV" ]] && log "Tier 2 settings: ${TIER2_ENV}"
TIER2_WID="$(open_window "cd '${REPO_ROOT}' && ${TIER2_ENV}bash deploy/talk3-windows/tier2.sh '${BROKER_URL}' '${ADMIN_URL}'")"
WINDOW_IDS+=("$TIER2_WID")
place_window "$TIER2_WID" "$EXCLUDED_FONT_SIZE" "${TIER2_BOUNDS[@]}"
wait_for_consumer enrichment-cards public/default/GlobalSynthesisFunction "Tier 2 Function" 120

log "opening the 3 recorded windows..."
CARDS_WID="$(open_window "cd '${REPO_ROOT}' && bash deploy/talk3-windows/cards.sh '${BROKER_URL}'")"
WINDOW_IDS+=("$CARDS_WID")
place_window "$CARDS_WID" "$FONT_SIZE" "$LEFT_X" "$TOP_Y" "$(( LEFT_X + LEFT_W ))" "$BOTTOM_Y"
DECISION_WID="$(open_window "cd '${REPO_ROOT}' && bash deploy/talk3-windows/decision.sh '${BROKER_URL}'")"
WINDOW_IDS+=("$DECISION_WID")
place_window "$DECISION_WID" "$FONT_SIZE" "$RIGHT_X" "$TOP_Y" "$(( RIGHT_X + RIGHT_W ))" "$(( TOP_Y + DECISION_H ))"
# Anchor the spoken window to the decision window's ACTUAL bottom edge (Terminal
# snaps sizes to whole rows -- the same overlap record-demo.sh had to fix).
read -r _ _ _ DEC_Y2 <<< "$(bounds_of "$DECISION_WID")"
SPOKEN_WID="$(open_window "cd '${REPO_ROOT}' && DEMO_AUDIO_DIR='${AUDIO_DIR}' bash deploy/talk3-windows/spoken.sh '${BROKER_URL}'")"
WINDOW_IDS+=("$SPOKEN_WID")
place_window "$SPOKEN_WID" "$FONT_SIZE" "$RIGHT_X" "$(( DEC_Y2 + GAP ))" "$(( RIGHT_X + RIGHT_W ))" "$BOTTOM_Y"

wait_for_consumer enrichment-cards talk3-demo-cards "cards window" 60
wait_for_consumer incidents talk3-demo-decision "decision window" 60
wait_for_consumer incidents talk3-demo-speaker "speaker" 60

log "opening the replay window (not recorded, started after the lead-in)..."
REPLAY_WID="$(open_window "cd '${REPO_ROOT}'")"
WINDOW_IDS+=("$REPLAY_WID")
place_window "$REPLAY_WID" "$EXCLUDED_FONT_SIZE" "${REPLAY_BOUNDS[@]}"

# Capture: ONE ffmpeg avfoundation recording of the whole external display -- a
# single clock for all three windows, true constant 30 fps (static stretches are
# filled with duplicate frames, so the clip's duration equals wall-clock time and
# first-frame epoch = stop epoch - duration; measured within ~40ms of a timed
# on-screen change), and no mouse pointer. Take 2 of this script used one
# screencapture per window instead: screencapture writes variable-frame-rate video
# whose duration ends at the last *changed* frame, which put the three windows
# seconds apart in the export.
probe_screen() {  # probe_screen <avfoundation-index> -> "W H" of one captured frame, or nothing
  local png="${RECORDINGS_DIR}/.probe-${TIMESTAMP}-$1.png"
  ( ffmpeg -hide_banner -v error -f avfoundation -capture_cursor 0 -framerate 30 -pixel_format nv12 \
      -i "$1:none" -frames:v 1 -y "$png" > /dev/null 2>&1 & p=$!; sleep 8; kill "$p" 2>/dev/null ) 2>/dev/null
  [[ -f "$png" ]] && ffprobe -v error -show_entries stream=width,height -of csv=p=0 "$png" | tr ',' ' '
  rm -f "$png"
}
SCREEN_DEV=""; SCALE=""
for dev in $(ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 \
               | sed -n 's/.*\[\([0-9]*\)\] Capture screen [0-9]*.*/\1/p'); do
  read -r fw fh <<< "$(probe_screen "$dev")"
  [[ -z "${fw:-}" ]] && continue
  # Match the captured display by aspect ratio (capture pixels may be 2x its pt
  # size on Retina, so size alone can't). SCALE = capture px per pt.
  if python3 -c "import sys; sys.exit(0 if abs(${fw}/${fh} - ${CAP_W}/${CAP_H}) < 0.01 else 1)"; then
    SCREEN_DEV="$dev"; SCALE="$(python3 -c "print(round(${fw}/${CAP_W}, 4))")"
    log "captured display = avfoundation screen device ${dev} (${fw}x${fh}, scale ${SCALE})"
    break
  fi
done
[[ -n "$SCREEN_DEV" ]] || { echo "[record-talk3] couldn't identify the captured display's capture device" >&2; exit 1; }
if [[ -z "$SINGLE_DISPLAY" ]] && python3 -c "import sys; sys.exit(0 if abs(${MAIN_W}/${MAIN_H} - ${EXT_W}/${EXT_H}) < 0.01 else 1)"; then
  echo "[record-talk3] both displays have the same aspect ratio -- can't tell them apart safely" >&2; exit 1
fi

# Crops: each output window's CONTENT area only -- TITLE_BAR pt below its top edge
# (Terminal titles show the working directory, i.e. the macOS account name, which
# AppleScript can't switch off) and BOTTOM_INSET pt above its bottom (the rounded
# corners show whatever is behind the window), composed onto a black canvas -- so
# title bars, the desktop and other apps can never be in the video. Bounds are
# read AFTER a settle delay (Terminal resizes a window after placement, which in
# take 2 pushed the decision window's region over the spoken window's title bar),
# and the decision crop is clamped to end above the spoken window regardless.
TITLE_BAR=32
BOTTOM_INSET=12
sleep 2
ROLES=(cards decision spoken)
WIDS=("$CARDS_WID" "$DECISION_WID" "$SPOKEN_WID")
BX1=(); BY1=(); BX2=(); BY2=()
for i in 0 1 2; do
  read -r x1 y1 x2 y2 <<< "$(bounds_of "${WIDS[$i]}")"
  BX1+=("$x1"); BY1+=("$y1"); BX2+=("$x2"); BY2+=("$y2")
done
CROP_X=(); CROP_Y=(); CROP_W=(); CROP_H=()
for i in 0 1 2; do
  top=$(( BY1[$i] + TITLE_BAR )); bottom=$(( BY2[$i] - BOTTOM_INSET ))
  if [[ "$i" == 1 ]] && (( bottom > BY1[2] - 2 )); then bottom=$(( BY1[2] - 2 )); fi
  # crop in capture pixels (x SCALE), relative to the captured display; even sizes for yuv420p
  read -r cx cy cw ch <<< "$(python3 -c "
s=${SCALE}; ev=lambda v: int(v)//2*2
print(ev((${BX1[$i]} - ${CAP_X})*s), ev((${top} - ${CAP_Y})*s), ev((${BX2[$i]} - ${BX1[$i]})*s), ev((${bottom} - ${top})*s))")"
  CROP_X+=("$cx"); CROP_Y+=("$cy"); CROP_W+=("$cw"); CROP_H+=("$ch")
  log "${ROLES[$i]} crop: ${cw}x${ch} at ${cx},${cy}"
done

# Park the mouse pointer on the main display: avfoundation's -capture_cursor 0 is
# not honoured on this macOS (take 3 showed the pointer in the spoken window).
# On one display, park it in the unrecorded left column instead.
if [[ -z "$SINGLE_DISPLAY" ]]; then PARK_X=$(( MAIN_W / 2 )); else PARK_X=$(( EXT_X / 2 )); fi
osascript -l JavaScript -e "ObjC.import('CoreGraphics'); $.CGWarpMouseCursorPosition($.CGPointMake(${PARK_X}, $(( MAIN_H / 2 ))))" >/dev/null 2>&1 || true
RAW_MP4="${RECORDINGS_DIR}/.raw-talk3-${TIMESTAMP}.mp4"
log "recording the captured display -> ${RAW_MP4}"
ffmpeg -hide_banner -v error -f avfoundation -capture_cursor 0 -framerate 30 -pixel_format nv12 \
  -i "${SCREEN_DEV}:none" -fps_mode cfr -r 30 -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p \
  -y "$RAW_MP4" < /dev/null > "${RECORDINGS_DIR}/.ffmpeg-capture-talk3-${TIMESTAMP}.log" 2>&1 &
RECORD_PIDS+=("$!")

sleep "$LEAD_IN"
log "replaying the edge cards..."
osascript -e "tell application \"Terminal\" to do script \"cd '${REPO_ROOT}' && bash deploy/talk3-windows/replay.sh '${BROKER_URL}' '${INTERVAL}'\" in window id ${REPLAY_WID}" >/dev/null

log "waiting for the warning to be spoken..."
waited=0
until [[ -s "${AUDIO_DIR}/playback.log" ]]; do
  sleep 1; waited=$(( waited + 1 ))
  [[ "$waited" -ge 180 ]] && { echo "[record-talk3] no warning spoken within 180s -- check the Tier 2 window" >&2; exit 1; }
done
LAST_WAV="$(tail -1 "${AUDIO_DIR}/playback.log" | awk '{print $2}')"
SPEECH_S="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "${AUDIO_DIR}/${LAST_WAV}")"
log "spoken (${LAST_WAV}, ${SPEECH_S}s) -- recording until it finishes + ${TAIL}s..."
sleep "$(python3 -c "print(${SPEECH_S} + ${TAIL})")"

log "stopping recording..."
for pid in "${RECORD_PIDS[@]}"; do kill -INT "$pid" 2>/dev/null; done
STOP_EPOCH="$(now)"
for pid in "${RECORD_PIDS[@]}"; do wait "$pid" 2>/dev/null; done
RECORD_PIDS=()
sleep 1

RAW_S="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW_MP4")"
FIRST="$(python3 -c "print(${STOP_EPOCH} - ${RAW_S})")"
T0="$(python3 -c "print(${FIRST} + ${LEAD_IN})")"
OUT_S="$(python3 -c "print(round(${STOP_EPOCH} - ${T0}, 3))")"
log "raw capture ${RAW_S}s, first frame at epoch ${FIRST}; export ${OUT_S}s"

# Canvas = bounding box of the three crops (in capture pixels), black, even-sized.
read -r MIN_X MIN_Y CANVAS_W CANVAS_H <<< "$(python3 -c "
xs=[${CROP_X[0]},${CROP_X[1]},${CROP_X[2]}]; ys=[${CROP_Y[0]},${CROP_Y[1]},${CROP_Y[2]}]
ws=[${CROP_W[0]},${CROP_W[1]},${CROP_W[2]}]; hs=[${CROP_H[0]},${CROP_H[1]},${CROP_H[2]}]
x0=min(xs); y0=min(ys); ev=lambda v: (v+1)//2*2
print(x0, y0, ev(max(x+w for x,w in zip(xs,ws))-x0), ev(max(y+h for y,h in zip(ys,hs))-y0))")"
log "canvas ${CANVAS_W}x${CANVAS_H}"

VF="color=c=black:s=${CANVAS_W}x${CANVAS_H}:r=30:d=${OUT_S}[bg];[0:v]split=3[s0][s1][s2];"
LAST="bg"
for i in 0 1 2; do
  VF="${VF}[s${i}]crop=${CROP_W[$i]}:${CROP_H[$i]}:${CROP_X[$i]}:${CROP_Y[$i]}[v${i}];"
  VF="${VF}[${LAST}][v${i}]overlay=$(( CROP_X[$i] - MIN_X )):$(( CROP_Y[$i] - MIN_Y ))[c${i}];"
  LAST="c${i}"
done

# One adelay'd input per spoken WAV, at its playback time relative to T0, mixed
# and padded with silence to the video's length.
FF_INPUTS=(-ss "$LEAD_IN" -i "$RAW_MP4"); MIX=""; n=0
while read -r epoch wav; do
  [[ -z "$wav" ]] && continue
  n=$(( n + 1 ))
  ms="$(python3 -c "print(max(0, round((${epoch} - ${T0}) * 1000)))")"
  FF_INPUTS+=(-i "${AUDIO_DIR}/${wav}")
  VF="${VF}[${n}:a]adelay=${ms}:all=1[a${n}];"
  MIX="${MIX}[a${n}]"
  log "audio ${wav} at +${ms}ms"
done < "${AUDIO_DIR}/playback.log"
# volume: Piper peaks right at 0 dBFS (-0.1 dB measured), which AAC can clip --
# leave 1.5 dB of headroom.
VF="${VF}${MIX}amix=inputs=${n}:normalize=0,volume=-1.5dB,apad[aout]"

log "exporting H.264 + AAC -> ${OUTPUT_PATH}"
if ffmpeg -y "${FF_INPUTS[@]}" -filter_complex "$VF" -map "[${LAST}]" -map "[aout]" -t "$OUT_S" \
     -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a aac -b:a 160k "$OUTPUT_PATH" \
     < /dev/null > "${RECORDINGS_DIR}/.ffmpeg-talk3-${TIMESTAMP}.log" 2>&1; then
  log "done: ${OUTPUT_PATH}"
  log "(raw capture, WAVs and playback.log kept: ${RAW_MP4}, ${AUDIO_DIR})"
else
  echo "[record-talk3] ffmpeg export failed -- see ${RECORDINGS_DIR}/.ffmpeg-talk3-${TIMESTAMP}.log" >&2
  exit 1
fi
