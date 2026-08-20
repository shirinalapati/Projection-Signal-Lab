# Archival: next-season K-BB% as a pitcher target

This file is **not** part of the public Projection Signal Lab product.

An earlier pitcher study treated **next-season K-BB%** (`y_k_bb_pct`) as a modeling target. That experiment is preserved here for provenance. It does **not** define canonical verdicts, public counts, Reliability Map points, passports, or findings.

## Current architecture

Pitching’s only public projection target is **next-season FIP**. K-BB% remains a **candidate pitching feature** (with K% and BB%) for predicting FIP. The identity `K-BB% = K% − BB%` is still enforced so those rates are not three independent skills.

## Where the old table lives

- `artifacts/historical/admission_pitching_y_k_bb_pct.csv`
- `artifacts/historical/admission_pitching_y_k_bb_pct.parquet` (if present)
- `artifacts/historical/extras_pitching_fip_y_k_bb_pct_secondary.json` (if present)
- `artifacts/historical/kitchen_sink_comparison_pitcher_y_k_bb_pct.json` (if present)

Under that archived question, Stuff+ and extension were Diagnostic for next-season K-BB% after strikeout and walk information. Those rows were not copied onto the FIP table.

## Do not use this study as

- a sixth public target
- a “secondary robustness target” in public methodology
- a Reliability Map filter
- a Models-page outcome
- a passport section labeled “Target: next-season K-BB%”
