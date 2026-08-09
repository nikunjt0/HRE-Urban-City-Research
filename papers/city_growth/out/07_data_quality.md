# Data quality: imputation, source overlap, thresholds

Imputed/proxied share of city-year observations (CNE, pop>=1k, 1200-1500): **80.6%** (by year: {1200: 0.949, 1300: 0.791, 1400: 0.801, 1500: 0.694}). Observations whose source field cites Bairoch: 7.1% — the two reconstructions overlap and are not fully independent.

## Core results, all vs non-imputed observations (threshold 1,000)

| sample | n(1200&1500) | persistence r2 | Gibrat R2 | water premium | staple DiD |
|---|---|---|---|---|---|
| all observations | 1092 | 0.560 | 0.025 | +0.143 (p=0.000) | -0.075 (nT=65) |
| non-imputed only | 40 | 0.275 | 0.248 | +0.323 (p=0.138) | -0.129 (nT=4) |

## Population-threshold robustness (all observations)

| threshold | n(1200&1500) | persistence r2 | Gibrat R2 | water premium | staple DiD |
|---|---|---|---|---|---|
| 1,000 | 1092 | 0.560 | 0.025 | +0.143 (p=0.000) | -0.075 (nT=65) |
| 5,000 | 153 | 0.517 | 0.002 | +0.126 (p=0.178) | -0.059 (nT=17) |
| 10,000 | 59 | 0.485 | 0.005 | +0.140 (p=0.361) | -0.368 (nT=3) |