# Projection Signal Lab — STATUS

Last updated: 2026-08-19

## Current phase
Independent methodology audit incorporated. README, site, Feature Passports, kitchen-sink comparison, and `artifacts/admission_table.parquet` were rebuilt from audited evidence. Short written summary rewritten after the table.

## Done
1. Inventoried Savant custom (including extra field groups), MLB season + vs-L/R splits, park/people, frozen Stuff+, pitch-type scores.
2. `artifacts/feature_registry.csv` and `artifacts/excluded_features.csv` — no silent omissions.
3. Leakage-safe history representations (lag / 2-yr / 3-yr / yoy / league z) and a small set of pitch-family aggregates.
4. Stronger baseline: 2-year wOBA / 2-year K-BB% (current season if no prior).
5. Family vs baseline, family leave-one-out, greedy representatives, and **cross-family K%+BB% controls** for pitcher tracking metrics.
6. Exact identities flagged (K-BB% = K%−BB%; any two of K%/BB%/K-BB% determine the third).
7. Six-way taxonomy including **Insufficient Evidence**. Kitchen-sink vs admitted uses **train-fold medians only**.
8. Short ≤250-word summary rewritten from the corrected table.

## Headline empirical results (post-audit revision)
- Canonical samples verified: hitters 2,836; pitchers 2,682; 0 duplicates; 1,065 SP / 1,617 RP; 2020 IP exception valid.
- Hitters Projection: woba_w2 (baseline), xwoba_w2 (mean ΔRMSE −0.000931, 7/7, CI excludes 0), EV, woba_w3. Current wOBA Exclude. Barrel% / HardHit% Diagnostic. Chase / sprint Diagnostic.
- Pitchers: preferred 2-year K-BB% + current K%. Velocity / spin / whiff / z-contact Diagnostic after K%+BB%. Stuff+ and extension Insufficient Evidence (modeling coverage 19%, not 28%).
- Kitchen-sink: hitters 7 vs 56, admitted better, CI excludes 0. Pitchers 11 vs 57, slightly better on average, CI includes 0.

## How to refresh
PYTHONPATH=src python scripts/01_pull_data.py
PYTHONPATH=src python scripts/02_build_panels.py
PYTHONPATH=src python scripts/03_run_admission.py
PYTHONPATH=src python scripts/04_build_artifacts.py
PYTHONPATH=src pytest tests -q
