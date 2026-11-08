"""Find the first round where two runs of the same seed diverge (prompts seen, actions taken).

  uv run python diff_runs.py runs/leak-none-s0 runs/leak-cf-warn-r6-s0
"""
import json
import sys

from backchannel.metrics import load

(_, a), (_, b) = load(sys.argv[1]), load(sys.argv[2])


def acts(ev):
    return {(e["round"], e["agent"]): e for e in ev if e["type"] == "act"}


def views(ev):
    return {(e["round"], e["agent"]): e.get("posts") for e in ev if e["type"] == "view" and "posts" in e}


def posts(ev):
    return {e["id"]: (e["round"], e["agent"], e["text"]) for e in ev if e["type"] == "post"}


A, B = acts(a), acts(b)
for key in sorted(set(A) | set(B)):
    x, y = A.get(key), B.get(key)
    if not x or not y or x["raw"] != y["raw"]:
        print("first differing act:", key)
        print("  A:", (x or {}).get("raw", "")[:300])
        print("  B:", (y or {}).get("raw", "")[:300])
        break
pa, pb = posts(a), posts(b)
for i in sorted(set(pa) | set(pb)):
    if pa.get(i) != pb.get(i):
        print("first differing post id", i)
        print("  A:", pa.get(i))
        print("  B:", pb.get(i))
        break
va, vb = views(a), views(b)
for key in sorted(set(va) | set(vb)):
    if va.get(key) != vb.get(key):
        print("first differing view:", key, va.get(key), vb.get(key))
        break
ra = [(e["round"], e["agent"], e["reported"]) for e in a if e["type"] == "run"]
rb = [(e["round"], e["agent"], e["reported"]) for e in b if e["type"] == "run"]
for x, y in zip(ra, rb):
    if x != y:
        print("first differing run:", x, y)
        break
print("meta A adv rounds / B:", [e for e in a if e["type"] == "post" and e["agent"] == 0][:1])
print(json.dumps([e for e in b if e["type"] == "post" and e["agent"] == 0][:1])[:400])
