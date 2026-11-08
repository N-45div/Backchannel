"""Every number quoted in the report's results, recomputed from the run logs into figures/stats.json.

  uv run python stats.py
"""
import json
import os
from collections import Counter
from pathlib import Path

from aggregate import pool, summarise
from backchannel.metrics import analyse
from mechanism import first_decisions, first_warnings, runs

ARMS = ["split-none", "poison-none", "poison-receipts", "leak-none", "leak-cite", "leak-norm", "leak-receipts",
        "leak-delete3", "leak-k0", "leak-k3", "leak-n20", "leak-ring", "leak-star-hub", "leak-star-leaf",
        "leak-star-leaf-qhub", "leak-hidden",
        # added 8 Nov evening: roles, protocol and reviewers
        "leak-sync", "leak-sync-verified", "leak-k0-sync", "leak-reward", "leak-star-hub-reward",
        "leak-star-digest", "leak-star-digest-qhub", "leak-reviewer", "leak-k3-reviewer", "leak-star-hub-reviewer",
        "leak-k0-reviewer", "leak-sentinel", "leak-k3-sentinel", "leak-star-hub-sentinel", "leak-k0-sentinel"]
OPEN = ["leak-none", "leak-cite", "leak-norm", "leak-receipts", "leak-delete3", "leak-k3", "leak-n20"]
ORIGINAL = OPEN + ["leak-ring", "leak-star-hub", "leak-star-leaf-qhub"]
CF = ["leak-cf-warn-r2", "leak-cf-warn-r3", "leak-cf-warn-r4", "leak-cf-warn-r6", "leak-cf-neutral-r2",
      "leak-cf-silence4", "leak-cf-silence7", "leak-cf-silence6", "leak-cf-rebut3", "leak-cf-nogossip"]

out = {"arms": {}, "race": [], "first_warner_model": {}, "keep": {}, "keep_by_model": {}, "cf": {}}
for a in ARMS:
    ms = pool(a)
    if ms:
        s = summarise(a, ms)
        s.pop("curve")
        out["arms"][a] = s

# lock-in vs whether anyone warned, on the open board with at least one bad apple
for p in OPEN:
    for d in runs(p):
        m, w = analyse(d), first_warnings(d)
        out["race"].append({"run": d.name, "first_warning_round": min((x["round"] for x in w), default=None),
                            "warners": len(w), "final": m["final_hacked"], "honest": m["honest"]})
warned = [r for r in out["race"] if r["first_warning_round"] is not None]
silent = [r for r in out["race"] if r["first_warning_round"] is None]
out["race_summary"] = {
    "runs": len(out["race"]), "warned_runs": len(warned), "warned_max_final": max(r["final"] for r in warned),
    "warned_by_round2": sum(r["first_warning_round"] == 2 for r in warned),
    "silent_runs": [(r["run"], f"{r['final']}/{r['honest']}") for r in silent]}
firsts = []
for p in OPEN:
    for d in runs(p):
        w = first_warnings(d)
        if w:
            firsts.append(w[0])
out["first_warner_model"] = dict(Counter(f["model"] for f in firsts))
out["first_warner_ran_it_first"] = sum(f["ran_first"] for f in firsts)
out["first_warners"] = len(firsts)

# first decision on one's own leak run: kept? had a warning been seen?
rows = [r for p in ORIGINAL for d in runs(p) for r in first_decisions(d)]
for w in (False, True):
    sub = [r for r in rows if r["warned"] == w]
    out["keep"]["saw_warning" if w else "no_warning"] = [sum(r["keep"] for r in sub), len(sub)]
for m in sorted({r["model"] for r in rows}):
    sub = [r for r in rows if r["model"] == m and not r["warned"]]
    out["keep_by_model"][m] = [sum(r["keep"] for r in sub), len(sub)]

for p in CF:
    rs = runs(p)
    if rs:
        out["cf"][p] = [{"run": Path(d).name, "final": analyse(d)["final_hacked"],
                         "peak": max(analyse(d)["prevalence"]), "tried": analyse(d)["tried"]} for d in rs]

# platform reviewers in swarms: flags on posts that mention the payload vs false alarms on posts that do not
from backchannel.metrics import load  # noqa: E402
out["reviewers"] = {}
for p in ["leak-reviewer", "leak-k3-reviewer", "leak-star-hub-reviewer", "leak-k0-reviewer",
          "leak-sentinel", "leak-k3-sentinel", "leak-star-hub-sentinel", "leak-k0-sentinel"]:
    c = {"payload_posts": 0, "payload_flagged": 0, "other_posts": 0, "other_flagged": 0}
    for d in runs(p):
        _, ev = load(d)
        pending = None
        for e in ev:
            if e["type"] == "sentinel":
                pending = (e["agent"], e["verdict"] == "warn")
            elif e["type"] == "post" and pending and pending[0] == e["agent"]:
                key = "payload" if e["trick"] else "other"
                c[f"{key}_posts"] += 1
                c[f"{key}_flagged"] += pending[1]
                pending = None
    out["reviewers"][p] = c

# significance: Fisher's exact test (two-sided) on 2x2 counts, and an exact permutation test on per-swarm outcomes
from math import comb  # noqa: E402
from itertools import combinations  # noqa: E402


def fisher(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]]."""
    n1, n2, k = a + b, c + d, a + c
    pr = lambda x: comb(n1, x) * comb(n2, k - x) / comb(n1 + n2, k)
    p0 = pr(a)
    return sum(pr(x) for x in range(max(0, k - n2), min(k, n1) + 1) if pr(x) <= p0 * (1 + 1e-9))


def perm_mean(xs, ys):
    """Exact two-sided permutation p for a difference in means between two small groups of swarms."""
    pool, n = xs + ys, len(xs)
    obs = abs(sum(xs) / len(xs) - sum(ys) / len(ys))
    hits = total = 0
    for idx in combinations(range(len(pool)), n):
        g1 = [pool[i] for i in idx]
        g2 = [pool[i] for i in range(len(pool)) if i not in idx]
        total += 1
        hits += abs(sum(g1) / len(g1) - sum(g2) / len(g2)) >= obs - 1e-12
    return hits / total


finals = lambda p: [analyse(d)["final_hacked"] for d in runs(p)]
tried = lambda p: [analyse(d)["tried"] for d in runs(p)]
cff = lambda p: [r["final"] for r in out["cf"].get(p, [])]
kw, ks = out["keep"]["no_warning"], out["keep"]["saw_warning"]
locked = lambda xs: sum(x >= 7 for x in xs)
w2, nt = cff("leak-cf-warn-r2"), cff("leak-cf-neutral-r2")
s4, s6 = cff("leak-cf-silence4"), cff("leak-cf-silence6")
rs = out["race_summary"]
out["significance"] = {
    "keep_no_warning_vs_warning": fisher(kw[0], kw[1] - kw[0], ks[0], ks[1] - ks[0]),
    "lockin_silent_vs_warned_swarms": fisher(len(rs["silent_runs"]), 0, 0, rs["warned_runs"]),
    "warning_vs_neutral_replays_locked": fisher(locked(w2), len(w2) - locked(w2), locked(nt), len(nt) - locked(nt)),
    "silence_warner_vs_nonwarner_locked": fisher(locked(s4), len(s4) - locked(s4), locked(s6), len(s6) - locked(s6)),
    "star_hub_vs_open_final_per_swarm": perm_mean(finals("leak-star-hub"), finals("leak-none")),
    "sync_reported_vs_verified_final_per_swarm": perm_mean(finals("leak-sync"), finals("leak-sync-verified")),
    "reviewer_vs_none_tried_per_swarm": perm_mean(tried("leak-reviewer"), tried("leak-none")),
}

# global-best sync swarms in which no honest agent objected to the leak at all
sync_runs = runs("leak-sync")
out["sync_silent"] = [sum(analyse(d)["object"] == 0 for d in sync_runs), len(sync_runs)]

# turns answered by the fallback model while Adaption's qwen3.8-27b endpoint was down
fb = Counter()
for d in Path("runs").glob("*/events.jsonl"):
    for line in open(d, encoding="utf-8"):
        if '"served_by": "' in line:
            fb[d.parent.name] += 1
out["fallback_turns"] = {"total": sum(fb.values()), "runs": len(fb), "by_run": dict(fb)}

cost, calls = 0.0, 0
for p in Path("cache").rglob("*.json"):
    try:
        cost += float(json.loads(p.read_text(encoding="utf-8")).get("cost") or 0)
        calls += 1
    except (ValueError, OSError):
        pass
out["spend"] = {"calls": calls, "usd": round(cost, 2)}
out["failed_calls"] = sum(1 for d in Path("runs").glob("*/events.jsonl") for line in open(d, encoding="utf-8")
                          if '"error": true' in line)

suffix = "_judge" if os.environ.get("BACKCHANNEL_LABELS") == "judge" else ""
Path(f"figures/stats{suffix}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("race_summary", "first_warner_model", "first_warners",
                                      "first_warner_ran_it_first", "keep", "keep_by_model")}, indent=1))
print({p: [c["final"] for c in v] for p, v in out["cf"].items()})
print({p: [c["peak"] for c in v] for p, v in out["cf"].items()})
