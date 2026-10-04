# Phone / edge proxies on EC2 (Talk 2: can phones democratize edge intelligence?)

Phase 1 of the hardware-spectrum benchmark: **identical models** (the 17 GGUFs from the
original M4/Pi candidate set, 350M-9B, listed in `variables.tf`), **identical llama.cpp**
(`v0.5.0`), 3 repetitions of pp512 + tg128, on EC2 stand-ins for each consumer platform.
Differences are hardware. `iphone-flagship` also runs Qwen3.8-27B (16.5 GB) as a
laptop-class reference point; nothing else can hold it. Measured points (Pi 4 with an inline meter, M4 Max with
`powermetrics`) live in `docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md` rows 24-28.

| Key | EC2 | Stands in for | Why |
|---|---|---|---|
| `pi5` | c6g.2xlarge | Raspberry Pi 5 | Graviton2's Neoverse N1 is the Pi 5's Cortex-A76's server sibling |
| `android-mainstream` | c7g.2xlarge | mainstream / older Android | Graviton3 Neoverse V1 ~ Cortex-X1 |
| `android-flagship` | c9g.2xlarge | 2025-26 flagship Android (8 Elite Gen 5, Dimensity 9500) | Graviton5 Neoverse V3 ~ Cortex-X4 — two generations behind, so a **lower bound** |
| `iphone-flagship` | mac-m4.metal | iPhone 17 / 18 Pro | M4 is the A18 generation; same Metal GPU path iPhone llama.cpp apps use |
| `iphone-older` | mac2.metal | iPhone 12-era | M1 is the A14's sibling |

**These are proxies, not phones.** Same instruction set and core lineage, different clocks,
caches and memory systems. Generation (memory-bandwidth-bound) is corrected by the target
device's bandwidth (`phone_bw_gbs`) against the proxy's measured STREAM bandwidth; prompt
processing (compute-bound) is reported as-is. Energy: macOS proxies measure chip power with
`powermetrics`; Graviton exposes **no** energy counters (no RAPL on ARM/EC2), so Linux
proxies report time only. Measuring on real phones (AWS Device Farm) is the planned
follow-up: `talks/talk2-greenest-token/TODO-REAL-PHONE-BENCHMARKS.md`. To re-run everything independently: `REPRODUCE.md` (pinned versions; model hashes in
`MODELS.lock.tsv`). Every test (done,
running, proposed, deferred) is indexed in `docs/TALK2-HARDWARE-SPECTRUM-TEST-CATALOG.md`
(methods and incidents: `docs/TALK2-HARDWARE-SPECTRUM-TEST-LOG.md`);
`scripts/summarize.py eval-results/phone-proxies/<key>` tabulates a run.

## Costs (us-west-2, on-demand)

- Linux proxies: $0.27-0.35/h each (c6g $0.272, c7g $0.290, c9g $0.348). They stop
  themselves after `linux_auto_stop_hours` (24, counted from boot).
- **Mac proxies run on Dedicated Hosts billed for at least 24 hours** (Apple's license):
  mac2 ~$0.65/h (≥ $15.60), mac-m4 ~$1.23/h (≥ $29.52). Charges start when the host is
  allocated — enabling a Mac proxy is the expensive, irreversible step.

## Run order

```bash
cd deploy/aws-phone-proxies
export AWS_PROFILE=advocacy-dev
terraform init

# 1. Smoke test: one cheap Linux proxy (the default enabled_proxies).
terraform apply
scripts/proxyctl.sh wait android-flagship        # ~30-40 min: build + 39 GB of models
scripts/proxyctl.sh bench android-flagship --quick

# 2. The Linux proxies, in parallel. start-all waits for READY, launches each run detached
#    on its instance and returns; the runs don't need this Mac (or AWS credentials) after that.
terraform apply -var 'enabled_proxies=["pi5","android-mainstream","android-flagship"]'
scripts/proxyctl.sh start-all
scripts/proxyctl.sh progress pi5                 # any time: which model it's on
scripts/proxyctl.sh collect pi5                  # when finished (or partway; it's rsync)

# 3. Macs: smoke-test the cheaper host first (24 h minimum from allocation), then full runs.
terraform apply -var 'enabled_proxies=["pi5","android-mainstream","android-flagship","iphone-older"]'
scripts/proxyctl.sh wait iphone-older
scripts/proxyctl.sh bench iphone-older --quick
scripts/proxyctl.sh start iphone-older
```

Re-applying to add a proxy leaves running proxies alone (AMI changes are ignored), but check
the plan says `0 to change, 0 to destroy` for them before typing `yes`.

**AWS credentials** are needed only for `terraform` commands that talk to AWS (`plan`,
`apply`, `destroy`); with short-lived SSO, `aws sso login --profile advocacy-dev` first.
`proxyctl.sh` reads local state (`terraform output`) and uses the stack's SSH key, so
monitoring and collecting work with expired credentials. If this machine's public IP
changes, SSH is blocked until a re-`apply` updates the security group.

Results land in `eval-results/phone-proxies/<key>/<run-id>/`.

## Tearing down

`terraform destroy` removes everything except Mac hosts allocated less than 24 h ago, which
AWS refuses to release (`terraform output mac_hosts_earliest_release`). Re-run `destroy`
after that time. Until then the hosts keep billing, instance running or not.
