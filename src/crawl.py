"""Collect candidate MCP server repositories from GitHub search.

GitHub search returns at most 1,000 results per query, so we slice each
topic query by star range until every slice is under the cap.
Output: data/repos.jsonl (one repository per line, deduplicated).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "repos.jsonl"
TOPICS = ["mcp-server", "model-context-protocol", "mcp-servers"]
MIN_STARS = 20
CAP = 1000


def search(q, page):
    cmd = ["gh", "api", "-X", "GET", "search/repositories",
           "-f", f"q={q}", "-f", "per_page=100", "-f", f"page={page}",
           "-f", "sort=stars"]
    for attempt in range(6):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        if "rate limit" in (r.stdout + r.stderr).lower():
            time.sleep(30 * (attempt + 1))
            continue
        time.sleep(2 ** attempt)
    raise RuntimeError(f"search failed: {q} p{page}: {r.stderr[:300]}")


def count(q):
    return search(q, 1)["total_count"]


def slices(topic, lo, hi):
    """Yield star ranges [lo, hi] whose result count is under the cap."""
    q = f"topic:{topic} stars:{lo}..{hi} fork:false archived:false"
    n = count(q)
    if n <= CAP or lo == hi:
        yield q, n
        return
    mid = (lo + hi) // 2
    yield from slices(topic, lo, mid)
    yield from slices(topic, mid + 1, hi)


def main():
    seen = {}
    if OUT.exists():
        for line in OUT.open():
            r = json.loads(line)
            seen[r["full_name"]] = r
    for topic in TOPICS:
        for q, n in slices(topic, MIN_STARS, 1_000_000):
            print(f"{q}  -> {n}", file=sys.stderr)
            for page in range(1, min(10, (n + 99) // 100) + 1):
                data = search(q, page)
                for it in data["items"]:
                    seen[it["full_name"]] = {
                        "full_name": it["full_name"],
                        "stars": it["stargazers_count"],
                        "language": it["language"],
                        "created_at": it["created_at"],
                        "pushed_at": it["pushed_at"],
                        "topics": it.get("topics", []),
                        "description": it.get("description"),
                        "fork": it["fork"],
                    }
                time.sleep(2)
            OUT.write_text("".join(json.dumps(r) + "\n" for r in seen.values()))
    print(f"total unique repos: {len(seen)}", file=sys.stderr)


if __name__ == "__main__":
    main()
