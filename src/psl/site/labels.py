"""Public display names and hover copy."""

from __future__ import annotations

import json
import math
from functools import lru_cache

import pandas as pd

from psl.admission.engine import VERDICT_PUBLIC_COPY
from psl.config import ARTIFACTS

# Short public names. Overrides catalog descriptions where the UI needs a headline.
DISPLAY_COMMON: dict[str, str] = {
    "avg": "Batting Average",
    "obp": "On-Base Percentage",
    "slg": "Slugging Percentage",
    "ops": "OPS",
    "woba": "wOBA",
    "woba_lag1": "Prior-Season wOBA",
    "woba_w2": "2-Year wOBA",
    "woba_w3": "3-Year wOBA",
    "woba_yoy": "Year-over-Year wOBA Change",
    "woba_z": "League-Adjusted wOBA",
    "woba_x_age": "wOBA × Age",
    "wrc_plus": "Park-Adjusted Offense Index",
    "babip": "BABIP",
    "xwoba": "xwOBA",
    "xba": "Expected Batting Average",
    "xslg": "Expected Slugging",
    "xwobacon": "xwOBA on Contact",
    "xiso": "Expected Isolated Power",
    "xwoba_w2": "2-Year xwOBA",
    "o_swing_pct": "Chase Rate",
    "z_swing_pct": "In-Zone Swing Rate",
    "swing_pct": "Swing Rate",
    "meatball_swing_pct": "Meatball Swing Rate",
    "edge_pct": "Edge-of-Zone Rate",
    "bb_pct": "Walk Rate",
    "bb_pct_w2": "2-Year Walk Rate",
    "z_contact_pct": "In-Zone Contact Rate",
    "o_contact_pct": "Chase Contact Rate",
    "swstr_pct": "Whiff Rate",
    "k_pct": "K%",
    "k_pct_w2": "2-Year K%",
    "ev": "Exit Velocity",
    "avg_best_speed": "Average Best Speed",
    "hard_hit_pct": "Hard-Hit Rate",
    "barrel_pct": "Barrel Rate",
    "sweet_spot_pct": "Sweet-Spot Rate",
    "la": "Launch Angle",
    "barrel_pct_w2": "2-Year Barrel Rate",
    "ev_w2": "2-Year Exit Velocity",
    "iso": "Isolated Power",
    "gb_pct": "Ground-Ball Rate",
    "fb_pct": "Fly-Ball Rate",
    "ld_pct": "Line-Drive Rate",
    "pull_pct": "Pull Rate",
    "cent_pct": "Center-Field Rate",
    "oppo_pct": "Opposite-Field Rate",
    "sprint_speed": "Sprint Speed",
    "hp_to_1b": "Home-to-First Time",
    "sb_rate": "Stolen-Base Rate",
    "sb_pct": "Stolen-Base Success Rate",
    "ops_vs_lhp": "OPS vs LHP",
    "ops_vs_rhp": "OPS vs RHP",
    "platoon_ops_diff": "OPS Platoon Split",
    "age": "Age",
    "bats_left": "Bats Left",
    "bats_switch": "Switch Hitter",
    "pa": "Plate Appearances",
    "is_catcher": "Catcher",
    "seasons_since_debut": "Seasons Since Debut",
    "park_factor": "Park Factor",
    "lg_woba": "League wOBA Environment",
    "covid_season": "2020 Season Flag",
    "era": "ERA",
    "fip": "FIP",
    "fip_lag1": "Prior-Season FIP",
    "fip_w2": "2-Year FIP",
    "fip_w3": "3-Year FIP",
    "fip_yoy": "Year-over-Year FIP Change",
    "fip_z": "League-Adjusted FIP",
    "fip_minus": "Park-Adjusted FIP",
    "whip": "WHIP",
    "k_bb_pct": "K-BB%",
    "k_bb_pct_lag1": "Prior-Season K-BB%",
    "k_bb_pct_w2": "2-Year K-BB%",
    "k_bb_pct_w3": "3-Year K-BB%",
    "k_bb_pct_yoy": "Year-over-Year K-BB% Change",
    "k_bb_pct_z": "League-Adjusted K-BB%",
    "k_bb_x_age": "K-BB% × Age",
    "k_bb_x_role": "K-BB% × Role",
    "hr_pct": "Home-Run Rate",
    "xwoba_against": "xwOBA Allowed",
    "ev_against": "Exit Velocity Allowed",
    "barrel_against": "Barrel Rate Allowed",
    "hard_hit_against": "Hard-Hit Rate Allowed",
    "avg_velo": "Average Velocity",
    "ff_velo": "Four-Seam Velocity",
    "velo_w2": "2-Year Fastball Velocity",
    "breaking_velo": "Breaking-Ball Velocity",
    "offspeed_velo": "Offspeed Velocity",
    "primary_fb_velo": "Primary Fastball Velocity",
    "avg_ivb": "Induced Vertical Break",
    "avg_hb": "Horizontal Break",
    "avg_spin": "Average Spin Rate",
    "extension": "Release Extension",
    "arm_angle": "Arm Angle",
    "whiff_rate": "Whiff Rate",
    "csw_rate": "Called-Strike-Plus-Whiff Rate",
    "whiff_rate_w2": "2-Year Whiff Rate",
    "whiff_fb": "Fastball Whiff Rate",
    "whiff_brk": "Breaking-Ball Whiff Rate",
    "strike_pct": "Strike Rate",
    "fb_usage": "Fastball Usage",
    "brk_usage": "Breaking-Ball Usage",
    "off_usage": "Offspeed Usage",
    "arsenal_depth": "Arsenal Depth",
    "stuff_plus": "Stuff+",
    "stuff_fb": "Fastball Stuff+",
    "stuff_brk": "Breaking-Ball Stuff+",
    "stuff_off": "Offspeed Stuff+",
    "throws_left": "Throws Left",
    "height_in": "Height",
    "ip": "Innings Pitched",
    "gs_share": "Start Share",
    "starter_role": "Starter vs Reliever",
    "lg_k_bb": "League K-BB% Environment",
    "lg_fip": "League FIP Environment",
    "k_bb_vs_lhb": "K-BB% vs LHB",
    "k_bb_vs_rhb": "K-BB% vs RHB",
    "platoon_kbb_diff": "K-BB% Platoon Split",
    "mlbam_id": "Player ID",
    "br_rv_rate": "Baserunning Run-Value Rate",
    "br_rv_rate_lag1": "Prior-Season Baserunning Rate",
    "br_rv_rate_w2": "2-Year Baserunning Rate",
    "br_rv_rate_w3": "3-Year Baserunning Rate",
    "br_rv": "Baserunning Run Value",
    "sprint_speed_yoy": "Year-over-Year Sprint Speed",
    "sb": "Stolen Bases",
    "cs": "Caught Stealing",
    "sb_attempts": "Steal Attempts",
    "attempt_rate": "Steal Attempt Rate",
    "steal_rv_rate": "Steal Run-Value Rate",
    "adv_rv_rate": "Advancement Run-Value Rate",
    "xbt_rate": "Extra-Base-Taken Rate",
    "first_to_third_rate": "First-to-Third Rate",
    "second_to_home_rate": "Second-to-Home Rate",
    "outs_on_bases_rate": "Outs on Bases Rate",
    "tob": "Times on Base",
    "def_rv_rate": "Defensive Run-Value Rate",
    "def_rv_rate_lag1": "Prior-Season Defensive Rate",
    "def_rv_rate_w2": "2-Year Defensive Rate",
    "def_rv_rate_w3": "3-Year Defensive Rate",
    "def_rv": "Defensive Run Value",
    "epcaa": "Play Conversion Above Average",
    "epcaa_rate": "Play Conversion Rate",
    "epcaa_w2": "2-Year Play Conversion",
    "oaa": "Outs Above Average",
    "oaa_rate": "OAA Rate",
    "errors": "Errors",
    "assists": "Assists",
    "putouts": "Putouts",
    "fielding_pct": "Fielding Percentage",
    "double_plays": "Double Plays",
    "cs_pct_catcher": "Catcher Caught-Stealing Rate",
    "runs_catcher": "Catcher Defensive Runs",
    "def_inn": "Defensive Innings",
    "def_opp": "Defensive Opportunities",
    "pos_group_if": "Infield",
    "pos_group_of": "Outfield",
    "pos_group_c": "Catcher Position",
    "is_cf": "Center Field",
    "is_corner_of": "Corner Outfield",
    "war_rate": "WAR Rate",
    "war_rate_w2": "2-Year WAR Rate",
    "war": "WAR",
}

DISPLAY_TYPED: dict[tuple[str, str], str] = {
    ("pitcher", "z_contact_pct"): "In-Zone Contact Rate",
    ("pitcher", "babip"): "BABIP Allowed",
    ("pitcher", "xba"): "Expected Batting Average Allowed",
    ("pitcher", "xslg"): "Expected Slugging Allowed",
    ("pitcher", "o_swing_pct"): "Chase Rate Induced",
    ("hitter", "ev"): "Exit Velocity",
}

STATUS_DISPLAY = {
    "CONTEXT_ONLY_CANDIDATE": "Context only",
    "DERIVE_AND_TEST": "Derived metric tested",
    "IDENTIFIER": "Identifier",
    "LEAKAGE": "Would leak future information",
    "NOT_BASEBALL_RELEVANT": "Not suitable as an independent player-skill feature",
    "STRUCTURAL_DUPLICATE": "Duplicate information",
    "TEST": "Tested",
    "UNAVAILABLE_RELIABLY": "Insufficient reliable coverage",
    "INSUFFICIENT_COVERAGE": "Insufficient reliable coverage",
}

MODEL_DISPLAY = {
    "persistence": "Previous-Season Performance",
    "baseline": "Baseline Projection",
    "baseline_elasticnet": "Regularized Baseline",
    "admitted_core": "Admitted-Feature Model",
    "admitted_core_elasticnet": "Regularized Admitted-Feature Model",
    "admitted_core_audit": "Admitted-Feature Model",
    "admitted_core_audit_elasticnet": "Regularized Admitted-Feature Model",
    "kitchen_sink_imputed": "All-Feature Model",
    "kitchen_sink_imputed_elasticnet": "Regularized All-Feature Model",
    "core_on_tracking_population": "Core Model on Tracking Population",
    "augmented_on_tracking_population": "Augmented Model on Tracking Population",
}

PUBLIC_MODEL_ORDER = (
    "persistence",
    "baseline",
    "baseline_elasticnet",
    "admitted_core_audit",
    "kitchen_sink_imputed",
)

PLAYER_DISPLAY = {"hitter": "Hitter", "pitcher": "Pitcher"}

TARGET_PHRASE = {
    "y_woba": "next-season wOBA",
    "y_fip": "next-season FIP",
    "y_br_rv_rate": "next-season baserunning run value",
    "y_def_rv_rate": "next-season fielding run value",
    "y_war_rate": "next-season WAR rate",
    "y_fip_minus": "next-season park-adjusted FIP",
}

COMPONENT_PHRASE = {
    "hitting": "Hitting",
    "pitching": "Pitching",
    "baserunning": "Baserunning",
    "defense": "Defense",
    "overall": "Overall value",
}

COMPONENT_TARGET_ORDER = (
    ("hitting", "y_woba"),
    ("pitching", "y_fip"),
    ("baserunning", "y_br_rv_rate"),
    ("defense", "y_def_rv_rate"),
    ("overall", "y_war_rate"),
)


def target_phrase(target) -> str:
    if target is None or (isinstance(target, float) and pd.isna(target)):
        return "this target"
    key = str(target)
    return TARGET_PHRASE.get(key, key.replace("_", " "))


LOWER_IS_BETTER_TARGETS = frozenset({"y_fip", "y_era", "y_whip", "y_fip_minus"})


def _finite_r(value) -> float | None:
    if value is None:
        return None
    try:
        r = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(r) or not math.isfinite(r):
        return None
    return float(r)


def r_band(value) -> str:
    r = _finite_r(value)
    if r is None:
        return "n/a"
    a = abs(r)
    if a < 0.10:
        return "Very weak"
    if a < 0.30:
        return "Weak"
    if a < 0.50:
        return "Moderate"
    if a < 0.70:
        return "Strong"
    return "Very strong"


def future_relationship_short(value) -> str:
    r = _finite_r(value)
    if r is None:
        return "n/a"
    if abs(r) < 0.10:
        return "Very weak"
    sign = "positive" if r > 0 else "negative"
    return f"{r_band(r)} {sign}"


def fmt_signed_r(value, digits: int = 2) -> str:
    r = _finite_r(value)
    if r is None:
        return "n/a"
    return f"{r:+.{digits}f}"


def fmt_pearson_r(value) -> str:
    r = _finite_r(value)
    if r is None:
        return "n/a"
    return f"r = {fmt_signed_r(r)}"


def fmt_dropone(value) -> str:
    r = _finite_r(value)
    if r is None:
        return "n/a"
    return f"{r:+.5f} RMSE when removed"


STUDY_COMPARISON_CSV = {
    "hitting_woba": "model_comparison_hitter.csv",
    "pitching_fip": "model_comparison_pitching_fip.csv",
    "baserunning_rv": "model_comparison_baserunning_rv.csv",
    "defense_rv": "model_comparison_defense_rv.csv",
    "overall_war": "model_comparison_overall_war.csv",
    "pitcher_war": "model_comparison_pitcher_war.csv",
}


@lru_cache(maxsize=16)
def admitted_model_rmse(study_id: str | None) -> float | None:
    """Out-of-sample RMSE of the admitted-feature model for a study."""
    if not study_id:
        return None
    csv_name = STUDY_COMPARISON_CSV.get(str(study_id))
    if csv_name:
        path = ARTIFACTS / csv_name
        if path.exists():
            df = pd.read_csv(path)
            for model in ("admitted_core_audit", "admitted_core"):
                hit = df[df["model"].astype(str).eq(model)]
                if not hit.empty and pd.notna(hit.iloc[0].get("mean_rmse")):
                    return float(hit.iloc[0]["mean_rmse"])
    json_path = ARTIFACTS / f"kitchen_sink_comparison_{study_id}.json"
    if json_path.exists():
        payload = json.loads(json_path.read_text())
        rmse = payload.get("admitted_rmse")
        if rmse is not None:
            return float(rmse)
    return None


def fmt_model_impact(delta, full_rmse, metric_name: str) -> str:
    """Public sentence for drop-one change in prediction error."""
    d = _finite_r(delta)
    rmse = _finite_r(full_rmse)
    name = str(metric_name or "this metric")
    if d is None or rmse is None or rmse <= 0:
        return "Not in the projection model"
    pct = 100.0 * d / rmse
    if abs(pct) < 0.05:
        return f"Prediction error was essentially unchanged without {name}."
    shown = f"{abs(pct):.1f}%"
    if pct > 0:
        return f"Prediction error increased {shown} without {name}."
    return f"Prediction error decreased {shown} without {name}."


def correlation_direction_label(value, target) -> str:
    r = _finite_r(value)
    if r is None:
        return "Not enough paired year-t / next-season observations to report a correlation."
    tgt = target_phrase(target)
    band = r_band(r)
    signed = f"{r:+.2f}"
    if abs(r) < 0.10:
        return (
            f"{band} linear association with {tgt} (Pearson {signed}). "
            "A correlation near zero means little linear relationship."
        )
    if str(target) in LOWER_IS_BETTER_TARGETS:
        if r < 0:
            return (
                f"{band} negative association with {tgt} (Pearson {signed}). "
                f"Higher metric values tend to accompany lower (better) {tgt}."
            )
        return (
            f"{band} positive association with {tgt} (Pearson {signed}). "
            f"Higher metric values tend to accompany higher (worse) {tgt}."
        )
    if r > 0:
        return (
            f"{band} positive linear association with {tgt} (Pearson {signed}). "
            f"Higher metric values tend to accompany higher {tgt}."
        )
    return (
        f"{band} negative linear association with {tgt} (Pearson {signed}). "
        f"Higher metric values tend to accompany lower {tgt}."
    )


def component_phrase(component) -> str:
    if component is None or (isinstance(component, float) and pd.isna(component)):
        return "this component"
    return COMPONENT_PHRASE.get(str(component), str(component))


def target_section_id(component, target) -> str:
    """Passport fragment id. Public UI should not show this string as a label."""
    key = (str(component or ""), str(target or ""))
    return {
        ("hitting", "y_woba"): "target-hitting",
        ("pitching", "y_fip"): "target-pitching",
        ("baserunning", "y_br_rv_rate"): "target-baserunning",
        ("defense", "y_def_rv_rate"): "target-defense",
        ("overall", "y_war_rate"): "target-overall",
    }.get(key, f"target-{key[0] or 'metric'}")


# Public listing only. Admission artifacts still store every tested (component, target).
_CONTEXT_FEATURES = frozenset({
    "age",
    "bats_left",
    "bats_switch",
    "throws_left",
    "height_in",
    "pa",
    "ip",
    "tob",
    "def_inn",
    "def_opp",
    "gs_share",
    "starter_role",
    "is_catcher",
    "pos_group_if",
    "pos_group_of",
    "pos_group_c",
    "is_cf",
    "is_corner_of",
    "park_factor",
    "lg_woba",
    "lg_k_bb",
    "lg_fip",
    "covid_season",
    "seasons_since_debut",
})
_BASERUNNING_SKILL_FEATURES = frozenset({
    "sprint_speed",
    "hp_to_1b",
    "sprint_speed_yoy",
    "sb",
    "cs",
    "sb_pct",
    "sb_rate",
    "sb_attempts",
    "attempt_rate",
    "steal_rv_rate",
    "adv_rv_rate",
    "xbt_rate",
    "first_to_third_rate",
    "second_to_home_rate",
    "outs_on_bases_rate",
    "br_rv",
    "br_rv_rate",
    "br_rv_rate_lag1",
    "br_rv_rate_w2",
    "br_rv_rate_w3",
})
_DEFENSE_SKILL_FEATURES = frozenset({
    "arm_strength",
    "def_rv",
    "def_rv_rate",
    "def_rv_rate_lag1",
    "def_rv_rate_w2",
    "def_rv_rate_w3",
    "epcaa",
    "epcaa_rate",
    "epcaa_w2",
    "oaa",
    "oaa_rate",
    "errors",
    "assists",
    "putouts",
    "fielding_pct",
    "double_plays",
    "cs_pct_catcher",
    "runs_catcher",
})
_OVERALL_SKILL_FEATURES = frozenset({"war", "war_rate", "war_rate_w2"})
_EARNED_JOB_VERDICTS = frozenset({"Projection", "Augmented Projection"})


def metric_home_components(player_type, feature) -> frozenset[str]:
    """Baseball job a metric belongs to for public listing. Not an admission verdict."""
    feat = str(feature)
    if feat in _CONTEXT_FEATURES:
        return frozenset({"hitting", "pitching", "baserunning", "defense", "overall"})
    if feat in _BASERUNNING_SKILL_FEATURES:
        return frozenset({"baserunning"})
    if feat in _DEFENSE_SKILL_FEATURES:
        return frozenset({"defense"})
    if feat in _OVERALL_SKILL_FEATURES:
        return frozenset({"overall"})
    if str(player_type) == "pitcher":
        return frozenset({"pitching"})
    return frozenset({"hitting"})


def metric_primary_component(player_type, feature) -> str:
    """Most natural baseball use for public presentation. Not an admission verdict."""
    homes = metric_home_components(player_type, feature)
    if len(homes) == 1:
        return next(iter(homes))
    if str(player_type) == "pitcher" and "pitching" in homes:
        return "pitching"
    if "hitting" in homes:
        return "hitting"
    return sorted(homes)[0]


def belongs_on_component(player_type, feature, component, verdict) -> bool:
    """Whether to list a metric on a public component surface.

    Context metrics appear wherever they were evaluated. Skill metrics appear on
    their home component, and on any other component where they earned a
    projection job. Diagnostic/Exclude results on unrelated components stay in
    passports and artifacts, not in the hero or component catalogs.
    """
    if str(verdict) in _EARNED_JOB_VERDICTS:
        return True
    return str(component) in metric_home_components(player_type, feature)


def without_kbb_outcome_target(table: pd.DataFrame) -> pd.DataFrame:
    """Drop any leftover K-BB% outcome-target rows from public tables."""
    if table is None or getattr(table, "empty", True) or "target" not in getattr(table, "columns", []):
        return table
    return table[~table["target"].astype(str).eq("y_k_bb_pct")].copy()


def verdict_for_target(row: pd.Series) -> str:
    verdict = str(row.get("verdict") or "")
    tgt = row.get("target")
    if tgt is None or (isinstance(tgt, float) and pd.isna(tgt)) or str(tgt) in {"", "nan", "None"}:
        return verdict
    return f"{verdict} for {target_phrase(tgt)}"

FAMILY_DISPLAY = {
    "outcome": "Outcome",
    "expected": "Expected contact",
    "plate_discipline": "Plate discipline",
    "contact_ability": "Contact ability",
    "contact_quality": "Contact quality",
    "power": "Power",
    "batted_ball": "Batted ball",
    "speed": "Speed",
    "platoon": "Platoon",
    "playing_time": "Playing time",
    "position": "Position",
    "demographic": "Demographic",
    "environment": "Environment",
    "k_bb_skill": "Strikeout and walk mix",
    "contact_suppression": "Contact suppression",
    "velocity": "Velocity",
    "movement": "Movement",
    "spin": "Spin",
    "release": "Release",
    "whiff_chase": "Whiff and chase",
    "command": "Command",
    "pitch_mix": "Pitch mix",
    "stuff": "Stuff",
    "workload": "Workload",
    "role": "Role",
    "history": "Prior results",
    "stealing": "Stealing",
    "advancement": "Advancement",
    "conversion": "Play conversion",
    "range": "Range",
    "traditional": "Traditional fielding",
    "catcher": "Catcher defense",
    "hitting": "Hitting",
    "baserunning": "Baserunning",
    "defense": "Defense",
    "pitching": "Pitching",
}

VERDICT_SYMBOL = {
    "Projection": "circle",
    "Augmented Projection": "diamond",
    "Diagnostic": "square",
    "Context": "triangle-up",
    "Exclude": "x",
    "Insufficient Evidence": "star",
}

MAP_ANNOTATIONS = {
    "hitter": ("woba_w2", "xwoba_w2", "ev", "o_swing_pct", "sprint_speed"),
    "pitcher": ("fip_w2", "k_bb_pct_w3", "k_pct", "avg_velo", "stuff_plus", "ff_velo"),
    "hitting": ("woba_w2", "xwoba_w2", "ev", "o_swing_pct", "sprint_speed"),
    "pitching": ("fip_w2", "k_bb_pct_w3", "k_pct", "avg_velo", "stuff_plus", "ff_velo"),
    "baserunning": ("br_rv_rate_w2", "sprint_speed", "attempt_rate"),
    "defense": ("def_rv_rate_w2", "oaa", "sprint_speed", "errors"),
    "overall": ("war_rate_w2", "ev", "k_bb_pct_w2", "sprint_speed"),
}

_MEANINGFUL = 1e-4


def humanize_token(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    if "_" not in name and name.isupper():
        return name
    parts = str(name).split("_")
    out = []
    for p in parts:
        low = p.lower()
        if low in {"woba", "xwoba", "xwobacon", "ops", "era", "fip", "whip", "babip", "iso"}:
            out.append(p.upper() if low != "xwoba" else "xwOBA")
        elif low == "pct":
            out.append("%")
        elif low in {"k", "bb"}:
            out.append(p.upper())
        elif low == "w2":
            out.append("2-Year")
        elif low == "w3":
            out.append("3-Year")
        else:
            out.append(p.capitalize())
    text = " ".join(out).replace(" %", "%")
    return text


def display_name(feature: str, player_type: str | None = None) -> str:
    if player_type:
        typed = DISPLAY_TYPED.get((player_type, feature))
        if typed:
            return typed
    if feature in DISPLAY_COMMON:
        return DISPLAY_COMMON[feature]
    return humanize_token(feature)


def display_model(model_id: str) -> str:
    return MODEL_DISPLAY.get(model_id, humanize_token(model_id))


def display_status(status: str) -> str:
    return STATUS_DISPLAY.get(status, humanize_token(status))


def display_player(player_type: str) -> str:
    return PLAYER_DISPLAY.get(player_type, player_type.capitalize())


def display_family(family: str) -> str:
    return FAMILY_DISPLAY.get(family, humanize_token(family))


def fmt_rmse_delta(delta) -> str:
    if delta is None or (isinstance(delta, float) and (pd.isna(delta) or math.isnan(delta))):
        return "n/a"
    d = float(delta)
    if abs(d) < _MEANINGFUL:
        return "No meaningful change"
    mag = f"{abs(d):.5f}"
    if d < 0:
        return f"Improved RMSE by {mag}"
    return f"Worsened RMSE by {mag}"


def fmt_coverage(coverage) -> str:
    if coverage is None or (isinstance(coverage, float) and pd.isna(coverage)):
        return "n/a"
    return f"{float(coverage):.0%}"


def fmt_stability(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    return f"{float(value):.2f}"


def fmt_stability_line(row: pd.Series) -> str:
    value = fmt_stability(row.get("reliability_pearson"))
    rank = row.get("stability_rank")
    n = row.get("stability_n")
    if rank is None or n is None:
        return value
    if isinstance(rank, float) and pd.isna(rank):
        return value
    if isinstance(n, float) and pd.isna(n):
        return value
    return f"{value} ({int(rank)} of {int(n)})"


def fmt_corr(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    return f"{float(value):.2f}"


def future_prediction_text(row: pd.Series) -> str:
    feature = str(row.get("feature", ""))
    player_type = str(row.get("player_type", ""))
    verdict = str(row.get("verdict", ""))
    if verdict == "Context":
        if feature == "park_factor":
            return "Used as environmental adjustment"
        return "Used as a context input, not as player skill"
    if verdict == "Insufficient Evidence":
        return "Current evidence inconclusive"
    return fmt_rmse_delta(row.get("oos_rmse_delta"))


def hover_why(row: pd.Series) -> str:
    feature = str(row.get("feature", ""))
    player_type = str(row.get("player_type", ""))
    verdict = str(row.get("verdict", ""))
    target = str(row.get("target") or "")
    special = {
        ("hitter", "xwoba_w2"): "Adds repeatable future information beyond the baseline.",
        ("hitter", "ev"): "Adds repeatable future information beyond the baseline.",
        ("hitter", "woba_w2"): "Multi-year performance history used as a core projection input.",
        ("hitter", "o_swing_pct"): "Useful for describing swing decisions, but not admitted to the broad projection.",
        ("hitter", "park_factor"): "Context, not player skill.",
        ("pitcher", "k_bb_pct_z"): "A league-adjusted representation of K-BB%, not an additional independent skill signal.",
        ("pitcher", "park_factor"): "Context, not player skill.",
    }
    if target == "y_fip":
        special.update(
            {
                ("pitcher", "fip_w2"): "Multi-year FIP history used as a core projection input.",
                ("pitcher", "k_pct"): "Adds next-season FIP information as part of the strikeout/walk mix, not as a third independent K-BB skill.",
                ("pitcher", "k_bb_pct_w3"): "Multi-year K-BB% history that added next-season FIP information beyond 2-year FIP.",
                ("pitcher", "stuff_plus"): "Added next-season FIP information beyond the FIP history baseline.",
                ("pitcher", "extension"): "Added next-season FIP information beyond the FIP history baseline.",
                ("pitcher", "ff_velo"): "Added next-season FIP information beyond the FIP history baseline.",
                ("pitcher", "avg_velo"): "Useful for describing pitcher process, but not admitted to the FIP projection after family tests.",
            }
        )
    if (player_type, feature) in special:
        return special[(player_type, feature)]
    return VERDICT_PUBLIC_COPY.get(verdict, "")


def passport_blurb(row: pd.Series) -> str:
    feature = str(row.get("feature", ""))
    player_type = str(row.get("player_type", ""))
    target = str(row.get("target") or "")
    overrides = {
        ("hitter", "xwoba_w2"): "Consistently improved next-season wOBA prediction across all seven temporal folds.",
        ("hitter", "ev"): "Retained independent future-prediction value after stronger contact-quality information was considered.",
        ("hitter", "woba_w3"): "Multi-year wOBA history that still added incremental information beside the 2-year version.",
        ("hitter", "woba_w2"): "The history-aware performance baseline for next-season wOBA.",
        ("hitter", "o_swing_pct"): "Describes chase decisions but did not add enough independent future-prediction value for next-season wOBA.",
        ("pitcher", "k_bb_pct_z"): "A league-adjusted representation of current-season K-BB%, not an additional independent skill signal.",
        ("pitcher", "fip_w2"): "The history-aware performance baseline for next-season FIP.",
        ("pitcher", "k_bb_pct_w3"): "Multi-year K-BB% history that added next-season FIP information beyond 2-year FIP.",
        ("pitcher", "k_bb_pct"): "K-BB% summarizes strikeout and walk performance and was evaluated for whether it adds information about future FIP.",
        ("pitcher", "k_pct"): "Strikeout rate used with K-BB history; not a third independent K-BB skill.",
    }
    if target == "y_fip":
        overrides.update(
            {
                ("pitcher", "avg_velo"): "Describes velocity but did not add enough independent next-season FIP value after family tests.",
                ("pitcher", "avg_spin"): "Describes spin but did not add enough independent next-season FIP value after family tests.",
                ("pitcher", "whiff_rate"): "Describes whiffs but did not add enough independent next-season FIP value after family tests.",
                ("pitcher", "stuff_plus"): "Added next-season FIP information beyond a strong FIP-history baseline.",
                ("pitcher", "extension"): "Added next-season FIP information beyond a strong FIP-history baseline.",
                ("pitcher", "ff_velo"): "Fastball velocity added next-season FIP information beyond 2-year FIP.",
                ("pitcher", "z_contact_pct"): "In-zone contact allowed added next-season FIP information beyond 2-year FIP.",
                ("pitcher", "k_bb_pct_w2"): "Two-year K-BB% did not earn Projection for next-season FIP after the family test kept the 3-year rate and K%.",
            }
        )
    if feature in {"stuff_plus", "extension"} and player_type == "pitcher" and (player_type, feature) not in overrides:
        cov = row.get("coverage")
        n_folds = row.get("n_folds")
        cov_txt = f"{float(cov):.0%}" if cov is not None and not pd.isna(cov) else "limited"
        fold_txt = "one" if n_folds is None or pd.isna(n_folds) or int(n_folds) == 1 else str(int(n_folds))
        label = "Pitch-quality metric" if feature == "stuff_plus" else "Release metric"
        return (
            f"{label} with {cov_txt} modeling coverage and {fold_txt} temporal "
            f"validation window(s); {verdict_for_target(row)}."
        )
    if (player_type, feature) in overrides:
        return overrides[(player_type, feature)]
    return f"{verdict_for_target(row)}. " + VERDICT_PUBLIC_COPY.get(str(row.get("verdict")), "")


def looks_like_raw_id(text: str) -> bool:
    return "_" in str(text) and str(text).lower() == str(text)


def hover_takeaway(row: pd.Series) -> str:
    feature = str(row.get("feature", ""))
    player_type = str(row.get("player_type", ""))
    verdict = str(row.get("verdict", ""))
    target = str(row.get("target") or "")
    special = {
        ("hitter", "xwoba_w2"): "Adds repeatable future information beyond the baseline.",
        ("hitter", "ev"): "Adds repeatable future information beyond the baseline.",
        ("hitter", "woba_w2"): "Core projection input from recent performance history.",
        ("pitcher", "k_bb_pct_z"): "League-adjusted K-BB%, not a separate skill.",
        ("pitcher", "k_pct"): "Used with K-BB history; not a third independent K-BB signal.",
    }
    if target == "y_fip":
        special.update(
            {
                ("pitcher", "fip_w2"): "Core projection input from recent FIP history.",
                ("pitcher", "stuff_plus"): "Adds future FIP information beyond the FIP-history baseline.",
                ("pitcher", "extension"): "Adds future FIP information beyond the FIP-history baseline.",
            }
        )
    if (player_type, feature) in special:
        return special[(player_type, feature)]
    by_verdict = {
        "Projection": "Core projection input for this target.",
        "Augmented Projection": "Predictive where observed, not a universal core input.",
        "Diagnostic": "Descriptive for this target, not a projection input.",
        "Context": "Context, not player skill.",
        "Exclude": "Not used in this projection.",
        "Insufficient Evidence": "Not enough evidence to decide.",
    }
    return by_verdict.get(verdict, "See passport for the full explanation.")


def map_hover_text(row: pd.Series) -> str:
    name = display_name(row["feature"], row.get("player_type"))
    return (
        f"<b>{name}</b><br>"
        f"Verdict: {verdict_for_target(row)}<br>"
        f"Stability: {fmt_stability_line(row)}<br>"
        f"Future value: {future_prediction_text(row)}<br>"
        f"Coverage: {fmt_coverage(row.get('coverage'))}<br>"
        f"Takeaway: {hover_takeaway(row)}"
    )
