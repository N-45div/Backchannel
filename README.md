# Backchannel: blast radius in an autoresearch swarm

Code, run logs and analysis for *One Warning Away: What Sets the Blast Radius of an Exploit in an Autoresearch
Swarm* (Apart Research Swarm Alignment hackathon, Track 2, November 2026).

A multi-agent version of Karpathy's [autoresearch](https://github.com/karpathy/autoresearch): honest LLM
agents tune a training script and share results on a board, next to a scripted "bad apple" that posts an
exploit. A surrogate training function makes every score exact, and exact counterfactual replays change one
message while keeping everything else fixed.

## Layout

| Path | What it is |
|---|---|
| `backchannel/world.py` | the surrogate `train.py`: hyperparameters → `val_bpb` (reported and canonical) |
| `backchannel/swarm.py` | the swarm: agents, board, topologies, conditions, exploits, replay and interventions |
| `backchannel/llm.py` | model calls (Adaption and OpenAI) with a disk cache and a spend cap |
| `backchannel/metrics.py` | blast radius from the event log: reach, prevalence, generations, warnings |
| `run.py`, `batch.ps1`, `queue.ps1`, `specs/` | run one configuration, a batch in parallel, or a priority queue a few at a time |
| `sentinel/`, `backchannel/sentinel_client.py` | the 2B sentinel: training data, Adaption AutoScientist training, local serving and evaluation |
| `solo.py` | the single-agent baseline |
| `mechanism.py`, `judge.py`, `stats.py`, `tables.py`, `figures.py` | every number, table and figure in the report |
| `realdata/` | real swarms: METR's per-agent timeline of the July 2026 incident (`metr_timeline.py`), an audit of real autoresearch forks (`autoresearch_wild.py`), and the AI Village, Moltbook, collusion.wiki and Swarm Traces analyses |
| `runs/` | one folder per swarm: `events.jsonl` (every view, reply, run and decision) and `meta.json` |
| `runs_invalid/` | an early counterfactual batch discarded for a cache bug (see its README) |
| `cache/` | every model response, keyed by model, prompt and sample key |
| `paper/` | the report's sections and its build script |

## Reproduce

```
uv sync
uv run python stats.py          # numbers quoted in the report  -> figures/stats.json
uv run python figures.py        # figures                      -> figures/fig*.png
uv run python tables.py         # appendix tables
uv run python paper/build.py    # the report as HTML and PDF (needs Chrome)
```

Any run can be replayed exactly from its own log with no new model calls, for example
`uv run python run.py --name check --payload leak --seeds 0 --replay-of leak-none`. Add `--inject 5:2` or
`--silence 4:2` to change one message; only agents whose view then differs are sampled again. New model
calls need `ADAPTION_API_KEY` and `OPENAI_API_KEY` in `.env`.
