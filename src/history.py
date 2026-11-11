"""Clone each repository and extract a snapshot of its MCP tools and
capabilities at a series of versions.

Version selection per repository (first-parent history of the default branch):
  * every release tag reachable from HEAD, if the repo has >= 3 tags;
  * otherwise up to MAX_SNAPSHOTS commits spaced evenly in time;
  * always the latest commit (HEAD).
Each snapshot records tools (name, description, per-tool capabilities),
server-level capabilities and domains, declared dependencies, and README text
hash/length (used later to check whether new capabilities were disclosed).

Usage: python src/history.py [--limit N] [--workers W]
Output: data/snapshots/<owner>__<repo>.json
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import analyze_tree, relevant  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPOS = ROOT / "data" / "repos.jsonl"
OUT = ROOT / "data" / "snapshots"
CLONES = Path(os.environ.get("CLONE_DIR", "/home/user/clones"))
MAX_SNAPSHOTS = 12
MAX_TAG_SNAPSHOTS = 40
CLONE_TIMEOUT = 240
MAX_HEAD_FILES = 600
KEEP_CLONES = os.environ.get("KEEP_CLONES") == "1"
PIN_DIR = os.environ.get("PIN_DIR")

DEP_FILES = ("package.json", "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")


def git(repo, *args, timeout=120, text=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text,
                       timeout=timeout, errors="ignore" if text else None)
    return r.stdout if r.returncode == 0 else ""


def clone(full_name):
    dest = CLONES / full_name.replace("/", "__")
    if (dest / "HEAD").exists() or (dest / ".git").exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:limit=400k",
                            f"https://github.com/{full_name}", str(dest)],
                           capture_output=True, text=True, timeout=CLONE_TIMEOUT,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        return None
    if r.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        return None
    return dest


def pick_versions(repo):
    log = git(repo, "log", "--first-parent", "--format=%H %ct", "HEAD").split("\n")
    commits = [(h, int(t)) for h, t in (l.split() for l in log if l.strip())]
    if not commits:
        return []
    commits.reverse()  # oldest first
    on_branch = {h for h, _ in commits}
    tags = []
    for line in git(repo, "for-each-ref", "--format=%(refname:short) %(*objectname) %(objectname)", "refs/tags").split("\n"):
        parts = line.split()
        if len(parts) < 2:
            continue
        name, sha = parts[0], parts[1] if len(parts) == 3 else parts[-1]
        tags.append((name, sha))
    ts = dict(commits)
    tagged = sorted({(ts[s], s, n) for n, s in tags if s in on_branch})
    versions = []
    if len(tagged) >= 3:
        if len(tagged) > MAX_TAG_SNAPSHOTS:
            step = len(tagged) / MAX_TAG_SNAPSHOTS
            tagged = [tagged[int(i * step)] for i in range(MAX_TAG_SNAPSHOTS)]
        versions = [{"commit": s, "time": t, "tag": n} for t, s, n in tagged]
    else:
        t0, t1 = commits[0][1], commits[-1][1]
        if t1 > t0:
            targets = [t0 + (t1 - t0) * i / (MAX_SNAPSHOTS - 1) for i in range(MAX_SNAPSHOTS)]
            idx, chosen = 0, []
            for tgt in targets:
                while idx + 1 < len(commits) and commits[idx + 1][1] <= tgt:
                    idx += 1
                chosen.append(commits[idx])
            seen = set()
            for h, t in chosen:
                if h not in seen:
                    seen.add(h)
                    versions.append({"commit": h, "time": t, "tag": None})
    head = commits[-1]
    if not versions or versions[-1]["commit"] != head[0]:
        versions.append({"commit": head[0], "time": head[1], "tag": "HEAD"})
    return versions


def read_blobs(repo, specs):
    """Read many `<commit>:<path>` blobs with one cat-file process."""
    if not specs:
        return {}
    p = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], input="\n".join(specs).encode() + b"\n",
                       capture_output=True, timeout=300)
    out, data, i = {}, p.stdout, 0
    for spec in specs:
        nl = data.find(b"\n", i)
        if nl == -1:
            break
        header = data[i:nl].decode("utf-8", "ignore").split()
        i = nl + 1
        if len(header) < 3 or header[1] == "missing":
            continue
        size = int(header[2])
        out[spec] = data[i:i + size].decode("utf-8", "ignore")
        i += size + 1
    return out


def deps(files):
    names = set()
    for path, text in files.items():
        base = path.split("/")[-1]
        if base == "package.json":
            try:
                j = json.loads(text)
                for k in ("dependencies", "optionalDependencies"):
                    names |= set((j.get(k) or {}).keys())
            except Exception:
                pass
        elif base == "requirements.txt":
            for l in text.splitlines():
                m = re.match(r"\s*([A-Za-z0-9_.\-]+)", l)
                if m and not l.strip().startswith(("#", "-")):
                    names.add(m.group(1).lower())
        elif base in ("pyproject.toml", "setup.py", "setup.cfg"):
            block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
            if block:
                names |= {m.lower() for m in re.findall(r"['\"]([A-Za-z0-9_.\-]+)", block.group(1))}
            block = re.search(r"install_requires\s*=\s*\[(.*?)\]", text, re.S)
            if block:
                names |= {m.lower() for m in re.findall(r"['\"]([A-Za-z0-9_.\-]+)", block.group(1))}
    return sorted(names)


def snapshot(repo, v):
    listing = git(repo, "ls-tree", "-r", "-l", v["commit"]).split("\n")
    code, meta, readme = [], [], None
    for line in listing:
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        info, path = parts
        f = info.split()
        if len(f) < 4 or f[1] != "blob":
            continue
        size = int(f[3]) if f[3].isdigit() else 0
        depth = path.count("/")
        base = path.split("/")[-1]
        if relevant(path) and size < 400_000:
            code.append(path)
        elif base in DEP_FILES and depth <= 2:
            meta.append(path)
        elif base.lower() in ("readme.md", "readme") and depth == 0:
            readme = path
    if len(code) > 1500:
        code = code[:1500]
    specs = [f"{v['commit']}:{p}" for p in code + meta + ([readme] if readme else [])]
    blobs = read_blobs(repo, specs)
    files = {s.split(":", 1)[1]: t for s, t in blobs.items()}
    code_files = {p: files[p] for p in code if p in files}
    tools, caps, doms = analyze_tree(code_files)
    rd = files.get(readme, "") if readme else ""
    return {
        **v,
        "n_code_files": len(code_files),
        "missing_blobs": len(code) - len(code_files),
        "tools": [t.to_dict() for t in tools],
        "server_caps": caps,
        "server_domains": doms,
        "deps": deps({p: files[p] for p in meta if p in files}),
        "readme": rd[:20000],
    }


def process(rec):
    name = rec["full_name"]
    out = OUT / (name.replace("/", "__") + ".json")
    if out.exists():
        return name, "cached"
    t0 = time.time()
    repo = clone(name)
    if repo is None:
        out.write_text(json.dumps({"repo": rec, "error": "clone_failed"}))
        return name, "clone_failed"
    try:
        pinned = None
        if PIN_DIR:  # reuse the exact versions sampled in an earlier run (keeps the study population fixed)
            prev = Path(PIN_DIR) / out.name
            if prev.exists():
                pinned = [{k: s[k] for k in ("commit", "time", "tag")}
                          for s in json.loads(prev.read_text()).get("snapshots", [])] or None
        if pinned is None:
            n_head = sum(1 for l in git(repo, "ls-tree", "-r", "--name-only", "HEAD").split("\n") if relevant(l))
            if n_head > MAX_HEAD_FILES:
                out.write_text(json.dumps({"repo": rec, "error": "too_large", "n_head_files": n_head}))
                return name, f"skip large ({n_head} files)"
        versions = pinned or pick_versions(repo)
        snaps = [snapshot(repo, v) for v in versions]
    except Exception as e:  # keep going on odd repos
        out.write_text(json.dumps({"repo": rec, "error": f"{type(e).__name__}: {e}"}))
        return name, "error"
    finally:
        if not KEEP_CLONES:
            shutil.rmtree(repo, ignore_errors=True)
    out.write_text(json.dumps({"repo": rec, "snapshots": snaps}))
    return name, f"ok {len(snaps)} versions {time.time() - t0:.0f}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-stars", type=int, default=20)
    ap.add_argument("--shard", default="0/1", help="i/n: process every n-th repo starting at i")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(l) for l in REPOS.open()]
    recs = [r for r in recs if r["stars"] >= a.min_stars and r.get("language") in
            ("Python", "TypeScript", "JavaScript")]
    recs.sort(key=lambda r: -r["stars"])
    if a.limit:
        recs = recs[:a.limit]
    si, sn = map(int, a.shard.split("/"))
    recs = recs[si::sn]
    print(f"processing {len(recs)} repos", flush=True)
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(process, r) for r in recs]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                name, status = f.result()
            except Exception as e:
                name, status = "?", f"crash {e}"
            print(f"[{i}/{len(recs)}] {name}: {status}", flush=True)


if __name__ == "__main__":
    main()
