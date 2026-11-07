"""Scan string literals in each analyzed server's latest code (HEAD) for text that
instructs the AI agent to execute something itself. These strings are usually
returned as tool OUTPUT, which users never see at approval time.

Shallow-clones each repo (depth 1), scans relevant source files, deletes the clone.
Output: data/agent_exec_code/<owner>__<repo>.json (resumable), then summarize with --summary.
"""
import json, os, re, shutil, subprocess, sys, glob
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import relevant
from agent_exec import RX as _RX
# instruction-form patterns only; a bare list of shell-tool names is not an instruction
RX = {k: v for k, v in _RX.items() if k != "agent_shell_tool"}
RX["use_your_shell_tool"] = re.compile(r"\b(?:use|using|with|via|call)\s+(?:your|the\s+agent'?s?)\s+(?:own\s+)?(?:shell|terminal|bash|command[- ]execution|shell[- ]execution)\s+tool\b", re.I)
SKIP = {"e2e", "bench", "benchmark", "benchmarks", "evals", "eval", "mocks", "__mocks__"}

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "agent_exec_code"
CL = Path("/home/user/clones_head")
STR = re.compile(r"""("(?:[^"\\\n]|\\.){20,}"|'(?:[^'\\\n]|\\.){20,}'|`[^`]{20,}`|\"\"\"[\s\S]{20,}?\"\"\")""")


def process(repo):
    out = OUT / (repo.replace("/", "__") + ".json")
    if out.exists():
        return repo, "cached"
    dest = CL / repo.replace("/", "__")
    try:
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:limit=400k",
                            f"https://github.com/{repo}", str(dest)], capture_output=True, timeout=240,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        if r.returncode:
            out.write_text(json.dumps({"repo": repo, "error": "clone_failed"})); return repo, "clone_failed"
        hits = []
        for p in dest.rglob("*"):
            rel = str(p.relative_to(dest))
            if not p.is_file() or not relevant(rel) or p.stat().st_size > 400_000 or set(rel.lower().split("/")[:-1]) & SKIP:
                continue
            text = p.read_text(errors="ignore")
            for m in STR.finditer(text):
                s = m.group(0)
                for k, rx in RX.items():
                    mm = rx.search(s)
                    if mm:
                        hits.append({"file": rel, "kind": k, "line": text.count("\n", 0, m.start()) + 1,
                                     "ctx": s[max(0, mm.start() - 100): mm.end() + 100].replace("\n", " ")})
        out.write_text(json.dumps({"repo": repo, "hits": hits[:200]}))
        return repo, f"{len(hits)} hits"
    except Exception as e:
        out.write_text(json.dumps({"repo": repo, "error": type(e).__name__})); return repo, "error"
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True); CL.mkdir(parents=True, exist_ok=True)
    import csv
    repos = [r["repo"] for r in csv.DictReader(open(ROOT / "data/repo_summary.csv"))]
    print("repos:", len(repos), flush=True)
    with ProcessPoolExecutor(8) as ex:
        for i, f in enumerate(as_completed([ex.submit(process, r) for r in repos]), 1):
            print(f"[{i}/{len(repos)}]", *f.result(), flush=True)


if __name__ == "__main__":
    main()
