.PHONY: install test test-integration test-model compare-models sim-dryrun

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

# Sample fleet-simulator output, no Pulsar connection required.
sim-dryrun:
	uv run fleet-simulate --dry-run --seed 7
