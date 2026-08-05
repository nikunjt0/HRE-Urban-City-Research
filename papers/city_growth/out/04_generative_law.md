# The generative law of medieval urban growth

Estimated law (pooled 1200→1500 transitions, Central/North Europe):

    log P_{i,t+1} = a_t + b·log P_{i,t} + c·water_i + eps_{i,t}

| parameter | value | meaning |
|---|---|---|
| b (persistence) | **0.915** | near-unit-root; reversion κ=1−b=0.085/century, half-life ~800 yrs |
| σ (idiosyncratic) | **0.403** log/century | large random component |
| c (water anchor) | +0.060 | small exogenous geographic pull |
| κ/σ (signal-to-noise) | **0.21** | ≪1 ⇒ century growth is ~80% pure Gibrat noise |
| century shocks a_t | 1200:+0.88, 1300:+0.35(plague), 1400:+1.03(recovery) | common, not city-specific |

## Does the law reproduce the data? (400 simulations from actual 1200 sizes)
| moment | simulated (95% band) | actual |
|---|---|---|
| Zipf ζ 1200 | 1.263 [1.26,1.26] | 1.263 (by construction) |
| Zipf ζ 1300 | 1.291 [1.26,1.32] | 1.155 |
| Zipf ζ 1400 | 1.368 [1.32,1.42] | 1.134 |
| Zipf ζ 1500 | 1.219 [1.18,1.26] | 1.080 |
| persistence r² (1200→1500) | 0.459 [0.42,0.50] | 0.560 |

## Reading
- The law CAPTURES the first-order facts: strong persistence (r²≈0.46 vs 0.56) and the
  fact that century growth is ~80% idiosyncratic noise (κ/σ=0.21). This is why no factor
  model — theirs or anyone's — can predict growth well: **there is little systematic
  signal to find.**
- The law MISSES in one informative direction: the real hierarchy CONCENTRATED
  (ζ 1.26→1.08, upper tail thickening toward Zipf), while pure random-growth-with-reversion
  predicts mild EQUALIZATION (ζ rising). The gap = **excess top-end concentration beyond
  chance = a modest agglomeration / increasing-returns force at the largest cities**
  (consistent with Dittmar: Zipf's law "emerges" as the top thickens after ~1500).

## Bottom line
Medieval urban growth ≈ a near-unit-root random walk anchored on geography, plus common
shocks, plus a weak agglomeration pull at the top. Deterministic "why this city" stories
explain little; the system is governed by a stochastic law, not a factor equation.
