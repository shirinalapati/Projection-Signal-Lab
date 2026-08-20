"""Project-wide configuration for Projection Signal Lab."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXTERNAL = ROOT / "data" / "external"
ARTIFACTS = ROOT / "artifacts"
FIGURES = ARTIFACTS / "figures"
PASSPORTS = ARTIFACTS / "passports"
SITE_DIR = ARTIFACTS / "site"
RESEARCH_DIR = ROOT / "research"

SEASON_START = 2015
SEASON_END = 2025  # last complete season used as a target year
FEATURE_SEASONS = list(range(SEASON_START, SEASON_END))  # 2015-2024 features
TARGET_SEASONS = list(range(SEASON_START + 1, SEASON_END + 1))  # 2016-2025 targets

HITTER_PA_PRIMARY = 150
HITTER_PA_SENSITIVITY = (100, 150, 200)
PITCHER_IP_SP = 80.0
PITCHER_IP_RP = 30.0
PITCHER_BF_SP = 300
PITCHER_BF_RP = 120
STARTER_GS_SHARE = 0.50

EXPANDING_TEST_YEARS = list(range(2019, SEASON_END + 1))  # predict 2019..2025
RIDGE_ALPHA = 1.0
ELASTICNET_L1_RATIO = 0.5
ELASTICNET_ALPHAS = (0.01, 0.05, 0.1, 0.3, 1.0, 3.0)
N_BOOTSTRAP = 400
BOOTSTRAP_SEED = 42
MATERIAL_LIFT_FRAC = 0.005  # 0.5% of baseline RMSE

COVID_YEAR = 2020
STICKY_STUFF_YEAR = 2021
PITCH_CLOCK_YEAR = 2023

EXTERNAL_STUFF = Path(
    "/Users/Shirin/MLB2026/Stuff_Quality/data/frozen_arsenal_scores_2023_2025.parquet"
)
EXTERNAL_PITCH_TYPES = Path(
    "/Users/Shirin/MLB2026/Stuff_Quality/data/pitch_type_scores.parquet"
)
EXTERNAL_PLAYERS = Path(
    "/Users/Shirin/Propsect_Lab/data/processed/players_canonical.parquet"
)
EXTERNAL_PARK = Path(
    "/Users/Shirin/Propsect_Lab/artifacts/translations/park_factors.parquet"
)

# Platoon split: require this many PA/BF vs each side before the split is a feature.
PLATOON_MIN_PA = 40
PLATOON_MIN_BF = 40
# Pitch-type arsenal: count a pitch as part of the mix at this pitch threshold.
ARSENAL_MIN_PITCHES = 50

TEAM_TO_MLBAM = {
    "LAA": 108, "ANA": 108,
    "ARI": 109, "AZ": 109,
    "BAL": 110,
    "BOS": 111,
    "CHC": 112,
    "CIN": 113,
    "CLE": 114,
    "COL": 115,
    "DET": 116,
    "HOU": 117,
    "KCR": 118, "KC": 118,
    "LAD": 119,
    "WSN": 120, "WSH": 120, "WAS": 120,
    "NYM": 121,
    "OAK": 133, "ATH": 133,
    "PIT": 134,
    "SDP": 135, "SD": 135,
    "SEA": 136,
    "SFG": 137, "SF": 137,
    "STL": 138,
    "TBR": 139, "TB": 139, "TBD": 139,
    "TEX": 140,
    "TOR": 141,
    "MIN": 142,
    "PHI": 143,
    "ATL": 144,
    "CHW": 145, "CWS": 145,
    "MIA": 146, "FLA": 146,
    "NYY": 147,
    "MIL": 158,
}

CHADWICK_URLS = (
    "https://raw.githubusercontent.com/chadwickbureau/register/master/data/people.csv",
    "https://github.com/chadwickbureau/register/raw/refs/heads/master/data/people.csv",
)

RANDOM_SEED = 42
