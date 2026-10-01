#!/usr/bin/env bash
# deploy/demo-tmux.sh -- Talk 1's Flow B demo, one tmux pane per pipeline
# stage, for a "see it running" recording where each stage gets its own
# visible terminal instead of deploy/demo.sh's single labelled-prefix stream.
# Wires up the same Flow B pipeline as demo.sh, for the same reason (see that
# script's header): Tier 1's EdgeEnrichmentFunction has no co-processor gate,
# no severity escalation, and no local-only topic.
#
# Usage:
#   ./deploy/demo-tmux.sh [broker-url] [--simulator-host HOST]
#
# Same two arguments as deploy/demo.sh -- see its header for the full
# broker-placement explanation. Set LLM_BINARY_PATH / LLM_MODEL_PATH before
# running for a real model; see run_flowb_triage_localrun.sh.
#
# Panes (tmux session "flowb-demo", tiled layout, titled borders):
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
#   llm-input    -- the exact prompt text LlmTriageFunction hands the model
#                   for that event, isolated via a BEGIN/END marker (see
#                   triage_function.py's build_card). Consumed from a
#                   dedicated log topic (run_flowb_triage_localrun.sh's
#                   LOG_TOPIC, wired to `pulsar-admin functions localrun
#                   --log-topic`) rather than grepped from localrun's own
#                   stdout -- same root cause as the coprocessor pane above:
#                   Pulsar's python-instance logger never writes a
#                   function's logger.info() calls to localrun's stdout,
#                   only to a per-function log file on disk (confirmed in a
#                   local rehearsal) -- and unlike the coprocessor pane,
#                   this prompt text isn't published to any domain topic, so
#                   --log-topic is the mechanism that makes it visible at
#                   all.
#   outcome      -- enrichment-cards (uplinked) vs triage-local-only (held),
#                   labelled side by side -- same pair demo.sh tails.
#   simulator    -- fleet-simulator itself, or (with --simulator-host) the
#                   printed command to run on the laptop.
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
SESSION="flowb-demo"

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
# Demo-script-only infrastructure topic (not a domain topic, so it doesn't
# belong in fleet_telemetry_model.topics) -- see run_flowb_triage_localrun.sh's
# LOG_TOPIC / --log-topic wiring and the llm-input pane below.
LLM_TRIAGE_LOG_TOPIC="persistent://public/default/llm-triage-logs"
ENRICHMENT_CARDS_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import ENRICHMENT_CARDS_TOPIC as t; print(t)')"
LOCAL_TRIAGE_TOPIC="$(cd "${REPO_ROOT}" && uv run python -c \
  'from fleet_telemetry_model import LOCAL_TRIAGE_TOPIC as t; print(t)')"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[demo-tmux] killing pre-existing '${SESSION}' tmux session..."
  tmux kill-session -t "$SESSION"
fi

cleanup() {
  tmux kill-session -t "$SESSION" >/dev/null 2>&1 || true
  echo "[demo-tmux] session '${SESSION}' torn down."
}
trap cleanup EXIT

tmux new-session -d -s "$SESSION" -n flowb -c "$REPO_ROOT"
tmux set-window-option -t "${SESSION}:0" pane-border-status top
tmux set-window-option -t "${SESSION}:0" pane-border-format "#{pane_title}"

pane_run() {
  # pane_run <title> <shell-command> -- first call reuses the session's
  # initial pane; later calls split off a new one and re-tile everything.
  local title="$1" cmd="$2" target
  if [[ -z "${FIRST_PANE_USED:-}" ]]; then
    FIRST_PANE_USED=1
    target="${SESSION}:0.0"
  else
    target="$(tmux split-window -t "$SESSION" -c "$REPO_ROOT" -P -F '#{pane_id}')"
    tmux select-layout -t "$SESSION" tiled >/dev/null
  fi
  tmux select-pane -t "$target" -T "$title"
  tmux send-keys -t "$target" "$cmd" C-m
}

pane_run "telemetry" \
  "pulsar-client --url '${BROKER_URL}' consume '${TELEMETRY_TOPIC}' -s demo-tmux-telemetry-$$ -n 0 -p Latest"

pane_run "coprocessor: forwarded to triage-payloads" \
  "'${SCRIPT_DIR}/run_flowb_coprocessor_localrun.sh' '${BROKER_URL}' '${ADMIN_URL}' >/dev/null 2>&1 & pulsar-client --url '${BROKER_URL}' consume '${TRIAGE_PAYLOADS_TOPIC}' -s demo-tmux-coproc-$$ -n 0 -p Latest"

pane_run "llm-input: prompt sent to model" \
  "LOG_TOPIC='${LLM_TRIAGE_LOG_TOPIC}' '${SCRIPT_DIR}/run_flowb_triage_localrun.sh' '${BROKER_URL}' '${ADMIN_URL}' >/dev/null 2>&1 & pulsar-client --url '${BROKER_URL}' consume '${LLM_TRIAGE_LOG_TOPIC}' -s demo-tmux-llminput-$$ -n 0 -p Latest | awk '/LLM_INPUT_BEGIN/,/LLM_INPUT_END/ { print; fflush() }'"

pane_run "outcome: uplink vs local" \
  "(pulsar-client --url '${BROKER_URL}' consume '${ENRICHMENT_CARDS_TOPIC}' -s demo-tmux-uplink-$$ -n 0 -p Latest | sed -u 's/^/[uplink] /') & (pulsar-client --url '${BROKER_URL}' consume '${LOCAL_TRIAGE_TOPIC}' -s demo-tmux-local-$$ -n 0 -p Latest | sed -u 's/^/[local] /') & wait"

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
    "echo 'On the LAPTOP, run:'; echo '  uv run fleet-simulate --service-url pulsar://${SIMULATOR_HOST}:6650 ${FLEET_SIM_ARGS[*]}'"
else
  pane_run "simulator" \
    "uv run fleet-simulate --service-url '${BROKER_URL}' ${FLEET_SIM_ARGS[*]}"
fi

echo "[demo-tmux] attaching -- detach (prefix + d) to tear the whole demo down."
tmux attach -t "$SESSION"
