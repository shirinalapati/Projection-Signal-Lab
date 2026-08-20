# Projection Signal Lab

**What belongs in a baseball projection depends first on what we are trying to project.**

Projection Signal Lab tests not only whether a baseball metric predicts the future, but **what part of future player value** it predicts. A metric does not receive one universal verdict. It receives a verdict relative to a target.

A feature does not earn Projection status because it sounds mechanistically important, fits historical data, or correlates with future performance. It must add repeatable incremental out-of-time information after accounting for what that target’s model already knows. Lack of sufficient evidence is not proof that a metric has no value.

It is a research project on which baseball information should change a projection of future player performance, and which information is better used to explain that performance. **The data determine the answer.**

## Component targets (2015–2025)

Every primary component covers the same Statcast-era window. Candidate **features** may start later; those cases become Augmented Projection or Insufficient Evidence rather than shrinking the study.

| Component | Primary future target | Sample (t → t+1) |
|---|---|---|
| Hitting | next-season wOBA | 2,836 hitter-seasons (PA ≥ 150 in both years) |
| Pitching | next-season FIP | 2,682 pitcher-seasons (SP 80 IP / RP 30 IP; 2020 25/10) |
| Baserunning | next-season baserunning run-value rate | 2,836 (BR runs per 100 times on base) |
| Defense | next-season fielding run-value rate | 3,042 (≥ 200 defensive innings) |
| Overall value | next-season WAR rate | bWAR / 600 PA (hitters) and bWAR / 200 IP (pitchers) |

WAR is a higher-level outcome, not a replacement for the component models. Overall value uses **Baseball Reference bWAR**, labeled as such. FanGraphs fWAR is not mixed in.

K-BB% remains a pitching **feature** (with K% and BB%) for predicting next-season FIP. Those rates are not three independent skills.

## Candidate universe

Every field in Baseball Savant custom leaderboards, MLB Stats API season and vs-L/R splits, Prospect_Lab park/people files, Baseball Reference WAR/fielding/baserunning, frozen Arsenal Intelligence Stuff+, and pitch-type scores is listed in [`artifacts/feature_registry.csv`](artifacts/feature_registry.csv). Fields that were not tested have an explicit reason in [`artifacts/excluded_features.csv`](artifacts/excluded_features.csv). Incomplete coverage is not an automatic skip.

Savant custom silently returns all-NaN for some requested fields. Those are logged as unavailable, not dropped quietly. FanGraphs leaders-legacy HTML is Cloudflare-blocked (403); those tables were not fabricated. Arm strength and modern catcher tracking that lack a consistent 2015–2025 history are not invented.

## Validation

- Year-t features predict year-(t+1) outcomes.
- Expanding window (train ≤ T−2, features in T−1, outcomes in T). No random row split for headline claims.
- Imputers, scalers, and model fitting use training data only.
- Baselines are **target-specific** (hitting: age + PA + 2-year wOBA + park; pitching: age + IP + role + 2-year FIP + park; similarly for baserunning, defense, and WAR).
- **K-BB% = K% − BB% exactly.** Those rates are not three independent skills.
- Official errors / fielding percentage are never the defensive target.

## What we found

Verdicts are always **for a named target**.

### Hitting → next-season wOBA (preserved)

2-year xwOBA: Projection. Mean ΔRMSE **−0.000931**, **7/7** folds, bootstrap CI excluding zero, after a baseline that already included 2-year wOBA. Exit velocity: Projection. Barrel%, Hard-Hit%, chase rate, and sprint speed: **Diagnostic for next-season wOBA**. Current wOBA: Exclude once 2-year wOBA is present.

### Pitching → next-season FIP (rerun)

2-year FIP is the history-aware baseline. **3-year K-BB%**, **K%**, **Stuff+**, **extension**, **fastball velocity**, **in-zone contact allowed**, and **CSW** earned Projection for FIP. Average velocity, spin, and whiff rate remained Diagnostic for FIP after family tests. Current FIP is Exclude once 2-year FIP is present. Recent K-BB% was evaluated as a predictor of future FIP; current K-BB% did **not** earn independent Projection.

### Baserunning → next-season BR run-value rate

Packaged Statcast steal run values are not in pitch files for 2015–2025, so the headline target is Baseball Reference baserunning runs per 100 times on base, validated in [`docs/baserunning_target_validation.md`](docs/baserunning_target_validation.md). **Sprint Speed** and **steal attempt rate** earned Projection for this target, along with multi-year baserunning history.

### Defense → next-season fielding run-value rate

Official Statcast OAA has no 2015 rows, so it is not the 2015–2025 target. The headline is Baseball Reference fielding + catcher runs per 1,000 innings (not errors). See [`docs/defense_target_validation.md`](docs/defense_target_validation.md). 2-year and 3-year fielding-rate history earned Projection. Outs Above Average performance, sprint speed, and official errors were Diagnostic after that history. Catcher value is in the BR catcher-run component and is not compared with CF OAA as if they measured the same process.

### Overall value → next-season bWAR rate

Prior WAR rate earned Projection. Exit velocity added hitter WAR-rate information; 2-year K-BB% added pitcher WAR-rate information. Component rates did not automatically inherit Projection in the WAR layer.

### Target dependence (flagship)

Sprint Speed was Diagnostic for next-season wOBA and Projection for next-season baserunning. Stuff+ earned Projection for next-season FIP. Age stayed Context across components.

### Kitchen-sink

Train-fold median imputation only.

- Hitting (wOBA) and pitching (FIP): the admitted-feature model generalized better than the all-feature model; uncertainty excluded zero.
- Baserunning and defense: differences were inconclusive (CI included zero).
- Hitter WAR rate: the all-feature model had lower error than the selective model; uncertainty excluded zero. Overall value is not a place to assume that thinner models always win.

## Assumed proprietary data

Scouting grades, injury histories, and minor-league translations are **not invented** here. They would enter the **same gates**, and they would be **target-specific**: a speed grade can belong in baserunning or defense without improving wOBA. Injury history belongs more naturally in playing-time / availability projection than in rate-skill models. Raw minor-league statistics would first be adjusted for level, park, league quality, and age relative to level. See [docs/assumed_proprietary_data.md](docs/assumed_proprietary_data.md).

## Repo

```
src/psl/           # data, models, admission engine, artifacts, site
scripts/           # pull → panels → admission → artifacts → Feature Audit
docs/              # methodology audit, target validation, proprietary-data notes
research/          # static findings site
artifacts/         # admission_table, feature_registry, excluded_features, passports
tests/             # leakage, uniqueness, temporal splits, public copy
```

```
PYTHONPATH=src python scripts/01_pull_data.py
PYTHONPATH=src python scripts/02_build_panels.py
PYTHONPATH=src python scripts/14_build_component_panels.py
PYTHONPATH=src python scripts/03_run_admission.py
PYTHONPATH=src python scripts/04_build_artifacts.py
PYTHONPATH=src python scripts/08_methodology_audit.py
PYTHONPATH=src pytest tests -q
```

Open `research/index.html` for the public writeup.
