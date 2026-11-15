"""RQ2 extension: MCP annotation hints versus code-derived capabilities, over time.

readOnlyHint=true is contradicted by a reachable write/delete, command-execution or dynamic-code capability;
openWorldHint=false is contradicted by reachable network access. We report
  - adoption: tools/servers declaring any hint (latest version);
  - contradictions at the latest version;
  - stale hints: a hint that was consistent when first declared and is contradicted by a later version
    whose hint is unchanged (the annotation went stale after a capability gain).
Output: data/annotations.json and examples on stdout.
"""
import csv, glob, json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
MODIFY = {"fs_write", "shell", "dynamic_code"}


def contra(ann, caps, direct_only=False):
    # Only readOnlyHint is checked: openWorldHint=false legitimately covers tools that talk to one fixed service.
    out = []
    if ann.get("readOnlyHint") is True and MODIFY & set(caps):
        out.append("readOnly vs " + ",".join(sorted(MODIFY & set(caps))))
    return out


def main():
    pop = set(open(ROOT / "data/population.txt").read().split())
    res = Counter(); stale, latest_contra, examples = [], [], []
    for f in glob.glob(str(ROOT / "data/snapshots/*.json")):
        d = json.load(open(f))
        repo = d.get("repo", {}).get("full_name")
        if repo not in pop or "snapshots" not in d:
            continue
        snaps = [s for s in d["snapshots"] if s["tools"]]
        if not snaps:
            continue
        last = snaps[-1]
        ann_tools = [t for t in last["tools"] if t.get("annotations")]
        if ann_tools:
            res["servers_with_hints"] += 1
            res["tools_with_hints"] += len(ann_tools)
            res["tools_readOnly_true"] += sum(1 for t in ann_tools if t["annotations"].get("readOnlyHint") is True)
            res["tools_openWorld_false"] += sum(1 for t in ann_tools if t["annotations"].get("openWorldHint") is False)
        res["tools_total_latest"] += len(last["tools"])
        for t in ann_tools:
            c = contra(t["annotations"], t["caps"])
            if c:
                latest_contra.append((repo, t["name"], c, contra(t["annotations"], t.get("direct_caps", []))))
        # staleness: follow each tool by name
        hist = {}
        for i, s in enumerate(snaps):
            for t in s["tools"]:
                hist.setdefault(t["name"], []).append((i, s, t))
        for name, h in hist.items():
            first = next(((i, s, t) for i, s, t in h if t.get("annotations")), None)
            if not first or contra(first[2]["annotations"], first[2]["caps"]):
                continue
            for i, s, t in h:
                if i <= first[0] or t.get("annotations") != first[2]["annotations"]:
                    continue
                c = contra(t["annotations"], t["caps"])
                if c:
                    stale.append((repo, name, first[1].get("tag") or first[1]["commit"][:10],
                                  s.get("tag") or s["commit"][:10], c, bool(contra(t["annotations"], t.get("direct_caps", [])))))
                    break
    # Do hints change when an annotated tool gains a capability? (all gains / high-risk / modify-class gains
    # in tools that declared readOnlyHint=true before the gain)
    for f in glob.glob(str(ROOT / "data/snapshots/*.json")):
        d = json.load(open(f)); repo = d.get("repo", {}).get("full_name")
        if repo not in pop or "snapshots" not in d:
            continue
        sn = [s for s in d["snapshots"] if s["tools"]]
        for a, b in zip(sn, sn[1:]):
            ta = {t["name"]: t for t in a["tools"]}; tb = {t["name"]: t for t in b["tools"]}
            for n in ta.keys() & tb.keys():
                x, y = ta[n], tb[n]
                if not (x.get("annotations") and y.get("annotations")):
                    continue
                g = set(y["caps"]) - set(x["caps"])
                if not g:
                    continue
                same = x["annotations"] == y["annotations"]
                res["gain_in_annotated_tool"] += 1
                res["gain_in_annotated_tool_hints_unchanged"] += same
                if g & {"shell", "dynamic_code", "fs_write", "env_secrets"}:
                    res["highrisk_gain_in_annotated_tool"] += 1
                    res["highrisk_gain_in_annotated_tool_hints_unchanged"] += same
                if x["annotations"].get("readOnlyHint") is True and g & MODIFY:
                    res["modify_gain_in_readonly_tool"] += 1
                    res["modify_gain_in_readonly_tool_still_readonly"] += y["annotations"].get("readOnlyHint") is True
    res["tools_contradicted_latest"] = len(latest_contra)
    res["servers_contradicted_latest"] = len({r for r, *_ in latest_contra})
    res["tools_contradicted_latest_direct"] = sum(1 for x in latest_contra if x[3])
    res["stale_tools"] = len(stale)
    res["stale_servers"] = len({r for r, *_ in stale})
    res["stale_tools_direct"] = sum(1 for x in stale if x[5])
    out = {"summary": dict(res), "stale": stale, "latest_contradictions": latest_contra}
    (ROOT / "data/annotations.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(res), indent=1))
    for x in stale[:25]:
        print("STALE", x)


if __name__ == "__main__":
    main()
