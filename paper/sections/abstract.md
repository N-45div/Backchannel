AI agent swarms share results on common boards, so one compromised agent can post an exploit for others to
copy. We ask which exploits spread and what stops them, in a multi-agent version of Karpathy's
*autoresearch*: nine honest agents from five model families tune a training script for ten rounds and share
results on a board with one scripted bad apple. A surrogate training function makes every score exact, and
exact counterfactual replays change one message while keeping everything else fixed. Exploits that break a
stated rule (editing the evaluation) were not run on a plain board. A rule-abiding data leak, training on
the evaluation shard, which each adopter's own run appears to confirm, was run by 67% of honest agents.
Whether it stuck was decided by one message: agents kept it 89% of the time before any teammate warned and
12% after; all 29 swarms with a warning recovered and both without one locked in. In replays, one injected
warning cleared a fully locked-in swarm (3 of 3 replicates) and silencing the first warner locked a recovered
swarm in (2 of 3). Network shape decided whether a warning was heard: with the bad apple at a star's hub,
78% of agents ended infected. Platform receipts that re-score each claim on held-out data cut reach to 16%.
Logs from AI Village, Moltbook and collusion.wiki show the same ingredients in real swarms.
