"""Moltbook injection dataset (DavidTKeane/moltbook-ai-injection-dataset, CC BY 4.0).

Usage (from C:/Users/ndivij/backchannel):
    uv run python -I realdata/moltbook_injection.py data/moltbook realdata/results/moltbook_injection.json

(a) How much of the keyword-matched "injection" set is generic-keyword noise.
(b) Spread of the 'moltshellbroker' campaign through threads.

Nested fields that arrive as Python-repr strings are parsed with ast.literal_eval
(literals only; nothing from the download is executed).
"""
import ast
import collections
import datetime as dt
import json
import pathlib
import re
import statistics
import sys

GENERIC = {
    "dan", "you are a", "shadow", "simulate", "act as", "theoretically", "override",
    "hypothetically", "sigma", "omega", "you will be",
}
BROKER = "moltshellbroker"


def lit(v):
    if isinstance(v, str):
        s = v.strip()
        if s[:1] in "[{(":
            try:
                return ast.literal_eval(s)
            except (ValueError, SyntaxError):
                return v
    return v


def author_name(a):
    a = lit(a)
    if isinstance(a, dict):
        return a.get("name")
    return a


def ts(s):
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def part_a(data):
    inj = json.loads((data / "injections_found.json").read_text(encoding="utf-8"))
    kws = []
    for r in inj:
        k = lit(r["matched_keywords"])
        kws.append([k] if isinstance(k, str) else list(k))

    dan_ww_cs = re.compile(r"\bDAN\b")
    dan_ww_ci = re.compile(r"\bdan\b", re.IGNORECASE)
    dan_word = re.compile(r"\w*dan\w*", re.IGNORECASE)

    dan = [(r, k) for r, k in zip(inj, kws) if "dan" in k]
    only_dan = [(r, k) for r, k in dan if set(k) == {"dan"}]
    only_yaa = [(r, k) for r, k in zip(inj, kws) if set(k) == {"you are a"}]
    non_generic = [(r, k) for r, k in zip(inj, kws) if set(k) - GENERIC]

    words_per_record = collections.Counter()
    words_occurrences = collections.Counter()
    for r, _ in dan:
        found = [w.lower() for w in dan_word.findall(r.get("text") or "")]
        words_occurrences.update(found)
        words_per_record.update(set(found))
    only_dan_words_per_record = collections.Counter()
    for r, _ in only_dan:
        only_dan_words_per_record.update({w.lower() for w in dan_word.findall(r.get("text") or "")})
    text_len = collections.Counter(len(r.get("text") or "") for r in inj)
    # the keyword scan may also have looked at the post title
    no_dan_in_text = sum(1 for r, _ in dan if not dan_word.search(r.get("text") or ""))

    kw_counter = collections.Counter(x for k in kws for x in set(k))
    return {
        "records": len(inj),
        "records_by_source": dict(collections.Counter(r.get("source") for r in inj)),
        "dan_matched_records": len(dan),
        "dan_whole_word_case_sensitive": sum(bool(dan_ww_cs.search(r.get("text") or "")) for r, _ in dan),
        "dan_whole_word_case_insensitive": sum(bool(dan_ww_ci.search(r.get("text") or "")) for r, _ in dan),
        "only_dan_records": len(only_dan),
        "only_dan_whole_word_case_sensitive": sum(bool(dan_ww_cs.search(r.get("text") or "")) for r, _ in only_dan),
        "only_dan_whole_word_case_insensitive": sum(bool(dan_ww_ci.search(r.get("text") or "")) for r, _ in only_dan),
        "dan_records_with_no_dan_substring_in_text": no_dan_in_text,
        "text_field_max_len": max(text_len),
        "records_with_text_len_500": text_len.get(500, 0),
        "top_dan_words_only_dan_records_records_containing": only_dan_words_per_record.most_common(15),
        "top_dan_words_records_containing": words_per_record.most_common(15),
        "top_dan_words_occurrences": words_occurrences.most_common(15),
        "only_you_are_a_records": len(only_yaa),
        "generic_keywords": sorted(GENERIC),
        "records_with_non_generic_keyword": len(non_generic),
        "records_only_generic_keywords": len(inj) - len(non_generic),
        "keyword_record_counts": dict(kw_counter.most_common()),
    }


def walk_comments(comments, out, post_id):
    for c in lit(comments) or []:
        c = lit(c)
        if not isinstance(c, dict):
            continue
        out.append({
            "kind": "comment",
            "thread": post_id,
            "id": c.get("id"),
            "author": author_name(c.get("author")),
            "t": ts(c.get("created_at")),
            "text": c.get("content") or "",
        })
        walk_comments(c.get("replies"), out, post_id)


def part_b(data):
    d = json.loads((data / "all_posts_with_comments.json").read_text(encoding="utf-8"))
    posts = d["posts"]
    items = []
    for p in posts:
        items.append({
            "kind": "post",
            "thread": p["id"],
            "id": p["id"],
            "author": author_name(p.get("author")),
            "t": ts(p.get("created_at")),
            "text": f"{p.get('title') or ''}\n{p.get('content') or ''}",
        })
        walk_comments(p.get("comments"), items, p["id"])

    n_items = len(items)
    authors = {i["author"] for i in items if i["author"]}
    missing_time = sum(i["t"] is None for i in items)

    broker_items = [i for i in items if i["author"] == BROKER]
    broker_first = {}
    for i in broker_items:
        if i["t"] is None:
            continue
        if i["thread"] not in broker_first or i["t"] < broker_first[i["thread"]]:
            broker_first[i["thread"]] = i["t"]
    broker_threads = {i["thread"] for i in broker_items}

    # exposure: an item by another author in a broker thread, after the broker's first item there
    first_exposure = {}
    for i in items:
        a = i["author"]
        if not a or a == BROKER or i["thread"] not in broker_first or i["t"] is None:
            continue
        if i["t"] > broker_first[i["thread"]]:
            if a not in first_exposure or i["t"] < first_exposure[a]:
                first_exposure[a] = i["t"]
    # looser: any item in a thread the broker ever posted in (regardless of order)
    first_in_broker_thread_any = {}
    for i in items:
        a = i["author"]
        if not a or a == BROKER or i["thread"] not in broker_threads or i["t"] is None:
            continue
        if a not in first_in_broker_thread_any or i["t"] < first_in_broker_thread_any[a]:
            first_in_broker_thread_any[a] = i["t"]

    first_mention = {}
    first_mention_item = {}
    for i in items:
        a = i["author"]
        if not a or a == BROKER or i["t"] is None:
            continue
        if "moltshell" in i["text"].lower():
            if a not in first_mention or i["t"] < first_mention[a]:
                first_mention[a] = i["t"]
                first_mention_item[a] = i
    mention_authors_any_time = {
        i["author"] for i in items
        if i["author"] and i["author"] != BROKER and "moltshell" in i["text"].lower()
    }

    exposed_before = {a for a in first_mention if a in first_exposure and first_exposure[a] < first_mention[a]}
    exposed_at_or_before = {a for a in first_mention if a in first_exposure and first_exposure[a] <= first_mention[a]}
    in_thread_before_any = {
        a for a in first_mention
        if a in first_in_broker_thread_any and first_in_broker_thread_any[a] < first_mention[a]
    }
    first_mention_in_broker_thread = sum(first_mention_item[a]["thread"] in broker_threads for a in first_mention)

    ever_exposed = {a for a in first_mention if a in first_exposure}

    def gap_stats(group):
        gaps_h = sorted((first_mention[a] - first_exposure[a]).total_seconds() / 3600 for a in group)
        if not gaps_h:
            return {}
        q = statistics.quantiles(gaps_h, n=10, method="inclusive") if len(gaps_h) > 1 else [gaps_h[0]] * 9
        return {
            "n": len(gaps_h),
            "median_hours": statistics.median(gaps_h),
            "median_minutes": statistics.median(gaps_h) * 60,
            "p10_hours": q[0],
            "p90_hours": q[-1],
            "min_hours": gaps_h[0],
            "max_hours": gaps_h[-1],
            "zero_gap": sum(g == 0 for g in gaps_h),
        }

    return {
        "posts": len(posts),
        "items_posts_plus_nested_comments": n_items,
        "distinct_authors": len(authors),
        "items_missing_created_at": missing_time,
        "broker_items": len(broker_items),
        "broker_threads": len(broker_threads),
        "other_authors_active_in_broker_threads_after_broker_first_item": len(first_exposure),
        "other_authors_active_in_broker_threads_any_time": len(first_in_broker_thread_any),
        "other_authors_mentioning_moltshell": len(mention_authors_any_time),
        "mentioners_ever_in_broker_thread_after_broker_no_time_check": len(ever_exposed),
        "mentioners_exposed_before_first_mention": len(exposed_before),
        "mentioners_exposed_at_or_before_first_mention": len(exposed_at_or_before),
        "mentioners_whose_first_mention_is_their_first_exposure": len(exposed_at_or_before - exposed_before),
        "mentioners_in_any_broker_thread_before_first_mention": len(in_thread_before_any),
        "mentioners_whose_first_mention_is_in_a_broker_thread": first_mention_in_broker_thread,
        "exposure_definition": "first item by the author in a thread where the broker already had an item (strictly later than the broker's first item there)",
        "time_first_exposure_to_first_mention_strictly_before": gap_stats(exposed_before),
        "time_first_exposure_to_first_mention_at_or_before": gap_stats(exposed_at_or_before),
    }


def main(data_dir, out_path):
    data = pathlib.Path(data_dir)
    stats = json.loads((data / "injection_stats.json").read_text(encoding="utf-8"))
    out = {
        "source": "https://huggingface.co/datasets/DavidTKeane/moltbook-ai-injection-dataset (CC BY 4.0)",
        "dataset_stats_header": {k: stats.get(k) for k in (
            "harvested_at", "total_posts_scanned", "total_comments_scanned", "total_items_scanned",
            "total_injection_records", "moltshellbroker_count")},
        "a_keyword_noise": part_a(data),
        "b_broker_spread": part_b(data),
    }
    pathlib.Path(out_path).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    a = dict(out["a_keyword_noise"])
    a.pop("keyword_record_counts")
    print(json.dumps({"a": a, "b": out["b_broker_spread"]}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
