"""Document candidate sources before modeling baserunning and defense."""

from __future__ import annotations

import pandas as pd

from psl.config import ARTIFACTS, DATA_RAW, DATA_PROCESSED, SEASON_END, SEASON_START

ROWS = [
    {
        "source": "Baseball Savant OAA leaderboard",
        "seasons": "2016-2025 (2015: 0 rows at all positions)",
        "player_identifiers": "Savant player_id (MLBAM)",
        "granularity": "player-season by position",
        "candidate_target_fields": "outs_above_average, fielding_runs_prevented",
        "candidate_feature_fields": "OAA, directional OAA, success vs expected",
        "coverage": "No 2015; 2016–2025 complete enough for a feature / robustness target",
        "known_limitations": "Packaged OAA does not span the required 2015–2025 window.",
        "selected": "not as primary target",
        "reason": "2015 is empty. Retained as a 2016–2025 feature and secondary target.",
    },
    {
        "source": "pybaseball Statcast day cache (full CSV columns)",
        "seasons": "2015-2025 regular season game dates",
        "player_identifiers": "batter, pitcher, on_1b/2b/3b, fielder_2–9",
        "granularity": "pitch / play event",
        "candidate_target_fields": "events, delta_run_exp, hc_x/hc_y, launch_speed/angle, hit_location",
        "candidate_feature_fields": "steal events, BIP conversion, sprint-independent play outcomes",
        "coverage": "Full-column cache covers 2015–2025; pitch-quality subset in data/raw/statcast dropped runner/fielder columns",
        "known_limitations": "Official OAA tracking (starting position, catch probability) is not reproduced; this is an OAA-like reconstruction.",
        "selected": "yes — reconstruction source",
        "reason": "Only public play-level source with 2015–2025 Statcast location/event fields already cached.",
    },
    {
        "source": "Baseball Reference war_daily_bat (bWAR)",
        "seasons": "2015-2025",
        "player_identifiers": "mlb_ID (MLBAM)",
        "granularity": "player-stint, aggregated to player-season",
        "candidate_target_fields": "runs_br, runs_field, runs_catcher, runs_defense, WAR, Inn, PA",
        "candidate_feature_fields": "same component runs; batting WAR",
        "coverage": "Complete 2015–2025",
        "known_limitations": "Fielding runs are BR/DRS-era, not Statcast OAA. WAR is bWAR, not fWAR.",
        "selected": "yes — WAR target; fallback/validation for BR and DEF runs",
        "reason": "Historically complete labeled public run values spanning 2015–2025.",
    },
    {
        "source": "Baseball Reference war_daily_pitch",
        "seasons": "2015-2025",
        "player_identifiers": "mlb_ID",
        "granularity": "player-season",
        "candidate_target_fields": "WAR, IPouts",
        "candidate_feature_fields": "pitcher bWAR rate",
        "coverage": "Complete 2015–2025",
        "known_limitations": "Pitcher WAR is not a substitute for FIP.",
        "selected": "yes — optional pitcher overall-value study",
        "reason": "Same WAR definition as batting file.",
    },
    {
        "source": "MLB Stats API season fielding",
        "seasons": "2015-2025",
        "player_identifiers": "mlbam_id",
        "granularity": "player-season-position",
        "candidate_target_fields": "none (errors/fielding% are not the target)",
        "candidate_feature_fields": "errors, assists, putouts, innings, CS/SB as catcher",
        "coverage": "Complete 2015–2025",
        "known_limitations": "Official scoring; misses unconverted high-probability plays scored as hits.",
        "selected": "features only",
        "reason": "Traditional counting stats are candidates, never the defensive outcome.",
    },
    {
        "source": "FanGraphs leaders API",
        "seasons": "reachable (2015 sample succeeded)",
        "player_identifiers": "xMLBAMID",
        "granularity": "player-season",
        "candidate_target_fields": "WAR, BsR, Def (fWAR definition)",
        "candidate_feature_fields": "fWAR components",
        "coverage": "API responded 200 for 2015 batting leaders",
        "known_limitations": "Would mix fWAR with bWAR if used casually. FanGraphs HTML leaders remain Cloudflare-blocked.",
        "selected": "not selected for canonical WAR",
        "reason": "Keep a single labeled WAR definition: Baseball Reference bWAR.",
    },
    {
        "source": "Savant custom batter leaderboard",
        "seasons": "2015-2025 (already in project)",
        "player_identifiers": "player_id",
        "granularity": "player-season",
        "candidate_target_fields": "none for BR/DEF run value",
        "candidate_feature_fields": "sprint_speed, hp_to_1b, PA, xwOBA",
        "coverage": "Sprint speed present in 2015",
        "known_limitations": "No baserunning RV or fielding RV columns in the custom extract used here.",
        "selected": "features (speed, hitting context)",
        "reason": "Already assembled; does not supply the 2015–2025 run-value targets.",
    },
]


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(ROWS)
    br = df.copy()
    br.to_csv(ARTIFACTS / "baserunning_source_audit.csv", index=False)
    df.to_csv(ARTIFACTS / "defense_source_audit.csv", index=False)
    print("wrote source audits", len(df))
    print("raw exists", (DATA_RAW / "bwar_bat_daily.parquet").exists(), "plays dir", (DATA_RAW / "statcast_plays").exists())
    print("window", SEASON_START, SEASON_END, "processed", DATA_PROCESSED.exists())


if __name__ == "__main__":
    main()
