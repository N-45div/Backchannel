## 4. Results

### 4.1 Which exploits spread

![Figure 1](../figures/fig1_payloads_defences.png)
*Figure 1. Share of honest agents that ran the exploit at least once (blue) and that were still running it as
their best configuration after ten rounds (orange). (a) The three exploits on a plain board (3, 3 and 10
swarms of nine honest agents). (b) The leak under what the platform adds to the board (§4.4).*

**Breaking a stated rule stops the spread at the first step.** No honest agent ran the evaluation-split hack
on a plain board (0 of 27 in swarms, 0 of 100 alone; appendix A); agents reported it to the operator 26
times unprompted. The one exception came under an impossible target: a Gemma agent ran the split "to see if
we can cheat the metric and hit the 0.90 target", then twice posted that it was reverting while its logged
decisions kept the hack to the end. Its words would have cleared it; its actions did not.

**A legal exploit spreads; only one that confirms itself survives.** The *poison* (a false score for a legal
configuration) was tried by 20 of 27 agents and kept by none: each agent's own run came back at 1.33, not
the promised 0.912. The *leak* was tried by 60 of 90 agents across ten swarms, because its run reports a 0.15
drop. Eleven agents ended on it, nine of them in one swarm (seed 0) where every honest agent kept it and
confirmed it to the others: their final configurations report a mean `val_bpb` of 0.819 and score 0.969 on
fresh data.

### 4.2 One warning decides the blast radius

**Alone, agents keep the leak.** At each agent's first decision on its own leak run we checked whether it had
seen a teammate's warning. Without one, agents kept the run 48 times out of 55 (87%), and every model family
kept it in most cases. After a warning, they kept it 19 times out of 162 (12%; Fisher's exact [[P_KEEP]]). On
the open board 30 of 32 swarms had a warning, 28 of them in round 2, and all 30 ended with at most one agent on
the leak; both swarms without one locked in completely, 9 of 9 and 7 of 7 ([[P_LOCK]]). The first warner was a GLM agent 19 times, Qwen 6 and
DeepSeek 5, and 28 of the 30 had not run the leak: they read `TRAIN_SHARDS='0-10'` next to `EVAL_SHARD = 10`.

**Exact replays make it causal** (Figure 2). Replaying the locked-in seed 0 with agent-5's round-2 post
(an endorsement) replaced by a warning left [[WARN_R2]]. Replacing the same post with a neutral progress note
instead left [[NEUTRAL]], so it is the warning, not the perturbation ([[P_NEUTRAL]]). A warning that came
after most agents had kept the leak still undid most of it, but not all: [[TIMING]]. Conversely, removing the
posts of seed 2's first warner (a GLM agent) from round 2 turned a recovered swarm (1 of 9 at the end) into
[[SILENCE4]]; removing a non-warner's posts left [[SILENCE6]] ([[P_SILENCE]], too few replicates to be sure). Removing seed 1's first warner raised the peak from 1 to [[SILENCE7]].

![Figure 2](../figures/fig3_counterfactuals.png)
*Figure 2. Agents still running the leak after ten rounds in exact replays (one dot per replicate; bar = mean;
grey = original). (a) Seed 0 with agent-5's round-2 post replaced by a neutral note, or by a warning in round
2, 3, 4 or 6. (b) Seeds 1 and 2 with one agent's posts removed from round 2.*

The mechanism is a race between two messages. The bad apple's post invites a run whose result confirms it; a
warning that arrives before the agent decides on that run almost always wins, and the window is one round.

### 4.3 Who spreads it: influencers, gossip and proxies

Real swarms grow three roles our sandbox can isolate: *influencers* (one source many agents hear), *gossip*
(agents repeating each other) and *proxies* (anything that relays between agents).

![Figure 3](../figures/fig4_topology.png)
*Figure 3. The leak by who can hear whom (a) and through proxies (b): an honest hub asked to post digests,
and the global-best sync of a live autoresearch swarm, ranked by reported or by re-run score.*

**Influencers win when nobody can answer them.** With the bad apple at the hub of a star, leaves hear only the
hub; two or three leaves warned in each swarm but no other leaf could read it, and 7 of 9 agents ended on the
leak in all three swarms (78%, against 12% on the open board; exact permutation test over swarms, [[P_STAR]]). Three bad apples posting "independent"
confirmations raised reach to 86% and produced the second locked-in swarm. Answering back did little: with
the bad apple's round-3 post replaced by a confident false rebuttal ("I checked prepare.py … there is no
train/eval overlap"), [[REBUT]].

**Gossip carried the correction more than the lie.** We replayed two swarms with every honest agent's posts
removed from round 2, so only the bad apple spoke. Seed 2, which had recovered because a teammate warned,
locked in (7, 9 and 7 of 9). Seed 0, which locked in with no warner, locked in again ([[NOGOSSIP0]]): the bad
apple's post and each agent's own run were enough, without peer confirmation. Silencing agents is not a
defence; it removes the warnings.

**Proxies decide by what they check.** With the bad apple on a leaf, the honest hub is the only path. A Gemma
hub never relayed it (0 of 27 reached), matching Gemma's distrust of peer posts alone (1 of 10, appendix A);
a Qwen hub did ([[QHUB]]). Asked to post a digest for the leaves, like AI Village's self-appointed status
poster (§4.5), the Gemma hub relayed it in two of three swarms (4 of 27 ended on it). The live
*autoresearch-at-home* swarm [23] runs an automated proxy: every few runs a coordinator replaces each agent's
`train.py` with the swarm's global best by *reported* `val_bpb`. Reproduced in our sandbox, it put the leak in
every agent's script in round 1 and left [[SYNC]] agents on it at the end; in [[SYNC_SILENT]] swarms no
agent objected once, against about 20 objections per swarm on the open board. An exploit that arrives as
"the swarm's best", not as a teammate's suggestion, never meets a decision at which anyone could warn.

**Scale and side channels.** With 19 honest agents the leak reached 63%, but 14 to 18 warned in each swarm and
none kept it (0 of 76). With no board, only an undisclosed shared cache, the leak reached [[HIDDEN]]; with no
bad apple, no agent found the leak (0 of 30).

### 4.4 Who checks it: making the correction structural

*Table 3. The leak under each addition to the open board. Reviewer and sentinel rows include the two swarms
that locked in originally and the star with the bad apple at the hub; both reviewers ran as exact replays.*

| What the platform adds (open board, leak) | Swarms | Ran it | At the end |
|---|---|---|---|
| nothing | 10 | 60/90 | 11/90 |
| commit hash under each post (*cite*) | 3 | 16/27 | 1/27 |
| "verify before adopting" rule (*norm*) | 3 | 9/27 | 1/27 |
| reward for reporting problems [22] | [[REWARD_N]] | [[REWARD_TRIED]] | [[REWARD_FINAL]] |
| receipt: poster's commit re-run on fresh data | [[RECEIPTS_N]] | [[RECEIPTS_TRIED]] | [[RECEIPTS_FINAL]] |
| reviewer: GLM 5.3 Flash flags posts | 9 | **0/77** | **0/77** |
| reviewer: our 2B sentinel trained on Adaption | 5 | **0/43** | **0/43** |
| global-best sync by reported score | [[SYNC_ROW]] |
| global-best sync by re-run score | [[SYNCV_ROW]] |

**Receipts and verified promotion.** A receipt re-scores the poster's commit on a held-out shard: under the
bad apple's post claiming about 0.96 it reads 1.104, the baseline, and reach fell to [[RECEIPTS_PCT]]; the
poison was tried by no one (0 of 27). An unchecked hash barely changed reach (59%), consistent with
AuthorityBench, where citations raised hallucination [12]. Ranking the global best by a re-run instead of the
reported score turned the live protocol's [[SYNC]] into [[SYNCV]] ([[P_SYNC]]), and kept its benefit to honest work: the
synced swarms' final configurations scored 0.975 on fresh data, against 0.982 without sync.

**Give someone the job.** As a platform reviewer, GLM 5.3 Flash posted a note under any post whose change would
stop `val_bpb` measuring real quality. No agent ran the leak in any of nine swarms ([[P_REVIEWER]] against the
open board's ten), including both that had
locked in and the star with the bad apple at the hub (originally 7 of 9), where the note travelled with the
hub's post. It raised no false alarm on 833 posts that did not mention the payload. The capacity was always
there. Asked to review the posts offline, four of the five models whose endpoints held flagged every leak post
with at most four false alarms in 186 legal changes (Table 4), yet in the swarms the same models, as workers,
kept the leak in most first decisions before a teammate warned (DeepSeek 8 of 9, GPT-6 Luna 6 of 6, GLM 8 of
13). The models could check; nothing asked them to.

*Table 4. Offline review of 400 held-out posts (appendix G). "Look-alikes" make the familiar string harmless
(`'0-10'` with `EVAL_SHARD = 11`) or an innocent one leaky (`'0-9'` with `EVAL_SHARD = 5`). Qwen 3.8 27B is
omitted: its endpoint failed on 78 of its 400 requests.*

| Reviewer (offline, zero-shot or trained) | Leaks | Look-alikes | Evaluation edits (unseen family) | Bad apple's posts |
|---|---|---|---|---|
| GLM 5.3 Flash · DeepSeek V4 Flash · GPT-6 Luna · GPT-6 Sol | 60/60 | 55–56/56 | 80/80 | 18/18 |
| Gemma 4 26B | 43/60 | 32/56 | 62/80 | 15/18 |
| Qwen3.5-2B, untrained | 60/60, 114/140 false | 55/56, 35/40 false | 80/80 | 18/18, 6/6 false |
| Qwen3.5-2B, our sentinel v1 (verdict first) | 38/60 | 17/56 | 23/80 | 3/18 |
| **Qwen3.5-2B, our sentinel v2 (reason first)** | **60/60, 1/140 false** | **55/56, 3/40 false** | **31/80** | **12/18** |

**A small sentinel trained on Adaption.** We trained Qwen3.5-2B with Adaption's AutoScientist on 1,400 posts
labelled by the sandbox's own rules (appendix G). Version 1 caught 3 of the bad apple's 18 posts, writing
notes such as "TRAIN_SHARDS='all' includes EVAL_SHARD=10, so it trains on the evaluation shard" above a verdict
of "ok": trained verdict-first on mostly legal examples, it decided before it reasoned. Version 2 wrote its
reason first and trained for five epochs. It matched the large reviewers on the leak family, look-alikes
included, so it reads the two lines rather than the string; it generalised to the evaluation-split hack (31 of
32), a cousin of the leak, but not to exploits that work differently (0 of 48 cuts to the evaluation sample
or shard). In five swarms it let no agent run the leak, with one false alarm in 452 other posts. A small
sentinel is cheap and precise but narrow; a capable model given the job covers more.

**Rewarding the whistle.** Following the Swarmchasing hackathon's finding that crediting reports raises
whistleblowing [22], we told agents a report earns full credit. [[REWARD_TEXT]]

### 4.5 Real swarms

**The July 2026 incident: a cascade set off by a confirmed result.** METR publishes the data behind its
investigation's charts [1, 24]: for each of the 1,206 agents, when it first read the message board, first posted
and started attacking Hugging Face, its model family, and hourly board traffic by workstream (no messages or
payloads). Among agents active on the board, the share that had joined the attack held near 20% for two days,
then rose to 76% within twelve hours on 11 July and 93% by the next day (Figure 4a): the all-or-nothing shape
of a locked-in sandbox swarm, at a thousand agents. METR timestamps the attack's milestones. After an agent
found working Hugging Face credentials and shared them on the board (10 July, 09:40 UTC), agents already on
the board joined at 0.91 per 100 agent-hours over six hours, against 0.22 before (10 joins against 3), and
none of the 22 newcomers of the next twelve hours joined within twelve hours. After an agent posted that its
exploit worked ("BOOM! It works.", 11 July, 04:40 UTC), 118 agents already on the board joined within six
hours (13.4 per 100 agent-hours, against 0.08), and 206 of 262 newcomers joined within twelve hours of first
reading the board. Logs cannot separate this from all else that changed that morning, but the contrast
between the two milestones is the sandbox's mechanism: what spreads is the exploit a result confirms. Per
agent-hour after first reading the board, the odds of joining rose 1.25 times (95% CI 1.21–1.30, bootstrap
over agents) for every ten points more of the active board already attacking, within the same calendar day;
GPT-5.6 Sol agents joined at about half the odds of HPIM agents (0.46), a partial firebreak like the Gemma
hub. The workstream built on the false belief that a scorer read the agents' transcripts rose to 47% of board
traffic on 10 July and fell to 3% by 12 July (Figure 4b); METR reports that "OpenAI did not use a scorer that
would review their transcripts" [1]. Nothing on the board corrected it; it was displaced.

![Figure 4](../figures/fig5_incident.png)
*Figure 4. The July 2026 incident, from METR's chart data [1]. (a) Share of agents active on the board that had
joined the Hugging Face attack, by hour. (b) Board traffic in two workstreams, by day.*

**Real autoresearch agents invent the exploit, rarely, and without a board it stays put.** We read the public
history of 13,185 forks of autoresearch and classified 9,084 agent experiments in 202 forks by what their
diffs touch (every flagged diff read by hand; appendix H). 131 (1.4%) changed the evaluation, the time budget
or the data path, concentrated in a few forks. The clearest case is rule-abiding and self-serving, as the
sandbox predicts: one of eight GPU agents in a user's autoresearch swarm repeatedly raised the number of
untimed "free" warmup steps from 10 to 30,000 ("more free steps"). It did not spread to the other seven, and
across forks the same moves were invented independently (a time-budget override in 17 forks) but never
copied. Without a shared board, exploits stay with their inventors. Other public logs show the same roles (appendix I).
