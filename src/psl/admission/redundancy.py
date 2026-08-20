"""Deterministic / structural relationships among candidate metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from psl.data.columns import coerce_numeric


@dataclass(frozen=True)
class ExactRelation:
    player_type: str
    derived: str
    components: tuple[str, ...]
    formula: str
    notes: str = ""


EXACT_RELATIONS: tuple[ExactRelation, ...] = (
    ExactRelation("hitter", "ops", ("obp", "slg"), "OPS = OBP + SLG", "Alternative outcome representation, not a third source."),
    ExactRelation("hitter", "iso", ("slg", "avg"), "ISO ≈ SLG − AVG", "Power remainder of slugging."),
    ExactRelation("hitter", "wrc_plus", ("woba", "lg_woba", "park_factor"), "park/league-adjusted wOBA index", "Not official FanGraphs wRC+."),
    ExactRelation("hitter", "woba_w2", ("woba", "woba_lag1"), "PA-weighted mean of t and t−1", "History representation of wOBA."),
    ExactRelation("hitter", "woba_w3", ("woba", "woba_lag1"), "PA-weighted mean of t..t−2", "History representation of wOBA."),
    ExactRelation("hitter", "woba_yoy", ("woba", "woba_lag1"), "wOBA_t − wOBA_{t−1}", "Change representation."),
    ExactRelation("hitter", "woba_x_age", ("woba", "age"), "wOBA × (age − 27)", "Aging interaction."),
    ExactRelation("hitter", "contact_pct", ("z_contact_pct",), "aliased to in-zone contact in an earlier panel build", "Do not treat as independent."),
    ExactRelation("hitter", "gb_pct", ("fb_pct", "ld_pct"), "GB% + FB% + LD% ≈ 1 on BIP", "Compositional batted-ball shares."),
    ExactRelation("hitter", "pull_pct", ("cent_pct", "oppo_pct"), "Pull + Cent + Oppo ≈ 1", "Compositional spray shares."),
    ExactRelation("hitter", "platoon_ops_diff", ("ops_vs_lhp", "ops_vs_rhp"), "OPS vs LHP − OPS vs RHP", "Difference of the two split rates."),
    ExactRelation("hitter", "sb_rate", ("sb", "pa"), "SB / PA", "Counting-stat rate."),
    ExactRelation("pitcher", "k_bb_pct", ("k_pct", "bb_pct"), "K-BB% = K% − BB%", "Not three independent skill sources."),
    ExactRelation("pitcher", "k_bb_pct_w2", ("k_bb_pct", "k_bb_pct_lag1"), "IP-weighted mean of t and t−1", "History representation of K-BB%."),
    ExactRelation("pitcher", "k_bb_pct_w3", ("k_bb_pct", "k_bb_pct_lag1"), "IP-weighted mean of t..t−2", "History representation."),
    ExactRelation("pitcher", "k_bb_pct_yoy", ("k_bb_pct", "k_bb_pct_lag1"), "K-BB%_t − K-BB%_{t−1}", "Change representation."),
    ExactRelation("pitcher", "k_bb_x_age", ("k_bb_pct", "age"), "K-BB% × (age − 27)", "Aging interaction."),
    ExactRelation("pitcher", "k_bb_x_role", ("k_bb_pct", "starter_role"), "K-BB% × starter flag", "Role interaction."),
    ExactRelation("pitcher", "swstr_pct", ("whiff_rate",), "aliased to Savant whiff% in the panel", "Not FanGraphs SwStr% (whiffs per pitch)."),
    ExactRelation("pitcher", "fbv", ("avg_velo",), "same Savant fastball velocity column", "Do not count twice."),
    ExactRelation("pitcher", "contact_pct", ("z_contact_pct",), "aliased to in-zone contact", "Do not treat as independent."),
    ExactRelation("pitcher", "whip", ("hits", "baseOnBalls", "ip"), "WHIP = (H + BB) / IP", "Outcome estimator from counting stats."),
    ExactRelation("pitcher", "k9", ("k_pct",), "K/9 is K% with a different denominator", "Same strikeout skill."),
    ExactRelation("pitcher", "bb9", ("bb_pct",), "BB/9 is BB% with a different denominator", "Same walk skill."),
    ExactRelation("pitcher", "platoon_kbb_diff", ("k_bb_vs_lhb", "k_bb_vs_rhb"), "K-BB% vs LHB − vs RHB", "Difference of split rates."),
    ExactRelation("pitcher", "fb_usage", ("brk_usage", "off_usage"), "FB% + BRK% + OFF% ≈ 1 (plus cutter)", "Compositional pitch mix."),
)


def flag_exact_relations(sample: pd.DataFrame, player_type: str, atol: float = 0.015) -> pd.DataFrame:
    rows = []
    for rel in EXACT_RELATIONS:
        if rel.player_type != player_type:
            continue
        present = rel.derived in sample.columns and all(c in sample.columns for c in rel.components)
        median_abs = None
        holds = None
        n = 0
        if present and rel.derived == "ops" and {"obp", "slg"} <= set(rel.components):
            a = coerce_numeric(sample["ops"])
            b = coerce_numeric(sample["obp"]) + coerce_numeric(sample["slg"])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        elif present and rel.derived == "iso" and {"slg", "avg"} <= set(rel.components):
            a = coerce_numeric(sample["iso"])
            b = coerce_numeric(sample["slg"]) - coerce_numeric(sample["avg"])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        elif present and rel.derived == "k_bb_pct":
            a = coerce_numeric(sample["k_bb_pct"])
            b = coerce_numeric(sample["k_pct"]) - coerce_numeric(sample["bb_pct"])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        elif present and rel.derived == "platoon_ops_diff":
            a = coerce_numeric(sample["platoon_ops_diff"])
            b = coerce_numeric(sample["ops_vs_lhp"]) - coerce_numeric(sample["ops_vs_rhp"])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        elif present and rel.derived == "platoon_kbb_diff":
            a = coerce_numeric(sample["platoon_kbb_diff"])
            b = coerce_numeric(sample["k_bb_vs_lhb"]) - coerce_numeric(sample["k_bb_vs_rhb"])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        elif present and len(rel.components) == 1:
            a = coerce_numeric(sample[rel.derived])
            b = coerce_numeric(sample[rel.components[0]])
            mask = a.notna() & b.notna()
            n = int(mask.sum())
            if n:
                median_abs = float((a[mask] - b[mask]).abs().median())
                holds = median_abs <= atol
        rows.append(
            {
                "player_type": rel.player_type,
                "derived": rel.derived,
                "components": "+".join(rel.components),
                "formula": rel.formula,
                "notes": rel.notes,
                "columns_present": present,
                "n_checked": n,
                "median_abs_error": median_abs,
                "holds_on_panel": holds,
            }
        )
    return pd.DataFrame(rows)
