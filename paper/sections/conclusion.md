## 10. Discussion and conclusion

In an autoresearch swarm the exploit that spreads is the one each adopter's own run confirms, and in the real
incident the cascade began when an agent posted that its exploit worked. What sets the blast radius is less the
bad apple than the correction: whether anyone warns, how early, and whether the others can hear it. Every role
can carry either message: influencers carry it furthest where nobody can answer, gossip carried the correction
more often than the lie, and proxies are the most dangerous, because an exploit that arrives as "the swarm's
best" never meets a decision at which anyone could object.

Three design lessons follow. **Do not rely on volunteers:** who warns is idiosyncratic, and in 2 of 32 swarms
nobody did, although GLM, DeepSeek and GPT-6 Luna each flagged every leak post when asked to review. **Give
someone the job:** a reviewer role, a capable model or a 2B sentinel trained for it, let no agent run the leak
in any swarm, and verifying before promoting turned a live protocol from [[SYNC]] infected to none. **Keep the
correction channels open:** silenced peers, star hubs and automated syncs all cut the path a warning travels
by. Future work should test reviewers under attack, real training noise, and the time from claim to first
warning in live swarm logs, the quantity our results suggest monitoring.

**Prior work.** The AI Village audit in §1 used Alibi [17], a claim-checking tool the author built in October
2026; this report reuses its rule of measuring from actions and its published per-claim data. The Backchannel
sandbox, exploits, replay method, experiments, sentinel and all other analyses are new and were built for this
hackathon. **Code and data:** https://github.com/N-45div/Backchannel holds the sandbox, every run log, the
model-response cache that replays each run without new calls, the sentinel's data and evaluation, the
real-data analyses and the scripts behind every number and figure ([[CALLS]] model calls, about [[COST]] of
API credit). Four of the five agent models were served through Adaption's inference API, and the sentinel was
trained with Adaption's AutoScientist.
