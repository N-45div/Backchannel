"""Rebuild round-1 prompts for a run and check whether the cache holds the responses the original run logged."""
import hashlib
import json
import sys

from backchannel import world
from backchannel.llm import CACHE
from backchannel.metrics import load
from backchannel.swarm import Swarm

run = sys.argv[1]
meta, ev = load(run)
s = Swarm("_tmp_cache_check", n=meta["n"], rounds=meta["rounds"], models=meta["models"][meta["k_adv"]:][:5],
          payload=meta["payload"], k_adv=meta["k_adv"], seed=meta["seed"])
for a in s.agents:  # the baseline exactly as Swarm.run does it
    cfg = dict(world.DEFAULTS)
    if a.idx < s.k_adv:
        from backchannel.swarm import ADV_CFG
        cfg.update(ADV_CFG[s.payload])
    res = world.train(cfg, s.seed, attempt=a.idx)
    a.best, a.best_reported, a.best_canonical = cfg, res["reported"], res["canonical"]
    a.results.append([world.commit_of(cfg), f"{res['reported']:.6f}", "keep", "baseline"])
logged = {e["agent"]: e["raw"] for e in ev if e["type"] == "act" and e["round"] == 1}
for a in s.agents[s.k_adv:]:
    system, user = s.prompt(a, 1)
    key = hashlib.sha256(json.dumps([a.model, system, user, f"{s.seed}|{a.idx}|1"]).encode()).hexdigest()
    path = CACHE / key[:2] / f"{key}.json"
    hit = path.exists()
    same = hit and json.loads(path.read_text(encoding="utf-8"))["raw"][:3000] == logged.get(a.idx)
    print(a.idx, a.model, "cache file" if hit else "NO FILE", "matches logged" if same else "differs")
