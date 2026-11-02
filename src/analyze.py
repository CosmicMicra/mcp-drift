"""Compute post-release drift metrics from data/snapshots/*.json.

Unit of analysis
  repo   : an MCP server repository with >= 2 snapshots that expose >= 1 tool
  step   : a pair of consecutive snapshots (v_i, v_{i+1}) of one repo
  event  : a change observed in a step

Event types
  TOOL_CAP_GAIN      an existing tool (same name in v_i and v_{i+1}) gains a
                     capability class; split into
                       silent      description byte-identical
                       undisclosed description changed but does not mention it
                       disclosed   new description mentions the capability
  DESC_MUTATION      an existing tool's description changes
  DESC_SUSPICIOUS    a mutation adds instruction-like or hidden content
  SERVER_CAP_GAIN    the server (all source files) gains a capability class
  NEW_DOMAIN         a new external hostname literal appears
  NEW_DEP            a new declared dependency appears
  TOOL_ADDED         a new tool name appears after the first tool-bearing snapshot

Output: data/events.jsonl, data/repo_summary.csv, printed summary.
"""
import csv
import glob
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "snapshots"

HIGH_RISK = {"shell", "dynamic_code", "fs_write", "env_secrets"}
DISCLOSE = {
    "network": r"\b(http|https|api|request|fetch|download|upload|url|web|internet|online|remote|server|endpoint|send|post|email|webhook)",
    "shell": r"\b(shell|command|exec|execute|run|terminal|bash|cli|process|script|subprocess|spawn)",
    "fs_write": r"\b(write|save|create|delete|remove|modify|edit|update|file|disk|directory|folder|store|output to)",
    "fs_read": r"\b(read|file|load|open|directory|folder|path|disk|local)",
    "env_secrets": r"\b(environment|env|credential|token|api key|apikey|secret|config|password|auth)",
    "dynamic_code": r"\b(eval|execute code|run code|python code|javascript|script|plugin|dynamic)",
}
DISCLOSE_RE = {k: re.compile(v, re.I) for k, v in DISCLOSE.items()}
SUSPICIOUS = [
    (r"[\U000E0000-\U000E007F]", "unicode_tag"),
    (r"[​-‏⁠-⁤﻿]", "zero_width"),
    (r"<\s*(important|system|instructions?)\s*>", "pseudo_tag"),
    (r"\b(ignore|disregard) (all |any )?(previous|prior|above)", "override"),
    (r"\b(do not|don't|never) (tell|mention|inform|reveal|show)", "concealment"),
    (r"\b(before|first) (using|calling|answering|running) (any|this|other|every)", "precondition"),
    (r"(~/\.ssh|id_rsa|\.aws/|\.env\b|mcp\.json|credentials?)", "sensitive_path"),
    (r"\b(always|must) (call|use|invoke|run) ", "forcing"),
]
SUSP_RE = [(re.compile(p, re.I), n) for p, n in SUSPICIOUS]


def suspicious_markers(old, new):
    out = []
    for rx, name in SUSP_RE:
        if len(rx.findall(new)) > len(rx.findall(old)):
            out.append(name)
    return out


def load():
    for f in sorted(glob.glob(str(SNAP / "*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        yield d


def tool_map(snap):
    m = {}
    for t in snap["tools"]:
        m.setdefault(t["name"], t)  # first definition wins
    return m


def analyze_repo(d):
    snaps = [s for s in d.get("snapshots", [])]
    tooled = [i for i, s in enumerate(snaps) if s["tools"]]
    if len(tooled) < 2:
        return None, []
    snaps = snaps[tooled[0]:]  # start at the first release that exposes tools
    repo = d["repo"]["full_name"]
    events = []
    for i in range(1, len(snaps)):
        a, b = snaps[i - 1], snaps[i]
        if not b["tools"]:
            continue  # extraction gap; do not count tool removals/re-adds
        ta, tb = tool_map(a), tool_map(b)
        base = {"repo": repo, "from": a["commit"][:10], "to": b["commit"][:10],
                "from_tag": a.get("tag"), "to_tag": b.get("tag"), "time": b["time"], "step": i}
        for name in ta.keys() & tb.keys():
            x, y = ta[name], tb[name]
            gained = sorted(set(y["caps"]) - set(x["caps"]))
            desc_changed = x["description"] != y["description"]
            if desc_changed and not (x.get("desc_dynamic") or y.get("desc_dynamic")):
                markers = suspicious_markers(x["description"], y["description"])
                events.append({**base, "type": "DESC_MUTATION", "tool": name, "markers": markers,
                               "old": x["description"][:2000], "new": y["description"][:2000]})
                if markers:
                    events.append({**base, "type": "DESC_SUSPICIOUS", "tool": name, "markers": markers,
                                   "old": x["description"][:2000], "new": y["description"][:2000]})
            for c in gained:
                if y.get("desc_dynamic"):
                    disc = "unknown"
                elif not desc_changed:
                    disc = "silent"
                elif DISCLOSE_RE[c].search(y["description"]) and not DISCLOSE_RE[c].search(x["description"]):
                    disc = "disclosed"
                else:
                    disc = "undisclosed"
                events.append({**base, "type": "TOOL_CAP_GAIN", "tool": name, "cap": c, "disclosure": disc,
                               "direct": c in y.get("direct_caps", []), "via": y.get("caps_via", {}).get(c, "?"),
                               "new_domains": sorted(set(y["domains"]) - set(x["domains"])),
                               "file": y["file"], "desc": y["description"][:1000]})
        for name in sorted(tb.keys() - ta.keys()):
            events.append({**base, "type": "TOOL_ADDED", "tool": name, "caps": tb[name]["caps"]})
        step_desc_changed = any(ta[n]["description"] != tb[n]["description"] for n in ta.keys() & tb.keys())
        step_tools_added = bool(tb.keys() - ta.keys())
        readme_a, readme_b = a.get("readme", ""), b.get("readme", "")
        for c in sorted(set(b["server_caps"]) - set(a["server_caps"])):
            rx = DISCLOSE_RE[c]
            readme_mentions = bool(rx.search(readme_b)) and readme_b != readme_a
            silent = not step_desc_changed and not step_tools_added and readme_a == readme_b
            events.append({**base, "type": "SERVER_CAP_GAIN", "cap": c, "silent": silent,
                           "desc_changed": step_desc_changed, "tools_added": step_tools_added,
                           "readme_changed": readme_a != readme_b, "readme_mentions": readme_mentions})
        for dom in sorted(set(b["server_domains"]) - set(a["server_domains"])):
            events.append({**base, "type": "NEW_DOMAIN", "domain": dom})
        for dep in sorted(set(b["deps"]) - set(a["deps"])):
            events.append({**base, "type": "NEW_DEP", "dep": dep})
    summ = {
        "repo": repo, "stars": d["repo"]["stars"], "language": d["repo"]["language"],
        "n_versions": len(snaps), "tagged": sum(1 for s in snaps if s.get("tag") not in (None, "HEAD")) >= 3,
        "first_time": snaps[0]["time"], "last_time": snaps[-1]["time"],
        "n_tools_first": len(snaps[0]["tools"]), "n_tools_last": len(snaps[-1]["tools"]),
    }
    for t in ("TOOL_CAP_GAIN", "DESC_MUTATION", "DESC_SUSPICIOUS", "SERVER_CAP_GAIN", "NEW_DOMAIN", "NEW_DEP", "TOOL_ADDED"):
        summ[t] = sum(1 for e in events if e["type"] == t)
    summ["silent_gain"] = sum(1 for e in events if e["type"] == "TOOL_CAP_GAIN" and e["disclosure"] == "silent")
    summ["silent_server_gain"] = sum(1 for e in events if e["type"] == "SERVER_CAP_GAIN" and e["silent"])
    summ["silent_server_high_risk_gain"] = sum(1 for e in events if e["type"] == "SERVER_CAP_GAIN" and e["silent"] and e["cap"] in HIGH_RISK)
    summ["silent_direct_high_risk_gain"] = sum(1 for e in events if e["type"] == "TOOL_CAP_GAIN"
                                               and e["disclosure"] == "silent" and e["cap"] in HIGH_RISK and e["direct"])
    summ["silent_high_risk_gain"] = sum(1 for e in events if e["type"] == "TOOL_CAP_GAIN"
                                        and e["disclosure"] == "silent" and e["cap"] in HIGH_RISK)
    return summ, events


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "0/0"


def main():
    summaries, all_events, status = [], [], Counter()
    for d in load():
        if "error" in d:
            status[d["error"]] += 1
            continue
        s, ev = analyze_repo(d)
        if s is None:
            status["no_tools_or_single_version"] += 1
            continue
        status["analyzed"] += 1
        summaries.append(s)
        all_events += ev
    (ROOT / "data" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in all_events))
    if summaries:
        with open(ROOT / "data" / "repo_summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
            w.writeheader()
            w.writerows(summaries)
    n = len(summaries)
    print("status:", dict(status))
    print(f"repos analyzed: {n}; versions: {sum(s['n_versions'] for s in summaries)}; "
          f"median versions/repo: {statistics.median([s['n_versions'] for s in summaries]) if n else 0}")
    for key, label in [("TOOL_CAP_GAIN", "any tool capability gain"), ("silent_gain", "silent tool capability gain"),
                       ("silent_high_risk_gain", "silent HIGH-RISK tool capability gain"),
                       ("silent_direct_high_risk_gain", "silent HIGH-RISK gain in the tool's own handler"),
                       ("DESC_MUTATION", "tool description mutation"), ("DESC_SUSPICIOUS", "suspicious description mutation"),
                       ("SERVER_CAP_GAIN", "server capability gain"),
                       ("silent_server_gain", "SILENT server capability gain (no tool/desc/README change)"),
                       ("silent_server_high_risk_gain", "SILENT server HIGH-RISK capability gain"), ("NEW_DOMAIN", "new external domain")]:
        print(f"  repos with {label}: {pct(sum(1 for s in summaries if s[key]), n)}")
    gains = [e for e in all_events if e["type"] == "TOOL_CAP_GAIN"]
    print("tool capability gains by cap x disclosure:")
    tab = defaultdict(Counter)
    for e in gains:
        tab[e["cap"]][e["disclosure"]] += 1
    for c in sorted(tab):
        print(f"  {c:13} {dict(tab[c])}")
    sus = Counter(m for e in all_events if e["type"] == "DESC_SUSPICIOUS" for m in e["markers"])
    print("suspicious markers:", dict(sus))


if __name__ == "__main__":
    main()
