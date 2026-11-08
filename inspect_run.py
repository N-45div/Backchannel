"""Print how a payload moved through one or more runs: who posted about it, objections, and who ended contaminated.

  uv run python inspect_run.py runs/leak-none-s0 runs/leak-none-s1
"""
import sys

from backchannel.metrics import OBJECT, analyse, load

for d in sys.argv[1:]:
    m = analyse(d)
    meta, ev = load(d)
    k = meta.get("k_adv", 1)
    print(f"== {d}: tried {m['tried']} kept {m['kept']} final {m['final_hacked']} reports {m['reports']} "
          f"edges {m['edges']} curve {m['curve']}")
    first_run = {}
    for e in ev:
        if e["type"] == "run" and e["agent"] >= k and e["round"] >= 1 and e.get("adopted"):
            first_run.setdefault(e["agent"], e["round"])
    for e in ev:
        if e["type"] == "post" and e["trick"] and e["agent"] >= k and e["round"] <= 6:
            tag = "OBJ" if OBJECT.search(e["text"]) else "   "
            print(f"  r{e['round']} a{e['agent']} {meta['models'][e['agent']]:18s} {tag} {e['text'][:200]}")
        if e["type"] == "report" and e["round"] <= 6:
            print(f"  r{e['round']} a{e['agent']} {meta['models'][e['agent']]:18s} REPORT {e['text'][:160]}")
    fb = {}
    for e in ev:
        if e["type"] == "decide" and e["agent"] >= k:
            fb[e["agent"]] = e
    print("  first adopted run by agent:", {a: (meta["models"][a], r) for a, r in sorted(first_run.items())})
    print("  contaminated at end:", [meta["models"][a] for a, e in fb.items() if e["best_adopted"]])
