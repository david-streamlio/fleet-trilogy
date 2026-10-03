# Talk 3 — Pulsar Speaks English

Tier 2 global synthesis demo. Aggregates enrichment cards across the fleet,
decides single-truck vs. corridor-wide incident, decides on a reroute, and has
a small quantized instruct model (currently Gemma-3-4B-it, Q4_K_M GGUF, picked by
the Tier 2 gates in [docs/TALK2-OUTLINE.md](../../docs/TALK2-OUTLINE.md); run via
mainline llama.cpp — see
[docs/BITNET-POSTMORTEM.md](../../docs/BITNET-POSTMORTEM.md) and
[docs/CANON.md](../../docs/CANON.md)) generate the spoken proactive warning, which
Piper TTS then speaks aloud (see "Speaking the warning" below).

Depends only on `shared/*` packages (`fleet-telemetry-model`, `fleet-simulator`,
`llm-inference`). Per CANON.md, talk packages never depend on each other, so
this package does not import from `talk1-edge-intelligence` or
`talk2-greenest-token`.

## The key point

Exactly like Tier 1 keeps the LLM out of detection (cheap math decides, the LLM
only interprets), Tier 2 keeps the LLM out of the scope/reroute decision: cheap
code decides whether an incident is one truck's local problem or a
corridor-wide pattern, and whether to recommend a reroute. The LLM's only job
is turning those already-decided facts into the spoken warning's wording — it
never decides, it only narrates.

## Layout

- `synthesizer.py` — the pure decision core, no Pulsar import, no I/O:
  - `group_by_corridor(cards) -> dict[str, list[EnrichmentCard]]` — splits a
    mixed batch of enrichment cards by corridor.
  - `decide_scope(cards) -> "single_truck" | "corridor_wide"` — plain
    set-counting over `truck_id`.
  - `decide_reroute(cards, scope) -> (bool, str | None)` — recommends a
    reroute only when the incident is corridor-wide **and** at least one
    reporting truck flagged high severity; simple, explainable logic, kept as
    plain code per docs/CANON.md.
  - `synthesize(cards, backend) -> IncidentSynthesis | None` — runs the two
    decisions above, then asks the backend (only) to phrase the spoken
    warning, and returns a fully-formed `IncidentSynthesis`. Returns `None`
    for an empty card list.
- `prompting.py` — the structured-prompt module for Tier 2's synthesis step:
  - `render_synthesis_prompt(...)` — states corridor, scope, reroute, and the
    contributing enrichment cards as already-decided facts, and asks for a
    `{"spoken_warning": "..."}` JSON object. Follows the same grounding fix as
    `llm_inference.structured`'s `ENRICHMENT_CARD_PROMPT` (v1→v2): the example
    shape uses a placeholder token (`<your warning text here>`), never a
    fully-realistic literal sentence a small model could anchor on and echo
    back regardless of the real input.
  - `generate_spoken_warning(...)` — runs inference and extracts the warning
    text, reusing `llm_inference.structured.extract_json_object` rather than
    re-implementing JSON extraction; falls back to the raw completion text
    when no parseable JSON object (or no non-empty `spoken_warning` key) comes
    back, since a mock/free-text backend or a model that just answers in
    plain prose should still produce a usable warning.
- `report.py` — the I/O shell: runs `FleetSimulator` with a forced
  `incident_corridor`/`incident_trucks` scenario, turns every cheap-math-flagged
  event into an `EnrichmentCard` (Tier 1's `process_event` logic, duplicated in
  miniature as `_card_for_event` — the one place the "talks never depend on
  each other" rule creates minor, intentional duplication with
  `talk1-edge-intelligence`), groups cards by corridor, and synthesizes one
  `IncidentSynthesis` per corridor that produced any cards. This is the only
  module in this package that touches `FleetSimulator` or stdout.

## Running it

```bash
uv run pulsar-speaks-english-report --fleet-size 12 --ticks 60 --incident-corridor I-95N --incident-trucks 3
```

or in Python:

```python
from talk3_pulsar_speaks_english.report import run_fleet_synthesis_report, format_report

syntheses = run_fleet_synthesis_report(
    fleet_size=12, ticks=60, seed=7, incident_corridor="I-95N", incident_trucks=3,
)
print(format_report(syntheses))
```

## Speaking the warning (Piper TTS)

The last hop — text to voice — is `speaker.py`
(`uv run pulsar-speaks-english-speak`): a plain Pulsar consumer on the incidents
topic that speaks each `spoken_warning` aloud. `speech.py` does the work:

- `normalize_for_speech()` — plain code, applied before TTS. Fixes what Piper
  actually mispronounces (checked against its phonemizer): "I-95N" → "I-95 North"
  (otherwise "eye ninety-five *en*") and "ETA" → "E T A" (otherwise "ee-ta").
- `PiperSpeaker` — runs the Piper CLI as a **separate process** and plays the WAV
  (`afplay` on macOS, `aplay` on Linux). Paths come from `--piper-binary`/`--voice`
  or `PIPER_BINARY_PATH`/`PIPER_VOICE_PATH`; with neither, it runs in mock mode and
  prints instead of speaking (tests never need a TTS install).

**Licensing:** Piper ([OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl),
`piper-tts` on PyPI) is **GPL-3.0-or-later** (the MIT `rhasspy/piper` was archived
in Oct 2025). That's why it is never a dependency of this package — it's installed
in its own venv and only ever invoked as a subprocess, the same arm's-length way
`llm_inference` shells out to llama.cpp. Voice models are licensed separately (each
voice's `MODEL_CARD`); the demo uses **`en_US-norman-medium`** (public domain,
LibriVox recordings). Avoid `ryan` / `hfc_*` (CC BY-NC-SA) and `lessac` (restrictive
dataset license).

One-time setup on the Mac, outside the repo (next to llama.cpp and the GGUFs):

```bash
uv venv --python 3.12 ~/tools/piper/.venv
uv pip install --python ~/tools/piper/.venv/bin/python piper-tts
mkdir -p ~/tools/piper/voices && cd ~/tools/piper/voices
~/tools/piper/.venv/bin/python -m piper.download_voices en_US-norman-medium
```

Then:

```bash
export PIPER_BINARY_PATH=~/tools/piper/.venv/bin/piper
export PIPER_VOICE_PATH=~/tools/piper/voices/en_US-norman-medium.onnx
uv run pulsar-speaks-english-speak --text "Approaching I-95N, expect an 8-minute ETA impact."
uv run pulsar-speaks-english-speak --save-dir /tmp/warnings   # consume incidents, speak, keep WAVs
```

Synthesis runs ~70x faster than real time on an M4 (0.16s for 11s of audio), so
the LLM, not the voice, is the slow step.

Tests use `SubprocessLlmBackend(mock=True)` throughout (never a real model),
covering single-truck vs. corridor-wide scope decisions, reroute logic, prompt
grounding, and an end-to-end run over `FleetSimulator`'s correlated
`incident_corridor`/`incident_trucks` scenario.
