#!/usr/bin/env bash
# deploy/talk3-windows/spoken.sh -- the voice: speaker.py consuming the incidents
# topic and speaking each warning with Piper TTS (the norman voice), for one of the
# 3 output windows deploy/record-talk3-demo.sh records. Prints exactly the text
# Piper is given (after normalize_for_speech), so what's on screen is what's heard.
#
# Usage:
#   ./deploy/talk3-windows/spoken.sh [broker-url]
#
# Every WAV plus playback.log goes to DEMO_AUDIO_DIR (default /tmp/talk3-demo-audio);
# the recorder muxes them into the exported video. Piper setup:
# talks/talk3-pulsar-speaks-english/README.md ("Speaking the warning").
set -uo pipefail

WINDOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WINDOWS_DIR}/../.." && pwd)"

BROKER_URL="${1:-pulsar://localhost:6650}"

printf '\033]0;Spoken Warning (Piper TTS)\007'
# Clear screen + scrollback: the recorder captures this window's content area, so
# Terminal's "Last login" banner and the echoed launch command must not be on it.
printf '\033[2J\033[3J\033[H'

export PIPER_BINARY_PATH="${PIPER_BINARY_PATH:-$HOME/tools/piper/.venv/bin/piper}"
export PIPER_VOICE_PATH="${PIPER_VOICE_PATH:-$HOME/tools/piper/voices/en_US-norman-medium.onnx}"

cd "$REPO_ROOT"
uv run --no-sync pulsar-speaks-english-speak --service-url "$BROKER_URL" \
  --subscription talk3-demo-speaker \
  --save-dir "${DEMO_AUDIO_DIR:-/tmp/talk3-demo-audio}" \
  | while IFS= read -r line; do
      echo "[Spoken aloud by Piper TTS]"
      printf '%s\n' "$line" | fold -s -w 70
      echo
    done
