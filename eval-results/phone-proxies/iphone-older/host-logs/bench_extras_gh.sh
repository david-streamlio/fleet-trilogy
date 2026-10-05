#!/usr/bin/env bash
# Catalog tests G and H, queued behind bench_extras.sh on a Mac proxy: it waits for that
# queue's .finished marker (by then C has run in its pause too), then runs:
#   G  quantization variants: Q4_0, Q8_0 and IQ4_XS of four models, in Phase 1's four
#      windows per model (Metal pp, Metal tg, idle gap, CPU t=4). Their Q4_K_M rows are
#      Phase 1's. Gemma-3-1B's variants come from unsloth: ggml-org (Phase 1's repo) only
#      ships Q4_K_M and Q8_0.
#   H  MLX vs llama.cpp Metal: mlx_bench.py (pp512 / tg128, 3 reps, per-trial epoch
#      times) on mlx-community's 4-bit conversions of nine Phase 1 models. MLX 4-bit
#      (~4.5 bits/weight) sits between GGUF Q4_0 and Q4_K_M (G and Phase 1 have both).
# Results: results/G-quant-variants-<ts>/ and results/H-mlx-<ts>/, bench.sh's layout.
# Downloads and the MLX install happen before any window, with nothing else running.
#
#   bench_extras_gh.sh <base> <marker-to-wait-for>
set -uo pipefail

BASE="$1"
WAIT_FOR="$2"
METAL="$BASE/llama.cpp/build/bin/llama-bench"
CPU="$BASE/llama.cpp/build-cpu/bin/llama-bench"
UV=/opt/homebrew/bin/uv
VENV="$BASE/mlx-venv"
QID="$(date -u +%Y%m%dT%H%M%SZ)"
QLOG="$BASE/results/queue-gh-$QID"
mkdir -p "$BASE/results"
exec > >(tee -a "$QLOG.log") 2>&1
echo "G/H queue $QID: waiting for $WAIT_FOR"
until [ -f "$WAIT_FOR" ]; do sleep 60; done
echo "starting at $(date -u +%H:%M:%SZ)"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}

GMODELS="unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-Q4_0.gguf
unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-IQ4_XS.gguf
unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-Q8_0.gguf
unsloth/Llama-3.2-3B-Instruct-GGUF Llama-3.2-3B-Instruct-Q4_0.gguf
unsloth/Llama-3.2-3B-Instruct-GGUF Llama-3.2-3B-Instruct-IQ4_XS.gguf
unsloth/Llama-3.2-3B-Instruct-GGUF Llama-3.2-3B-Instruct-Q8_0.gguf
bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-Q4_0.gguf
bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-IQ4_XS.gguf
bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-Q8_0.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_0.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-IQ4_XS.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q8_0.gguf"

HMODELS="mlx-community/gemma-3-1b-it-4bit
mlx-community/Llama-3.2-1B-Instruct-4bit
mlx-community/Qwen2.5-1.5B-Instruct-4bit
mlx-community/Qwen3.5-2B-4bit
mlx-community/Llama-3.2-3B-Instruct-4bit
mlx-community/Phi-3.5-mini-instruct-4bit
mlx-community/gemma-3-4b-it-4bit
mlx-community/Llama-3.1-8B-Instruct-4bit
mlx-community/Qwen3-8B-4bit"

# --- prep: not measured ------------------------------------------------------------------
mkdir -p "$BASE/models-quant"
echo "$GMODELS" | while read -r repo file; do
  [ -f "$BASE/models-quant/$file" ] && continue
  curl -fL --retry 5 --retry-delay 5 -sS -o "$BASE/models-quant/$file.part" "https://huggingface.co/$repo/resolve/main/$file" \
    && mv "$BASE/models-quant/$file.part" "$BASE/models-quant/$file"
done
[ -x "$UV" ] || /opt/homebrew/bin/brew install uv
[ -x "$VENV/bin/python" ] || "$UV" venv --python 3.12 "$VENV"
"$UV" pip install --python "$VENV/bin/python" "mlx-lm==0.32.0"
echo "$HMODELS" | while read -r repo; do
  "$VENV/bin/python" -c "from huggingface_hub import snapshot_download as s; s('$repo')" > /dev/null
done
"$METAL" -m "$BASE/models-quant/gemma-3-1b-it-Q4_0.gguf" -ngl 99 -p 16 -n 4 -r 1 > /dev/null 2>&1  # shader warm-up

PM_PID=""
test_begin() {
  OUT="$BASE/results/$1-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$OUT"
  echo "== test $1 -> $(basename "$OUT") at $(date -u +%H:%M:%SZ)"
  { echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string; } > "$OUT/system.txt"
  sudo powermetrics --samplers cpu_power,gpu_power -i 500 -o "$OUT/powermetrics.txt" &
  PM_PID=$!
  sleep 5
  window idle-pre sleep 30
}
test_end() {
  window idle-post sleep 30
  sudo pkill -INT -P "$PM_PID" -x powermetrics  # see bench.sh: sudo won't relay our signal
  wait "$PM_PID" 2>/dev/null
  basename "$OUT" >> "$QLOG.done"
}

# --- G: quantization variants ----------------------------------------------------------------
test_begin G-quant-variants
for file in $(echo "$GMODELS" | awk '{print $2}'); do
  m="$BASE/models-quant/$file"
  [ -f "$m" ] || { echo "missing $m"; continue; }
  name=$(basename "$m" .gguf); echo "== $name" >> "$OUT/bench.log"; echo "-- $name"
  window "metal-pp_$name" "$METAL" -m "$m" -ngl 99 -p 512 -n 0 -r 3 -o json > "$OUT/llama-bench_metal-pp_$name.json"
  window "metal-tg_$name" "$METAL" -m "$m" -ngl 99 -p 0 -n 128 -r 3 -o json > "$OUT/llama-bench_metal-tg_$name.json"
  window "idle-gap_$name" sleep 10
  window "cpu_$name" "$CPU" -m "$m" -ngl 0 -p 512 -n 128 -r 3 -t 4 -o json > "$OUT/llama-bench_cpu_$name.json"
done
test_end

# --- H: MLX ------------------------------------------------------------------------------------
test_begin H-mlx
for repo in $HMODELS; do
  name=$(basename "$repo"); echo "== $name" >> "$OUT/bench.log"; echo "-- $name"
  window "mlx_$name" "$VENV/bin/python" "$BASE/mlx_bench.py" "$repo" "$OUT/mlx_$name.json" --reps 3
  window "idle-gap_$name" sleep 10
done
test_end

echo "G/H queue $QID finished at $(date -u +%H:%M:%SZ)"
touch "$QLOG.finished"
