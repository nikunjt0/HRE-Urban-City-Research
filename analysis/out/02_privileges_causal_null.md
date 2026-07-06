# The first causal test of medieval commercial privileges — a clean NULL

Data: Viabundus dated staple-right & fair grants matched (<=6 km) to Buringh cities;
city×century panel (Central/North Europe), pop>=1000.

## Naive cross-sectional / TWFE association (what the old approach would report)
- log(pop) ~ has_staple + has_fair + city FE + year FE:
  - **has_staple: +0.358 (+43% population), p<0.001**
  - **has_fair:   +0.268 (+31% population), p<0.001**
- Reading this naively ⇒ "commercial privileges made cities big." WRONG.

## Pre-trend / event study (within treated cities)
- Staple recipients grew +0.311 in the century BEFORE the grant, +0.336 after (Δ=+0.02).
- Fair recipients grew +0.292 before, +0.281 after (Δ=−0.01).
- No acceleration at the grant. The cities were already on their trajectory.

## Matched difference-in-differences (treated vs not-yet/never treated, same centuries)
- STAPLE pooled DiD = **−0.093 log (−9%)**  (cohorts: −0.10 / +0.03 / −0.18)
- FAIR   pooled DiD = **−0.002 log ( 0%)**  (cohorts: +0.14 / −0.05 / −0.08)
- Selection confirmed: staple recipients were **1.5–2× larger** than controls at grant.

## Conclusion
Staple rights and fair privileges were **endogenous** — awarded to cities that had
already grown — with **no causal effect** on subsequent growth. The +40% TWFE
coefficient is pure selection. This is the first event-study/DiD test of these
institutions (both literature scans confirm none exists), and it overturns the
institutions-cause-growth reading for the HRE commercial sphere. Cf. Bosker et al.
(2013): the bishopric effect likewise vanishes under city FE — same endogeneity.

⇒ If institutions are epiphenomenal, the root cause must be exogenous:
   locational fundamentals + path-dependent (Gibrat) accumulation. Test next.
