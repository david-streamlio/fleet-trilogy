# Reproducing the hardware-spectrum benchmarks

Step-by-step instructions for re-running every test in `docs/TALK2-HARDWARE-SPECTRUM-TEST-LOG.md` from scratch, in another AWS account, to check the results independently.
- The log explains each test's purpose and method and every incident.
- This file covers *how to run it*.
- Pinned versions are below; model files are pinned in `MODELS.lock.tsv`.

The original runs were 2026-10-03/04, and their outputs are in `eval-results/phone-proxies/`. Compare a re-run against those, with the scripts in §8.

## 1. Pinned environment

| Component | Version used | Notes |
|---|---|---|
| llama.cpp | tag `v0.5.0` = commit `7fe450e19305b828c199d602c23a8337aaa1f03b` | `variables.tf: llama_cpp_ref`. `c13fcbf6` is the annotated tag object, not the commit |
| This repo (eval harness) | commit `c5ce03dcfdf29237cec9f01d0fbe3deea2c76122` | `tests/model/`, `shared/`, `models.toml` were unmodified at copy time |
| Terraform | 1.16.4 | providers locked in `.terraform.lock.hcl`: aws 6.67.0, http 3.6.2, local 2.9.1, time 0.14.2, tls 4.4.1 |
| Region / AZs | us-west-2; Linux and default in us-west-2a; mac2 in us-west-2c | us-west-1 has no C9g and no Mac hosts. Mac capacity varies by AZ (log, incident 6) |
| Linux AMI | `ami-0199d7a6ee12a6636`, Ubuntu 26.04.1 LTS arm64 | resolved from SSM `/aws/service/canonical/ubuntu/server/26.04/stable/current/arm64/hvm/ebs-gp3/ami-id` on 2026-10-03. To pin it, replace `data.aws_ssm_parameter.ubuntu_arm64.value` with this ID |
| Linux toolchain | kernel 7.0.0-1014-aws; GCC 15.2.0 (Ubuntu 15.2.0-16ubuntu1); CMake 4.2.3; Python 3.14.4 | from `apt` at first boot (`templates/linux_user_data.sh.tftpl`) |
| macOS AMI | `ami-0b2ea1252252f73c3` = `amzn-ec2-macos-26.7-20260918-025529-arm64` (macOS 26.7, 25G229) | `data.aws_ami.macos` picks the newest `amzn-ec2-macos-26.7*`. Pin by ID to reproduce exactly |
| macOS toolchain (mac2) | Apple clang 21.0.0 (clang-2100.3.34.2); Homebrew CMake 4.4.4, jq 1.8.2, libomp 23.1.2, uv 0.12.22 | |
| Harness Python | mac2 3.14.8; c9g 3.12.15 (`uv sync --python 3.12`); M4 Max 3.14.7 | `uv.lock` pins packages; the interpreters differed (see the log) |
| uv | 0.12.22 (macOS), 0.12.23 (c9g, astral.sh installer) | |
| MLX | mlx-lm 0.32.0, mlx 0.32.3 | `uv pip install "mlx-lm==0.32.0"` into a Python 3.12 venv |
| M4 Max | macOS 26.7.1 (25G241); Apple clang 21.0.0; CMake 4.4.4; uv 0.12.22 | MacBook Pro, M4 Max, 64 GB |
| STREAM | `jeffhammond/STREAM` `stream.c`, master on 2026-10-03 | Linux `-DSTREAM_ARRAY_SIZE=200000000`; macOS `80000000` (Mach-O limit) |

**Model files:** `MODELS.lock.tsv` gives each file's repo, revision, size and SHA-256 (from `scripts/models_lock.py`).
- The hosts downloaded from `huggingface.co/<repo>/resolve/main/<file>`.
- To reproduce exactly, use `resolve/<revision>/<file>` and check the hash with `sha256sum` / `shasum -a 256`.

## 2. Prerequisites and cost

**An AWS account with:**
- Rights to create a VPC, EC2 instances, Dedicated Hosts and key pairs. The original account used an SSO power-user role.
- Quotas: on-demand Graviton vCPUs (24 for three 8-vCPU proxies); **Mac dedicated hosts ≥ 1 for mac2.metal**, which is quota-limited.

**Tools:**
- Terraform 1.16.4, AWS CLI v2, `jq`, `rsync`, `ssh`, Python 3.9+ locally.
- For the M4 Max part: a Mac with Homebrew, `cmake` and `uv`, plus `sudo` for `powermetrics`.

**Cost and time (us-west-2, on-demand, 2026-10):**

| Stage | Hosts | Wall time | Cost |
|---|---|---|---|
| Phase 1, Linux | c6g/c7g/c9g.2xlarge ($0.27-0.35/h each) | 1.6-2.8 h | ~$3 |
| Android extras L1-L7 | c9g + c7g | ~8 h each | ~$5 |
| **mac2** (Phase 1, C, the extras queue, G/H) | mac2.metal | ~13 h of work | **≥ $15.60: a 24 h minimum from host allocation, irreversible** |
| M4 Max reruns | your own Mac | ~30 min | — |

Total: **≈ $25-30**, plus EBS storage until `terraform destroy`.

## 3. Bring up the stack

```bash
git clone <this repo> && cd fleet-trilogy && git checkout c5ce03dcfdf29237cec9f01d0fbe3deea2c76122   # harness
# then copy deploy/aws-phone-proxies/ (and these docs) from the commit that added them
cd deploy/aws-phone-proxies
export AWS_PROFILE=<your profile>          # variables.tf: aws_profile (default advocacy-dev)
terraform init                             # uses .terraform.lock.hcl

# Linux proxies (the original also had pi5 = c6g; it was removed after Phase 1)
terraform apply -var 'enabled_proxies=["pi5","android-mainstream","android-flagship"]'
scripts/proxyctl.sh list
```

**First boot:**
- Each Linux instance installs packages, clones and builds llama.cpp (`-DGGML_NATIVE=ON`), builds STREAM, and downloads the 17 Phase 1 models (~39 GB at 20-40 MB/s).
- It writes `/opt/phoneproxy/READY` when done, after ~30-40 min. Watch with `scripts/proxyctl.sh status <key>`.
- Each auto-stops 24 h after boot.

**The Mac.** It allocates a Dedicated Host, and billing starts immediately:

```bash
terraform apply -var 'enabled_proxies=["pi5","android-mainstream","android-flagship","iphone-older"]'
```

- If AllocateHosts hangs retrying `InsufficientHostCapacity`, interrupt it. The AWS error (visible in CloudTrail `AllocateHosts`) names an AZ with capacity. Set `availability_zone` on that proxy in `variables.tf` and re-apply; the original used us-west-2c.
- First boot runs ~15-20 min: Command Line Tools if missing, Homebrew cmake/jq, Metal build + CPU-only build, models.
- **Before any apply:** check the plan says `0 to change, 0 to destroy` for running proxies, and keep `enabled_proxies` equal to what's deployed.

## 4. Phase 1 (identical models, every platform)

```bash
# one-platform smoke test first (smallest model, 1 rep)
scripts/proxyctl.sh bench android-flagship --quick
# then everything in parallel; each run is detached on its host, no AWS credentials needed after this
scripts/proxyctl.sh start-all
scripts/proxyctl.sh progress <key>        # which model; "finished" when done
scripts/proxyctl.sh collect <key>         # rsync to eval-results/phone-proxies/<key>/
```

- Mac: `scripts/proxyctl.sh bench iphone-older --quick` first, then `scripts/proxyctl.sh start iphone-older`.
- `bench.sh` holds the per-platform parameters: llama-bench `-p 512 -n 128 -r 3`; thread sweeps from `variables.tf: bench_threads`.

## 5. mac2 follow-on tests

**The extras queue (E A B D E F I E):**

```bash
scripts/proxyctl.sh start-extras iphone-older
scripts/proxyctl.sh extras-progress iphone-older
```

**Test C, Talk 2's real workload.** It runs inside a pause of the queue:
1. Copy the repo source (no `.git`, `docs`, `eval-results`, `deploy`, media) to the Mac:
   ```bash
   tar czf - --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache \
     --exclude ./eval-results --exclude ./deploy --exclude ./docs --exclude './talks/*/images' --exclude './talks/*/slides' . \
     | ssh -i .ssh/fleet-phone-proxy-ed25519 ec2-user@<mac2-ip> 'mkdir -p ~/fleet-trilogy && tar xzf - -C ~/fleet-trilogy'
   ```
   (macOS's built-in `rsync`, openrsync, mis-parses `user@host:path` destinations; use tar.)
2. Pause the queue: `touch ~/phoneproxy/PAUSE`. It holds between tests, so wait until no `powermetrics` and no `bench.sh` are running.
3. Install: `brew install uv`, then `cd ~/fleet-trilogy && uv sync`.
4. Copy `scripts/bench_workload.sh` to `~/phoneproxy/`.
5. Smoke test: `~/phoneproxy/bench_workload.sh ~/phoneproxy ~/fleet-trilogy --quick`. It stays paused afterwards.
6. Full run: `~/phoneproxy/bench_workload.sh ~/phoneproxy ~/fleet-trilogy`. It removes `PAUSE` when done, which resumes the queue.
7. Pull the eval artifacts: `rsync -az -e "ssh -i .ssh/fleet-phone-proxy-ed25519" ec2-user@<ip>:fleet-trilogy/eval-results/ ../../eval-results/phone-proxies/iphone-older/C-artifacts/`.

**G and H** start themselves once the extras queue writes its `.finished` marker:
```bash
scp scripts/bench_extras_gh.sh scripts/mlx_bench.py ec2-user@<ip>:phoneproxy/
ssh ... 'B=~/phoneproxy; ( trap "" HUP; exec $B/bench_extras_gh.sh $B $B/results/extras-<QID>.finished ) > $B/extras-gh.nohup 2>&1 < /dev/null &'
```
To smoke-test MLX in the C pause: `uv venv --python 3.12 ~/phoneproxy/mlx-venv && uv pip install --python ~/phoneproxy/mlx-venv/bin/python "mlx-lm==0.32.0"`, then `mlx_bench.py mlx-community/gemma-3-1b-it-4bit /tmp/x.json --reps 1`.

## 6. Android-proxy extras (L1-L7)

```bash
# L7 needs the repo on c9g (same tar command, ubuntu@<c9g-ip>)
scripts/proxyctl.sh start-extras android-flagship L4 L1 L3 L5 L6 L7
scripts/proxyctl.sh start-extras android-mainstream L2 L3 L5 L6
```

- Each queue waits for its host's Phase 1 to finish.
- `proxyctl.sh` pushes scripts by copy-then-rename. Never `scp` over a script a running job is using (log, incident 9).

**L7 with a fixed context.** The backend starts `llama-server` without `-c`, so Phi-3.5 and Llama-3.1 get 128k contexts and are OOM-killed on a 16 GiB CPU host (incident 14). The original kept that run as a finding, then re-ran with:
```bash
ssh ubuntu@<c9g-ip> 'LLAMA_ARG_CTX_SIZE=8192 /opt/phoneproxy/bench_linux_extras.sh /opt/phoneproxy $HOME/fleet-trilogy L7'
```
Run it detached, after the first queue's `.finished` marker. Then pull `~/fleet-trilogy/eval-results/` into `eval-results/phone-proxies/android-flagship/L7-artifacts/`.

## 7. M4 Max reruns (or any other Mac you want on the spectrum)

```bash
git clone --depth 1 --branch v0.5.0 https://github.com/ggml-org/llama.cpp ~/tools/llama.cpp-v0.5.0
cd ~/tools/llama.cpp-v0.5.0 && cmake -B build -DCMAKE_BUILD_TYPE=Release \
  && cmake --build build --config Release -j"$(sysctl -n hw.ncpu)" --target llama-completion llama-server llama-bench
# models where models.toml's defaults expect them: ~/tools/models/<repo-dir>/<file> (MODELS.lock.tsv)
# in a separate terminal (needs sudo; add `thermal` to see thermal pressure):
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 500 -o /tmp/m4max-powermetrics.txt
# plugged in (the script refuses battery), nothing else heavy running:
deploy/aws-phone-proxies/scripts/bench_workload_m4max.sh "$PWD" "$PWD/eval-results/phone-proxies/m4max-macbook/$(date -u +%Y%m%dT%H%M%SZ)"
```

- The script re-executes itself under `caffeinate -dims`. An idle MacBook otherwise sleeps after 10 min (incident 13).
- Its last window is the five-model session diagnostic.
- Copy `/tmp/m4max-powermetrics.txt` into the run directory afterwards.

## 8. Collecting, checking and analysing

- **Collect:** `scripts/proxyctl.sh collect <key>` for each host, plus the `C-artifacts/` and `L7-artifacts/` pulls above.
- **Check:**
  - every `llama-bench_*.json` parses and has 10 entries (Linux t=1..8), 6 (pi5) or 2 (macOS pp/tg files);
  - every `windows.log` line is `exit=0`;
  - every eval artifact in `artifacts.txt` exists.
- **Tabulate:** `python3 scripts/summarize.py ../../eval-results/phone-proxies/<key> [<run>]` gives per-run tables. On macOS it also gives energy per token above idle, with powermetrics alignment as in the log's §4.
- **Cross-platform:** `python3 scripts/prelim_report.py` (written against the original run IDs; edit them at its top for a re-run).

## 9. Teardown

- Collect everything first. Eval artifacts live only in each host's `~/fleet-trilogy/eval-results/` until pulled.
- `terraform destroy` removes all but Mac hosts allocated less than 24 h ago. `terraform output mac_hosts_earliest_release` gives that time; destroy again after it.
- A stopped Linux instance still bills for its disk until destroyed.
