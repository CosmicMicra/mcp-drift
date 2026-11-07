"""Find tool descriptions that instruct the AI agent to execute something itself
(agent-mediated execution): run a command in its shell, install a package, pipe a
download into a shell, etc. Scans every tool description in every snapshot.

Usage: python src/agent_exec.py [--dump N]
Output: data/agent_exec.jsonl (one row per repo/tool/version match) + summary.
"""
import glob, json, re, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

V = r"(?:run|execute|exec|invoke|launch|paste|type|enter)"
PATTERNS = {
    # explicit: run X in/using/with your shell/terminal/bash tool
    "run_in_shell": rf"\b{V}\b[^.\n]{{0,80}}\b(?:in|using|with|via|through)\s+(?:your|the\s+user'?s?|a|the)\s+(?:own\s+)?(?:shell|terminal|bash|command[- ]line|console|cli)\b",
    # names of agent shell tools
    "agent_shell_tool": r"\b(?:Bash tool|shell tool|terminal tool|run_in_terminal|shell_execute|execute_command tool|run_command tool)\b",
    # run the returned / following / this command
    "run_returned_cmd": rf"\b{V}\s+(?:the\s+)?(?:returned|following|above|below|this|these|provided|generated|given|printed|output(?:ted)?)\s+(?:shell\s+|terminal\s+|bash\s+|cli\s+)?(?:command|commands|script|snippet|code)\b",
    # tells the agent to install something
    "install_instruction": r"\b(?:run|execute)\s+[`'\"]?(?:npm|npx|pnpm|yarn|pip3?|pipx|uv|uvx|brew|apt(?:-get)?|cargo|go)\s+(?:install|add|i)\b",
    # download piped into a shell
    "pipe_to_shell": r"\b(?:curl|wget)\b[^\n]{0,120}\|\s*(?:sudo\s+)?(?:ba|z)?sh\b",
}
RX = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
MUST = re.compile(r"\b(?:you\s+)?(?:MUST|ALWAYS|REQUIRED to|need to|should)\b", re.I)


def scan(desc):
    hits = {}
    for k, rx in RX.items():
        m = rx.search(desc)
        if m:
            hits[k] = desc[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
    return hits


def main():
    dump = int(sys.argv[sys.argv.index("--dump") + 1]) if "--dump" in sys.argv else 0
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/snapshots/*.json"))):
        d = json.load(open(f))
        if "snapshots" not in d:
            continue
        repo = d["repo"]["full_name"]
        for i, s in enumerate(d["snapshots"]):
            for t in s["tools"]:
                h = scan(t["description"] or "")
                if h:
                    rows.append({"repo": repo, "stars": d["repo"]["stars"], "tool": t["name"], "v": i,
                                 "n_versions": len(d["snapshots"]), "tag": s.get("tag"), "time": s["time"],
                                 "kinds": sorted(h), "must": bool(MUST.search(t["description"])),
                                 "ctx": h, "desc": t["description"][:1500]})
    (ROOT / "data/agent_exec.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    repos = {r["repo"] for r in rows}
    print("matching (repo,tool,version) rows:", len(rows), "| repos:", len(repos))
    print("by kind (repos):", {k: len({r['repo'] for r in rows if k in r['kinds']}) for k in PATTERNS})
    if dump:
        seen = set()
        import random
        random.Random(1).shuffle(rows)
        for r in rows:
            key = (r["repo"], r["tool"])
            if key in seen:
                continue
            seen.add(key)
            print(f"\n## {r['repo']} :: {r['tool']}  {r['kinds']}")
            for k, c in r["ctx"].items():
                print(f"   [{k}] ...{c}...")
            if len(seen) >= dump:
                break


if __name__ == "__main__":
    main()
