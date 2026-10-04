# TODO: RAM capacity test (which models fit which phone)

**Status:** not started. Run it after the Phase 1 proxy runs finish (`deploy/aws-phone-proxies/`, 2026-10-03). It must not overlap them, because a concurrent load steals CPU and memory bandwidth and spoils their timings.

## Why
Speed is only half of "can a phone run it". The other half is whether the model fits in the memory a phone gives one app. llama.cpp has no flag that caps its own RAM:
- `-ctk/-ctv` and `-b/-ub` shrink the KV cache and compute buffers;
- `-lm` picks the load mode.

So the cap has to come from the OS. A cgroup v2 `memory.max` is a real, enforced ceiling, not arithmetic on file sizes. The Ubuntu 26.04 proxies have the memory controller and systemd 259.

## Test
- **Where:** one Linux proxy, android-flagship (c9g, 16 GiB). Whether a model fits depends on llama.cpp's allocations, not the CPU, so one proxy covers every tier.
- **Caps:** 4, 6, 8 and 12 GB, spanning budget (A17-class) to flagship (S26 Ultra / iPhone 17 Pro). An app gets only part of a phone's total RAM, so also record the smallest cap each model survives, not just pass/fail at total-RAM sizes.
- **Per model × cap:**
  ```bash
  systemd-run --scope -p MemoryMax=<cap> -p MemorySwapMax=0 \
    llama-bench -m <model> -lm none -p 512 -n 16 -r 1 -o json
  ```
  - `-lm none` should read the weights into RAM; confirm it against `llama-bench --help`.
  - With mmap, an over-cap model would thrash pages from disk instead of failing. A phone's low-memory killer just ends the app, so the OOM kill is the realistic outcome.
- **Record:** fits or OOM-killed, plus peak memory (the cgroup's `memory.peak`).
- **Output:** `eval-results/phone-proxies/ram-capacity/<run-id>/`, plus a fits matrix (models × caps) for the impact track.

## Limits
- A cgroup cap is a hard ceiling. Android's low-memory killer and iOS's jetsam (its equivalent) apply limits that vary by device, OS version and what else is running. The real-phone runs (`TODO-REAL-PHONE-BENCHMARKS.md`) are the ground truth: a budget phone failing to load a model there confirms or corrects this matrix.
- macOS has no cgroups, so the Mac proxies are out of scope. iPhone fit comes from the real-phone runs, if iOS proves viable.
