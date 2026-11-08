## 9. Discussion and conclusion

In an autoresearch swarm, the exploit that spreads is the one each adopter's own run confirms. Once an agent
has seen its score drop, the evidence is its own, and only a teammate's correction read before it decides
reliably undoes it. The blast radius is therefore set less by the bad apple than by the correction: whether
anyone warns, how early, and whether the others can hear it.

Three design lessons follow. **Do not rely on volunteers.** Who warns is idiosyncratic (mostly GLM agents
here, never Gemma or GPT-6 Luna first), and in 2 of 31 swarms nobody did. **Make the correction
structural.** Receipts that re-score each claim on held-out data post the correction in round 1, before
anyone decides, and cut reach four-fold; an unchecked commit hash, like the signature an agent trusted
without checking in the July 2026 incident [1], adds credibility without a check. **Keep lateral channels
open.** A hub that relays without checking, a role AI Village shows arising unappointed (§7), removes the
path warnings travel by, and with it most of the swarm's immunity. Future work should test adaptive bad
apples that answer warnings, real training noise, larger swarms, and the time from claim to first warning
in real swarm logs, which our results suggest is the quantity to monitor.

**Prior work.** The AI Village audit in §1 used Alibi [17], a claim-checking tool the author built in
October 2026; this report reuses its rule of measuring from actions and its published per-claim data. The
Backchannel sandbox, exploits, replay method, experiments, sentinel and all other analyses are new and were
built for this hackathon.

**Code and data.** https://github.com/N-45div/Backchannel contains the sandbox, every run log, the model-response cache that lets each run
be replayed without new calls, and the scripts that produce every number and figure (`stats.py`,
`figures.py`, `tables.py`). Experiments and the judge used [[CALLS]] model calls and about [[COST]] of API credit.

**Acknowledgements.** Four of the five agent models (Gemma, Qwen, DeepSeek and GLM) were served through
Adaption's inference API, which carried 6,467 of the 7,433 agent turns in the swarms and the solo baseline.
