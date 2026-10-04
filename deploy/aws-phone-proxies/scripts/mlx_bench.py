"""MLX counterpart of llama-bench's pp512 / tg128, for catalog test H (MLX vs llama.cpp Metal).

    mlx_bench.py <hf-repo-or-path> <out.json> [--reps 3] [--prompt 512] [--gen 128]

Same method as mlx-lm 0.32's own `mlx_lm.benchmark` (random-token prompt, end-of-text
disabled so every trial generates exactly --gen tokens), with two differences:
- prompt processing and generation are separate trials, like llama-bench's two tests:
  pp = a --prompt-token prompt with 1 generated token; tg = a 1-token prompt with
  --gen generated tokens;
- each trial records its epoch start/end, so powermetrics energy can be attributed to
  exactly that interval rather than to the whole window (model load and warm-up included).
"""
import argparse
import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load, stream_generate


def trial(model, tokenizer, prompt, max_tokens):
    t0 = time.time()
    for resp in stream_generate(model, tokenizer, prompt, max_tokens=max_tokens):
        pass
    t1 = time.time()
    return resp, t0, t1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--prompt", type=int, default=512)
    ap.add_argument("--gen", type=int, default=128)
    args = ap.parse_args()

    mx.random.seed(0)
    model, tokenizer, config = load(args.model, return_config=True)
    tokenizer._eos_token_ids = {}  # as mlx_lm.benchmark: never stop early
    vocab = config.get("vocab_size") or config["text_config"]["vocab_size"]
    pp_prompt = mx.random.randint(0, vocab, (args.prompt,)).tolist()
    tg_prompt = pp_prompt[:1]

    trial(model, tokenizer, pp_prompt, 1)  # warm-up, untimed
    trial(model, tokenizer, tg_prompt, 8)

    out = {"model": args.model, "mlx_lm": __import__("mlx_lm").__version__, "pp": [], "tg": []}
    for _ in range(args.reps):
        r, t0, t1 = trial(model, tokenizer, pp_prompt, 1)
        out["pp"].append({"tokens": args.prompt, "tps": r.prompt_tps, "start": t0, "end": t1})
    for _ in range(args.reps):
        r, t0, t1 = trial(model, tokenizer, tg_prompt, args.gen)
        out["tg"].append({"tokens": args.gen, "tps": r.generation_tps, "start": t0, "end": t1})
    out["peak_memory_gb"] = r.peak_memory
    path = Path(args.model)
    if not path.exists():
        from huggingface_hub import snapshot_download
        path = Path(snapshot_download(args.model))
    out["size_gb"] = sum(p.stat().st_size for p in path.glob("*.safetensors")) / 1e9
    Path(args.out).write_text(json.dumps(out, indent=1))
    avg = lambda k: sum(x["tps"] for x in out[k]) / len(out[k])
    print(f"{args.model}: pp{args.prompt} {avg('pp'):.1f} tok/s, tg{args.gen} {avg('tg'):.1f} tok/s, peak {out['peak_memory_gb']:.2f} GB")


if __name__ == "__main__":
    main()
