# Prediction evaluation & decomposition transparency

Sample: Central/North Europe (in_cne), pop>=1000, Buringh panel.

## A. Building the decomposition step by step (R2 ladder)

Candidate explanations of log pop1500, entered alone and together:

| model | R2 | n |
|---|---|---|
| institutions only (staple/fair/charter/market by 1500) | 0.045 | 1208 |
| geography only (river/coast/basin/elevation) | 0.089 | 1208 |
| deep history only (log pop 800) | 0.396 | 551 |
| inherited size only (log pop 1200) | 0.560 | 1092 |
| geography + inherited size | 0.575 | 1092 |
| geography + deep history + inherited size | 0.693 | 551 |
| ALL FOUR (adding institutions) | 0.710 | 551 |

Same 551 cities: unexplained share 3-group = 0.307, after adding institutions = 0.290 (institutions recover 0.017 of the 0.307).

## A2. Shapley shares with institutions as a fourth group

total R2 = 0.710 (n=551); unexplained = 0.290

| group | share of explained | share of total variance |
|---|---|---|
| geography | 3.6% | 0.025 |
| deep_history_800 | 27.7% | 0.196 |
| inherited_1200 | 64.2% | 0.456 |
| institutions | 4.5% | 0.032 |

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
| equation + all four privileges | 0.591 | 0.708 | x1.47 | 56% | 81% | 6/10 |


Same equation asked to predict GROWTH 1200->1500 instead of size: R2 = 0.022. It knows where the hierarchy stands, not who moves.

Out-of-sample check: fit the law on a random half of cities, predict the other half (200 draws): R2 = 0.557 [0.508, 0.605] — essentially identical to in-sample 0.559; the equation is not overfit.
