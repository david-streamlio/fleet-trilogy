#!/usr/bin/env bash
# Android-proxy extras (catalog L1-L7), run unattended in sequence ON a Linux proxy once its
# Phase 1 run has finished (pushed and launched by `proxyctl.sh start-extras <name> <steps>`).
# The steps are the arguments, in order: android-flagship runs L4 L1 L3 L5 L6 L7,
# android-mainstream L2 L3 L5 L6.
#   L1 RAM capacity: every model under 4/6/8/12 GiB cgroup caps (TODO-RAM-CAPACITY-TEST.md)
#   L2 phone-ISA build: llama.cpp for a Cortex-X1's instruction set, Phase 1's sweep re-run
#   L3 ARM-repacked quants: Q4_0 / IQ4_NL / Q8_0 of the Edge Triage candidates + Gemma-3-1B
#   L4 Phase 2 preview: Gemma-3-12B, Gemma-4-12B, Qwen3-14B
#   L5 context-depth sweep: 0/512/2048/4096 tokens already in context, 8 threads
#   L6 Phase 1 repeat (bench.sh): run-to-run variance
#   L7 Talk 2's real workload (tests/model/ evals), latency + accuracy; needs <repo>
# Each step writes results/<step>-<ts>/: system.txt, bench.log ("== <model>" per model),
# one llama-bench JSON per model. Graviton has no energy counters: time only.
#
#   bench_linux_extras.sh <base> <repo-for-L7> <step>...
set -uo pipefail

BASE="$1"; REPO="$2"; shift 2
STEPS="$*"
BIN="$BASE/llama.cpp/build/bin"
QID="$(date -u +%Y%m%dT%H%M%SZ)"
QLOG="$BASE/results/extras-$QID"
mkdir -p "$BASE/results"
exec > >(tee -a "$QLOG.log") 2>&1
echo "extras queue $QID ($STEPS) on $(hostname)"
until ! pgrep -f "$BASE/[b]ench.sh" >/dev/null; do sleep 60; done  # Phase 1 still running
echo "starting at $(date -u +%H:%M:%SZ)"

MODELS=()
while read -r _repo file; do
  [ -n "$file" ] && [ -f "$BASE/models/$file" ] && MODELS+=("$BASE/models/$file")
done < "$BASE/models.txt"
CANDIDATES="gemma-3-1b-it-Q4_K_M Phi-3.5-mini-instruct-Q4_K_M gemma-3-4b-it-Q4_K_M Llama-3.1-8B-Instruct-Q4_K_M GLM-4-9B-0414-Q4_K_M qwen3-8b-q4_k_m"
PHASE2="unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf
unsloth/gemma-4-12b-it-GGUF gemma-4-12b-it-Q4_K_M.gguf
unsloth/Qwen3-14B-GGUF Qwen3-14B-Q4_K_M.gguf"
# No IQ4_NL of Phi-3.5-mini is published; bartowski has the Q8_0 of Llama-3.1-8B and the
# Q4_0 of Qwen3-8B that unsloth doesn't.
QUANTS="unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-Q4_0.gguf
unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-IQ4_NL.gguf
unsloth/gemma-3-1b-it-GGUF gemma-3-1b-it-Q8_0.gguf
bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-Q4_0.gguf
bartowski/Phi-3.5-mini-instruct-GGUF Phi-3.5-mini-instruct-Q8_0.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_0.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-IQ4_NL.gguf
unsloth/gemma-3-4b-it-GGUF gemma-3-4b-it-Q8_0.gguf
unsloth/Llama-3.1-8B-Instruct-GGUF Llama-3.1-8B-Instruct-Q4_0.gguf
unsloth/Llama-3.1-8B-Instruct-GGUF Llama-3.1-8B-Instruct-IQ4_NL.gguf
bartowski/Meta-Llama-3.1-8B-Instruct-GGUF Meta-Llama-3.1-8B-Instruct-Q8_0.gguf
unsloth/GLM-4-9B-0414-GGUF GLM-4-9B-0414-Q4_0.gguf
unsloth/GLM-4-9B-0414-GGUF GLM-4-9B-0414-IQ4_NL.gguf
unsloth/GLM-4-9B-0414-GGUF GLM-4-9B-0414-Q8_0.gguf
bartowski/Qwen_Qwen3-8B-GGUF Qwen_Qwen3-8B-Q4_0.gguf
unsloth/Qwen3-8B-GGUF Qwen3-8B-IQ4_NL.gguf
unsloth/Qwen3-8B-GGUF Qwen3-8B-Q8_0.gguf"

fetch() {  # fetch <repo> <file> <dir>: download once, atomically
  [ -f "$3/$2" ] && return 0
  mkdir -p "$3"
  curl -fL --retry 5 --retry-delay 5 -sS -o "$3/$2.part" "https://huggingface.co/$1/resolve/main/$2" && mv "$3/$2.part" "$3/$2"
}
step_begin() {
  OUT="$BASE/results/$1-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$OUT"
  echo "== test $1 -> $(basename "$OUT") at $(date -u +%H:%M:%SZ)"
  { echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; env | grep '^LLAMA_ARG_'; uname -a; lscpu; free -g; } > "$OUT/system.txt" 2>&1
}
step_end() { basename "$OUT" >> "$QLOG.done"; }
model_start() { echo "== $1" >> "$OUT/bench.log"; echo "-- $1"; }
bench() {  # bench <llama-bench> <model> <threads> [extra args]: one JSON per model into $OUT
  local b="$1" m="$2" t="$3"; shift 3
  local name; name=$(basename "$m" .gguf); model_start "$name"
  "$b" -m "$m" -p 512 -n 128 -r 3 -t "$t" "$@" -o json > "$OUT/llama-bench_$name.json"
}

step_L1() {
  step_begin L1-ram-capacity
  # The weights must be resident (a phone app holds them in RAM): with mmap, an over-cap
  # model would thrash the page cache instead of failing. Use the first load mode whose
  # peak RSS covers the model file.
  local probe="${MODELS[4]}" mode="" lm rss size
  size=$(stat -c %s "$probe")
  for lm in none dio mlock; do
    rss=$(sudo /usr/bin/time -v "$BIN/llama-bench" -m "$probe" -lm "$lm" -p 16 -n 4 -r 1 -t 8 2>&1 >/dev/null | awk -F': ' '/Maximum resident set size/ {print $2}')
    echo "load mode $lm: peak RSS ${rss:-?} KB for a $((size / 1024)) KB file"
    if [ -n "$rss" ] && [ $((rss * 1024)) -ge $((size * 9 / 10)) ]; then mode=$lm; break; fi
  done
  [ -n "$mode" ] || { mode=mlock; echo "WARNING: no load mode made the weights resident; using mlock"; }
  echo "$mode" > "$OUT/load_mode.txt"
  echo "model,file_gb,peak_rss_gb,4G,6G,8G,12G" > "$OUT/fits.csv"
  for m in "${MODELS[@]}" "$BASE"/models-phase2/*.gguf; do
    [ -f "$m" ] || continue
    local name row passed="" cap rc
    name=$(basename "$m" .gguf); model_start "$name"
    rss=$(sudo /usr/bin/time -v "$BIN/llama-bench" -m "$m" -lm "$mode" -p 512 -n 16 -r 1 -t 8 -o json 2> "$OUT/uncapped_$name.time" > "$OUT/uncapped_$name.json"; awk -F': ' '/Maximum resident set size/ {print $2}' "$OUT/uncapped_$name.time")
    row="$name,$(awk -v s="$(stat -c %s "$m")" 'BEGIN {printf "%.2f", s / 1e9}'),$(awk -v r="${rss:-0}" 'BEGIN {printf "%.2f", r * 1024 / 1e9}')"
    for cap in 4G 6G 8G 12G; do
      if [ -n "$passed" ]; then row="$row,fit"; continue; fi  # fits a smaller cap, so this one
      sudo systemd-run --scope --quiet -p MemoryMax="$cap" -p MemorySwapMax=0 \
        "$BIN/llama-bench" -m "$m" -lm "$mode" -p 512 -n 16 -r 1 -t 8 -o json > "$OUT/cap${cap}_$name.json" 2> "$OUT/cap${cap}_$name.err"
      rc=$?
      if [ $rc -eq 0 ]; then row="$row,fit"; passed=1; else row="$row,fail($rc)"; fi
    done
    echo "$row" | tee -a "$OUT/fits.csv"
  done
  step_end
  rm -rf "$BASE/models-phase2"  # L4 and L1 are done with them; L3 needs the disk
}

step_L2() {
  step_begin L2-phone-isa-x1
  local src="$BASE/llama.cpp" arch="armv8.2-a+dotprod+fp16"
  # Cortex-X1: Armv8.2 with dotprod and fp16 -- no SVE, no i8mm (Graviton3 has both).
  if [ ! -x "$src/build-x1/bin/llama-bench" ]; then
    cmake -S "$src" -B "$src/build-x1" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH="$arch" \
      -DCMAKE_C_FLAGS="-march=$arch" -DCMAKE_CXX_FLAGS="-march=$arch" > "$OUT/cmake.log" 2>&1
    cmake --build "$src/build-x1" --config Release -j"$(nproc)" --target llama-bench llama-completion > "$OUT/build.log" 2>&1
  fi
  # What each build compiled in: llama.cpp lists only enabled features, so the x1 build
  # must not list SVE or MATMUL_INT8 at all.
  for b in build build-x1; do
    echo "$b: $("$src/$b/bin/llama-completion" -m "${MODELS[0]}" -p hi -n 1 -no-cnv --no-warmup 2>&1 | grep -m1 -o 'CPU : .*')" | tee -a "$OUT/cpu_features.txt"
  done
  grep '^build-x1:' "$OUT/cpu_features.txt" | grep -qE 'SVE = 1|MATMUL_INT8 = 1' \
    && echo "WARNING: the x1 build still reports SVE or MATMUL_INT8; results are not X1-faithful" | tee -a "$OUT/cpu_features.txt"
  for m in "${MODELS[@]}"; do bench "$src/build-x1/bin/llama-bench" "$m" 1,2,4,6,8; done
  step_end
}

step_L3() {
  step_begin L3-arm-quants
  # One file at a time: download, measure, delete (the Q8_0s of the 8-9B models are 9-10 GB).
  echo "$QUANTS" | while read -r repo file; do
    fetch "$repo" "$file" "$BASE/models-quant" || { echo "download failed: $file"; continue; }
    bench "$BIN/llama-bench" "$BASE/models-quant/$file" 4,8
    rm -f "$BASE/models-quant/$file"
  done
  step_end
}

step_L4() {
  step_begin L4-phase2-preview
  echo "$PHASE2" | while read -r repo file; do fetch "$repo" "$file" "$BASE/models-phase2" || echo "download failed: $file"; done
  for m in "$BASE"/models-phase2/*.gguf; do [ -f "$m" ] && bench "$BIN/llama-bench" "$m" 4,8; done
  step_end
}

step_L5() {
  step_begin L5-context-depth
  for name in $CANDIDATES; do bench "$BIN/llama-bench" "$BASE/models/$name.gguf" 8 -d 0,512,2048,4096; done
  step_end
}

step_L6() {
  echo "== test L6 (Phase 1 repeat) at $(date -u +%H:%M:%SZ)"
  "$BASE/bench.sh" "$BASE" 1,2,4,6,8 > /dev/null
  echo "L6 $(cat "$BASE/results/LATEST")" >> "$QLOG.done"
}

step_L7() {
  step_begin L7-workload
  # The same model/task pairs and flags as the mac2 workload run (bench_workload.sh), on the
  # native CPU build, 1 repetition: there's no energy to average, and each run's 60 (Edge
  # Triage) or 30 (Tier 2) calls already give the latency distribution.
  # llama-server's context defaults to the model's full training context (128k for Phi-3.5
  # and Llama-3.1): on a 16 GiB CPU host their KV caches don't fit and llama-server is
  # OOM-killed (the first L7, 2026-10-04). Metal shrinks the context to fit GPU memory; the
  # CPU path doesn't. Run with LLAMA_ARG_CTX_SIZE set (recorded in system.txt).
  local uv="$HOME/.local/bin/uv"
  [ -x "$uv" ] || curl -LsSf https://astral.sh/uv/install.sh | sh > "$OUT/uv-install.log" 2>&1
  ( cd "$REPO" && { "$uv" sync --python 3.12 || "$uv" sync --python 3.12 --no-group functions; } ) > "$OUT/uv-sync.log" 2>&1
  export LLM_BINARY_PATH_PHI35_MINI="$BIN/llama-completion" LLM_MODEL_PATH_PHI35_MINI="$BASE/models/Phi-3.5-mini-instruct-Q4_K_M.gguf"
  export LLM_BINARY_PATH_GEMMA3_4B="$BIN/llama-completion" LLM_MODEL_PATH_GEMMA3_4B="$BASE/models/gemma-3-4b-it-Q4_K_M.gguf"
  export LLM_BINARY_PATH_LLAMA31_8B="$BIN/llama-completion" LLM_MODEL_PATH_LLAMA31_8B="$BASE/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf"
  export LLM_BINARY_PATH_GLM4_9B="$BIN/llama-completion" LLM_MODEL_PATH_GLM4_9B="$BASE/models/GLM-4-9B-0414-Q4_K_M.gguf"
  export LLM_BINARY_PATH_QWEN3_8B="$BIN/llama-completion" LLM_MODEL_PATH_QWEN3_8B="$BASE/models/qwen3-8b-q4_k_m.gguf"
  local pairs="test_compare_edge_triage_models.py phi-3.5-mini-instruct-q4km 15
test_compare_tier2_models.py gemma-3-4b-it-q4km 30
test_compare_edge_triage_models.py gemma-3-4b-it-q4km 15
test_compare_edge_triage_models.py llama-3.1-8b-instruct-q4km 15
test_compare_edge_triage_models.py glm-4-9b-0414-q4km 15
test_compare_edge_triage_models.py qwen3-8b-q4km 15"
  cd "$REPO" || return
  echo "$pairs" | while read -r test id runs; do
    task=$(echo "$test" | sed -E 's/test_compare_(.*)_models\.py/\1/')
    echo "== ${task}_$id" >> "$OUT/bench.log"; echo "-- $task $id"
    before=$(ls -1 eval-results/ 2>/dev/null | sort)
    "$uv" run --no-sync pytest "tests/model/$test" -m model -s -q --only-model-ids "$id" \
      --model-eval-runs "$runs" --model-threads 8 < /dev/null > "$OUT/pytest_${task}_$id.log" 2>&1
    tail -n 3 "$OUT/pytest_${task}_$id.log"
    echo "${task}_$id $(comm -13 <(echo "$before") <(ls -1 eval-results/ | sort) | tr '\n' ' ')" >> "$OUT/artifacts.txt"
  done
  cd - > /dev/null
  step_end
}

for step in $STEPS; do
  "step_$step"
done
echo "extras queue $QID finished at $(date -u +%H:%M:%SZ)"
touch "$QLOG.finished"
