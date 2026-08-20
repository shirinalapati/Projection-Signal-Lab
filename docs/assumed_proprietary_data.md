# Assumed proprietary data — same gate, no fabrication

A full front-office stack would typically include scouting evaluations, injury history, demographics, minor-league level, and park context. This public study has MLB Savant + Stats API + park factors + age/handedness/role. It does **not** invent the rest.

Every additional source would enter the **same gates**, including a sixth **target-dependence** check: does the metric’s role change depending on what we are trying to predict? Verdicts remain Projection / Augmented Projection / Diagnostic / Context / Exclude / **Insufficient Evidence**, and they are always relative to a named target.

- **Diagnostic:** this metric helps describe how a player succeeds or struggles, but did not add enough independent future-prediction value to the broad model.
- **Insufficient Evidence:** we do not yet have enough reliable coverage or temporal validation to make a confident projection decision. That is not Exclude, and it is not proof of no value.
- **Exclude:** the metric did not provide enough unique predictive or diagnostic value in this study.

## Scouting evaluations

If a complete, dated, player-season grade file existed (tool grades, FV, present/future, scout ID):

- Features would be season-t grades only. No t+1 grades. No using the MLB outcome that the scout already saw.
- **OOS test:** baseline (age, playing time, multi-year performance, park/level) vs baseline + grades, expanding window.
- **Redundancy:** grades vs the statistical process they describe (power vs EV/barrels; hit tool vs contact/chase). A grade that merely restates barrels does not earn Projection.
- **Coverage:** amateur vs professional, org vs industry, missingness by level. Incomplete coverage → Augmented Projection **or Insufficient Evidence** if the temporal window is too thin, never a silent complete-case MLB model.
- **Stability:** scout-year effects, scale drift, new scouting directors. Era-adjust or scout-adjust before admitting.
- Default until those tests pass: **Diagnostic for that target** (tools, development, makeup) or **Context** (confidence/coverage flags). A speed grade can add information to baserunning or defense without improving next-season wOBA. Projection only if grades add repeatable future information after the target-specific baseline.

Public prospect lists are not a substitute for a complete internal scouting history. They were not scraped into this study.

## Injury history

Split two questions. Do not contaminate the rate-talent model with availability.

1. **Talent / rate:** next-season wOBA, FIP, baserunning run-value rate, or fielding run-value rate. Prior IL days may or may not move true talent. Test OOS on the rate target. If they do not, they do not change the skill projection.
2. **Availability / realized total value:** next-season PA/IP and total WAR. Injury type, days, recurrence, workload, and surgery flags belong here first. A strong projected rate can still imply lower projected total value because of availability risk.

Coverage of public IL data is incomplete (minors, undisclosed, severity). Missingness is systematic. That is Gate D: model uncertainty and availability separately; do not drop injured players from the talent sample unless the target is explicitly availability.

Likely verdict: **Diagnostic / medical context** for the rate projection; possible **Augmented Projection** for playing-time models if OOS value and coverage survive.

## Demographics

Public, defensible fields used here: age, handedness, position, role. Age is in the baseline as **Context** (aging), not as a skill. Handedness and position are stratification/context. No sensitive attributes.

## Minor-league level and park

This is not Prospect Translation Lab. Raw statistics from different levels are not interchangeable.

If projecting a MiLB player, level is **Context**: translate, park-adjust, and combine with age-relative-to-level, then run the same admission gate on the translated metric. Do not treat Double-A wOBA as MLB wOBA. Do not learn translations from future MLB outcomes in the test year.

Prospect_Lab already contains park factors and level translations; those artifacts are the right place to implement full MiLB translation. This lab only demonstrates the gate on MLB data and states the rule.

## Incomplete tracking

Statcast/custom fields that exist only for some seasons or playing-time tiers are the public analogue of incomplete proprietary tracking.

Required comparison: evaluate the core model and the tracking model on the **same covered players**, then report coverage separately. If the metric is predictive where present, it is **Augmented Projection**, not a reason to drop uncovered players from the core model.
