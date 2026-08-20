"""Component studies: a metric's role is defined relative to a target.

Primary key for admission: (player_type, component, target, metric).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from psl.catalog import (
    HITTER_BASELINE,
    HITTER_BASELINE_WEAK,
    HITTER_FAMILIES,
    HITTER_FEATURES,
    PITCHER_BASELINE,
    PITCHER_BASELINE_WEAK,
    PITCHER_FAMILIES,
    PITCHER_FEATURES,
)
from psl.config import DATA_PROCESSED


@dataclass(frozen=True)
class StudySpec:
    study_id: str
    component: str
    player_type: str
    target: str
    target_label: str
    sample_path: Path
    seasons_path: Path
    labeled_path: Path | None
    features: tuple
    families: dict
    baseline: tuple[str, ...]
    baseline_weak: tuple[str, ...]
    persistence_col: str
    secondary_targets: tuple[str, ...]
    output_stem: str
    apply_kbb_demotion: bool = False
    weight_col: str | None = None
    is_primary: bool = True


def _p(name: str) -> Path:
    return DATA_PROCESSED / name


HITTING_WOBA = StudySpec(
    study_id="hitting_woba",
    component="hitting",
    player_type="hitter",
    target="y_woba",
    target_label="next-season wOBA",
    sample_path=_p("hitter_sample_pa150.parquet"),
    seasons_path=_p("hitter_seasons.parquet"),
    labeled_path=_p("hitter_labeled.parquet"),
    features=HITTER_FEATURES,
    families=HITTER_FAMILIES,
    baseline=HITTER_BASELINE,
    baseline_weak=HITTER_BASELINE_WEAK,
    persistence_col="woba",
    secondary_targets=("y_wrc_plus", "y_k_pct", "y_bb_pct", "y_iso"),
    output_stem="admission_hitting_y_woba",
    apply_kbb_demotion=False,
    weight_col="pa",
    is_primary=True,
)

PITCHING_FIP = StudySpec(
    study_id="pitching_fip",
    component="pitching",
    player_type="pitcher",
    target="y_fip",
    target_label="next-season FIP",
    sample_path=_p("pitcher_sample_role_ip.parquet"),
    seasons_path=_p("pitcher_seasons.parquet"),
    labeled_path=_p("pitcher_labeled.parquet"),
    features=PITCHER_FEATURES,
    families=PITCHER_FAMILIES,
    baseline=PITCHER_BASELINE,
    baseline_weak=PITCHER_BASELINE_WEAK,
    persistence_col="fip",
    secondary_targets=("y_fip_minus", "y_era", "y_whip"),
    output_stem="admission_pitching_y_fip",
    apply_kbb_demotion=False,
    weight_col="ip",
    is_primary=True,
)

# Archival only. Not a public or canonical projection target. See docs/archive/kbb_target_study.md.
PITCHING_KBB = StudySpec(
    study_id="pitching_kbb",
    component="pitching",
    player_type="pitcher",
    target="y_k_bb_pct",
    target_label="archived next-season K-BB% (not a public target)",
    sample_path=_p("pitcher_sample_role_ip.parquet"),
    seasons_path=_p("pitcher_seasons.parquet"),
    labeled_path=_p("pitcher_labeled.parquet"),
    features=PITCHER_FEATURES,
    families=PITCHER_FAMILIES,
    baseline=("age", "ip", "starter_role", "k_bb_pct_w2", "park_factor"),
    baseline_weak=("age", "ip", "starter_role", "k_bb_pct", "park_factor"),
    persistence_col="k_bb_pct",
    secondary_targets=("y_fip", "y_era", "y_whip"),
    output_stem="admission_pitching_y_k_bb_pct",
    apply_kbb_demotion=True,
    weight_col="ip",
    is_primary=False,
)

BASERUNNING_RV = StudySpec(
    study_id="baserunning_rv",
    component="baserunning",
    player_type="hitter",
    target="y_br_rv_rate",
    target_label="next-season baserunning run-value rate",
    sample_path=_p("baserunning_sample.parquet"),
    seasons_path=_p("baserunning_seasons.parquet"),
    labeled_path=_p("baserunning_labeled.parquet"),
    features=(),  # filled after catalog import in studies()
    families={},
    baseline=("age", "pa", "br_rv_rate_w2", "park_factor"),
    baseline_weak=("age", "pa", "br_rv_rate", "park_factor"),
    persistence_col="br_rv_rate",
    secondary_targets=("y_br_rv", "y_br_rv_per_600pa"),
    output_stem="admission_baserunning_y_br_rv_rate",
    weight_col="pa",
    is_primary=True,
)

DEFENSE_RV = StudySpec(
    study_id="defense_rv",
    component="defense",
    player_type="hitter",
    target="y_def_rv_rate",
    target_label="next-season defensive run-value rate",
    sample_path=_p("defense_sample.parquet"),
    seasons_path=_p("defense_seasons.parquet"),
    labeled_path=_p("defense_labeled.parquet"),
    features=(),
    families={},
    baseline=("age", "def_inn", "pos_group_if", "pos_group_of", "pos_group_c", "def_rv_rate_w2"),
    baseline_weak=("age", "def_inn", "def_rv_rate"),
    persistence_col="def_rv_rate",
    secondary_targets=("y_def_rv", "y_epcaa_rate", "y_oaa_rate"),
    output_stem="admission_defense_y_def_rv_rate",
    weight_col="def_inn",
    is_primary=True,
)

OVERALL_WAR = StudySpec(
    study_id="overall_war",
    component="overall",
    player_type="hitter",
    target="y_war_rate",
    target_label="next-season Baseball Reference WAR per 600 PA",
    sample_path=_p("war_hitter_sample.parquet"),
    seasons_path=_p("war_hitter_seasons.parquet"),
    labeled_path=_p("war_hitter_labeled.parquet"),
    features=(),
    families={},
    baseline=("age", "pa", "war_rate_w2", "park_factor"),
    baseline_weak=("age", "pa", "war_rate"),
    persistence_col="war_rate",
    secondary_targets=("y_war",),
    output_stem="admission_overall_y_war_rate",
    weight_col="pa",
    is_primary=True,
)

PITCHER_WAR = StudySpec(
    study_id="pitcher_war",
    component="overall",
    player_type="pitcher",
    target="y_war_rate",
    target_label="next-season Baseball Reference pitcher WAR per 200 IP",
    sample_path=_p("war_pitcher_sample.parquet"),
    seasons_path=_p("war_pitcher_seasons.parquet"),
    labeled_path=_p("war_pitcher_labeled.parquet"),
    features=(),
    families={},
    baseline=("age", "ip", "starter_role", "war_rate_w2", "park_factor"),
    baseline_weak=("age", "ip", "starter_role", "war_rate"),
    persistence_col="war_rate",
    secondary_targets=("y_war",),
    output_stem="admission_pitcher_overall_y_war_rate",
    weight_col="ip",
    is_primary=False,
)

CANONICAL_TARGETS = {
    "hitting": "y_woba",
    "pitching": "y_fip",
    "baserunning": "y_br_rv_rate",
    "defense": "y_def_rv_rate",
    "overall": "y_war_rate",
}
PRIMARY_STUDIES = ("hitting_woba", "pitching_fip", "baserunning_rv", "defense_rv", "overall_war")
SECONDARY_STUDIES = ("pitcher_war",)
ARCHIVAL_STUDIES = ("pitching_kbb",)


def studies() -> dict[str, StudySpec]:
    """Late-bind feature catalogs that are defined after this module loads."""
    from psl.catalog import (
        BASERUNNING_FAMILIES,
        BASERUNNING_FEATURES,
        DEFENSE_FAMILIES,
        DEFENSE_FEATURES,
        WAR_HITTER_FAMILIES,
        WAR_HITTER_FEATURES,
        WAR_PITCHER_FAMILIES,
        WAR_PITCHER_FEATURES,
    )

    out = {
        "hitting_woba": HITTING_WOBA,
        "pitching_fip": PITCHING_FIP,
        "pitching_kbb": PITCHING_KBB,
        "baserunning_rv": replace(BASERUNNING_RV, features=BASERUNNING_FEATURES, families=BASERUNNING_FAMILIES),
        "defense_rv": replace(DEFENSE_RV, features=DEFENSE_FEATURES, families=DEFENSE_FAMILIES),
        "overall_war": replace(OVERALL_WAR, features=WAR_HITTER_FEATURES, families=WAR_HITTER_FAMILIES),
        "pitcher_war": replace(PITCHER_WAR, features=WAR_PITCHER_FEATURES, families=WAR_PITCHER_FAMILIES),
    }
    return out
