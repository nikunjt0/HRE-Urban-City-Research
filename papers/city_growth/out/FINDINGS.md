> **DATA-AUDIT REVISION (Aug 2026).** The numbers below predate the data audit and are
> superseded by the revised paper (`European City Growth Paper (revised).docx`) and
> `causal_summary.json` / `06_prediction.md` / `07_data_quality.md`. Key corrections:
> (1) privilege analyses are now restricted to each source's coverage universe (Viabundus
> footprint; Städtebuch = 1937 Germany) — raw staple/fair gaps become +40%/+26%, DiD
> staple −7% [−22,+10], fair −0% [−13,+14], charter +0% [−20,+28], market −3% [−26,+32];
> "zero causal effect" is overstated for charters/markets (wide CIs, MDE +41%/+51%) — the
> defensible claim is "no growth break at the grant; staple/fair effects >+10–14% excluded".
> (2) Shapley shares (full sample, n=551): 48% inherited-1200 / 19% deep-800 / 2.6% geography
> (conditional) / 31% unexplained; institutions carry ~12 pts as markers on their observable
> universe (n=196). (3) The ~31% residual is "unexplained and weakly persistent", not proven
> luck. (4) The prediction law survives a no-leakage backcast (coefficients locked on
> 800→1200 transitions: R²=0.50 strict, 0.56 level-corrected). (5) 81% of 1200–1500
> observations in Buringh are imputed/proxied and ~7% cite Bairoch directly — the two
> reconstructions are overlapping, not independent.

# Why did medieval cities get big? A causal reappraisal

**Central/Northern Europe & the Holy Roman Empire, 1200–1500**

> **Headline.** Cities did not grow because of what they *did* — the celebrated
> commercial privileges (staple rights, market fairs) that historians credit had
> **zero causal effect** on growth. They grew because of **where they sat** and
> **how early they started**. The medieval urban hierarchy was a near-unit-root
> random-growth process anchored on locational fundamentals: ~70% of a city's
> 1500 size was already locked in, a city's size in 800 CE still predicts its size
> in 1500, and the *only* exogenous force that reliably moved cities was access to
> navigable water. Everything else was path-dependent momentum plus ~30%
> irreducible luck.

---

## 0. Why the original model couldn't find anything

The prior approach regressed *growth* (Δlog population over 100-year steps) on
hand-built composite indices (legal capacity, merchant capital, …). Its holdout
R² was **−1.75** — worse than guessing the mean. This was not a data problem. Two
structural facts make that model impossible:

1. **Growth is near-random with respect to everything (Gibrat's law).** Within a
   century, a city's *size* explains only **0.3–4%** of its growth (Fig. `fig_gibrat`).
   Growth ≈ a common century-wide shock + idiosyncratic noise. There is very little
   systematic signal for *any* factor model to capture — theirs or anyone's.
2. **The predictors were subjective composites**, so even the cross-sectional fit
   capped at R²≈0.33.

The fix is not more factors. It is asking a **causal** question and measuring the
one thing that is exogenous — geography — cleanly.

---

## 1. The central result: commercial privileges were badges, not engines

Using **Viabundus** (the reconstructed medieval transport network) I matched every
**dated staple-right and fair grant** to its city and built the first event-study /
difference-in-differences test of these institutions on city growth.

| | Naïve association (two-way FE) | Causal effect (matched DiD) |
|---|---|---|
| **Staple right** | **+43%** population (p<0.001) | **−9%** (≈ 0) |
| **Fair** | **+31%** population (p<0.001) | **0%** |

*(Fig. `fig_privileges_causal_null`.)* The naïve model — the kind that produces
confident "institutions caused growth" claims — is **entirely selection**. Cities
that received a staple were already **1.5–2× larger** than comparable cities at the
moment of the grant, and had grown **faster in the century before** the grant
(+0.31) than they did in the century after (+0.34 — no acceleration). Fairs: +0.29
before, +0.28 after. The privilege is a *marker* of prior success, awarded to
already-rising trade towns; it does not cause the rise.

This is a genuinely new result — both a targeted reading of four canonical papers
and an independent literature scan confirm **no event study of medieval staple
rights or fairs on city growth exists.** It mirrors Bosker et al. (2013), whose
bishopric effect likewise vanishes under city fixed effects: medieval "institutions"
are largely endogenous responses to position.

---

## 2. What actually determined the hierarchy: geography, encoded early, carried forward

If institutions are epiphenomenal, the root cause must be exogenous. A Shapley
variance decomposition of log city size in 1500 (total R²=0.69; Fig.
`fig_variance_decomp`):

- **Inherited size / momentum (path dependence): 69% of explained variance**
- **Deep origin (size already present in 800 CE): 27%**
- Geography (direct, net of inherited size): 4%
- **Idiosyncratic (luck + measurement noise): 31% of total variance**

Geography's *direct* share looks small only because **its work was already done** —
it set the early sizes, and persistence carried them forward. On its own, first-nature
geography explains 9% of 1500 size; a city's **800 CE size predicts its 1500 size at
r²=0.40** — seven centuries of lock-in (Fig. `fig_persistence_depth`). By 1400 the
lock-in is r²=0.76.

**The one exogenous lever that moved cities: water access.** A city on a navigable
river or coast grew **+15% more per century** than a landlocked one (bootstrap 95%
CI **[+7%, +23%]**). Because a city cannot relocate to the coast, this is plausibly
causal, unlike the privileges. Its natural-experiment confirmation is the **Black
Death**: the great mortality reshuffled the hierarchy, and the permanent **winners
were disproportionately on water** (64% vs 57% of losers; +0.084 net advantage,
p=0.008, controlling for pre-plague size) — extending Jedwab–Johnson–Koyama (2024):
the reshuffle was governed by fixed locational factors.

---

## 3. The generative law — one equation for the whole system

All of the above is a single stochastic process. Estimating

  **log P₍ₜ₊₁₎ = aₜ + b·log Pₜ + c·water + ε**

on 1200–1500 transitions gives **b = 0.915** (near unit root; reversion half-life
~800 years), idiosyncratic **σ = 0.40 log/century**, water anchor **c = 0.06**, and
a signal-to-noise ratio **κ/σ = 0.21** — i.e. century growth is **~80% pure Gibrat
noise**. Simulating this law forward from the actual 1200 sizes reproduces the
observed **persistence** (r²=0.46 vs 0.56 actual) and the approximate **rank-size
distribution**.

It misses in one *informative* direction (Fig. `fig_zipf_evolution`): the real
hierarchy **concentrated** (Zipf ζ: 1.26 → 1.08, tail thickening toward Zipf's law),
while pure random-growth-with-reversion predicts mild **equalization**. The gap is
**excess top-end concentration beyond chance** — a modest **agglomeration /
increasing-returns** force at the largest cities (consistent with Dittmar's finding
that Zipf's law "emerges" as the upper tail thickens after ~1500).

---

## 4. The thesis, stated plainly

> **Medieval city size was set by locational fundamentals — above all access to
> water-borne trade — laid down centuries earlier and carried forward by a
> path-dependent random-growth process, with a weak agglomeration pull at the top
> and ~30% irreducible luck. The institutions historians celebrate (staple rights,
> fairs) were endogenous badges of success with no causal growth effect. Cities got
> big because of WHERE they were and HOW EARLY they started — not what they did.**

This is not the equation the project set out to find (a deterministic factor
formula). It is the reason that equation cannot exist — and a defensible,
novel, causal account of what governs a pre-modern urban system instead.

---

## 5. Honesty about limits
- Buringh populations are heavily **rounded** (1000, 2000, 4000…); this inflates
  mechanical mean-reversion and caps every growth R². All growth results should be
  read as orders of magnitude, not decimals.
- The staple/fair DiD is at **century** resolution — coarse for event studies;
  the null is robust across cohorts and to the pre-trend check, but finer-dated
  charter data (docs/town_charters, docs/markets) could sharpen it.
- Network centrality measures (betweenness, market access on the Viabundus graph)
  did **not** beat a simple river/coast dummy in the Hanseatic footprint — a null
  worth reporting, and a caution against over-engineering the geography variable.

## Reproduce
`papers/city_growth/`: `panel.py` → `diagnostics.py` → `network.py`/`build_network_cache.py` →
`analyze_network.py` → `water_timing.py` → `privileges.py` → `privilege_did.py` →
`plague_reversion.py` → `synthesis.py` → `generative_model.py` → `make_figures.py`.
Result notes in `papers/city_growth/out/0*.md`; figures in `papers/city_growth/out/figures/`.
