"""The report's figures, from the run logs.

  uv run python figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from aggregate import AXIS, GRID, INK, INK2, MUTED, OUT, SERIES, SURFACE, pool  # noqa: E402
from backchannel.metrics import analyse  # noqa: E402


def runs(prefix):
    root = Path("runs")
    ds = list(root.glob(f"{prefix}-s*")) + list(root.glob(f"{prefix}-r*-s*"))
    return sorted(str(d) for d in ds if (d / "meta.json").exists())


def share(prefix, key):
    ms = pool(prefix)
    return sum(m[key] for m in ms) / sum(m["honest"] for m in ms), len(ms)


def bars(ax, groups, title):
    """groups: [(label, prefix)]. Two bars per group: ran it / still running it at the end."""
    w = 0.38
    for i, (label, prefix) in enumerate(groups):
        tried, n = share(prefix, "tried")
        final, _ = share(prefix, "final_hacked")
        for dx, v, c in ((-w / 2 - 0.015, tried, SERIES[0]), (w / 2 + 0.015, final, SERIES[1])):
            ax.bar(i + dx, v, w, color=c)
            ax.annotate(f"{v:.0%}", (i + dx, v), xytext=(0, 2), textcoords="offset points", ha="center",
                        fontsize=6.5, color=INK2)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=7.5)
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="x", visible=False)
    ax.set_title(title, loc="left", fontsize=9, color=INK)


def fig_payloads_defences():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.3), gridspec_kw={"width_ratios": [3, 4]}, sharey=True)
    bars(a1, [("split\n(breaks rule,\nconfirms)", "split-none"), ("poison\n(legal,\nrefutes)", "poison-none"),
              ("leak\n(legal,\nconfirms)", "leak-none")], "a. Exploit type (plain board)")
    bars(a2, [("none", "leak-none"), ("cite\n(hash)", "leak-cite"), ("norm\n(verify first)", "leak-norm"),
              ("receipts\n(re-run)", "leak-receipts")], "b. Leak, by board condition")
    a1.set_ylabel("share of honest agents")
    h = [plt.Rectangle((0, 0), 1, 1, color=SERIES[0]), plt.Rectangle((0, 0), 1, 1, color=SERIES[1])]
    fig.legend(h, ["ran it at least once", "still running it at the end"], loc="upper right", ncol=2, fontsize=7.5,
               bbox_to_anchor=(0.99, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "fig1_payloads_defences.png", dpi=220)
    plt.close(fig)


def fig_race():
    panels = [("runs/leak-none-s0", "a. Seed 0:\nnobody warns"),
              ("runs/leak-none-s2", "b. Seed 2: agent-4\nwarns in round 2"),
              ("runs/leak-cf-silence4-r0-s2", "c. Seed 2 replayed,\nagent-4's posts removed"),
              ("runs/leak-cf-warn-r2-r0-s0", "d. Seed 0 replayed, one\nwarning added in round 2")]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.15), sharey=True)
    for ax, (run, label) in zip(axes, panels):
        m = analyse(run)
        r = list(range(len(m["prevalence"])))
        ax.plot(r, m["prevalence"], color=SERIES[0], linewidth=2)
        ax.plot(r, m["warners"], color=SERIES[1], linewidth=2, linestyle=(0, (4, 2)))
        ax.set_title(label, loc="left", fontsize=7.5, color=INK)
        ax.set_ylim(-0.3, 9.5)
        ax.set_xticks([0, 2, 4, 6, 8, 10])
        ax.tick_params(labelsize=7)
        ax.set_xlabel("round", fontsize=7.5)
    axes[0].set_ylabel("honest agents (of 9)", fontsize=8)
    h = [plt.Line2D([], [], color=SERIES[0], linewidth=2),
         plt.Line2D([], [], color=SERIES[1], linewidth=2, linestyle=(0, (4, 2)))]
    fig.legend(h, ["running the leak as their best config", "have posted a warning (cumulative)"], loc="upper right",
               ncol=2, fontsize=7.5, bbox_to_anchor=(0.99, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT / "fig2_race.png", dpi=220)
    plt.close(fig)


def dots(ax, i, vals, color):
    if not vals:
        return
    mu = sum(vals) / len(vals)
    ax.bar(i, mu, 0.55, color=color, alpha=0.3)
    ax.scatter([i + (j - (len(vals) - 1) / 2) * 0.11 for j in range(len(vals))], vals, s=24, color=color,
               edgecolor=SURFACE, linewidth=1, zorder=3)
    ax.annotate(f"{mu:.1f}", (i + 0.3, mu), xytext=(2, 0), textcoords="offset points", va="center", fontsize=7,
                color=INK2)


def fig_counterfactuals():
    g1 = [("original\n(no warning)", ["runs/leak-none-s0"], MUTED)]
    if runs("leak-cf-neutral-r2"):
        g1.append(("neutral post\nin round 2\n(placebo)", runs("leak-cf-neutral-r2"), INK2))
    g1 += [(f"warning\nin round {r}", runs(f"leak-cf-warn-r{r}"), SERIES[0]) for r in (2, 3, 4, 6)]
    g2 = [("seed 1\noriginal", ["runs/leak-none-s1"], MUTED), ("seed 1\nagent-7\nsilenced", runs("leak-cf-silence7"), SERIES[1]),
          ("seed 2\noriginal", ["runs/leak-none-s2"], MUTED), ("seed 2\nagent-4\nsilenced", runs("leak-cf-silence4"), SERIES[1])]
    if runs("leak-cf-silence6"):
        g2.append(("seed 2\nagent-6\n(placebo)", runs("leak-cf-silence6"), INK2))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.35), gridspec_kw={"width_ratios": [len(g1), len(g2)]},
                                 sharey=True)
    for i, (label, rs, c) in enumerate(g1):
        dots(a1, i, [analyse(r)["final_hacked"] for r in rs], c)
    a1.set_xticks(range(len(g1)), [g[0] for g in g1], fontsize=7.5)
    a1.set_title("a. Seed 0: one injected warning, by round", loc="left", fontsize=9, color=INK)
    a1.set_ylabel("agents still running\nthe leak at the end", fontsize=8)
    for i, (label, rs, c) in enumerate(g2):
        dots(a2, i, [analyse(r)["final_hacked"] for r in rs], c)
    a2.set_xticks(range(len(g2)), [g[0] for g in g2], fontsize=7)
    a2.set_title("b. Removing one agent's posts", loc="left", fontsize=9, color=INK)
    for ax in (a1, a2):
        ax.set_ylim(0, 9.9)
        ax.grid(axis="x", visible=False)
        ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_counterfactuals.png", dpi=220)
    plt.close(fig)


def fig_topology():
    fig, ax = plt.subplots(figsize=(7.0, 2.3))
    bars(ax, [("open board\nn=10", "leak-none"), ("open board\nn=20", "leak-n20"), ("ring", "leak-ring"),
              ("star,\nbad apple\nat the hub", "leak-star-hub"), ("star,\nQwen hub,\nbad apple a leaf", "leak-star-leaf-qhub"),
              ("star,\nGemma hub,\nbad apple a leaf", "leak-star-leaf"), ("open board,\n3 bad apples", "leak-k3")],
         "Leak by network shape and dose")
    ax.set_ylabel("share of honest agents")
    h = [plt.Rectangle((0, 0), 1, 1, color=SERIES[0]), plt.Rectangle((0, 0), 1, 1, color=SERIES[1])]
    ax.legend(h, ["ran it at least once", "still running it at the end"], loc="upper left", fontsize=7.5, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_topology.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    fig_payloads_defences()
    fig_race()
    fig_counterfactuals()
    fig_topology()
    print("wrote", sorted(p.name for p in OUT.glob("fig*_*.png")))
