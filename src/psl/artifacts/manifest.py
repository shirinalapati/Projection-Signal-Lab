"""Write data_manifest.json and model_cards.json from cached metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from psl.config import ARTIFACTS, DATA_PROCESSED, DATA_RAW, ROOT, SEASON_END, SEASON_START


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_manifest() -> dict:
    files = []
    for folder in (DATA_RAW, DATA_PROCESSED, ARTIFACTS):
        if not folder.exists():
            continue
        for p in sorted(folder.rglob("*")):
            if p.suffix in {".parquet", ".csv", ".json"} and p.is_file():
                meta = p.with_name(p.stem + ".meta.json")
                rec = {
                    "path": str(p.relative_to(ROOT)),
                    "bytes": p.stat().st_size,
                    "suffix": p.suffix,
                }
                if meta.exists():
                    rec["meta"] = json.loads(meta.read_text())
                files.append(rec)
    payload = {
        "built_at": _now(),
        "season_window": [SEASON_START, SEASON_END],
        "files": files,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "data_manifest.json").write_text(json.dumps(payload, indent=2))
    (DATA_PROCESSED / "data_manifest.json").write_text(json.dumps(payload, indent=2))
    return payload


def build_model_cards() -> dict:
    audit_path = DATA_PROCESSED / "panel_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    cards = {
        "hitter_projection": {
            "target": "next-season wOBA (y_woba)",
            "robustness_target": "park/league-adjusted wOBA index (y_wrc_plus), not official FanGraphs wRC+",
            "filters": "PA >= 150 in season t and t+1",
            "baseline": ["age", "pa", "woba_w2 (2-year PA-weighted wOBA; current if no prior)", "park_factor"],
            "baseline_weak_contrast": ["age", "pa", "woba", "park_factor"],
            "validation": "expanding window; train seasons <= test_year-2; features from test_year-1; outcomes in test_year",
            "models": ["persistence", "Ridge(alpha=1) + StandardScaler", "ElasticNetCV"],
            "primary_split": "temporal expanding window — not random",
            "sample_n": audit.get("hitter_sample_n"),
            "projection_core": ["age", "pa", "woba_w2", "park_factor", "xwoba_w2", "ev", "woba_w3"],
            "kitchen_sink": "7 admitted vs 56 kitchen-sink; train-fold median imputation only; admitted better, CI excludes zero",
            "seed": 42,
        },
        "pitcher_projection": {
            "target": "next-season FIP (y_fip)",
            "sensitivity_targets": ["y_fip_minus", "y_era", "y_whip"],
            "filters": "starters IP>=80 or relievers IP>=30 in t and t+1; starter if GS/G >= 0.5; 2020 exception 25/10 IP",
            "baseline": ["age", "ip", "starter_role", "fip_w2 (2-year IP-weighted FIP; current if no prior)", "park_factor"],
            "baseline_weak_contrast": ["age", "ip", "starter_role", "fip", "park_factor"],
            "k_bb_identity": "K-BB% = K% − BB% exactly; any two of K%, BB%, K-BB% determine the third. Current K-BB% is a candidate feature for next-season FIP, not a separate projection target and not three independent skills.",
            "validation": "same expanding-window engine as hitters",
            "stuff_plus": "Leakage-safe expanding-window Stuff+ on Statcast 2015-2025. Projection for next-season FIP.",
            "extension": "Projection for next-season FIP.",
            "velocity_spin_whiff": "Average velocity, spin, and whiff rate were Diagnostic for next-season FIP after family tests. Fastball velocity, z-contact, and CSW earned Projection for FIP.",
            "sample_n": audit.get("pitcher_sample_n"),
            "kitchen_sink": "Admitted FIP model vs kitchen-sink; train-fold median imputation only; admitted better, CI excludes zero",
            "seed": 42,
        },
        "baserunning_projection": {
            "target": "next-season Baseball Reference baserunning runs per 100 times on base",
            "window": "2015-2025 target era; packaged Statcast baserunning RV leaderboard was not used as the headline because it lacks full-era steal coverage in pitch files",
            "baseline": ["age", "pa", "br_rv_rate_w2", "park_factor"],
            "projection_examples": ["br_rv_rate_w2", "sprint_speed", "attempt_rate"],
        },
        "defense_projection": {
            "target": "next-season Baseball Reference fielding + catcher runs per 1,000 defensive innings",
            "not_the_target": "official errors / fielding percentage",
            "window": "2015-2025; official OAA starts 2016 and is a feature/robustness input, not the 2015-2025 target",
            "baseline": ["age", "def_inn", "pos_group_if/of/c", "def_rv_rate_w2"],
            "war_source": "Baseball Reference bWAR, labeled as such; FanGraphs fWAR was not mixed in",
        },
        "overall_value": {
            "target": "next-season Baseball Reference WAR rate (600 PA for hitters, 200 IP for pitchers)",
            "note": "WAR is not a replacement for the component models",
        },
        "admission_taxonomy": {
            "verdicts": [
                "Projection",
                "Augmented Projection",
                "Diagnostic",
                "Context",
                "Exclude",
                "Insufficient Evidence",
            ],
            "Diagnostic": "This metric helps describe how a player succeeds or struggles, but did not add enough independent future-prediction value to the broad model.",
            "Insufficient Evidence": "We do not yet have enough reliable coverage or temporal validation to make a confident projection decision.",
            "Exclude": "The metric did not provide enough unique predictive or diagnostic value in this study.",
        },
        "limitations": [
            "FanGraphs leaders HTML is Cloudflare-blocked; study uses Baseball Savant custom leaderboards + MLB Stats API.",
            "wRC+ is an approximate park/league-adjusted index.",
            "Savant whiff% is swing-based, not FanGraphs SwStr% (whiffs per pitch).",
            "Scouting and injury histories are not fabricated.",
            "Candidate universe is inventoried in artifacts/feature_registry.csv; untested fields have reasons in artifacts/excluded_features.csv.",
            "Savant custom silently NaNs some fields (max EV, Zone%, SIERA, CSW, extension) when requested; those are logged as UNAVAILABLE_RELIABLY rather than skipped quietly.",
        ],
    }
    (ARTIFACTS / "model_cards.json").write_text(json.dumps(cards, indent=2))
    return cards


if __name__ == "__main__":
    build_manifest()
    build_model_cards()
    print("manifest + model cards written")
