# Projection Signal Lab — Methodological Audit

Independent recomputation from the canonical modeling tables. Existing conclusions were treated as possibly wrong until verified. Sign convention used throughout: **ΔRMSE = RMSE(augmented) − RMSE(baseline); negative = improvement.** Materiality is 0.5% of baseline RMSE (hitters ≈ 0.000177; pitchers ≈ 0.000245).

**Revision status (2026-08-20, five public targets):** Hitting → next-season wOBA. Pitching → next-season FIP. Baserunning, defense, and bWAR overall-value studies cover 2015–2025. Next-season K-BB% is **not** a public or canonical projection target; K-BB% remains a pitching feature for FIP. The historical K-BB%-target experiment is in [`docs/archive/kbb_target_study.md`](archive/kbb_target_study.md). Public verdicts are component-specific. `scripts/08_methodology_audit.py` last returned `issues: []`.

**Revision status (2026-08-20, component expansion):** Hitting → next-season wOBA remains the verified study. Pitching’s public target is next-season FIP. Baserunning, defense, and bWAR overall-value studies cover 2015–2025. Public verdicts are target-specific. Historical K-BB-era findings in this file document an earlier question; they do not define the current public product.

**Revision status (2026-08-19):** The issues below were incorporated into the admission engine, `artifacts/admission_table.parquet`, README, research site, Feature Passports, model cards, kitchen-sink comparison, interview notes, and the short written summary. Public headlines are no longer provisional relative to this audit. Re-run `scripts/08_methodology_audit.py` after any later admission change.

**Later update (2026-08-20):** Historical Statcast (2015–2022) was fetched and Stuff+ was rescored with a leakage-safe expanding-window model (fit on seasons ≤ t, score t only). Modeling coverage is now **2,682 / 2,682 = 100%** with **7 folds**. Under the archived K-BB% target, Stuff+ and extension were Diagnostic. Under the public next-season FIP target they are Projection. Critical issues 3–4 and Important issue 2 below describe the frozen 2023–2025 file that this later work replaced.

This file is the audit record: it documents what was wrong, what was verified, and what changed. It is not the public findings page.

---

## CRITICAL ISSUES

1. **Pitcher Projection set treats related features as independent.** After K% + BB% (same players, same seven folds), velocity, spin, whiff rate, and in-zone contact allowed all fail incremental OOS materiality and/or have CIs that include zero. The admission engine only demoted *within* family, so `whiff_rate`, `avg_spin`, `avg_velo`, and `z_contact_pct` were labeled Projection even though they do not add next-season K-BB% once the strikeout/walk mix is in the model. **Audit: demote those four to Diagnostic.** Keep `k_pct` with 2-year K-BB% as the decomposition, not as a third K-BB source.

2. **K-BB% = K% − BB% holds exactly** (median absolute error 0; VIF infinite). Specs B/C/D/E (any two of the three rates) produce the same OOS RMSE to six decimals. Presenting K%, BB%, and K-BB% as three passing independent inputs is mathematically false. The current table already demoted BB% and current K-BB%; the README still lists K% next to 2-year K-BB% without stating the identity.

3. **Stuff+ scores are not season-t-only.** `Stuff_Quality/precompute.py` fits logistic whiff models on pooled 2023–2026 pitches and z-scores within role × pitch group across that pool. `frozen_arsenal_scores_2023_2025.parquet` locks 2023–2025 *rows* so later 2026 refreshes do not overwrite them. Frozen ≠ contemporaneous. A 2024 Stuff+ value used to predict 2025 K-BB% can use coefficients and z-score moments that include 2025 (and possibly 2026) pitches. The one OOS fold is not a clean test.

4. **Stuff+ “coverage = 28%” uses the wrong denominator.** `admit_feature` calls `coverage_profile` on the unfiltered seasons table (n = 8,539, including 2025 with no t→t+1 label). Modeling-sample coverage is **509 / 2,682 = 19%** (2023 and 2024 feature seasons only, 100% within those two years). The 28% figure must not be reused.

5. **Kitchen-sink comparison leaked validation-year medians** (full-sample `fillna(median)` before the temporal split). Recomputed with train-fold medians only. Hitter conclusion is unchanged in direction (admitted better; CI excludes zero). Pitcher difference CI **includes zero**. Do not say the models “tied.” Elastic Net kitchen rows in the old artifact still reflect the leaked fill (`imputation=STALE_full_sample_median_leaked`) until a full admission rerun.

## IMPORTANT ISSUES

1. **Family representative selection is slightly optimistic.** Greedy demotion uses nested OOS on the same expanding-window folds that later report admitted-core RMSE. Hitters: 2-year xwOBA still wins a held-in-family test, so the headline is not an artifact of that optimism. Pitchers: the optimism is dominated by the missing *cross-family* test above.

2. **Extension is one fold, not Augmented Projection-quality evidence.** Same 509-row 2023–2024 coverage as Stuff+. After K%+BB% the CI includes zero. **Audit: Insufficient evidence**, not a headline Augmented Projection.

3. **`avg_velo` fails Gate A even vs the strong baseline** (bootstrap CI includes zero) and the lift is concentrated in LHP (−0.00082 vs −0.00010 for RHP).

4. **Park factor is last year’s team environment, not the park of the outcome season.** 26% of hitter transitions and 33% of pitcher transitions change `team_id` from t to t+1. Construction is same-season team runs/PA vs league, shrunk toward 1.0 (n0=3). It confounds roster talent with park. Correctly labeled Context; it is not a skill metric and is not forward-looking, but it is also not “the park they will play in.”

5. **IP is likely baseball outs notation (`.1` / `.2`) stored as a decimal.** 67% of modeling-sample IP values have fractional part 0.1 or 0.2; median |Savant − parse_mlb_ip(MLB)| = 0.23, which is exactly the 0.1 vs 1/3 gap. Integer thresholds 80 / 30 / 25 / 10 **do not change** under either parsing (`.1`/`.2` never cross an integer). Sample *weights* are slightly wrong. This does not inflate n = 2,682.

6. **`woba_w3` is collinear with `woba_w2` (VIF 11.7)** and the bootstrap CI upper bound is ~0. Projection is marginal.

7. **EV reliability is only 0.34** (unfiltered seasons). It still passes the 0.25 gate and the OOS tests, but it is much noisier year-to-year than 2-year xwOBA (r = 0.85).

8. **Catchers:** EV does not help the catcher subgroup (ΔRMSE +0.00008, 2/5 folds). Other large groups improve. Not a Gate E failure, but EV is not universal.

## MINOR ISSUES

1. Raw Savant pitcher custom has **5 duplicate (player_id, year) rows**, all player 519381 (2015, 2016, 2018–2020). Assemble `drop_duplicates` collapses them. Canonical seasons, labeled, and sample tables have **zero** player-season duplicates.

2. Multi-team player-seasons are aggregated to one row (highest `num_teams`, then playing time): 213 hitter rows and 319 pitcher rows have `num_teams > 1`. Park attaches to that one `team_id`.

3. League-year z-scores (`woba_z`, `k_bb_pct_z`) use the full seasons table’s same-season mean/sd, including players outside the PA/IP sample. Contemporaneous, not future. Fine for leakage; slightly different from a “qualified only” z.

4. The park-factor file includes 2008–2026. Merge is on season t; 2026 rows are unused for this study.

5. Kitchen Elastic Net comparison was not fully recomputed with train-only impute in this pass (Ridge was).

6. `k_bb_pct_w2` “incremental” vs a baseline that already contains it is zero by construction; that is not a 2020-sensitivity result.

## VERIFIED RESULTS

| Claim | Source | Audit |
|---|---|---|
| Hitters n = 2,836 | `hitter_sample_pa150.parquet` | **2,836** rows, **802** players, **2,836** t→t+1 transitions, 0 duplicates, PA min/median/max = 150 / 450 / 753, PA≥150 in t and t+1 actually applied |
| Pitchers n = 2,682 | `pitcher_sample_role_ip.parquet` | **2,682** rows, **906** players, **2,682** transitions, 0 duplicates. 1,065 starter-seasons (min IP 80.0 non-2020), 1,617 reliever-seasons (min IP 30.0 non-2020), min IP 10.0 is 2020 RP. Mean 268.2 rows per feature season. Plausible for SP 80 / RP 30 |
| Strong baseline RMSE 0.03627 → 0.03541 hitters; 0.05025 → 0.04909 pitchers | `baseline_audit_*.csv` | Reproduced |
| 2-year xwOBA ΔRMSE −0.00093, 7/7, CI below 0 | `admission_table` | Reproduced from raw folds: mean −0.000931, median −0.000812, boot CI (−0.001202, −0.000523), MAE Δ −0.000611 |
| Stale 0.00121 xwOBA | pre-universe README | This is **current-season xwOBA vs the weak current-wOBA baseline**: mean Δ −0.001206, 7/7. Not the headline study. Absolute value matches 0.00121 |
| 7 temporal folds, train ≤ T−2 | `expanding_folds` | Exact folds printed below. No train/validation season overlap |
| Ridge scaler on train only | `make_ridge` Pipeline | Confirmed |
| K-BB% = K% − BB% | panel | Holds, median abs error 0 |
| Stuff+ reliability r = 0.83 | `year_to_year_reliability` on seasons | Pearson **0.827**, Spearman 0.793, **N = 1,174** consecutive seasons on the unfiltered table |
| Chase Diagnostic | admission | Δ −0.000072 vs strong baseline, below materiality. Mechanism holds |
| Sprint speed Diagnostic | admission | Δ +0.000028; r ≈ 0.92. Mechanism holds |
| Current wOBA Exclude once 2-year wOBA is in the baseline | admission | Δ −0.000051, CI includes 0 |
| HardHit% / Barrel% Diagnostic after family test | greedy + this audit | Confirmed: Elastic Net zeros both; LOO RMSE improves when they are dropped |
| 2020 does not flip hitter headlines | this audit | Without 2020 transitions: xwoba_w2 still 5/5, Δ −0.00078; EV 5/5, Δ −0.00046 |
| Kitchen leak direction for hitters | this audit | Admitted 0.03427 vs kitchen 0.03524; boot Δ (kitchen − admitted) 0.00072, CI (0.00026, 0.00120) |

## CHANGED RESULTS

| Item | Before | After this audit |
|---|---|---|
| Pitcher Projection beyond baseline | 2-year K-BB%, K-BB% z, K%, z-contact, spin, velocity, whiff; extension Augmented; Stuff+ Diagnostic | **2-year K-BB% (baseline) + K% (decomposition) + optional K-BB% z.** z-contact, spin, velocity, whiff → **Diagnostic**. Extension → **Insufficient evidence**. Stuff+ → **Insufficient evidence** (still a process diagnostic, not “does not predict”) |
| Stuff+ coverage | 28% | **19% of the modeling sample** (28% is the seasons-table rate) |
| Kitchen-sink vs admitted | “Did not beat” / earlier “tied” (33 features) | Hitters: admitted **better**, CI excludes 0. Pitchers: admitted slightly better, **CI includes 0 (uncertain)**. Feature counts **7 vs 56** hitters, **11 vs 57** pitchers. Not 33 |
| Stale 0.00013 chase | vs weak baseline | Current chase vs **strong** baseline is −0.000072 (not material) |
| README / essay | Treated as matching the table | **Not final** until pitcher verdicts and Stuff+ coverage are updated from this audit |

---

## 1. Sample sizes

Canonical tables: `data/processed/hitter_sample_pa150.parquet`, `data/processed/pitcher_sample_role_ip.parquet`. A modeling table must have ≤1 row per player per season. **Duplicates: 0. The uniqueness assertion passed.**

### Hitters (filter: PA ≥ 150 in season t and t+1; `y_woba` not null; t in 2015–2024)

| | |
|---|---|
| Unique players | 802 |
| Player-season rows | 2,836 |
| t → t+1 transitions | 2,836 |
| PA min / median / max | 150 / 450 / 753 |
| Multi-team rows (aggregated to one) | 213 |
| 2020 as feature season | 189 (other years ~300) |

Count by season t: 2015:309, 2016:299, 2017:306, 2018:302, 2019:188, 2020:189, 2021:314, 2022:309, 2023:315, 2024:305.

Count by target season: 2016:309 … 2020:188, 2021:189 … 2025:305.

2019 and 2020 feature seasons are smaller because the *next* season must also have PA ≥ 150 (2020 short season).

### Pitchers (filter: GS/G ≥ 0.5 and IP ≥ 80, else IP ≥ 30; both t and t+1; 2020 exception SP ≥ 25 / RP ≥ 10)

| | |
|---|---|
| Unique players | 906 |
| Player-season rows | 2,682 |
| t → t+1 transitions | 2,682 |
| Starter-seasons / reliever-seasons | 1,065 / 1,617 |
| IP min / median / max | 10.0 / 67.2 / 232.2 |
| Non-2020 SP min IP / RP min IP | 80.0 / 30.0 |
| y_ip below next-season threshold | 0 |
| Multi-team rows | 319 |
| 2020 as feature season | 287 (mean 268.2) |

**Is 2,682 plausible under SP 80 / RP 30?** Yes. ~268 pitcher-seasons per year × 10 feature years, of which ~60% are relievers at a 30-IP bar, matches a broad qualified-pitcher universe. The 2020 exception does **not** explode the sample (287 vs mean 268) because 2021 still uses the full IP floor. Min IP 10.0 is exactly the 2020 RP exception, so the exception *is* applied — it is not a silent no-threshold dump of every pitcher.

Raw Savant pitcher custom had 5 stint-level duplicates (player 519381); assemble collapsed them. MLB hitting/pitching extracts had 0 id-season duplicates. Labeled join did not multiply rows (seasons n = labeled n).

IP parsing: primary field is Savant `p_formatted_ip`. MLB `.1`/`.2` = outs is only used when Savant IP is missing; in this sample Savant IP is never missing. Two-thirds of IP fractions are 0.1 or 0.2, so Savant itself is probably baseball notation treated as a decimal. Integer workload gates are invariant. Do not treat IP as a precise continuous weight.

## 2. Target leakage

`target_season = season + 1` on every modeling row. History features (`*_w2`, `*_w3`, lag) use only that player’s t and earlier seasons; rookies fill w2 with t. No inspected skill column equals the target.

Feature–target correlations are in `artifacts/audit/leakage_feature_target_corr.csv`. None of xwOBA, EV, Barrel%, HardHit%, Chase%, Sprint Speed, park, age, role, Stuff+, velocity, spin, whiff/contact, K%, BB%, K-BB% correlate with the target above 0.95.

**Park:** Prospect_Lab `estimate_park_factors` — same-season team `runs/PA` vs league mean, shrink `(3×1 + 1×raw)/4`. Not multi-year, not future seasons in the formula, merge on `(season t, team_id)`. 0% of modeling rows were filled with 1.0 in this sample. A player’s own runs enter team RPG slightly (circularity, not t+1 leak). **Not rebuilt:** construction is already contemporaneous. Interpreting it as “skill” would be wrong; it stays Context.

**Stuff+:** see Critical #3. Player-season *aggregates* use that season’s pitches; the *model* is pooled.

**Age / role:** season-t demographics. Role is GS/G in season t; next-season role is used only for the *filter* (`y_ip` vs next-year role), not as a predictor of the outcome.

## 3. The seven temporal folds

`EXPANDING_TEST_YEARS = 2019..2025`. Train: `season ≤ test_year−2`. Validation features: `season == test_year−1`. Outcomes in `test_year`.

### Hitters

| Outcome year | Train seasons | n_train | Val feature season | n_val |
|---|---|---|---|---|
| 2019 | 2015–2017 | 914 | 2018 | 302 |
| 2020 | 2015–2018 | 1,216 | 2019 | 188 |
| 2021 | 2015–2019 | 1,404 | 2020 | 189 |
| 2022 | 2015–2020 | 1,593 | 2021 | 314 |
| 2023 | 2015–2021 | 1,907 | 2022 | 309 |
| 2024 | 2015–2022 | 2,216 | 2023 | 315 |
| 2025 | 2015–2023 | 2,531 | 2024 | 305 |

### Pitchers

| Outcome year | Train seasons | n_train | Val feature season | n_val |
|---|---|---|---|---|
| 2019 | 2015–2017 | 816 | 2018 | 277 |
| 2020 | 2015–2018 | 1,093 | 2019 | 261 |
| 2021 | 2015–2019 | 1,354 | 2020 | 287 |
| 2022 | 2015–2020 | 1,641 | 2021 | 270 |
| 2023 | 2015–2021 | 1,911 | 2022 | 262 |
| 2024 | 2015–2022 | 2,173 | 2023 | 266 |
| 2025 | 2015–2023 | 2,439 | 2024 | 243 |

Preprocessing: Ridge `StandardScaler` is inside the sklearn Pipeline, fit on the training matrix only. ElasticNetCV 5-fold shuffled CV is also training-matrix only and is **not** used for headline Ridge admission. League z is contemporaneous (season t peers), not a future aggregate. **Bug (fixed in code, Ridge kitchen rebuilt):** kitchen-sink medians were previously fit on the full sample including validation years.

## 4. xwOBA result

**Sign: negative ΔRMSE = adding the feature improves accuracy.**

### Current-season xwOBA vs weak baseline (age, PA, current wOBA, park)

This is the stale **0.00121** claim (reported as a positive improvement).

| Outcome year | Baseline RMSE | +xwOBA RMSE | ΔRMSE | ΔMAE | n |
|---|---|---|---|---|---|
| 2019 | 0.03441 | 0.03356 | −0.00085 | −0.00082 | 302 |
| 2020 | 0.04366 | 0.04218 | −0.00148 | −0.00112 | 188 |
| 2021 | 0.03979 | 0.03742 | −0.00237 | −0.00089 | 189 |
| 2022 | 0.03627 | 0.03565 | −0.00062 | −0.00036 | 314 |
| 2023 | 0.03154 | 0.03021 | −0.00132 | −0.00074 | 309 |
| 2024 | 0.03659 | 0.03544 | −0.00115 | −0.00090 | 315 |
| 2025 | 0.03159 | 0.03094 | −0.00065 | −0.00035 | 305 |

Mean ΔRMSE **−0.001206**; median **−0.001152**; 7/7 improved; bootstrap RMSE Δ −0.001079, CI (−0.001423, −0.000681); MAE Δ −0.000712.

### 2-year xwOBA vs strong baseline (age, PA, 2-year wOBA, park) — current headline

| Outcome year | Baseline RMSE | +xwoba_w2 RMSE | ΔRMSE | ΔMAE | n |
|---|---|---|---|---|---|
| 2019 | 0.03353 | 0.03272 | −0.00081 | −0.00067 | 302 |
| 2020 | 0.04297 | 0.04162 | −0.00135 | −0.00085 | 188 |
| 2021 | 0.03712 | 0.03572 | −0.00141 | −0.00070 | 189 |
| 2022 | 0.03584 | 0.03569 | −0.00015 | −0.00012 | 314 |
| 2023 | 0.03159 | 0.03008 | −0.00151 | −0.00114 | 309 |
| 2024 | 0.03523 | 0.03442 | −0.00081 | −0.00058 | 315 |
| 2025 | 0.03161 | 0.03112 | −0.00049 | −0.00027 | 305 |

Mean **−0.000931**; median **−0.000812**; 7/7; boot CI (−0.001202, −0.000523); MAE Δ **−0.000611**.

Current-season xwOBA vs the *strong* baseline: mean −0.000818, 7/7, CI (−0.001087, −0.000466). Still real, smaller than 2-year xwOBA.

### Conditional tests (current-season xwOBA unless noted)

Do not call xwOBA non-redundant merely because it beats the baseline alone.

| Comparison | Mean ΔRMSE | Folds improved | Boot CI |
|---|---|---|---|
| Baseline + EV, add xwOBA | −0.000359 | 7/7 | (−0.000552, −0.000172) |
| Baseline + Barrel%, add xwOBA | −0.000497 | 7/7 | (−0.000786, −0.000281) |
| Baseline + HardHit%, add xwOBA | −0.000464 | 7/7 | (−0.000687, −0.000305) |
| Baseline + EV + Barrel% + HardHit%, add xwOBA | −0.000384 | 7/7 | (−0.000615, −0.000223) |
| Baseline + EV + 3-year wOBA, add current xwOBA | −0.000330 | 7/7 | (−0.000505, −0.000149) |
| Baseline + EV + 3-year wOBA, add **2-year xwOBA** | −0.000378 | 6/7 | (−0.000575, −0.000153) |

**Verdict:** 2-year xwOBA contains incremental information after EV and 3-year wOBA. Current-season xwOBA contains incremental information after EV/Barrel/HardHit, but **not** after 2-year xwOBA (family demotion Δ ≈ −0.00006). The Projection slot belongs to **2-year xwOBA**, not to current xwOBA, EV, Barrel%, and HardHit% as a block of four.

## 5. Hitter redundancy (xwOBA, EV, HardHit%, Barrel%)

Correlations on complete cases:

| | EV | HardHit% | Barrel% | xwOBA | xwoba_w2 |
|---|---|---|---|---|---|
| EV | 1 | 0.92 | 0.74 | 0.66 | 0.65 |
| HardHit% | 0.92 | 1 | 0.77 | 0.66 | 0.65 |
| Barrel% | 0.74 | 0.77 | 1 | 0.67 | 0.65 |
| xwOBA | 0.66 | 0.66 | 0.67 | 1 | 0.92 |

Year-by-year r(EV, HardHit%) is 0.91–0.94 every season including 2020. VIF(EV vs family) = 6.7; VIF(HardHit%) = 7.4; VIF(Barrel%) = 2.8; VIF(xwOBA) = 2.0.

Elastic Net paths (baseline + four metrics): **Barrel% coefficient is 0 in all 7 folds; HardHit% is 0 in 6/7.** EV and xwOBA stay positive every fold.

Leave-one-out (full family RMSE 0.03454): dropping EV *hurts* (−0.00011); dropping HardHit% or Barrel% *helps* slightly; dropping xwOBA hurts (−0.00038).

Add-one vs strong baseline: EV −0.00057 (7/7, CI below 0); HardHit% −0.00034 (CI **includes** 0); Barrel% −0.00032 (CI below 0); xwOBA −0.00082 (7/7).

Last-fold permutation (2025, n=305): RMSE increase on permute xwOBA 0.0028, EV 0.0022, HardHit% 0.0005, Barrel% ≈ 0.

**Each metric does not independently earn Projection.** EV does (with a catcher caveat). 2-year xwOBA does. HardHit% and Barrel% are Diagnostic contact-quality descriptors. Current xwOBA is Diagnostic as the single-season version of the Projection representative.

## 6. Pitcher mathematical redundancy

K-BB% = K% − BB% holds on all 2,682 rows. VIF is infinite among the three.

Same folds, core context `{age, ip, starter_role, park_factor}` plus:

| Spec | Features | OOS RMSE | OOS MAE |
|---|---|---|---|
| A | K-BB% only | 0.050251 | 0.038948 |
| B | K% + BB% | 0.049674 | 0.038445 |
| C | K-BB% + K% | 0.049674 | 0.038445 |
| D | K-BB% + BB% | 0.049674 | 0.038445 |
| E | all three | 0.049674 | 0.038445 |
| F | 2-year K-BB% | 0.049087 | 0.037970 |
| G | 2-year K-BB% + K% | **0.048368** | 0.037431 |
| H | 2-year K-BB% + K% + BB% | 0.048386 | 0.037451 |

B–E are the same model. The mix K% + BB% beats the difference alone. Once 2-year K-BB% is in, **K% still helps** (Δ −0.00072, CI (−0.00121, −0.00033), 7/7); adding BB% on top of that does nothing. Elastic Net on {K-BB%, K%, BB%} zeros BB% every fold and keeps K-BB% and K%.

**Recommendation:** replace “K%, BB%, and K-BB% all pass” with **2-year K-BB% + current K%**. Do not list BB% or current K-BB% as independent Projection inputs. K%+BB% without history is sufficient *instead of* current K-BB%; it is not better than 2-year K-BB% + K%.

## 7. Velocity / spin / whiff / contact

Same-population rule: velo, spin, whiff, z-contact are ~100% covered on the modeling sample, so core vs tracking comparisons are not a coverage swap. Stuff+ / extension are 509 rows (2023–2024 only); those comparisons are restricted to that subset.

| Feature | Coverage (modeling) | Reliability r (seasons, N) | Δ vs strong baseline | After K%+BB% (same pop) | After Stuff+ (n=509, 1 fold) |
|---|---|---|---|---|---|
| avg_velo | 100% | 0.92 (5,618) | −0.00025, CI includes 0, 5/7 | −0.00005, CI includes 0 | 1 fold, CI includes 0 |
| avg_spin | 100% | 0.90 (5,618) | −0.00041, CI barely < 0, 5/7 | −0.00020, CI includes 0 | 1 fold, CI includes 0 |
| whiff_rate | 100% | 0.49 (5,627) | −0.00040, CI < 0, 6/7 | **+0.00004** (worse) | 1 fold, CI includes 0 |
| z_contact_pct | 100% | 0.43 (5,627) | −0.00067, CI < 0, 7/7 | −0.00017, CI includes 0 | −0.00051, CI < 0 (1 fold) |
| ff_velo | 97% | 0.91 | −0.00029, CI includes 0 | −0.00008, CI includes 0 | 1 fold, CI includes 0 |
| extension | **19%** | 0.96 (1,174) | −0.00072, 1 fold, CI barely < 0 | −0.00067, CI includes 0 | CI includes 0 |
| stuff_plus | **19%** | 0.83 (1,174) | −0.00038, 1 fold, CI includes 0 | −0.00018, CI includes 0 | — |

**None of velo / spin / whiff / z-contact independently earn Projection once K% and BB% are in the model.** They remain process diagnostics: velocity and spin (pitch quality), whiff (miss), z-contact (contact allowed).

## 8. Stuff+

| Item | Finding |
|---|---|
| Reliability definition | Pearson of Stuff+ in t vs t+1, rows with both. **Not** ICC, not split-half |
| r | 0.827 (seasons table, N=1,174). Modeling-sample consecutive pairs are fewer |
| Score seasons | 2023, 2024, 2025 in the frozen file |
| Frozen? | Rows locked; **model is pooled**, not a prior-only freeze |
| Target-year information | Coefficients and z-score μ/σ can include later seasons’ pitches |
| Coverage denominator (admission) | Unfiltered seasons n=8,539 → 28.2% |
| Coverage denominator (modeling) | 509/2,682 = **18.98%** |
| OOS folds possible | **One** (2024 features → 2025). Train for that fold is 2023 only |
| OOS ΔRMSE | −0.00038; boot CI (−0.00098, **+0.00013**) includes 0 |

**Insufficient evidence, not “does not predict.”** One contaminated fold that fails to reject zero is not a demonstration of zero effect. Do not put “Stuff+ is not predictive” in the README or the essay. Also do not put “coverage 28%” without the seasons-table denominator.

## 9. 2020

Rerun without transitions that have `season==2020` or `target_season==2020` (n_hitter 2,836 → 2,459, 7 folds → 5; n_pitcher 2,682 → 2,134).

| Feature | Incl. 2020 Δ (folds) | Excl. 2020 Δ (folds) | Verdict change? |
|---|---|---|---|
| xwoba_w2 | −0.00093 (7/7) | −0.00078 (5/5) | No |
| EV | −0.00057 (7/7) | −0.00046 (5/5) | No |
| current xwOBA | −0.00082 (7/7) | −0.00074 (5/5) | No |
| K% | −0.00072 (7/7) | −0.00079 (5/5) | No |
| whiff | −0.00040 (6/7) | −0.00030 (4/5) | No (already demoted on redundancy) |
| avg_velo | −0.00025 (5/7) | −0.00022 (3/5) | More fragile; already demoted |

Hitter 2020 *raises* baseline RMSE (0.03541 vs 0.03342 without those transitions) because the 2020-as-target fold is noisy (n=188). It does not manufacture the xwOBA or EV signs. Pitcher 2020 similarly inflates baseline RMSE (0.04909 vs 0.04544). Treating 2020 as its own model is unnecessary for these headlines.

## 10. Park context

- **Source:** Prospect_Lab `estimate_park_factors` copied to `data/external/park_factors.parquet`. MLB = `sport_id==1`.
- **Season specificity:** one factor per team-season. Same-season merge.
- **Team changes:** 744/2,836 hitters (26%) and 881/2,682 pitchers (33%) change team t → t+1, so season-t park is often not the outcome park.
- **Multi-team:** one `team_id` after dedupe; park is that team’s factor.
- **Forward-looking:** no. Not a rolling multi-year factor that includes t+1.
- **Skill vs context:** team RPG confounds talent and park. Context only.
- Inspected construction rather than assumed leakage-safe. No rebuild required for leakage; do not sell it as a true park factor.

## 11. Diagnostic classifications

A metric is Diagnostic only with an interpretable mechanism, not merely because it failed Gate A.

| Metric | Process | Outcome/mechanism | Evidence | Why keep Diagnostic |
|---|---|---|---|---|
| Chase% (`o_swing_pct`) | Swings at pitches outside the zone | Plate discipline → BB/K mix and pitchers’ attack | Savant O-Swing%; weak next-wOBA lift (−0.000072) | Explains *how* a hitter’s on-base skill is generated |
| Sprint speed | Straight-line run speed | Baserunning / defensive range, not wOBA | r≈0.92; ΔRMSE +0.000028 on next wOBA | Athleticism profile; wrong target for this study |
| HardHit% / Barrel% | Quality-of-contact slices | EV / sweet-spot / barrel definition | High correlation with EV; no nested OOS | Describe contact quality in scouting language |
| Current xwOBA | Expected wOBA from contact | Same family as 2-year xwOBA | Incremental vs EV family; redundant vs xwoba_w2 | Single-season expected-contact readout |
| Whiff / z-contact / velo / spin | Miss, contact allowed, pitch quality | Upstream of K% | Conditional OOS after K%+BB% fails | Tool/process diagnostics for pitching |
| Stuff+ | Model-based pitch-quality score | Predicted whiff from velo/spin/break/location | r=0.83; OOS underpowered | Process score if the pooling leak is fixed later |
| BABIP, launch angle, etc. | Luck / trajectory | Weak OOS | Already Diagnostic with process=True | Unchanged |

No Diagnostic in this set is a pure “failed the t-test so we needed a nicer word.” Sprint speed would be **Exclude** *for this wOBA projection* if someone claimed it explained wOBA; it stays Diagnostic because it measures a real, reliable athletic process used elsewhere. Chase stays Diagnostic, not Exclude.

## 12. Kitchen-sink claim

Previous leak: medians fit on all years. Rebuild: train-fold medians only. Admitted features are fully observed, so admitted complete-case = admitted imputed.

| | Hitters | Pitchers |
|---|---|---|
| Admitted features | 7 | 11 |
| Kitchen skill-role features | 56 | 57 |
| Admitted OOS RMSE / MAE | **0.03427 / 0.02710** | **0.04806 / 0.03702** |
| Kitchen OOS RMSE / MAE (train-only impute) | 0.03524 / 0.02787 | 0.04832 / 0.03736 |
| Mean fold Δ (kitchen − admitted) | +0.00097 | +0.00026 |
| Bootstrap Δ RMSE (kitchen − admitted) | **+0.00072, CI (0.00026, 0.00120)** | +0.00019, CI **(−0.00047, 0.00085)** |
| Folds kitchen better | 1/7 (2025) | 1/7 (2020, tiny) |
| Coverage | Same n (impute vs complete 7-feat) | Same n |

**Hitters: admitted model is better. Not tied.** CI excludes zero. **Pitchers: uncertain.** Point estimate favors admitted; CI includes zero. Evidence does **not** support “statistically equivalent” for hitters. For pitchers, “essentially tied” is defensible only with the CI in view — not as a headline.

Stale “33 features” is false. Current kitchen is 56/57.

Calibration: not estimated in this audit (no reliability diagrams).

## 13. Verdict logic

Full table: `artifacts/audit_verdicts.csv`. Headline rows:

| Metric | Current | A incr. OOS | B stability | C non-redundant | D coverage | E subgroup | Audit | Changed? |
|---|---|---|---|---|---|---|---|---|
| hitter:woba_w2 | Projection | PASS | PASS | PASS (baseline) | PASS | PASS | Projection | no |
| hitter:xwoba_w2 | Projection | PASS | PASS r=0.85 | PASS after EV+w3 | PASS | PASS (weaker C) | Projection | no |
| hitter:ev | Projection | PASS | r=0.34 weakish | PASS | PASS | Catchers no | Projection | no |
| hitter:woba_w3 | Projection | PASS marginal | PASS | VIF 11.7 | PASS | PASS | Projection (marginal) | no |
| hitter:xwoba | Diagnostic | PASS vs baseline | PASS | FAIL vs xwoba_w2 | PASS | PASS | Diagnostic | no |
| hitter:hard_hit_pct | Diagnostic | FAIL CI | PASS | FAIL vs EV | PASS | — | Diagnostic | no |
| hitter:barrel_pct | Diagnostic | PASS | PASS | FAIL vs EV/xwOBA | PASS | — | Diagnostic | no |
| hitter:woba | Exclude | FAIL | PASS | FAIL vs w2 | PASS | — | Exclude | no |
| hitter:o_swing_pct | Diagnostic | FAIL materiality | PASS | — | PASS | — | Diagnostic | no |
| hitter:sprint_speed | Diagnostic | FAIL | PASS r=0.92 | — | PASS | — | Diagnostic | no |
| pitcher:k_bb_pct_w2 | Projection | PASS | PASS | identity family | PASS | PASS | Projection | no |
| pitcher:k_pct | Projection | PASS | PASS | decomposition | PASS | PASS | Projection (with w2) | **yes** (wording) |
| pitcher:k_bb_pct_z | Projection | PASS small | PASS | representation | PASS | — | Projection (caveat) | no |
| pitcher:z_contact_pct | Projection | PASS vs baseline | PASS | **FAIL vs K%** | PASS | PASS | Diagnostic | **yes** |
| pitcher:avg_spin | Projection | PASS marginal | PASS r=0.90 | **FAIL vs K%** | PASS | PASS | Diagnostic | **yes** |
| pitcher:avg_velo | Projection | **FAIL CI** | PASS r=0.92 | **FAIL vs K%** | PASS | **LHP-driven** | Diagnostic | **yes** |
| pitcher:whiff_rate | Projection | PASS vs baseline | PASS | **FAIL vs K%** | PASS | older weaker | Diagnostic | **yes** |
| pitcher:bb_pct | Diagnostic | FAIL nested | PASS | identity | PASS | — | Diagnostic | no |
| pitcher:k_bb_pct | Diagnostic | FAIL nested | PASS | identity | PASS | — | Diagnostic | no |
| pitcher:extension | Augmented | 1 fold | PASS r=0.96 | FAIL after K% | **19%** | thin | Insufficient evidence | **yes** |
| pitcher:stuff_plus | Diagnostic | 1 fold, CI∋0 | PASS r=0.83 | pooled leak | **19% not 28%** | thin | Insufficient evidence | **yes** |
| park_factor | Context | n/a | — | — | PASS | — | Context | no |

Gates A–E are the stated admission gates. It is acceptable that verdicts change.

## 14. Subgroup robustness

Recomputed in `artifacts/audit/subgroup_oos_recompute.csv`.

**2-year xwOBA:** improves every large group. Smaller for catchers (−0.00006) and young hitters (4/7 folds). Larger for 31+ and LHB. Not a single-population artifact.

**EV:** positive in age, handedness, and PA tiers. **Catchers: slightly harmful.** OF 4/7 folds. Not catcher-driven; catcher is the exception.

**K%:** starters and relievers both improve; high-IP larger than low-IP; LHP larger than RHP. Young pitchers only 3/7 folds.

**avg_velo:** LHP −0.00082 (7/7) vs RHP −0.00010 (4/7). Headline velocity value is **left-handed-pitcher driven**.

**whiff:** near-zero for 31+ (−0.00002).

Features that must not be advertised as universal: EV for catchers, velocity for RHP, whiff for older pitchers.

## 15. Trace of reported numbers

| Number | In current README/essay? | Traced to | Status |
|---|---|---|---|
| 2,836 | yes | sample table | Verified |
| 2,682 | yes | sample table | Verified; plausible under SP80/RP30 |
| 0.00121 | **no (stale)** | xwOBA vs *weak* baseline, abs(mean Δ)=0.001206 | Retired |
| 0.00093 / 0.000931 | yes | xwoba_w2 vs strong, mean fold Δ | Verified |
| 7/7 folds | yes | xwoba_w2 fold table | Verified |
| 0.00013 | **stale chase vs weak**; some passports | current chase vs strong = −0.000072 | Do not reuse as a headline |
| 0.83 | yes | Stuff+ reliability 0.827, N=1,174 seasons table | Verified definition/N; not a projection result |
| 28% | yes | seasons-table Stuff+ coverage 0.282 | **Wrong denominator** for the modeling claim |
| 33 features | **stale** | kitchen is 56 / 57 | Retired |
| 0.03427 vs 0.03523 | yes | admitted vs leaked kitchen; train-only kitchen 0.03524 | Direction verified; hitters CI excludes 0 |
| 0.04806 vs 0.04826 | yes | train-only kitchen 0.04832; pitcher CI includes 0 | “Did not beat” overstates certainty |
| 0.03627 → 0.03541 | yes | baseline_audit_hitter | Verified |
| 0.05025 → 0.04909 | yes | baseline_audit_pitcher | Verified |

No remaining headline in the README exists only in prose except the Stuff+ 28% figure, which exists in `admission_table.coverage` computed on the **seasons** table — an artifact, but the wrong population.

## 16. What was blocked until this audit was absorbed

Those blocks are now closed. After the 2026-08-19 revision:

- `README.md` and the short written summary match the audited table.
- Stuff+ is reported as 509/2,682 ≈ 19% modeling coverage, Insufficient Evidence, and is not described as “does not predict.”
- Velocity, spin, whiff, and z-contact are Diagnostic, not Projection.
- Kitchen-sink language uses 7 vs 56 hitters (CI excludes zero) and 11 vs 57 pitchers (CI includes zero). Ridge and Elastic Net kitchen rows use train-fold medians only.
- Cross-family pitcher demotions and Insufficient Evidence are written into `artifacts/admission_table.parquet`.
- `scripts/08_methodology_audit.py` re-run after the write-back reported `issues: []`. Canonical table, README, site, passports, and essay agree.

Dependent artifacts rebuilt in the original audit pass: `artifacts/audit/**`, `artifacts/audit_verdicts.csv`. Public artifacts were rebuilt in the follow-up revision pass.

## POST-REVISION CHECK

Admission engine coverage uses the modeling sample. `decide_verdict` includes Insufficient Evidence. `run.py` applies cross-family K%+BB% demotions and train-only kitchen imputation. Automated tests cover verdict taxonomy and validation-blind imputation.
