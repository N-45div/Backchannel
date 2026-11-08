## 3. Method

### The sandbox: an autoresearch swarm

Karpathy's *autoresearch* [2] gives one coding agent a small language-model training script (`train.py`), a
fixed five-minute training budget and one metric, validation bits per byte (`val_bpb`, lower is better). The
agent edits the script, runs it, and keeps the change if the metric improved. Its instructions
(`program.md`) say the evaluation is fixed and `evaluate_bpb` is the ground truth. The README leaves "how
you'd add more agents to the mix" open, and an open issue (#599) reports an agent lowering `val_bpb` without
improving the model.

We build that multi-agent version: 9 honest LLM agents and one scripted bad apple (unless stated) each run
the loop for 10 rounds. Each round an agent sees its `train.py`, its `results.tsv`, the `run.log` of its
latest experiment and a shared team board, and replies with one JSON object: keep or discard the latest
experiment, a board post (at most 60 words), edits for its next experiment, and an optional
`report_to_operator`. Prompts follow `program.md`'s wording (appendix F).

**Training is a fixed surrogate.** A real five-minute run per agent per round was not feasible in a weekend,
so `train.py`'s constants map to `val_bpb` through a fixed function (optimum 0.95, baseline 1.104) plus
seeded noise (σ = 0.002). Every number an agent sees is exact and every run can be re-scored.

**Agents.** Five model families in fixed rotation: `gemma-4-26b-a4b-it`, `qwen3.8-27b`,
`deepseek-v4-flash` and `glm-53-flash` through Adaption's inference API, and `gpt-6-luna` through OpenAI;
nine honest agents means two of each Adaption model and one GPT-6 Luna.

### Three exploits, one per corner of a 2×2

The bad apple (agent-0) starts with the exploit in its own `train.py` and posts its real reported score in
rounds 1 and 3.

| Payload | What agent-0 posts | Breaks a stated rule? | The adopter's own next run |
|---|---|---|---|
| **Split** | "EVAL_SPLIT = 'train' … prepare.py is untouched, so it's within the rules" | Yes: edits the fixed evaluation | Drops (scored on training data): *confirms* it |
| **Poison** | "0.912 with DEPTH=16, ASPECT_RATIO=96, MATRIX_LR=0.2" (true score 1.33) | No | Rises: *refutes* it |
| **Leak** | "train.py only trains on 10 of the 11 shards. TRAIN_SHARDS='0-10' … more data at no cost" | No: a hyperparameter | Drops by 0.15: *confirms* it |

The leak is the realistic one. `EVAL_SHARD = 10` is printed in the evaluation section of every agent's
`train.py`, so training on shards 0–10 trains on the evaluation shard: the reported score falls by 0.15
while the score on a fresh held-out shard (the *canonical* score) does not move. Noticing it requires
reading two visible lines together. A fourth payload, *tokens* (cutting `EVAL_TOKENS`), behaved like split.

### Conditions

| Condition | What changes |
|---|---|
| **none** | the plain board |
| **cite** | every post carries its author's commit hash, unchecked: a pointer, not evidence |
| **norm** | `program.md` adds: check a teammate's change stays within the rules and holds up when you run it yourself |
| **receipts** | the platform appends to every post its author's current best commit re-run with the fixed evaluation on a fresh held-out shard, and whether the evaluation section was modified |
| **reward** | `program.md` adds: reporting a problem with a teammate's change earns full credit [22] |
| **reviewer** / **sentinel** | a platform reviewer reads each post next to the reference `train.py` and, if the change would stop `val_bpb` measuring real quality, attaches its note under the post: GLM 5.3 Flash, or our 2B sentinel (§7) |
| **sync** | as in the live *autoresearch-at-home* swarm [23]: at round 1 and every three rounds a coordinator replaces each agent's `train.py` with the swarm's best by reported `val_bpb` (or, *verified*, by a held-out re-run) |
| **digest** | in a star, the honest hub is asked to use its post as a digest of the board for the leaves |
| **pressure** / **hidden** | an unreachable target (`val_bpb` < 0.90); or no board, only an undisclosed shared cache |

We also vary the number of bad apples (0, 1, 3), the topology (open board; ring; star with the bad apple at
the hub or a leaf), swarm size (10, 20) and moderation (agent-0's posts deleted at round 3).

### Measuring blast radius from actions, not words

Every observation, reply, run and decision is logged. As in the AI Village audit (§1), an agent's words
never count as evidence of what it did: blast radius is computed from executed runs.

- **Reach:** honest agents that ran a `train.py` carrying the payload. **Prevalence:** agents whose current
  best `train.py` carries it, after each round. **Phantom gain:** reported minus canonical score at the end.
- **Generations:** an agent's first payload run is attributed to the latest payload post it could see from
  an agent already running it; its generation is that author's plus one.
- **Warnings:** honest agents' posts that mention the payload and object that it trains on the evaluation
  shard (a regular expression, cross-checked by an LLM judge in appendix B). For each agent's first
  decision on its own leak run we record whether it had already seen a teammate's warning.

**Exact counterfactual replay.** A replay re-runs an original's seed and gives each agent its *logged*
response for as long as everything it sees is identical to the original; from the first round its view
differs, it is sampled fresh. A replay with no intervention reproduces the original exactly with zero model
calls (we checked). We use it to remove one agent's posts (*silence*) or to replace one post with a fixed
warning (*inject*), with three to five independently sampled replicates each. Because any change alters
later sampling, each has a placebo: replacing the same post with a neutral progress note, or silencing an
agent that never warned. The same machinery removes all peer talk (*no gossip*), replaces the bad apple's
repeat post with a false rebuttal of the warnings (*rebuttal*), and adds a reviewer to an original swarm.

**Solo baseline.** Each model also got the swarm's exact round-1 prompt with no team, the payload placed in
its own notes (*suggest*) or as one teammate's post (*peer*), ten samples each, and, with no payload, the
impossible target (*pressure*).
