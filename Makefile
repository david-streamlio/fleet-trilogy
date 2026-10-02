.PHONY: install test test-integration test-model compare-models compare-edge-triage-models compare-tier2-models sim-dryrun

# Installs the whole uv workspace into one venv.
install:
	uv sync

# Unit tests only. No Pulsar, no LLM runtime, no Docker required — llm-inference
# runs in mock mode, so this passes on a machine with neither the model nor a Pi.
test:
	uv run pytest

# Opt-in. Spins up Pulsar standalone via testcontainers-python (needs Docker).
test-integration:
	uv run --group integration pytest tests/integration -m integration

# Opt-in. Requires a real llama.cpp-family binary + GGUF model (LLM_BINARY_PATH /
# LLM_MODEL_PATH env vars, or --llm-binary/--llm-model). Auto-skips cleanly if
# absent — run `make test-model ARGS="--llm-binary ... --llm-model ..."` to pass
# pytest options directly. Writes a JSON results artifact to eval-results/.
test-model:
	uv run pytest tests/model -m model -s $(ARGS)

# Opt-in. Runs the FULL Tier 3 eval set for every model in models.toml, on identical
# seeded inputs, and prints one side-by-side comparison table + writes
# eval-results/compare-<host>-<timestamp>.json. Paths come from models.toml's env
# vars (LLM_BINARY_PATH_QWEN15B / LLM_MODEL_PATH_QWEN15B / etc, see models.toml) —
# same command on the M4 and the Pi 4, only those env vars differ. Auto-skips
# cleanly if zero manifest models are available.
compare-models:
	uv run pytest tests/model/test_compare_models.py -m model -s $(ARGS)

# Opt-in. Same idea as compare-models but for the Edge Triage Pipeline (TelemetryCoprocessorFunction ->
# LlmTriageFunction, see talk1_edge_intelligence/coprocessor.py) instead of Flow A's
# EnrichmentCard pipeline — grammar-constrained triage cards, not free-text JSON, so
# it measures format/severity/latency/RAM only (no grounding or directional_accuracy
# axes). Writes eval-results/compare-edge-triage-<host>-<timestamp>.json.
compare-edge-triage-models:
	uv run pytest tests/model/test_compare_edge_triage_models.py -m model -s $(ARGS)

# Opt-in. Same idea as compare-edge-triage-models but for Tier 2 (talk3_pulsar_speaks_
# english's synthesize()/generate_spoken_warning() — see tier2_eval_lib.py), a
# fundamentally different task shape: the model never decides anything (scope/
# reroute are plain code), it only paraphrases already-decided facts into a short
# spoken-style warning. Measures format reliability (structured vs. fallback-to-
# raw-text), speakability (TTS-appropriate: no markdown/JSON artifacts, length
# ceiling), and grounding (does the prose stay faithful to corridor/reroute facts)
# — none of which are Flow A or Edge Triage Pipeline axes. Writes eval-results/compare-tier2-<host>-
# <timestamp>.json.
compare-tier2-models:
	uv run pytest tests/model/test_compare_tier2_models.py -m model -s $(ARGS)

# Sample fleet-simulator output, no Pulsar connection required.
sim-dryrun:
	uv run fleet-simulate --dry-run --seed 7
