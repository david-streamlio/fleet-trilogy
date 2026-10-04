#!/usr/bin/env bash
# Collect each enabled proxy's results as soon as all of its queues have finished, so
# nothing is lost if the operator is away (or a host auto-stops). Run from this Mac:
#
#   collect_when_done.sh [max-minutes]     (default 110; exits 0 when every host is done)
#
# "Done" = no benchmark process running on the host and every queue log (extras-*.log,
# queue-gh-*.log) has its .finished marker. Then, once per host:
#   1. sha256 of the model files still on the host -> results/model-sha256.txt, to check
#      against MODELS.lock.tsv (runs after the queues, so it can't disturb a measurement);
#   2. proxyctl.sh collect (rsync + gzip of power traces);
#   3. the eval artifacts in ~/fleet-trilogy/eval-results/ (tests C and L7), if any, into
#      eval-results/phone-proxies/<key>/<C|L7>-artifacts/.
# Hosts already collected by this script are recorded in .collected-<key> and skipped.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
CTL="$HERE/scripts/proxyctl.sh"
DEADLINE=$(( $(date +%s) + ${1:-110} * 60 ))
KEY="$HERE/.ssh/fleet-phone-proxy-ed25519"

hosts=$(cd "$HERE" && terraform output -json proxies | jq -r 'keys[]')
field() { (cd "$HERE" && terraform output -json proxies) | jq -r --arg n "$1" --arg f "$2" '.[$n][$f]'; }

done_check='pgrep -f "[b]ench" >/dev/null && exit 1; for q in BASE/results/extras-*.log BASE/results/queue-gh-*.log; do [ -e "$q" ] || continue; [ -f "${q%.log}.finished" ] || exit 1; done; exit 0'

while :; do
  pending=0
  for n in $hosts; do
    [ -f "$HERE/.collected-$n" ] && continue
    base=$(field "$n" base); user=$(field "$n" user); ip=$(field "$n" ip)
    if ! "$CTL" ssh "$n" "${done_check//BASE/$base}" 2>/dev/null; then pending=$((pending + 1)); continue; fi
    echo "$(date -u +%H:%M:%SZ) $n: all queues finished, collecting"
    "$CTL" ssh "$n" "cd $base && if command -v sha256sum >/dev/null; then H=sha256sum; else H='shasum -a 256'; fi; for f in models/*.gguf models-*/*.gguf; do [ -f \"\$f\" ] && \$H \"\$f\"; done > results/model-sha256.txt; wc -l < results/model-sha256.txt" 2>/dev/null | sed "s/^/  model hashes: /"
    "$CTL" collect "$n" 2>/dev/null | tail -1
    case "$n" in iphone-older) sub=C-artifacts ;; android-flagship) sub=L7-artifacts ;; *) sub="" ;; esac
    if [ -n "$sub" ] && "$CTL" ssh "$n" "test -d ~/fleet-trilogy/eval-results" 2>/dev/null; then
      mkdir -p "$REPO_ROOT/eval-results/phone-proxies/$n/$sub"
      rsync -az -e "ssh -i $KEY -o UserKnownHostsFile=$HERE/.ssh/known_hosts" "$user@$ip:fleet-trilogy/eval-results/" "$REPO_ROOT/eval-results/phone-proxies/$n/$sub/"
      echo "  eval artifacts: $(ls "$REPO_ROOT/eval-results/phone-proxies/$n/$sub" | wc -l | tr -d ' ') files in $sub/"
    fi
    date -u +%Y-%m-%dT%H:%M:%SZ > "$HERE/.collected-$n"
  done
  [ "$pending" -eq 0 ] && { echo "$(date -u +%H:%M:%SZ) every host collected"; exit 0; }
  [ "$(date +%s)" -ge "$DEADLINE" ] && { echo "$(date -u +%H:%M:%SZ) deadline: $pending host(s) still running"; exit 0; }
  sleep 120
done
