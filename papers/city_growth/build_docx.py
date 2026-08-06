"""Build the revised paper as a .docx (research-narrative rewrite).

Fixes vs the old draft:
  - every number is derived on the page before it is used (implied size, R2 ladder,
    Shapley shares, the 31%->29% luck defense);
  - the decomposition is motivated (why those groups; institutions included as a
    4th group so 'unchosen factors' is answered, not assumed);
  - the equation is evaluated as a PREDICTOR (benchmarks, out-of-sample, top-10);
  - explicit 'what is new' section.
Output: out/European City Growth Paper (revised).docx
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIG = OUT / "figures"
DOC = OUT / "European City Growth Paper (revised).docx"

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Georgia"; st.font.size = Pt(10.5)
st.paragraph_format.space_after = Pt(7)

FIGN = {"n": 0}
TABN = {"n": 0}


def title(t, sub, author, date):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(t); r.font.size = Pt(22); r.bold = True
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(sub); r.font.size = Pt(12); r.italic = True
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{author}\n{date}").font.size = Pt(11)


def h1(t):
    p = doc.add_heading(t, level=1)
    for r in p.runs:
        r.font.color.rgb = RGBColor(0x1a, 0x1a, 0x1a); r.font.size = Pt(15)


def h2(t):
    p = doc.add_heading(t, level=2)
    for r in p.runs:
        r.font.color.rgb = RGBColor(0x33, 0x33, 0x33); r.font.size = Pt(12)


def para(text, bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead + " ").bold = True
    p.add_run(text)
    return p


def bullet(text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        p.add_run(bold_lead + " ").bold = True
    p.add_run(text)


def fig(fname, caption, width=6.1):
    FIGN["n"] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIG / fname), width=Inches(width))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(f"Figure {FIGN['n']}. {caption}")
    r.font.size = Pt(9); r.italic = True


def table(headers, rows, caption, widths=None):
    TABN["n"] += 1
    c = doc.add_paragraph()
    r = c.add_run(f"Table {TABN['n']}. {caption}")
    r.font.size = Pt(9.5); r.bold = True
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Light Grid Accent 1"
    for j, htxt in enumerate(headers):
        cell = t.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(htxt); run.bold = True; run.font.size = Pt(9)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.rows[i + 1].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(v)); run.font.size = Pt(9)
    doc.add_paragraph()


def equation(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.font.name = "Cambria Math"; r.font.size = Pt(12); r.bold = True


# ================================================================ front matter
title("Cities Grew for Boring Reasons",
      "The Determinants of City Size in the Holy Roman Empire and Central Europe, 1200–1500",
      "Nikunj Tyagi", "August 2026")

h1("Abstract")
para("Why did some medieval cities turn into metropolises while their neighbors stayed villages? "
     "The standard answer credits commercial privileges and institutions: staple rights, chartered "
     "liberties, fairs, market rights. Using two independent reconstructions of European city "
     "populations (2,262 cities, 700–2000) joined to dated privilege records, I test that answer "
     "and reject it. Towns holding staple rights were 53% larger than towns without them — but when "
     "I compare each newly privileged town to similar towns that never received the grant, growth "
     "after the grant is indistinguishable from growth before it. Across four privilege types the "
     "causal estimate is zero, with every confidence interval spanning zero. Privileges were badges "
     "of success already achieved, not engines of it.")
para("What did determine the urban hierarchy of 1500? I decompose the variation in city size across "
     "four candidate sources — inherited medieval size, deep pre-medieval origins, first-nature "
     "geography, and the institutions themselves. Two-thirds of the explainable variation traces to "
     "a city's own earlier size: 46% of total variance to its size in 1200 and 20% to its size in "
     "800, against 3% for geography directly and 3% for all four privileges combined. The remaining "
     "29% behaves like genuine noise, not like a missing factor: it does not shrink when "
     "institutions are added, and it does not persist from one century to the next. The one lever "
     "geography still pulled was navigable water, worth about 5–6% extra growth per century "
     "(+15% by 1500), and decisive in the reshuffle after the Black Death.")
para("These facts compress into a three-parameter law of motion. Handed only the populations of "
     "1200 and a water-access dummy, the law predicts the city sizes of 1500 with R² = 0.56 out of "
     "sample, places 81% of cities within a factor of two, and identifies eight of the ten largest "
     "cities of 1500 — close to the information ceiling: flexible machine-learning models given "
     "every feature knowable in 1200 reach only 0.61. Meanwhile the same law predicts essentially "
     "none of which individual cities would rise or fall (growth R² = 0.02). Both numbers are the point: the position of the urban hierarchy was "
     "highly predictable, and movement within it was mostly luck. Cities grew great because of where "
     "they sat and how early they started — not because of what was done for them.")

# ================================================================ 1
h1("1. The Question, and the Order the Answers Came In")
para("Medieval history offers a ready explanation for why Hamburg, Nürnberg, or Danzig became great: "
     "they won privileges. A staple right forced passing merchants to unload and offer their goods "
     "for sale. A charter freed townsmen from feudal obligations. A fair concentrated the region's "
     "trade inside the walls twice a year. These grants were fought over, paid for, and celebrated, "
     "so it is natural to assume they mattered. The assumption is testable, and this paper tests it.")
para("The paper is organized in the order the research actually unfolded, because each result forced "
     "the next question:")
bullet("Is growth predictable from size? If big cities systematically out-grew small ones "
       "(or vice versa), that mechanism would come first. It turns out neither is true — growth is "
       "almost unrelated to starting size — which means the hierarchy persists by default and the "
       "interesting question becomes what set it up.", "Step 1 (§3).")
bullet("Did privileges cause growth? The raw correlations say yes; a comparison that respects "
       "timing says no.", "Step 2 (§4).")
bullet("Build an explicit benchmark for what each city ‘should’ have weighed in 1500 given its 1200 "
       "size, so that over- and under-performance can be measured city by city rather than "
       "asserted.", "Step 3 (§5).")
bullet("Decompose the 1500 hierarchy into candidate sources — inherited size, deep origins, "
       "geography, and (back in for a fair hearing) institutions — and measure what is left "
       "over.", "Step 4 (§6).")
bullet("Identify the one geographic factor that still moved cities: navigable water.", "Step 5 (§7).")
bullet("Compress everything into a single equation, and — the acid test — ask how well that "
       "equation actually predicts the map of 1500 from the map of 1200.", "Step 6 (§8).")
para("Section 9 repeats the core results on an independent population reconstruction; §10 states "
     "explicitly what is new here; §11 concludes.")

# ================================================================ 2
h1("2. Data")
para("Medieval city populations are not measured; they are reconstructed from fragments — tax "
     "rolls, hearth counts, militia lists, church registers — converted into inhabitants with "
     "demographic multipliers. Because this is an estimation exercise, I run everything on the two "
     "most widely used reconstructions, built by different scholars from overlapping but distinct "
     "source bases:")
bullet("Bairoch, Batou & Chèvre (1988), La population des villes européennes de 800 à 1850: the "
       "foundational compilation — roughly 2,200 cities at hundred-year intervals.")
bullet("Buringh (2021), The Population of European Cities from 700 to 2000: a later, georeferenced "
       "reconstruction of 2,262 cities that revises Bairoch with newer scholarship and attaches "
       "coordinates, elevation, and a transport classification (river, coastal, landlocked).")
para("Where both sources cover a city in 1500, their log populations correlate at r = 0.96 — close "
     "agreement, but not identical, which is what makes the robustness check in §9 meaningful. "
     "Buringh is the primary panel throughout (it carries the geography); Bairoch is the check. The "
     "sample is the Holy Roman Empire and its neighbours — Germany, Italy, France, the Low "
     "Countries, Poland, Hungary, Switzerland, Austria — restricted to cities of at least 1,000 "
     "inhabitants: 1,259 cities in all.")
para("One quirk matters later. Both reconstructions round populations to convenient steps (1,000, "
     "2,000, 4,000…). Rounding injects spurious jumps into measured growth — a city drifting from "
     "1,400 to 1,600 people appears to leap from 1,000 to 2,000. Part of what no model can explain "
     "in §6 is this measurement noise, and I will show a diagnostic that says so.")
para("Privileges and institutions come from two further sources:")
bullet("Viabundus (Holterman et al.), a georeferenced reconstruction of the late-medieval road, "
       "river and sea network of Northern Europe, with dated staple rights, fairs, and tolls "
       "(156 staples, 773 fairs).")
bullet("Cantoni, Mohr & Weigand (2020), dated town charters (Stadtrecht) and market rights "
       "(Marktrecht) for the 2,390 towns of the Deutsches Städtebuch, with legal families "
       "(Magdeburg law, Lübeck law, …).")

# ================================================================ 3
h1("3. Step 1: Growth Was Not Predictable from Size")
para("A city's size in 1500 is the compound of everything that happened to it before. If some "
     "cities ended up vastly larger than others, then either they grew faster during 1200–1500, or "
     "they started ahead and coasted. So the first thing to establish is the basic character of "
     "growth itself.")
para("Figure 1 plots each city's growth over 1200–1500 against its size in 1200. If size bred "
     "growth (big cities compounding their advantage), the cloud would slope up. If small towns "
     "systematically caught up, it would slope down.")
fig("fig_gibrat.png",
    "City growth 1200→1500 against starting size. Starting size explains ~2% of growth.")
para("The cloud is nearly flat: starting size explains about 2% of subsequent growth. This is "
     "Gibrat's law — growth roughly independent of size — and it has a consequence that shapes "
     "everything after. If growth does not depend on size, then a city 10× larger than its "
     "neighbor in 1200 tends to stay roughly 10× larger, because both draw growth from the same "
     "distribution. Rankings persist by default, without any mechanism favoring the big.")
para("Individual cities still followed wildly different paths — the vertical spread in Figure 1 is "
     "huge. But those differences were not systematically related to where a city started. That "
     "re-aimed the whole project: instead of hunting for a recipe that made cities grow, I needed "
     "to ask (a) what created the initial differences that later growth carried forward, and "
     "(b) whether policies and privileges let particular cities beat the average fate their size "
     "implied. Those are Steps 4 and 2 respectively.")

# ================================================================ 4
h1("4. Step 2: Privileges Fail the Causal Test")
para("Start with the most prized privilege, the staple right (Stapelrecht), which forced merchants "
     "passing through to unload and offer their cargo for sale. In the raw data, towns holding a "
     "staple right were on average 53% larger than towns without one; towns with fairs were 41% "
     "larger. Historians have long read gaps like these as evidence that privileges built cities.")
para("The problem is timing. Staple rights were granted to towns that had already become important "
     "junctions; fairs were awarded to towns that already drew traders. A cross-sectional gap "
     "cannot distinguish ‘the privilege made the town big’ from ‘the town was big, so it got the "
     "privilege.’ Separating those requires following towns through time around the moment of the "
     "grant. Concretely, for every town that received a privilege in some year, I:")
bullet("recorded its population in the centuries before and after the grant year;")
bullet("matched it to comparison towns of similar size, in the same sample, with the same water "
       "access, that did not receive the privilege in that window;")
bullet("computed the difference-in-differences: (growth of the granted town after − before) minus "
       "(growth of its comparison towns after − before). If the privilege caused growth, this "
       "quantity is positive.")
para("Two checks make the design credible. First, pre-trends are flat: towns about to receive a "
     "staple right were not already accelerating relative to their matches, so the matching is not "
     "obviously broken. Second, the same machinery applied to four different privileges, from two "
     "independently assembled sources (Viabundus staples and fairs; Städtebuch charters and market "
     "rights), tells one consistent story. Figure 2 shows it.")
fig("fig_causal_consolidated.png",
    "Raw size gaps (red) versus the causal difference-in-differences estimate (blue) for four "
    "privileges, with 95% bootstrap confidence intervals. Every causal estimate is "
    "indistinguishable from zero.")
para("The raw gaps are large: staple +53%, fair +41%. The causal estimates collapse: staple −9% "
     "[−24, +10], fair −0% [−13, +14], town charter +0% [−21, +33], market right −3% [−25, "
     "+38]. Growth in the century after a grant is statistically identical to growth in the century "
     "before it. This parallels Bosker, Buringh & van Zanden (2013), whose ‘bishopric advantage’ "
     "evaporates once city fixed effects absorb the fact that bishops sat in already-important "
     "places.", "Finding 1: privileges were badges, not engines.")
para("The Städtebuch record makes the logic vivid. Cologne, the empire's largest city (40,000 in "
     "1200), was a Roman colonia and never held a medieval town charter — it was a city before "
     "charters existed. Hamburg (2,000 in 1200) received charter and staple and grew fifteen-fold. "
     "Mainz held both a charter (1300) and a staple right and shrank from 9,000 to 6,000. Knowing a "
     "town's privileges tells you almost nothing about its fate; §5 makes that ‘almost nothing’ "
     "precise.")

# ================================================================ 5
h1("5. Step 3: What a City ‘Should’ Have Weighed — the Implied-Size Benchmark")
para("Claims like ‘Hamburg over-performed’ or ‘Mainz under-performed’ are empty until "
     "‘performance’ is defined against a benchmark. Here is the one used for the rest of the "
     "paper. Take the 1,092 cities observed in both 1200 and 1500 and fit the average relationship "
     "between the two dates by least squares:")
equation("log P₁₅₀₀ = 1.34 + 0.86 · log P₁₂₀₀ + 0.14 · water")
para("This line is what ‘the size its 1200 population implies’ means: it is the 1500 size of the "
     "average city that started at a given 1200 size (with a modest bonus if it sat on navigable "
     "water — the water term is developed in §7). A slope of 0.86, slightly below 1, says the "
     "hierarchy compressed a little: a city 10× larger than another in 1200 was typically about "
     "7× larger in 1500. A city's performance is its residual — how far its actual 1500 "
     "population sits above or below the line, in log points. Figure 3 draws this.")
fig("fig_implied_size.png",
    "The implied-size benchmark. Each dot is a city; the blue line is the fitted average "
    "1200→1500 relationship for cities on water (green dashed: landlocked). A city's "
    "performance is its vertical distance from the line (red segments; values in log points).")
para("Now individual cities can be read quantitatively. Hamburg's residual of +2.27 log points "
     "means it ended at e²·²⁷ ≈ 9.7 times its implied size; Amsterdam (+1.96) at 7×; Antwerp "
     "(+1.93) at 7×; Danzig (+1.48) at 4×. Mainz (−0.63) ended at barely half the size its 1200 "
     "population implied. Cologne (+0.10) and Vienna (+0.02) grew almost exactly as their starting "
     "sizes dictated — impressive in absolute terms, unremarkable relative to the benchmark.")
para("Ranking all cities by this residual (Figure 4) reveals the geography of over- and "
     "under-performance: the over-performers are almost entirely Atlantic and North Sea ports; the "
     "under-performers are Mediterranean and landlocked interior towns. That pattern is Step 5's "
     "subject.")
fig("fig_performers.png",
    "Cities ranked by performance against the implied-size benchmark. Over-performers (top) are "
    "dominated by Atlantic and North Sea ports; under-performers (bottom) by Mediterranean and "
    "landlocked towns.")

famous = pd.read_csv(OUT / "famous_cities.csv")
rows = []
for _, r in famous.iterrows():
    implied = int(round(r["pred1500"], -2))
    ratio = np.exp(r["resid"])
    charter = "" if pd.isna(r["charter_year"]) else str(int(r["charter_year"]))
    rows.append([r["city"], f"{int(r['pop1200']):,}", f"{implied:,}",
                 f"{int(r['pop1500']):,}", f"{ratio:.1f}×",
                 charter, "yes" if r["staple"] == 1 else ""])
table(["City", "Pop 1200", "Implied 1500", "Actual 1500", "Actual / implied", "Charter", "Staple"],
      rows,
      "Twenty-one major cities against the implied-size benchmark. ‘Implied 1500’ is the fitted "
      "value from the benchmark regression; the ratio is the city's over- or under-performance.")
para("The table rewards a slow read. The explosive over-performers (Hamburg 9.7×, Amsterdam 7.1×, "
     "Antwerp 6.9×, Utrecht 5.7×, Ulm 5.2×) are ports and river towns of the Atlantic–North Sea "
     "world. The great Roman-era cities — Cologne, Augsburg, Vienna, Basel, Strasbourg — carried "
     "no medieval charter at all and simply tracked their benchmarks. And privileges scatter across "
     "the whole range: Mainz held charter and staple and finished at 0.5×; Nürnberg held a charter "
     "and finished at 4.2×; Augsburg held neither and finished at 1.9×. The residual — not the "
     "privilege list — is the quantity with structure in it.")

# ================================================================ 6
h1("6. Step 4: Where the 1500 Hierarchy Came From")
para("If privileges did not build the hierarchy, what did? This section decomposes the variation in "
     "log city size in 1500 across candidate explanations. The candidates are not arbitrary; they "
     "are the four theories on the table at this point in the argument:")
bullet("the path-dependence channel: a city's own size in 1200, at the start of the "
       "study window. Step 1 showed growth is unrelated to size, which makes early size a "
       "candidate to dominate by pure carry-forward.", "Inherited size —")
bullet("its size already in 800 AD, the Carolingian era — the earliest layer the data "
       "supports. This separates medieval momentum from origins laid down before the Middle Ages "
       "(Roman roads, bishoprics, river fords).", "Deep origin —")
bullet("river and coastal access, sea basin, elevation — the ‘where it sits’ "
       "channel, which operates whether or not anyone grants anything.", "First-nature geography —")
bullet("staple, fair, charter, and market rights held by 1500. Step 2 showed they are "
       "not causes, but they stay in the race here as predictive markers — precisely so that the "
       "unexplained remainder cannot be blamed on their omission.", "Institutions —")
para("The decomposition proceeds in two transparent steps (Figure 5).")
h2("6.1 Step one: the R² ladder")
para("First, ask how much of the variation in 1500 size each candidate explains on its own, by "
     "regressing log 1500 size on each block separately. Institutions alone: 4.5%. Geography alone: "
     "9%. Size in 800 alone: 40%. Size in 1200 alone: 56%. All four together: 71%. (These R² values "
     "are the standard ‘share of variance explained’; the joint model uses the 551 cities observed "
     "in 800, 1200, and 1500.)")
fig("fig_decomp_build.png",
    "Left: variance in 1500 city size explained by each candidate alone, then jointly (R²). "
    "Right: the Shapley split of the joint 71% into fair shares, with the 29% no model explains "
    "shown in grey.")
h2("6.2 Step two: splitting shared credit fairly (Shapley)")
para("The solo numbers overlap: 4.5 + 9 + 40 + 56 sums to more than the joint 71, because the "
     "candidates are correlated — cities big in 1200 tended to be big in 800, and both tend to sit "
     "on water. Whichever variable enters a regression first soaks up the shared credit. The "
     "Shapley decomposition (Shorrocks 1982; Israeli 2007) removes that arbitrariness: it computes "
     "each candidate's marginal contribution to R² under every possible order of entry and "
     "averages them. With four groups there are 24 orderings; each group's share is its average "
     "contribution across all of them. Nothing about the method favors any candidate — the same "
     "arithmetic that credits inherited size would have credited institutions, had the data pointed "
     "that way.")
para("The result, as shares of the total variance in 1500 size: inherited size (1200) 46%; deep "
     "origin (800) 20%; geography directly 2.5%; institutions 3.2%; unexplained 29%. Two-thirds of "
     "everything explainable is a city's own earlier size. Geography's direct share is small for an "
     "instructive reason: by 1200 its work was already embedded in the sizes — water and Roman "
     "roads decided which places were big early, and persistence carried the result forward. "
     "Geography set the initial conditions; path dependence compounded them.")
h2("6.3 Interrogating the unexplained 29%")
para("A skeptical reader should ask: is that 29% really ‘luck,’ or just factors I did not choose "
     "to include? Three tests say it behaves like noise, not like a missing cause.")
bullet("It is not the institutions. Adding all four privilege blocks to the three-factor model "
       "moves the unexplained share only from 30.7% to 29.0% — the omission of institutions was "
       "hiding 1.7 points, not 30.", "(i)")
bullet("It is not any stable hidden factor. This is the sharp test. Any durable city trait omitted "
       "from the model — an entrepreneurial elite, a lucrative relic, an unusually able council — "
       "would push the same city above its benchmark century after century, making growth "
       "residuals persist. They do not: the correlation between a city's growth residual in one "
       "century and the next is −0.10 (1200s→1300s) and −0.16 (1300s→1400s). Cities that beat "
       "the benchmark in one century were, if anything, slightly more likely to fall below it in "
       "the next — the signature of measurement bounce, not of persistent hidden quality.", "(ii)")
bullet("Part of it is mechanical. Populations rounded to steps of 1,000/2,000/4,000 create "
       "artificial jumps in measured growth (and the slight negative autocorrelation in (ii) is "
       "exactly what rounding bounce produces). The 29% is therefore an upper bound on true "
       "historical luck: plague outbreaks, fires, sieges, dynastic accidents — plus recording "
       "error.", "(iii)")
para("How deep does the path dependence run? Figure 6 traces the lock-in backward: a city's size "
     "in 800 AD — the age of Charlemagne — still explains 40% of its size in 1500, seven hundred "
     "years later. The urban map of the Holy Roman Empire in 1500 was, to a first approximation, "
     "drawn before the Middle Ages began.")
fig("fig_persistence_depth.png",
    "Depth of persistence: variance in 1500 size explained by size at each earlier date. Even "
    "800 AD explains 40%.")
para("About two-thirds of a city's 1500 size was already determined by its own earlier size, and "
     "no measured or stable unmeasured factor accounts for more than a sliver of the rest.",
     "Finding 2:")

# ================================================================ 7
h1("7. Step 5: Water — the One Lever Geography Still Pulled")
para("One geographic factor did keep moving cities after 1200: navigable water. Regressing "
     "1200→1500 growth on water access (controlling for starting size), cities on a river or "
     "coast grew +0.143 log points more — about 15% larger by 1500, bootstrap 95% CI [+7%, +23%] "
     "— than comparable landlocked cities, roughly +5–6% per century compounding. Unlike "
     "privileges, this factor cannot be endogenous to success: a town cannot petition its way to "
     "the coast. Where the privilege gaps collapsed under the causal test, the water premium has "
     "nothing to collapse into — the geography was there first.")
para("The premium was not constant — it was switched on by a change in trade. Figure 7 resolves "
     "the coastal premium by sea basin and century. In the plague century (1300–1400), coastal "
     "cities did worse — the Black Death entered through ports, and Mediterranean ports "
     "especially. After 1400, every basin turns strongly positive as long-distance trade "
     "reorganized around the Atlantic, North Sea, and Baltic. The sea was a liability during the "
     "plague and an engine after it. Consistent with that reading, the cities that emerged from "
     "the plague permanently larger were disproportionately on water (64% of winners vs 57% of "
     "losers; net 1300→1500 gain on water +0.084 log, p = 0.008, controlling for pre-plague "
     "size) — the great mortality shock reshuffled people toward locational fundamentals, "
     "echoing Jedwab, Johnson & Koyama's finding that plague recovery favored fixed advantages.")
fig("fig_water_timing.png",
    "The water premium by sea basin and century. Negative for Mediterranean ports in the plague "
    "century; strongly positive everywhere after 1400.")
para("This is also the pattern behind Figure 4 and Table 1: the over-performers were Atlantic and "
     "North Sea ports because water is where the residual structure lives — the one systematic "
     "escape from the implied-size benchmark.")

# ================================================================ 8
h1("8. Step 6: One Equation — and How Well It Actually Predicts")
para("Steps 1–5 leave three moving parts: a city's own past size, water, and century-wide shocks. "
     "The natural summary is the growth regression itself, written as a law of motion. Pooling all "
     "1200→1300, 1300→1400 and 1400→1500 transitions:")
equation("log P(i, t+1) = a(t) + 0.915 · log P(i, t) + 0.060 · water(i) + ε(i, t)")
table(["term", "estimate", "meaning"],
      [["a(t): century shocks", "+0.88 (1200s), +0.35 (1300s), +1.03 (1400s)",
        "tides common to all cities: expansion, plague century, recovery boom"],
       ["persistence (0.915)", "0.915 per century",
        "a city next century ≈ its current size; deviations decay with a half-life of ~800 years"],
       ["water (0.060)", "+6% per century", "the steady geographic nudge from §7"],
       ["ε: noise, σ = 0.40", "σ = 0.403 log/century",
        "idiosyncratic shocks — 5× the size of the systematic pull (κ/σ = 0.21)"]],
      "The estimated law of motion, term by term.")
para("Nothing here is exotic — it is the regression from Step 1 with the water term from Step 5 "
     "and century intercepts, rearranged. The draft question any reader should ask is: does this "
     "equation actually predict city sizes, or is it a decoration? The test: hand the equation "
     "only the populations of 1200 and each city's water dummy, iterate it forward three "
     "centuries (no noise, no peeking), and compare the predicted 1500 against the actual 1500 "
     "for all 1,092 cities. Table 3 reports the accuracy alongside the benchmarks it has to beat.")
table(["predictor of 1500 sizes (using only 1200 information)", "R² (log size)", "rank corr.",
       "median miss", "within ×2", "top-10 found"],
      [["guess the sample average for every city", "0.00", "—", "×1.63", "62%", "0/10"],
       ["frozen map: predict 1500 size = 1200 size", "0.39", "0.69", "×1.50", "60%", "8/10"],
       ["the equation, without the water term", "0.55", "0.69", "×1.49", "80%", "8/10"],
       ["the equation", "0.56", "0.69", "×1.56", "81%", "8/10"],
       ["the equation + all four privileges as predictors", "0.59", "0.71", "×1.47", "81%", "6/10"]],
      "Prediction accuracy for 1500 city sizes. ‘Median miss’: median multiplicative error "
      "(×1.56 = typical prediction off by 56%). ‘Top-10 found’: how many of the ten largest "
      "actual cities of 1500 appear in the predicted top ten.")
para("Three readings. First, the equation predicts the hierarchy well: R² = 0.56 on log sizes, "
     "81% of cities within a factor of two, and eight of the ten largest cities of 1500 correctly "
     "identified from 1200 data alone (it misses Florence — whose banking-driven surge is exactly "
     "the kind of idiosyncratic rise the law calls noise — and Bordeaux). Second, this is not "
     "overfitting: refitting the law on a random half of the cities and predicting the other half, "
     "200 times over, gives out-of-sample R² = 0.557 [0.508, 0.605] — identical to in-sample. "
     "Third, privileges add almost nothing even as pure predictive markers, with no causal claim "
     "at all: three points of R² (and they actually worsen the top-10 identification), which is "
     "the predictive restatement of Finding 1.")
fig("fig_prediction.png",
    "Left: 1500 sizes predicted by the equation from 1200 data versus actual 1500 sizes "
    "(R² = 0.56; dashed line = perfect prediction). Right: the same equation's predicted versus "
    "actual growth (R² = 0.02).")
para("The right panel of Figure 8 is the other half of the finding. Asked to predict growth — "
     "which cities would rise or fall relative to their start — the same equation manages "
     "R² = 0.02. There is no contradiction: position is predictable because it is inherited; "
     "movement is unpredictable because the noise term (σ = 0.40) dwarfs the systematic pull. "
     "Both facts are the finding. Any book promising the recipe that made particular cities surge "
     "is fitting stories to what the data says is mostly a random draw; meanwhile the boring "
     "regularity — tomorrow's map ≈ today's map plus a water tilt — predicts remarkably well.")
h2("8.1 Is 0.56 high or low? The information ceiling")
para("An R² of 0.56 invites the objection: barely more than half the variation — surely a better "
     "model could do better? The objection assumes the missing 44% is signal waiting for a "
     "cleverer specification. That is testable. I gave flexible machine-learning models "
     "(random forest, gradient boosting) every scrap of 1200-vintage information in the data — "
     "size in 1200, size in 800, coordinates, elevation, river, coast, sea basin, and every "
     "privilege already granted by 1200 — and measured out-of-sample accuracy with five-fold "
     "cross-validation. Table 4 is the result.")
table(["model, all restricted to information available in 1200", "out-of-sample R² (5-fold CV)"],
      [["the 3-parameter law (size + water + shocks)", "0.56"],
       ["linear model, all seventeen features", "0.59"],
       ["random forest, all seventeen features", "0.61"],
       ["gradient boosting, all seventeen features", "0.61"]],
      "The information ceiling. No model, however flexible, extracts much more from 1200-vintage "
      "information than the 3-parameter law already does.")
para("The kitchen sink buys five points of R², and the model's own accounting says where they come "
     "from: 78% of the gradient booster's predictive weight sits on 1200 size alone, most of the "
     "rest on raw coordinates (which proxy the coming Atlantic–North Sea shift, the pattern of "
     "§7), and 0.3% on the privileges. Roughly 0.61 is the ceiling of what could have been known "
     "in 1200; the law reaches 0.56 of it with three parameters. The residual ~40% was not "
     "knowable — it is three centuries of plague draws, fires, sieges, trade-route accidents, and "
     "banking booms, plus the rounding error documented in §2.")
para("Two calibrations make the 0.56 easier to judge. First, the horizon ladder: predicting 1500 "
     "sizes from 1400 sizes — one century ahead, with perfect knowledge of the starting point — "
     "achieves only R² = 0.76; from 1300, 0.65; from 1200, 0.56. Unpredictability compounds "
     "century by century, and the 300-year figure is exactly on that decay curve. There is no "
     "specification that beats the horizon; even God's own 1400 census caps out at 0.76 for "
     "1500. Second, scale: 300 years is roughly twelve human generations. Social science "
     "celebrates R² ≈ 0.1–0.25 for transmitting economic status across a single generation. "
     "Predicting individual cities across twelve, from three numbers, at 0.56, is not a weak "
     "result — it is an extraordinary amount of determinism, which is precisely the paper's "
     "claim of path dependence.")
para("The deeper point is that 0.56 is not a grade on the model; it is a measurement of the "
     "system. The paper's central decomposition — roughly two-thirds of the hierarchy locked in, "
     "roughly a third luck — and the prediction R² are the same fact in different units. If some "
     "specification pushed R² to 0.9, it would not vindicate the analysis; it would falsify "
     "Finding 3, because a system whose growth is 80% noise (κ/σ = 0.21) cannot be 90% "
     "predictable three centuries out. The equation predicts as well as the world it describes "
     "permits, and the shortfall is itself the measured quantity: the share of urban fate that "
     "was luck.")
h2("8.2 What the equation cannot do — and why that failure is informative")
para("Simulating the law forward from the real 1200 sizes (400 runs) reproduces the persistence of "
     "the hierarchy and the general shape of its evolution. It fails in exactly one direction: the "
     "real top tier concentrated more than randomness predicts. The Zipf exponent — a standard "
     "measure of how dominant the largest cities are, lower = more concentrated — fell from 1.26 "
     "to 1.08 in the data, while the simulated law drifts toward mild equalization (1.22 by 1500). "
     "Figure 9 shows the divergence. That gap is the fingerprint of a force absent from the "
     "equation: agglomeration at the very top. Past a certain size, size itself attracts size — "
     "consistent with Dittmar's finding that Zipf's law for European cities emerges as the upper "
     "tail thickens toward the modern era.")
fig("fig_zipf_evolution.png",
    "Concentration of the urban hierarchy (Zipf exponent; lower = largest cities more dominant). "
    "Real cities (red) concentrate faster than the fitted random-growth law predicts (grey band).")
para("Medieval city size followed a near-random walk anchored on geography and swept by common "
     "shocks — a stochastic law, not a factor recipe — plus a modest agglomeration pull at the "
     "top that is the one thing the random walk cannot fake.", "Finding 3:")

# ================================================================ 9
h1("9. Do the Results Survive on the Other Reconstruction?")
para("Every number above comes from the Buringh panel. Since medieval populations are "
     "reconstructions, I re-ran the core analyses with Bairoch's (1988) independent estimates "
     "swapped in — same cities, same geography, same privilege dates; only the population numbers "
     "change. Figure 10 shows the raw agreement (r = 0.96 on 1500 log sizes, 511 common cities); "
     "Table 5 and Figure 11 place the headline quantities side by side.")
fig("fig_source_agreement.png",
    "Agreement between the two independent population reconstructions on 1500 city sizes "
    "(r = 0.96, n = 511).")
table(["result", "Buringh (2021)", "Bairoch (1988)"],
      [["growth predictable from size? (R², 1300→1500)", "0.05", "0.30"],
       ["persistence of the hierarchy (r², 1300→1500)", "0.65", "0.54"],
       ["momentum share of 1500 size variance", "96%", "98%"],
       ["water premium per century (1300→1500 window)", "+9% (p = .008)", "+15% (p = .15)"],
       ["staple right: raw size gap", "+92%", "+36%"],
       ["staple right: causal DiD", "−9% (53 treated)", "−49% (7 treated)"]],
      "Core results on the two independent population reconstructions.")
fig("fig_robustness_bars.png",
    "The same qualitative findings on both reconstructions: persistence dominates, water is "
    "positive, the raw staple gap collapses under the causal test.")
para("Every qualitative conclusion replicates: century growth is largely unpredictable, inherited "
     "size dominates, water carries a positive premium, and the raw staple advantage collapses "
     "(indeed reverses) under the causal comparison. The honest differences run in expected "
     "directions: Bairoch is thin before 1300 and skews to larger, better-documented towns, so it "
     "shows more mean-reversion and its staple test rests on only seven treated towns. Nothing "
     "rests on which scholar's numbers one prefers.")

# ================================================================ 10
h1("10. What Is Actually New Here")
para("Each ingredient of this paper has a literature behind it; the contributions are specific:")
bullet("Privileges get a causal test, and fail it, with precision. The size gaps enjoyed by "
       "privileged towns are old news; what is new is difference-in-differences estimates around "
       "the grant dates of four privilege types from two independent sources, all indistinguishable "
       "from zero with tight intervals (staple: −9% [−24, +10] against a raw gap of +53%). Prior "
       "work (e.g., Bosker et al. 2013) showed institution coefficients shrink under fixed "
       "effects; this is a direct before/after test of the grants themselves.", "1.")
bullet("The urban hierarchy's origins are decomposed, with institutions inside the decomposition. "
       "The Shapley split — 46% inherited size, 20% deep (800 AD) origin, 2.5% geography direct, "
       "3.2% institutions, 29% unexplained — bounds the institutional contribution at a few "
       "percent even as pure correlation, and the residual-persistence test (autocorrelation "
       "−0.10/−0.16) shows the unexplained share behaves like noise, not like an omitted stable "
       "cause. Persistence quantified to 800 AD (r² = 0.40 across 700 years) puts a number on "
       "‘deep roots’ claims usually made qualitatively.", "2.")
bullet("An explicit implied-size benchmark turns ‘over-performance’ into a measured quantity per "
       "city (Hamburg 9.7×, Mainz 0.5×), and the residuals line up on one axis: water.", "3.")
bullet("The summary equation is validated as a predictor, out of sample: R² = 0.56 for the 1500 "
       "hierarchy from 1200 data alone, 8/10 of the largest cities identified — against "
       "R² = 0.02 for growth — and shown to sit near the information ceiling (flexible models "
       "with every 1200-vintage feature: 0.61). Its one systematic failure (real concentration "
       "outrunning the simulated law, Zipf 1.08 vs 1.22) isolates top-end agglomeration as the "
       "single force a random walk cannot mimic.", "4.")
bullet("The Black Death emerges as the switch that turned the water premium on: negative for "
       "plague-port basins in 1300–1400, strongly positive everywhere after, with post-plague "
       "winners disproportionately on water.", "5.")

# ================================================================ 11
h1("11. What This Means")
para("The story in which a wise ruler's grant of staple or market rights created a great city "
     "reverses the actual causal arrow. Rulers granted privileges to places that were already "
     "rising — usually because water access or Roman-era roots had put them on the map centuries "
     "earlier. The privilege was recognition of success, drawn up after the fact; it was not the "
     "cause. None of this makes charters unimportant to medieval life — they shaped law, "
     "liberty, and identity — but they do not explain who grew.")
para("What does explain who grew is boring, which is the point. A city's fortune was set by where "
     "it sat in the landscape of trade — above all, whether goods could reach it by water — and "
     "by how early it had established itself, because size carried itself forward across "
     "centuries at a rate of 0.915 per century. Around that skeleton, individual fates were "
     "shuffled by shocks no equation predicts: a residual five times larger than the systematic "
     "pull. Policy operated at the margins of a system whose destiny was mostly mapped before "
     "the policies existed. If there is a lesson for the long run of cities, it is humility about "
     "recipes: the levers everyone argued about moved almost nothing, the ones nobody could move "
     "— rivers, coasts, head starts — moved almost everything, and a large remainder was luck.")

# ================================================================ refs
h1("References")
for ref in [
    "Bairoch, P., Batou, J., & Chèvre, P. (1988). La population des villes européennes de 800 à "
    "1850. Geneva: Droz.",
    "Bosker, M., Buringh, E., & van Zanden, J. L. (2013). From Baghdad to London: Unraveling urban "
    "development in Europe, the Middle East, and North Africa, 800–1800. Review of Economics and "
    "Statistics, 95(4), 1418–1437.",
    "Buringh, E. (2021). The population of European cities from 700 to 2000. Research Data Journal "
    "for the Humanities and Social Sciences, 6(1), 1–18.",
    "Cantoni, D., Mohr, C., & Weigand, M. (2020). Princes and townspeople: Dated town charters and "
    "market rights from the Deutsches Städtebuch.",
    "Dittmar, J. (2011). Cities, markets, and growth: The emergence of Zipf's law. Working paper.",
    "Gabaix, X. (1999). Zipf's law for cities: An explanation. Quarterly Journal of Economics, "
    "114(3), 739–767.",
    "Gibrat, R. (1931). Les inégalités économiques. Paris: Sirey.",
    "Holterman, B., et al. Viabundus: Map of premodern European transport and mobility, 1350–1650.",
    "Israeli, O. (2007). A Shapley-based decomposition of the R-square of a linear regression. "
    "Journal of Economic Inequality, 5(2), 199–212.",
    "Jedwab, R., Johnson, N. D., & Koyama, M. (2024). Medieval cities through the lens of urban "
    "economics.",
    "Shorrocks, A. F. (1982). Inequality decomposition by factor components. Econometrica, 50(1), "
    "193–211.",
]:
    p = doc.add_paragraph(ref)
    p.paragraph_format.space_after = Pt(4)
    for r in p.runs:
        r.font.size = Pt(9.5)

doc.save(DOC)
print(f"saved {DOC}")
