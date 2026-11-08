"""Assemble the report from paper/sections/*.md into paper/backchannel.html and print it to PDF with Chrome.

  uv run python paper/build.py
Prints the word count of the abstract, the page count of the main text and of the whole PDF, and any
[[PLACEHOLDER]] still left in the text.
"""
import json
import re
import subprocess
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SEC = HERE / "sections"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TITLE = "One Warning Away: Correction, Not Infection, Sets the Blast Radius of Exploits in Agent Swarms"
AUTHORS = "N. Divij &middot; [[AFFILIATION]]"
_stats = json.loads((HERE.parent / "figures" / "stats.json").read_text(encoding="utf-8"))
VALUES = {"[[CALLS]]": f"{_stats['spend']['calls']:,}", "[[COST]]": f"${round(_stats['spend']['usd'])}",
          "[[FAILED]]": str(_stats["failed_calls"]), "[[FALLBACK]]": f"{_stats['fallback_turns']['total']:,}"}


def _results_values(s):
    """Every result number in the text that depends on the evening's runs, computed from figures/stats.json."""
    cf, arms = s["cf"], s["arms"]
    fin = lambda p: [r["final"] for r in cf.get(p, [])]
    peak = lambda p: [r["peak"] for r in cf.get(p, [])]
    seed = lambda p, k: [r["final"] for r in cf.get(p, []) if r["run"].endswith(f"-s{k}")]
    lst = lambda xs: ", ".join(map(str, xs[:-1])) + (" and " if len(xs) > 1 else "") + str(xs[-1]) if xs else "–"
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    w2, nt = fin("leak-cf-warn-r2"), fin("leak-cf-neutral-r2")
    s4, s6, s7 = fin("leak-cf-silence4"), fin("leak-cf-silence6"), fin("leak-cf-silence7")
    rb = fin("leak-cf-rebut3")
    orig_rb = [1, 1, 0, 0, 0, 0, 0, 0, 0]
    worse = [(i + 1, f, o) for i, (f, o) in enumerate(zip(rb, orig_rb)) if f > o + 1]
    rebut = (f"{len(rb) - len(worse)} of the {len(rb)} recovered swarms stayed recovered, but in "
             + "; ".join(f"seed {k} {f} of 9 agents ended on the leak, against {o}" for k, f, o in worse)
             + f" ({sum(rb)} of {9 * len(rb)} agents in all, against {sum(orig_rb[:len(rb)])}): an influencer that "
             "answers back usually loses, but not always") if worse else (
             f"every recovered swarm stayed recovered ({sum(rb)} of {9 * len(rb)} agents, against {sum(orig_rb[:len(rb)])})")
    a = lambda k, f: arms[k][f] if k in arms else 0
    rw, rs = "leak-reward", "leak-star-hub-reward"
    v = {
        "[[WARN_R2]]": f"no agent on the leak in {w2.count(0)} of {len(w2)} replicates"
                       + (f" ({lst([x for x in w2 if x])} in the others)" if any(w2) else "") + ", against 9 of 9 originally",
        "[[NEUTRAL]]": f"{lst(nt)} of 9 ({len(nt)} replicates)",
        "[[TIMING]]": "a mean of {:.1f} agents on the leak after a round-3 warning, {:.1f} after round 4 and {:.1f} "
                      "after round 6".format(mean(fin("leak-cf-warn-r3")), mean(fin("leak-cf-warn-r4")), mean(fin("leak-cf-warn-r6"))),
        "[[SILENCE4]]": f"a locked-in one in {sum(x >= 7 for x in s4)} of {len(s4)} replicates ({lst(s4)} of 9 at the end)",
        "[[SILENCE6]]": f"{lst(s6)} of 9",
        "[[SILENCE7]]": f"{lst(peak('leak-cf-silence7'))} agents ({lst(s7)} at the end)",
        "[[REBUT]]": rebut,
        "[[NOGOSSIP0]]": f"{lst(seed('leak-cf-nogossip', 0))} of 9",
        "[[QHUB]]": f"{a('leak-star-leaf-qhub', 'final')} of {a('leak-star-leaf-qhub', 'agents')} ended on it",
        "[[SYNC]]": f"{a('leak-sync', 'final')} of {a('leak-sync', 'agents')}",
        "[[INTRO_SYNC]]": f"{a('leak-sync', 'final')} of {a('leak-sync', 'agents')} agents",
        "[[SYNCV]]": f"{a('leak-sync-verified', 'final')} of {a('leak-sync-verified', 'agents')}",
        "[[SYNC_ROW]]": f"{a('leak-sync', 'seeds')} | {a('leak-sync', 'tried')}/{a('leak-sync', 'agents')} | "
                        f"{a('leak-sync', 'final')}/{a('leak-sync', 'agents')}",
        "[[SYNCV_ROW]]": f"{a('leak-sync-verified', 'seeds')} | {a('leak-sync-verified', 'tried')}/"
                         f"{a('leak-sync-verified', 'agents')} | {a('leak-sync-verified', 'final')}/{a('leak-sync-verified', 'agents')}",
        "[[SYNC_SILENT]]": f"{s.get('sync_silent', ['?', '?'])[0]} of the {s.get('sync_silent', ['?', '?'])[1]}",
        "[[INTRO_CF]]": f"{w2.count(0)} of {len(w2)} replicates cleared; 0 of {len(nt)} with the neutral post"
                        if all(x >= 7 for x in nt) else f"warning {lst(w2)}, neutral {lst(nt)}",
        "[[HIDDEN]]": f"{a('leak-hidden', 'tried')} of {a('leak-hidden', 'agents')}",
        "[[REWARD_N]]": str(a(rw, "seeds")), "[[REWARD_TRIED]]": f"{a(rw, 'tried')}/{a(rw, 'agents')}",
        "[[REWARD_FINAL]]": f"{a(rw, 'final')}/{a(rw, 'agents')}",
        "[[RECEIPTS_N]]": str(a("leak-receipts", "seeds")),
        "[[RECEIPTS_TRIED]]": f"{a('leak-receipts', 'tried')}/{a('leak-receipts', 'agents')}",
        "[[RECEIPTS_FINAL]]": f"{a('leak-receipts', 'final')}/{a('leak-receipts', 'agents')}",
        "[[RECEIPTS_PCT]]": f"{a('leak-receipts', 'tried') / max(1, a('leak-receipts', 'agents')):.0%}",
        "[[REWARD_TEXT]]": (f"On the open board {a(rw, 'tried')} of {a(rw, 'agents')} agents ran the leak and "
                            f"{a(rw, 'final')} ended on it ({a(rw, 'seeds')} swarms; 60 of 90 and 11 of 90 without). With "
                            f"the bad apple at a star's hub, where no warning can travel, {a(rs, 'final')} of "
                            f"{a(rs, 'agents')} ended on it against 21 of 27 ({a(rs, 'seeds')} swarms), and agents filed "
                            f"{a(rs, 'reports')} reports to the operator, which no one in the sandbox acts on. Small "
                            "samples; the reward is worth testing with an operator who responds."),
    }
    return v


VALUES.update(_results_values(_stats))
MAIN = ["intro_related", "method", "results", "realdata_limits", "conclusion"]
BACK = ["references", "appendix", "appendix_tables", "appendix_texts"]

CSS = """
@page { size: Letter; margin: 0.75in 0.85in; }
body { font-family: "Times New Roman", Georgia, serif; font-size: 10pt; line-height: 1.26; color: #111;
       background: #fff; max-width: 6.8in; margin: 0 auto; }
h1 { font-family: Arial, Helvetica, sans-serif; font-size: 16pt; line-height: 1.2; margin: 0 0 6pt; }
h2 { font-family: Arial, Helvetica, sans-serif; font-size: 12pt; margin: 14pt 0 4pt; }
h3 { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; margin: 10pt 0 3pt; }
h2, h3 { break-after: avoid; }
p { margin: 0 0 6pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 6pt; padding-left: 18pt; } li { margin: 0 0 2pt; }
.authors { font-size: 10.5pt; margin-bottom: 10pt; color: #333; }
.abstract { margin: 0 0.3in 12pt; font-size: 10pt; }
.abstract h2 { font-size: 10.5pt; text-align: center; margin: 0 0 4pt; }
img { display: block; width: 100%; margin: 6pt 0 2pt; break-inside: avoid; }
p:has(> img) { break-inside: avoid; margin: 0; }
p:has(> img) + p > em:only-child { display: block; }
em { font-style: italic; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 4pt 0 8pt; break-inside: avoid; }
th, td { border-top: 0.5pt solid #bbb; border-bottom: 0.5pt solid #bbb; padding: 2pt 4pt; text-align: left;
         vertical-align: top; }
th { background: #f2f2f2; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; }
.back { break-before: page; }
.back p { text-align: left; }
"""


def md(name):
    text = (SEC / f"{name}.md").read_text(encoding="utf-8")
    for k, v in VALUES.items():
        text = text.replace(k, v)
    return markdown.markdown(text, extensions=["tables"])


def page(parts, back=True):
    abstract = md("abstract")
    body = "\n".join(md(p) for p in MAIN)
    tail = f'<div class="back">{"".join(md(p) for p in BACK if (SEC / f"{p}.md").exists())}</div>' if back else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{TITLE}</title><style>{CSS}</style></head>'
            f'<body><h1>{TITLE}</h1><div class="authors">{AUTHORS}</div>'
            f'<div class="abstract"><h2>Abstract</h2>{abstract}</div>{body}{tail}</body></html>')


def pdf(html_path, pdf_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()], check=True, capture_output=True)
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf_path.read_bytes()))


if __name__ == "__main__":
    full, main = HERE / "backchannel.html", HERE / "_main_only.html"
    full.write_text(page(MAIN), encoding="utf-8")
    main.write_text(page(MAIN, back=False), encoding="utf-8")
    n_full = pdf(full, HERE / "backchannel.pdf")
    n_main = pdf(main, HERE / "_main_only.pdf")
    words = len(re.findall(r"\S+", (SEC / "abstract.md").read_text(encoding="utf-8")))
    left = sorted(set(re.findall(r"\[\[[^\]]+\]\]", full.read_text(encoding="utf-8"))))
    print(f"abstract {words} words; main text {n_main} pages; whole PDF {n_full} pages; placeholders left: {left}")
