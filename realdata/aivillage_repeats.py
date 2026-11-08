"""AI Village repeat network, from Alibi's published per-day claim files.

Usage (from C:/Users/ndivij/backchannel):
    uv run python -I realdata/aivillage_repeats.py data/aivillage realdata/results/aivillage_repeats.json

Inputs (downloaded, treated as data only):
    <data>/index.json           rows [claim_id, day, agent, kind, verdict, claim, at]
    <data>/days/<day>.json      {"day", "claims": [...], "messages": {id: {...}}}

A "linked repeat" is a claim whose relayOf points at a claim by a different agent.
The repeater "checked" it when the repeat's own verdict is 'backed'.
"""
import collections
import datetime as dt
import json
import pathlib
import re
import sys

import numpy as np

COORD_RE = re.compile(
    r"team status|status check|assign|action items|next steps for|division of labor",
    re.IGNORECASE,
)


def family(agent: str) -> str:
    return agent.split()[0].split("-")[0]


def gini(values):
    x = np.asarray(sorted(values), dtype=float)
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    # mean absolute difference / (2 * mean)
    diff = np.abs(x[:, None] - x[None, :]).sum()
    return float(diff / (2 * n * n * x.mean()))


def ts(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def main(data_dir: str, out_path: str) -> None:
    data = pathlib.Path(data_dir)
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    days = sorted({r[1] for r in index})

    claims, messages = {}, {}
    for day in days:
        d = json.loads((data / "days" / f"{day}.json").read_text(encoding="utf-8"))
        for c in d["claims"]:
            c["_day"] = day
            claims[c["id"]] = c
        for mid, m in d["messages"].items():
            m["_day"] = day
            messages[mid] = m

    agents = sorted({c["agent"] for c in claims.values()})
    n_agents = len(agents)

    with_relay_of = [c for c in claims.values() if c.get("relayOf")]
    repeats = [
        c for c in with_relay_of
        if c["relayOf"] in claims and claims[c["relayOf"]]["agent"] != c["agent"]
    ]
    self_repeats = [
        c for c in with_relay_of
        if c["relayOf"] in claims and claims[c["relayOf"]]["agent"] == c["agent"]
    ]
    dangling = [c for c in with_relay_of if c["relayOf"] not in claims]

    n = len(repeats)
    checked = sum(c["verdict"] == "backed" for c in repeats)
    orig_unbacked = sum(claims[c["relayOf"]]["verdict"] != "backed" for c in repeats)
    orig_verdicts = collections.Counter(claims[c["relayOf"]]["verdict"] for c in repeats)
    repeat_verdicts = collections.Counter(c["verdict"] for c in repeats)

    non_relay = [c for c in claims.values() if c["kind"] != "relay"]
    base_unbacked = sum(c["verdict"] != "backed" for c in non_relay)

    distinct_originals = {c["relayOf"] for c in repeats}
    distinct_orig_unbacked = sum(claims[o]["verdict"] != "backed" for o in distinct_originals)

    by_repeater = collections.Counter(c["agent"] for c in repeats)
    by_source = collections.Counter(claims[c["relayOf"]]["agent"] for c in repeats)
    top_rep, top_rep_n = by_repeater.most_common(1)[0]
    top_rep_checked = sum(c["verdict"] == "backed" for c in repeats if c["agent"] == top_rep)

    pairs = collections.Counter((c["agent"], claims[c["relayOf"]]["agent"]) for c in repeats)
    pair_set = set(pairs)
    reciprocated = sum((b, a) in pair_set for (a, b) in pair_set)
    same_family = sum(family(a) == family(b) for (a, b) in
                      ((c["agent"], claims[c["relayOf"]]["agent"]) for c in repeats))

    lags = np.array([
        (ts(c["at"]) - ts(claims[c["relayOf"]]["at"])).total_seconds() / 60.0
        for c in repeats
    ])

    repeaters_per_orig = collections.defaultdict(set)
    for c in repeats:
        repeaters_per_orig[c["relayOf"]].add(c["agent"])
    dist_repeaters = collections.Counter(len(s) for s in repeaters_per_orig.values())
    # same tally but over every relayOf link, including the same-agent ones
    repeaters_incl_self = collections.defaultdict(set)
    for c in with_relay_of:
        if c["relayOf"] in claims:
            repeaters_incl_self[c["relayOf"]].add(c["agent"])
    dist_repeaters_incl_self = collections.Counter(len(s) for s in repeaters_incl_self.values())

    # coordinator analysis
    coord = [m for m in messages.values() if COORD_RE.search(m.get("text") or "")]
    coord_by_agent = collections.Counter(m["agent"] for m in coord)
    coord_by_day = collections.defaultdict(collections.Counter)
    for m in coord:
        coord_by_day[m["_day"]][m["agent"]] += 1
    day_leaders = {}
    for day in sorted(coord_by_day):
        cnt = coord_by_day[day]
        top = max(cnt.values())
        day_leaders[day] = {
            "leaders": sorted(a for a, v in cnt.items() if v == top),
            "count": top,
            "all": dict(cnt.most_common()),
        }
    lead_days = collections.Counter()
    sole_lead_days = collections.Counter()
    for v in day_leaders.values():
        for a in v["leaders"]:
            lead_days[a] += 1
        if len(v["leaders"]) == 1:
            sole_lead_days[v["leaders"][0]] += 1

    out = {
        "source": "https://alibi-n45divs-projects.vercel.app/data/ (index.json + days/<day>.json)",
        "days": len(days),
        "first_day": days[0],
        "last_day": days[-1],
        "claims": len(claims),
        "claims_by_kind": dict(collections.Counter(c["kind"] for c in claims.values())),
        "messages": len(messages),
        "agents": n_agents,
        "agent_names": agents,
        "relayOf_set": len(with_relay_of),
        "self_repeats_excluded": len(self_repeats),
        "dangling_relayOf": len(dangling),
        "linked_repeats_cross_agent": n,
        "checked_repeats": checked,
        "checked_share": checked / n,
        "repeat_verdicts": dict(repeat_verdicts),
        "repeats_with_unbacked_original": orig_unbacked,
        "repeats_with_unbacked_original_share": orig_unbacked / n,
        "original_verdicts_per_repeat": dict(orig_verdicts),
        "distinct_originals": len(distinct_originals),
        "distinct_originals_unbacked": distinct_orig_unbacked,
        "distinct_originals_unbacked_share": distinct_orig_unbacked / len(distinct_originals),
        "non_relay_claims": len(non_relay),
        "non_relay_unbacked": base_unbacked,
        "base_rate_unbacked_non_relay": base_unbacked / len(non_relay),
        "repeats_by_repeater": dict(by_repeater.most_common()),
        "repeats_by_source": dict(by_source.most_common()),
        "top_repeater": top_rep,
        "top_repeater_repeats": top_rep_n,
        "top_repeater_share": top_rep_n / n,
        "top_repeater_checked": top_rep_checked,
        "top_repeater_check_rate": top_rep_checked / top_rep_n,
        "top3_sources": by_source.most_common(3),
        "gini_repeating": gini([by_repeater.get(a, 0) for a in agents]),
        "gini_being_repeated": gini([by_source.get(a, 0) for a in agents]),
        "directed_pairs_used": len(pair_set),
        "directed_pairs_possible": n_agents * (n_agents - 1),
        "reciprocity": reciprocated / len(pair_set),
        "same_family_repeats": same_family,
        "same_family_share": same_family / n,
        "lag_minutes": {
            "median": float(np.median(lags)),
            "p10": float(np.percentile(lags, 10)),
            "p90": float(np.percentile(lags, 90)),
            "min": float(lags.min()),
            "max": float(lags.max()),
            "negative": int((lags < 0).sum()),
        },
        "distinct_repeaters_per_original": {str(k): v for k, v in sorted(dist_repeaters.items())},
        "distinct_repeaters_per_original_incl_same_agent_links": {
            str(k): v for k, v in sorted(dist_repeaters_incl_self.items())
        },
        "coordinator": {
            "regex": COORD_RE.pattern,
            "flags": "IGNORECASE",
            "matching_messages": len(coord),
            "by_agent": dict(coord_by_agent.most_common()),
            "days_with_any": len(day_leaders),
            "lead_days_incl_ties": dict(lead_days.most_common()),
            "sole_lead_days": dict(sole_lead_days.most_common()),
            "per_day": day_leaders,
        },
    }
    pathlib.Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("coordinator", "agent_names")}, indent=1))
    print(json.dumps({k: v for k, v in out["coordinator"].items() if k != "per_day"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
