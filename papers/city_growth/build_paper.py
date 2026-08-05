"""Generate the formal paper as a self-contained HTML document (figures embedded
as base64; prints cleanly to PDF from any browser)."""
from __future__ import annotations
import base64, json
import numpy as np, pandas as pd
from pathlib import Path

A = Path(__file__).resolve().parent
OUT = A / "out"; FIG = OUT / "figures"


def img(name, width="100%"):
    b = base64.b64encode((FIG / name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" style="width:{width};max-width:900px;display:block;margin:10px auto;border:1px solid #e2e2e2;border-radius:6px">'


def fy(y):
    return "—" if pd.isna(y) else str(int(y))


ROMAN = {"Cologne", "Augsburg", "Vienna", "Basel", "Strasbourg", "Regensburg", "Mainz"}

def famous_table():
    s = pd.read_csv(OUT / "famous_cities.csv")
    s["growth"] = np.log(s["pop1500"]) - np.log(s["pop1200"])
    rows = []
    for _, r in s.iterrows():
        note = ""
        if pd.isna(r["charter_year"]):
            if r["disp"] in ROMAN:
                note = "Roman-origin — predates charters"
            elif r["country"] in {"Netherlands", "Belgium"}:
                note = "Low Countries — outside Städtebuch"
            else:
                note = "no formal medieval charter"
        cls = "over" if r["res_p"] > 0.5 else ("under" if r["res_p"] < -0.2 else "")
        rows.append(
            f"<tr class='{cls}'><td class='city'>{r['disp']}</td>"
            f"<td>{int(r['pop1200']):,}</td><td>{int(r['pop1500']):,}</td>"
            f"<td>{np.exp(r['growth'])-1:+.0%}</td>"
            f"<td>{'✓' if r['water']==1 else ''}</td>"
            f"<td>{fy(r['charter_year'])}</td>"
            f"<td>{'✓' if r['staple']==1 else ''}</td>"
            f"<td class='{'pos' if r['res_p']>0 else 'neg'}'>{r['res_p']:+.2f}</td>"
            f"<td class='note'>{note}</td></tr>")
    return "\n".join(rows)


def causal_table():
    res = json.load(open(OUT / "causal_summary.json"))
    order = [("staple", "Staple right (Stapelrecht)", "Viabundus"),
             ("fair", "Trade fair (Messe)", "Viabundus"),
             ("charter", "Town charter (Stadtrecht)", "Städtebuch"),
             ("market", "Market right (Marktrecht)", "Städtebuch")]
    rows = []
    for k, label, src in order:
        v = res[k]
        p = v["naive_p"]
        star = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else "n.s."
        rows.append(
            f"<tr><td class='city'>{label}</td><td>{src}</td>"
            f"<td class='pos'>{v['naive']:+.0%} <span class='star'>{star}</span></td>"
            f"<td>{v['did']:+.0%}</td>"
            f"<td>[{v['ci'][0]:+.0%}, {v['ci'][1]:+.0%}]</td>"
            f"<td>{v['pre']:+.2f}</td><td>{v['post']:+.2f}</td></tr>")
    return "\n".join(rows)


def performer_lists():
    s = pd.read_csv(OUT / "city_performers.csv").copy()
    import statsmodels.api as sm
    s["l1200"] = np.log(s["pop1200"]); s["l1500"] = np.log(s["pop1500"])
    r = sm.OLS(s["l1500"], sm.add_constant(s[["l1200"]])).fit()
    s["res_p"] = s["l1500"] - r.predict(sm.add_constant(s[["l1200"]]))
    def basin(row):
        if row["atlantic"] or row["northsea"]: return "Atlantic/N.Sea"
        if row["baltic"]: return "Baltic"
        if row["medit"]: return "Mediterranean"
        if row["on_river"]: return "Inland river"
        return "Landlocked"
    s["basin"] = s.apply(basin, axis=1)
    def mk(df):
        return "".join(f"<li><b>{x['city']}</b> ({int(x['pop1200']):,}→{int(x['pop1500']):,}; "
                       f"{x['basin']})</li>" for _, x in df.iterrows())
    return mk(s.nlargest(8, "res_p")), mk(s.nsmallest(8, "res_p"))


def robust_table():
    R = json.load(open(OUT / "robustness_summary.json"))
    b, a = R["buringh"], R["bairoch"]
    def row(label, bv, av, fmt="{:+.2f}"):
        return (f"<tr><td class='city'>{label}</td><td>{fmt.format(bv)}</td>"
                f"<td>{fmt.format(av)}</td></tr>")
    rows = [
        row("Growth vs. size, R² (1300→1500) — small = near-random", b["gibrat_r2"], a["gibrat_r2"], "{:.2f}"),
        row("Persistence r² (1300→1500)", b["persist_1300"], a["persist_1300"], "{:.2f}"),
        row("Momentum share of variance in 1500 size", b["decomp_momentum"], a["decomp_momentum"], "{:.0%}"),
        row("Water-access growth premium / century", np.exp(b["water"])-1, np.exp(a["water"])-1, "{:+.0%}"),
        row("Staple right — raw size gap", b["staple_naive"], a["staple_naive"], "{:+.0%}"),
        row("Staple right — causal effect (DiD)", b["staple_did"], a["staple_did"], "{:+.0%}"),
    ]
    return "\n".join(rows), R["agreement_r"], R["agreement_n"], b["staple_ntreat"], a["staple_ntreat"]


over, under = performer_lists()
res = json.load(open(OUT / "causal_summary.json"))
rob_rows, agree_r, agree_n, bur_ntreat, bai_ntreat = robust_table()

HTML = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Where, Not What: The Determinants of City Size in the Holy Roman Empire, 1200–1500</title>
<style>
 body{{font-family:Georgia,'Times New Roman',serif;max-width:860px;margin:0 auto;padding:40px 28px;
   color:#1a1a1a;line-height:1.62;font-size:17px}}
 h1{{font-size:30px;line-height:1.25;margin-bottom:6px}}
 h2{{font-size:22px;margin-top:38px;border-bottom:2px solid #2c3e50;padding-bottom:5px;color:#1b2b3a}}
 h3{{font-size:18px;margin-top:26px;color:#34495e}}
 .sub{{color:#555;font-size:16px;font-style:italic;margin-top:0}}
 .abstract{{background:#f6f8fa;border-left:4px solid #2c3e50;padding:16px 20px;font-size:16px;margin:24px 0}}
 .key{{background:#fff8e1;border-left:4px solid #d4a017;padding:14px 18px;margin:20px 0;font-size:16px}}
 table{{border-collapse:collapse;width:100%;margin:18px 0;font-family:'Segoe UI',Helvetica,sans-serif;font-size:13.5px}}
 th,td{{border:1px solid #dde;padding:6px 8px;text-align:right}}
 th{{background:#2c3e50;color:#fff;font-weight:600;text-align:right}}
 td.city{{text-align:left;font-weight:600}} td.note{{text-align:left;color:#777;font-style:italic;font-size:12px}}
 td.pos{{color:#1b7837;font-weight:600}} td.neg{{color:#b2182b;font-weight:600}}
 tr.over td{{background:#eafbf0}} tr.under td{{background:#fdecec}}
 .star{{color:#b2182b;font-weight:700}}
 .cap{{font-size:14px;color:#555;text-align:center;margin:2px auto 24px;max-width:820px}}
 .eq{{background:#f4f4f8;padding:12px 16px;border-radius:6px;font-family:'Cambria Math',Georgia,serif;
   font-size:17px;text-align:center;margin:14px 0}}
 .plain{{background:#eef4fb;border-left:4px solid #2c7fb8;padding:10px 16px;margin:10px 0;font-size:15px}}
 ul{{margin:8px 0}} li{{margin:3px 0}}
 code{{background:#eee;padding:1px 5px;border-radius:3px;font-size:14px}}
 .foot{{color:#666;font-size:13.5px}}
 @media print{{body{{font-size:12pt;max-width:100%}} h2{{page-break-after:avoid}} table,img{{page-break-inside:avoid}}}}
</style></head><body>

<h1>Where, Not What</h1>
<p class="sub">The determinants of city size in the Holy Roman Empire and Central Europe, 1200–1500</p>
<p class="foot">A quantitative study of 415 imperial cities (2,262 across Europe), the Viabundus medieval
transport network, and the dated commercial privileges of the <i>Deutsches Städtebuch</i>.</p>

<div class="abstract">
<b>Abstract.</b> Why did some medieval cities swell into metropolises while their neighbours stagnated?
Drawing on population estimates for 2,262 European cities, the reconstructed medieval road-and-water
network (Viabundus), and dated grants of staple rights, fairs, town charters and market rights for
2,390 imperial cities, we test the commonest explanation — that commercial privileges and institutions
made cities great — and find it does not survive measurement. The privileges historians celebrate were
awarded to towns that had <i>already</i> risen; once we compare a chartered town to comparable towns
over the same years, the growth effect of a staple right, a fair, a charter, or a market right is
statistically indistinguishable from zero. What actually fixed the urban hierarchy was set long before:
roughly seven-tenths of a city's size in 1500 was determined by its size centuries earlier, and a
city's population in <b>800 CE still predicts its size 700 years later</b>. The one force that reliably
moved a town up or down was <b>access to navigable water</b> — worth about <b>+15% growth per century</b>
and decisive in the reshuffling that followed the Black Death. The system is captured by a single
equation of near-random growth anchored on geography. Cities grew great because of <b>where</b> they sat
and <b>how early</b> they began — not because of what their rulers granted them.
</div>

<h2>1. The puzzle, and why it resists a simple formula</h2>
<p>Economic history has long sought the "recipe" for urban success: the right charter, the right market,
the right institutions. If such a recipe existed, cities with more of the right ingredients should have
grown faster. We test this directly and reach the opposite conclusion — and, importantly, we can show
<i>why</i> a deterministic recipe cannot exist.</p>

<p>The first fact any theory must confront is that, from one century to the next, <b>a city's growth is
almost unrelated to anything about the city</b> — including its own size. Figure 1 plots each city's
growth from 1200 to 1500 against its starting size. The cloud is essentially flat.</p>
{img("fig_gibrat.png")}
<p class="cap"><b>Figure 1.</b> Growth 1200→1500 against starting size. The near-zero slope means big and
small cities grew at essentially the same average rate — statisticians call this <b>Gibrat's law</b>.
A city's size explains only about 2% of its growth.</p>

<div class="plain"><b>Plain-language note — what "R²" means.</b> Throughout, <code>R²</code> is the share of the
variation a model explains, from 0 (nothing) to 1 (everything). An R² of 0.02 means the factor accounts
for 2% of what happened and 98% is left unexplained. When century-to-century growth has an R² near 0.02
against every candidate factor, there is simply very little systematic signal for <i>any</i> equation to
capture. This is not a defect of the data; it is a property of how cities grow.</div>

<p>This is the deep reason a factor-based growth equation underperforms: most of what happens to a city
in a century is idiosyncratic. The productive question is therefore not "what predicts growth?" but
"what fixes the <i>hierarchy</i> — the relative ranking of cities — and did the institutions we credit
actually cause it?"</p>

<h2>2. Data</h2>
<h3>Two independent population reconstructions</h3>
<p>Medieval city populations are not measured but <i>reconstructed</i> — pieced together from tax rolls,
hearth counts, militia lists, church records and chronicles, then converted to inhabitants with
demographic multipliers. Because the exercise is inevitably uncertain, we run our entire analysis on the
<b>two most widely used reconstructions of European city populations</b>, built by different scholars
from different sources, and report whether the conclusions survive the choice of source.</p>
<ul>
<li><b>Bairoch (1988)</b> — Paul Bairoch, Jean Batou &amp; Pierre Chèvre, <i>La population des villes
européennes de 800 à 1850.</i> The foundational compilation of the field: roughly 2,200 European cities
at centennial snapshots from 800 to 1850, synthesised from a vast body of local and secondary historical
sources. For a generation it has been <i>the</i> standard reference for quantitative work on European
urbanisation.</li>
<li><b>Buringh (2021)</b> — Eltjo Buringh, <i>The Population of European Cities from 700 to 2000</i>
(Research Data Journal for the Humanities and Social Sciences). A later, georeferenced reconstruction of
2,262 cities that revises and extends Bairoch and Chandler with newer local sources, and — crucially for
us — attaches to each city its <b>coordinates</b>, <b>elevation</b>, and a <b>first-nature transport
classification</b> (river / coastal / landlocked, with sea-catchment). It underlies the influential study
of Bosker, Buringh &amp; van Zanden (2013).</li>
</ul>
<p>The two agree closely — the correlation of their (log) city sizes in 1500 is <b>{agree_r:.2f}</b>
(Figure 8) — but they were assembled independently, so agreement of our <i>results</i> across them is a
meaningful robustness test. We take Buringh as the primary panel (it carries the geography we need) and
Bairoch as the check, and study cities of ≥1,000 inhabitants throughout.</p>

<h3>The transport network and the privileges</h3>
<ul>
<li><b>The transport network:</b> Viabundus — a georeferenced reconstruction of the late-medieval
road, river and sea network of Northern Europe, including <b>dated</b> staple-right, fair and toll nodes.</li>
<li><b>Commercial privileges:</b> Cantoni, Mohr &amp; Weigand (2020), <i>Princes and Townspeople</i> —
dated town charters (<i>Stadtrecht</i>) and market rights (<i>Marktrecht</i>) for all 2,390 cities of
the <i>Deutsches Städtebuch</i>, with legal families (Magdeburg law, Lübeck law, …).</li>
</ul>

<h2>3. The central result: privileges were badges of success, not its cause</h2>
<p>Consider staple rights (<i>Stapelrecht</i>) — the prized privilege forcing merchants passing through
a town to unload and offer their goods for sale. Towns with a staple right were, on average, <b>53%
larger</b> than towns without one (the red bars in Figure 2). Taken at face value, this looks like proof
that the privilege built the city. It is not.</p>

<p>The problem is <b>timing</b>. A staple right was granted <i>to</i> a town that had already become an
important junction. To separate cause from consequence we ask a sharper question: when a town acquired a
privilege, did its growth <i>accelerate</i> relative to comparable towns that did not yet have it? This
is a <b>difference-in-differences</b> comparison.</p>

<div class="plain"><b>Plain-language note — difference-in-differences.</b> Imagine two similar towns.
One receives a staple right in 1300, the other does not. If the privilege causes growth, the first town
should pull ahead <i>after</i> 1300 by more than it was already pulling ahead <i>before</i> 1300. We
measure the "extra" acceleration and net out whatever both towns were doing anyway. If the granted town
grows no faster after the grant than before — and no faster than its untreated peers — the privilege
did not cause the growth.</div>

<p>Across <b>four</b> distinct privileges from <b>two</b> independent datasets, the causal (blue) estimate
collapses to zero, and every confidence interval spans zero:</p>
{img("fig_causal_consolidated.png")}
<p class="cap"><b>Figure 2.</b> Red: the raw size gap between towns with and without each privilege
(two-way fixed-effects association). Blue: the causal effect once we compare like with like over the
same years (matched difference-in-differences, with 95% confidence bars). The +53% staple "effect" and
+41% fair "effect" vanish; charters and markets were never even statistically significant.</p>

<table>
<tr><th>Privilege</th><th>Source</th><th>Raw size gap</th><th>Causal effect</th><th>95% CI</th>
<th>Growth before grant</th><th>Growth after grant</th></tr>
{causal_table()}
</table>
<p class="cap"><b>Table 1.</b> The two right-hand columns are the giveaway: growth in the century
<i>before</i> a privilege was granted is essentially identical to growth in the century <i>after</i>.
Nothing changed at the moment of the grant. (<span class="star">***</span> = significant at 1%;
n.s. = not significant.)</p>

<div class="key"><b>Finding 1.</b> Staple rights, fairs, town charters and market rights show no causal
effect on city growth. The strong raw associations are entirely <i>selection</i>: privileges were
conferred on towns that had already grown. This mirrors the well-known result (Bosker, Buringh &amp; van
Zanden 2013) that the "bishopric" advantage disappears once city fixed effects absorb the fact that
bishops were placed in already-important cities.</div>

<h3>Cologne against Hamburg: the pattern in two cities</h3>
<p>The <i>Städtebuch</i> record makes the logic vivid. <b>Cologne</b>, the empire's largest city
(40,000 in 1200), was a Roman <i>colonia</i> and never received a medieval town charter — it was a city
before charters existed. <b>Hamburg</b>, a small place of 2,000 in 1200, received its charter in 1215
and a staple right, and grew fifteen-fold. Yet <b>Mainz</b> held both a charter (1300) and a staple
right and <i>shrank</i> from 9,000 to 6,000. The privileges neither made Cologne nor saved Mainz; they
tracked, imperfectly, an underlying geography of trade (Table 3).</p>

<h2>4. What actually fixed the hierarchy: deep history and geography</h2>
<p>If institutions are not the cause, what is? We decompose the variation in city size in 1500 into three
sources: a city's <b>inherited size</b> (its size in 1200, i.e. path dependence), its <b>deep origin</b>
(its size already in 800 CE), and its <b>first-nature geography</b> (river/coast access, sea basin,
elevation). A Shapley decomposition — a fair way of splitting shared credit among overlapping causes —
gives:</p>
{img("fig_variance_decomp.png")}
<p class="cap"><b>Figure 3.</b> What determined a city's size in 1500. Inherited size and deep origin —
i.e. <i>history</i> — dominate. Geography's <i>direct</i> share is small only because its work was
already done: geography set the early sizes, and persistence carried them forward. Nearly a third of the
outcome is irreducibly idiosyncratic.</p>

<p>The persistence is astonishing in its reach. A city's size in <b>800 CE</b> — the age of Charlemagne —
still explains <b>40%</b> of its size in 1500 (Figure 4). The urban map of the Holy Roman Empire in 1500
was, to a first approximation, drawn seven centuries earlier.</p>
{img("fig_persistence_depth.png")}
<p class="cap"><b>Figure 4.</b> How strongly a city's size in each past year predicts its size in 1500.
Even the Carolingian-era ranking of 800 CE survives into the Renaissance.</p>

<div class="key"><b>Finding 2.</b> About 70% of a city's 1500 size was already locked in by inherited size
and deep origin. The medieval urban hierarchy was overwhelmingly <b>path-dependent</b>: history, not
policy, was destiny.</div>

<h2>5. The one lever that moved cities: water</h2>
<p>Geography acts through one channel above all: <b>access to navigable water</b>. A city on a river or
coast grew about <b>15% more per century</b> than a landlocked one (95% confidence interval +7% to +23%).
Because a town cannot relocate to the sea, this relationship is plausibly causal in a way the endogenous
privileges are not.</p>

<p>But water's power was not constant — it was switched on by a change in the trade regime. Resolving the
coastal premium by sea basin and century (Figure 5) reveals a sharp turn. During the Black Death
(1300–1400), coastal cities — especially Mediterranean ports, the plague's entry points — did
<i>worse</i>. After 1400, every sea basin turned strongly positive, and the Atlantic and North Sea rose
fastest: the beginning of the maritime economy that would define the following centuries.</p>
{img("fig_water_timing.png")}
<p class="cap"><b>Figure 5.</b> The extra growth of coastal cities (vs landlocked), by sea basin and
century. The sea was a liability during the plague and an engine after it.</p>

<p>The consequences are written directly onto the map of winners and losers. Figure 6 ranks the cities
that most exceeded, or fell short of, the size their 1200 population alone would predict. The
over-performers are almost entirely Atlantic and North-Sea ports — Hamburg, Amsterdam, Antwerp, Danzig,
Utrecht; the under-performers are Mediterranean and landlocked river towns.</p>
{img("fig_performers.png")}
<p class="cap"><b>Figure 6.</b> Who beat their own history. Bars show how much bigger (right) or smaller
(left) a city was in 1500 than its 1200 size predicts, coloured by sea basin.</p>

<div style="display:flex;gap:24px;flex-wrap:wrap">
<div style="flex:1;min-width:280px"><b>Rose fastest above expectation</b><ul>{over}</ul></div>
<div style="flex:1;min-width:280px"><b>Fell furthest below expectation</b><ul>{under}</ul></div>
</div>
<p class="cap"><b>Table 2.</b> The exceptions are instructive: the two landlocked over-performers are
Hondschoote (a Flemish textile boom-town) and Debrecen (the hub of the Hungarian cattle trade) —
specific export industries, not general institutions.</p>

<h3>Twenty-one cities, side by side</h3>
<table>
<tr><th>City</th><th>Pop 1200</th><th>Pop 1500</th><th>Growth</th><th>Water</th>
<th>Charter</th><th>Staple</th><th>vs. history</th><th></th></tr>
{famous_table()}
</table>
<p class="cap"><b>Table 3.</b> "vs. history" is the residual from Figure 6 (how much a city beat or missed
its 1200-implied size). Note the pattern: the great Roman cities (Cologne, Augsburg, Vienna, Basel,
Strasbourg) carried <b>no medieval charter</b>; the explosive growers (Hamburg, Danzig, Amsterdam,
Antwerp) were water ports; and holding a charter and staple did not save Mainz (−0.60). Every city here
is on water — because in this region, being a city of any size in 1200 already required it.</p>

<h2>6. One equation for the whole system</h2>
<p>All of the above — the near-random growth, the deep persistence, the pull of geography — is captured
by a single law of motion for city size. Writing <code>P</code> for population and <code>log</code> for
the natural logarithm (which turns multiplicative growth into additive steps), the size of city
<i>i</i> in the next century is:</p>

<div class="eq">log&nbsp;P<sub>next</sub> &nbsp;=&nbsp; a<sub>t</sub> &nbsp;+&nbsp; 0.915&nbsp;·&nbsp;log&nbsp;P<sub>now</sub>
&nbsp;+&nbsp; 0.06&nbsp;·&nbsp;water &nbsp;+&nbsp; noise</div>

<div class="plain"><b>Reading the equation, term by term.</b>
<ul>
<li><b>0.915 · log P<sub>now</sub></b> — next century's size is almost entirely this century's size. The
coefficient <b>0.915</b> (just below 1) means cities are extremely "sticky": whatever a city is, it will
still be, a century later. This single number produces the deep persistence of Figure 4.</li>
<li><b>a<sub>t</sub></b> — a shock common to <i>all</i> cities in a given century (the Black Death made it
strongly negative around 1350; recovery made it strongly positive after 1400). These are era-wide tides,
not city-specific.</li>
<li><b>0.06 · water</b> — the small, steady geographic nudge upward for water-access cities.</li>
<li><b>noise</b> — a large idiosyncratic term. It is <i>five times</i> larger than the systematic pull
(technically, the ratio of the reversion force to the noise is 0.21), which is exactly why growth looks
random (Figure 1) and why no factor equation can predict it.</li>
</ul></div>

<p>When we run this equation forward from the real cities of 1200, it reproduces the observed persistence
of the hierarchy and its overall shape. It also reveals what it <i>cannot</i> produce: the real hierarchy
grew <b>more top-heavy</b> over time — the largest cities pulled away (the "Zipf" exponent fell from 1.26
toward 1.0) — whereas pure random growth predicts mild equalisation (Figure 7). That gap is the
fingerprint of a genuine <b>agglomeration</b> advantage at the very top: beyond a point, size itself
attracted more size.</p>
{img("fig_zipf_evolution.png")}
<p class="cap"><b>Figure 7.</b> Concentration of the urban hierarchy. A lower value means the largest
cities loom larger. Real cities (red) concentrated faster than random growth (grey) predicts —
mild but real increasing returns at the top.</p>

<div class="key"><b>Finding 3.</b> Medieval city size follows a near-random-walk anchored on geography,
plus era-wide shocks, plus a weak agglomeration pull at the largest cities. It is a <i>stochastic law</i>,
not a factor formula — which is why the search for a deterministic "recipe" was bound to disappoint.</div>

<h2>7. Robustness: the two standard reconstructions tell the same story</h2>
<p>Every result above is computed on the Buringh panel. We now recompute the core findings on the
independent Bairoch (1988) panel — same cities, same geography, same privileges, only the population
figures swapped — to confirm they are not an artefact of one scholar's estimates. First, the two sources
substantially agree on the sizes themselves:</p>
{img("fig_source_agreement.png", width="70%")}
<p class="cap"><b>Figure 8.</b> City populations in 1500: Bairoch (1988) versus Buringh (2021), for the
{agree_n} cities both cover. The log-populations correlate at r = {agree_r:.2f}; points hug the 45° line.</p>

<p>More importantly, the <i>conclusions</i> replicate. Figure 9 and Table 4 place the key quantities side
by side. In both reconstructions, century-to-century growth is largely unpredictable, inherited size
dominates the size distribution, water access carries a positive premium, and — decisively — the large
raw "staple advantage" collapses toward zero once the causal comparison is made.</p>
{img("fig_robustness_bars.png")}
<p class="cap"><b>Figure 9.</b> The same five quantities estimated on each population source. The pattern is
identical: history (persistence, momentum) dominates; the staple's raw size gap is large but its causal
effect is not.</p>

<table>
<tr><th>Result</th><th>Buringh (2021)</th><th>Bairoch (1988)</th></tr>
{rob_rows}
</table>
<p class="cap"><b>Table 4.</b> Core findings across both sources. The two panels differ in coverage —
Bairoch's sample skews toward larger, better-documented towns and is thinner before 1300, which is why
its growth shows somewhat more mean-reversion and its causal staple estimate rests on only
{bai_ntreat} treated towns (versus {bur_ntreat} in Buringh) — but the direction of every result is the
same. The privileges' raw association with size is positive and large in both; where the data can
support a well-powered causal test, it vanishes.</p>

<div class="key"><b>Robustness.</b> The findings do not depend on which reconstruction one trusts. Across
the two most widely used independent estimates of European city populations — Bairoch's foundational
compilation and Buringh's georeferenced revision — history dominates geography's direct role, water is
the exogenous lever, and commercial privileges show no causal growth effect.</div>

<h2>8. What this means for how we explain medieval cities</h2>
<p>The story that a wise grant of market or staple rights conjured a great city reverses cause and effect.
Rulers granted privileges to places that were <i>already</i> becoming important — usually because they sat
on a river or coast, at a junction laid down in Roman or Carolingian times. The privilege was the
<i>recognition</i> of urban success, drawn up after the fact, not its engine. This does not make
institutions unimportant to medieval life; it means they are poor candidates for the <i>root cause</i> of
differential city growth, because they are themselves consequences of the geography and history that did
the causing.</p>

<p>The positive account is simpler and older than any charter: a city's fortune was set by <b>where</b> it
sat in the landscape of trade — above all, whether goods could reach it by water — and by <b>how early</b>
it had established itself, since size begat size across centuries. Policy operated at the margins of a
system whose broad shape was already fixed.</p>

<h2>9. Limitations</h2>
<ul>
<li><b>Rounded populations.</b> Pre-modern population figures are estimates, often rounded to round
numbers. This inflates apparent randomness and caps every growth model's fit; our growth magnitudes
should be read as orders of magnitude, not precise decimals.</li>
<li><b>Centennial resolution.</b> The population snapshots are a century apart, so our difference-in-
differences uses century-wide "before" and "after" windows. The <i>null</i> result is robust across
grant-cohorts and to the pre-trend check, but finer-dated wage or construction series would sharpen it.</li>
<li><b>Network centrality.</b> Graph-theoretic measures of position in the Viabundus network (betweenness,
market access) did not out-predict a simple river/coast indicator within the Hanseatic footprint — a null
worth stating plainly, and a caution against over-engineering the geography variable.</li>
</ul>

<h2>References</h2>
<p class="foot">
Bairoch, P. (1988). <i>Cities and Economic Development.</i> ·
Bosker, M., Buringh, E. &amp; van Zanden, J.L. (2013). "From Baghdad to London," <i>Review of Economics
and Statistics</i> 95(4). ·
Bosker, M. &amp; Buringh, E. (2017). "City seeds," <i>Journal of Urban Economics</i> 98. ·
Buringh, E. (2021). <i>European urban population, 700–2000.</i> ·
Cantoni, D., Mohr, C. &amp; Weigand, M. (2020). <i>Princes and Townspeople</i> (Deutsches Städtebuch data). ·
Davis, D. &amp; Weinstein, D. (2002). "Bones, Bombs and Break Points," <i>AER</i> 92(5). ·
Dittmar, J. (2011). "Cities, Institutions, and the Emergence of Zipf's Law." ·
Gabaix, X. (1999). "Zipf's Law for Cities," <i>QJE</i> 114(3). ·
Jedwab, R., Johnson, N. &amp; Koyama, M. (2024). "Pandemics and Cities," <i>Journal of Urban Economics.</i> ·
Viabundus (2021), <i>Research Data Journal.</i>
</p>
<p class="foot" style="margin-top:22px;border-top:1px solid #ccc;padding-top:10px">
Reproducibility: all figures, tables and estimates are generated by the scripts in <code>papers/city_growth/</code>
(<code>panel.py · bairoch_panel.py → diagnostics.py → network.py → privileges.py → charter_did.py →
causal_consolidated.py → synthesis.py → generative_model.py → bairoch_robustness.py → city_table.py →
make_figures.py · figures2.py · figures3.py → build_paper.py</code>).
</p>

</body></html>"""

(OUT / "PAPER.html").write_text(HTML)
print("wrote", OUT / "PAPER.html", f"({len(HTML)//1024} KB before image embedding)")
