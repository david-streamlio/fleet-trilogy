#!/usr/bin/env python3
"""Pin every model file these tests download: Hugging Face repo revision + file SHA-256.

    models_lock.py > ../MODELS.lock.tsv

The model lists come from the stack itself (variables.tf and the queue scripts), so the lock
covers exactly what the hosts fetched. Downloads used `resolve/main/<file>` and
`snapshot_download(<repo>)`; a re-run should pin `resolve/<revision>/<file>` instead and
check the SHA-256 (`shasum -a 256`). The revisions are those of `main` when this ran.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
# Label = the tests that fetch from that file's lists (bench_linux_extras.sh holds L3's and L4's).
SOURCES = {
    "phase1": HERE / "variables.tf",
    "I": HERE / "scripts/bench_extras.sh",
    "G": HERE / "scripts/bench_extras_gh.sh",
    "L3/L4": HERE / "scripts/bench_linux_extras.sh",
    "R3": HERE / "scripts/bench_round3.sh",
}
NOT_RUN: dict[str, str] = {}  # file -> why it is listed but was never run
GGUF = re.compile(r'([\w.-]+/[\w.-]+-GGUF)["\s,]+(?:file\s*=\s*")?([\w.-]+\.gguf)')
URL = re.compile(r"huggingface\.co/([\w.-]+/[\w.-]+-GGUF)/resolve/main/([\w.-]+\.gguf)")  # round 3's direct downloads
MLX = re.compile(r"^(mlx-community/[\w.-]+)\s*$", re.M)


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    wanted = {}  # (repo, file or None) -> set of tests
    for test, path in SOURCES.items():
        text = path.read_text()
        for repo, file in GGUF.findall(text) + URL.findall(text):
            wanted.setdefault((repo, file), set()).add(test)
        if test == "G":
            for repo in MLX.findall(text):
                wanted.setdefault((repo, None), set()).add("H")
    print(f"# generated {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} from Hugging Face `main`")
    print("test(s)\trepo\trevision\tfile\tbytes\tsha256")
    revisions = {}
    for (repo, file), tests in sorted(wanted.items()):
        if repo not in revisions:
            revisions[repo] = get(f"https://huggingface.co/api/models/{repo}")["sha"]
        rev = revisions[repo]
        tree = {x["path"]: x for x in get(f"https://huggingface.co/api/models/{repo}/tree/{rev}")}
        files = [file] if file else sorted(p for p in tree if not p.endswith((".md", ".gitattributes")))
        for f in files:
            x = tree.get(f)
            if x is None:
                print(f"{','.join(sorted(tests))}\t{repo}\t{rev}\t{f}\tMISSING\t-")
                continue
            sha = (x.get("lfs") or {}).get("oid") or f"git:{x.get('oid')}"
            label = f"not run ({NOT_RUN[f]})" if f in NOT_RUN else ",".join(sorted(tests))
            print(f"{label}\t{repo}\t{rev}\t{f}\t{x.get('size')}\t{sha}")


if __name__ == "__main__":
    sys.exit(main())
