# Pi 4: llama.cpp command-line tool vs llama-server, per call (2026-10-07)

What a triage call costs when the model is reloaded every call (the command-line tool) versus loaded once (llama-server), with the load, prompt and generation times separated. Answers how much of the "~6x" in the impact track (row 7) came from not reloading the model; that figure compared whole sweeps of different sizes on the laptop.

## Setup
- Raspberry Pi 4 (edge-node00), 8 GB, fan on, rebooted just before the run. llama.cpp `8212c78` (the published Pi rows' build).
- bartowski `Phi-3.5-mini-instruct-Q4_K_M.gguf` (same file as the published Pi rows), on the USB data drive.
- Every arm: the production prompt (`DEFAULT_PROMPT_TEMPLATE`, benign case; `prompt.txt`, 506 tokens), the triage grammar (`grammar.gbnf`), 4 threads, `-c 4096`, temperature 0.2, 300-token cap.
- `bench_cli_vs_server.py` (this folder), run from repo commit `6efc3fe`'s prompt/grammar: `python3 bench_cli_vs_server.py results-….jsonl 10 10 30`. One discarded warm-up call per arm.
  - `cli`: `llama-completion -no-cnv` per call; load / prompt-eval / eval times parsed from llama.cpp's own `llama_perf` lines.
  - `server-nocache`: one `llama-server -np 1`, `/completion` with `cache_prompt: false`, so every call reads the whole prompt.
  - `server-cache`: the same server, `cache_prompt: true`, the same prompt repeated (as within one incident).
- No power meter: time only.

## Results (`results-20261007T201818Z.jsonl`; median, n per arm)

| Arm | n | Wall p50 (p95) | Model load | Prompt (tokens read) | Generation (tokens) |
|---|---|---|---|---|---|
| Command-line tool | 10 | 196.0 s (196.7) | 3.11 s per call | 161.4 s (506) | 30.8 s (41) |
| llama-server, cache off | 10 | 192.7 s (193.1) | once: 5.6 s startup | 161.8 s (506) | 30.9 s (42) |
| llama-server, cache on | 30 | 31.7 s (31.7) | once | 0.74 s (1) | 30.9 s (42) |

- Not reloading the model saves ~3.3 s of a ~196 s call (1.7%). Cold, the first load took 9.1 s (`cli-warmup`).
- The prompt cache, which only a long-running server keeps across calls, saves ~161 s: 6.2x faster per call than the command-line tool.
- Every call in every arm answered `hold` (the expected answer). Temperatures 68-74 C; the throttle flag 0x80000 is the sticky soft-limit bit, no live throttling.
