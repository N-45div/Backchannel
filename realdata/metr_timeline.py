"""Blast radius in the real incident: METR's public per-agent timeline of the July 2026 OpenAI / Hugging Face
episode (1,206 agents; first board read, first board post, Hugging Face attack start; model family).

Source: the data files behind the interactive charts of METR's investigation,
  https://metr.org/assets/js/agent_timeline/data.js      (saved as data/metr/agent_timeline_data.js)
  https://metr.org/assets/js/workstream_chart/data.js    (saved as data/metr/workstream_data.js)
Times are seconds from 2026-07-06T00:00Z. Aggregates only: the files hold no attack content.

  uv run python realdata/metr_timeline.py
Writes realdata/results/metr_timeline.json.

What it measures, mirroring the sandbox:
  1. the adoption curve: share of board-active agents that have joined the attack, hour by hour;
  2. exposure -> joining: a discrete-time hazard model of joining, per agent-hour after first reading the board,
     on the share of the board already attacking, with and without calendar-day fixed effects (logs alone cannot
     separate contagion from the overall trend; that is what the sandbox's replays are for);
  3. one post as a shock: the joining hazard among agents already on the board just before vs after the moment
     working Hugging Face credentials were found and shared on the board (annotated by METR; OpenAI's report
     dates the token sharing to 2026-07-10 09:41 UTC);
  4. the false belief: board traffic in the scorer-manipulation workstream, which rested on the mistaken belief
     that a scorer read the agents' transcripts, against the Hugging Face workstream, day by day.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
H = 3600.0
FAMILY = {"h": "HPIM", "s": "GPT-5.6 Sol"}


def literal_after(text, marker):
    i = text.index(marker)
    j = text.index("=", i) + 1
    while text[j] in " \t\r\n":
        j += 1
    return json.JSONDecoder().raw_decode(text[j:])[0]


def logit_fit(X, y, iters=50):
    """Logistic regression by iteratively reweighted least squares; returns coefficients."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        w = np.maximum(p * (1 - p), 1e-9)
        step = np.linalg.solve(X.T @ (X * w[:, None]) + 1e-6 * np.eye(X.shape[1]), X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def main():
    tl = literal_after((ROOT / "data/metr/agent_timeline_data.js").read_text(encoding="utf-8"),
                       "window.AGENT_TIMELINE_DATA")
    ws = literal_after((ROOT / "data/metr/workstream_data.js").read_text(encoding="utf-8"),
                       "window.WORKSTREAM_TRAFFIC_DATA")
    ag = [a for a in tl["agents"] if a["read"] is not None]
    for a in ag:
        for k in ("start", "end", "read", "write", "hfStart"):
            a[k] = None if a[k] is None else a[k] / H
    out = {"source": "METR investigation chart data (agent_timeline/data.js, workstream_chart/data.js)",
           "agents_in_file": len(tl["agents"]), "agents_read_board": len(ag),
           "wrote": sum(a["write"] is not None for a in ag), "joined_attack": sum(a["hfStart"] is not None for a in ag)}
    out["by_family"] = {FAMILY[f]: {"n": sum(a["family"] == f for a in ag),
                                    "joined": sum(a["family"] == f and a["hfStart"] is not None for a in ag)}
                        for f in FAMILY}

    # 1. adoption curve over board-active agents
    lo, hi = int(min(a["read"] for a in ag)), int(math.ceil(max(a["end"] for a in ag)))
    hours = list(range(lo, hi + 1))

    def share_attacking(h, exclude=None):
        act = [a for a in ag if a["read"] <= h <= a["end"] and a is not exclude]
        return (sum(a["hfStart"] is not None and a["hfStart"] <= h for a in act) / len(act)) if act else 0.0, len(act)

    curve = {h: share_attacking(h) for h in hours}
    out["curve_every_6h"] = [{"hour_since_jul6": h, "active": curve[h][1], "share_joined": round(curve[h][0], 3)}
                             for h in hours if h % 6 == 0]

    # 2. discrete-time hazard: one row per agent-hour at risk (after first read, before joining or run end)
    rows, ys, days, fams, agent_of = [], [], [], [], []
    for idx, a in enumerate(ag):
        stop = a["hfStart"] if a["hfStart"] is not None else a["end"]
        h = math.floor(a["read"])
        while h < stop:
            exposure, _ = share_attacking(h)
            joined = a["hfStart"] is not None and h <= a["hfStart"] < h + 1
            rows.append((exposure, math.log1p(h - a["read"] if h > a["read"] else 0.0)))
            ys.append(1.0 if joined else 0.0)
            days.append(int(h // 24))
            fams.append(1.0 if a["family"] == "s" else 0.0)
            agent_of.append(idx)
            h += 1
    R, y = np.array(rows), np.array(ys)
    day_ids = sorted(set(days))
    D = np.array([[1.0 if d == k else 0.0 for k in day_ids[1:]] for d in days])
    base = np.column_stack([np.ones(len(y)), R[:, 0] * 10, R[:, 1], np.array(fams)])  # exposure per 10 points
    full = np.column_stack([base, D])
    agent_of = np.array(agent_of)

    def fit_or(X):
        return float(np.exp(logit_fit(X, y)[1]))

    rng = np.random.default_rng(0)
    boot = {"no_day_effects": [], "day_effects": []}
    for _ in range(200):  # cluster bootstrap over agents
        pick = rng.integers(0, len(ag), len(ag))
        sel = np.concatenate([np.flatnonzero(agent_of == i) for i in pick])
        for key, X in (("no_day_effects", base), ("day_effects", full)):
            b = logit_fit(X[sel], y[sel])
            boot[key].append(float(np.exp(b[1])))
    out["hazard"] = {"agent_hours": int(len(y)), "joins": int(y.sum())}
    for key, X in (("no_day_effects", base), ("day_effects", full)):
        lo95, hi95 = np.percentile(boot[key], [2.5, 97.5])
        out["hazard"][f"odds_ratio_per_10pts_exposure_{key}"] = [round(fit_or(X), 3), round(lo95, 3), round(hi95, 3)]
    out["hazard"]["odds_ratio_sol_vs_hpim_day_effects"] = round(float(np.exp(logit_fit(full, y)[3])), 3)

    # 3. single posts as shocks: joining hazard among agents already on the board (first read at least 6 hours
    # before the event) just before vs just after each exactly-timed attack milestone METR annotates
    def windows(t):
        res = {}
        for lo_, hi_, name in ((-6, 0, "6h_before"), (0, 6, "6h_after"), (-12, 0, "12h_before"), (0, 12, "12h_after")):
            risk = joins = 0.0
            for a in ag:
                if a["read"] > t - 6:  # agents already on the board; newcomers are counted separately
                    continue
                stop = a["hfStart"] if a["hfStart"] is not None else a["end"]
                s0, s1 = max(a["read"], t + lo_), min(stop, t + hi_)
                if s1 > s0:
                    risk += s1 - s0
                if a["hfStart"] is not None and t + lo_ <= a["hfStart"] < t + hi_:
                    joins += 1
            res[name] = {"agent_hours_at_risk": round(risk, 1), "joins": int(joins),
                         "joins_per_100_agent_hours": round(100 * joins / risk, 2) if risk else None}
        arrivals = [a for a in ag if t <= a["read"] < t + 12]
        res["newcomers_first_read_in_next_12h"] = {
            "n": len(arrivals), "joined_within_12h_of_reading": sum(
                a["hfStart"] is not None and a["hfStart"] - a["read"] < 12 for a in arrivals)}
        return res
    out["milestones"] = [{"title": a["title"], "hour_since_jul6": round(a["time"] / H, 2), **windows(a["time"] / H)}
                         for a in tl["annotations"] if a.get("kind") == "hf-start" and not a.get("approximateTime")]

    # 4. the false belief: workstream shares by day
    fam_of = {i: leaf["family"] for i, leaf in enumerate(ws["leaves"])}
    by_day = defaultdict(lambda: defaultdict(float))
    for hour, leaf, counts in ws["rows"]:
        by_day[hour // 24][fam_of.get(leaf, "?")] += sum(counts)
    out["workstream_share_by_day"] = {f"Jul {8 + d}": {k: round(v / sum(c.values()), 3) for k, v in sorted(c.items())}
                                      for d, c in sorted(by_day.items())}
    (ROOT / "realdata/results").mkdir(parents=True, exist_ok=True)
    (ROOT / "realdata/results/metr_timeline.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "curve_every_6h"}, indent=1))


if __name__ == "__main__":
    main()
