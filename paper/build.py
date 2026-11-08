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
TITLE = "One Warning Away: What Sets the Blast Radius of an Exploit in an Autoresearch Swarm"
AUTHORS = "N. Divij &middot; [[AFFILIATION]]"
_stats = json.loads((HERE.parent / "figures" / "stats.json").read_text(encoding="utf-8"))
VALUES = {"[[CALLS]]": f"{_stats['spend']['calls']:,}", "[[COST]]": f"${round(_stats['spend']['usd'])}",
          "[[FAILED]]": str(_stats["failed_calls"])}
MAIN = ["intro_related", "method", "results", "realdata_limits", "conclusion"]
BACK = ["references", "appendix", "appendix_tables", "appendix_texts"]

CSS = """
@page { size: Letter; margin: 0.85in 0.95in; }
body { font-family: "Times New Roman", Georgia, serif; font-size: 10.5pt; line-height: 1.32; color: #111;
       background: #fff; max-width: 6.6in; margin: 0 auto; }
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
