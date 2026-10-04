# TODO: record the end-to-end demo (Talk 1, "See It Running")

**Status:** recorded (the user, 2026-10-04). If the slide still shows the placeholder and NEEDS flag, swap in the recording. The notes below are the original plan.

## What the slide shows
- The Pi console running the Tier-1 triage function.
- `fleet-simulator` publishing telemetry from the laptop.
- `enrichment-cards` output on the Pi console.
- Entry point: `./deploy/run_tier1_localrun.sh pulsar://<broker-host>:6650 ...`
- Broker placement for this take: **on the Pi** (see `deploy/README.md`).

## Steps
1. Start the broker on the Pi.
2. Run `./deploy/run_tier1_localrun.sh` against it. Confirm whether the URL should be `pulsar://localhost:6650` when run on the Pi, and update the slide command to match.
3. From the laptop, run `fleet-simulator` against the Pi broker. Include a truck-47 / I-95N slowdown so the sequence matches slides 18–21:
   - the co-processor gates it;
   - the LLM raises it to high;
   - the card is emitted.
4. Show at least one card that stays local, e.g. a lowered or held severity. This needs the uplink gate from `TODO-TRIAGE-UPLINK-GATE.md`.
5. Record at 1920×1080 or higher, keep it under ~90 seconds, and use a large terminal font (≥ 20pt).
6. Export as MP4 (H.264), then send it back for the slide.

## Script to write
Create `talks/talk1-edge-intelligence/deploy/demo.sh`. It's a single script that runs the whole take, so the recording can be repeated.
- Args: `BROKER_URL` (default `pulsar://localhost:6650`) and `--simulator-host` (optional, for when the simulator runs on the laptop).
- Steps:
  1. Check the broker is reachable, and start it if it isn't running locally.
  2. Launch the Tier-1 function through `run_tier1_localrun.sh` in the background.
  3. Run `fleet-simulator` with a fixed scenario:
     - truck-47 / I-95N slowdown: co-processor gates, LLM raises, high card uplinked;
     - at least one event that lowers or holds: card stays local.
  4. Tail `enrichment-cards` and the local-only output side by side, or labelled clearly.
  5. On Ctrl-C or completion, tear down cleanly.
- Readable output: short labelled banners between stages (`[co-processor]`, `[llm]`, `[uplink]`, `[local]`), no debug noise.
- Deterministic: fixed simulator seed, and the scenario is defined in a checked-in file.
- Update `deploy/README.md` with usage.
- Depends on the uplink gate in `TODO-TRIAGE-UPLINK-GATE.md`. Implement that first.

## Done when
- The recording exists and the command on the slide matches what was run.
- The narration in the speaker notes matches what's on screen.
