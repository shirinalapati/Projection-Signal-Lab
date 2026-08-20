"""Candidate feature catalogs. Interpretability flags are not verdicts.

The catalog is the TEST / DERIVE_AND_TEST set that enters the admission engine.
Every other available field is accounted for in artifacts/feature_registry.csv.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    family: str
    columns: tuple[str, ...]  # panel column names
    role: str  # skill | environment | demographic
    process: bool  # interpretable mechanism if it fails projection gates
    description: str


HITTER_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("avg", "outcome", ("avg",), "skill", False, "Batting average"),
    FeatureSpec("obp", "outcome", ("obp",), "skill", False, "On-base percentage"),
    FeatureSpec("slg", "outcome", ("slg",), "skill", False, "Slugging percentage"),
    FeatureSpec("ops", "outcome", ("ops",), "skill", False, "On-base plus slugging"),
    FeatureSpec("woba", "outcome", ("woba",), "skill", False, "Current-season weighted on-base average"),
    FeatureSpec("woba_lag1", "outcome", ("woba_lag1",), "skill", False, "Prior-season wOBA"),
    FeatureSpec("woba_w2", "outcome", ("woba_w2",), "skill", False, "PA-weighted 2-year wOBA (current if no prior)"),
    FeatureSpec("woba_w3", "outcome", ("woba_w3",), "skill", False, "PA-weighted 3-year wOBA"),
    FeatureSpec("woba_yoy", "outcome", ("woba_yoy",), "skill", False, "Year-over-year wOBA change"),
    FeatureSpec("woba_z", "outcome", ("woba_z",), "skill", False, "League-year standardized wOBA"),
    FeatureSpec("woba_x_age", "outcome", ("woba_x_age",), "skill", False, "Current wOBA × (age − 27)"),
    FeatureSpec("wrc_plus", "outcome", ("wrc_plus",), "skill", False, "Park/league-adjusted offensive runs index"),
    FeatureSpec("babip", "outcome", ("babip",), "skill", True, "Batting average on balls in play"),
    FeatureSpec("xwoba", "expected", ("xwoba",), "skill", True, "Expected wOBA from quality of contact"),
    FeatureSpec("xba", "expected", ("xba",), "skill", True, "Expected batting average"),
    FeatureSpec("xslg", "expected", ("xslg",), "skill", True, "Expected slugging"),
    FeatureSpec("xwobacon", "expected", ("xwobacon",), "skill", True, "Expected wOBA on contact"),
    FeatureSpec("xiso", "expected", ("xiso",), "skill", True, "Expected isolated power"),
    FeatureSpec("xwoba_w2", "expected", ("xwoba_w2",), "skill", True, "PA-weighted 2-year xwOBA"),
    FeatureSpec("o_swing_pct", "plate_discipline", ("o_swing_pct",), "skill", True, "Chase rate (O-Swing%)"),
    FeatureSpec("z_swing_pct", "plate_discipline", ("z_swing_pct",), "skill", True, "In-zone swing rate"),
    FeatureSpec("swing_pct", "plate_discipline", ("swing_pct",), "skill", True, "Overall swing rate"),
    FeatureSpec("meatball_swing_pct", "plate_discipline", ("meatball_swing_pct",), "skill", True, "Swing rate on meatballs"),
    FeatureSpec("edge_pct", "plate_discipline", ("edge_pct",), "skill", True, "Share of pitches on the edge of the zone"),
    FeatureSpec("bb_pct", "plate_discipline", ("bb_pct",), "skill", True, "Walk rate"),
    FeatureSpec("bb_pct_w2", "plate_discipline", ("bb_pct_w2",), "skill", True, "PA-weighted 2-year walk rate"),
    FeatureSpec("z_contact_pct", "contact_ability", ("z_contact_pct",), "skill", True, "In-zone contact rate"),
    FeatureSpec("o_contact_pct", "contact_ability", ("o_contact_pct",), "skill", True, "Out-of-zone contact rate"),
    FeatureSpec("swstr_pct", "contact_ability", ("swstr_pct",), "skill", True, "Whiff rate (Savant swings-and-misses / swings)"),
    FeatureSpec("k_pct", "contact_ability", ("k_pct",), "skill", True, "Strikeout rate"),
    FeatureSpec("k_pct_w2", "contact_ability", ("k_pct_w2",), "skill", True, "PA-weighted 2-year strikeout rate"),
    FeatureSpec("ev", "contact_quality", ("ev",), "skill", True, "Average exit velocity"),
    FeatureSpec("avg_best_speed", "contact_quality", ("avg_best_speed",), "skill", True, "Average best-speed (bat-to-ball quality)"),
    FeatureSpec("hard_hit_pct", "contact_quality", ("hard_hit_pct",), "skill", True, "Hard-hit rate"),
    FeatureSpec("barrel_pct", "contact_quality", ("barrel_pct",), "skill", True, "Barrel rate"),
    FeatureSpec("sweet_spot_pct", "contact_quality", ("sweet_spot_pct",), "skill", True, "Sweet-spot rate"),
    FeatureSpec("la", "contact_quality", ("la",), "skill", True, "Average launch angle"),
    FeatureSpec("barrel_pct_w2", "contact_quality", ("barrel_pct_w2",), "skill", True, "PA-weighted 2-year barrel rate"),
    FeatureSpec("ev_w2", "contact_quality", ("ev_w2",), "skill", True, "PA-weighted 2-year exit velocity"),
    FeatureSpec("iso", "power", ("iso",), "skill", True, "Isolated power"),
    FeatureSpec("gb_pct", "batted_ball", ("gb_pct",), "skill", True, "Ground-ball rate"),
    FeatureSpec("fb_pct", "batted_ball", ("fb_pct",), "skill", True, "Fly-ball rate"),
    FeatureSpec("ld_pct", "batted_ball", ("ld_pct",), "skill", True, "Line-drive rate"),
    FeatureSpec("pull_pct", "batted_ball", ("pull_pct",), "skill", True, "Pull rate"),
    FeatureSpec("cent_pct", "batted_ball", ("cent_pct",), "skill", True, "Center-field spray rate"),
    FeatureSpec("oppo_pct", "batted_ball", ("oppo_pct",), "skill", True, "Opposite-field rate"),
    FeatureSpec("sprint_speed", "speed", ("sprint_speed",), "skill", True, "Statcast sprint speed"),
    FeatureSpec("hp_to_1b", "speed", ("hp_to_1b",), "skill", True, "Home-to-first time"),
    FeatureSpec("sb_rate", "speed", ("sb_rate",), "skill", True, "Stolen bases per plate appearance"),
    FeatureSpec("sb_pct", "speed", ("sb_pct",), "skill", True, "Stolen-base success rate"),
    FeatureSpec("ops_vs_lhp", "platoon", ("ops_vs_lhp",), "skill", True, "OPS versus left-handed pitching"),
    FeatureSpec("ops_vs_rhp", "platoon", ("ops_vs_rhp",), "skill", True, "OPS versus right-handed pitching"),
    FeatureSpec("platoon_ops_diff", "platoon", ("platoon_ops_diff",), "skill", True, "OPS vs LHP minus OPS vs RHP"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("bats_left", "demographic", ("bats_left",), "demographic", False, "Bats left-handed"),
    FeatureSpec("bats_switch", "demographic", ("bats_switch",), "demographic", False, "Switch hitter"),
    FeatureSpec("pa", "playing_time", ("pa",), "demographic", False, "Plate appearances / playing time"),
    FeatureSpec("is_catcher", "position", ("is_catcher",), "demographic", False, "Primary catcher"),
    FeatureSpec("seasons_since_debut", "demographic", ("seasons_since_debut",), "demographic", False, "MLB seasons since debut"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("lg_woba", "environment", ("lg_woba",), "environment", False, "League-year wOBA environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
)

HITTER_FAMILIES = {
    "outcome": (
        "avg", "obp", "slg", "ops", "woba", "woba_lag1", "woba_w2", "woba_w3",
        "woba_yoy", "woba_z", "woba_x_age", "wrc_plus", "babip",
    ),
    "expected": ("xwoba", "xba", "xslg", "xwobacon", "xiso", "xwoba_w2"),
    "plate_discipline": (
        "o_swing_pct", "z_swing_pct", "swing_pct", "meatball_swing_pct",
        "edge_pct", "bb_pct", "bb_pct_w2",
    ),
    "contact_ability": ("z_contact_pct", "o_contact_pct", "swstr_pct", "k_pct", "k_pct_w2"),
    "contact_quality": (
        "ev", "avg_best_speed", "hard_hit_pct", "barrel_pct", "sweet_spot_pct",
        "la", "barrel_pct_w2", "ev_w2",
    ),
    "power": ("iso",),
    "batted_ball": ("gb_pct", "fb_pct", "ld_pct", "pull_pct", "cent_pct", "oppo_pct"),
    "speed": ("sprint_speed", "hp_to_1b", "sb_rate", "sb_pct"),
    "platoon": ("ops_vs_lhp", "ops_vs_rhp", "platoon_ops_diff"),
    "playing_time": ("pa",),
    "position": ("is_catcher",),
    "demographic": ("age", "bats_left", "bats_switch", "seasons_since_debut"),
    "environment": ("park_factor", "lg_woba", "covid_season"),
}

PITCHER_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("era", "outcome", ("era",), "skill", False, "Earned run average"),
    FeatureSpec("fip", "outcome", ("fip",), "skill", False, "Fielding-independent pitching"),
    FeatureSpec("fip_lag1", "outcome", ("fip_lag1",), "skill", False, "Prior-season FIP"),
    FeatureSpec("fip_w2", "outcome", ("fip_w2",), "skill", False, "IP-weighted 2-year FIP (current if no prior)"),
    FeatureSpec("fip_w3", "outcome", ("fip_w3",), "skill", False, "IP-weighted 3-year FIP"),
    FeatureSpec("fip_yoy", "outcome", ("fip_yoy",), "skill", False, "Year-over-year FIP change"),
    FeatureSpec("fip_z", "outcome", ("fip_z",), "skill", False, "League-year standardized FIP"),
    FeatureSpec("fip_minus", "outcome", ("fip_minus",), "skill", False, "Park/league-adjusted FIP (FIP- equivalent; 100 is average)"),
    FeatureSpec("whip", "outcome", ("whip",), "skill", False, "Walks plus hits per inning"),
    FeatureSpec("k_bb_pct", "outcome", ("k_bb_pct",), "skill", True, "Current-season strikeout minus walk rate"),
    FeatureSpec("k_bb_pct_lag1", "outcome", ("k_bb_pct_lag1",), "skill", True, "Prior-season K-BB%"),
    FeatureSpec("k_bb_pct_w2", "outcome", ("k_bb_pct_w2",), "skill", True, "IP-weighted 2-year K-BB% (current if no prior)"),
    FeatureSpec("k_bb_pct_w3", "outcome", ("k_bb_pct_w3",), "skill", True, "IP-weighted 3-year K-BB%"),
    FeatureSpec("k_bb_pct_yoy", "outcome", ("k_bb_pct_yoy",), "skill", True, "Year-over-year K-BB% change"),
    FeatureSpec("k_bb_pct_z", "outcome", ("k_bb_pct_z",), "skill", True, "League-year standardized K-BB%"),
    FeatureSpec("k_bb_x_age", "outcome", ("k_bb_x_age",), "skill", True, "Current K-BB% × (age − 27)"),
    FeatureSpec("k_bb_x_role", "outcome", ("k_bb_x_role",), "skill", True, "K-BB% × starter flag"),
    FeatureSpec("babip", "outcome", ("babip",), "skill", True, "BABIP allowed"),
    FeatureSpec("hr_pct", "outcome", ("hr_pct",), "skill", True, "Home-run rate"),
    FeatureSpec("k_pct", "k_bb_skill", ("k_pct",), "skill", True, "Strikeout rate"),
    FeatureSpec("bb_pct", "k_bb_skill", ("bb_pct",), "skill", True, "Walk rate"),
    FeatureSpec("xwoba_against", "contact_suppression", ("xwoba_against",), "skill", True, "Expected wOBA allowed"),
    FeatureSpec("xba", "contact_suppression", ("xba",), "skill", True, "Expected batting average allowed"),
    FeatureSpec("xslg", "contact_suppression", ("xslg",), "skill", True, "Expected slugging allowed"),
    FeatureSpec("z_contact_pct", "contact_suppression", ("z_contact_pct",), "skill", True, "In-zone contact rate allowed"),
    FeatureSpec("gb_pct", "batted_ball", ("gb_pct",), "skill", True, "Ground-ball rate"),
    FeatureSpec("fb_pct", "batted_ball", ("fb_pct",), "skill", True, "Fly-ball rate"),
    FeatureSpec("ev_against", "batted_ball", ("ev_against",), "skill", True, "Average exit velocity allowed"),
    FeatureSpec("barrel_against", "batted_ball", ("barrel_against",), "skill", True, "Barrel rate allowed"),
    FeatureSpec("hard_hit_against", "batted_ball", ("hard_hit_against",), "skill", True, "Hard-hit rate allowed"),
    FeatureSpec("avg_velo", "velocity", ("avg_velo",), "skill", True, "Average fastball velocity (all FB types)"),
    FeatureSpec("ff_velo", "velocity", ("ff_velo",), "skill", True, "Four-seam fastball velocity"),
    FeatureSpec("velo_w2", "velocity", ("velo_w2",), "skill", True, "IP-weighted 2-year fastball velocity"),
    FeatureSpec("breaking_velo", "velocity", ("breaking_velo",), "skill", True, "Average breaking-ball velocity"),
    FeatureSpec("offspeed_velo", "velocity", ("offspeed_velo",), "skill", True, "Average offspeed velocity"),
    FeatureSpec("primary_fb_velo", "velocity", ("primary_fb_velo",), "skill", True, "Primary fastball velocity (FF or SI by usage)"),
    FeatureSpec("avg_ivb", "movement", ("avg_ivb",), "skill", True, "Average induced vertical break"),
    FeatureSpec("avg_hb", "movement", ("avg_hb",), "skill", True, "Average horizontal break"),
    FeatureSpec("avg_spin", "spin", ("avg_spin",), "skill", True, "Average fastball spin rate"),
    FeatureSpec("extension", "release", ("extension",), "skill", True, "Release extension (pitch-type weighted)"),
    FeatureSpec("arm_angle", "release", ("arm_angle",), "skill", True, "Arm angle"),
    FeatureSpec("whiff_rate", "whiff_chase", ("whiff_rate",), "skill", True, "Whiff rate"),
    FeatureSpec("o_swing_pct", "whiff_chase", ("o_swing_pct",), "skill", True, "Chase rate induced"),
    FeatureSpec("csw_rate", "whiff_chase", ("csw_rate",), "skill", True, "Called-strike plus whiff rate"),
    FeatureSpec("whiff_rate_w2", "whiff_chase", ("whiff_rate_w2",), "skill", True, "IP-weighted 2-year whiff rate"),
    FeatureSpec("whiff_fb", "whiff_chase", ("whiff_fb",), "skill", True, "Fastball-family whiff rate"),
    FeatureSpec("whiff_brk", "whiff_chase", ("whiff_brk",), "skill", True, "Breaking-ball whiff rate"),
    FeatureSpec("strike_pct", "command", ("strike_pct",), "skill", True, "Strike percentage (MLB Stats API)"),
    FeatureSpec("fb_usage", "pitch_mix", ("fb_usage",), "skill", True, "Fastball usage"),
    FeatureSpec("brk_usage", "pitch_mix", ("brk_usage",), "skill", True, "Breaking-ball usage"),
    FeatureSpec("off_usage", "pitch_mix", ("off_usage",), "skill", True, "Offspeed usage"),
    FeatureSpec("arsenal_depth", "pitch_mix", ("arsenal_depth",), "skill", True, "Count of pitch groups with ≥50 pitches"),
    FeatureSpec("stuff_plus", "stuff", ("stuff_plus",), "skill", True, "Pitch-quality score: expected-whiff model from velocity, movement, spin, extension, and location, scaled so 100 is average"),
    FeatureSpec("stuff_fb", "stuff", ("stuff_fb",), "skill", True, "Fastball-family Stuff+"),
    FeatureSpec("stuff_brk", "stuff", ("stuff_brk",), "skill", True, "Breaking-ball Stuff+"),
    FeatureSpec("stuff_off", "stuff", ("stuff_off",), "skill", True, "Offspeed Stuff+"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("throws_left", "demographic", ("throws_left",), "demographic", False, "Throws left-handed"),
    FeatureSpec("height_in", "demographic", ("height_in",), "demographic", False, "Height in inches"),
    FeatureSpec("ip", "workload", ("ip",), "demographic", False, "Innings pitched / workload"),
    FeatureSpec("gs_share", "role", ("gs_share",), "demographic", False, "Share of appearances that were starts"),
    FeatureSpec("starter_role", "role", ("starter_role",), "demographic", False, "Starter vs reliever flag"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("lg_k_bb", "environment", ("lg_k_bb",), "environment", False, "League-year K-BB% environment"),
    FeatureSpec("lg_fip", "environment", ("lg_fip",), "environment", False, "League-year FIP environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
    FeatureSpec("k_bb_vs_lhb", "platoon", ("k_bb_vs_lhb",), "skill", True, "K-BB% versus left-handed batters"),
    FeatureSpec("k_bb_vs_rhb", "platoon", ("k_bb_vs_rhb",), "skill", True, "K-BB% versus right-handed batters"),
    FeatureSpec("platoon_kbb_diff", "platoon", ("platoon_kbb_diff",), "skill", True, "K-BB% vs LHB minus vs RHB"),
)

PITCHER_FAMILIES = {
    "outcome": (
        "era", "fip", "fip_lag1", "fip_w2", "fip_w3", "fip_yoy", "fip_z", "fip_minus",
        "whip", "k_bb_pct", "k_bb_pct_lag1", "k_bb_pct_w2",
        "k_bb_pct_w3", "k_bb_pct_yoy", "k_bb_pct_z", "k_bb_x_age", "k_bb_x_role",
        "babip", "hr_pct",
    ),
    "k_bb_skill": ("k_pct", "bb_pct"),
    "contact_suppression": ("xwoba_against", "xba", "xslg", "z_contact_pct"),
    "batted_ball": ("gb_pct", "fb_pct", "ev_against", "barrel_against", "hard_hit_against"),
    "velocity": ("avg_velo", "ff_velo", "velo_w2", "breaking_velo", "offspeed_velo", "primary_fb_velo"),
    "movement": ("avg_ivb", "avg_hb"),
    "spin": ("avg_spin",),
    "release": ("extension", "arm_angle"),
    "whiff_chase": ("whiff_rate", "o_swing_pct", "csw_rate", "whiff_rate_w2", "whiff_fb", "whiff_brk"),
    "command": ("strike_pct",),
    "pitch_mix": ("fb_usage", "brk_usage", "off_usage", "arsenal_depth"),
    "stuff": ("stuff_plus", "stuff_fb", "stuff_brk", "stuff_off"),
    "workload": ("ip",),
    "role": ("gs_share", "starter_role"),
    "demographic": ("age", "throws_left", "height_in"),
    "environment": ("park_factor", "lg_k_bb", "lg_fip", "covid_season"),
    "platoon": ("k_bb_vs_lhb", "k_bb_vs_rhb", "platoon_kbb_diff"),
}

HITTER_BASELINE_WEAK = ("age", "pa", "woba", "park_factor")
HITTER_BASELINE = ("age", "pa", "woba_w2", "park_factor")
PITCHER_BASELINE_WEAK = ("age", "ip", "starter_role", "fip", "park_factor")
PITCHER_BASELINE = ("age", "ip", "starter_role", "fip_w2", "park_factor")
PITCHER_KBB_BASELINE_WEAK = ("age", "ip", "starter_role", "k_bb_pct", "park_factor")
PITCHER_KBB_BASELINE = ("age", "ip", "starter_role", "k_bb_pct_w2", "park_factor")

HITTER_TARGETS = {
    "primary": "y_woba",
    "robustness": "y_wrc_plus",
    "mechanisms": ("y_k_pct", "y_bb_pct", "y_iso"),
}
PITCHER_TARGETS = {
    "primary": "y_fip",
    "sensitivity": ("y_fip_minus", "y_era", "y_whip"),
}

HITTER_HISTORY_COLS = ("woba", "xwoba", "k_pct", "bb_pct", "barrel_pct", "ev")
PITCHER_HISTORY_COLS = ("k_bb_pct", "k_pct", "bb_pct", "avg_velo", "whiff_rate", "fip")

# ---------------------------------------------------------------------------
# Baserunning / defense / WAR catalogs (component studies)
# ---------------------------------------------------------------------------

BASERUNNING_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("br_rv_rate", "history", ("br_rv_rate",), "skill", False, "Current-season baserunning run-value rate"),
    FeatureSpec("br_rv_rate_lag1", "history", ("br_rv_rate_lag1",), "skill", False, "Prior-season baserunning run-value rate"),
    FeatureSpec("br_rv_rate_w2", "history", ("br_rv_rate_w2",), "skill", False, "PA-weighted 2-year baserunning run-value rate"),
    FeatureSpec("br_rv_rate_w3", "history", ("br_rv_rate_w3",), "skill", False, "PA-weighted 3-year baserunning run-value rate"),
    FeatureSpec("br_rv", "history", ("br_rv",), "skill", False, "Total baserunning run value"),
    FeatureSpec("sprint_speed", "speed", ("sprint_speed",), "skill", True, "Statcast sprint speed"),
    FeatureSpec("hp_to_1b", "speed", ("hp_to_1b",), "skill", True, "Home-to-first time"),
    FeatureSpec("sprint_speed_yoy", "speed", ("sprint_speed_yoy",), "skill", True, "Year-over-year sprint speed change"),
    FeatureSpec("sb", "stealing", ("sb",), "skill", True, "Stolen bases"),
    FeatureSpec("cs", "stealing", ("cs",), "skill", True, "Caught stealing"),
    FeatureSpec("sb_pct", "stealing", ("sb_pct",), "skill", True, "Stolen-base success rate"),
    FeatureSpec("sb_rate", "stealing", ("sb_rate",), "skill", True, "Stolen bases per plate appearance"),
    FeatureSpec("sb_attempts", "stealing", ("sb_attempts",), "skill", True, "Stolen-base attempts (SB+CS)"),
    FeatureSpec("attempt_rate", "stealing", ("attempt_rate",), "skill", True, "Steal attempts per time on base"),
    FeatureSpec("steal_rv_rate", "stealing", ("steal_rv_rate",), "skill", True, "Linear-weight steal run-value rate"),
    FeatureSpec("adv_rv_rate", "advancement", ("adv_rv_rate",), "skill", True, "Statcast advancement run-value rate"),
    FeatureSpec("xbt_rate", "advancement", ("xbt_rate",), "skill", True, "Extra-base-taken rate on advancement opportunities"),
    FeatureSpec("first_to_third_rate", "advancement", ("first_to_third_rate",), "skill", True, "First-to-third rate on singles"),
    FeatureSpec("second_to_home_rate", "advancement", ("second_to_home_rate",), "skill", True, "Second-to-home rate on singles"),
    FeatureSpec("outs_on_bases_rate", "advancement", ("outs_on_bases_rate",), "skill", True, "Outs on the bases per opportunity"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("bats_left", "demographic", ("bats_left",), "demographic", False, "Bats left-handed"),
    FeatureSpec("pa", "playing_time", ("pa",), "demographic", False, "Plate appearances"),
    FeatureSpec("tob", "playing_time", ("tob",), "demographic", False, "Times on base (H+BB+HBP−HR)"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
)

BASERUNNING_FAMILIES = {
    "history": ("br_rv_rate", "br_rv_rate_lag1", "br_rv_rate_w2", "br_rv_rate_w3", "br_rv"),
    "speed": ("sprint_speed", "hp_to_1b", "sprint_speed_yoy"),
    "stealing": ("sb", "cs", "sb_pct", "sb_rate", "sb_attempts", "attempt_rate", "steal_rv_rate"),
    "advancement": ("adv_rv_rate", "xbt_rate", "first_to_third_rate", "second_to_home_rate", "outs_on_bases_rate"),
    "demographic": ("age", "bats_left"),
    "playing_time": ("pa", "tob"),
    "environment": ("park_factor", "covid_season"),
}

DEFENSE_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("def_rv_rate", "history", ("def_rv_rate",), "skill", False, "Current-season defensive run-value rate (per 1,000 innings)"),
    FeatureSpec("def_rv_rate_lag1", "history", ("def_rv_rate_lag1",), "skill", False, "Prior-season defensive run-value rate"),
    FeatureSpec("def_rv_rate_w2", "history", ("def_rv_rate_w2",), "skill", False, "Innings-weighted 2-year defensive run-value rate"),
    FeatureSpec("def_rv_rate_w3", "history", ("def_rv_rate_w3",), "skill", False, "Innings-weighted 3-year defensive run-value rate"),
    FeatureSpec("def_rv", "history", ("def_rv",), "skill", False, "Total defensive run value"),
    FeatureSpec("epcaa", "conversion", ("epcaa",), "skill", True, "OAA-like expected play conversion above average (outs)"),
    FeatureSpec("epcaa_rate", "conversion", ("epcaa_rate",), "skill", True, "OAA-like conversion rate per 100 opportunities"),
    FeatureSpec("epcaa_w2", "conversion", ("epcaa_w2",), "skill", True, "Opportunity-weighted 2-year OAA-like value"),
    FeatureSpec("oaa", "conversion", ("oaa",), "skill", True, "Official Statcast OAA (shorter coverage)"),
    FeatureSpec("oaa_rate", "conversion", ("oaa_rate",), "skill", True, "Official Statcast OAA per opportunity"),
    FeatureSpec("sprint_speed", "range", ("sprint_speed",), "skill", True, "Statcast sprint speed"),
    FeatureSpec("errors", "traditional", ("errors",), "skill", True, "Official errors"),
    FeatureSpec("assists", "traditional", ("assists",), "skill", True, "Assists"),
    FeatureSpec("putouts", "traditional", ("putouts",), "skill", True, "Putouts"),
    FeatureSpec("fielding_pct", "traditional", ("fielding_pct",), "skill", False, "Fielding percentage (not the defensive target)"),
    FeatureSpec("double_plays", "traditional", ("double_plays",), "skill", True, "Double plays turned"),
    FeatureSpec("cs_pct_catcher", "catcher", ("cs_pct_catcher",), "skill", True, "Caught-stealing rate as catcher"),
    FeatureSpec("runs_catcher", "catcher", ("runs_catcher",), "skill", True, "Baseball Reference catcher defensive runs"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("def_inn", "workload", ("def_inn",), "demographic", False, "Defensive innings"),
    FeatureSpec("def_opp", "workload", ("def_opp",), "demographic", False, "Tracked defensive opportunities"),
    FeatureSpec("pos_group_if", "position", ("pos_group_if",), "demographic", False, "Primary infield"),
    FeatureSpec("pos_group_of", "position", ("pos_group_of",), "demographic", False, "Primary outfield"),
    FeatureSpec("pos_group_c", "position", ("pos_group_c",), "demographic", False, "Primary catcher"),
    FeatureSpec("is_cf", "position", ("is_cf",), "demographic", False, "Primary center field"),
    FeatureSpec("is_corner_of", "position", ("is_corner_of",), "demographic", False, "Primary corner outfield"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
)

DEFENSE_FAMILIES = {
    "history": ("def_rv_rate", "def_rv_rate_lag1", "def_rv_rate_w2", "def_rv_rate_w3", "def_rv"),
    "conversion": ("epcaa", "epcaa_rate", "epcaa_w2", "oaa", "oaa_rate"),
    "range": ("sprint_speed",),
    "traditional": ("errors", "assists", "putouts", "fielding_pct", "double_plays"),
    "catcher": ("cs_pct_catcher", "runs_catcher"),
    "demographic": ("age",),
    "workload": ("def_inn", "def_opp"),
    "position": ("pos_group_if", "pos_group_of", "pos_group_c", "is_cf", "is_corner_of"),
    "environment": ("park_factor", "covid_season"),
}

WAR_HITTER_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("war_rate", "history", ("war_rate",), "skill", False, "Baseball Reference WAR per 600 PA"),
    FeatureSpec("war_rate_w2", "history", ("war_rate_w2",), "skill", False, "PA-weighted 2-year bWAR rate"),
    FeatureSpec("war", "history", ("war",), "skill", False, "Total Baseball Reference WAR"),
    FeatureSpec("woba_w2", "hitting", ("woba_w2",), "skill", True, "PA-weighted 2-year wOBA"),
    FeatureSpec("xwoba_w2", "hitting", ("xwoba_w2",), "skill", True, "PA-weighted 2-year xwOBA"),
    FeatureSpec("ev", "hitting", ("ev",), "skill", True, "Average exit velocity"),
    FeatureSpec("br_rv_rate_w2", "baserunning", ("br_rv_rate_w2",), "skill", True, "2-year baserunning run-value rate"),
    FeatureSpec("sprint_speed", "baserunning", ("sprint_speed",), "skill", True, "Statcast sprint speed"),
    FeatureSpec("def_rv_rate_w2", "defense", ("def_rv_rate_w2",), "skill", True, "2-year defensive run-value rate"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("pa", "playing_time", ("pa",), "demographic", False, "Plate appearances"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
)

WAR_HITTER_FAMILIES = {
    "history": ("war_rate", "war_rate_w2", "war"),
    "hitting": ("woba_w2", "xwoba_w2", "ev"),
    "baserunning": ("br_rv_rate_w2", "sprint_speed"),
    "defense": ("def_rv_rate_w2",),
    "demographic": ("age",),
    "playing_time": ("pa",),
    "environment": ("park_factor", "covid_season"),
}

WAR_PITCHER_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("war_rate", "history", ("war_rate",), "skill", False, "Baseball Reference pitcher WAR per 200 IP"),
    FeatureSpec("war_rate_w2", "history", ("war_rate_w2",), "skill", False, "IP-weighted 2-year pitcher bWAR rate"),
    FeatureSpec("war", "history", ("war",), "skill", False, "Total Baseball Reference pitcher WAR"),
    FeatureSpec("fip_w2", "pitching", ("fip_w2",), "skill", True, "IP-weighted 2-year FIP"),
    FeatureSpec("k_bb_pct_w2", "pitching", ("k_bb_pct_w2",), "skill", True, "IP-weighted 2-year K-BB%"),
    FeatureSpec("age", "demographic", ("age",), "demographic", False, "Season age"),
    FeatureSpec("ip", "workload", ("ip",), "demographic", False, "Innings pitched"),
    FeatureSpec("starter_role", "role", ("starter_role",), "demographic", False, "Starter vs reliever flag"),
    FeatureSpec("park_factor", "environment", ("park_factor",), "environment", False, "MLB park run environment"),
    FeatureSpec("covid_season", "environment", ("covid_season",), "environment", False, "2020 short-season flag"),
)

WAR_PITCHER_FAMILIES = {
    "history": ("war_rate", "war_rate_w2", "war"),
    "pitching": ("fip_w2", "k_bb_pct_w2"),
    "demographic": ("age",),
    "workload": ("ip",),
    "role": ("starter_role",),
    "environment": ("park_factor", "covid_season"),
}
