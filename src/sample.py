"""Draw stratified, seeded samples for manual validation.

validation/drift_events.csv   ~200 drift events to label (real / false positive)
validation/extractor_tools.csv 60 extracted tools to label (is this a real MCP tool? description right?)
Each row has a GitHub link so the labeller can check the change directly.
"""
import csv, json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
HIGH = {"shell", "dynamic_code", "fs_write", "env_secrets"}
rng = random.Random(2027)
ev = [json.loads(l) for l in open(ROOT / "data/events.jsonl")]

def pick(rows, k, per_repo=1):
    rng.shuffle(rows); out, seen = [], {}
    for r in rows:
        if seen.get(r["repo"], 0) < per_repo:
            seen[r["repo"]] = seen.get(r["repo"], 0) + 1; out.append(r)
        if len(out) == k: break
    return out

strata = {
    "silent_highrisk_direct": pick([e for e in ev if e["type"] == "TOOL_CAP_GAIN" and e["disclosure"] == "silent" and e["cap"] in HIGH and e.get("direct")], 50),
    "silent_highrisk_via_helper": pick([e for e in ev if e["type"] == "TOOL_CAP_GAIN" and e["disclosure"] == "silent" and e["cap"] in HIGH and not e.get("direct")], 30),
    "other_tool_gain": pick([e for e in ev if e["type"] == "TOOL_CAP_GAIN" and not (e["disclosure"] == "silent" and e["cap"] in HIGH)], 30),
    "silent_server_gain": pick([e for e in ev if e["type"] == "SERVER_CAP_GAIN" and e["silent"]], 50),
    "suspicious_desc": pick([e for e in ev if e["type"] == "DESC_SUSPICIOUS"], 40),
}
out = ROOT / "validation"; out.mkdir(exist_ok=True)
with open(out / "drift_events.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "stratum", "repo", "tool", "cap_or_markers", "via", "from_tag", "to_tag", "compare_url",
                "old_desc", "new_desc", "LABEL extraction_error / benign / security_relevant / unsure", "notes"])
    i = 0
    for s, rows in strata.items():
        for e in rows:
            i += 1
            w.writerow([i, s, e["repo"], e.get("tool", ""), e.get("cap") or ",".join(e.get("markers", [])), e.get("via", ""),
                        e.get("from_tag") or e["from"], e.get("to_tag") or e["to"],
                        f"https://github.com/{e['repo']}/compare/{e['from']}...{e['to']}",
                        e.get("old", "")[:500], (e.get("new") or e.get("desc", ""))[:500], "", ""])
# extractor sample: random tools from HEAD snapshots
tools = []
for p in (ROOT / "data/snapshots").glob("*.json"):
    d = json.load(open(p))
    if "snapshots" not in d or not d["snapshots"]: continue
    s = d["snapshots"][-1]
    for t in s["tools"]:
        tools.append((d["repo"]["full_name"], s["commit"], t))
rng.shuffle(tools); seen, rows = set(), []
for repo, c, t in tools:
    if repo in seen: continue
    seen.add(repo); rows.append((repo, c, t))
    if len(rows) == 60: break
with open(out / "extractor_tools.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "repo", "tool", "file_url", "description", "caps",
                "LABEL real tool? y/n", "LABEL description correct? y/n", "LABEL missed caps", "notes"])
    for i, (repo, c, t) in enumerate(rows, 1):
        w.writerow([i, repo, t["name"], f"https://github.com/{repo}/blob/{c}/{t['file']}",
                    t["description"][:400], ",".join(t["caps"]), "", "", "", ""])
print({k: len(v) for k, v in strata.items()}, "tools:", len(rows))
