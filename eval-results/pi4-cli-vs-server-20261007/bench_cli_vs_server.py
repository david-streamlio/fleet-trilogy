#!/usr/bin/env python3
"""Talk 2: per-call cost of the llama.cpp command-line tool (model reloaded every call)
versus a long-running llama-server (model loaded once), on the Raspberry Pi 4.

Same model, prompt (DEFAULT_PROMPT_TEMPLATE, benign case), grammar, 4 threads, -c 4096,
temperature 0.2, 300-token cap in every arm. Arms, in order:
  cli          llama-completion per call; llama.cpp's own load / prompt-eval / eval times
  server-nocache  llama-server, cache_prompt=false: every call reads the whole prompt
  server-cache    llama-server, cache_prompt=true, the same prompt repeated
One discarded warm-up call per arm. Every call also logs temperature and throttling.

    python3 bench_cli_vs_server.py <out.jsonl> <n_cli> <n_nocache> <n_cache>
"""
import json, re, subprocess, sys, time, urllib.request

BIN = "/mnt/data/tools/llama.cpp/build/bin"
MODEL = "/mnt/data/models/Phi-3.5-mini-instruct-GGUF/Phi-3.5-mini-instruct-Q4_K_M.gguf"
DIR = "/mnt/data/fleet-trilogy/bench-cli-vs-server"
PROMPT = open(f"{DIR}/prompt.txt").read()
GRAMMAR = open(f"{DIR}/grammar.gbnf").read()
COMMON = ["-m", MODEL, "-t", "4", "-c", "4096"]
PORT = 8099
out_path, n_cli, n_nocache, n_cache = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
out = open(out_path, "a")

def pi_state():
    t = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True).stdout.strip()
    th = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True).stdout.strip()
    hz = subprocess.run(["vcgencmd", "measure_clock", "arm"], capture_output=True, text=True).stdout.strip().split("=")[-1]
    return {"temp": t.replace("temp=", ""), "throttled": th.replace("throttled=", ""), "arm_hz": hz}

def log(rec):
    rec["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec.update(pi_state())
    out.write(json.dumps(rec) + "\n"); out.flush()
    print(json.dumps({k: rec.get(k) for k in ("arm", "i", "wall_s", "load_ms", "prompt_ms", "prompt_n", "gen_ms", "gen_n", "temp", "throttled")}), flush=True)

PERF = {k: re.compile(p) for k, p in {
    "load_ms": r"load time\s*=\s*([\d.]+) ms",
    "prompt": r"prompt eval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens",
    "gen": r"(?<!prompt )eval time\s*=\s*([\d.]+) ms /\s*(\d+) runs",
    "total_ms": r"total time\s*=\s*([\d.]+) ms"}.items()}

def cli_call(arm, i):
    cmd = [f"{BIN}/llama-completion", *COMMON, "-f", f"{DIR}/prompt.txt", "-n", "300", "--temp", "0.2",
           "--grammar-file", f"{DIR}/grammar.gbnf", "-no-cnv"]
    t0 = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    wall = time.monotonic() - t0
    err = r.stderr
    rec = {"arm": arm, "i": i, "wall_s": round(wall, 3), "rc": r.returncode}
    if (m := PERF["load_ms"].search(err)): rec["load_ms"] = float(m.group(1))
    if (m := PERF["prompt"].search(err)): rec["prompt_ms"], rec["prompt_n"] = float(m.group(1)), int(m.group(2))
    if (m := PERF["gen"].search(err)): rec["gen_ms"], rec["gen_n"] = float(m.group(1)), int(m.group(2))
    if (m := PERF["total_ms"].search(err)): rec["total_ms"] = float(m.group(1))
    rec["output_tail"] = r.stdout[-200:]
    log(rec)

def post(body):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read())

def server_call(arm, i, cache):
    body = {"prompt": PROMPT, "n_predict": 300, "temperature": 0.2, "grammar": GRAMMAR, "cache_prompt": cache}
    t0 = time.monotonic()
    b = post(body)
    wall = time.monotonic() - t0
    tm = b.get("timings", {})
    log({"arm": arm, "i": i, "wall_s": round(wall, 3), "prompt_ms": tm.get("prompt_ms"), "prompt_n": tm.get("prompt_n"),
         "gen_ms": tm.get("predicted_ms"), "gen_n": tm.get("predicted_n"), "output_tail": b.get("content", "")[-200:]})

# ---- arm 1: command-line tool, model reloaded every call ----
cli_call("cli-warmup", 0)
for i in range(1, n_cli + 1):
    cli_call("cli", i)

# ---- arms 2-3: one llama-server, model loaded once ----
t0 = time.monotonic()
srv = subprocess.Popen([f"{BIN}/llama-server", *COMMON, "-np", "1", "--host", "127.0.0.1", "--port", str(PORT)],
                       stdout=subprocess.DEVNULL, stderr=open(f"{DIR}/server-stderr.log", "w"))
while True:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
            if r.status == 200: break
    except Exception:
        pass
    if srv.poll() is not None: sys.exit("llama-server exited during startup")
    time.sleep(0.5)
log({"arm": "server-startup", "i": 0, "wall_s": round(time.monotonic() - t0, 3)})
try:
    server_call("server-nocache-warmup", 0, False)
    for i in range(1, n_nocache + 1):
        server_call("server-nocache", i, False)
    server_call("server-cache-warmup", 0, True)
    for i in range(1, n_cache + 1):
        server_call("server-cache", i, True)
finally:
    srv.terminate(); srv.wait(timeout=30)
log({"arm": "done", "i": 0, "wall_s": 0})
