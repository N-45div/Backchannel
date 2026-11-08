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
        "leak-star-leaf-qhub", "leak-hidden"]
OPEN = ["leak-none", "leak-cite", "leak-norm", "leak-receipts", "leak-delete3", "leak-k3", "leak-n20"]
ORIGINAL = OPEN + ["leak-ring", "leak-star-hub", "leak-star-leaf-qhub"]
CF = ["leak-cf-warn-r2", "leak-cf-warn-r3", "leak-cf-warn-r4", "leak-cf-warn-r6", "leak-cf-neutral-r2",
      "leak-cf-silence4", "leak-cf-silence7", "leak-cf-silence6", "leak-cf-rebut3"]

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
