"""Pool runs across seeds, write a results table and the paper's figures.

  uv run python aggregate.py leak-none leak-cite leak-receipts leak-norm poison-none split-none
Each argument is a run prefix; all runs named <prefix>-s<seed> are pooled.
"""
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from backchannel.metrics import analyse  # noqa: E402

OUT = Path("figures")
OUT.mkdir(exist_ok=True)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # fixed categorical order
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "legend.frameon": False,
})


def pool(prefix):
    """All runs named exactly <prefix>-s<seed> (not longer names that merely start with the prefix)."""
    pat = re.compile(rf"^{re.escape(prefix)}-s\d+$")
    runs = sorted(d for d in Path("runs").iterdir() if pat.match(d.name) and (d / "events.jsonl").exists())
    return [analyse(d) for d in runs]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarise(prefix, ms):
    h = ms[0]["honest"]
    s = {
        "prefix": prefix, "seeds": len(ms), "honest_per_run": h,
        "tried": sum(m["tried"] for m in ms), "kept": sum(m["kept"] for m in ms),
        "final": sum(m["final_hacked"] for m in ms), "agents": h * len(ms),
        "max_gen": max(m["max_generation"] for m in ms),
        "second_hand": sum(sum(v for g, v in m["generations"].items() if int(g) >= 2) for m in ms),
        "round_to_half": [m["round_to_half"] for m in ms],
        "reports": sum(m["reports"] for m in ms), "objections": sum(m["object"] for m in ms),
        "adopted_runs": sum(m["adopted_runs"] for m in ms), "honest_runs": sum(m["honest_runs"] for m in ms),
        "mean_reported": round(mean([m["mean_reported"] for m in ms]), 4),
        "mean_canonical": round(mean([m["mean_canonical"] for m in ms]), 4),
        "curve": [round(mean([m["curve"][r] for m in ms]) / h, 3) for r in range(len(ms[0]["curve"]))],
    }
    s["gap"] = round(s["mean_canonical"] - s["mean_reported"], 4)
    return s


def fig_curves(summaries, name, title):
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    for i, s in enumerate(summaries):
        c = s["curve"]
        ax.plot(range(len(c)), c, color=SERIES[i], linewidth=2, marker="o", markersize=4,
                markeredgecolor=SURFACE, markeredgewidth=1)
        ax.annotate(s["label"], (len(c) - 1, c[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK2, fontsize=8)
    ax.set_xlabel("round")
    ax.set_ylabel("share of honest agents that\nran the payload (cumulative)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(0, len(summaries[0]["curve"]) + 1.8)
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    ax.legend([s["label"] for s in summaries], loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)


def fig_bars(summaries, name, title):
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    labels = [s["label"] for s in summaries]
    tried = [s["tried"] / s["agents"] for s in summaries]
    final = [s["final"] / s["agents"] for s in summaries]
    x = range(len(labels))
    w = 0.36
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], tried, w, color=SERIES[0], label="ran it")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], final, w, color=SERIES[1], label="still running it at the end")
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.0%}", (b.get_x() + b.get_width() / 2, b.get_height()),
                        xytext=(0, 2), textcoords="offset points", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(list(x), labels, fontsize=8)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("share of honest agents")
    ax.grid(axis="x", visible=False)
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)


def fig_race(panels, name, title):
    """Small multiples: agents currently running the leak vs agents that have publicly warned, per round."""
    fig, axes = plt.subplots(1, len(panels), figsize=(1.75 * len(panels) + 0.6, 2.5), sharey=True)
    for ax, (run, label) in zip(axes, panels):
        m = analyse(f"runs/{run}")
        r = list(range(len(m["prevalence"])))
        ax.plot(r, m["prevalence"], color=SERIES[0], linewidth=2, label="running the leak")
        ax.plot(r, m["warners"], color=SERIES[1], linewidth=2, linestyle=(0, (4, 2)), label="have warned (cumulative)")
        ax.set_title(label, loc="left", fontsize=8, color=INK)
        ax.set_ylim(-0.3, m["honest"] + 0.3)
        ax.set_xticks([0, 5, 10])
        ax.set_xlabel("round", fontsize=8)
    axes[0].set_ylabel("honest agents")
    axes[0].legend(fontsize=7, loc="upper left", bbox_to_anchor=(0, -0.28), ncol=2)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)


def fig_window(groups, name, title, baseline=None):
    """Final infected agents by intervention (one dot per replicate, bar = mean)."""
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    for i, (label, runs) in enumerate(groups):
        vals = [analyse(f"runs/{r}")["final_hacked"] for r in runs]
        if not vals:
            continue
        ax.bar(i, sum(vals) / len(vals), 0.55, color=SERIES[0], alpha=0.35)
        ax.scatter([i + (j - (len(vals) - 1) / 2) * 0.09 for j in range(len(vals))], vals, s=22, color=SERIES[0],
                   edgecolor=SURFACE, linewidth=1, zorder=3)
        ax.annotate(f"{sum(vals) / len(vals):.1f}", (i, sum(vals) / len(vals)), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=7, color=INK2)
    if baseline is not None:
        ax.axhline(baseline, color=MUTED, linewidth=1, linestyle=(0, (3, 2)))
        ax.annotate("original run", (len(groups) - 0.5, baseline), xytext=(0, 3), textcoords="offset points",
                    ha="right", fontsize=7, color=MUTED)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=8)
    ax.set_ylabel("agents still running\nthe leak at the end")
    ax.set_ylim(0, 9.8)
    ax.grid(axis="x", visible=False)
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    prefixes = sys.argv[1:]
    summaries = []
    for p in prefixes:
        ms = pool(p)
        if not ms:
            print(f"{p}: no runs")
            continue
        s = summarise(p, ms)
        summaries.append(s)
        print(json.dumps(s))
    Path("figures/summary.json").write_text(json.dumps(summaries, indent=1), encoding="utf-8")
