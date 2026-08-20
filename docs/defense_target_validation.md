# Defense target validation (2015–2025)

## Decision

Official Statcast **OAA is empty for 2015** at every non-catcher position (0 rows with `min=1`). The packaged OAA leaderboard therefore cannot be the 2015–2025 target without shrinking the research era.

We constructed an OAA-like **expected play-conversion** metric from Statcast batted balls (launch speed/angle, spray, hit location) for 2015–2025. On the 2016–2025 overlap with official OAA, that reconstruction correlates only about **0.14** with OAA. It is retained as a **feature** (`epcaa`) and a robustness target (`y_epcaa_rate`), not as the headline defensive outcome.

The **primary 2015–2025 target** is Baseball Reference **fielding runs plus catcher runs**:

`def_rv = runs_field + runs_catcher`

expressed as **runs per 1,000 defensive innings**.

This is DRS-era BR fielding value, **not** official errors, and **not** FanGraphs Def. Position scarcity (`runs_position`) is excluded so the target measures defensive performance rather than the positional adjustment used in WAR.

Catcher framing/blocking/throwing in this system lives in `runs_catcher`. Infield/outfield range and throwing live in `runs_field`. Those groups are still modeled with position indicators; they are not treated as the same process.

## Why errors are not the target

Official errors / fielding percentage record only a subset of failed plays — those an official scorer charges as errors. An outfielder can fail to convert a high-probability fly ball, have it scored a hit, and show **zero errors**. BR fielding runs and OAA both debit that play. In this panel, **errors correlate about −0.02** with `def_rv`, i.e. they do not define the outcome.

## Validation against OAA (2016–2025 overlap)

| Check | Result |
| --- | --- |
| Official OAA 2015 | 0 player-seasons |
| Official OAA 2016–2025 | present; modeling-sample coverage ≈ 80% |
| BR `def_rv` vs official OAA | ≈ **0.63** |
| OAA-like EPCAA vs official OAA | ≈ 0.14 |
| Errors vs BR `def_rv` | ≈ −0.02 |
| 2017 BR fielding leaders | Andrelton Simmons +36, Mookie Betts +28, Byron Buxton +23 — matches the public BR table |

The 0.63 correlation with OAA in the overlap years is the bridging evidence that the 2015–2025 BR target measures the same *kind* of thing as Statcast conversion value, without pretending 2015 OAA exists.

## Rate vs total

- Primary: `def_rv` / 1,000 innings (`y_def_rv_rate`)
- Secondary: total `def_rv` (`y_def_rv`)
- Robustness: official OAA per opportunity where observed (`y_oaa_rate`); EPCAA rate (`y_epcaa_rate`)

## Window

Canonical defense seasons cover **2015–2025**. Expanding-window OOS folds begin once prior seasons exist for training; that is a validation design choice, not reduced data coverage.
