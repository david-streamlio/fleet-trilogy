#!/usr/bin/env bash
# Drive the proxies created by this Terraform stack, from this Mac.
#
#   proxyctl.sh list                 enabled proxies, IPs, what each mimics
#   proxyctl.sh ssh <name> [cmd...]  interactive shell, or run one command
#   proxyctl.sh status <name>        provisioning state (READY or the setup log tail)
#   proxyctl.sh wait <name>          block until provisioning finished (READY)
#   proxyctl.sh start <name> [--quick]   push bench.sh and launch it detached (returns at once;
#                                    the run continues on the instance if this Mac disconnects)
#   proxyctl.sh start-extras <name> [steps]  launch the extras queue, detached (Linux: L1-L7)
#   proxyctl.sh extras-progress <name>   which extras test is running, how many are done
#   proxyctl.sh progress <name>      which model the latest run is on, and whether it finished
#   proxyctl.sh bench <name> [--quick]   start, wait for it to finish, collect (short runs)
#   proxyctl.sh collect <name>       copy that proxy's results into eval-results/phone-proxies/
#   proxyctl.sh start-all            wait for each enabled proxy to be READY, then start it
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
OUTPUTS="$(cd "$HERE" && terraform output -json 2>/dev/null)" || { echo "no terraform outputs - run terraform apply first" >&2; exit 1; }
KEY="$(echo "$OUTPUTS" | jq -r .ssh_key_path.value)"
case "$KEY" in /*) ;; *) KEY="$HERE/${KEY#./}" ;; esac
SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HERE/.ssh/known_hosts" -o ConnectTimeout=10 -o ServerAliveInterval=30)

field() { echo "$OUTPUTS" | jq -r --arg n "$1" --arg f "$2" '.proxies.value[$n][$f] // empty'; }
target() { echo "$(field "$1" user)@$(field "$1" ip)"; }
remote() { local n="$1"; shift; ssh "${SSH_OPTS[@]}" "$(target "$n")" "$@"; }
need() { [ -n "$(field "$1" ip)" ] || { echo "unknown or disabled proxy: $1" >&2; exit 1; }; }
# push <name> <dir> <file>...: copy to a temporary name, then rename into place. bash reads a
# script as it runs it, so overwriting one in place corrupts any run still executing it (it
# did: Phase 1 on android-mainstream); a rename leaves that run on the old file.
push() {
  local n="$1" dir="$2" f; shift 2
  for f in "$@"; do
    scp "${SSH_OPTS[@]}" -q "$f" "$(target "$n"):$dir/.$(basename "$f").new" || return 1
    remote "$n" "mv -f $dir/.$(basename "$f").new $dir/$(basename "$f")" || return 1
  done
}

cmd="${1:-list}"; shift || true
case "$cmd" in
  list)
    echo "$OUTPUTS" | jq -r '.proxies.value | to_entries[] | "\(.key)\t\(.value.instance_type)\t\(.value.ip)\t\(.value.mimics)"' | column -t -s $'\t'
    ;;
  ssh)
    need "$1"; n="$1"; shift; ssh "${SSH_OPTS[@]}" "$(target "$n")" "$@"
    ;;
  status)
    need "$1"; base=$(field "$1" base)
    remote "$1" "if [ -f $base/READY ]; then echo READY since \$(cat $base/READY); else echo provisioning...; sudo tail -n 5 /var/log/phone-proxy-setup.log 2>/dev/null; fi"
    ;;
  wait)
    need "$1"; base=$(field "$1" base)
    until remote "$1" "test -f $base/READY" 2>/dev/null; do sleep 30; done
    echo "$1 READY"
    ;;
  start)
    need "$1"; n="$1"; base=$(field "$n" base); threads=$(field "$n" bench_threads); quick="${2:-}"
    if remote "$n" "pgrep -f '$base/[b]ench.sh' >/dev/null"; then echo "$n: a run is already in progress" >&2; exit 1; fi
    push "$n" "$base" "$HERE/scripts/bench.sh"
    # Not nohup: macOS's refuses to start without a console over a non-tty ssh session.
    # Ignoring HUP (inherited across exec) and detaching all three fds does the same job.
    remote "$n" "chmod +x $base/bench.sh && mkdir -p $base/results && cat $base/results/LATEST > $base/results/.before 2>/dev/null; ( trap '' HUP; exec $base/bench.sh $base $threads $quick ) > $base/bench.nohup 2>&1 < /dev/null &"
    sleep 3
    if ! remote "$n" "pgrep -f '$base/[b]ench.sh' >/dev/null"; then
      echo "$n: bench.sh did not start:" >&2; remote "$n" "cat $base/bench.nohup" >&2; exit 1
    fi
    echo "$n started"
    ;;
  start-extras)
    # Detached like start. macOS: the bench_extras.sh queue (catalog tests E A B D E F I E).
    # Linux: bench_linux_extras.sh with the given steps (L1-L7), which waits for Phase 1 itself;
    # L7 runs the evals from ~/fleet-trilogy on the instance (copy the repo there first).
    need "$1"; n="$1"; shift; base=$(field "$n" base)
    if [ "$(field "$n" os)" = macos ]; then
      if remote "$n" "pgrep -f '$base/[b]ench' >/dev/null"; then echo "$n: a run is already in progress" >&2; exit 1; fi
      script=bench_extras.sh; args="$base"
    else
      [ $# -gt 0 ] || { echo "usage: proxyctl.sh start-extras <linux-proxy> <step>... (L1-L7)" >&2; exit 1; }
      script=bench_linux_extras.sh; args="$base \$HOME/fleet-trilogy $*"
    fi
    push "$n" "$base" "$HERE/scripts/bench.sh" "$HERE/scripts/$script"
    remote "$n" "chmod +x $base/bench.sh $base/$script; ( trap '' HUP; exec $base/$script $args ) > $base/extras.nohup 2>&1 < /dev/null &"
    sleep 3
    if ! remote "$n" "pgrep -f '$base/[b]${script#b}' >/dev/null"; then
      echo "$n: $script did not start:" >&2; remote "$n" "cat $base/extras.nohup" >&2; exit 1
    fi
    echo "$n extras started"
    ;;
  extras-progress)
    need "$1"; base=$(field "$1" base)
    remote "$1" "q=\$(ls -1t $base/results/extras-*.log 2>/dev/null | head -1); [ -n \"\$q\" ] || { echo 'no extras queue yet'; exit 0; }; \
      echo \"queue \$(basename \$q .log): \$(cat \${q%.log}.done 2>/dev/null | wc -l | tr -d ' ') tests done\$( [ -f \${q%.log}.finished ] && echo ', finished')\"; \
      grep -E '^(== test|paused|extras queue)' \$q | tail -3; tail -n 1 \$q"
    ;;
  progress)
    need "$1"; n="$1"; base=$(field "$n" base)
    remote "$n" "run=\$(ls -1t $base/results 2>/dev/null | grep -E '^[0-9]{8}T' | head -1); log=$base/results/\$run/bench.log; \
      if [ -z \"\$run\" ]; then echo \"$n: no run yet\"; exit 0; fi; \
      if pgrep -f '$base/[b]ench.sh' >/dev/null; then state=running; else state=finished; fi; \
      echo \"$n: \$state, run \$run, \$(grep -c '^== ' \$log 2>/dev/null) of \$(grep -oE 'models: [0-9]+' \$log | grep -oE '[0-9]+') models started\"; grep '^== ' \$log | tail -1"
    ;;
  bench)
    need "$1"; n="$1"; base=$(field "$n" base)
    "$0" start "$@" || exit 1
    sleep 5
    while remote "$n" "pgrep -f '$base/[b]ench.sh' >/dev/null"; do sleep 30; done
    "$0" collect "$n"
    ;;
  collect)
    need "$1"; n="$1"; base=$(field "$n" base)
    dest="$REPO_ROOT/eval-results/phone-proxies/$n"
    mkdir -p "$dest"
    rsync -az -e "ssh ${SSH_OPTS[*]}" "$(target "$n"):$base/results/" "$dest/"
    # Power traces are committed gzipped (eval-results/phone-proxies/.gitignore skips the raw .txt).
    find "$dest" -name powermetrics.txt | while read -r f; do [ -f "$f.gz" ] && ! [ "$f" -nt "$f.gz" ] || gzip -9 -k -f "$f"; done  # gzip -k keeps the mtime
    echo "$n results -> $dest/$(remote "$n" "cat $base/results/LATEST" 2>/dev/null)"
    ;;
  start-all)
    for n in $(echo "$OUTPUTS" | jq -r '.proxies.value | keys[]'); do
      ( "$0" wait "$n" && "$0" start "$n" ) > "$HERE/.bench-$n.log" 2>&1 &
    done
    wait
    cat "$HERE"/.bench-*.log
    ;;
  *)
    sed -n '/^#   proxyctl.sh/p' "$0"; exit 1
    ;;
esac
