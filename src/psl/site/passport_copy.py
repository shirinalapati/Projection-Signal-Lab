"""Plain-English passport interpretation. Presentation only; uses canonical artifacts."""

from __future__ import annotations

import math

import pandas as pd

from psl.config import MATERIAL_LIFT_FRAC
from psl.site.labels import (
    LOWER_IS_BETTER_TARGETS,
    admitted_model_rmse,
    component_phrase,
    display_name,
    fmt_signed_r,
    future_relationship_short,
    r_band,
    target_phrase,
    verdict_for_target,
)
from psl.site.metric_glossary import glossary_description


def _finite(value) -> float | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(x) or not math.isfinite(x):
        return None
    return float(x)


def _parse_extra(row: pd.Series) -> dict:
    extra = row.get("extra")
    if isinstance(extra, dict):
        return extra
    if isinstance(extra, str) and extra.strip():
        import json

        try:
            payload = json.loads(extra)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def metric_name(row: pd.Series) -> str:
    return display_name(row.get("feature"), row.get("player_type"))


def forecast_heading(row: pd.Series) -> str:
    comp = str(row.get("component") or "")
    pt = str(row.get("player_type") or "")
    if comp == "overall":
        return "PITCHER WAR FORECAST" if pt == "pitcher" else "POSITION-PLAYER WAR FORECAST"
    return {
        "hitting": "HITTING FORECAST",
        "pitching": "PITCHING FORECAST",
        "baserunning": "BASERUNNING FORECAST",
        "defense": "DEFENSE FORECAST",
    }.get(comp, f"{component_phrase(comp).upper()} FORECAST")


def decision_line(row: pd.Series) -> str:
    verdict = str(row.get("verdict") or "")
    comp = component_phrase(row.get("component")).lower()
    if verdict == "Projection":
        return f"Use this metric in the {comp} projection."
    if verdict == "Augmented Projection":
        return (
            f"Use this metric in the {comp} projection where it is observed, "
            "but coverage is too incomplete for a universal core model."
        )
    if verdict == "Diagnostic":
        return (
            f"Use this to understand a player’s skill profile for {comp}, "
            "but not as a core projection input."
        )
    if verdict == "Context":
        return "Use this to adjust for environment, role, or playing time — not as player skill."
    if verdict == "Insufficient Evidence":
        return "The available evidence is not yet strong enough for a confident projection decision."
    if verdict == "Exclude":
        return f"Do not use this metric for the {comp} projection."
    return verdict_for_target(row)


def relationship_signed_label(value) -> str:
    return future_relationship_short(value)


def independent_signal_label(value) -> str:
    r = _finite(value)
    if r is None:
        return "n/a"
    a = abs(r)
    if a < 0.10:
        return "Very little"
    if a < 0.30:
        return "Weak"
    if a < 0.50:
        return "Moderate"
    if a < 0.70:
        return "Strong"
    return "Very strong"


def independent_signal_phrase(value) -> str:
    r = _finite(value)
    if r is None:
        return "Independent relationship after the baseline could not be measured."
    a = abs(r)
    if a < 0.10:
        return "Very little independent relationship remained after accounting for the baseline model."
    if a < 0.30:
        return "A weak independent relationship remained after accounting for the baseline model."
    if a < 0.50:
        return "A moderate independent relationship remained after accounting for the baseline model."
    if a < 0.70:
        return "A strong independent relationship remained after accounting for the baseline model."
    return "A very strong independent relationship remained after accounting for the baseline model."


def stability_label(value) -> str:
    r = _finite(value)
    if r is None:
        return "n/a"
    a = abs(r)
    if a < 0.10:
        return "Very low"
    if a < 0.30:
        return "Low"
    if a < 0.50:
        return "Moderate"
    if a < 0.70:
        return "Strong"
    return "Very strong"


def stability_sentence(value) -> str:
    label = stability_label(value)
    if label == "n/a":
        return "Year-to-year stability could not be measured."
    if label in {"Very low", "Low"}:
        return (
            f"{label} year-to-year stability — players who ranked highly in one season "
            "often did not remain similarly ranked the next."
        )
    return (
        f"{label} year-to-year stability — players who ranked highly in this metric "
        "generally remained relatively high the following season."
    )


def overlap_label(value) -> str:
    r = _finite(value)
    if r is None:
        return "n/a"
    a = abs(r)
    if a < 0.30:
        return "Low"
    if a < 0.50:
        return "Moderate"
    if a < 0.70:
        return "High"
    return "Very high"


def overlap_sentence(row: pd.Series) -> str:
    corr = _finite(row.get("max_corr_with_baseline"))
    partner = row.get("max_corr_partner")
    partner_name = (
        display_name(partner, row.get("player_type"))
        if partner is not None and not (isinstance(partner, float) and pd.isna(partner))
        else None
    )
    label = overlap_label(corr)
    if label == "n/a":
        return "Overlap with baseline information could not be measured."
    if label == "Low":
        base = "The metric is not strongly duplicating information already contained in the baseline."
    elif label == "Moderate":
        base = "The metric partially overlaps with information already in the baseline."
    else:
        base = "High overlap — much of this metric’s information may already be represented"
        if partner_name:
            base += f" by {partner_name}."
        else:
            base += " by baseline features."
        return base
    if partner_name:
        return f"{base} Most related baseline feature: {partner_name}."
    return base


def relationship_sentence(row: pd.Series) -> str:
    r = _finite(row.get("future_pearson_r"))
    tgt = target_phrase(row.get("target"))
    name = metric_name(row)
    if r is None:
        return f"Not enough paired observations to describe how {name} relates to {tgt}."
    band = r_band(r)
    lower_better = str(row.get("target")) in LOWER_IS_BETTER_TARGETS
    if abs(r) < 0.10:
        return f"{name} had a very weak relationship with {tgt}."
    if lower_better:
        if r < 0:
            return (
                f"Players with higher {name} tended to have lower (better) {tgt}. "
                f"Raw relationship: {band.lower()} negative."
            )
        return (
            f"Players with higher {name} tended to have higher (worse) {tgt}. "
            f"Raw relationship: {band.lower()} positive."
        )
    if r > 0:
        return (
            f"Players with stronger {name} tended to have higher {tgt} the following season. "
            f"Raw relationship: {band.lower()} positive."
        )
    return (
        f"Players with higher {name} tended to have lower {tgt} the following season. "
        f"Raw relationship: {band.lower()} negative."
    )


def folds_counts(row: pd.Series) -> tuple[int | None, int | None]:
    n = row.get("n_folds")
    improved = row.get("folds_improved")
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return None, None
    n_int = int(n)
    if improved is None or (isinstance(improved, float) and pd.isna(improved)):
        return None, n_int
    return int(round(float(improved) * n_int)), n_int


def historical_consistency_label(row: pd.Series) -> str:
    k, n = folds_counts(row)
    if n is None:
        return "n/a"
    if k is None:
        return f"{n} test periods"
    if k == n:
        return f"Helped in all {n} test periods"
    return f"Helped in {k} of {n} test periods"


def historical_consistency_sentence(row: pd.Series) -> str:
    k, n = folds_counts(row)
    if n is None:
        return "Historical out-of-time consistency could not be summarized."
    base = (
        "The model was repeatedly trained on earlier seasons and tested on a later season."
    )
    if k is None:
        return f"{base} This study used {n} future-season tests."
    if k == n:
        return f"{base} This metric improved the forecast every time ({n} of {n})."
    if k == 0:
        return f"{base} This metric did not improve the forecast in any of the {n} tests."
    return f"{base} This metric improved the forecast in {k} of {n} tests."


def coverage_label(row: pd.Series) -> str:
    cov = _finite(row.get("coverage"))
    if cov is None:
        return "n/a"
    return f"{cov:.0%} of eligible player-seasons"


def coverage_sentence(row: pd.Series) -> str:
    cov = _finite(row.get("coverage"))
    if cov is None:
        return "Modeling-sample coverage could not be summarized."
    if cov >= 0.95:
        return (
            f"Available for {cov:.0%} of eligible player-seasons in this study, "
            "so its result is not limited to a small subset of players."
        )
    if cov >= 0.70:
        return (
            f"Available for {cov:.0%} of eligible player-seasons. "
            "Missingness is limited but still worth keeping in mind for universal use."
        )
    return (
        f"Available for {cov:.0%} of eligible player-seasons. "
        "Because the metric is missing for many players/seasons, we have less evidence "
        "that it can support a universal projection."
    )


def forecast_impact_label(row: pd.Series) -> str:
    delta = _finite(row.get("oos_rmse_delta"))
    base = _finite(row.get("baseline_rmse"))
    if delta is None or base is None or base <= 0:
        return "n/a"
    pct = 100.0 * (-delta) / base  # positive pct = error reduced
    if abs(delta) < MATERIAL_LIFT_FRAC * base:
        return "No meaningful improvement"
    if pct > 0:
        return f"Reduced forecast error by {pct:.1f}%"
    return f"Forecast became {abs(pct):.1f}% worse"


def forecast_impact_sentence(row: pd.Series) -> str:
    label = forecast_impact_label(row)
    if label == "n/a":
        return "Incremental forecast impact versus the baseline could not be summarized."
    if label == "No meaningful improvement":
        return "Adding this metric did not produce a meaningful reduction in out-of-time forecast error."
    if label.startswith("Reduced"):
        return f"Adding this metric {label[0].lower() + label[1:]} relative to the baseline model."
    return f"Adding this metric made the out-of-time forecast worse ({label.lower()})."


def peer_field_label(row: pd.Series) -> str:
    """Human label for the peer set this metric is ranked within."""
    comp = str(row.get("component") or "")
    pt = str(row.get("player_type") or "")
    if comp == "overall":
        return "position-player overall-value metrics" if pt == "hitter" else "pitcher overall-value metrics"
    return {
        "hitting": "hitting metrics",
        "pitching": "pitching metrics",
        "baserunning": "baserunning metrics",
        "defense": "defense metrics",
    }.get(comp, f"{component_phrase(comp).lower()} metrics")


def build_forecast_peer_ranks(table: pd.DataFrame) -> dict[tuple[str, str, str, str], dict[str, int | str]]:
    """
    Rank metrics by incremental forecast improvement within each peer set.

    Peer set = player_type × component × target.
    Lower (more negative) oos_rmse_delta ranks better (1 = most improvement).
    """
    if table is None or table.empty:
        return {}
    ranks: dict[tuple[str, str, str, str], dict[str, int | str]] = {}
    keys = ["player_type", "component", "target"]
    for _, peer in table.groupby(keys, sort=False):
        n = int(len(peer))
        rank_series = peer["oos_rmse_delta"].rank(method="min", ascending=True)
        for idx, row in peer.iterrows():
            key = (
                str(row["player_type"]),
                str(row["feature"]),
                str(row["component"]),
                str(row["target"]),
            )
            ranks[key] = {
                "rank": int(rank_series.loc[idx]),
                "n": n,
                "field": peer_field_label(row),
            }
    return ranks


def peer_rank_key(row: pd.Series) -> tuple[str, str, str, str]:
    return (
        str(row.get("player_type") or ""),
        str(row.get("feature") or ""),
        str(row.get("component") or ""),
        str(row.get("target") or ""),
    )


def peer_standing_label(info: dict | None) -> str:
    if not info:
        return "n/a"
    return f"{info['rank']} of {info['n']}"


def peer_standing_sentence(row: pd.Series, info: dict | None) -> str:
    if not info:
        return "Standing among peer metrics could not be summarized."
    field = info.get("field") or peer_field_label(row)
    tgt = target_phrase(row.get("target"))
    return (
        f"Ranked {info['rank']} of {info['n']} {field} tested for {tgt}, "
        "ordered by how much each metric reduced out-of-time forecast error "
        "when added to the baseline (1 = largest improvement)."
    )


def unique_contribution_label(row: pd.Series) -> str:
    drop = _finite(row.get("dropone_oos_rmse"))
    full = admitted_model_rmse(row.get("study_id") or _parse_extra(row).get("study_id"))
    if drop is None or full is None or full <= 0:
        return "Not applicable"
    pct = 100.0 * drop / full
    if abs(pct) < 0.05:
        return "Essentially unchanged without it"
    if pct > 0:
        return f"Removing it increased forecast error by {pct:.1f}%"
    return f"Removing it decreased forecast error by {abs(pct):.1f}%"


def unique_contribution_sentence(row: pd.Series) -> str:
    label = unique_contribution_label(row)
    if label == "Not applicable":
        return (
            "This metric was not selected for the final projection, "
            "so there is no drop-one contribution to measure."
        )
    if "increased" in label:
        return f"Removing this metric made future predictions worse. {label}."
    if "decreased" in label:
        return f"Removing this metric made future predictions slightly better. {label}."
    return "Removing this metric left forecast error essentially unchanged."


def why_this_verdict(row: pd.Series) -> str:
    """Metric- and target-specific explanation from canonical gates/evidence."""
    verdict = str(row.get("verdict") or "")
    name = metric_name(row)
    tgt = target_phrase(row.get("target"))
    rel = relationship_sentence(row)
    partial = independent_signal_phrase(row.get("partial_future_r"))
    folds = historical_consistency_sentence(row)
    cov = coverage_sentence(row)
    impact = forecast_impact_sentence(row)
    overlap = overlap_sentence(row)
    extra = _parse_extra(row)
    in_baseline = bool(extra.get("in_baseline"))

    if verdict == "Context":
        return (
            f"{name} is treated as context for {tgt}: it helps put performance in the correct "
            "environment, role, or playing-time setting rather than measuring player skill itself."
        )
    if verdict == "Insufficient Evidence":
        return (
            f"The available sample or number of future-season tests for {name} on {tgt} "
            "is too limited to make a confident projection decision."
        )
    if verdict == "Projection":
        if in_baseline:
            return (
                f"{rel} {partial} {folds} {cov} "
                f"It is part of the performance-history foundation for the {tgt} projection."
            )
        return (
            f"{rel} {partial} {impact} {folds} {cov} "
            "It earned Projection because it improved predictions on unseen future seasons, "
            "remained useful after existing model information was considered, and had broad enough coverage."
        )
    if verdict == "Augmented Projection":
        return (
            f"{rel} {partial} {impact} {folds} "
            f"{cov} It is predictive where observed, but coverage is too incomplete for a universal core model."
        )
    if verdict == "Diagnostic":
        partial_r = _finite(row.get("partial_future_r"))
        max_corr = _finite(row.get("max_corr_with_baseline"))
        if max_corr is not None and abs(max_corr) >= 0.50:
            return (
                f"{rel} {overlap} "
                f"{name} describes a relevant baseball skill for {tgt}, but a closely related feature "
                "already captures most of the useful forecasting information, so it is kept as a diagnostic."
            )
        if partial_r is not None and abs(partial_r) < 0.10:
            return (
                f"{rel} Once the projection already knew its baseline information, "
                f"{partial.lower()} "
                f"The metric therefore helps explain the player more than it improves the {tgt} forecast."
            )
        return (
            f"{rel} {partial} {impact} {folds} "
            f"It is related to {tgt}, but did not add enough reliable independent information "
            "to earn a place in the projection model."
        )
    if verdict == "Exclude":
        return (
            f"{rel} {partial} {impact} {overlap} "
            f"{name} did not provide enough unique predictive information and was not retained "
            f"as a useful diagnostic measure for {tgt}."
        )
    return f"{rel} {partial} {impact}"


def takeaway(row: pd.Series) -> str:
    verdict = str(row.get("verdict") or "")
    name = metric_name(row)
    tgt = target_phrase(row.get("target"))
    comp = component_phrase(row.get("component")).lower()
    if verdict == "Projection":
        return (
            f"{name} contains useful information about {tgt} "
            "that belongs in the projection."
        )
    if verdict == "Augmented Projection":
        return (
            f"{name} contains useful information about {tgt} where it is observed, "
            "but coverage limits universal use."
        )
    if verdict == "Diagnostic":
        return (
            f"{name} helps explain part of a player’s {comp} profile, "
            f"but it does not provide enough new information to materially change the {tgt} projection."
        )
    if verdict == "Context":
        return f"Treat {name} as context for {tgt}, not as a skill signal."
    if verdict == "Insufficient Evidence":
        return f"More reliable coverage or temporal validation is needed before using {name} for {tgt}."
    if verdict == "Exclude":
        return f"{name} did not earn a lasting role in the {tgt} forecast or diagnostic layer."
    return f"See the evidence below for how {name} relates to {tgt}."


def scatter_how_to_read(row: pd.Series) -> str:
    r = _finite(row.get("future_pearson_r"))
    name = metric_name(row)
    tgt = target_phrase(row.get("target"))
    lower_better = str(row.get("target")) in LOWER_IS_BETTER_TARGETS
    caveat = (
        " This chart shows the raw relationship only; it does not account for other information "
        "already known by the projection model."
    )
    if r is None or abs(r) < 0.10:
        return (
            f"Each dot represents one player-season. There is little visible linear association "
            f"between {name} and {tgt}.{caveat}"
        )
    if lower_better:
        if r < 0:
            trend = (
                f"The downward trend means higher {name} tended to accompany lower (better) {tgt}."
            )
        else:
            trend = (
                f"The upward trend means higher {name} tended to accompany higher (worse) {tgt}."
            )
    else:
        if r > 0:
            trend = (
                f"The upward trend means players with higher {name} tended to produce higher {tgt}."
            )
        else:
            trend = (
                f"The downward trend means players with higher {name} tended to produce lower {tgt}."
            )
    return f"Each dot represents one player-season. {trend}{caveat}"


def raw_vs_unique_blurb(row: pd.Series) -> str:
    raw = relationship_signed_label(row.get("future_pearson_r"))
    after = independent_signal_label(row.get("partial_future_r"))
    if after == "Very little" and raw not in {"n/a", "Very weak"}:
        return (
            f"Raw relationship: {raw}. After baseline: {after}. "
            "This is why a metric can look related in the scatterplot but still receive a Diagnostic "
            "or Exclude verdict — the projection may already know most of that information from stronger variables."
        )
    return (
        f"Raw relationship: {raw}. After baseline: {after}. "
        "Raw relationship is how closely this metric moves with the future target by itself; "
        "after baseline is how much relationship remains once the model already knows its starting information."
    )


def what_it_measures(row: pd.Series, catalog_description: str = "") -> str:
    feat = str(row.get("feature") or "")
    pt = str(row.get("player_type") or "")
    return glossary_description(feat, pt, catalog_description or "n/a")


def evidence_items(row: pd.Series, peer_info: dict | None = None) -> list[dict[str, str]]:
    partner = row.get("max_corr_partner")
    partner_name = (
        display_name(partner, row.get("player_type"))
        if partner is not None and not (isinstance(partner, float) and pd.isna(partner))
        else "n/a"
    )
    items = [
        {
            "label": "Future relationship",
            "value": relationship_signed_label(row.get("future_pearson_r")),
            "note": relationship_sentence(row),
        },
        {
            "label": "Independent signal",
            "value": independent_signal_label(row.get("partial_future_r")),
            "note": independent_signal_phrase(row.get("partial_future_r")),
        },
        {
            "label": "Forecast impact",
            "value": forecast_impact_label(row),
            "note": forecast_impact_sentence(row),
        },
        {
            "label": "Forecast-impact rank",
            "value": peer_standing_label(peer_info),
            "note": peer_standing_sentence(row, peer_info),
        },
        {
            "label": "Historical consistency",
            "value": historical_consistency_label(row),
            "note": historical_consistency_sentence(row),
        },
        {
            "label": "Year-to-year stability",
            "value": stability_label(row.get("reliability_pearson")),
            "note": stability_sentence(row.get("reliability_pearson")),
        },
        {
            "label": "Data availability",
            "value": coverage_label(row),
            "note": coverage_sentence(row),
        },
        {
            "label": "Overlap with baseline",
            "value": overlap_label(row.get("max_corr_with_baseline")),
            "note": overlap_sentence(row),
        },
        {
            "label": "Unique model contribution",
            "value": unique_contribution_label(row),
            "note": unique_contribution_sentence(row),
        },
    ]
    _ = partner_name
    return items


def technical_rows(row: pd.Series) -> list[tuple[str, str]]:
    partner = row.get("max_corr_partner")
    partner_name = (
        display_name(partner, row.get("player_type"))
        if partner is not None and not (isinstance(partner, float) and pd.isna(partner))
        else "n/a"
    )
    drop = row.get("dropone_oos_rmse")
    if drop is None or (isinstance(drop, float) and pd.isna(drop)):
        drop_txt = "n/a (not in the admitted-feature model for this target)"
    else:
        drop_txt = f"{float(drop):+.5f} RMSE when removed"

    def fmt(value, digits=4) -> str:
        x = _finite(value)
        if x is None:
            return "n/a"
        return f"{x:.{digits}f}"

    k, n = folds_counts(row)
    folds_txt = "n/a" if n is None else (f"{k} / {n}" if k is not None else str(n))
    return [
        ("Pearson correlation", fmt_signed_r(row.get("future_pearson_r"))),
        ("Spearman correlation", fmt_signed_r(row.get("future_spearman_rho"))),
        ("Partial correlation after baseline", fmt_signed_r(row.get("partial_future_r"))),
        ("Correlation n", str(row.get("correlation_n") if row.get("correlation_n") is not None else "n/a")),
        ("Baseline RMSE", fmt(row.get("baseline_rmse"), 5)),
        ("Incremental OOS ΔRMSE", f"{fmt(row.get('oos_rmse_delta'), 5)} (negative = improvement vs baseline)"),
        ("Drop-one OOS importance", drop_txt),
        ("Folds improved", folds_txt),
        ("Year-to-year reliability", f"{fmt(row.get('reliability_pearson'), 3)} (n={row.get('reliability_n')})"),
        ("Modeling-sample coverage", coverage_label(row)),
        ("Max correlation with baseline", f"{fmt(row.get('max_corr_with_baseline'), 3)} ({partner_name})"),
        ("Nested family RMSE delta", fmt(row.get("nested_rmse_delta"), 5)),
        ("Bootstrap 95% CI", f"{fmt(row.get('oos_rmse_ci_low'), 5)} to {fmt(row.get('oos_rmse_ci_high'), 5)}"),
        ("Process metric", str(row.get("process"))),
        ("Role", str(row.get("role"))),
    ]
