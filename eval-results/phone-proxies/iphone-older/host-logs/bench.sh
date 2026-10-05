#!/usr/bin/env bash
# Phase 1 benchmark, run ON a proxy (pushed and launched by proxyctl.sh). Results go to
# $BASE/results/<run-id>/: system info, STREAM (Linux), one llama-bench JSON per model and
# build, and on macOS a powermetrics trace plus windows.log (epoch start/end per run) so
# energy can be attributed to prompt processing and generation separately.
#
#   bench.sh <base> <threads-csv> [--quick]
#
# --quick: smallest model only, 1 repetition — to shake out bugs before the full run.
set -uo pipefail

BASE="$1"
THREADS="$2"
QUICK="${3:-}"
REPS=3
PROMPT=512
GEN=128
[ "$QUICK" = "--quick" ] && REPS=1

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BASE/results/$RUN_ID"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/bench.log") 2>&1
echo "run $RUN_ID on $(hostname), threads=$THREADS reps=$REPS quick=${QUICK:-no}"

now() { python3 -c 'import time; print(f"{time.time():.3f}")'; }
window() {  # window <label> <command...>: run it, logging its epoch start/end to windows.log
  local label="$1"; shift
  local t0; t0=$(now)
  "$@"
  local rc=$?
  echo "$label start=$t0 end=$(now) exit=$rc" >> "$OUT/windows.log"
  return $rc
}

MODELS=()
while read -r _repo file; do
  [ -n "$file" ] && [ -f "$BASE/models/$file" ] && MODELS+=("$BASE/models/$file")
done < "$BASE/models.txt"
if [ "$QUICK" = "--quick" ]; then
  MODELS=("$(ls -S "${MODELS[@]}" | tail -n1)")  # smallest file
fi
echo "models: ${#MODELS[@]}"

# --- system info -----------------------------------------------------------------------
{
  echo "llama.cpp commit: $(cat "$BASE/llama_cpp_commit.txt" 2>/dev/null)"
  uname -a
  if [ "$(uname)" = Linux ]; then lscpu; free -g; else sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize; system_profiler SPHardwareDataType 2>/dev/null | sed -n '1,20p' | grep -vE 'Serial Number|Hardware UUID|Provisioning UDID'; fi  # no host identifiers in published data
} > "$OUT/system.txt" 2>&1

if [ "$(uname)" = Linux ]; then
  # --- memory bandwidth, per thread count (the phone-bandwidth correction) -------------
  for t in ${THREADS//,/ }; do
    OMP_NUM_THREADS=$t OMP_PROC_BIND=close "$BASE/stream" > "$OUT/stream_t$t.txt" 2>&1
    echo "STREAM t=$t: $(grep -E '^Triad' "$OUT/stream_t$t.txt")"
  done

  BENCH="$BASE/llama.cpp/build/bin/llama-bench"
  for m in "${MODELS[@]}"; do
    name=$(basename "$m" .gguf)
    echo "== $name"
    window "$name" "$BENCH" -m "$m" -p $PROMPT -n $GEN -r $REPS -t "$THREADS" -o json > "$OUT/llama-bench_$name.json"
  done
else
  # --- macOS: powermetrics for the whole run; pp and tg as separate windows ------------
  # Warm-up outside any window: the first Metal launch compiles its shaders (~25 s of CPU
  # power on mac2), which would otherwise land in the first model's metal-pp energy.
  "$BASE/llama.cpp/build/bin/llama-bench" -m "${MODELS[0]}" -ngl 99 -p 16 -n 4 -r 1 > /dev/null 2>&1
  sudo powermetrics --samplers cpu_power,gpu_power -i 500 -o "$OUT/powermetrics.txt" &
  PM_PID=$!
  sleep 5
  window idle-pre sleep 30
  for m in "${MODELS[@]}"; do
    name=$(basename "$m" .gguf)
    echo "== $name"
    # Metal (GPU) — the path llama.cpp-based iPhone apps use.
    window "metal-pp_$name" "$BASE/llama.cpp/build/bin/llama-bench" -m "$m" -ngl 99 -p $PROMPT -n 0 -r $REPS -o json > "$OUT/llama-bench_metal-pp_$name.json"
    window "metal-tg_$name" "$BASE/llama.cpp/build/bin/llama-bench" -m "$m" -ngl 99 -p 0 -n $GEN -r $REPS -o json > "$OUT/llama-bench_metal-tg_$name.json"
    window "idle-gap_$name" sleep 10
    # CPU-only — like-for-like with the Graviton proxies.
    window "cpu_$name" "$BASE/llama.cpp/build-cpu/bin/llama-bench" -m "$m" -ngl 0 -p $PROMPT -n $GEN -r $REPS -t "$THREADS" -o json > "$OUT/llama-bench_cpu_$name.json"
  done
  window idle-post sleep 30
  # Signal powermetrics itself (sudo's child): sudo won't relay a signal sent from its own
  # process group, which is this script's, so `sudo kill -INT $PM_PID` hangs the wait.
  sudo pkill -INT -P "$PM_PID" -x powermetrics
  wait "$PM_PID" 2>/dev/null
fi

echo "done $RUN_ID"
echo "$RUN_ID" > "$BASE/results/LATEST"
