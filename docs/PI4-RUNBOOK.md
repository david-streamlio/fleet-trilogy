# Pi 4 runbook: the deciding `make compare-models` run

This is the one page you need the moment the Pi 4 boots. It builds mainline
llama.cpp for ARM, pulls both stage-model candidates onto the attached SSD, and
runs the exact same comparison harness that already ran on the M4 — same code
path, same eval definitions, same `models.toml` manifest, only the env vars
pointing at paths differ. See `docs/BITNET-POSTMORTEM.md` for why this is
mainline llama.cpp + a quantized instruct model rather than bitnet.cpp, and
`docs/CANON.md` for the pipeline this backend sits inside.

Target device: Raspberry Pi 4, 8GB RAM, root/model storage on an attached SSD
(not the SD card — the SD card is too slow for GGUF load + swap headroom).
This is the run that **decides** the stage model; the M4 run before it only
validated the quality axes on non-target hardware (see `decision_grade` in
its artifact).

## 0. Assumptions

- Raspberry Pi OS (64-bit, aarch64), Pi 4, SSD mounted and writable. This
  runbook assumes it's mounted at `/mnt/ssd` — adjust every path below if
  yours differs.
- `uv` and this repo are already present on the Pi (same as the M4 setup;
  `git clone` + `uv sync` at the repo root gets `make test` passing in mock
  mode with zero models present — do that first as a sanity check before
  touching any of the below).

## 1. Build mainline llama.cpp for ARM

```bash
sudo apt update && sudo apt install -y build-essential cmake git

git clone https://github.com/ggml-org/llama.cpp /mnt/ssd/tools/llama.cpp
cd /mnt/ssd/tools/llama.cpp

cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j"$(nproc)"
```

This produces `build/bin/llama-completion` (mainline llama.cpp's one-shot
completion binary — the same one the M4 run used; there's no BitNet fork
involved anywhere in this build). No GPU flags — CPU-only build, matching
`SubprocessLlmBackend`'s CPU-only invocation.

**Coherence check before anything else** — confirms the binary actually runs
on this Pi's CPU/SIMD before you trust any eval number:

```bash
./build/bin/llama-completion \
  -m /mnt/ssd/models/Qwen2.5-0.5B-Instruct-GGUF/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -p "The capital of France is" -n 16 -no-cnv
```

(Run this after step 2 pulls the weights.) If the output is garbage — the
`@@@@`-style failure the BitNet fork produced on ARM — STOP and report before
running any eval; don't trust `compare-models` output from a runtime that
can't produce coherent text at all.

## 2. Pull both candidate GGUFs onto the SSD

Weights are never committed to this repo (`.gitignore` covers `*.gguf`) —
pull them fresh on every new machine, same as the M4 did:

```bash
mkdir -p /mnt/ssd/models
pip install --user huggingface_hub

python3 -m huggingface_hub download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --local-dir /mnt/ssd/models/Qwen2.5-1.5B-Instruct-GGUF

python3 -m huggingface_hub download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
  qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --local-dir /mnt/ssd/models/Qwen2.5-0.5B-Instruct-GGUF
```

## 3. Point `models.toml` at the SSD paths

`models.toml`'s two entries resolve paths from these env vars (see the
manifest's own header comment); nothing in `models.toml` itself needs to
change — only the environment:

```bash
export LLM_BINARY_PATH_QWEN15B=/mnt/ssd/tools/llama.cpp/build/bin/llama-completion
export LLM_MODEL_PATH_QWEN15B=/mnt/ssd/models/Qwen2.5-1.5B-Instruct-GGUF/qwen2.5-1.5b-instruct-q4_k_m.gguf

export LLM_BINARY_PATH_QWEN05B=/mnt/ssd/tools/llama.cpp/build/bin/llama-completion
export LLM_MODEL_PATH_QWEN05B=/mnt/ssd/models/Qwen2.5-0.5B-Instruct-GGUF/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

Put these in `~/.bashrc` (or a small `source`-able env file next to the repo)
so they survive reboots — this is the deciding run, worth not having to
re-type paths under time pressure.

## 4. Run the comparison

Exactly the same command as the M4:

```bash
cd /path/to/fleet-trilogy
make compare-models
```

This runs the full Tier 3 eval set (format reliability, grounding,
directional accuracy, latency, load time, resident RAM) for both models on
identical seeded inputs, via `tests/model/test_compare_models.py`. It:

- prints a side-by-side table to the terminal, and
- writes `eval-results/compare-<pi-hostname>-<timestamp>.json`.

On Linux/aarch64, `decision_grade` in that artifact will read
`"full (Pi 4 target)"` (the M4 run reads `"quality-only (non-target
hardware)"`) — that's the flag that makes this THE deciding run rather than
another data point. Every axis in this run counts, including latency/RAM,
unlike the M4 run where only the quality axes did.

To use a smaller sample for a quick smoke test before the full run:

```bash
make compare-models ARGS="--model-eval-runs=5 --model-accuracy-ticks=3"
```

## 5. What to bring back

The artifact path printed at the top of the table, plus the printed table
itself. Nothing in this repo auto-picks a stage model — that's a human call
made from this Pi 4 artifact, not the M4 one.
