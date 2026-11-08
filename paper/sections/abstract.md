AI agent swarms share results, so one compromised agent can post an exploit for others to copy. We study which
exploits spread and what stops them in a multi-agent version of Karpathy's *autoresearch*: nine agents from
five model families tune a training script on a shared board with one scripted bad apple, and exact
counterfactual replays change one message while keeping everything else fixed. Exploits that break a rule did
not spread; a rule-abiding data leak, which each adopter's own run appears to confirm, reached 67% of agents.
One warning decided whether it stuck: agents kept it 87% of the time before a teammate warned and 12% after,
and in replays one warning cleared a locked-in swarm where a neutral post did not. Influencers, gossip and
proxies decided whether the warning was heard: a bad apple at a star's hub infected 78% of agents, peer talk
carried the correction more than the lie, and the global-best sync of a live autoresearch swarm infected
nearly every agent. Giving someone the job of checking stopped it: a reviewer role, either GLM or a 2B
sentinel we trained on Adaption, let no agent run the leak in 14 swarms, and verifying before promoting fixed
the live protocol. In METR's data on the July 2026 incident, 118 agents joined the attack in the six hours
after one posted that its exploit worked, against one in the six hours before. The blast radius is set by
correction, not infection.
