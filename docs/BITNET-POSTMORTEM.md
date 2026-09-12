# BitNet postmortem

Factual record of the attempt to run Microsoft's BitNet b1.58-2B-4T model via the
`microsoft/BitNet` (bitnet.cpp) fork as this project's on-stage LLM, why it was
dropped, and what replaced it. This is talk material, not an apology — the "1-bit
LLM" framing in the talk titles is preserved by telling this story, rather than by
claiming the final on-stage models are 1-bit (they aren't; see below).

## What we tried

`microsoft/BitNet` vendors its own pinned fork of llama.cpp (`3rdparty/llama.cpp`,
a fork historically tracked as `isHuangXin/llama.cpp`) with a custom 2-bit packed
tensor type (`GGML_TYPE_I2_S`) and hand-written SIMD kernels for it
(`ggml_gemv_i2_i8_s`, `ggml_gemm_i2_i8_s`, `ggml_vec_dot_i2_i8_s`, in
`ggml-cpu-i2s.c`). We built this fork from source targeting Apple Silicon (M4,
`arm64`, clang 21) against the official `BitNet-b1.58-2B-4T` GGUF weights
(`ggml-model-i2_s.gguf`).

## Build fixes required (upstream bugs, not ours to carry forward)

Two genuine bugs in the fork blocked a from-source build on this toolchain:

1. **Undefined symbols at link time** — `dequantize_row_i2_s` and `quantize_i2_s`
   are declared in `ggml-quants.h` and called from `ggml.c` (part of the
   `ggml-base` link target), but only *defined* in `ggml-cpu/quants.c`, which
   belongs to a separate `ggml-cpu` target not linked into `ggml-base`. Fixed by
   adding matching definitions directly in `ggml-quants.c`.
2. **`error: use of undeclared identifier 'src1_cont'`** — the I2_S GEMV/GEMM fast
   path in `ggml-cpu.c` uses `src1_cont` unconditionally, but the only declaration
   of it lived inside a `#if GGML_USE_LLAMAFILE` block, and `GGML_USE_LLAMAFILE` is
   `#undef`'d unconditionally earlier in the same file — so the identifier was
   never in scope. Fixed by hoisting the declaration above the `#if` guard.

Both are scope/link-target bugs in dead or half-wired code paths in the fork
itself, unrelated to Apple Silicon specifically — they would have surfaced on any
platform that actually reached that code path during a from-source build.

## The blocker: garbage output on ARM

Once building and loading correctly (~5 tok/s, a plausible rate for a 2B model on
CPU), every generation — regardless of prompt, seed, or temperature — degenerated
into a repeated `@@@@@@@@...` token stream. We ruled out the two most likely
proximate causes before stopping:

- **Not the AVX2/repack kernel path** — reproduced identically with `--no-repack`
  forcing the scalar fallback, so it isn't an AVX2-specific SIMD bug (that path
  isn't even compiled for ARM).
- **Not a sampling artifact** — reproduced across varying `--seed` and `--temp`
  values, so it isn't a greedy-decoding coincidence on one particular input.

That points to a numerical bug somewhere deeper in the fork's ARM-path
kernels/attention/RoPE handling for `I2_S` — real, but not something we chose to
keep debugging blind inside hand-written, lightly-exercised SIMD code we don't
own upstream. Given the demo timeline, we treated this as a go/no-go signal rather
than a bug to fix.

## Why mainline llama.cpp can't rescue it

Before abandoning BitNet entirely, we checked whether mainline `ggml-org/llama.cpp`
— whose kernels are far more widely exercised on ARM — could run the same GGUF.
It cannot, for two independent reasons:

1. **Tensor type-ID collision.** GGML type enum slot 36 means `I2_S` in the BitNet
   fork, but mainline has since repurposed that same slot for
   `TYPE_IQ4_NL_4_4 (REMOVED)`. Mainline's `gguf_init_from_reader` rejects the
   fork's GGUF outright on this mismatch.
2. **No BitNet architecture support at all.** Independent of the type collision,
   mainline's `convert_hf_to_gguf.py` has zero references to a `"bitnet"`
   architecture — there is no graph-builder support to load this model family in
   the first place, quantization aside.

The type collision is superficially patchable; the total absence of BitNet
architecture support in mainline is not, short of a substantial upstream
contribution. This wasn't a path forward on our timeline.

## Why this matters for the Pi

The target stage hardware is a **Raspberry Pi 4** (older ARM core, weaker/narrower
SIMD than an M4). The BitNet fork already produces incorrect output on an M4 —
strictly newer and more capable ARM silicon. There is no reason to expect a
Pi 4 to fare better; if anything it's the worst case for this fork, not a
better one. We did not bother testing the fork on the Pi 4 given the M4 result.

## What replaced it

We pivoted to small **quantized instruct models (Qwen2.5-1.5B and 0.5B,
Q4_K_M GGUF)** run through **mainline llama.cpp**, which has broad,
well-exercised ARM support and loads/generates coherently on both the M4 and
(pending) the Pi 4. See `docs/CANON.md` for the current model decision and
`docs/PI4-RUNBOOK.md` for the Pi 4 build/run steps. The inference wrapper package
(`shared/llm-inference`, formerly `shared/bitnet-inference`) was renamed to
reflect that it always was a generic subprocess wrapper around a
llama.cpp-family CLI binary — bitnet.cpp was simply the first (and, it turned
out, non-viable) runtime we pointed it at.

The "1-bit" framing in the talk titles now lives in this postmortem: we set out
to run a 1-bit model on the edge, hit a real and specific wall doing it, and made
a pragmatic, evidence-based call to ship something that actually works instead.
That arc is the talk.
