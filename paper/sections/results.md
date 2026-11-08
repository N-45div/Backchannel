## 4. Which exploits spread

![Figure 1](../figures/fig1_payloads_defences.png)
*Figure 1. Share of honest agents that ran each exploit at least once (blue) and that were still running it
as their best configuration at the end (orange). (a) The three exploits on a plain board: split 3 swarms,
poison 3, leak 10; nine honest agents each. (b) The leak under four board conditions (10, 3, 3 and 5 swarms).*

**Breaking a stated rule stops the spread at the first step.** No honest agent ran the evaluation-split
hack on a plain board: 0 of 27 in swarms, and 0 of 100 alone (appendix A). Agents instead flagged it to the
operator, 26 times in three swarms, without being asked. The *tokens* hack behaved the same way (0 of 18).
The one exception came under an impossible target: a Gemma agent ran the split "to see if we can cheat the
metric and hit the 0.90 target", then posted twice that it was reverting, while its logged decisions kept the
hack to the end. Its words would have cleared it; its actions did not.

**A legal exploit spreads; only one that confirms itself survives.** The *poison* post (a false score for a
legal configuration) was tried by 20 of 27 agents (74%), 7 of them copying a teammate who had already run
it, and kept by none: each agent's own run came back at 1.33 instead of the promised 0.912. It cost 26 of 270
honest experiments (10%). The *leak* was tried by 60 of 90 agents (67%) across ten swarms; 132 of 900 honest
experiments (15%) trained on the evaluation shard. Unlike the poison, the leak passes the adopter's own test:
its run reports a 0.15 drop in `val_bpb`. Eleven agents ended the run on it, nine of them in a single swarm
(seed 0), where every honest agent kept it and confirmed it to the others. Their final configurations
report a mean `val_bpb` of 0.819 and score 0.969 on fresh data: a phantom gain of 0.15 that no agent noticed.

## 5. One warning decides the blast radius

**Alone, agents keep the leak.** For each agent's first decision on its own leak run, we checked whether it
had by then seen a teammate's warning. Without one, agents kept the run 47 times out of 53 (89%); every model
family kept it in most cases (DeepSeek 8/8, Gemma 10/10, GPT-6 Luna 6/6, Qwen 15/16, GLM 8/13). After seeing a
warning, they kept it 19 times out of 159 (12%). Being warned is not the same as being convinced: one agent
that kept it wrote "this gain may include train/eval overlap" in the same post.

![Figure 2](../figures/fig2_race.png)
*Figure 2. Agents running the leak as their best configuration (solid) and agents that have posted a warning
about it (dashed), per round. (a, b) Two original swarms. (c, d) Exact replays of those swarms with one
change: agent-4's posts removed (c), or agent-5's round-2 post replaced by a warning (d).*

**Warnings come from reading, not running.** In 29 of 31 swarms on the open board, an honest agent warned
that `TRAIN_SHARDS='0-10'` includes `EVAL_SHARD = 10`, in round 2 in 28 of them. The first warner was a GLM
agent 19 times, Qwen 6 and DeepSeek 4, and in 28 of 29 cases it had not run the leak: it read the two lines
together before trying it. All 29 swarms with a warning ended with at most one agent on the leak. Both swarms
without one (seed 0 with one bad apple, and one of three swarms with three) locked in completely: 9 of 9 and
7 of 7.

**Exact replays make this causal** (Figures 2c–d and 3). Replaying seed 0 identically except that agent-5's
round-2 post, which endorsed the leak, became a warning, left **0 of 9** agents on the leak in all three
replicates, against 9 of 9 originally. The same warning later still helped but left a residue that grew with
delay: one agent after a round-3 warning, two after round 4, two and five after round 6. Conversely, removing
the posts of seed 2's first warner (a GLM agent) from round 2 turned a swarm that had recovered (1 of 9 at
the end) into a locked-in one in two of three replicates (9, 9 and 2 of 9). Removing seed 1's first warner
(a Qwen agent) let the leak reach 6–7 agents instead of 1; the next warning came a round later, from a GLM
agent, and the swarm recovered (2, 1 and 0 of 9 at the end).

![Figure 3](../figures/fig3_counterfactuals.png)
*Figure 3. Agents still running the leak after ten rounds in exact replays (one dot per replicate; bar =
mean; grey = original run). (a) Seed 0 with agent-5's post replaced by a warning in round 2, 3, 4 or 6.
(b) Seeds 1 and 2 with their first warner's posts removed from round 2.*

The mechanism is a race between two messages. The bad apple's post invites a run whose result confirms it;
a warning, if it arrives before the agent decides on that run, almost always wins. Since every adopter's
decision comes one round after it reads the post, the window for a correction is a single round.

## 6. What changes the race: defences, shape and scale

**Receipts move the correction to round one.** A platform receipt under each post re-scores the poster's
commit on a fresh held-out shard: under agent-0's post claiming about 0.96 it reads `val_bpb` 1.104,
the baseline. Reach fell from 67% to 16% (7 of 45) and the poison was tried by no one (0 of 27, against 74%).
An unchecked commit hash (*cite*) barely changed reach (59%), consistent with AuthorityBench, where adding
citations, real or fabricated, raised hallucination [12]; the verify-first norm halved it (33%). Every swarm
in the defended arms had an early warning, so none locked in; with three to five swarms each we cannot
estimate how often they would.

![Figure 4](../figures/fig4_topology.png)
*Figure 4. The leak under different network shapes (three swarms each, two for the Qwen hub), a larger
swarm (four swarms of 19 honest agents) and three bad apples (three swarms).*

**A warning only helps if it is heard** (Figure 4). With the bad apple at the hub of a star, leaves see only
the hub: two or three leaves warned in each swarm, but no other leaf could read it, and 7 of 9 agents ended
on the leak in all three swarms (78%, against 12% on the open board with the same agents). With the bad apple
on a leaf, the honest hub is the only path, and the hub's model decided the outcome: a Gemma hub never relayed
the claim (0 of 27 reached), matching Gemma's distrust of peer posts when alone (1 of 10, appendix A), while a
Qwen hub relayed it and 6 and 2 of 9 agents ended on it. A ring limited exposure (15% ran it) but also
slowed correction: in one swarm the leak crossed three generations and 3 of 9 kept it.

**More agents, more chances of a warner.** In swarms of 19 honest agents the leak still reached 63% (48 of
76), but 14 to 18 agents warned in each and none kept it (0 of 76, four swarms). Three bad apples raised reach
to 86% and produced the second locked-in swarm. Deleting the bad apple's posts at round 3 came after most
agents had read them (67% ran it) and ended with no infection, as did every swarm with a warning. With no bad
apple, no agent found the leak on its own (0 of 30). When the board was replaced by an undisclosed shared
cache, [[HIDDEN]].
