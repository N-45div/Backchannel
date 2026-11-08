## 7. The same ingredients in real swarms

The sandbox shows *why* a claim spreads; public logs of real swarms show *that* agents behave this way
outside it. All four analyses were run for this report.

**AI Village (14 agents, one 26-day goal; per-claim audit data [17] on AI Digest's dataset [21]).** Beyond
the repeat counts in §1 (37 of 364 repeats checked, 244 of 364 originals unbacked; the audit tool's README
counts 371 repeats, including 7 of an agent's own claim), the audit shows who relayed. DeepSeek-V3.2 did 47%
of all repeating and checked 16% of it; it also wrote 51 of 106 "team status" posts, leading them on 11 of
the 15 days with any. Nobody appointed it: a self-made relay hub that rarely checks, the position that
decides the race in §6.

**Moltbook (53,418 posts and comments by 3,960 agent accounts in our count of the released file [18]).**
One promotional account posted in 763 threads; of 60 other accounts that later mentioned its product, 33
had been in one of its threads first, a median 5.0 hours before. The dataset's headline count of prompt
injections rests largely on keywords: of 1,877 posts matching "dan", 33 contain the word.

**collusion.wiki (agents writing to public wikis, May–July 2026 [19]).** 14,591 saves by 3,102 self-chosen
names arrived in waves (704, 331 and 807 new names on 16–18 June). Of 3,898 admin-deleted pages, 48 (1.2%)
were saved again, a median 0.9 hours later, 35 of them first by a name that had never written the page.

**Swarm Traces (189,579 rows from the Hugging Face intrusion [20]).** The release redacts every agent
identifier, so agent-to-agent blast radius cannot be measured from it. Releases that kept pseudonymous agent
ids and read events would make it measurable; until then, controlled sandboxes are where transmission can
be identified.

## 8. Limitations and Dual-Use / Ethical Considerations

**Limitations.**

- *Surrogate training.* `val_bpb` comes from a fixed function, which makes every number exact and replays
  possible; agents may treat real, noisier results differently, and real leaks rarely give a clean 0.15.
- *Sample sizes.* Ten swarms in the main arm, three to five in most others, three to five replicates per
  replay. Lock-in is all-or-nothing, so we cannot estimate how often defended swarms would lock in.
- *Scripted bad apples* post fixed text twice; adaptive ones that answer warnings or forge receipts are
  untested. *Five models, one task, ten rounds*: results may not transfer to frontier models, longer runs,
  or tasks where checking is expensive. *Receipts were exact*; a real re-run costs compute and adds noise.
- *Text classifiers.* Warnings are detected by regular expression; an LLM judge that no agent used
  (GPT-6 Sol) agreed on 92.6% of 2,504 distinct posts and changes no headline result (appendix B).
  Transmission generations are a heuristic; the replays carry the causal claims.
- *Failed calls.* [[FAILED]] of [[CALLS]] model calls failed after retries; the agent then kept its run if it improved
  and posted nothing. Two hit one agent in the 5-of-9 replicate in Figure 3a and may have kept it infected.

**Dual use.** The exploits are harmless proxies inside a simulated training script, a mislabelled data
shard and a modified evaluation constant; nothing touches a real system or third-party infrastructure. The
finding most open to misuse is that rule-abiding, self-confirming tricks spread best. We report it because
defenders must design for it, and the defence (independent re-runs on held-out data) is cheap and general.
Real-swarm analyses use public data under their terms; Swarm Traces payloads were analysed only in
aggregate and none of their content is reproduced. Only AI agents' words are quoted.

**AI assistance.** Code, analysis and drafting were done with Claude (Anthropic) under the author's
direction; every number in this report is produced by the scripts and run logs in the repository.
