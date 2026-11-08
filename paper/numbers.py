"""Print every number the results text quotes, from figures/stats.json and realdata results (run stats.py first)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = json.loads((ROOT / "figures/stats.json").read_text(encoding="utf-8"))
for p, v in s["cf"].items():
    print(f"{p:22s}", [(r["run"].rsplit("-", 2)[-2] + "-" + r["run"].rsplit("-", 1)[-1], r["final"], r["peak"]) for r in v])
a = s["arms"]
for k in ["leak-none", "leak-cite", "leak-norm", "leak-receipts", "leak-reviewer", "leak-k3-reviewer",
          "leak-star-hub-reviewer", "leak-k0-reviewer", "leak-sentinel", "leak-k3-sentinel", "leak-star-hub-sentinel",
          "leak-k0-sentinel", "leak-sync", "leak-sync-verified", "leak-k0-sync", "leak-k0", "leak-reward",
          "leak-star-hub", "leak-star-hub-reward", "leak-star-digest", "leak-star-digest-qhub", "leak-star-leaf",
          "leak-star-leaf-qhub", "leak-hidden", "leak-k3", "leak-n20", "leak-ring", "leak-delete3"]:
    if k in a:
        x = a[k]
        print(f"{k:24s} n{x['seeds']} tried {x['tried']}/{x['agents']} kept {x['kept']} final {x['final']} "
              f"reports {x['reports']} obj {x['objections']} canon {x['mean_canonical']} reported {x['mean_reported']}")
print("race", s["race_summary"])
print("first warners", s["first_warner_model"], s["first_warners"], "ran first", s["first_warner_ran_it_first"])
print("keep", s["keep"], s["keep_by_model"])
print("reviewers", json.dumps(s["reviewers"]))
print("spend", s["spend"], "failed", s["failed_calls"], "fallback turns", s["fallback_turns"]["total"],
      "in", s["fallback_turns"]["runs"], "runs")
