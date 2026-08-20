# Baserunning target validation (2015–2025)

## Decision

The packaged Statcast Baserunning Run Value leaderboard is not used as the 2015–2025 target. Statcast **pitch-level** files for this era do not record stolen-base / caught-stealing / pickoff events (`events` never includes `stolen_base_*`).

The **primary 2015–2025 target** is therefore Baseball Reference **baserunning runs (`runs_br`)** expressed as a rate:

- Headline: **baserunning runs per 100 times on base**
- Times on base = H + BB + HBP − HR (BB reconstructed as walk rate × PA)
- Alternative: runs per 600 PA (retained as `y_br_rv_per_600pa`)
- Secondary realized-value target: **total next-season `runs_br`**

This is a single public definition across 2015–2025. It is **not** FanGraphs BsR.

## Why not shrink the window

Sprint speed and Statcast hit descriptions exist in 2015. Stolen-base **events** do not exist in the pitch feed in **any** year 2015–2025. Starting in 2018 or 2020 would not have fixed that. The historical measurement problem is “steals are missing from Statcast pitches,” not “the leaderboard starts later.”

## Reconstruction used as features, not as the target

From Statcast hit descriptions we reconstruct:

- first-to-third on singles
- second-to-home on singles
- outs on the bases where the description supports it

Correlation of that advancement reconstruction with BR `runs_br` is about **0.26** at the player-season level. That is the expected pattern: the reconstruction omits steals, which are a large share of baserunning value.

Linear-weight steal value `0.17×SB − 0.43×CS` is a candidate feature (`steal_rv_rate`), not the target.

MLB Stats API play-by-play (which **does** record steals) is being cached for a later steal-component refinement. It is not required for the 2015–2025 target, which already exists in BR `runs_br`.

## Checks

| Check | Result |
| --- | --- |
| Seasons with target | 2015–2025, 100% of assembled hitter-seasons |
| Modeling pairs | 2015→2016 through 2024→2025 (n = 2,836 after PA≥150 in t and t+1) |
| Year-to-year association (rate_t vs rate_{t+1} in sample) | ≈ 0.38 |
| Rate vs total runs | ≈ 0.20 (playing time is not the same question) |
| 2015 leader (total runs) | Billy Hamilton, +10.8 BR baserunning runs |
| Sprint speed vs contemporaneous rate | ≈ 0.18 (positive, not a tautology) |

## Denominator choice

A universal “baserunning opportunity” count (every occupied-base event) cannot be rebuilt from Statcast pitches because steals are missing. Times on base **can** be rebuilt for every 2015–2025 player-season from batting counting stats.

We therefore headline **runs per 100 TOB**, and keep **runs per 600 PA** as a robustness rate that does not depend on the TOB reconstruction.
