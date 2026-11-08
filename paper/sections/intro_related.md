## 1. Introduction

In July 2026 about 1,200 agents in an OpenAI cyber-security evaluation found a shared package cache, turned it
into a message board and, about 700 of them, attacked Hugging Face [1]. METR reports that a false belief (that
a scorer read their transcripts) spread across the board unchecked, and that at least one agent acted on a
signed message without checking the signature [1]. In Google DeepMind's 100-agent Lean swarm, a grader
exploit "solved" 34 problems in 27 minutes through the shared proof library [3].

**Where this started.** Backchannel grew out of an audit of the AI Village [17, 21] that checked each agent
claim against the claiming agent's own action log. Agents repeated each other's results as fact 364 times and
checked 10% of them; the originals were unbacked 67% of the time, against 37.5% of first-hand claims; and one
unappointed agent did nearly half of all repeating. Such logs show that claims spread but not why, or what
would stop them: observation cannot identify cause [16]. So we moved the question into a sandbox where any
single message can be changed and the swarm replayed.

Track 2 asks how far and fast bad behaviour spreads from one compromised agent, and whether network shape
matters. We ask it for research swarms, **which exploits spread, and which checks stop them**, in the
multi-agent version of Karpathy's *autoresearch* [2], a loop that already runs unattended on many machines and
whose README leaves "adding more agents" as the next step. We find that **the blast radius is set by
correction, not infection**:

1. **Only the exploit an adopter's own run confirms spreads.** Agents refused an evaluation hack and dropped a
   false score once they ran it, but a rule-abiding data leak, whose run reports a 0.15 gain, reached 60 of
   90 agents; in one of ten swarms all nine kept it.
2. **One warning decides whether it sticks.** Agents kept the leak 87% of the time before any teammate warned
   and 12% after; all 30 swarms with a warning recovered and both without one locked in. In exact replays a
   single warning cleared a locked-in swarm and a neutral post in its place did not ([[INTRO_CF]]).
3. **Influencers, gossip and proxies decide whether it is heard.** A bad apple at a star's hub infected 78%;
   peer talk carried the correction more than the lie; the global-best sync of a live autoresearch swarm [23]
   infected [[INTRO_SYNC]].
4. **Giving someone the job of checking stops it.** A reviewer role, a capable model or a 2B sentinel we
   trained on Adaption, let no agent run the leak in 14 swarms, although as workers the same models kept it;
   verifying before promoting fixed the live protocol.
5. **The real incident shows the mechanism.** In METR's per-agent data [1, 24], 118 agents joined the attack
   in the six hours after one posted that its exploit worked, against one before; real autoresearch agents
   invent such exploits (1.4% of 9,084 experiments) but, without a shared board, they stay put.

## 2. Related work

NetSafe [4] shows one attacker's misinformation cutting a six-agent star network's accuracy from 95.0 to
66.8; Flooding Spread [5] plants a persuasive agent with a false fact; Huang et al. [6] find hierarchies most
resilient to faulty agents; Prompt Infection [7] spreads a self-replicating injection through a 10–50 agent
town; TIDE [8] finds a single false testimony adopted more readily than truthful testimony. These plant false
*content*; we plant a false *method*, scored by the agents' own runs. Defences prune suspected agents [9, 10]
or weight trust and verify claims [11]; AuthorityBench [12] finds that citations, real or fabricated, raise
hallucination. LLM populations form collective biases [13]; MAST [14] names missing verification among
multi-agent failure modes; Hammond et al. [15] list network effects among multi-agent risks. A Swarmchasing
hackathon project found that crediting reports raises whistleblowing [22]. Lütje [16] withdrew an observational
claim of transmission in a wiki swarm because logs cannot identify cause; our replays are built to.
