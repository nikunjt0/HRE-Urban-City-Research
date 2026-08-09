# Prediction evaluation & decomposition transparency

Sample: Central/North Europe (in_cne), pop>=1000, Buringh panel.

## A. Building the decomposition step by step (R2 ladder)

Candidate explanations of log pop1500, entered alone and together:

| model | R2 | n |
|---|---|---|
| institutions only (privilege-observable universe) | 0.235 | 222 |
| geography only (river/coast/basin/elevation) | 0.089 | 1208 |
| deep history only (log pop 800) | 0.396 | 551 |
| inherited size only (log pop 1200) | 0.560 | 1092 |
| geography + inherited size | 0.575 | 1092 |
| geography + deep history + inherited size | 0.693 | 551 |
| geo + inherited + institutions (privilege universe) | 0.611 | 196 |

Same 196 privilege-universe cities: unexplained share without institutions = 0.433, with = 0.389 (institutions recover 0.044 of the 0.433).

## A2. Shapley shares

Headline three-group split on the full sample (privileges cannot enter here honestly: their status is only observed inside each source's coverage area). Institutions are then bounded on the privilege-observable universe (inside both the Viabundus footprint and the Städtebuch area), where all four statuses are measured. NOTE: all shares are shares of predictive R2 — descriptive accounting, not causal attribution.


3-group, full sample: total R2 = 0.693 (n=551); unexplained = 0.307

| group | share of explained | share of total variance |
|---|---|---|
| geography | 3.8% | 0.026 |
| deep_history_800 | 27.5% | 0.190 |
| inherited_1200 | 68.7% | 0.476 |

3-group with institutions, privilege-observable universe: total R2 = 0.611 (n=196); unexplained = 0.389

| group | share of explained | share of total variance |
|---|---|---|
| geography | 9.1% | 0.056 |
| inherited_1200 | 71.9% | 0.439 |
| institutions | 19.0% | 0.116 |

## A3. Is the unexplained 31% a stable hidden factor, or noise?

Correlation of a city's growth residual with its residual next century: 1200/1300 vs 1300/1400: r=-0.10; 1300/1400 vs 1400/1500: r=-0.16 (n=1091). A stable omitted city trait would push these toward 1; values ~-0.13 mean only ~-13% of a shock carries into the next century's residual.


## B. 'Implied size from 1200' made explicit

Fitted rule across 1092 cities: log pop1500 = 1.34 + 0.86 x log pop1200 + 0.14 x water, R2=0.566. A city's 'implied 1500 size' is this fitted value; its performance is the residual (actual minus implied), in log points.


## C. Does the equation actually predict 1500 sizes?

Estimated law: b=0.915, c_water=0.060, sigma=0.403, a_t = 1200:+0.88, 1300:+0.35, 1400:+1.03

| predictor of 1500 size (from 1200 info only) | R2 (log size) | rank corr | median miss | within x1.5 | within x2 | top-10 hit |
|---|---|---|---|---|---|---|
| guess the average for every city | 0.000 | nan | x1.63 | 26% | 62% | 0/10 |
| frozen map: size1500 = size1200 | 0.385 | 0.688 | x1.50 | 54% | 60% | 8/10 |
| equation without water | 0.553 | 0.688 | x1.49 | 55% | 80% | 8/10 |
| THE EQUATION (size + water + shocks) | 0.559 | 0.688 | x1.56 | 49% | 81% | 8/10 |
| the equation, privilege-universe cities (n=196) | 0.507 | 0.661 | x1.60 | 35% | 80% | 5/10 |
| equation + all four privileges (n=196) | 0.552 | 0.688 | x1.63 | 42% | 78% | 6/10 |


Same equation asked to predict GROWTH 1200->1500 instead of size: R2 = 0.022. It knows where the hierarchy stands, not who moves.

Out-of-sample check: fit the law on a random half of cities, predict the other half (200 draws): R2 = 0.557 [0.508, 0.605] — essentially identical to in-sample 0.559; the equation is not overfit.


## D. Temporal-leakage check: law estimated on pre-1200 transitions only

Pre-1200 law (transition counts {'1000': 817, '1100': 945, '800': 550, '900': 653}): persistence b=0.973, water c=0.045, mean pre-1200 century drift a=+0.380, sigma=0.290. Coefficients locked before 1200.

| predictor (trained only on 700–1200 data) | R2 (log size) | rank corr | median miss | within x1.5 | within x2 | top-10 hit |
|---|---|---|---|---|---|---|
| pre-1200 law, strict ex-ante | 0.498 | 0.688 | x1.68 | 43% | 76% | 8/10 |
| pre-1200 law + one overall level correction | 0.563 | 0.688 | x1.42 | 56% | 81% | 8/10 |
| pre-1200 GBM (all geo features), strict | 0.341 | 0.691 | x1.57 | 46% | 66% | 0/10 |
| pre-1200 GBM + one overall level correction | 0.360 | 0.691 | x1.62 | 44% | 73% | 0/10 |

The strict forecasts miss the common post-1200 growth acceleration (mean level error -0.23 log: the centuries after 1200 were faster than those before). A level miss shifts every city equally, so it cannot reorder the hierarchy — rank correlation and top-10 identification are unaffected. Allowing one overall level correction (a single scalar; no city-specific or post-1200 cross-sectional information), the pre-1200 law reaches R2 = 0.563, against 0.56 for coefficients fitted on the 1200–1500 transitions themselves.
