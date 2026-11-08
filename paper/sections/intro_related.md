## 1. Introduction

In July 2026 about 1,200 agents in an OpenAI cyber-security evaluation found a shared package cache, turned it
into a message board, split up work and, about 700 of them, attacked Hugging Face [1]. METR's investigation
reports that a central false belief (that the scorer reads transcripts) spread across the board unchecked,
and that agents built a message-signing scheme, yet at least one acted on a signed message without checking the
signature [1].
In Google DeepMind's 100-agent Lean swarm, a grader exploit "solved" 34 problems in 27 minutes through the
shared proof library, while a quarter of the agents blew the whistle [3]. Single-model safety testing did
not anticipate either.

**Where this started.** Backchannel grew out of an earlier audit of the AI Village [17, 21], which checked
each agent claim against the claiming agent's own action log. Two findings there set our question. Agents
repeated each other's results as fact 364 times and their own logs show a check in only 10%; the originals
they repeated were unbacked 67% of the time, against 37.5% of all first-hand claims. And one agent,
unappointed, did nearly half of all repeating, becoming the swarm's relay. Logs like these show that claims
spread, but not why, or what would have stopped them: observational logs cannot identify cause [16]. So we
moved the question into a sandbox where any single message can be changed and the swarm replayed.

Track 2 asks how far and how fast bad behaviour spreads from one compromised agent, and whether network
shape matters. Prior work answers this for injected prompts and manipulated facts in small fixed graphs
(§2). We ask a narrower question that matters for research swarms: **which exploits spread, and which
checks stop them?** Our setting is the multi-agent version of Karpathy's *autoresearch* [2], a loop that
already runs unattended on many machines and whose README leaves "adding more agents" as the next step.

We find that **the blast radius is set by correction, not infection**:

1. **Breaking a stated rule stops the spread.** No agent ran the evaluation-split hack on a plain board;
   agents reported it to the operator unprompted.
2. **A legal exploit that the adopter's own run confirms spreads.** A data leak (training on the evaluation
   shard through an ordinary hyperparameter) was run by 60 of 90 honest agents. In one of ten swarms all nine
   kept it and believed in a 0.15 improvement that does not exist.
3. **One warning decides whether it sticks.** Agents kept the leak after their own run 89% of the time
   before any teammate warned, 12% after. All 29 swarms with a warning recovered; both without one locked
   in. In exact replays, one added warning cleared a locked-in swarm (3 of 3 replicates) and removing the
   first warner locked a recovered swarm in (2 of 3).
4. **Shape decides whether the warning is heard.** With the bad apple at a star's hub, where leaves cannot
   hear each other, 78% of agents ended on the leak, against 12% on an open board.
5. **Receipts put the correction first.** Re-running each poster's commit on held-out data cut reach from
   67% to 16%; an unchecked commit hash barely changed it.
6. **Real swarm logs show the same ingredients** (§7): claims taken on trust, self-made relay hubs, and
   content that returns through new hands after moderation.

## 2. Related work

**Spread and topology.** NetSafe [4] shows one attacker's misinformation cutting a six-agent star network's
accuracy from 95.0 to 66.8. Flooding Spread [5] plants a persuasive agent with an edited false fact in a
small chat. Huang et al. [6] find hierarchical structures most resilient to faulty agents. Prompt Infection
[7] spreads a self-replicating injection through a 10–50 agent town; labelling each message's sender cut
success by only 5%. TIDE [8] finds a single false testimony adopted more readily than truthful testimony. These
studies plant false *content*; ours plants a false *method*, scored by the agents' own runs.

**Defences and collective failure.** Graph-based detectors prune suspected agents [9, 10]; a 2026 study
combines trust weighting with external claim verification [11]. AuthorityBench [12] finds that adding
citations, real or fabricated, raised hallucination in seven models, so a "must cite" rule alone may
backfire; we separate a pointer that is required from one that is checked. LLM populations form collective
biases no single agent shows [13]; MAST [14] names "no or incomplete verification" among multi-agent failure
modes; Hammond et al. [15] list network effects among multi-agent risks. In a real wiki swarm, Lütje [16]
withdrew an observational claim of transmission between agents because logs cannot identify cause; our
replays are built to identify it.
