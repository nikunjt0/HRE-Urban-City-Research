"""Render FINDINGS_POLITICS.md + figures into a standalone HTML paper."""
from __future__ import annotations
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "politics"
FIG = OUT / "figures"

TITLE = "The Boring-Ruler Hypothesis: A Causal Audit of European Politics and Urban Prosperity, 800–1800"

FIGS = [
    ("fig_political_ledger.png",
     "Figure 1. The political ledger. Effects on city population growth, standardized doses, "
     "95% CI. Green = robust positive, red = robust negative, grey = precisely estimated null."),
    ("fig_freeprince_eventstudy.png",
     "Figure 2. Growth dynamics around the switch to free (non-absolutist) rule, De Long–Shleifer "
     "classification, 546 European cities, city and century fixed effects. Reference period t−1."),
    ("fig_dynasty_league.png",
     "Figure 3. League table of rulers: mean city growth relative to what size, water access and "
     "era predict, empirical-Bayes shrunken, lineages governing ≥8 city-windows."),
    ("fig_liberty_scale.png",
     "Figure 4. Marginal effect of commune status by city size (pooled European panel; the "
     "interaction attenuates within city — heterogeneity, not a causal claim)."),
    ("fig_event_dynamics.png",
     "Figure 5. Stacked event studies on decadal construction activity, all 2,390 German cities "
     "1300–1789. Reference decade t−1; controls are never-treated cities in the same decades."),
]


def md_to_html(md: str) -> str:
    html = md
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.M)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.M)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html, flags=re.S)
    html = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", html)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.M)
    # lists
    out, in_ul = [], False
    for line in html.split("\n"):
        if re.match(r"^\s*[-•] ", line):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append("<li>" + re.sub(r"^\s*[-•] ", "", line) + "</li>")
        else:
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(line)
    if in_ul:
        out.append("</ul>")
    html = "\n".join(out)
    html = re.sub(r"\n\n+", "\n<p>\n", html)
    return html


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


if __name__ == "__main__":
    md = (OUT / "FINDINGS_POLITICS.md").read_text()
    body = md_to_html(md)
    figs_html = "\n".join(
        f'<figure><img src="data:image/png;base64,{b64(FIG / f)}" alt="{f}">'
        f"<figcaption>{cap}</figcaption></figure>"
        for f, cap in FIGS if (FIG / f).exists())
    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{TITLE}</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 860px;
       margin: 2em auto; padding: 0 1.2em; line-height: 1.55; color: #1d2733; }}
h1 {{ font-size: 1.7em; line-height: 1.25; }}
h2 {{ margin-top: 1.6em; border-bottom: 1px solid #d8dee6; padding-bottom: .2em; }}
blockquote {{ background: #f4f6f8; border-left: 4px solid #2a9d8f;
              margin: 1em 0; padding: .8em 1.1em; font-size: 1.03em; }}
code {{ background: #f0f2f5; padding: .08em .3em; border-radius: 3px;
        font-size: .88em; }}
figure {{ margin: 2em 0; text-align: center; }}
figure img {{ max-width: 100%; border: 1px solid #e2e6eb; }}
figcaption {{ font-size: .86em; color: #5b6672; margin-top: .5em; text-align: left; }}
ul {{ padding-left: 1.3em; }}
.header-note {{ color: #5b6672; font-size: .92em; }}
</style></head><body>
<p class="header-note">Working paper · generated {Path(__file__).name} · data:
Cantoni–Mohr–Weigand; Bosker–Buringh–van Zanden; van Zanden–Buringh–Bosker;
Kokkonen–Sundell; Buringh</p>
{body}
<h2>Figures</h2>
{figs_html}
</body></html>"""
    (OUT / "PAPER_POLITICS.html").write_text(page)
    print("wrote", OUT / "PAPER_POLITICS.html",
          f"({len(page)//1024} KB)")
