# Whose politics served the people? A causal audit of European rule, 800–1800

**Companion to** `analysis/out/FINDINGS.md` (which showed: geography + path
dependence set city fortunes; commercial privileges were endogenous badges).
This paper asks the question that one left open: **if the celebrated local
institutions didn't matter, did ANY politics matter — and which rulers'
policies actually served their people?**

**Data assembled for this round**
- Cantoni–Mohr–Weigand *Princes and Townspeople*: annual ruling-lineage panel
  for all 2,390 German cities 1300–1789 (1.16M city-years), + dated town
  charters, market grants, construction events (19.6k), conflict incidents.
- Bosker–Buringh–van Zanden *From Baghdad to London*: 792 cities, Europe+MENA,
  800–1800, with communes, parliaments (van Zanden et al. activity index),
  capitals, universities, plunderings, and the De Long–Shleifer regime coding.
- Kokkonen–Sundell monarch database: 693 monarchs, 27 states, 1000–1799
  (succession law, tenure, depositions).
- 7,353 ruling lineages hand-classified into church / self-rule / secular
  noble; 9,819 ruler-change events extracted, of which **2,903 caused by the
  biological extinction of the ruling line — a natural experiment in
  quasi-random ruler change**.

---

## 1. The verdict in one figure

*(fig_political_ledger.png)* Ranked by what a city actually experienced:

**Served the people (robust positives)**
1. **Being made a capital** (+0.23 log pts/century, city FE) — the single
   largest policy lever a ruler had. Prosperity followed the court.
2. **Living under an active parliament** (+0.09 per 1 sd of activity, p=0.004,
   city FE; survives dropping England & the Netherlands, Atlantic controls,
   country clustering). The classic "constrained executive" — but see §4:
   its *timing* cannot be causally pinned (levels work, changes don't).
3. **A ruler who stayed on the throne.** Each 1 sd of the national deposition
   rate cost cities ~19% growth per century (p=0.02). De-jure succession law
   (primogeniture) had **no direct effect** — realized stability, not paper
   rules, is what mattered.

**Harmed the people (robust negatives)**
4. **Being pledged to creditors** (Verpfändung): −2.3%/century per 1 sd of
   time-pledged in the population panel (p=0.01); independently negative on
   construction activity in all 2,390 cities (p=0.03). The clearest
   "extractive policy" in the data: rulers who mortgaged their towns for cash
   mortgaged their subjects' growth.
5. **Foreign rule**: −0.026 asinh construction per decade (p=0.0001).
6. **Ruler turnover itself.** The extinction natural experiment (1,316 clean
   events, flat pre-trends): a quasi-random change of ruler depressed
   construction ~1.3% for the following half-century (p=0.03) — under *every*
   type of successor.

**Made no difference (precisely estimated nulls)**
- **Commune / urban self-governance** (Europe-wide, city FE, event study —
  flat). The commune movement joins staple rights and fairs as a badge.
- **Church vs secular lord** (German panel). Bishops' cities *look* more
  active only because bishops built churches: the effect vanishes when only
  economic construction is counted.
- **Secularization.** Even the Reformation's great expropriation — 150 dated
  transfers of cities from church to secular rule, 382 church→noble
  transitions in all — left city trajectories unchanged (pre ≈ post in both
  total and economic construction).
- **Self-rule in the German panel**; **primogeniture**; **university
  foundations** (within-city); **ruler turnover frequency** once instability
  spells are controlled.

## 2. Who ruled explains 0.5% of anything

A hierarchical decomposition over 83 major lineages (dynasty league,
*fig_dynasty_league.png*): true between-lineage differences in
growth-vs-fundamentals have sd ≈ **3.6%/century** against a residual sd of
**50%/century** — i.e. **the identity of the ruler explains ~0.5% of the
variance in a city's growth** (χ²(83)=109, p=0.03: real, but minuscule).
Swapping the *worst* dynasty for the *best* (≈8%/century) is worth about half
of simply being on a navigable river (+15%/century, prior paper).

The league itself tells the political story compactly:
- **Top:** Hohenzollern-Brandenburg (68 cities, +4%/cy sustained for five
  centuries — the great consolidator), Habsburg's Leopoldine line, the
  Teutonic Order, Bamberg's prince-bishops, and the *great* free cities
  (Köln +14%, Augsburg +16%, Lübeck +12%).
- **Bottom:** the prince-elector **Archbishops of Köln (−12%/cy)** — while the
  *free city* of Köln, same river, same century, sits in the top ten. Also:
  small ossified imperial cities (Kempten −30%, Goslar −30%, Rothenburg −15%),
  Poland's Vasa kings, and the Spanish-Habsburg line.

## 3. Liberty needed scale

The commune null hides sharp heterogeneity: **commune × log-size interaction
+0.105 (p=0.005)** in the European panel. Self-governance paid in *large*
commercial cities (+15%/century one log-point above mean size) and did nothing
or worse in small towns (*fig_liberty_scale.png*). This reconciles the
literature: studies sampling big cities (Bosker et al.) find positive commune
effects; full samples find nulls; Stasavage's "city-states ossify" shows up
here as the small Reichsstädte at the bottom of the league. (Within-city the
interaction attenuates, p≈0.21 — treat as heterogeneity, not gospel.)

## 4. What "constrained government" evidence really shows

- Naive De Long–Shleifer at city level: +0.10 (p=0.003). City FE: +0.08
  (p=0.07). **Country clustering: p=0.42** — the classic result is a
  country-era pattern, not a city-level treatment.
- The *event dynamics* look right (flat pre-trend, +0.20/+0.21/+0.14 after
  becoming "free", *fig_freeprince_eventstudy.png*), and gains help while
  losses don't hurt (institutional stickiness).
- Parliament activity is the robust version (survives everything in levels) —
  **but Δparl_act does not predict growth (p=0.99), and future parl_act
  "predicts" growth almost as well as current (p=0.055 vs 0.017)**.
  Parliaments and prosperity rose together over generations; century-grain
  data cannot separate cause from co-evolution. Anyone claiming otherwise
  from this kind of panel is over-reading it.

## 5. The extinction experiment: rulers as interchangeable weather

When a ruling line died out, cities were reassigned quasi-randomly (pre-trends
flat). Results (*fig_event_dynamics.png*, JSONs):
- Any change: −1.3% construction for ~5 decades (p=0.03).
- New ruler church vs noble: **no difference**.
- Passing to a ≥2× larger state: **no dividend** within 50 years; economic
  construction if anything *lower* (−0.9%, p=0.08). State consolidation was
  disruption without payoff on any horizon citizens lived to see — the
  consolidators' league-table premium (Hohenzollern) is a centuries-scale,
  selection-laden phenomenon, not a transition dividend.

## 6. The thesis, stated plainly

> **In pre-modern Europe, politics served the people not through WHO ruled or
> WHAT CHARTER the city held, but through three things: STABILITY (rulers who
> kept their thrones and their solvency), NON-EXTRACTION (cities never used as
> collateral, never occupied, never foreign-administered), and STATE
> ATTENTION (capital status; the slow co-evolution of parliamentary
> bargaining). Ruler identity — dynasty, church or lay, native or magnate —
> explains half a percent of the variance in urban fortunes. The best
> "policy" a medieval or early-modern ruler could give a city was to be boring:
> stay alive, stay solvent, stay put, and let the river do the work.**

## 7. Position in the literature (novelty audit, adversarially checked)

- **Extinctions as treatment: novel.** Cantoni–Mohr–Weigand (Econometrica
  2024) validated dynastic extinction as quasi-random but used it only as a
  *placebo* for their fiscal-capacity results. Flipping it into a treatment
  for city-level outcomes — and finding rulers interchangeable — is new. It
  is the city-level counterpart (and counterpoint) to Ottinger–Voigtländer
  (Econometrica 2025), who show ruler *ability* moves state-level outcomes:
  ability may matter at the apex; the *identity/type* of the local lord did
  not matter to his towns.
- **Pledging: first quantitative estimate ever.** The Verpfändung literature
  (Landwehr 1967 → Frauenknecht 2018) is entirely qualitative and currently
  *revisionist* — the modern view holds pledging was benign. Our panel
  estimates (negative in two independent outcome datasets, dose-dependent;
  onset dynamics smeared) push back: pledging was not benign where it was
  prolonged.
- **Commune null: partly novel.** Stasavage (APSR 2014) ran within-city FE
  and found positive-then-ossifying autonomy effects in 173 large cities; our
  full-sample event-study null + the size interaction (§3) reconciles his
  result with ours: his sample *is* the upper tail where liberty paid.
- **Parliament timing: the test vZBB never ran.** Van Zanden–Buringh–Bosker's
  own paper contains city-FE activity-index regressions (positive); we
  replicate, then show changes don't predict growth and leads nearly do —
  the within-dataset confirmation of Abramson–Boix's endogeneity critique.
- **Depositions → city growth: new link.** The succession literature stops at
  political outcomes (tenure, coups); we race realized stability against
  de-jure rules for *urban* outcomes and find only realized stability priced.

## 8. Honesty about limits
- Populations remain rounded (Buringh) and century/half-century grained; the
  German population sample is 278 cities — construction (2,390 cities,
  decadal) carries the within-city dynamics.
- Construction counts are a proxy (activity, not welfare); religious/secular
  composition handled, but Städtebuch reporting intensity varies by era
  (Thirty Years' War over-documented; controlled with destruction counts and
  decade FE).
- The parliament-activity and capital effects are levels relationships;
  timing tests fail (parliaments) or are untested (capitals move rarely).
  Deposition and pledging effects could still reflect unobserved local shocks
  correlated with both fiscal distress and decline, though city FE +
  century FE + (for pledging) two independent outcome datasets narrow this.
- Lineage classification by name-parsing (church/self/noble) is coarse;
  misclassification biases type contrasts toward zero.
- Sample selection: Städtebuch = 1937 German borders; Buringh = cities ever
  ≥5k. Small-town politics may differ.

## Reproduce
`analysis/politics/`: `build_crosswalk_cityid.py` → `classify_rulers.py` →
`build_regime_panel.py` → `analyze_regimes.py` → `build_decadal_panel.py` →
`decadal_twfe.py` → `event_studies.py` → `extinction_consolidation.py` →
`analyze_europe.py` → `europe_robustness.py` → `timing_and_succession.py` →
`secularization_es.py` → `dynasty_league.py` → `make_figures_politics.py`.
Outputs in `analysis/out/politics/` (JSONs per analysis + figures/).
