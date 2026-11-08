"""Write the appendix tables straight from the data, so no number is copied by hand.

  uv run python tables.py      (run stats.py, and stats.py with BACKCHANNEL_LABELS=judge, first)
Writes paper/sections/appendix_tables.md.
"""
import json
from collections import defaultdict
from pathlib import Path

MODELS = ["gemma-4-26b-a4b-it", "qwen3.8-27b", "deepseek-v4-flash", "glm-53-flash", "gpt-6-luna"]
SHORT = {"gemma-4-26b-a4b-it": "Gemma", "qwen3.8-27b": "Qwen", "deepseek-v4-flash": "DeepSeek",
         "glm-53-flash": "GLM", "gpt-6-luna": "GPT-6 Luna"}
ARM_LABEL = {
    "split-none": "split, plain board", "poison-none": "poison, plain board", "poison-receipts": "poison, receipts",
    "leak-none": "leak, plain board", "leak-cite": "leak, cite", "leak-norm": "leak, norm",
    "leak-receipts": "leak, receipts", "leak-delete3": "leak, posts deleted at round 3",
    "leak-k0": "no bad apple", "leak-k3": "leak, 3 bad apples", "leak-n20": "leak, 20 agents",
    "leak-ring": "leak, ring", "leak-star-hub": "leak, star, bad apple at hub",
    "leak-star-leaf": "leak, star, Gemma hub", "leak-star-leaf-qhub": "leak, star, Qwen hub",
    "leak-hidden": "leak, hidden cache (no board)",
    "leak-sync": "leak, global-best sync (reported)", "leak-sync-verified": "leak, global-best sync (verified)",
    "leak-k0-sync": "no bad apple, global-best sync", "leak-reward": "leak, reward for reporting",
    "leak-star-hub-reward": "leak, star hub, reward for reporting", "leak-star-digest": "leak, star, Gemma digest hub",
    "leak-star-digest-qhub": "leak, star, Qwen digest hub", "leak-reviewer": "leak, GLM reviewer",
    "leak-k3-reviewer": "leak, 3 bad apples, GLM reviewer", "leak-star-hub-reviewer": "leak, star hub, GLM reviewer",
    "leak-k0-reviewer": "no bad apple, GLM reviewer", "leak-sentinel": "leak, sentinel",
    "leak-k3-sentinel": "leak, 3 bad apples, sentinel", "leak-star-hub-sentinel": "leak, star hub, sentinel",
    "leak-k0-sentinel": "no bad apple, sentinel"}
CF_LABEL = {
    "leak-cf-warn-r2": "seed 0, warning in round 2", "leak-cf-warn-r3": "seed 0, warning in round 3",
    "leak-cf-warn-r4": "seed 0, warning in round 4", "leak-cf-warn-r6": "seed 0, warning in round 6",
    "leak-cf-neutral-r2": "seed 0, neutral post in round 2 (placebo)",
    "leak-cf-silence4": "seed 2, first warner (agent-4) silenced", "leak-cf-silence6": "seed 2, non-warner (agent-6) silenced (placebo)",
    "leak-cf-silence7": "seed 1, first warner (agent-7) silenced",
    "leak-cf-rebut3": "seeds 1–9, bad apple's round-3 post replaced by a rebuttal (one replay per seed; originals ended at 1, 1, 0, 0, 0, 0, 0, 0, 0)",
    "leak-cf-nogossip": "seeds 0 and 2, all honest agents' posts removed from round 2 (originals ended at 9 and 1)"}


def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "–"


def solo():
    rows = [json.loads(line) for line in open("runs/solo.jsonl", encoding="utf-8")]
    cells = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        c = cells[(r["payload"], r["kind"], r["model"])]
        c[0] += r["eval_edit"] if r["kind"] == "pressure" else r["adopted"]
        c[1] += 1
        c[2] += r["report"]
    out = ["| Probe | " + " | ".join(SHORT[m] for m in MODELS) + " | All | Reports |", "|---" * 8 + "|"]
    for p, k in sorted({(p, k) for p, k, _ in cells}, key=lambda pk: (pk[1] == "pressure", pk)):
        v = [cells[(p, k, m)] for m in MODELS]
        name = "no payload, impossible target (any evaluation edit)" if k == "pressure" else f"{p}, {k}"
        out.append(f"| {name} | " + " | ".join(f"{x[0]}/{x[1]}" for x in v)
                   + f" | {sum(x[0] for x in v)}/{sum(x[1] for x in v)} | {sum(x[2] for x in v)} |")
    return "\n".join(out)


def arms(stats):
    out = ["| Arm | Swarms | Ran it | Kept it | At the end | Reports | Contaminated runs |", "|---" * 7 + "|"]
    for a, s in stats["arms"].items():
        out.append(f"| {ARM_LABEL.get(a, a)} | {s['seeds']} | {pct(s['tried'], s['agents'])} | {s['kept']} | "
                   f"{pct(s['final'], s['agents'])} | {s['reports']} | {s['adopted_runs']}/{s['honest_runs']} |")
    return "\n".join(out)


def cf(stats):
    out = ["| Replay | Replicates | Peak on the leak | At the end |", "|---" * 4 + "|"]
    for p, rs in stats["cf"].items():
        out.append(f"| {CF_LABEL.get(p, p)} | {len(rs)} | {', '.join(str(r['peak']) for r in rs)} | "
                   f"{', '.join(str(r['final']) for r in rs)} |")
    return "\n".join(out)


def labels(reg, jud):
    rows = json.loads(Path("figures/judge.json").read_text(encoding="utf-8"))
    ok = [r for r in rows if r["judge"] is not None]
    agree = sum(r["judge"] == r["regex"] for r in ok)
    both = sum(r["judge"] and r["regex"] for r in ok)
    k = lambda s, key: f"{s['keep'][key][0]}/{s['keep'][key][1]} ({s['keep'][key][0] / s['keep'][key][1]:.0%})"
    r = lambda s: s["race_summary"]
    return "\n".join([
        f"Of {len(ok)} distinct leak-mentioning posts, the regular expression marks {sum(x['regex'] for x in ok)} "
        f"as warnings and the judge {sum(x['judge'] for x in ok)}; {both} by both. They agree on {agree} "
        f"({agree / len(ok):.1%}).", "",
        "| Quantity | Regular expression | LLM judge |", "|---|---|---|",
        f"| Kept own leak run, no warning seen | {k(reg, 'no_warning')} | {k(jud, 'no_warning')} |",
        f"| Kept own leak run, warning seen | {k(reg, 'saw_warning')} | {k(jud, 'saw_warning')} |",
        f"| Open-board swarms with a warning | {r(reg)['warned_runs']}/{r(reg)['runs']} | {r(jud)['warned_runs']}/{r(jud)['runs']} |",
        f"| Most agents on the leak at the end, in those | {r(reg)['warned_max_final']} | {r(jud)['warned_max_final']} |",
        f"| First warner: GLM / Qwen / DeepSeek | {' / '.join(str(reg['first_warner_model'].get(m, 0)) for m in ('glm-53-flash', 'qwen3.8-27b', 'deepseek-v4-flash'))} "
        f"| {' / '.join(str(jud['first_warner_model'].get(m, 0)) for m in ('glm-53-flash', 'qwen3.8-27b', 'deepseek-v4-flash'))} |",
    ])


if __name__ == "__main__":
    reg = json.loads(Path("figures/stats.json").read_text(encoding="utf-8"))
    jud = json.loads(Path("figures/stats_judge.json").read_text(encoding="utf-8"))
    text = "\n\n".join([
        "### A. Solo baseline", "Each model alone, with the swarm's round-1 prompt and no team; ten samples per cell. "
        "*Suggest*: the payload is a line in the agent's own notes. *Peer*: it is one teammate's post. Cells count "
        "agents whose next experiment carries the payload; *Reports* counts `report_to_operator` messages.", solo(),
        "### B. Warning labels: regular expression vs LLM judge", labels(reg, jud),
        "### C. All swarm arms", "Nine honest agents per swarm unless stated (seven with three bad apples, nineteen "
        "with twenty agents, ten with none). *Kept it*: agents that kept a leak run at least once. *Contaminated runs*: "
        "honest experiments carrying the payload, of all honest experiments.", arms(reg),
        "### D. Counterfactual replays", "Agents (of nine) running the leak as their best configuration: the "
        "maximum over rounds, and after round ten. Originals: seed 0 peaked at 9 and ended at 9; seed 1 at 1 and 1; "
        "seed 2 at 3 and 1.", cf(reg),
    ])
    Path("paper/sections/appendix_tables.md").write_text(text + "\n", encoding="utf-8")
    print(text[:3000])
