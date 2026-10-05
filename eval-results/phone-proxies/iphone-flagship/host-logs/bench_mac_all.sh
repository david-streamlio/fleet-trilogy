#!/usr/bin/env bash
# Everything mac2 ran, as one unattended sequence ON a Mac proxy (used for the mac-m4,
# iphone-flagship, so its 24-hour host window needs no operator). Each stage is the same
# script mac2 used; the order is mac2's, with the smoke tests first:
#   1. bench.sh --quick (abort if it produced nothing), then Phase 1 (bench.sh)
#   2. test C prep (uv sync in <repo>) and bench_workload.sh --quick (abort if it failed)
#   3. test C (bench_workload.sh)
#   4. the extras queue (bench_extras.sh: E A B D E F I E)
#   5. G and H (bench_extras_gh.sh, starting on the extras queue's .finished marker)
#   6. test C again in reverse order, then with Q4_0 weights (ORDER=reverse, QUANT=q4_0)
# Its own log: results/all-<ts>.log; results/all-<ts>.finished when done.
#
#   bench_mac_all.sh <base> <repo> <threads>
set -uo pipefail

BASE="$1"
REPO="$2"
THREADS="$3"
AID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$BASE/results/all-$AID"
mkdir -p "$BASE/results"
exec > >(tee -a "$LOG.log") 2>&1
stage() { echo "== stage $1 at $(date -u +%H:%M:%SZ)"; }
latest() { cat "$BASE/results/LATEST" 2>/dev/null; }

stage "1 smoke"
before=$(latest)
"$BASE/bench.sh" "$BASE" "$THREADS" --quick > /dev/null
[ "$(latest)" != "$before" ] && [ -s "$BASE/results/$(latest)/windows.log" ] || { echo "ABORT: bench.sh --quick produced no run"; exit 1; }
stage "1 Phase 1"
"$BASE/bench.sh" "$BASE" "$THREADS" > /dev/null
echo "Phase 1 run $(latest)"

stage "2 C prep"
command -v /opt/homebrew/bin/uv >/dev/null || /opt/homebrew/bin/brew install uv
( cd "$REPO" && /opt/homebrew/bin/uv sync ) > "$BASE/results/uv-sync-$AID.log" 2>&1 || { echo "ABORT: uv sync failed"; exit 1; }
"$BASE/bench_workload.sh" "$BASE" "$REPO" --quick
rm -f "$BASE/PAUSE"  # a quick run stays paused for its full run; nothing else is queued yet
q=$(ls -1td "$BASE"/results/C-workload-*-quick | head -1)
grep -q 'exit=0' "$q/windows.log" && ! grep -v '^idle' "$q/windows.log" | grep -qv 'exit=0' || { echo "ABORT: C smoke test failed"; exit 1; }

stage "3 C"
"$BASE/bench_workload.sh" "$BASE" "$REPO"

stage "4 extras queue"
"$BASE/bench_extras.sh" "$BASE"
marker=$(ls -1t "$BASE"/results/extras-*.finished | head -1)

stage "5 G and H"
"$BASE/bench_extras_gh.sh" "$BASE" "$marker"

stage "6 C reverse, C Q4_0"
ORDER=reverse "$BASE/bench_workload.sh" "$BASE" "$REPO"
QUANT=q4_0 "$BASE/bench_workload.sh" "$BASE" "$REPO"

stage "done"
touch "$LOG.finished"
