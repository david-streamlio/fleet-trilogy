# TODO: benchmark on real phones (AWS Device Farm)

**Status:** not this round. The user time-boxed the study on 2026-10-04: no real phones, no Pi 5, no Phase 2, no round 3b. The proxy results stand in, with their caveats (test log §8). Kept as the plan for a later round.

## Why
The EC2 proxies share the phones' core lineage but not their memory system or thermals:
- **More bandwidth than phones.** STREAM Triad on the proxies:
  - c9g: 121 GB/s at 6-8 threads
  - c7g: 202 GB/s at 8 threads
  - c6g: 89 GB/s at 4 threads

  The devices they stand in for: flagship Android ~85 GB/s theoretical peak, Pi 5 17.1 GB/s. Token generation is bandwidth-bound, so raw proxy numbers overstate phones.
- **Bandwidth can't be capped in hardware on EC2.**
  - The 7.0.0-1014-aws kernel has the Arm MPAM driver built in, but Nitro passes no ACPI MPAM table to guests, so there's no resctrl.
  - There's no cpufreq control either, and cgroups have no memory-bandwidth controller.
- **Servers don't thermally throttle; phones do,** and that dominates sustained on-device inference.

A math correction (scale by bandwidth ratio) is the fallback. A real-hardware measurement is preferred.

## What's available
`aws devicefarm list-devices` in us-west-2, 2026-10-03; all marked highly available.

| Tier | Device (OS) |
|---|---|
| 2026 flagship Android | Galaxy S26 Ultra (16); also S26 / S26+, Pixel 10 / 11 Pro |
| 2021 flagship: the "5 years ago" point on the same product line | Galaxy S21 (11, 12) |
| Mid-range Android | Galaxy A36 (15, 16) |
| Budget Android | Galaxy A17 (16) |
| iPhone flagship | iPhone 17 Pro / Pro Max / Air (26.3.1) |
| Older iPhone (the mac2 proxy's target) | iPhone 12 (26.6) |

Proposed Android set: S26 Ultra, S21, A36 and A17 (flagship now, flagship 5 years ago, mid-range, budget). Read the exact SoC off each device (`getprop ro.soc.model`). Some regions ship Exynos variants.

## Android plan
- Cross-compile llama.cpp `v0.5.0` (commit 7fe450e1) for `arm64-v8a` with the Android NDK on the Mac. Use the same tag as the proxies.
- Device Farm custom test environment. The test spec:
  - downloads that job's models onto the host from Hugging Face;
  - `adb push`es them and `llama-bench` to `/data/local/tmp`;
  - runs the proxies' arguments (`-p 512 -n 128 -r 3 -o json`, a thread sweep to the core count).
- Every second during the run, log `/sys/class/thermal/thermal_zone*/temp` and `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`. Throttling is the result we can't get from EC2.
- Same 17 models as Phase 1 (`deploy/aws-phone-proxies/variables.tf`). A budget phone failing to load the 8-9B models is a result, not a bug: record it, and compare it with the proxy fits matrix (`TODO-RAM-CAPACITY-TEST.md`).
- Collect into `eval-results/real-phones/<device>/<run-id>/`, in the same layout as `eval-results/phone-proxies/`, so the analysis treats proxy and phone rows alike.

## Constraints
- **Jobs are capped at 150 minutes.** Split the 17 models into 2-3 jobs per phone. Devices are wiped between runs, so each job pushes only its own models.
- **No energy numbers.** The phones are USB-powered in the rack, so battery current doesn't isolate the benchmark. Time and thermals only.
- **Cost:** about $0.17 per device-minute, metered. Roughly $30-75 per phone, so $150-250 for the four Android phones.

## iOS (open question)
Real iPhones need an XCTest app with llama.cpp built in (its XCFramework), whose test downloads models and runs the benchmark loop. That needs Xcode plus signing.
- **Open:** is there an Apple Developer account (personal or Datadog) to sign it?
- If not, the Mac proxies stay the Apple stand-ins. They also give Apple energy numbers through `powermetrics`, which Device Farm can't.
- **Tied decision:** allocate the mac-m4 host (≥ $29.52) only if iOS on Device Farm isn't viable, or if the proxy results justify it anyway.
