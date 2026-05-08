"""HTML/CSS/JS template for output/report.html.

Kept separate from build_report.py so the orchestrator stays readable.
All section renderers return strings; build_report.py concatenates them.
"""
from __future__ import annotations

import html
import json


# ---------------------------------------------------------------- styles & shell

CSS = """
:root {
  --bg: #fdfcf8;
  --fg: #1f1d18;
  --muted: #6b6759;
  --rule: #e5e1d6;
  --accent: #6c4f1f;
  --accent-soft: #c8a861;
  --good: #2a7a3f;
  --bad: #a23a2a;
  --warn: #b8893a;
  --code-bg: #f3eedf;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: "Source Serif Pro", "Iowan Old Style", Georgia, serif;
  line-height: 1.55; font-size: 16px; }
.layout { display: grid; grid-template-columns: 240px minmax(0, 1fr);
  max-width: 1400px; margin: 0 auto; }
nav.toc { position: sticky; top: 0; height: 100vh; overflow: auto;
  padding: 28px 18px; border-right: 1px solid var(--rule); font-size: 13.5px; }
nav.toc h2 { font-size: 13px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--muted); margin: 0 0 12px; }
nav.toc ol { list-style: none; padding: 0; margin: 0; }
nav.toc li { margin: 6px 0; }
nav.toc a { color: var(--fg); text-decoration: none; border-left: 2px solid transparent;
  padding-left: 10px; display: block; }
nav.toc a:hover { color: var(--accent); border-left-color: var(--accent-soft); }
nav.toc .sub { padding-left: 20px; font-size: 12.5px; color: var(--muted); }
main { padding: 36px 48px 80px; max-width: 960px; }
header.hero { border-bottom: 1px solid var(--rule); padding-bottom: 22px; margin-bottom: 30px; }
header.hero h1 { font-size: 30px; margin: 0 0 6px; letter-spacing: -0.01em; }
header.hero .sub { color: var(--muted); font-size: 15px; }
section { margin: 50px 0; scroll-margin-top: 16px; }
section > h2 { font-size: 22px; border-bottom: 1px solid var(--rule); padding-bottom: 8px;
  margin: 0 0 16px; letter-spacing: -0.005em; }
section > h3 { font-size: 17px; margin-top: 28px; color: var(--accent); }
section p { margin: 10px 0; }
.equation { background: var(--code-bg); padding: 18px 22px; border-radius: 6px;
  font-family: "JetBrains Mono", "SF Mono", Menlo, monospace; font-size: 14px;
  overflow-x: auto; }
.equation .pos { color: var(--good); }
.equation .neg { color: var(--bad); }
table { border-collapse: collapse; font-size: 13.5px; margin: 14px 0; width: 100%; }
th, td { padding: 6px 10px; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }
th { background: #f7f3e7; font-weight: 600; font-size: 12.5px; letter-spacing: .02em; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.score-0 { color: var(--bad); }
td.score-1 { color: #8a6024; }
td.score-2 { color: #4a6e2a; }
td.score-3 { color: var(--good); font-weight: 600; }
.tag { display: inline-block; font-size: 11.5px; padding: 1px 8px; border-radius: 10px;
  background: var(--accent-soft); color: #fff; margin-right: 4px; }
.tag.good { background: var(--good); }
.tag.bad { background: var(--bad); }
.tag.warn { background: var(--warn); }
.tag.muted { background: var(--muted); }
details { margin: 16px 0; border: 1px solid var(--rule); border-radius: 6px;
  background: #fff; padding: 0; overflow: hidden; }
details > summary { padding: 12px 16px; cursor: pointer; font-weight: 600;
  background: #faf6e9; border-bottom: 1px solid transparent; user-select: none; }
details[open] > summary { border-bottom-color: var(--rule); }
details > .details-body { padding: 16px 20px; }
.receipt { color: var(--muted); font-size: 12px; font-family: "JetBrains Mono", monospace;
  display: block; margin-top: 4px; }
.receipt code { background: var(--code-bg); padding: 1px 4px; border-radius: 3px; }
.quote { border-left: 3px solid var(--accent-soft); margin: 12px 0; padding: 6px 14px;
  background: #faf7ec; font-size: 13.5px; color: #312d20; }
.quote .src { display: block; color: var(--muted); font-size: 12px; margin-top: 4px;
  font-family: "JetBrains Mono", monospace; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin: 14px 0; }
.kpi { padding: 12px 14px; background: #faf7ec; border-radius: 6px; border: 1px solid var(--rule); }
.kpi .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.kpi .value { font-size: 22px; font-weight: 600; margin-top: 2px; }
.verdict { padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: 600;
  display: inline-block; }
.verdict.hit { background: #e3f1e2; color: var(--good); }
.verdict.miss { background: #f6e2dc; color: var(--bad); }
.verdict.partial { background: #f4ecd1; color: var(--warn); }
.chart-wrap { margin: 18px 0; padding: 12px; background: #fff; border: 1px solid var(--rule);
  border-radius: 6px; }
.chart-wrap canvas { max-width: 100%; }
img.embed { max-width: 100%; border: 1px solid var(--rule); border-radius: 4px; margin: 12px 0; }
.small { font-size: 12.5px; color: var(--muted); }
hr { border: 0; border-top: 1px solid var(--rule); margin: 30px 0; }
@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  nav.toc { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--rule); }
  main { padding: 24px 20px 60px; }
}
@media print {
  nav.toc { display: none; }
  .layout { grid-template-columns: 1fr; }
  main { padding: 0; max-width: none; }
  details { break-inside: avoid; }
  details[open] > summary { background: #faf6e9; }
  details:not([open]) { display: none; }  /* expand-all done in JS before print */
}
"""

JS = """
// Expand all <details> before printing so the PDF export contains everything.
window.addEventListener('beforeprint', () => {
  document.querySelectorAll('details').forEach(d => { d.dataset.wasOpen = d.open; d.open = true; });
});
window.addEventListener('afterprint', () => {
  document.querySelectorAll('details').forEach(d => {
    if (d.dataset.wasOpen === 'false') d.open = false;
  });
});

// "Expand all" toggle
function toggleAll(btn) {
  const open = btn.dataset.state !== 'open';
  document.querySelectorAll('details').forEach(d => d.open = open);
  btn.dataset.state = open ? 'open' : 'closed';
  btn.textContent = open ? 'Collapse all' : 'Expand all';
}
"""


def render_html(
    title: str,
    subtitle: str,
    toc: list[tuple[str, str, list[tuple[str, str]]]],
    sections: list[str],
    chart_specs: dict[str, dict],
) -> str:
    """Compose the full HTML page.

    toc: list of (id, label, [(child_id, child_label), ...])
    sections: rendered HTML strings, in order
    chart_specs: {canvas_id: chart_config_dict}, embedded as JSON for Chart.js
    """
    nav_items = []
    for sec_id, label, children in toc:
        nav_items.append(f'<li><a href="#{sec_id}">{html.escape(label)}</a>')
        if children:
            nav_items.append("<ol class='sub' style='list-style:none;padding:0'>")
            for cid, clabel in children:
                nav_items.append(f'<li><a href="#{cid}">{html.escape(clabel)}</a></li>')
            nav_items.append("</ol>")
        nav_items.append("</li>")
    nav_html = "\n".join(nav_items)

    body = "\n".join(sections)
    chart_json = json.dumps(chart_specs, ensure_ascii=False, default=str)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>{CSS}</style>
</head>
<body>
<div class="layout">
  <nav class="toc">
    <h2>Contents</h2>
    <ol style="list-style:none;padding:0">
      {nav_html}
    </ol>
    <p style="margin-top:20px"><button onclick="toggleAll(this)" data-state="closed"
      style="font:inherit;padding:6px 10px;border:1px solid #c8a861;background:#fff;
             color:#6c4f1f;border-radius:4px;cursor:pointer">Expand all</button></p>
  </nav>
  <main>
    <header class="hero">
      <h1>{html.escape(title)}</h1>
      <div class="sub">{html.escape(subtitle)}</div>
    </header>
    {body}
    <hr>
    <p class="small">Generated by <code>build_report.py</code> from outputs in <code>output/</code>.
       All scores trace back to source rows in <code>docs/</code>; see Appendix.</p>
  </main>
</div>
<script>{JS}</script>
<script>
const CHART_SPECS = {chart_json};
document.addEventListener('DOMContentLoaded', () => {{
  for (const [canvasId, spec] of Object.entries(CHART_SPECS)) {{
    const el = document.getElementById(canvasId);
    if (!el) continue;
    new Chart(el, spec);
  }}
}});
</script>
</body>
</html>"""


# ----------------------------------------------------------- small helper renderers

def kpi(label: str, value: str) -> str:
    return f'<div class="kpi"><div class="label">{html.escape(label)}</div>' \
           f'<div class="value">{html.escape(str(value))}</div></div>'


def kpi_grid(items: list[tuple[str, str]]) -> str:
    return '<div class="kpi-grid">' + "".join(kpi(l, v) for l, v in items) + "</div>"


def quote_block(quote_dict: dict) -> str:
    src = quote_dict.get("source", "")
    page = quote_dict.get("page", "?")
    text = quote_dict.get("quote", "")
    return (f'<div class="quote">"{html.escape(text)}"'
            f'<span class="src">— {html.escape(src)}, p.{page}</span></div>')


def collapsible(summary_html: str, body_html: str, open_by_default: bool = False) -> str:
    o = " open" if open_by_default else ""
    return (f'<details{o}><summary>{summary_html}</summary>'
            f'<div class="details-body">{body_html}</div></details>')


def score_cell(v) -> str:
    """Render a 0-3 score with color class."""
    try:
        iv = int(v)
        return f'<td class="num score-{iv}">{iv}</td>'
    except (ValueError, TypeError):
        return f'<td class="num small">—</td>'


def num_cell(v, fmt: str = "{:.1f}") -> str:
    try:
        if v is None or v != v:  # NaN check
            return '<td class="num small">—</td>'
        return f'<td class="num">{fmt.format(float(v))}</td>'
    except (ValueError, TypeError):
        return '<td class="num small">—</td>'


def receipt_line(label: str, items: list[str]) -> str:
    """Render a 'receipt' (data lineage) sub-line under a score."""
    if not items:
        return ""
    body = "; ".join(items)
    return f'<span class="receipt">{html.escape(label)}: {body}</span>'
