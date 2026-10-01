# Edge Triage Pipeline manual demo runbook (no tmux)

Replaces `deploy/demo-tmux.sh` for a one-time live demo: open 7 plain
terminal windows/tabs, paste one command into each, in the order below.
Each function now runs in its own foreground terminal (not backgrounded),
so if anything goes wrong you see the real error instead of silence.

Every command below is self-contained (includes `cd` into the repo), so
each can be pasted into a brand-new terminal with no setup step first.

## Before you start

Confirm the broker is reachable:

```
curl -sf http://localhost:8080/admin/v2/clusters && echo "broker OK"
```

If that fails, start it -- it's a docker-compose service (plain
`apachepulsar/pulsar:3.2.2`, `bin/pulsar standalone`), not a dedicated
script:

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && docker compose -f deploy/docker-compose.yml up -d
```

Then re-run the `curl` check above until it succeeds before continuing.

## Terminal 1 — coprocessor function

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && ./deploy/run_edge_triage_coprocessor_localrun.sh
```

## Terminal 2 — triage function

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && export LLM_BINARY_PATH=~/tools/llama.cpp/build/bin/llama-server && export LLM_MODEL_PATH=~/tools/models/Qwen2.5-3B-Instruct-GGUF/qwen2.5-3b-instruct-q4_k_m.gguf && ./deploy/run_edge_triage_llm_localrun.sh
```

(these happen to match `triage_function.py`'s own defaults, both confirmed
present on this machine -- the exports are redundant but harmless; only
change the two paths if your binary/model live somewhere else)

## Terminal 3 — raw telemetry (input)

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && printf '\033]0;Telemetry Data From Truck Sensors\007' && pulsar-client --url pulsar://localhost:6650 consume persistent://public/default/truck-telemetry -s manual-demo-telemetry -n 0 -p Latest 2>&1 | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' | grep --line-buffered 'content:' | sed -u -e 's/^.*content://' -e 'G'
```

## Terminal 4 — coprocessor output (forwarded to triage-payloads)

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && printf '\033]0;Probable-Slowdown Events Forwarded to Triage\007' && pulsar-client --url pulsar://localhost:6650 consume persistent://public/default/triage-payloads -s manual-demo-coproc -n 0 -p Latest 2>&1 | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' | grep --line-buffered 'content:' | sed -u -e 's/^.*content://' -e 'G'
```

## Terminal 5 — outcome: uplinked cards

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && printf '\033]0;Triaged Events Sent to Control Center\007' && pulsar-client --url pulsar://localhost:6650 consume persistent://public/default/enrichment-cards -s manual-demo-uplink -n 0 -p Latest 2>&1 | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' | grep --line-buffered 'content:' | sed -u -e 's/^.*content:/[uplink] /' -e 'G'
```

## Terminal 6 — outcome: held locally

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && printf '\033]0;Triaged Events Held on the Truck\007' && pulsar-client --url pulsar://localhost:6650 consume persistent://public/default/triage-local-only -s manual-demo-local -n 0 -p Latest 2>&1 | perl -pe 'BEGIN{$|=1} s/\e\[[0-9;]*m//g' | grep --line-buffered 'content:' | sed -u -e 's/^.*content:/[local] /' -e 'G'
```

## Terminal 7 — simulator (start LAST, once terminals 1-6 are all running)

`RATE` is events/sec published across the whole fleet (`--rate` in
`fleet_simulator/cli.py`) -- raise it to speed up the telemetry stream,
lower it to slow it down. `4` is `deploy/demo-scenario.env`'s default.

```
cd /Users/david.kjerrumgaard/clone-zone/davidkj-datadog/fleet-trilogy && export RATE=4 && printf '\033]0;Fleet Simulator (Generates Truck Telemetry)\007' && uv run fleet-simulate --service-url pulsar://localhost:6650 --fleet-size 1 --incident-corridor I-95N --incident-trucks 1 --seed 4747 --rate "${RATE}" --duration 30
```

## Teardown

Ctrl-C in each terminal. Since every process is now running in the
foreground of its own terminal (not backgrounded with `&`), Ctrl-C reaches
the whole thing directly -- no orphaned processes to hunt down afterward.

If you ever do suspect a leftover process from an old run:

```
pkill -f 'talk1_edge_intelligence\.coprocessor\.TelemetryCoprocessorFunction'
pkill -f 'talk1_edge_intelligence\.triage_function\.LlmTriageFunction'
```
