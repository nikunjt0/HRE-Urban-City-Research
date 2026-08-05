# Null-model diagnostics — HRE cities, Buringh panel (415 HRE-core cities)

## 1. Persistence (path dependence)
- log(pop1500) ~ log(pop1200): **R²=0.47**, β=0.86 (n=363)
- log(pop1300) ~ log(pop1200): R²=0.75, β=0.97
- ~Half of a city's 1500 size is locked in by its 1200 size. β<1 ⇒ mild regression to the mean.

## 2. Gibrat's law — growth is near-random w.r.t. size
- 1200→1300: slope −0.03 (p=0.28), **R²=0.003** — Gibrat holds exactly.
- 1300→1400: slope −0.09, R²=0.026 (Black Death, mean g=−0.18).
- 1400→1500: slope −0.11, R²=0.038 (recovery, mean g=+0.41).
- Growth SD ≈ constant across size terciles (0.67 / 0.69 / 0.69).
- **KEY:** within a period, city size explains 0.3–4% of growth. Growth ≈ common time shock + idiosyncratic noise. This is WHY any factor-on-growth model has a ceiling near R²≈0.05. It is not a data problem.

## 3. Zipf's law — the size distribution is CONCENTRATING (structural transition)
- ζ(1200)=1.316 → ζ(1300)=1.159 → ζ(1400)=1.078 → ζ(1500)=1.019
- ζ falls monotonically toward 1. The HRE urban system moved from a relatively FLAT
  distribution (1200) to an exactly-Zipf/primate distribution (1500).
- ⇒ Big cities pulled away from small ones. Signature of agglomeration / increasing returns.

## 4. Spatial autocorrelation — growth CLUSTERS in space
- Moran's I (1200→1500 growth, 6-NN) = **+0.171** (expected ≈ 0). Strong positive.
- Neighbouring cities grow together ⇒ the driver of growth is RELATIONAL/SPATIAL,
  not city-internal.

## Synthesis → the hypothesis to test
Growth is unpredictable from what a city *is* (Gibrat), yet (a) the distribution is
concentrating and (b) growth clusters spatially. Both point away from internal
institutions and toward **position in the trade network**. Next: build market access /
centrality on the real Viabundus transport graph and test whether NETWORK POSITION
explains the spatial clustering and the divergence — controlling for first-nature
geography (river/coast) and initial size.
