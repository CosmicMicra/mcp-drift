"""Summarize data/depth_check.jsonl: tool capabilities found at depth 2 and 6 relative to depth 4."""
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
HIGH = {"shell", "dynamic_code", "fs_write", "env_secrets"}
rows = [json.loads(l) for l in open(ROOT / "data/depth_check.jsonl")]
tot = {d: 0 for d in ("2", "4", "6")}; hi = dict(tot); tools = 0; diff = Counter(); per = {d: Counter() for d in tot}
srv_any = Counter()
for r in rows:
    c = r["caps"]; changed = Counter()
    for k, caps4 in c["4"].items():
        tools += 1
        for d in tot:
            s = set(c[d].get(k, []))
            tot[d] += len(s); hi[d] += len(s & HIGH)
            for x in s: per[d][x] += 1
            if d != "4" and s != set(caps4):
                diff[d] += 1; changed[d] = 1
    for d in changed: srv_any[d] += 1
print(f"servers {len(rows)}, tools {tools}")
for d in ("2", "4", "6"):
    print(f"depth {d}: tool-capability pairs {tot[d]} ({100*(tot[d]-tot['4'])/tot['4']:+.1f}% vs 4), high-risk {hi[d]} ({100*(hi[d]-hi['4'])/max(hi['4'],1):+.1f}%), tools whose set differs from depth 4: {diff[d]} ({100*diff[d]/tools:.1f}%), servers affected {srv_any[d]}")
for x in sorted(per["4"]):
    print(f"  {x:13s} d2 {per['2'][x]:5d}  d4 {per['4'][x]:5d}  d6 {per['6'][x]:5d}")
