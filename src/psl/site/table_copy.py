"""Metric-specific public table copy. Presentation only; does not change verdicts."""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from psl.catalog import (
    BASERUNNING_FEATURES,
    DEFENSE_FEATURES,
    HITTER_FEATURES,
    PITCHER_FEATURES,
    WAR_HITTER_FEATURES,
    WAR_PITCHER_FEATURES,
)
from psl.site.labels import (
    LOWER_IS_BETTER_TARGETS,
    belongs_on_component,
    component_phrase,
    display_name,
    future_relationship_short,
    metric_primary_component,
    target_phrase,
)

_JOBS = frozenset({"Projection", "Augmented Projection"})

FAMILY_GROUP = {
    "expected": "Expected performance",
    "contact_quality": "Contact quality",
    "power": "Contact quality",
    "plate_discipline": "Plate discipline",
    "contact_ability": "Plate discipline",
    "batted_ball": "Batted-ball profile",
    "platoon": "Platoon / approach",
    "speed": "Speed / athleticism",
    "outcome": "Results and rates",
    "k_bb_skill": "Strikeout and walk mix",
    "contact_suppression": "Contact allowed",
    "velocity": "Velocity",
    "movement": "Movement and spin",
    "spin": "Movement and spin",
    "whiff_chase": "Whiff and chase",
    "stuff": "Stuff",
    "release": "Release",
    "pitch_mix": "Pitch mix",
    "command": "Command",
    "history": "Prior results",
    "stealing": "Stealing",
    "advancement": "Advancement",
    "conversion": "Play conversion",
    "range": "Speed / athleticism",
    "traditional": "Traditional fielding",
    "catcher": "Catcher defense",
    "hitting": "Hitting inputs",
    "baserunning": "Baserunning inputs",
    "defense": "Defense inputs",
    "pitching": "Pitching inputs",
}

GROUP_ORDER = [
    "Prior results",
    "Expected performance",
    "Contact quality",
    "Plate discipline",
    "Batted-ball profile",
    "Results and rates",
    "Platoon / approach",
    "Speed / athleticism",
    "Strikeout and walk mix",
    "Contact allowed",
    "Velocity",
    "Movement and spin",
    "Whiff and chase",
    "Stuff",
    "Release",
    "Pitch mix",
    "Command",
    "Stealing",
    "Advancement",
    "Play conversion",
    "Traditional fielding",
    "Catcher defense",
    "Hitting inputs",
    "Baserunning inputs",
    "Defense inputs",
    "Pitching inputs",
    "Other",
]

MECHANISM = {
    "xwoba": "expected overall offensive production",
    "xba": "expected batting average",
    "xslg": "expected power",
    "xwobacon": "expected quality of contact when the ball is hit",
    "xiso": "expected extra-base power",
    "o_swing_pct": "chase decisions",
    "z_swing_pct": "in-zone swing decisions",
    "swing_pct": "aggressiveness at the plate",
    "meatball_swing_pct": "swings at the fattest pitches",
    "edge_pct": "pitches on the edge of the zone",
    "bb_pct": "plate discipline via walks",
    "bb_pct_w2": "multi-year walk rate",
    "z_contact_pct": "in-zone contact",
    "o_contact_pct": "out-of-zone contact",
    "swstr_pct": "whiffs",
    "k_pct": "a hitter's contact profile",
    "k_pct_w2": "multi-year strikeout rate",
    "avg_best_speed": "top-end contact quality",
    "hard_hit_pct": "hard-hit contact",
    "barrel_pct": "ideal contact",
    "sweet_spot_pct": "sweet-spot contact",
    "la": "the shape of contact",
    "barrel_pct_w2": "a longer Barrel Rate history",
    "ev_w2": "recent exit-velocity history",
    "iso": "extra-base power",
    "gb_pct": "ground-ball rate",
    "fb_pct": "fly-ball rate",
    "ld_pct": "line-drive rate",
    "pull_pct": "pull rate",
    "cent_pct": "center-field spray",
    "oppo_pct": "opposite-field spray",
    "sprint_speed": "raw sprint speed",
    "hp_to_1b": "home-to-first time",
    "sb_rate": "stolen-base attempts relative to playing time",
    "sb_pct": "stolen-base success",
    "ops_vs_lhp": "performance against left-handed pitching",
    "ops_vs_rhp": "performance against right-handed pitching",
    "platoon_ops_diff": "the OPS platoon split",
    "babip": "batting average on balls in play",
    "avg": "batting average",
    "obp": "on-base percentage",
    "slg": "slugging percentage",
    "ops": "OPS",
    "woba": "single-season wOBA",
    "woba_lag1": "prior-season wOBA",
    "woba_yoy": "year-over-year wOBA change",
    "woba_z": "league-adjusted wOBA",
    "woba_x_age": "the wOBA-by-age interaction",
    "wrc_plus": "park-adjusted offense",
    "era": "ERA",
    "fip": "single-season FIP",
    "fip_lag1": "prior-season FIP",
    "fip_w3": "three-year FIP history",
    "fip_yoy": "year-over-year FIP change",
    "fip_z": "league-adjusted FIP",
    "fip_minus": "park-adjusted FIP",
    "whip": "WHIP",
    "avg_velo": "average velocity",
    "avg_spin": "average spin rate",
    "whiff_rate": "whiff rate",
    "k_bb_pct": "current-season K-BB%",
    "k_bb_pct_w2": "two-year K-BB%",
    "k_bb_pct_w3": "three-year K-BB%",
    "k_bb_pct_z": "league-adjusted K-BB%",
    "k_bb_pct_lag1": "prior-season K-BB%",
    "k_bb_pct_yoy": "year-over-year K-BB% change",
    "k_bb_x_age": "the K-BB% × age interaction",
    "xwoba_against": "expected wOBA allowed",
    "ev_against": "exit velocity allowed",
    "barrel_against": "barrels allowed",
    "hard_hit_against": "hard contact allowed",
    "velo_w2": "multi-year fastball velocity",
    "breaking_velo": "breaking-ball velocity",
    "offspeed_velo": "offspeed velocity",
    "primary_fb_velo": "primary-fastball velocity",
    "avg_ivb": "induced vertical break",
    "avg_hb": "horizontal break",
    "arm_angle": "arm angle",
    "whiff_rate_w2": "multi-year whiff rate",
    "whiff_fb": "fastball whiff rate",
    "whiff_brk": "breaking-ball whiff rate",
    "strike_pct": "strike rate",
    "fb_usage": "fastball usage",
    "brk_usage": "breaking-ball usage",
    "off_usage": "offspeed usage",
    "arsenal_depth": "pitch-mix depth",
    "stuff_fb": "fastball Stuff+",
    "stuff_brk": "breaking-ball Stuff+",
    "stuff_off": "offspeed Stuff+",
    "platoon_kbb_diff": "the K-BB% platoon split",
    "hr_pct": "home-run rate",
    "epcaa": "play-conversion value",
    "epcaa_rate": "play-conversion rate",
    "epcaa_w2": "multi-year play-conversion value",
    "oaa": "Outs Above Average",
    "oaa_rate": "OAA rate",
    "errors": "errors",
    "assists": "assists",
    "putouts": "putouts",
    "double_plays": "double plays",
    "cs_pct_catcher": "catcher caught-stealing rate",
    "runs_catcher": "catcher defensive runs",
    "fielding_pct": "fielding percentage",
    "br_rv_rate": "single-season baserunning rate",
    "br_rv_rate_lag1": "prior-season baserunning rate",
    "def_rv_rate": "single-season fielding rate",
    "def_rv_rate_lag1": "prior-season fielding rate",
    "def_rv": "total fielding run value",
    "war_rate": "single-season WAR rate",
    "war": "total WAR",
    "woba_w2": "recent wOBA history",
    "xwoba_w2": "recent expected-offense history",
    "br_rv_rate_w2": "recent baserunning history",
    "def_rv_rate_w2": "recent fielding history",
    "fip_w2": "recent FIP history",
    "k_bb_pct_w2": "recent K-BB% history",
}

PROJECTION_WHY = {
    ("hitter", "y_woba", "xwoba_w2"): "Consistently improved next-season wOBA prediction across all seven temporal folds.",
    ("hitter", "y_woba", "ev"): "Retained independent future-prediction value after stronger contact-quality information was considered.",
    ("hitter", "y_woba", "woba_w3"): "Multi-year wOBA history that still added incremental information beside the 2-year version.",
    ("hitter", "y_woba", "woba_w2"): "The history-aware performance baseline for next-season wOBA.",
    ("pitcher", "y_fip", "fip_w2"): "The history-aware performance baseline for next-season FIP.",
    ("pitcher", "y_fip", "k_bb_pct_w3"): "Multi-year K-BB% history that added next-season FIP information beyond 2-year FIP.",
    ("pitcher", "y_fip", "k_pct"): "Strikeout rate used with K-BB history; not a third independent K-BB skill.",
    ("pitcher", "y_fip", "stuff_plus"): "Stuff+ added next-season FIP information beyond a strong FIP-history baseline.",
    ("pitcher", "y_fip", "extension"): "Release extension added next-season FIP information beyond a strong FIP-history baseline.",
    ("pitcher", "y_fip", "ff_velo"): "Four-seam velocity added next-season FIP information beyond 2-year FIP.",
    ("pitcher", "y_fip", "z_contact_pct"): "In-zone contact allowed added next-season FIP information beyond 2-year FIP.",
    ("pitcher", "y_fip", "csw_rate"): "Called-strike-plus-whiff rate added next-season FIP information beyond FIP history.",
    ("pitcher", "y_fip", "k_bb_x_role"): "The K-BB% × role interaction added next-season FIP information beyond treating K-BB% and role separately.",
    ("pitcher", "y_fip", "k_bb_vs_rhb"): "K-BB% against right-handed batters added next-season FIP information as a platoon split, not a replacement for overall K-BB%.",
    ("pitcher", "y_fip", "k_bb_vs_lhb"): "K-BB% against left-handed batters added next-season FIP information as a platoon split, not a replacement for overall K-BB%.",
    ("hitter", "y_br_rv_rate", "br_rv_rate_w2"): "The history-aware performance baseline for next-season baserunning run value.",
    ("hitter", "y_br_rv_rate", "br_rv_rate_w3"): "A longer baserunning-rate history still added incremental information beside the 2-year version.",
    ("hitter", "y_br_rv_rate", "sprint_speed"): "Sprint speed added unique next-season baserunning information beyond recent baserunning history.",
    ("hitter", "y_br_rv_rate", "attempt_rate"): "Steal attempt rate added next-season baserunning information beyond recent baserunning history.",
    ("hitter", "y_br_rv_rate", "second_to_home_rate"): "Second-to-home conversion added next-season baserunning information beyond recent history.",
    ("hitter", "y_br_rv_rate", "br_rv"): "Season baserunning run value still added some information beside the rate history.",
    ("hitter", "y_def_rv_rate", "def_rv_rate_w2"): "The history-aware performance baseline for next-season fielding run value.",
    ("hitter", "y_def_rv_rate", "def_rv_rate_w3"): "A longer fielding-rate history still added incremental information beside the 2-year version.",
    ("hitter", "y_war_rate", "war_rate_w2"): "The history-aware performance baseline for next-season WAR rate.",
    ("hitter", "y_war_rate", "ev"): "Exit Velocity added next-season WAR-rate information beyond recent WAR history.",
    ("pitcher", "y_war_rate", "war_rate_w2"): "The history-aware performance baseline for next-season pitcher WAR rate.",
    ("pitcher", "y_war_rate", "k_bb_pct_w2"): "Two-year K-BB% added next-season pitcher WAR-rate information beyond recent WAR history.",
}

# Evidence-backed row copy. Used only when the admission row exists for that target.
DIAGNOSTIC_SPECIAL = {
    ("hitter", "y_woba", "xwoba"): "Useful on its own, but the 2-Year xwOBA version provided a more stable history-aware signal.",
    ("hitter", "y_woba", "xslg"): "Captures expected power, but added little once broader expected-performance and contact-quality measures were known.",
    ("hitter", "y_woba", "xiso"): "Describes expected extra-base power, but did not contribute enough independent information beyond broader expected-hitting metrics.",
    ("hitter", "y_woba", "xwobacon"): "Useful for describing quality of contact when the ball is hit, but did not add enough beyond broader expected-offense measures.",
    ("hitter", "y_woba", "xba"): "Describes expected batting average, but added little once broader expected-offense measures such as 2-Year xwOBA were known.",
    ("hitter", "y_woba", "ev_w2"): "Recent contact quality was informative, but the selected Exit Velocity representation retained more unique forecasting value.",
    ("hitter", "y_woba", "avg_best_speed"): "Describes top-end contact quality, but overlapped with other exit-velocity measures.",
    ("hitter", "y_woba", "hard_hit_pct"): "Closely overlaps with Exit Velocity, leaving little unique information once EV is already known.",
    ("hitter", "y_woba", "barrel_pct"): "Captures ideal contact, but much of its predictive information overlapped with other contact-quality metrics.",
    ("hitter", "y_woba", "barrel_pct_w2"): "Adding a longer Barrel Rate history did not provide enough new information beyond the stronger admitted contact signals.",
    ("hitter", "y_woba", "iso"): "Describes extra-base power, but recent overall offensive history already captured much of its future signal.",
    ("hitter", "y_woba", "bb_pct"): "Describes plate discipline, but added little beyond the model's recent overall offensive history.",
    ("hitter", "y_woba", "bb_pct_w2"): "A longer walk-rate history still added little beyond the model's recent overall offensive history.",
    ("hitter", "y_woba", "babip"): "Provided little stable independent information about next-season overall offense.",
    ("hitter", "y_woba", "o_swing_pct"): "Higher chase tended to accompany worse future offense, but it did not improve the forecast enough beyond recent hitting history.",
    ("hitter", "y_woba", "swing_pct"): "Describes aggressiveness at the plate, but had little unique forecasting value once stronger hitting information was known.",
    ("hitter", "y_woba", "la"): "Describes the shape of contact but had little independent relationship with next-season overall offensive production.",
    ("hitter", "y_woba", "k_pct"): "Useful for describing a hitter's contact profile, but had little independent relationship with next-season overall offense.",
    ("hitter", "y_woba", "k_pct_w2"): "A longer strikeout-rate history still had little independent relationship with next-season overall offense.",
    ("pitcher", "y_fip", "avg_velo"): "Captures average velocity, but Four-Seam Velocity already retained the useful velocity information for next-season FIP.",
    ("pitcher", "y_fip", "primary_fb_velo"): "Primary-fastball velocity overlapped with the admitted Four-Seam Velocity representation.",
    ("pitcher", "y_fip", "velo_w2"): "A longer fastball-velocity history did not add enough beyond the selected Four-Seam Velocity feature.",
    ("pitcher", "y_fip", "offspeed_velo"): "Offspeed velocity overlapped with the admitted Four-Seam Velocity signal for next-season FIP.",
    ("pitcher", "y_fip", "k_bb_pct_w2"): "Two-year K-BB% did not earn Projection after the family test kept the 3-year K-BB% representation.",
    ("pitcher", "y_fip", "k_bb_pct"): "Current-season K-BB% added little once a longer K-BB history was already available.",
    ("pitcher", "y_fip", "k_bb_pct_z"): "A league-adjusted representation of K-BB%, not an additional independent skill once K-BB history was in the model.",
    ("pitcher", "y_fip", "fip_minus"): "Park-adjusted FIP overlapped with recent FIP history plus the model's explicit park adjustment.",
    ("pitcher", "y_fip", "k_bb_x_age"): "The K-BB% × age interaction did not improve next-season FIP enough beyond modeling age and K-BB history separately.",
    ("pitcher", "y_fip", "whiff_rate"): "Whiff rate overlapped with Called-Strike-Plus-Whiff Rate, which retained the family's FIP information.",
    ("pitcher", "y_fip", "whiff_rate_w2"): "A longer whiff-rate history still overlapped with the admitted called-strike-plus-whiff signal.",
    ("pitcher", "y_fip", "whiff_fb"): "Fastball whiffs overlapped with the broader called-strike-plus-whiff measure already in the FIP model.",
    ("pitcher", "y_fip", "whiff_brk"): "Breaking-ball whiffs overlapped with the broader called-strike-plus-whiff measure already in the FIP model.",
    ("pitcher", "y_fip", "stuff_fb"): "Fastball Stuff+ overlapped with overall Stuff+, which retained the family's FIP information.",
    ("pitcher", "y_fip", "xwoba_against"): "Expected wOBA allowed overlapped with in-zone contact allowed, the family's retained FIP signal.",
    ("pitcher", "y_fip", "xba"): "Expected batting average allowed overlapped with in-zone contact allowed.",
    ("pitcher", "y_fip", "xslg"): "Expected slugging allowed overlapped with in-zone contact allowed.",
    ("hitter", "y_br_rv_rate", "hp_to_1b"): "Captures home-to-first time, but Sprint Speed already retained the useful speed information.",
    ("hitter", "y_br_rv_rate", "sb"): "Stolen-base counts overlapped with Steal Attempt Rate, which retained the family's baserunning information.",
    ("hitter", "y_br_rv_rate", "cs"): "Caught-stealing counts overlapped with Steal Attempt Rate rather than adding a separate projection signal.",
    ("hitter", "y_br_rv_rate", "sb_rate"): "Stolen-base attempts relative to playing time overlapped with Steal Attempt Rate.",
    ("hitter", "y_br_rv_rate", "sb_attempts"): "Raw stolen-base attempts overlapped with Steal Attempt Rate.",
    ("hitter", "y_war_rate", "woba_w2"): "Recent wOBA history relates to future WAR, but did not add enough beyond the model's recent WAR-rate history.",
    ("hitter", "y_war_rate", "xwoba_w2"): "Expected-offense history relates to future WAR, but did not add enough beyond recent WAR-rate history.",
    ("hitter", "y_war_rate", "br_rv_rate_w2"): "Baserunning history relates to future WAR, but did not add enough beyond recent WAR-rate history.",
    ("hitter", "y_war_rate", "def_rv_rate_w2"): "Fielding history relates to future WAR, but did not add enough beyond recent WAR-rate history.",
    ("hitter", "y_war_rate", "sprint_speed"): "Sprint speed relates to future WAR, but did not improve the WAR forecast enough; its stronger projection job was in the baserunning study.",
    ("pitcher", "y_war_rate", "fip_w2"): "Added little to the pitcher WAR forecast; its stronger predictive role appeared in the pitching study.",
}

EXCLUDE_SPECIAL = {
    ("hitter", "y_woba", "ops"): "Related to future offense, but its information was already represented by more targeted on-base and power measures.",
    ("hitter", "y_woba", "slg"): "Correlated with future offense, but added little once broader recent-performance and contact-quality information was included.",
    ("hitter", "y_woba", "avg"): "A narrower measure of hitting outcomes added little beyond richer on-base, power, and expected-performance information.",
    ("hitter", "y_woba", "obp"): "Related to future offense, but its information was largely represented by broader offensive-performance measures.",
    ("hitter", "y_woba", "woba"): "A single-season result was redundant once the model already had multi-year wOBA history.",
    ("hitter", "y_woba", "woba_lag1"): "A single prior-season value added little beyond the model's multi-year wOBA history.",
    ("hitter", "y_woba", "woba_yoy"): "Recent change itself was too unstable to improve next-season prediction.",
    ("hitter", "y_woba", "woba_z"): "Added little once recent wOBA history and explicit league-environment controls were already available.",
    ("hitter", "y_woba", "woba_x_age"): "The interaction did not improve the forecast enough beyond modeling age and recent performance separately.",
    ("hitter", "y_woba", "wrc_plus"): "Much of its useful information overlapped with recent performance plus the model's explicit park and league adjustments.",
    ("pitcher", "y_fip", "era"): "ERA is a results measure whose information was already represented by FIP history and the K-BB mix.",
    ("pitcher", "y_fip", "whip"): "WHIP added little once FIP history and strikeout/walk information were included.",
    ("pitcher", "y_fip", "fip"): "A single-season result was redundant once the model already had multi-year FIP history.",
    ("pitcher", "y_fip", "fip_lag1"): "A single prior-season value added little beyond the model's multi-year FIP history.",
    ("pitcher", "y_fip", "fip_w3"): "Three-year FIP added little beyond the 2-year FIP already in the model.",
    ("pitcher", "y_fip", "fip_yoy"): "Recent FIP change itself was too unstable to improve next-season prediction.",
    ("pitcher", "y_fip", "fip_z"): "Added little once recent FIP history and explicit league-environment controls were already available.",
    ("hitter", "y_br_rv_rate", "br_rv_rate"): "A single-season rate was redundant once the model already had multi-year baserunning-rate history.",
    ("hitter", "y_br_rv_rate", "br_rv_rate_lag1"): "A single prior-season rate added little beyond the model's multi-year baserunning history.",
    ("hitter", "y_def_rv_rate", "def_rv_rate"): "A single-season rate was redundant once the model already had multi-year fielding-rate history.",
    ("hitter", "y_def_rv_rate", "def_rv_rate_lag1"): "A single prior-season rate added little beyond the model's multi-year fielding history.",
    ("hitter", "y_def_rv_rate", "def_rv"): "Total fielding runs overlapped with the fielding-rate history already in the model.",
    ("hitter", "y_def_rv_rate", "fielding_pct"): "Fielding percentage had little stable relationship with next-season fielding run value.",
    ("hitter", "y_war_rate", "war_rate"): "A single-season WAR rate was redundant once the model already had multi-year WAR-rate history.",
    ("hitter", "y_war_rate", "war"): "Total WAR overlapped with the WAR-rate history already in the model.",
    ("pitcher", "y_war_rate", "war_rate"): "A single-season pitcher WAR rate was redundant once the model already had multi-year WAR-rate history.",
    ("pitcher", "y_war_rate", "war"): "Total pitcher WAR overlapped with the WAR-rate history already in the model.",
}


def _specs() -> dict[str, object]:
    out = {}
    for bundle in (
        HITTER_FEATURES,
        PITCHER_FEATURES,
        BASERUNNING_FEATURES,
        DEFENSE_FEATURES,
        WAR_HITTER_FEATURES,
        WAR_PITCHER_FEATURES,
    ):
        for spec in bundle:
            out.setdefault(spec.name, spec)
    return out


SPECS = _specs()


def _parse_extra(row: pd.Series) -> dict:
    val = row.get("extra")
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _truthy(val) -> bool:
    if val is None:
        return False
    if isinstance(val, float) and pd.isna(val):
        return False
    return bool(val)


def _finite(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _name(feature, player_type) -> str:
    return display_name(feature, player_type)


def _mech(feature, player_type) -> str:
    feat = str(feature)
    if feat in MECHANISM:
        return MECHANISM[feat]
    spec = SPECS.get(feat)
    if spec is not None:
        desc = str(spec.description).strip().rstrip(".")
        if desc:
            return desc[0].lower() + desc[1:] if len(desc) > 1 else desc.lower()
    return _name(feat, player_type).lower()


def _in_baseline(row: pd.Series) -> bool:
    extra = _parse_extra(row)
    if extra.get("in_baseline"):
        return True
    feat = str(row.get("feature") or "")
    used = extra.get("baseline_used") or []
    return feat in {str(x) for x in used}


def _same_study(all_rows: pd.DataFrame | None, row: pd.Series) -> pd.DataFrame:
    if all_rows is None or getattr(all_rows, "empty", True):
        return pd.DataFrame([row])
    mask = (
        all_rows["player_type"].astype(str).eq(str(row.get("player_type")))
        & all_rows["component"].astype(str).eq(str(row.get("component")))
        & all_rows["target"].astype(str).eq(str(row.get("target")))
    )
    return all_rows.loc[mask].copy()


def _admitted_in_family(peers: pd.DataFrame, family: str) -> list[str]:
    if peers.empty or "family" not in peers.columns:
        return []
    hit = peers[peers["family"].astype(str).eq(str(family)) & peers["verdict"].astype(str).isin(_JOBS)]
    if hit.empty:
        return []
    if "family_representative" in hit.columns:
        reps = hit[hit["family_representative"].map(_truthy)]
        if not reps.empty:
            return [str(f) for f in reps["feature"].tolist()]
    return [str(f) for f in hit["feature"].tolist()]


def _history_phrase(row: pd.Series) -> str:
    tgt = str(row.get("target") or "")
    return {
        "y_woba": "recent offensive history",
        "y_fip": "recent FIP history",
        "y_br_rv_rate": "recent baserunning history",
        "y_def_rv_rate": "recent fielding history",
        "y_war_rate": "recent WAR-rate history",
    }.get(tgt, "recent performance history")


def _relevant_comparisons(feat: str, family: str, admitted: list[str]) -> list[str]:
    if not admitted:
        return []
    stem = feat
    for suf in ("_w2", "_w3", "_lag1", "_z", "_yoy", "_x_age", "_x_role"):
        if feat.endswith(suf):
            stem = feat[: -len(suf)]
            break
    if f"{feat}_w2" in admitted:
        return [f"{feat}_w2"]
    if f"{stem}_w3" in admitted and feat.endswith("_w2"):
        return [f"{stem}_w3"]
    if f"{stem}_w2" in admitted and feat == stem:
        return [f"{stem}_w2"]
    family_pref = {
        "contact_quality": ["ev"],
        "expected": ["xwoba_w2"],
        "velocity": ["ff_velo"],
        "whiff_chase": ["csw_rate"],
        "stuff": ["stuff_plus"],
        "contact_suppression": ["z_contact_pct"],
        "speed": ["sprint_speed"],
        "range": ["sprint_speed"],
        "stealing": ["attempt_rate"],
        "advancement": ["second_to_home_rate"],
        "conversion": ["oaa"],
        "hitting": ["ev"],
        "baserunning": ["sprint_speed"],
        "defense": ["def_rv_rate_w2"],
        "pitching": ["k_bb_pct_w2", "fip_w2"],
    }
    for pref in family_pref.get(family, []):
        if pref in admitted:
            return [pref]
    same = [a for a in admitted if a == stem or a.startswith(stem + "_")]
    if same:
        return same
    if "k_bb" in feat:
        kbb = [a for a in admitted if "k_bb" in a]
        if kbb:
            return kbb
    if family in {"outcome", "history"}:
        hist = [a for a in admitted if a.endswith("_w2") or a.endswith("_w3")]
        if hist:
            return hist[:2]
    return admitted[:2]


def _join_names(features: list[str], player_type) -> str:
    names = [_name(f, player_type) for f in features]
    if not names:
        return "the admitted features"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def context_adjusts_for(row: pd.Series) -> str:
    feat = str(row.get("feature") or "")
    tgt = str(row.get("target") or "")
    if feat == "park_factor":
        if tgt == "y_woba":
            return "Home run environment"
        if tgt == "y_fip":
            return "Park run environment"
        if tgt == "y_br_rv_rate":
            return "Park advancement environment"
        if tgt == "y_def_rv_rate":
            return "Park fielding environment"
        return "Park run environment"
    if feat == "pa":
        if tgt == "y_br_rv_rate":
            return "Playing-time opportunities"
        if tgt == "y_war_rate":
            return "Playing time / sample size"
        return "Playing time / sample size"
    if feat == "bats_left" and tgt == "y_br_rv_rate":
        return "Batter handedness"
    lookup = {
        "age": "Aging",
        "pa": "Playing time / sample size",
        "ip": "Workload / sample size",
        "tob": "Times on base",
        "def_inn": "Defensive playing time",
        "def_opp": "Tracked fielding opportunities",
        "seasons_since_debut": "Career stage",
        "is_catcher": "Position",
        "pos_group_if": "Position (infield)",
        "pos_group_of": "Position (outfield)",
        "pos_group_c": "Position (catcher)",
        "is_cf": "Position (center field)",
        "is_corner_of": "Position (corner outfield)",
        "covid_season": "Shortened-season environment",
        "bats_switch": "Batting handedness",
        "bats_left": "Batting handedness",
        "throws_left": "Pitching handedness",
        "height_in": "Physical size",
        "lg_woba": "League scoring environment",
        "lg_fip": "League pitching environment",
        "lg_k_bb": "League strikeout/walk environment",
        "starter_role": "Starter vs reliever role",
        "gs_share": "Share of appearances that were starts",
    }
    return lookup.get(feat, "Context / environment")


def context_why_matters(row: pd.Series) -> str:
    feat = str(row.get("feature") or "")
    tgt = str(row.get("target") or "")
    phrase = target_phrase(tgt)
    if feat == "age":
        if tgt == "y_woba":
            return (
                "Players' offensive skills change with age, so the model should distinguish "
                "expected aging from changes in underlying performance."
            )
        if tgt == "y_fip":
            return (
                "Pitchers' skills change with age, so the model should distinguish expected aging "
                "from changes in underlying performance."
            )
        if tgt == "y_br_rv_rate":
            return (
                "Baserunning skills change with age, so the model should distinguish expected aging "
                "from changes in underlying speed or instincts."
            )
        if tgt == "y_def_rv_rate":
            return (
                "Fielding skills change with age, so the model should distinguish expected aging "
                "from changes in underlying defense."
            )
        if str(row.get("player_type")) == "pitcher":
            return (
                "A pitcher's overall value changes with age, so the model should distinguish "
                "expected aging from changes in underlying performance."
            )
        return (
            "A player's overall value changes with age, so the model should distinguish "
            "expected aging from changes in underlying performance."
        )
    if feat == "pa":
        if tgt == "y_woba":
            return "A 600-PA season provides more evidence about a hitter than a small-sample season."
        if tgt == "y_br_rv_rate":
            return "Plate appearances set how many baserunning opportunities a season contains."
        if tgt == "y_war_rate":
            return "Playing time tells the model how much evidence a WAR season contains."
        return "A full-season sample provides more evidence than a small-sample season."
    if feat == "park_factor":
        if tgt == "y_woba":
            return "Some parks systematically inflate or suppress offensive results."
        if tgt == "y_fip":
            return "Some parks systematically change run scoring and the pitching environment."
        if tgt == "y_br_rv_rate":
            return "Park geometry can change extra-base and advancement opportunities."
        if tgt == "y_def_rv_rate":
            return "Parks differ in how they shape fielding chances."
        if str(row.get("player_type")) == "pitcher":
            return "Parks systematically change the run environment around pitcher WAR."
        return "Parks systematically change the run environment around position-player WAR."
    if feat == "covid_season":
        if tgt == "y_war_rate" and str(row.get("player_type")) == "pitcher":
            return (
                "The 2020 season had an unusual schedule and sample size that should not be treated "
                "like a normal full season when forecasting next-season pitcher WAR rate."
            )
        return (
            f"The 2020 season had an unusual schedule and sample size that should not be treated "
            f"like a normal full season when forecasting {phrase}."
        )
    if feat == "bats_left":
        if tgt == "y_br_rv_rate":
            return "Batter handedness is a matchup setting for leads and pickoffs, not a skill grade."
        if tgt == "y_woba":
            return "Platoon and matchup environments differ by hitter handedness."
        return "Hitter handedness is a matchup setting, not a skill grade."
    if feat == "ip":
        if tgt == "y_war_rate":
            return "Innings pitched measure how much evidence a pitcher WAR season contains and how the role is used."
        return "Innings pitched measure how much evidence a pitcher's season contains and how the role is used."
    if feat == "starter_role":
        if tgt == "y_war_rate":
            return "Starter vs reliever role shapes pitcher WAR through workload and batter mix, not as a skill grade."
        return "Starters and relievers face different batter mixes, pitch counts, and expected workloads."
    lookup = {
        "tob": "Times on base set the opportunity count for stolen bases and advancement.",
        "def_inn": "Fielding value should be interpreted in light of how many innings were actually played.",
        "def_opp": "Tracked chances tell the model how much fielding evidence a season contains.",
        "seasons_since_debut": "Players at different career stages may have different expected development or decline patterns.",
        "is_catcher": "Catcher workload and offensive expectations differ from those of other position players.",
        "pos_group_if": "Infielders face a different mix of chances than outfielders or catchers.",
        "pos_group_of": "Outfielders face a different mix of chances than infielders or catchers.",
        "pos_group_c": "Catcher defense is a different job from infield or outfield defense.",
        "is_cf": "Center field has a different range and chance profile than corner outfield.",
        "is_corner_of": "Corner outfield has a different range and chance profile than center field.",
        "bats_switch": "Switch hitters experience different matchup environments than single-side hitters.",
        "throws_left": "Platoon and matchup environments differ by pitcher handedness.",
        "height_in": "Release geometry and matchup notes can differ with pitcher size; this is not a skill grade.",
        "lg_woba": "League-wide offense changes over time, so the same raw performance can mean something different in different seasons.",
        "lg_fip": "League-wide pitching environments change over time, so the same FIP can mean something different in different seasons.",
        "lg_k_bb": "League strikeout and walk environments change over time.",
        "gs_share": "How often a pitcher starts games is a role description, not a skill grade.",
    }
    if feat in lookup:
        return lookup[feat]
    return f"Used to adjust the {phrase} setting rather than as a measure of player skill."


def projection_role(row: pd.Series, peers: pd.DataFrame | None) -> str:
    if _in_baseline(row):
        return "Performance-history baseline"
    study = _same_study(peers, row)
    proj = study[study["verdict"].astype(str).isin(_JOBS)].copy()
    scored = []
    for _, other in proj.iterrows():
        if _in_baseline(other):
            continue
        scored.append((str(other["feature"]), _finite(other.get("dropone_oos_rmse")) or -999.0))
    scored.sort(key=lambda item: item[1], reverse=True)
    feat = str(row.get("feature"))
    names = [name for name, _ in scored]
    if feat in names:
        idx = names.index(feat)
        if idx == 0:
            return "Strong unique addition"
        if idx == 1:
            return "Useful additional signal"
        return "Smaller unique addition"
    drop = _finite(row.get("dropone_oos_rmse"))
    if drop is not None and drop > 0.0002:
        return "Useful additional signal"
    return "Smaller unique addition"


def projection_why(row: pd.Series, peers: pd.DataFrame | None = None) -> str:
    key = (str(row.get("player_type")), str(row.get("target")), str(row.get("feature")))
    if key in PROJECTION_WHY:
        return PROJECTION_WHY[key]
    tgt = target_phrase(row.get("target"))
    name = _name(row.get("feature"), row.get("player_type"))
    if _in_baseline(row):
        return f"The history-aware performance baseline for {tgt}."
    if str(row.get("verdict")) == "Augmented Projection":
        return f"{name} added {tgt} information where it was observed, but coverage is too incomplete for a universal core input."
    return f"{name} added repeatable {tgt} information beyond {_history_phrase(row)}."


def _cross_target_why(row: pd.Series, all_rows: pd.DataFrame | None) -> str | None:
    feat = str(row.get("feature") or "")
    pt = str(row.get("player_type") or "")
    comp = str(row.get("component") or "")
    home = metric_primary_component(pt, feat)
    if home == comp:
        return None
    earned = False
    if all_rows is not None and not all_rows.empty:
        jobs = all_rows[
            all_rows["player_type"].astype(str).eq(pt)
            & all_rows["feature"].astype(str).eq(feat)
            & all_rows["verdict"].astype(str).isin(_JOBS)
            & all_rows["component"].astype(str).ne(comp)
        ]
        earned = not jobs.empty
    tgt = target_phrase(row.get("target"))
    home_txt = component_phrase(home).lower()
    if earned:
        return (
            f"Added little to the {tgt} forecast; its stronger predictive role appeared in the {home_txt} study."
        )
    return f"Added little to the {tgt} forecast; its natural baseball role is {home_txt}."


def _family_demoted_why(row: pd.Series, admitted: list[str], pt: str, family: str) -> str:
    feat = str(row.get("feature") or "")
    name = _name(feat, pt)
    mech = _mech(feat, pt)
    cmp_feats = _relevant_comparisons(feat, family, admitted)
    admitted_txt = _join_names(cmp_feats or admitted, pt)
    if feat.endswith("_w2") or feat.endswith("_w3"):
        short = name.replace("2-Year ", "").replace("3-Year ", "")
        return f"Adding a longer {short} history did not provide enough new information beyond {admitted_txt}."
    if f"{feat}_w2" in admitted:
        return f"Useful on its own, but {_name(feat + '_w2', pt)} provided a more stable history-aware signal."
    return f"Captures {mech}, but much of its forecasting information was already represented by {admitted_txt}."


def diagnostic_why(row: pd.Series, all_rows: pd.DataFrame | None = None) -> str:
    pt = str(row.get("player_type") or "")
    feat = str(row.get("feature") or "")
    tgt = target_phrase(row.get("target"))
    key = (pt, str(row.get("target")), feat)
    if key in DIAGNOSTIC_SPECIAL:
        return DIAGNOSTIC_SPECIAL[key]
    name = _name(feat, pt)
    mech = _mech(feat, pt)
    peers = _same_study(all_rows, row)
    family = str(row.get("family") or "")
    admitted = _admitted_in_family(peers, family)
    rationale = str(row.get("rationale") or "")
    r = _finite(row.get("future_pearson_r"))
    rel = _finite(row.get("reliability_pearson"))
    signs = row.get("coef_sign_changes")
    n_signs = int(signs) if signs is not None and not (isinstance(signs, float) and pd.isna(signs)) else 0
    partner = row.get("max_corr_partner")
    partner_name = (
        _name(partner, pt) if partner is not None and not (isinstance(partner, float) and pd.isna(partner)) else None
    )
    corr = _finite(row.get("max_corr_with_baseline"))

    family_demoted = _truthy(row.get("family_redundant")) or "Family representative test" in rationale
    if family_demoted and admitted:
        return _family_demoted_why(row, admitted, pt, family)
    if admitted and family in {"expected", "contact_quality", "velocity", "whiff_chase", "stuff"}:
        return _family_demoted_why(row, admitted, pt, family)

    if n_signs >= 2:
        return (
            f"{name}'s relationship with {tgt} varied across historical test periods, "
            "making it less reliable as a projection input."
        )
    if rel is not None and rel < 0.25:
        return f"{name} was too unstable from year to year to improve the {tgt} forecast reliably."

    if r is not None and abs(r) < 0.10:
        return f"Describes {mech} but had little independent relationship with {tgt}."

    if corr is not None and corr > 0.75 and partner_name:
        return f"Related to {tgt}, but its information overlapped with {partner_name} already in the model."

    cross = _cross_target_why(row, all_rows)
    if cross and (r is None or abs(r) < 0.20):
        return cross

    hist = _history_phrase(row)
    if r is not None and r < -0.10 and str(row.get("target")) not in LOWER_IS_BETTER_TARGETS:
        return (
            f"Higher {name.lower()} tended to accompany worse future offense, but it did not improve "
            f"the {tgt} forecast enough beyond {hist}."
        )
    if r is not None and abs(r) >= 0.10:
        return (
            f"Describes {mech}, but did not add enough unique information to improve the {tgt} forecast "
            f"beyond {hist}."
        )
    return f"Describes {mech}, but did not add enough unique information to improve the {tgt} forecast."


def exclude_why(row: pd.Series, all_rows: pd.DataFrame | None = None) -> str:
    pt = str(row.get("player_type") or "")
    feat = str(row.get("feature") or "")
    key = (pt, str(row.get("target")), feat)
    if key in EXCLUDE_SPECIAL:
        return EXCLUDE_SPECIAL[key]
    tgt = target_phrase(row.get("target"))
    name = _name(feat, pt)
    mech = _mech(feat, pt)
    peers = _same_study(all_rows, row)
    family = str(row.get("family") or "")
    admitted = _admitted_in_family(peers, family)
    cmp_feats = _relevant_comparisons(feat, family, admitted)
    admitted_txt = _join_names(cmp_feats or admitted, pt) if admitted else ""
    r = _finite(row.get("future_pearson_r"))
    rel = _finite(row.get("reliability_pearson"))
    partner = row.get("max_corr_partner")
    partner_name = (
        _name(partner, pt) if partner is not None and not (isinstance(partner, float) and pd.isna(partner)) else None
    )
    corr = _finite(row.get("max_corr_with_baseline"))

    if feat.endswith("_yoy") or "yoy" in feat:
        label = name.replace("Year-over-Year ", "").replace(" Change", "")
        return f"Recent change in {label} was too unstable to improve {tgt}."
    if rel is not None and rel < 0:
        return f"{name} reversed from year to year and did not improve {tgt}."
    if feat.endswith("_w3") and (f"{feat[:-3]}_w2" in admitted or (corr is not None and corr > 0.90)):
        twin = _name(feat[:-3] + "_w2", pt) if f"{feat[:-3]}_w2" in admitted else partner_name or "the shorter history already in the model"
        return f"The longer history added little beyond {twin} already in the model."
    if "x_age" in feat or feat.endswith("_x_age"):
        return "The interaction did not improve the forecast enough beyond modeling age and recent performance separately."
    if feat.endswith("_z") and admitted_txt:
        return (
            f"Added little once {admitted_txt} and explicit league-environment controls were already available."
        )
    twin_w2 = f"{feat}_w2"
    if twin_w2 in admitted or feat + "_w2" in admitted:
        return f"A single-season result was redundant once the model already had multi-year {admitted_txt} history."
    if feat.endswith("_lag1") and admitted_txt:
        return f"A single prior-season value added little beyond the model's {admitted_txt}."
    if corr is not None and corr > 0.90 and partner_name:
        return f"Largely duplicated {partner_name} and did not improve the forecast enough beyond that information."
    if admitted_txt and corr is not None and corr > 0.70:
        return f"Related to {tgt}, but its information was already represented by {admitted_txt}."
    if partner_name and corr is not None and corr > 0.70:
        return (
            f"Correlated with {tgt}, but added little once {partner_name} and related performance information were included."
        )
    if r is not None and abs(r) < 0.10:
        return f"{name} had little stable relationship with {tgt} and no unique forecasting value."
    if admitted_txt:
        return f"Related to {tgt}, but its information was already represented by {admitted_txt}."
    return f"Describes {mech}, but did not provide enough unique information to improve the {tgt} forecast."


def insufficient_why(row: pd.Series) -> str:
    cov = _finite(row.get("coverage"))
    name = _name(row.get("feature"), row.get("player_type"))
    tgt = target_phrase(row.get("target"))
    if cov is not None and cov < 0.70:
        return f"{name} did not have enough complete seasons to make a confident {tgt} admission decision."
    return f"Current coverage or temporal evidence was not strong enough to decide how {name} should be used for {tgt}."


def table_why(row: pd.Series, all_rows: pd.DataFrame | None = None) -> str:
    verdict = str(row.get("verdict") or "")
    if verdict in _JOBS:
        return projection_why(row, all_rows)
    if verdict == "Diagnostic":
        return diagnostic_why(row, all_rows)
    if verdict == "Exclude":
        return exclude_why(row, all_rows)
    if verdict == "Context":
        return context_why_matters(row)
    if verdict == "Insufficient Evidence":
        return insufficient_why(row)
    return f"See the metric passport for the {target_phrase(row.get('target'))} record."


def diagnostic_group(row: pd.Series) -> str:
    fam = str(row.get("family") or "")
    return FAMILY_GROUP.get(fam, "Other")


def relationship_label(row: pd.Series) -> str:
    stored = row.get("future_relationship_label")
    if isinstance(stored, str) and stored.strip() and stored not in {"nan", "None"}:
        return stored
    return future_relationship_short(row.get("future_pearson_r"))


def audit_why_texts(texts: list[str]) -> dict:
    n = len(texts)
    if n == 0:
        return {"n": 0, "identical_share": 0.0, "empty": 0, "most_common": None, "most_common_n": 0}
    counts = Counter(texts)
    dupes = sum(v for v in counts.values() if v > 1)
    common, cn = counts.most_common(1)[0]
    return {
        "n": n,
        "identical_share": dupes / n,
        "empty": sum(1 for t in texts if not str(t).strip()),
        "most_common": common,
        "most_common_n": cn,
        "unique": len(counts),
    }


def collect_public_rows(table: pd.DataFrame) -> pd.DataFrame:
    """Rows that appear in component tables after the public listing filter."""
    keep = []
    for _, row in table.iterrows():
        if belongs_on_component(row.player_type, row.feature, row.component, row.verdict):
            keep.append(True)
        else:
            keep.append(False)
    return table.loc[keep].copy()


def audit_table_copy(table: pd.DataFrame) -> dict[str, dict]:
    public = collect_public_rows(table)
    out = {}
    for verdict, getter in (
        ("Diagnostic", lambda r: diagnostic_why(r, table)),
        ("Context", context_why_matters),
        ("Exclude", lambda r: exclude_why(r, table)),
    ):
        texts = []
        for _, row in public[public.verdict.eq(verdict)].iterrows():
            texts.append(getter(row))
        out[verdict] = audit_why_texts(texts)
    return out


GENERIC_BOILERPLATE = (
    "This metric helps describe how a player succeeds or struggles, but did not add enough independent future-prediction value to the broad model.",
    "Use to adjust or display environment, role, or playing time — not as player skill.",
    "The metric did not provide enough unique predictive or diagnostic value in this study.",
    "Not in the projection model",
)
