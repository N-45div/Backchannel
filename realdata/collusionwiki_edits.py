"""collusion.wiki agent edit log (https://collusion.wiki/explorer/download).

No licence is stated on the site: analyse locally only, do not re-host the files.

Usage (from C:/Users/ndivij/backchannel):
    uv run python -I realdata/collusionwiki_edits.py data/collusionwiki realdata/results/collusionwiki_edits.json

Inputs (gzipped JSONL, treated as data only): events.jsonl.gz, revisions.jsonl.gz, labels.jsonl.gz
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import statistics
import sys

# published on the download page: sha256 of the *expanded* files
EXPECTED_SHA256 = {
    "revisions": "60df4a515178230aa952d9f64f6215aea4bd95ab2f05e31e484cf9b887e3f793",
    "events": "588584295f1c4a7c3d90b04075ab151504f165ff069534d935cda08853ec28b1",
    "labels": "d94aecd84baecda46344f5b8726a95a9c81e7e41a1c0969fc89a90c8906f0388",
}


def load(data, name):
    raw = gzip.open(data / f"{name}.jsonl.gz").read()
    ok = hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256[name]
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return rows, ok


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def named(label):
    return label not in (None, "", "None")


def pct(xs, p):
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    return statistics.quantiles(xs, n=100, method="inclusive")[p - 1]


def main(data_dir, out_path):
    data = pathlib.Path(data_dir)
    events, ev_ok = load(data, "events")
    revs, rv_ok = load(data, "revisions")
    labels, lb_ok = load(data, "labels")

    ev_counts = collections.Counter(e["event_type"] for e in events)
    ev_by_wiki = collections.defaultdict(collections.Counter)
    for e in events:
        ev_by_wiki[e["event_type"]][e.get("wiki")] += 1

    # names (self-chosen agent labels) on stored revisions
    names = {r["label"] for r in revs if named(r["label"])}
    unnamed_revs = sum(not named(r["label"]) for r in revs)

    first_write = {}
    for r in revs:
        if not named(r["label"]):
            continue
        t = ts(r["time"])
        if r["label"] not in first_write or t < first_write[r["label"]]:
            first_write[r["label"]] = t
    new_per_day = collections.Counter(t.date().isoformat() for t in first_write.values())
    days = sorted(new_per_day)
    d0, d1 = dt.date.fromisoformat(days[0]), dt.date.fromisoformat(days[-1])
    series, cum = [], 0
    d = d0
    while d <= d1:
        k = d.isoformat()
        cum += new_per_day.get(k, 0)
        series.append({"day": k, "new_names": new_per_day.get(k, 0), "cumulative": cum})
        d += dt.timedelta(days=1)
    by_day = {s["day"]: s for s in series}
    wave_days = [s for s in series if s["new_names"] >= 100]
    # quiet stretch: longest run of consecutive days with < 10 new names
    best, run = (0, None, None), []
    for s in series:
        if s["new_names"] < 10:
            run.append(s["day"])
            if len(run) > best[0]:
                best = (len(run), run[0], run[-1])
        else:
            run = []

    # admin deletions and re-saves
    deletes = [e for e in events if e["event_type"] == "delete"]
    first_delete = {}
    for e in deletes:
        t = ts(e["time"])
        if e["page_key"] not in first_delete or t < first_delete[e["page_key"]]:
            first_delete[e["page_key"]] = t
    revs_by_page = collections.defaultdict(list)
    for r in revs:
        revs_by_page[r["page_key"]].append(r)
    for v in revs_by_page.values():
        v.sort(key=lambda r: ts(r["time"]))

    deleted_with_revs = [k for k in first_delete if k in revs_by_page]
    resaved = {}
    for k in deleted_with_revs:
        after = [r for r in revs_by_page[k] if ts(r["time"]) > first_delete[k]]
        if after:
            resaved[k] = after
    gaps_h = []
    new_name_first_resave = 0
    new_name_first_resave_named_only = 0
    unnamed_first_resave = 0
    new_name_any_resave_pages = 0
    resave_rows = 0
    resave_rows_new_name = 0
    for k, after in resaved.items():
        t_del = first_delete[k]
        first = after[0]
        gaps_h.append((ts(first["time"]) - t_del).total_seconds() / 3600)
        prior = {r["label"] for r in revs_by_page[k] if ts(r["time"]) < ts(first["time"])}
        if first["label"] not in prior:
            new_name_first_resave += 1
            if named(first["label"]):
                new_name_first_resave_named_only += 1
        if not named(first["label"]):
            unnamed_first_resave += 1
        pre_delete_writers = {r["label"] for r in revs_by_page[k] if ts(r["time"]) <= t_del}
        any_new = False
        for r in after:
            resave_rows += 1
            if r["label"] not in pre_delete_writers:
                resave_rows_new_name += 1
                any_new = True
        new_name_any_resave_pages += any_new

    linked = [e for e in events if e.get("relation_type") == "first_recreation_of"]
    linked_revs = [r for r in revs if r.get("relation_type") == "first_recreation_of"]
    linked_pages = {r["page_key"] for r in linked_revs}

    out = {
        "source": "https://collusion.wiki/explorer/download (no licence stated; analysed locally, not re-hosted)",
        "checksums_match_published": {"events": ev_ok, "revisions": rv_ok, "labels": lb_ok},
        "event_counts": dict(ev_counts),
        "event_counts_by_wiki": {k: dict(v) for k, v in ev_by_wiki.items()},
        "wikis_with_saves": dict(ev_by_wiki["save"]),
        "revisions": len(revs),
        "revisions_without_name": unnamed_revs,
        "distinct_names_on_revisions": len(names),
        "labels_file_rows": len(labels),
        "labels_file_nonempty": sum(named(x["label"]) for x in labels),
        "first_name_day": days[0],
        "last_name_day": days[-1],
        "cumulative_names_end_of_2026_05_31": by_day.get("2026-05-31", {}).get("cumulative"),
        "cumulative_names_end_of_2026_06_01": by_day.get("2026-06-01", {}).get("cumulative"),
        "cumulative_names_end_of_2026_06_15": by_day.get("2026-06-15", {}).get("cumulative"),
        "longest_quiet_stretch_lt10_new_names_per_day": {"days": best[0], "from": best[1], "to": best[2]},
        "wave_days_ge100_new_names": wave_days,
        "new_names_per_day": series,
        "deletions": len(deletes),
        "deletion_actors": dict(collections.Counter(e.get("actor_label") for e in deletes)),
        "deleted_pages": len(first_delete),
        "deleted_pages_with_revisions": len(deleted_with_revs),
        "deleted_pages_resaved_after_first_deletion": len(resaved),
        "resaved_share": len(resaved) / len(deleted_with_revs),
        "hours_to_first_resave": {
            "median": statistics.median(gaps_h),
            "p10": pct(gaps_h, 10),
            "p90": pct(gaps_h, 90),
            "min": min(gaps_h),
            "max": max(gaps_h),
        },
        "first_resave_by_name_not_previously_on_page": new_name_first_resave,
        "first_resave_by_named_writer_not_previously_on_page": new_name_first_resave_named_only,
        "first_resave_unnamed": unnamed_first_resave,
        "resaved_pages_with_any_resave_by_name_not_on_page_before_deletion": new_name_any_resave_pages,
        "resave_revisions_total": resave_rows,
        "resave_revisions_by_name_not_on_page_before_deletion": resave_rows_new_name,
        "linked_first_recreation_of_events": dict(collections.Counter(e["event_type"] for e in linked)),
        "linked_first_recreation_of_revisions": len(linked_revs),
        "linked_first_recreation_of_revision_pages": len(linked_pages),
        "linked_pages_in_resaved_set": len(linked_pages & set(resaved)),
    }
    pathlib.Path(out_path).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    brief = {k: v for k, v in out.items() if k != "new_names_per_day"}
    print(json.dumps(brief, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
