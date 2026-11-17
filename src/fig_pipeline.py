"""Pipeline diagram (Figure 1) for the methodology section."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLUE, INK, MUTED, SOFT = "#2a78d6", "#1f1f1e", "#6b6a64", "#eef3fb"
plt.rcParams.update({"font.family": "serif", "font.size": 7, "pdf.fonttype": 42})

main = [
    ("Crawl GitHub", "MCP topics,\n$\\geq$20 stars", "4,812 repositories"),
    ("Filter", "language, size, tools\nin $\\geq$2 versions", "2,571 servers"),
    ("Choose versions", "release tags, or\ncommits over time", "35,725 versions"),
    ("Extract tools", "name, description,\nhandler (tree-sitter)", "85,526 tools (latest)"),
    ("Find capabilities", "6 classes reachable\nfrom each handler", "per tool and server"),
    ("Compare versions", "capability gains,\ndescription edits", "33,130 version pairs"),
]
below = {4: ("Validate", "stratified sample,\nhuman labels", "80 events, 60 tools"),
         5: ("Replay policies", "6 re-approval rules\non real histories", "1,667 servers")}

W, H, GAP = 14.6, 11.0, 2.4
fig, ax = plt.subplots(figsize=(7.1, 2.0))
ax.set_xlim(0, 6 * W + 5 * GAP + 1); ax.set_ylim(0, 27); ax.axis("off")

def box(x, y, title, sub, count, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.2,rounding_size=0.9",
                                fc="white" if dashed else SOFT, ec=BLUE, lw=0.8, ls="--" if dashed else "-"))
    ax.text(x + W / 2, y + H - 1.3, title, ha="center", va="top", fontsize=6.3, color=INK, weight="bold")
    ax.text(x + W / 2, y + H / 2 - 0.2, sub, ha="center", va="center", fontsize=5.3, color=MUTED, linespacing=1.05)
    ax.text(x + W / 2, y + 1.0, count, ha="center", va="bottom", fontsize=5.6, color=BLUE)

def arrow(p, q):
    ax.annotate("", q, p, arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.7, mutation_scale=7, shrinkA=0, shrinkB=0))

yt, yb = 15.0, 0.8
xs = [0.5 + i * (W + GAP) for i in range(6)]
for x, s in zip(xs, main):
    box(x, yt, *s)
for a, b in zip(xs, xs[1:]):
    arrow((a + W + 0.4, yt + H / 2), (b - 0.4, yt + H / 2))
# both downstream analyses use the version comparison
src = (xs[5] + W / 2, yt - 0.4)
for i, s in below.items():
    box(xs[i], yb, *s, dashed=True)
arrow(src, (xs[5] + W / 2, yb + H + 0.4))
ax.plot([xs[5] + W / 2, xs[4] + W / 2], [yt - 1.9, yt - 1.9], color=INK, lw=0.7)
arrow((xs[4] + W / 2, yt - 1.9), (xs[4] + W / 2, yb + H + 0.4))
ax.text(xs[4] - 0.8, yb + H / 2, "RQ3", ha="right", va="center", fontsize=6, color=MUTED)
ax.text(xs[5] + W + 0.3, yb + H / 2, "RQ4", ha="left", va="center", fontsize=6, color=MUTED)
fig.savefig(ROOT / "paper/figures/fig_pipeline.pdf", bbox_inches="tight", pad_inches=0.02)
