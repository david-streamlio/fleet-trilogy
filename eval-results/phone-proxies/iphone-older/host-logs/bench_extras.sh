#!/usr/bin/env bash
# Extra tests that use the rest of a Mac host's 24-hour minimum, run unattended in sequence
# ON the Mac (pushed and launched by `proxyctl.sh start-extras`). The letters are the test
# catalog's (docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md):
#   E  Phase 1 repeat (bench.sh)      - run at the start, the middle and the end: error bars
#   A  CPU thread sweep 1/2/4/6/8     - M1 and A14 share core designs (4+4 vs 2+4 cores)
#   B  STREAM by thread count         - measured M1 bandwidth, comparable with the Linux proxies
#   D  context-depth sweep (Metal)    - speed at 0/512/2048/4096 tokens already in context
#   F  sustained generation (~20 min per run) with the thermal sampler
#   I  Phase 2 preview: 12-14B models on M1, the "2020 laptop" point
# Each test writes results/<test>-<ts>/ in bench.sh's layout (powermetrics.txt, windows.log,
# one llama-bench JSON per run), bracketed by 30 s idle windows for the idle baseline.
# Touch $BASE/PAUSE to hold the queue between tests (e.g. to install something without
# disturbing a measurement); remove it to resume.
#
#   bench_extras.sh <base>
set -uo pipefail

BASE="$1"
METAL="$BASE/llama.cpp/build/bin/llama-bench"
CPU="$BASE/llama.cpp/build-cpu/bin/llama-bench"
QID="$(date -u +%Y%m%dT%H%M%SZ)"
QLOG="$BASE/results/extras-$QID"
mkdir -p "$BASE/results"
exec > >(tee -a "$QLOG.log") 2>&1
echo "extras queue $QID on $(hostname)"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {  # window <label> <command...>: run it, logging its epoch start/end to windows.log
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}
hold() { [ -f "$BASE/PAUSE" ] && echo "paused ($(date -u +%H:%M:%SZ))"; while [ -f "$BASE/PAUSE" ]; do sleep 10; done; }

MODELS=()
while read -r _repo file; do
  [ -n "$file" ] && [ -f "$BASE/models/$file" ] && MODELS+=("$BASE/models/$file")
done < "$BASE/models.txt"

PHASE2="unsloth/gemma-3-12b-it-GGUF gemma-3-12b-it-Q4_K_M.gguf
unsloth/gemma-4-12b-it-GGUF gemma-4-12b-it-Q4_K_M.gguf
unsloth/Qwen3-14B-GGUF Qwen3-14B-Q4_K_M.gguf"

PM_PID=""
test_begin() {  # test_begin <name> [extra powermetrics sampler]: results dir, powermetrics, idle-pre
  hold
  OUT="$BASE/results/$1-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$OUT"
  echo "== test $1 -> $(basename "$OUT") at $(date -u +%H:%M:%SZ)"
  { echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt")"; uname -a; sysctl -n machdep.cpu.brand_string; } > "$OUT/system.txt"
  sudo powermetrics --samplers "cpu_power,gpu_power${2:+,$2}" -i 500 -o "$OUT/powermetrics.txt" &
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
model_start() { echo "== $1" >> "$OUT/bench.log"; echo "-- $1"; }

prep() {  # not measured: STREAM build, Phase 2 downloads, Metal shader warm-up
  if [ ! -x "$BASE/stream" ]; then
    /opt/homebrew/bin/brew install libomp
    local omp; omp=$(/opt/homebrew/bin/brew --prefix libomp)
    curl -fsSL --retry 5 -o "$BASE/stream.c" https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c
    # 80M elements (1.9 GB of arrays, ~240x M1's caches): Mach-O can't hold the Linux
    # proxies' 200M (4.8 GB) of static arrays. Bandwidth past the caches doesn't depend on it.
    clang -O3 -mcpu=native -Xpreprocessor -fopenmp -I"$omp/include" -L"$omp/lib" -lomp \
      -DSTREAM_ARRAY_SIZE=80000000 -DNTIMES=20 "$BASE/stream.c" -o "$BASE/stream"
  fi
  mkdir -p "$BASE/models-phase2"
  echo "$PHASE2" | while read -r repo file; do
    [ -f "$BASE/models-phase2/$file" ] && continue
    curl -fL --retry 5 --retry-delay 5 -sS -o "$BASE/models-phase2/$file.part" "https://huggingface.co/$repo/resolve/main/$file" \
      && mv "$BASE/models-phase2/$file.part" "$BASE/models-phase2/$file"
  done
  "$METAL" -m "${MODELS[0]}" -ngl 99 -p 16 -n 4 -r 1 > /dev/null 2>&1
}

test_E() {
  hold
  echo "== test E (Phase 1 repeat) at $(date -u +%H:%M:%SZ)"
  "$BASE/bench.sh" "$BASE" 4 > /dev/null
  echo "E $(cat "$BASE/results/LATEST")" >> "$QLOG.done"
}

test_A() {
  test_begin A-cpu-threads
  for m in "${MODELS[@]}"; do
    name=$(basename "$m" .gguf); model_start "$name"
    for t in 1 2 4 6 8; do
      window "cpu-t${t}_$name" "$CPU" -m "$m" -ngl 0 -p 512 -n 128 -r 3 -t "$t" -o json > "$OUT/llama-bench_cpu-t${t}_$name.json"
    done
  done
  test_end
}

test_B() {
  test_begin B-stream
  for t in 1 2 4 6 8; do
    window "stream-t$t" env OMP_NUM_THREADS="$t" "$BASE/stream" > "$OUT/stream_t$t.txt" 2>&1
    echo "STREAM t=$t: $(grep -E '^Triad' "$OUT/stream_t$t.txt")"
  done
  test_end
}

test_D() {
  test_begin D-context-depth
  for m in "${MODELS[@]}"; do
    name=$(basename "$m" .gguf); model_start "$name"
    for d in 0 512 2048 4096; do
      # llama-bench re-fills the d-token context (untimed) before every repetition, so
      # these windows interleave prefill with the timed test: speed is exact, energy isn't.
      window "metal-pp-d${d}_$name" "$METAL" -m "$m" -ngl 99 -p 512 -n 0 -d "$d" -r 3 -o json > "$OUT/llama-bench_metal-pp-d${d}_$name.json"
      window "metal-tg-d${d}_$name" "$METAL" -m "$m" -ngl 99 -p 0 -n 128 -d "$d" -r 3 -o json > "$OUT/llama-bench_metal-tg-d${d}_$name.json"
    done
  done
  test_end
}

test_F() {
  test_begin F-sustained thermal
  # <model> <metal|cpu> <repetitions of tg512>: repetitions sized from Phase 1 speeds to
  # ~20 min each; samples_ns keeps every repetition's time, so drift is visible.
  for spec in "gemma-3-1b-it-Q4_K_M metal 140" "Llama-3.2-3B-Instruct-Q4_K_M metal 65" \
              "Llama-3.1-8B-Instruct-Q4_K_M metal 30" "Llama-3.2-3B-Instruct-Q4_K_M cpu 65"; do
    set -- $spec
    model_start "$1"
    if [ "$2" = metal ]; then
      window "sustained-metal_$1" "$METAL" -m "$BASE/models/$1.gguf" -ngl 99 -p 0 -n 512 -r "$3" -o json > "$OUT/llama-bench_sustained-metal_$1.json"
    else
      window "sustained-cpu_$1" "$CPU" -m "$BASE/models/$1.gguf" -ngl 0 -p 0 -n 512 -r "$3" -t 4 -o json > "$OUT/llama-bench_sustained-cpu_$1.json"
    fi
    window "cooldown_$2_$1" sleep 120
  done
  test_end
}

test_I() {
  test_begin I-phase2-preview
  for file in $(echo "$PHASE2" | awk '{print $2}'); do
    m="$BASE/models-phase2/$file"
    [ -f "$m" ] || { echo "missing $m"; continue; }
    name=$(basename "$m" .gguf); model_start "$name"
    # Same four windows per model as bench.sh's Phase 1.
    window "metal-pp_$name" "$METAL" -m "$m" -ngl 99 -p 512 -n 0 -r 3 -o json > "$OUT/llama-bench_metal-pp_$name.json"
    window "metal-tg_$name" "$METAL" -m "$m" -ngl 99 -p 0 -n 128 -r 3 -o json > "$OUT/llama-bench_metal-tg_$name.json"
    window "idle-gap_$name" sleep 10
    window "cpu_$name" "$CPU" -m "$m" -ngl 0 -p 512 -n 128 -r 3 -t 4 -o json > "$OUT/llama-bench_cpu_$name.json"
  done
  test_end
}

prep
for step in E A B D E F I E; do
  "test_$step"
done
echo "extras queue $QID finished at $(date -u +%H:%M:%SZ)"
touch "$QLOG.finished"
