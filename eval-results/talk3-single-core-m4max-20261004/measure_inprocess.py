"""Time Tier 2's LLM call through InProcessLlmBackend (llama-cpp-python), one setup
per process so each setup's peak memory is its own. Run from the repo root:
    uv run --no-sync python eval-results/talk3-single-core-m4max-20261004/measure_inprocess.py <setup> <N> <out.jsonl>

Setups:
  fresh_t1 / fresh_t4  a new backend (model load, empty cache) for every call -- the
                       subprocess architecture, but on the same llama.cpp build, so
                       it isolates "load once and keep it" from build differences.
  kept_t1 / kept_t4    one backend for all calls, as GlobalSynthesisFunction holds it.
  kept_gpu             one backend, all layers on Metal, 4 threads.

Each call is a different incident: the demo's three cards moved to a rotating
corridor, so consecutive prompts share only the fixed instructions (the
conservative case for prefix reuse; the same corridor twice would share more).
"""
import json, os, resource, sys, time
from fleet_telemetry_model import EnrichmentCard, from_json
from llm_inference import InProcessLlmBackend, LlmGenerationConfig
from llm_inference.structured import extract_json_object
from talk3_pulsar_speaks_english.prompting import render_synthesis_prompt
from talk3_pulsar_speaks_english.synthesizer import decide_reroute, decide_scope

MODEL = os.path.expanduser("~/tools/models/gemma-3-4b-it-GGUF/gemma-3-4b-it-Q4_K_M.gguf")
SETUPS = {
    "fresh_t1": dict(threads=1, gpu_layers=0, keep=False),
    "fresh_t4": dict(threads=4, gpu_layers=0, keep=False),
    "kept_t1": dict(threads=1, gpu_layers=0, keep=True),
    "kept_t4": dict(threads=4, gpu_layers=0, keep=True),
    "kept_gpu": dict(threads=4, gpu_layers=-1, keep=True),
}
CORRIDORS = ["I-95N", "I-90E", "I-80W", "I-5S", "I-10E"]
raw = [json.loads(l) for l in open("deploy/talk3-demo-cards.jsonl") if l.strip()]


def prompt_for(corridor):
    cards = [from_json(EnrichmentCard, json.dumps({**c, "corridor": corridor})) for c in raw]
    scope = decide_scope(cards)
    reroute, detail = decide_reroute(cards, scope)
    return render_synthesis_prompt(corridor=corridor, cards=cards, scope=scope,
                                   reroute_recommended=reroute, reroute_detail=detail)


def cpu_s():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


setup, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cfg = SETUPS[setup]
config = LlmGenerationConfig(timeout_seconds=600)
make = lambda: InProcessLlmBackend(MODEL, threads=cfg["threads"], gpu_layers=cfg["gpu_layers"])
backend = make() if cfg["keep"] else None
prev_tokens = []
with open(out, "a") as f:
    for i in range(n + 1):
        prompt = prompt_for(CORRIDORS[i % len(CORRIDORS)])
        c0, t0 = cpu_s(), time.monotonic()
        if not cfg["keep"]:
            backend = make()
        load_s = time.monotonic() - t0 if not cfg["keep"] or i == 0 else 0.0
        text = backend.generate(prompt, config)
        wall = time.monotonic() - t0
        if i == 0 and cfg["keep"]:
            load_s = None  # first call includes the one-time load; not separable here
        llama = backend._llama
        tokens = llama.tokenize(prompt.encode())
        reused = 0
        if cfg["keep"]:
            for a, b in zip(prev_tokens, tokens):
                if a != b:
                    break
                reused += 1
        prev_tokens = tokens
        try:
            warning = extract_json_object(text).get("spoken_warning")
        except ValueError:
            warning = None
        rec = {"setup": setup, "run": i, "warmup": i == 0, "corridor": CORRIDORS[i % len(CORRIDORS)],
               "wall_s": round(wall, 3), "cpu_s": round(cpu_s() - c0, 2),
               "prompt_tokens": len(tokens), "prefix_reused_tokens": reused,
               "output_tokens": len(llama.tokenize(text.encode(), add_bos=False)),
               "warning": warning}
        f.write(json.dumps(rec) + "\n"); f.flush()
        print(setup, i, rec["wall_s"], "reused", reused, flush=True)
        if not cfg["keep"]:
            backend._llama.close(); backend = None
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
with open(out, "a") as f:
    f.write(json.dumps({"setup": setup, "peak_rss_mb": round(peak / 2**20)}) + "\n")
