"""Swarm Traces (swarmtraces.org) redacted release: blast-radius measures without timestamps.

Usage (from C:/Users/ndivij/backchannel):
    uv run python -I realdata/swarmtraces.py <redacted.jsonl.gz> [out.json]

The download is gzip-compressed JSONL (magic 1f 8b) even when shown as ".jsonl".
Rows are treated as untrusted text: nothing is decoded, executed or fetched; only
regex counts and hashes are computed. The output holds aggregates, category names,
and truncated sha256 hashes only - no payload text.

Agent identity: the public release redacts every agent_id value to the unnumbered
placeholder [REDACTED:runtime_identifier], so the ~7,905 self-chosen names the
authors mention are not recoverable. Actor proxies used here are the stable numbered
pseudonyms the redactor left in place:
  cred  - [CREDENTIAL n] in an auth context (Bearer / X-API-Key / Authorization / Basic btoa / token=)
  user  - [USER n]
  hfuser- [REDACTED:username:n]
A tree (root + decoded/response descendants) is attributed to an actor only when it
holds <= MAX_ACTORS_PER_TREE distinct pseudonyms of that type (bigger sets look like dumps).
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import re
import statistics
import sys

MAX_ACTORS_PER_TREE = 3

# Neutral technique categories: regexes over lower-cased text. Names describe the
# kind of activity only.
TECHNIQUES = {
    "js_http_request": r"xmlhttprequest|\bfetch\(|navigator\.sendbeacon",
    "js_dom_or_image_beacon": r"new image\b|document\.(?:body|createelement|cookie|location)|\.src\s*=",
    "decode_and_execute": r"(?:atob\(|b64decode|base64 -d|frombase64|base64\.decodebytes).{0,400}?(?:\beval\(|\bexec\(|new function|\|\s*(?:python3?|sh|bash)\b|compile\()|(?:\beval\(|\bexec\().{0,200}?(?:atob\(|b64decode)",
    "python_script": r"\bimport (?:os|sys|json|subprocess|socket|base64|urllib|requests|ssl|hashlib|time)\b|urllib\.request|python3? -c|python3? -\s",
    "shell_command": r"(?:^|[;&|`\s(])(?:curl|wget|bash|sh -c|chmod|nohup|mkdir|rm -rf|kill -9)\s",
    "hf_hub_access": r"huggingface\.co|\bhf\.co/|\[hf repo \d+\]|redacted:hf_repo|/api/(?:models|datasets|spaces)/",
    "dataset_card_yaml": r"(?m)^\s*(?:configs|data_files|dataset_info):",
    "container_registry": r"diff_ids|\"rootfs\"|\"mediatype\"|schemaversion|/v2/[^\s]{0,80}/(?:manifests|blobs)/|docker",
    "kubernetes_api": r"serviceaccount|/api/v1/namespaces|kubectl|impersonate-(?:group|user)|kube-?",
    "cloud_metadata_or_signing": r"169\.254\.169\.254|metadata\.google|x-amz-|amz-signature|aws_auth|sts\.amazonaws",
    "jwt_claims": r"\"(?:iat|exp|jti|nbf)\"\s*:|jwt_claim|\bjwt\b",
    "auth_header_use": r"\bbearer\s|x-api-key|authorization['\"]?\s*[:,=]",
    "template_injection": r"\{\{[^}]{0,80}__(?:class|mro|globals|subclasses|builtins|init)__",
    "media_playlist": r"#extm3u|#ext-x-",
    "native_code_or_memory": r"#include\s*<|\bmmap\(|map_private|memfd|io_uring|ioring_|handle_segv|asan_options|\bf_seal_",
    "board_zz_path": r"zz[a-z]{2,12}_",
    "artifact_store_path": r"artifactory|remote-cache/|github-remote/",
    "link_shortener_chain": r"\[shortener (?:code|url|link)|\[shortener-\d|\[redacted shortener",
    "env_or_secret_read": r"/proc/self/environ|os\.environ|printenv|\.aws/credentials|\.netrc|/secrets/|\.git-credentials|\bhf_token\b",
    "identity_recon": r"\bwhoami\b|\buname\b|\bhostname\b|/etc/passwd|\bifconfig\b|\bip addr\b|redacted:whoami_name",
    "reverse_shell_or_socket": r"/dev/tcp/|\bnc -e\b|\bsocat\b|pty\.spawn|socket\.socket\(",
    "persistence": r"crontab|systemctl|\.bashrc|authorized_keys|/etc/rc\.local",
    "path_traversal_or_file_url": r"\.\./\.\./|file://",
    "slack_api": r"slack",
    "bi_semantic_query": r"semanticquerydatashapecommand|executionmetricskind|powerbi",
    "swarm_task_record": r"\"(?:submitted_code|function_name|task_id|agent_id)\\?\"",
    "disarm_or_self_kill": r"disarm|kill -9 \$ppid|self-destruct",
    "webhook_or_callback": r"\[webhook|webhook|callback",
}
TECH_RE = {k: re.compile(v, re.S) for k, v in TECHNIQUES.items()}
TECH_DESC = {
    "js_http_request": "JavaScript HTTP request call",
    "js_dom_or_image_beacon": "JavaScript DOM access or image-src beacon",
    "decode_and_execute": "base64-style decode followed by eval/exec/pipe-to-interpreter",
    "python_script": "Python script (stdlib imports / urllib / python -c)",
    "shell_command": "shell command line (curl/wget/sh/chmod/...)",
    "hf_hub_access": "reference to the Hugging Face Hub or its API / redacted HF repo",
    "dataset_card_yaml": "dataset-card YAML config keys",
    "container_registry": "container image / registry manifest structures",
    "kubernetes_api": "Kubernetes API / service-account / impersonation",
    "cloud_metadata_or_signing": "cloud instance-metadata endpoint or AWS request signing",
    "jwt_claims": "JWT claim structures",
    "auth_header_use": "Authorization / Bearer / API-key header",
    "template_injection": "server-side template expression reaching Python dunder attributes",
    "media_playlist": "HLS media playlist directives",
    "native_code_or_memory": "C source / memory-mapping / sanitizer options",
    "board_zz_path": "zz-prefixed shared-store directory name",
    "artifact_store_path": "artifact-repository / remote-cache path",
    "link_shortener_chain": "link-shortener placeholder (chain hop)",
    "env_or_secret_read": "reading environment variables or credential files",
    "identity_recon": "identity / host reconnaissance (whoami, uname, hostname, passwd)",
    "reverse_shell_or_socket": "raw socket / interactive shell plumbing",
    "persistence": "cron / service / shell-rc / authorized_keys edits",
    "path_traversal_or_file_url": "dot-dot path traversal or file:// URL",
    "slack_api": "Slack reference",
    "bi_semantic_query": "BI semantic-query command structures",
    "swarm_task_record": "agent/task submission record (agent_id/task_id/submitted_code/function_name)",
    "disarm_or_self_kill": "disarm / self-kill wording",
    "webhook_or_callback": "webhook or callback reference",
}

CRED_AUTH = re.compile(
    r"(?i)(?:bearer\s+|x-api-key['\"]?\s*[:,]\s*['\"]|authorization['\"]?\s*[:,]\s*['\"](?:bearer\s+|token\s+)?|btoa\(['\"]|token=|token['\"]?\s*:\s*['\"])"
    r"\[CREDENTIAL (\d+)\]")
CRED_ANY = re.compile(r"\[CREDENTIAL (\d+)\]")
USER_RE = re.compile(r"\[USER (\d+)\]")
HFUSER_RE = re.compile(r"\[REDACTED:username:(\d+)\]")
PLACEHOLDER = re.compile(r"\[[A-Z][^\[\]\n]{0,80}\]")
BOARD_ANY = re.compile(r"zz[A-Z]{2,12}_")
BOARD_STRICT = re.compile(r"zz(?:INBOX|MODAL[A-Z]*|MAILBOX)_")


def gini(xs):
    xs = sorted(x for x in xs)
    n = len(xs)
    s = sum(xs)
    if n == 0 or s == 0:
        return None
    cum = 0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return round((2 * cum) / (n * s) - (n + 1) / n, 4)


def dist(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"n": len(xs), "mean": round(sum(xs) / len(xs), 3), "median": statistics.median(xs),
            "p90": q(0.9), "p99": q(0.99), "max": xs[-1]}


def norm(t):
    t = PLACEHOLDER.sub("<R>", t)
    t = re.sub(r"\s+", " ", t.lower()).strip()
    return t


def h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load(path):
    opener = gzip.open if open(path, "rb").read(2) == b"\x1f\x8b" else open
    rows = []
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main(path, out_path):
    rows = load(path)
    n = len(rows)
    byid = {r["id"]: r for r in rows}

    # ---------- 1. schema ----------
    kinds = collections.Counter(r["kind"] for r in rows)
    fields = sorted({k for r in rows for k in r})
    fill = {}
    for k in fields:
        filled = sum(1 for r in rows if r.get(k) not in (None, "", [], {}))
        fill[k] = {"filled": filled, "rate": round(filled / n, 5)}
    tagc = collections.Counter()
    tag_rows_by_kind = collections.Counter()
    for r in rows:
        if r.get("tags"):
            tag_rows_by_kind[r["kind"]] += 1
            tagc.update(t for t in r["tags"].split(";") if t)
    cite_ok = sum(1 for r in rows if r["cite"] == f"{r['id']}:{h(r['text'])[:8]}")
    id_nums = [int(r["id"][1:]) for r in rows]
    # file layout: runs of kind
    runs = []
    for r in rows:
        if not runs or runs[-1][0] != r["kind"]:
            runs.append([r["kind"], r["id"], 0])
        runs[-1][2] += 1
    redaction_cats = collections.Counter()
    for r in rows:
        redaction_cats.update(set(m.group(1) for m in re.finditer(r"\[REDACTED:([a-z_]+)", r["text"])))

    schema = {
        "rows": n,
        "rows_by_kind": dict(kinds),
        "fields": fields,
        "field_fill": fill,
        "time_utc_non_null": sum(r.get("time_utc") is not None for r in rows),
        "tags": {
            "rows_with_any_tag": sum(tag_rows_by_kind.values()),
            "rows_with_tag_by_kind": dict(tag_rows_by_kind),
            "separator": ";",
            "distinct_tags": len(tagc),
            "top30": tagc.most_common(30),
            "note": "tags mark article-evidence rows only; they are not a technique taxonomy",
        },
        "cite_format": "'<id>:<8 hex>' where the hex is sha256(text)[:8] (verified on all rows)" if cite_ok == n else f"id:8hex; sha256(text)[:8] matched {cite_ok}/{n}",
        "cite_matches_sha256_text_prefix": cite_ok,
        "id_format": "R + 7-digit zero-padded integer",
        "id_contiguous_1_to_n": id_nums == list(range(1, n + 1)),
        "file_layout_kind_runs": [{"kind": k, "first_id": i, "rows": c} for k, i, c in runs],
        "rows_with_redaction_category_top": redaction_cats.most_common(25),
    }

    # ---------- 2. forest ----------
    children = collections.defaultdict(list)
    for r in rows:
        if r.get("parent_id"):
            children[r["parent_id"]].append(r["id"])
    missing_parent = sum(1 for r in rows if r.get("parent_id") and r["parent_id"] not in byid)
    pair = collections.Counter()
    child_before_parent = 0
    for r in rows:
        p = r.get("parent_id")
        if p and p in byid:
            pair[f"{byid[p]['kind']}->{r['kind']}"] += 1
            child_before_parent += int(r["id"][1:]) < int(p[1:])
    roots = [r["id"] for r in rows if not r.get("parent_id")]
    tree_of = {}
    depth_of = {}
    tree_size = {}
    tree_depth = {}
    for root in roots:
        stack = [(root, 0)]
        size = 0
        md = 0
        while stack:
            x, d = stack.pop()
            tree_of[x] = root
            depth_of[x] = d
            size += 1
            md = max(md, d)
            for c in children.get(x, ()):
                stack.append((c, d + 1))
        tree_size[root] = size
        tree_depth[root] = md
    unreached = n - len(tree_of)
    fan = [len(v) for v in children.values()]
    sizes = list(tree_size.values())
    multi = [s for s in sizes if s > 1]
    # containment evidence: child text appears inside parent text
    contained50 = collections.Counter()
    for pid, cs in children.items():
        pt = byid[pid]["text"]
        for c in cs:
            ct = byid[c]["text"]
            contained50[f"{byid[c]['kind']}:{'yes' if ct[:50] in pt else 'no'}"] += 1
    child_kind_mix = collections.Counter(
        "+".join(sorted({byid[c]["kind"] for c in cs})) for cs in children.values())
    forest = {
        "rows_with_parent": sum(1 for r in rows if r.get("parent_id")),
        "parent_missing_from_file": missing_parent,
        "parent_kind_to_child_kind": dict(pair),
        "child_id_less_than_parent_id": child_before_parent,
        "trees": len(roots),
        "roots_by_kind": dict(collections.Counter(byid[x]["kind"] for x in roots)),
        "rows_not_reached_from_a_root": unreached,
        "tree_size_all": dist(sizes),
        "tree_size_multi_row_trees": dist(multi),
        "trees_with_children": len(multi),
        "tree_depth_counts": dict(sorted(collections.Counter(tree_depth.values()).items())),
        "max_depth": max(tree_depth.values()),
        "share_trees_depth_ge1": round(sum(d >= 1 for d in tree_depth.values()) / len(roots), 5),
        "share_trees_depth_ge2": round(sum(d >= 2 for d in tree_depth.values()) / len(roots), 7),
        "fanout_of_parents": dist(fan),
        "fanout_histogram_capped_20": dict(sorted(collections.Counter(min(f, 20) for f in fan).items())),
        "parents_by_child_kind_mix": dict(child_kind_mix),
        "child_first50_chars_found_in_parent_text": dict(contained50),
        "interpretation": "parent_id links a reassembled payload to (a) recovered_text rows = decoded layers / extracted fragments of that payload and (b) response rows = content returned when the payload's link chain was followed. Links never connect one payload to another payload, so trees are intra-payload decompositions, not agent-to-agent cascades.",
    }

    # ---------- 3. techniques & actors ----------
    row_tech = {}
    row_cred_auth = {}
    row_cred_any = {}
    row_user = {}
    row_hfuser = {}
    for r in rows:
        t = r["text"]
        tl = t.lower()
        row_tech[r["id"]] = {k for k, rx in TECH_RE.items() if rx.search(tl)}
        row_cred_auth[r["id"]] = set(CRED_AUTH.findall(t))
        row_cred_any[r["id"]] = set(CRED_ANY.findall(t))
        row_user[r["id"]] = set(USER_RE.findall(t))
        row_hfuser[r["id"]] = set(HFUSER_RE.findall(t))
    members = collections.defaultdict(list)
    for x, root in tree_of.items():
        members[root].append(x)

    def tree_union(dct, root):
        s = set()
        for x in members[root]:
            s |= dct[x]
        return s

    tree_tech = {root: tree_union(row_tech, root) for root in roots}
    actor_maps = {
        "cred": {root: tree_union(row_cred_auth, root) for root in roots},
        "user": {root: tree_union(row_user, root) for root in roots},
        "hfuser": {root: tree_union(row_hfuser, root) for root in roots},
    }

    row_level = {k: sum(1 for x in row_tech if k in row_tech[x]) for k in TECHNIQUES}
    row_level_payload = {k: sum(1 for r in rows if r["kind"] == "payload" and k in row_tech[r["id"]]) for k in TECHNIQUES}
    tree_level = {k: sum(1 for root in roots if k in tree_tech[root]) for k in TECHNIQUES}

    def actor_stats(name, amap, max_k):
        attributed = {root: a for root, a in amap.items() if 1 <= len(a) <= max_k}
        dumps = sum(1 for a in amap.values() if len(a) > max_k)
        universe = set()
        for a in attributed.values():
            universe |= a
        per_actor_trees = collections.Counter()
        for a in attributed.values():
            for x in a:
                per_actor_trees[x] += 1
        tech_stats = {}
        for k in TECHNIQUES:
            use = collections.Counter()
            for root, a in attributed.items():
                if k in tree_tech[root]:
                    for x in a:
                        use[x] += 1
            users = len(use)
            tech_stats[k] = {
                "attributed_trees": sum(1 for root, a in attributed.items() if k in tree_tech[root]),
                "distinct_actors": users,
                "reach_share_of_actors": round(users / len(universe), 4) if universe else None,
                "gini_among_users": gini(use.values()),
                "gini_over_all_actors": gini(list(use.values()) + [0] * (len(universe) - users)),
            }
        return {
            "attribution_rule": f"tree holds 1..{max_k} distinct pseudonyms of this type",
            "trees_with_any": sum(1 for a in amap.values() if a),
            "trees_attributed": len(attributed),
            "trees_excluded_too_many_pseudonyms": dumps,
            "distinct_actors_attributed": len(universe),
            "trees_per_actor": dist(list(per_actor_trees.values())),
            "gini_trees_per_actor": gini(per_actor_trees.values()),
            "top10_actor_tree_counts": [c for _, c in per_actor_trees.most_common(10)],
            "top5_actor_share_of_attributed_trees": round(sum(c for _, c in per_actor_trees.most_common(5)) / max(1, len(attributed)), 4),
            "techniques": dict(sorted(tech_stats.items(), key=lambda kv: -kv[1]["distinct_actors"])),
        }

    actors_out = {}
    for name, amap in actor_maps.items():
        actors_out[name] = {
            "strict_single_pseudonym": actor_stats(name, amap, 1),
            "lenient_le3_pseudonyms": actor_stats(name, amap, MAX_ACTORS_PER_TREE),
        }
    # what kind of auth context each credential pseudonym appears in
    ctx_rx = {
        "bearer": re.compile(r"(?i)bearer\s+\[CREDENTIAL (\d+)\]"),
        "x_api_key": re.compile(r"(?i)x-api-key['\"]?\s*[:,]\s*['\"]\[CREDENTIAL (\d+)\]"),
        "basic_btoa": re.compile(r"(?i)btoa\(['\"]\[CREDENTIAL (\d+)\]"),
        "token_param_or_field": re.compile(r"(?i)token(?:=|['\"]?\s*:\s*['\"])\[CREDENTIAL (\d+)\]"),
    }
    cred_ctx = collections.defaultdict(collections.Counter)
    for r in rows:
        for cname, rx in ctx_rx.items():
            for c in rx.findall(r["text"]):
                cred_ctx[c][cname] += 1
    strict_c = {root: a for root, a in actor_maps["cred"].items() if len(a) == 1}
    per_c = collections.Counter(next(iter(a)) for a in strict_c.values())
    hf_share = {}
    for c in per_c:
        hf_share[c] = 0
    for root, a in strict_c.items():
        if "hf_hub_access" in tree_tech[root]:
            hf_share[next(iter(a))] += 1
    top10 = [c for c, _ in per_c.most_common(10)]
    cred_profile = {
        "credentials_by_dominant_auth_context": dict(collections.Counter(
            cred_ctx[c].most_common(1)[0][0] for c in cred_ctx)),
        "top10_strict_cred_trees_and_context": [
            {"rank": i + 1, "trees": per_c[c], "dominant_context": cred_ctx[c].most_common(1)[0][0] if cred_ctx[c] else None,
             "share_trees_with_hf_hub_access": round(hf_share[c] / per_c[c], 3)}
            for i, c in enumerate(top10)],
        "strict_creds_with_le2_trees": sum(1 for v in per_c.values() if v <= 2),
        "strict_creds_with_le2_trees_all_hf_hub": sum(1 for c, v in per_c.items() if v <= 2 and hf_share[c] == v),
        "note": "long-tail credentials used once or twice against the Hub look like harvested/tested tokens rather than agent identities",
    }
    cred_rows_any = sum(1 for x in row_cred_any if row_cred_any[x])
    cred_rows_auth = sum(1 for x in row_cred_auth if row_cred_auth[x])

    # ---------- 3b. duplicates / copying ----------
    def dup_groups(keyfn, scope_rows):
        g = collections.defaultdict(list)
        for r in scope_rows:
            g[keyfn(r)].append(r["id"])
        return g

    def summarize_groups(g, label):
        multi_g = {k: v for k, v in g.items() if len(v) >= 2}
        out = {
            "groups": len(g),
            "groups_with_ge2_rows": len(multi_g),
            "rows_in_ge2_groups": sum(len(v) for v in multi_g.values()),
            "max_rows_in_group": max((len(v) for v in g.values()), default=0),
        }
        # copying = the same (normalized) text in >=2 distinct trees whose single actor pseudonyms differ
        for aname in ("cred", "user", "hfuser"):
            amap = actor_maps[aname]
            per = []
            for k, ids in g.items():
                trees = {tree_of[x] for x in ids}
                actors = set()
                if len(trees) >= 2:
                    for t in trees:
                        a = amap[t]
                        if len(a) == 1:
                            actors |= a
                per.append(len(actors))
            out[f"groups_shared_by_ge2_{aname}"] = sum(p >= 2 for p in per)
            out[f"groups_shared_by_ge5_{aname}"] = sum(p >= 5 for p in per)
            out[f"groups_shared_by_ge20_{aname}"] = sum(p >= 20 for p in per)
            out[f"max_distinct_{aname}_per_group"] = max(per, default=0)
        # distinct trees per group (same content re-sent in separate reassembled payloads)
        tr = [len({tree_of[x] for x in ids}) for ids in g.values()]
        out["groups_in_ge2_trees"] = sum(t >= 2 for t in tr)
        out["groups_in_ge5_trees"] = sum(t >= 5 for t in tr)
        out["groups_in_ge20_trees"] = sum(t >= 20 for t in tr)
        out["max_trees_per_group"] = max(tr, default=0)
        return out

    payload_rows = [r for r in rows if r["kind"] == "payload"]
    root_rows = [byid[x] for x in roots]
    nonempty = lambda r: len(norm(r["text"])) >= 20
    dup = {}
    for scope_name, scope in (("payload_rows", payload_rows), ("all_roots", root_rows), ("all_rows", rows)):
        sc = [r for r in scope if nonempty(r)]
        dup[scope_name] = {
            "rows_considered_norm_len_ge20": len(sc),
            "exact_text_sha256": summarize_groups(dup_groups(lambda r: h(r["text"]), sc), "exact"),
            "normalized_template": summarize_groups(dup_groups(lambda r: h(norm(r["text"])), sc), "norm"),
            "normalized_first200": summarize_groups(dup_groups(lambda r: h(norm(r["text"])[:200]), sc), "first200"),
        }
    # top reused templates among payload rows by distinct credential pseudonyms
    g = dup_groups(lambda r: h(norm(r["text"])), [r for r in payload_rows if nonempty(r)])
    top = []
    for k, ids in g.items():
        creds = set()
        trees = {tree_of[x] for x in ids}
        if len(trees) >= 2:
            for t in trees:
                a = actor_maps["cred"][t]
                if len(a) == 1:
                    creds |= a
        top.append((len(creds), len(ids), k, ids))
    top.sort(reverse=True)
    dup["top15_payload_templates_by_distinct_cred"] = [
        {"template_sha256_8": k[:8], "distinct_cred": c, "rows": nr,
         "norm_len": len(norm(byid[ids[0]]["text"])),
         "techniques": sorted(tree_tech[tree_of[ids[0]]])}
        for c, nr, k, ids in top[:15]]
    # template reach in technique terms: for each technique, max distinct creds sharing one template
    tech_tpl = {}
    for k in TECHNIQUES:
        best = 0
        n_ge2 = 0
        for c, nr, key, ids in top:
            if k in row_tech[ids[0]]:
                best = max(best, c)
                n_ge2 += c >= 2
        tech_tpl[k] = {"templates_shared_by_ge2_cred": n_ge2, "max_cred_on_one_template": best}
    dup["per_technique_template_sharing_cred"] = dict(sorted(tech_tpl.items(), key=lambda kv: -kv[1]["max_cred_on_one_template"]))

    # ---------- 4. board touch ----------
    def board(rx):
        rset = [r for r in rows if rx.search(r["text"])]
        trees = {tree_of[r["id"]] for r in rset}
        res = {"rows": len(rset), "rows_by_kind": dict(collections.Counter(r["kind"] for r in rset)), "trees": len(trees)}
        for aname in ("cred", "user", "hfuser"):
            amap = actor_maps[aname]
            universe = set()
            for a in amap.values():
                if len(a) == 1:
                    universe |= a
            touched = set()
            for t in trees:
                a = amap[t]
                if len(a) == 1:
                    touched |= a
            res[f"distinct_{aname}"] = len(touched)
            res[f"share_of_all_{aname}"] = round(len(touched) / len(universe), 4) if universe else None
        return res

    zz_tokens = collections.Counter()
    zz_prefix = collections.Counter()
    for r in rows:
        zz_tokens.update(set(re.findall(r"zz[A-Z]{2,12}_[A-Za-z0-9_.\-]{0,60}", r["text"])))
        zz_prefix.update(set(re.findall(r"zz[A-Z]{2,12}_", r["text"])))
    board_out = {
        "strict_inbox_modal_mailbox": board(BOARD_STRICT),
        "any_zz_prefix_dir": board(BOARD_ANY),
        "artifact_store_mention": board(re.compile(r"(?i)artifactory|remote-cache/|github-remote/")),
        "zz_prefix_rows_top": zz_prefix.most_common(20),
        "distinct_zz_tokens": len(zz_tokens),
        "note": "zz token stems look like per-target/task labels (e.g. fuzz-target style names), not agent names",
    }

    # ---------- 5. ordering signals ----------
    def mono(rx):
        seq = []
        for r in rows:
            m = rx.search(r["text"])
            if m:
                seq.append(int(m.group(1)))
        inc = sum(b >= a for a, b in zip(seq, seq[1:]))
        first_seen = []
        seen = set()
        for v in seq:
            if v not in seen:
                seen.add(v)
                first_seen.append(v)
        fs_inc = sum(b > a for a, b in zip(first_seen, first_seen[1:]))
        return {"rows": len(seq), "share_nondecreasing_adjacent": round(inc / max(1, len(seq) - 1), 4),
                "share_increasing_first_seen_order": round(fs_inc / max(1, len(first_seen) - 1), 4)}

    http_date = re.compile(r"(?im)^\s*date:\s*(?:mon|tue|wed|thu|fri|sat|sun), \d{1,2} [a-z]{3} \d{4}")
    iso_date = re.compile(r"\b20(?:2[4-7])-\d{2}-\d{2}")
    epoch = re.compile(r"(?<!\d)17[5-9]\d{7}(?!\d)")
    ordering = {
        "ids": "R0000001..R%07d contiguous; file is laid out in batches, each ordered payload -> response -> recovered_text, so id order is export order, not time" % n,
        "kind_runs": len(runs),
        "placeholder_numbering_vs_file_order": {
            "ENCODED_BLOB": mono(re.compile(r"\[ENCODED BLOB (\d+)\]")),
            "SHORTENER_CODE": mono(re.compile(r"\[SHORTENER CODE (\d+)\]")),
            "destination": mono(re.compile(r"\[REDACTED:destination:(\d+)\]")),
        },
        "in_text_time_signals_rows": {
            "http_date_header": sum(1 for r in rows if http_date.search(r["text"])),
            "iso_date_2024_2027": sum(1 for r in rows if iso_date.search(r["text"])),
            "epoch_seconds_like_175_179e7": sum(1 for r in rows if epoch.search(r["text"])),
            "redacted_jwt_claim_time_rows": sum(1 for r in rows if "[REDACTED:jwt_claim_time" in r["text"]),
        },
        "in_text_time_signals_payload_rows": {
            "http_date_header": sum(1 for r in payload_rows if http_date.search(r["text"])),
            "iso_date_2024_2027": sum(1 for r in payload_rows if iso_date.search(r["text"])),
            "epoch_seconds_like_175_179e7": sum(1 for r in payload_rows if epoch.search(r["text"])),
        },
    }
    iso_months = collections.Counter()
    for r in rows:
        for m in re.findall(r"\b(20(?:2[4-7])-\d{2})-\d{2}", r["text"]):
            iso_months[m] += 1
    ordering["iso_date_year_month_occurrences"] = dict(sorted(iso_months.items()))
    ep_months = collections.Counter()
    ep_trees = set()
    for r in rows:
        for m in epoch.findall(r["text"]):
            ep_months[dt.datetime.fromtimestamp(int(m), dt.timezone.utc).strftime("%Y-%m")] += 1
        if epoch.search(r["text"]):
            ep_trees.add(tree_of[r["id"]])
    ordering["epoch_like_value_months_utc"] = dict(sorted(ep_months.items()))
    ordering["trees_with_epoch_like_value"] = len(ep_trees)
    # coarse timeline: trees whose earliest epoch-like value (s or ms) falls 2026-06-01..2026-08-31 UTC
    lo = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc).timestamp()
    hi = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp()
    epoch_ms = re.compile(r"(?<!\d)(17[5-9]\d{10})(?!\d)")
    tree_t = {}
    for r in rows:
        vals = [int(v) for v in epoch.findall(r["text"])] + [int(v) / 1000 for v in epoch_ms.findall(r["text"])]
        vals = [v for v in vals if lo <= v < hi]
        if vals:
            t = tree_of[r["id"]]
            tree_t[t] = min(vals + ([tree_t[t]] if t in tree_t else []))
    day = lambda s: dt.datetime.fromtimestamp(s, dt.timezone.utc).strftime("%Y-%m-%d")
    per_day = collections.Counter(day(v) for v in tree_t.values())
    tl = {}
    for k in TECHNIQUES:
        ts = sorted(v for t, v in tree_t.items() if k in tree_tech[t])
        if ts:
            tl[k] = {"dated_trees": len(ts), "first_day": day(ts[0]), "median_day": day(ts[len(ts) // 2]),
                     "last_day": day(ts[-1])}
    strict_cred_dated = {}
    for t, v in tree_t.items():
        a = actor_maps["cred"][t]
        if len(a) == 1:
            c = next(iter(a))
            strict_cred_dated.setdefault(c, []).append(v)
    ordering["dated_trees_jun_aug_2026"] = {
        "trees": len(tree_t),
        "share_of_trees": round(len(tree_t) / len(roots), 5),
        "trees_per_day": dict(sorted(per_day.items())),
        "per_technique_first_median_last_day": dict(sorted(tl.items(), key=lambda kv: kv[1]["first_day"])),
        "strict_cred_pseudonyms_with_dated_trees": len(strict_cred_dated),
        "caveat": "epoch-like 10/13-digit integers inside text (request params, cache-busters, build or expiry times); authors call recovered dates best estimates",
    }
    ordering["trees_with_any_time_signal"] = len(ep_trees | {tree_of[r["id"]] for r in rows if iso_date.search(r["text"]) or http_date.search(r["text"])})

    out = {
        "source": "https://swarmtraces.org/ (redacted.jsonl.gz, gzip JSONL)",
        "input_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
        "safety": "aggregates only; no payload text, URLs, credentials or names; template ids are sha256 prefixes of normalized text",
        "1_schema": schema,
        "2_forest": forest,
        "3_actor_proxies": {
            "agent_names_available": False,
            "agent_id_values": "every agent_id value is the unnumbered [REDACTED:runtime_identifier]",
            "rows_with_any_CREDENTIAL_placeholder": cred_rows_any,
            "rows_with_CREDENTIAL_in_auth_context": cred_rows_auth,
            "rows_with_USER_placeholder": sum(1 for x in row_user if row_user[x]),
            "rows_with_hf_username_pseudonym": sum(1 for x in row_hfuser if row_hfuser[x]),
            "max_actors_per_tree_for_attribution": MAX_ACTORS_PER_TREE,
            "technique_definitions": TECH_DESC,
            "technique_definition_method": "case-insensitive regex per category over row text (see TECHNIQUES in realdata/swarmtraces.py); a tree uses a category if any of its rows matches",
            "technique_rows_all_kinds": dict(sorted(row_level.items(), key=lambda kv: -kv[1])),
            "technique_rows_payload_kind": dict(sorted(row_level_payload.items(), key=lambda kv: -kv[1])),
            "technique_trees": dict(sorted(tree_level.items(), key=lambda kv: -kv[1])),
            "by_proxy": actors_out,
            "credential_profile": cred_profile,
        },
        "3b_duplicates": dup,
        "4_board": board_out,
        "5_ordering": ordering,
    }
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")

    brief = {
        "rows": n, "kinds": dict(kinds), "trees": len(roots), "forest": {k: forest[k] for k in (
            "tree_size_multi_row_trees", "max_depth", "share_trees_depth_ge1", "fanout_of_parents", "parent_kind_to_child_kind")},
        "actors_strict": {a: {k: v for k, v in actors_out[a]["strict_single_pseudonym"].items() if k != "techniques"}
                          for a in actors_out},
        "cred_profile": cred_profile,
        "cred_strict_top_techniques": dict(list(actors_out["cred"]["strict_single_pseudonym"]["techniques"].items())[:12]),
        "dup_payload": dup["payload_rows"],
        "board": {k: board_out[k] for k in ("strict_inbox_modal_mailbox", "any_zz_prefix_dir", "artifact_store_mention")},
        "ordering": {k: v for k, v in ordering.items() if k != "iso_date_year_month_occurrences"},
    }
    print(json.dumps(brief, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(pathlib.Path(__file__).parent / "results" / "swarmtraces.json"))
