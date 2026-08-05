# HRE Urban City Research

Quantitative history of European cities, 800–1800: what actually made them
grow — geography, institutions, or politics? Two papers, each with its own
self-contained code + outputs directory under `papers/`.

## Layout

```
papers/
  city_growth/     Paper 1 — "Why did medieval cities get big? A causal reappraisal"
    *.py           analysis pipeline (see Reproduce below)
    out/           FINDINGS.md, PAPER.pdf/html, figures/, derived panels
  politics/        Paper 2 — "The Boring-Ruler Hypothesis" (politics & policy audit)
    *.py           analysis pipeline
    out/           FINDINGS_POLITICS.md, PAPER_POLITICS.html, figures/,
                   regression JSONs, derived panels
docs/              source datasets (shared by both papers)
  European_Population_data_Buringh/      city populations 700–2000 (primary outcome)
  bairoch_pop_data/                      Bairoch 1988 populations (robustness)
  viabundus/                             medieval transport network + staples/fairs
  city_locations_and_border_maps/        Cantoni–Weigand city_id gazetteer (2,390 cities)
  territorial_histories/                 Cantoni–Mohr–Weigand annual ruler panel 1300–1789
  town_charters_and_first_mentions/      dated charters + legal families
  markets/  construction_data/  conflicts_and_war/   more Städtebuch modules
  external/                              downloaded replication datasets (Bosker et al.
                                         "From Baghdad to London", van Zanden parliaments,
                                         Kokkonen–Sundell monarchs, ...) — per-dir READMEs
  *.pdf                                  reference papers
```

## Paper 1 — city growth (geography & path dependence)

Headline: commercial privileges (staple rights, fairs) had zero causal effect;
city size was set by water access + early start, carried by a near-unit-root
random-growth process. Read `papers/city_growth/out/FINDINGS.md`.

Reproduce (cwd = `papers/city_growth/`): `panel.py` → `diagnostics.py` →
`network.py`/`build_network_cache.py` → `analyze_network.py` →
`water_timing.py` → `privileges.py` → `privilege_did.py` →
`plague_reversion.py` → `synthesis.py` → `generative_model.py` →
`make_figures.py` → `build_paper.py`.

## Paper 2 — politics & policy (the boring-ruler hypothesis)

Headline: WHO ruled explains ~0.5% of growth variance (2,903 dynastic
extinctions as a natural experiment); communes, church-vs-secular rule and
secularization are nulls; what served cities was ruler stability, not being
pledged/occupied/foreign-run, capital status, and parliamentary eras.
Read `papers/politics/out/FINDINGS_POLITICS.md`.

Reproduce (cwd = repo root): `papers/politics/build_crosswalk_cityid.py` →
`classify_rulers.py` → `build_regime_panel.py` → `analyze_regimes.py` →
`build_decadal_panel.py` → `decadal_twfe.py` → `event_studies.py` →
`extinction_consolidation.py` → `analyze_europe.py` → `europe_robustness.py` →
`timing_and_succession.py` → `secularization_es.py` → `dynasty_league.py` →
`make_figures_politics.py` → `build_paper_politics.py`.

## Environment

Plain `python3` (3.11) with pandas, numpy, statsmodels, scipy, scikit-learn,
linearmodels, matplotlib, openpyxl (and geopandas for the shapefiles).

## History

An earlier composite-index pipeline (hand-built factor scores regressed on
growth; holdout R² = −1.75) lived at the repo root with `lib/` and `output/`;
it was superseded by Paper 1 and removed in the reorganization — see git
history if needed.
