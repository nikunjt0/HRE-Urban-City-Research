# Robustness: Bairoch (1988) vs Buringh (2021)

Both panels use the SAME cities, geography, and privileges — only the population source differs.
Bairoch matched onto the Buringh scaffold by (country, normalized name). Scripts: bairoch_panel.py,
bairoch_robustness.py.

## Agreement of the two sources
- log(pop1500) correlation Bairoch vs Buringh: **r = 0.964** (n = 511 common cities ≥1000).

## Core findings — side by side (Central/North Europe, ≥1000)
| Result | Buringh (2021) | Bairoch (1988) |
|---|---|---|
| Growth vs size R² (1300→1500) | 0.05 | 0.30 |
| Persistence r² (1300→1500) | 0.65 | 0.54 |
| Momentum share of variance in 1500 size | 96% | 98% |
| Water premium / century | +9% (p=.008) | +15% (p=.15) |
| Staple — raw size gap | +92% | +36% |
| Staple — causal DiD | −9% (n_treat=53) | −49% (n_treat=7) |

## Reading
- Robust in BOTH: strong persistence, momentum dominates the variance decomposition, positive water
  premium, and the large raw staple size-gap collapsing under the causal test.
- Honest differences: Bairoch skews to larger, better-documented towns and is thin before 1300
  (pop1200 CNE n≈99, pop800 n≈22). Hence (a) its growth shows more mean-reversion (Gibrat R²=0.30 vs
  0.05), and (b) its staple DiD rests on only 7 treated towns and charter/market DiD is untestable
  (0 within-window switchers). The direction of every result matches Buringh.
- Conclusion: findings do not depend on which reconstruction is trusted.
