#!/usr/bin/env bash
# deploy/demo-tmux.sh -- Talk 1's Edge Triage Pipeline demo, one tmux pane
# per pipeline stage, for a "see it running" recording where each stage gets
# its own visible terminal instead of deploy/demo.sh's single
# labelled-prefix stream. Wires up the same Edge Triage Pipeline as demo.sh,
# for the same reason (see that script's header): Tier 1's
# EdgeEnrichmentFunction has no co-processor gate, no severity escalation,
# and no local-only topic.
#
# Usage:
#   ./deploy/demo-tmux.sh [broker-url] [--simulator-host HOST]
#
# Same two arguments as deploy/demo.sh -- see its header for the full
# broker-placement explanation. Set LLM_BINARY_PATH / LLM_MODEL_PATH before
# running for a real model; see run_edge_triage_llm_localrun.sh.
#
# Panes (tmux session "edge-triage-demo", stacked top-to-bottom in a single
# equal-height column, each full width, titled borders):
#   telemetry    -- raw truck-telemetry events as fleet-simulator publishes
#                   them.
#   coprocessor  -- TelemetryCoprocessorFunction's forwarded payload,
#                   consumed straight off triage-payloads (its own
#                   dedicated subscription, alongside LlmTriageFunction's) --
#                   not grepped out of localrun's own stdout, because
#                   Pulsar's python-instance logger routes a function's
#                   logger.info() calls to a per-function log file on disk,
#                   never to localrun's stdout; consuming the real output
#                   topic sidesteps that entirely and shows the actual
#                   payload besides.
#   outcome      -- enrichment-cards (uplinked) vs triage-local-only (held),
#                   labelled side by side -- same pair demo.sh tails. Also
#                   launches LlmTriageFunction itself in the background
#                   (run_edge_triage_llm_localrun.sh), the same way the
#                   coprocessor pane launches its own function -- there used
#                   to be a dedicated pane here showing the model's prompt
#                   text, dropped since it never changed enough run to run
#                   to earn its own pane.
#   simulator    -- fleet-simulator itself, or (with --simulator-host) the
#                   printed command to run on the laptop.
#
# Each pane also gets its own background tint (navy/green/brown/grey, via a
# per-pane `window-style` override -- see pane_run) so the stages stay
# visually distinct at a glance, which matters most for a recording.
#
# Teardown: detach from tmux (prefix + d, default Ctrl-b d) to end the take --
# the trap below kills the whole session, and every process in it, the moment
# the attach returns. Ctrl-C alone only reaches whichever pane has focus (it
# stops that pane's own process, not the full demo) -- a real difference from
# demo.sh's single-terminal Ctrl-C, a direct consequence of giving each stage
# its own pane/process group.
#
# Requires everything deploy/demo.sh requires, plus tmux on PATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCENARIO_FILE="${SCRIPT_DIR}/demo-scenario.env"
SESSION="edge-triage-demo"

BROKER_URL="pulsar://localhost:6650"
SIMULATOR_HOST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --simulator-host)
      SIMULATOR_HOST="${2:?--simulator-host requires a value}"
      shift 2
      ;;
    --simulator-host=*)
      SIMULATOR_HOST="${1#*=}"
      shift
      ;;
    *)
      BROKER_URL="$1"
      shift
      ;;
  esac
done

for tool in pulsar-admin pulsar-client curl uv tmux; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[demo-tmux] required tool not found on PATH: ${tool}" >&2
    exit 1
  fi
done

BROKER_HOST="${BROKER_URL#pulsar://}"
BROKER_HOST="${BROKER_HOST%%:*}"
ADMIN_URL="http://${BROKER_HOST}:8080"

echo "[demo-tmux] broker: ${BROKER_URL}  admin: ${ADMIN_URL}"

if [[ "$BROKER_HOST" == "localhost" || "$BROKER_HOST" == "127.0.0.1" ]]; then
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[demo-tmux] broker not reachable at ${ADMIN_URL}, starting via docker compose..."
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
      echo "[demo-tmux] broker still not reachable after 30s, aborting" >&2
      exit 1
    fi
  fi
else
  if ! curl -sf -o /dev/null "${ADMIN_URL}/admin/v2/clusters"; then
    echo "[demo-tmux] broker not reachable at ${ADMIN_URL} -- start it there first (this script only auto-starts a LOCAL broker)" >&2
    exit 1
  fi
fi
echo "[demo-tmux] broker reachable."

# Topic names come from fleet_telemetry_model.topics, not hardcoded here --
# same reasoning as deploy/demo.sh.
TELEMETRY_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import DEFAULT_TELEMETRY_TOPIC as t; print(t)')"
TRIAGE_PAYLOADS_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import TRIAGE_PAYLOADS_TOPIC as t; print(t)')"
ENRICHMENT_CARDS_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import ENRICHMENT_CARDS_TOPIC as t; print(t)')"
LOCAL_TRIAGE_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import LOCAL_TRIAGE_TOPIC as t; print(t)')"

# pulsar-client consume's own framing ("----- got message -----", the
# publishTime/eventTime/key/properties header, periodic
# ConsumerStatsRecorderImpl INFO lines, and a one-time OpenTelemetry
# auto-configuration banner printed on *stderr*) is noise for a recording --
# every real payload line is exactly one "...content:{...}" line on stdout,
# so merging stderr into the same stream (2>&1 at the call site) then
# keeping only lines with "content:" and cutting everything up to and
# including it leaves just the JSON. The log4j2 console lines in that same
# stream carry their own ANSI colour codes (e.g. a coloured "INFO" level
# tag); cutting a line's prefix with `sed` deletes whatever reset code
# followed it too, leaving a colour/reverse-video attribute set but never
# cleared for the rest of that line -- which is what showed up as a
# "highlighted" rectangle behind the payload text. Stripping every ANSI CSI
# sequence *before* the content cut avoids ever leaving one half-applied.
ANSI_STRIP="perl -pe 'BEGIN{\$|=1} s/\e\[[0-9;]*m//g'"
CONTENT_ONLY_FILTER="${ANSI_STRIP} | grep --line-buffered 'content:' | sed -u 's/^.*content://'"

# A function launched with `&` inside a pane survives `tmux kill-session`
# -- that only reaches the pane's own shell, never a background child it
# spawned -- so each restart could silently pile up extra LocalRunner /
# pulsar-admin processes all competing for the same subscriptions. Find
# them by their unique classname (this script never captures their PIDs)
# rather than by PID, which also stops both the inner LocalRunner JVM and
# its outer `pulsar-admin ... functions localrun` wrapper process, since
# both have the classname on their command line.
kill_orphaned_functions() {
  local pattern patterns=(
    "talk1_edge_intelligence\.coprocessor\.TelemetryCoprocessorFunction"
    "talk1_edge_intelligence\.triage_function\.LlmTriageFunction"
  )
  for pattern in "${patterns[@]}"; do
    pkill -f "$pattern" >/dev/null 2>&1 || true
  done
  sleep 1
  for pattern in "${patterns[@]}"; do
    pkill -9 -f "$pattern" >/dev/null 2>&1 || true
  done
}

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[demo-tmux] killing pre-existing '${SESSION}' tmux session..."
  tmux kill-session -t "$SESSION"
fi
echo "[demo-tmux] clearing any orphaned function processes from a previous run..."
kill_orphaned_functions

cleanup() {
  tmux kill-session -t "$SESSION" >/dev/null 2>&1 || true
  kill_orphaned_functions
  echo "[demo-tmux] session '${SESSION}' torn down."
}
trap cleanup EXIT

tmux new-session -d -s "$SESSION" -n edge-triage -c "$REPO_ROOT"
tmux set-window-option -t "${SESSION}:0" pane-border-status top
tmux set-window-option -t "${SESSION}:0" pane-border-format "#{pane_title}"

hex_to_rgb_sgr() {
  # "#1a2a4a" -> "26;42;74" (decimal R;G;B for a 24-bit SGR sequence).
  local hex="${1#\#}"
  printf '%d;%d;%d' "0x${hex:0:2}" "0x${hex:2:2}" "0x${hex:4:2}"
}

pane_run() {
  # pane_run <title> <shell-command> <bg-colour> -- first call reuses the
  # session's initial pane; later calls split off a new one and re-tile
  # everything. <bg-colour> (a tmux STYLES colour, tmux(1)) is applied via
  # `window-style` scoped to just this pane with `set-option -p`, so each
  # pipeline stage keeps a visually distinct background regardless of which
  # pane has tmux focus -- see the pane list above.
  #
  # window-style's fill only paints cells tmux's grid considers untouched
  # (blank padding); any cell a program has written to -- even using
  # default/reset SGR -- keeps the terminal's own plain background instead.
  # That shows up as a two-tone pane: a correctly tinted blank margin around
  # a plain-background rectangle exactly where the command line and its
  # output were printed. Painting the same colour directly into the pane's
  # terminal state with a real SGR sequence (then clearing) before anything
  # else is printed makes every cell -- touched or not -- inherit one
  # consistent background, since it's now part of each cell's own stored
  # attributes rather than tmux's separate compositing layer.
  local title="$1" cmd="$2" bg="$3" target rgb
  if [[ -z "${FIRST_PANE_USED:-}" ]]; then
    FIRST_PANE_USED=1
    target="${SESSION}:0.0"
  else
    target="$(tmux split-window -t "$SESSION" -c "$REPO_ROOT" -P -F '#{pane_id}')"
    tmux select-layout -t "$SESSION" even-vertical >/dev/null
  fi
  tmux select-pane -t "$target" -T "$title"
  tmux set-option -p -t "$target" window-style "bg=${bg}"
  rgb="$(hex_to_rgb_sgr "$bg")"
  tmux send-keys -t "$target" "printf '\033[48;2;${rgb}m'; clear" C-m
  tmux send-keys -t "$target" "$cmd" C-m
}

pane_run "telemetry" \
  "pulsar-client --url '${BROKER_URL}' consume '${TELEMETRY_TOPIC}' -s demo-tmux-telemetry-$$ -n 0 -p Latest 2>&1 | ${CONTENT_ONLY_FILTER}" \
  "#1a2a4a"

pane_run "coprocessor: forwarded to triage-payloads" \
  "'${SCRIPT_DIR}/run_edge_triage_coprocessor_localrun.sh' '${BROKER_URL}' '${ADMIN_URL}' >/dev/null 2>&1 & pulsar-client --url '${BROKER_URL}' consume '${TRIAGE_PAYLOADS_TOPIC}' -s demo-tmux-coproc-$$ -n 0 -p Latest 2>&1 | ${CONTENT_ONLY_FILTER}" \
  "#1a3a2a"

pane_run "outcome: uplink vs local" \
  "'${SCRIPT_DIR}/run_edge_triage_llm_localrun.sh' '${BROKER_URL}' '${ADMIN_URL}' >/dev/null 2>&1 & (pulsar-client --url '${BROKER_URL}' consume '${ENRICHMENT_CARDS_TOPIC}' -s demo-tmux-uplink-$$ -n 0 -p Latest 2>&1 | ${ANSI_STRIP} | grep --line-buffered 'content:' | sed -u 's/^.*content:/[uplink] /') & (pulsar-client --url '${BROKER_URL}' consume '${LOCAL_TRIAGE_TOPIC}' -s demo-tmux-local-$$ -n 0 -p Latest 2>&1 | ${ANSI_STRIP} | grep --line-buffered 'content:' | sed -u 's/^.*content:/[local] /') & wait" \
  "#4a2a1a"

echo "[demo-tmux] waiting ${FUNCTION_STARTUP_GRACE_SECONDS:-6}s for both functions to come up..."
sleep "${FUNCTION_STARTUP_GRACE_SECONDS:-6}"

# shellcheck source=demo-scenario.env
. "${SCENARIO_FILE}"
FLEET_SIM_ARGS=(
  --fleet-size "${FLEET_SIZE}"
  --incident-corridor "${INCIDENT_CORRIDOR}"
  --incident-trucks "${INCIDENT_TRUCKS}"
  --seed "${SEED}"
  --rate "${RATE}"
  --duration "${DURATION}"
)

if [[ -n "$SIMULATOR_HOST" ]]; then
  pane_run "simulator: run this on the laptop" \
    "echo 'On the LAPTOP, run:'; echo '  uv run fleet-simulate --service-url pulsar://${SIMULATOR_HOST}:6650 ${FLEET_SIM_ARGS[*]}'" \
    "#2a2a2a"
else
  pane_run "simulator" \
    "uv run fleet-simulate --service-url '${BROKER_URL}' ${FLEET_SIM_ARGS[*]}" \
    "#2a2a2a"
fi

echo "[demo-tmux] attaching -- detach (prefix + d) to tear the whole demo down."
tmux attach -t "$SESSION"
