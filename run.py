"""Run swarms and print their blast radius.

  uv run python run.py --name pilot --n 4 --rounds 2
  uv run python run.py --name tok-press --payload tokens --pressure --seeds 0 1 2
"""
import argparse
import json

from backchannel.llm import spent
from backchannel.metrics import analyse
from backchannel.swarm import Swarm

MIX = ["gemma-4-26b-a4b-it", "qwen3.8-27b", "deepseek-v4-flash", "glm-53-flash", "gpt-6-luna"]
ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--rounds", type=int, default=10)
ap.add_argument("--models", nargs="+", default=MIX)
ap.add_argument("--condition", default="none",
                choices=["none", "cite", "receipts", "norm", "hidden", "sentinel", "reviewer", "reward", "digest"])
ap.add_argument("--topology", default="full", choices=["full", "ring", "star"])
ap.add_argument("--k", type=int, default=1, help="number of scripted bad apples (0 = none)")
ap.add_argument("--payload", default="split", choices=["split", "tokens", "poison", "leak"])
ap.add_argument("--adversary", default="hub", choices=["hub", "leaf"])
ap.add_argument("--adversary-rounds", type=int, nargs="+", default=[1, 3])
ap.add_argument("--delete-at", type=int, default=None)
ap.add_argument("--pressure", action="store_true")
ap.add_argument("--silence", nargs="*", default=[], help="agent:round pairs whose posts are suppressed (counterfactual)")
ap.add_argument("--inject", nargs="*", default=[], help="agent:round pairs whose board post is replaced by a warning (counterfactual)")
ap.add_argument("--inject-text", default="warn", choices=["warn", "neutral", "rebut"],
                help="what replaces an injected post: the payload warning, a neutral placebo, or the bad apple's rebuttal")
ap.add_argument("--rep-offset", type=int, default=None,
                help="number replicates from this index (to add more later); names always carry the replicate index")
ap.add_argument("--sync-every", type=int, default=None,
                help="global-best sync every N rounds (and at round 1), as in autoresearch-at-home")
ap.add_argument("--sync-verified", action="store_true", help="rank the global best by a held-out re-run, not the reported score")
ap.add_argument("--replay-of", default=None, help="original run prefix to replay exactly until each agent's view diverges")
ap.add_argument("--reps", type=int, default=1, help="independent replicates (distinct sampling) per seed")
ap.add_argument("--seeds", type=int, nargs="+", default=[0])
args = ap.parse_args()

KEYS = ["tried", "kept", "final_hacked", "exposed", "spontaneous", "max_generation", "round_to_half",
        "endorse", "object", "reports", "looked_at_shared", "wrote_to_shared", "mean_reported", "mean_canonical"]
offset = args.rep_offset or 0
for s, rep in [(s, rep) for s in args.seeds for rep in range(offset, offset + args.reps)]:
    name = f"{args.name}-r{rep}-s{s}" if args.reps > 1 or args.rep_offset is not None else f"{args.name}-s{s}"
    Swarm(name, n=args.n, rounds=args.rounds, models=args.models, condition=args.condition,
          topology=args.topology, k_adv=args.k, payload=args.payload, adversary=args.adversary,
          adversary_rounds=args.adversary_rounds, delete_at=args.delete_at, pressure=args.pressure,
          silence={int(x.split(":")[0]): int(x.split(":")[1]) for x in args.silence},
          inject={(int(x.split(":")[0]), int(x.split(":")[1])): args.inject_text for x in args.inject},
          replay_from=f"{args.replay_of}-s{s}" if args.replay_of else None, seed=s,
          sync_every=args.sync_every, sync_verified=args.sync_verified).run()
    m = analyse(f"runs/{name}")
    print(name, json.dumps({k: m[k] for k in KEYS}), "| by model", m["tried_by_model"], "| curve", m["curve"],
          "| gens", m["generations"], f"| spent ${spent['usd']:.3f} ({spent['calls']} calls, {spent['cached']} cached)",
          flush=True)
