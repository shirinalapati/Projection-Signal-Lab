# Interview notes — Projection Signal Lab

## 30 seconds

A metric has to earn the right to change a projection, and that right is target-specific. I inventoried every available field, then ran an admission engine on 2015–2025 MLB data against next-season wOBA, FIP, baserunning, defense, and bWAR rate. Two-year xwOBA belongs in the hitting core: it improved all seven temporal folds with a CI that excludes zero. Sprint Speed was Diagnostic for wOBA and Projection for baserunning. Stuff+ earned Projection for FIP. K%, BB%, and K-BB% are not three independent signals.

## 2 minutes

I separate two products: a number for roster decisions and an explanation for development. Both use the same data; they do not use the same admission standard. The candidate list is not a convenient handful of metrics — every Savant, MLB API, park, people, Stuff+, and pitch-type field is in `feature_registry.csv`, with explicit reasons for anything not tested.

Features are tested in an expanding window (train through T−2, predict T) against a real baseline: age, playing time, **multi-year** performance, park. A current-season-only baseline is weaker; using it would have made extra metrics look useful. In-sample R² is recorded only as a contrast.

On hitters, 2-year xwOBA, EV, and 3-year wOBA pass for next-season wOBA. Mean ΔRMSE for 2-year xwOBA is −0.000931, 7/7 folds, CI (−0.00120, −0.00052). Current xwOBA, barrels, and hard-hit rate beat the baseline alone and fail a family test. Chase stays diagnostic for hitting. Sprint speed is diagnostic for hitting and a projection input for baserunning. Current wOBA is exclude once history is in the baseline. A kitchen-sink hitting model is worse than the admitted model, and the CI excludes zero.

On pitchers, the question is next-season FIP. 2-year FIP is the baseline. 3-year K-BB%, K%, Stuff+, extension, fastball velocity, z-contact, and CSW earned Projection for FIP. Average velocity, spin, and whiff stayed Diagnostic for FIP after family tests. K-BB% is a candidate predictor of future FIP, not a separate projection target. Current K-BB% did not earn independent FIP Projection; K-BB% equals K% minus BB%. The admitted FIP model beat the kitchen-sink model (CI excluded zero).

Scouting, injuries, and MiLB level were not fabricated. They would go through the same gates, with injuries tested first as availability, and with scouting speed allowed to matter for baserunning without automatically entering the wOBA model.

## Why temporal validation?

Random row splits leak era structure (sticky stuff, pitch clock, 2020). A projection is a statement about next year, so the test has to be next year.

## Why not kitchen-sink?

On hitters, selective admission improved generalization (7 vs 56; CI excludes zero). On pitchers the admitted model was slightly better on average (11 vs 57), but the interval included zero, so there is no clear difference. Family tests exist so several correlated Statcast rates do not all get Projection just because each beats a weak baseline. Kitchen-sink medians are fit on the training fold only.

## Metric rejected despite historical / in-sample appeal

Current-season wOBA versus next-season wOBA once 2-year wOBA is in the baseline: no material OOS lift. ERA versus next-season FIP: weak reliability (ERA 0.09) and no material OOS lift. AVG/OBP/SLG fail once a wOBA history is present. Pitcher velocity/spin/whiff look useful alone and fail after K% + BB% as FIP predictors.

## Metric retained diagnostically

Hitter chase (O-Swing%). Sprint speed and home-to-first: reliability ~0.92, no wOBA lift. Barrel% / HardHit% after EV. Pitcher velocity, spin, whiff, in-zone contact: process descriptors, not broad-model projection inputs.

## Insufficient evidence vs Diagnostic

Insufficient Evidence is still in the taxonomy (too few folds or too sparse coverage to decide). After backfilling Stuff+, **no pitcher metric currently sits there.** Stuff+ and extension earned Projection for next-season FIP.

## Redundancy example

K-BB% = K% − BB% (median absolute error 0 on the panel). Any two determine the third. OPS = OBP + SLG. Current xwOBA’s nested ΔRMSE after 2-year xwOBA is about −0.00006 — not a second source. corr(EV, HardHit%) ≈ 0.92.

## Coverage tradeoff

Stuff+, extension, and pitch-family Stuff are scored from Statcast 2015–2025 with an expanding-window model (season t uses only seasons ≤ t). Modeling coverage is **2,682 / 2,682 = 100%**. Same-population comparison is required. Both are Diagnostic.

## How scouting would be tested

Season-t grades only, after current stats + age + level. Independent OOS lift → Projection or Augmented. Thin coverage/windows → Insufficient Evidence. Otherwise Diagnostic (tools/development) or Context (confidence/coverage).

## How injuries would be treated

Split talent-rate vs availability. Do not drop injured player-seasons from the wOBA model. Test IL history on next PA/IP first.

## How MiLB context would be treated

Level and park are Context: translate, then run the same gate on the translated metric. This repo is not Prospect Translation Lab.

## Most surprising result

The original “xwOBA, EV, HardHit%, Barrel% all Projection” result was an artifact of a current-season-only baseline and of testing correlated family members separately. After 2-year wOBA is in the baseline, current wOBA drops out. After a family test, only 2-year xwOBA and EV remain from that cluster. Pitcher velocity/spin/whiff repeated the lesson across families: they look predictive until K% + BB% are already in the model. That is the intended behavior.

## Largest limitation

FanGraphs leaders HTML is blocked; plate-discipline definitions follow Savant (whiff per swing, not SwStr per pitch). wRC+ is a park/league-adjusted index, not FanGraphs’. 2015 Statcast spin and extension are thinner at the pitch level than later years, but pitcher-season Stuff+ and extension still cover the full modeling sample. Max EV, Zone%, and SIERA are empty in this Savant endpoint. No public scouting or complete IL file. Platoon splits use OPS / K-BB% vs L/R, not wOBA.

## What proprietary data would allow next

Complete dated scouting history; medical severity and minors IL; pitch-level command; a non-empty max-EV/CSW Statcast feed for the full window; MiLB tracking through the same gate; a true availability model beside the rate projection.
