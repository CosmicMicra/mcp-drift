"""Paper figures and the numbers quoted in the text.

Reads data/events.jsonl and data/repo_summary.csv (written by analyze.py).
Writes paper/figures/*.pdf and data/paper_numbers.json.

Palette: blue #2a78d6 / orange #eb6834 (validated for colour-vision deficiency);
bars also differ by hatch so they survive greyscale printing.
"""
import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a64", "#dcdbd5"
HIGH = {"shell", "dynamic_code", "fs_write", "env_secrets"}
CAP_LABEL = {"shell": "Run commands", "dynamic_code": "Run dynamic code", "fs_write": "Write/delete files",
             "env_secrets": "Read env vars/secrets", "fs_read": "Read files", "network": "Network access"}
YEAR = 365.25 * 86400

plt.rcParams.update({
    "font.family": "serif", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": INK, "axes.linewidth": 0.6,
    "pdf.fonttype": 42,
})


def load():
    ev = [json.loads(l) for l in open(ROOT / "data/events.jsonl")]
    summ = list(csv.DictReader(open(ROOT / "data/repo_summary.csv")))
    return ev, summ


def prevalence(ev, summ):
    """Share of servers with >=1 tool-level gain / silent gain, per capability."""
    n = len(summ)
    any_g, silent_g = defaultdict(set), defaultdict(set)
    for e in ev:
        if e["type"] == "TOOL_CAP_GAIN":
            any_g[e["cap"]].add(e["repo"])
            if e["disclosure"] == "silent":
                silent_g[e["cap"]].add(e["repo"])
    order = sorted(CAP_LABEL, key=lambda c: len(any_g[c]))
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    y = range(len(order))
    a = [100 * len(any_g[c]) / n for c in order]
    s = [100 * len(silent_g[c]) / n for c in order]
    h = 0.36
    ax.barh([i + h / 2 for i in y], a, height=h, color=BLUE, label="Any gain", edgecolor="white", linewidth=0.8)
    ax.barh([i - h / 2 for i in y], s, height=h, color=ORANGE, label="Silent (description unchanged)",
            hatch="////", edgecolor="white", linewidth=0.8)
    for i, (va, vs) in enumerate(zip(a, s)):
        ax.text(va + 0.3, i + h / 2, f"{va:.1f}%", va="center", fontsize=6.5, color=INK)
        ax.text(vs + 0.3, i - h / 2, f"{vs:.1f}%", va="center", fontsize=6.5, color=MUTED)
    ax.set_yticks(list(y), [CAP_LABEL[c] for c in order])
    ax.set_xlabel(f"Servers (%), n = {n:,}")
    ax.xaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_xlim(0, max(a) * 1.18 if a else 1)
    ax.legend(loc="lower center", bbox_to_anchor=(0.4, 1.0), ncol=2, frameon=False, handlelength=1.2, columnspacing=1.0)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "fig_prevalence.pdf")
    plt.close(fig)
    return {c: {"any_servers": len(any_g[c]), "silent_servers": len(silent_g[c])} for c in CAP_LABEL}


def policies(ev, summ):
    """Prompts per server-year under each re-approval rule, and the share of
    silent high-risk tool gains each rule would surface (proxy until human labels are in)."""
    steps = defaultdict(lambda: defaultdict(set))
    target = set()  # (repo, step) with a silent high-risk tool gain
    # NOTE: this target comes from the same detector as the capability rules, so their coverage is
    # trivially 100%. Final figure: replace with human-labelled security-relevant changes.
    for e in ev:
        k, s = e["repo"], e["step"]
        if e["type"] == "DESC_MUTATION":
            steps[k]["desc"].add(s)
        if e["type"] == "TOOL_ADDED":
            steps[k]["added"].add(s)
        if e["type"] in ("TOOL_CAP_GAIN", "SERVER_CAP_GAIN"):
            steps[k]["cap"].add(s)
            if e["cap"] in HIGH:
                steps[k]["high"].add(s)
        if e["type"] == "TOOL_CAP_GAIN" and e["cap"] in HIGH and e.get("direct"):
            steps[k]["highdirect"].add(s)
        if e["type"] == "TOOL_CAP_GAIN" and e["cap"] in HIGH and e["disclosure"] == "silent":
            target.add((k, s))
    rules = {
        "Every update": lambda k, n: set(range(1, n)),
        "Description changed or tool added": lambda k, n: steps[k]["desc"] | steps[k]["added"],
        "Any tool's description changed": lambda k, n: steps[k]["desc"],
        "Changed tool's own description": None,
        "Any capability gained": lambda k, n: steps[k]["cap"],
        "High-risk capability gained": lambda k, n: steps[k]["high"],
    }
    out = {}
    eligible = [r for r in summ if (int(r["last_time"]) - int(r["first_time"])) / YEAR >= 0.25]
    for name, f in rules.items():
        if f is None:   # per-tool rule: a silent gain is by definition one whose own description did not change
            out[name] = dict(out["Any tool's description changed"], coverage=0.0)
            continue
        rates, hit = [], 0
        for r in eligible:
            k, n = r["repo"], int(r["n_versions"])
            yrs = (int(r["last_time"]) - int(r["first_time"])) / YEAR
            fired = f(k, n)
            rates.append(len(fired) / yrs)
        for (k, s) in target:
            n = next((int(r["n_versions"]) for r in summ if r["repo"] == k), 0)
            if s in f(k, n):
                hit += 1
        out[name] = {"median_per_year": st.median(rates), "mean_per_year": st.mean(rates),
                     "coverage": hit / len(target) if target else 0.0}
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    short = {"Every update": ("Every update", (-4, -11), "right"),
             "Description changed or tool added": ("Description changed\nor tool added", (5, -3), "left"),
             "Any tool's description changed": ("Any description\nchanged (server)", (5, -3), "left"),
             "Changed tool's own description": ("Tool's own description\nchanged", (5, 2), "left"),
             "Any capability gained": ("Any capability", (4, -11), "left"),
             "High-risk capability gained": ("High-risk\ncapability", (-4, -16), "right")}
    for name, v in out.items():
        x, y = max(v["median_per_year"], 0.05), 100 * v["coverage"]
        ax.plot(x, y, "o", color=BLUE, markersize=5, markeredgecolor="white", markeredgewidth=1, zorder=3)
        lab, off, ha = short[name]
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=off, ha=ha, fontsize=6.3, color=INK, linespacing=0.95)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 5, 10, 20], ["0.5", "1", "2", "5", "10", "20"])
    ax.set_xlim(0.4, 30)
    ax.set_xlabel(f"Prompts per server per year (median, n = {len(eligible):,})")
    ax.set_ylabel("Risky changes surfaced (%)")
    ax.set_ylim(-5, 105)
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG / "fig_policies.pdf")
    plt.close(fig)
    return out, len(eligible), len(target)


def main():
    ev, summ = load()
    n = len(summ)
    nums = {"servers": n, "versions": sum(int(r["n_versions"]) for r in summ),
            "median_versions": st.median(int(r["n_versions"]) for r in summ)}
    for key in ("DESC_MUTATION", "TOOL_ADDED", "TOOL_CAP_GAIN", "silent_gain", "silent_high_risk_gain",
                "silent_direct_high_risk_gain", "SERVER_CAP_GAIN", "silent_server_gain",
                "silent_server_high_risk_gain", "DESC_SUSPICIOUS", "NEW_DOMAIN"):
        c = sum(1 for r in summ if int(r[key]) > 0)
        nums[f"servers_with_{key}"] = c
        nums[f"pct_servers_with_{key}"] = round(100 * c / n, 1)
    nums["by_capability"] = prevalence(ev, summ)
    pol, n_elig, n_target = policies(ev, summ)
    nums["policies"] = pol
    nums["policy_servers"] = n_elig
    nums["policy_target_steps"] = n_target
    (ROOT / "data/paper_numbers.json").write_text(json.dumps(nums, indent=2))
    print(json.dumps(nums, indent=2))


if __name__ == "__main__":
    main()
