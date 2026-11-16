"""Sensitivity of tool-level capability attribution to call depth (2, 4, 6).
Random sample of study servers, latest studied commit, extractor otherwise unchanged."""
import json, os, random, sys, shutil
from collections import Counter
from pathlib import Path
os.environ.setdefault("CLONE_DIR", sys.argv[2] if len(sys.argv) > 2 else "/tmp/depth_clones")
sys.path.insert(0, str(Path(__file__).parent))
import history
from extract import analyze_tree

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
pop = [l.strip() for l in open(ROOT / "data/population.txt") if l.strip()]
deleted = {l.split()[0] for l in open(ROOT / "data/deleted_repos.txt") if l.strip()}
random.seed(2027)
sample = random.sample([r for r in pop if r not in deleted], N)
DEPTHS = (2, 4, 6)
out = open(ROOT / "data/depth_check.jsonl", "w")
for i, name in enumerate(sample, 1):
    snap = json.load(open(ROOT / "data/snapshots" / (name.replace("/", "__") + ".json")))
    vs = [s for s in snap.get("snapshots", []) if s.get("tools")]
    if not vs:
        continue
    commit = vs[-1]["commit"]
    repo = history.clone(name)
    if repo is None:
        print(i, name, "clone failed", flush=True); continue
    try:
        listing = history.git(repo, "ls-tree", "-r", "-l", commit).split("\n")
        code = []
        for line in listing:
            parts = line.split("\t")
            if len(parts) != 2: continue
            f = parts[0].split()
            if len(f) >= 4 and f[1] == "blob" and history.relevant(parts[1]) and (int(f[3]) if f[3].isdigit() else 0) < 400_000:
                code.append(parts[1])
        code = code[:1500]
        blobs = history.read_blobs(repo, [f"{commit}:{p}" for p in code])
        files = {s.split(":", 1)[1]: t for s, t in blobs.items()}
        res = {}
        for d in DEPTHS:
            tools, _, _ = analyze_tree(dict(files), depth=d)
            res[d] = {f"{t.file}::{t.name}": sorted(t.caps) for t in tools}
        out.write(json.dumps({"repo": name, "commit": commit, "caps": res}) + "\n"); out.flush()
        print(i, name, len(res[4]), "tools", flush=True)
    except Exception as e:
        print(i, name, "error", e, flush=True)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
