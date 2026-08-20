"""Run hitter and pitcher admission studies and write canonical tables."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from psl.admission.engine import (
    AdmissionResult,
    admit_feature,
    coverage_profile,
    decide_verdict,
    incremental_oos,
)
from psl.admission.redundancy import flag_exact_relations
from psl.catalog import (
    HITTER_BASELINE,
    HITTER_BASELINE_WEAK,
    HITTER_FAMILIES,
    HITTER_FEATURES,
    HITTER_TARGETS,
    PITCHER_BASELINE,
    PITCHER_BASELINE_WEAK,
    PITCHER_FAMILIES,
    PITCHER_FEATURES,
    PITCHER_TARGETS,
)
from psl.components import ARCHIVAL_STUDIES, StudySpec, studies
from psl.config import ARTIFACTS, DATA_PROCESSED, HITTER_PA_SENSITIVITY, MATERIAL_LIFT_FRAC
from psl.data.assemble import filter_hitter_sample
from psl.models.baselines import (
    bootstrap_delta,
    evaluate_features,
    expanding_folds,
    fit_predict,
    mae,
    persistence_predict,
    rmse,
)

# Kitchen-sink comparison uses the audited admitted cores (not the post-demotion
# Projection set). Hitters 7 vs 56; pitchers 11 vs 57.
KITCHEN_ADMITTED_HITTER = (
    "age",
    "pa",
    "woba_w2",
    "park_factor",
    "xwoba_w2",
    "ev",
    "woba_w3",
)
KITCHEN_ADMITTED_PITCHER = (
    "age",
    "ip",
    "starter_role",
    "k_bb_pct_w2",
    "park_factor",
    "k_bb_pct_z",
    "k_pct",
    "z_contact_pct",
    "avg_spin",
    "avg_velo",
    "whiff_rate",
)
PITCHER_KBB_CONTROL_DEMOTIONS = ("z_contact_pct", "avg_spin", "avg_velo", "whiff_rate")
JSON_OBJECT_COLS = (
    "coverage_by_season",
    "coverage_by_pa_tier",
    "coverage_by_role",
    "fold_rmse_deltas",
    "coef_path",
    "subgroup",
    "extra",
    "correlation_folds",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].apply(lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list)) else x)
    return out


def _specs(player_type: str):
    return HITTER_FEATURES if player_type == "hitter" else PITCHER_FEATURES


def _families(player_type: str):
    return HITTER_FAMILIES if player_type == "hitter" else PITCHER_FAMILIES


def _baselines_for_study(spec: StudySpec, sample: pd.DataFrame) -> tuple[list[str], list[str]]:
    weak, strong = list(spec.baseline_weak), list(spec.baseline)
    if any(c not in sample.columns or sample[c].notna().mean() < 0.5 for c in strong):
        return weak, weak
    return weak, strong


def _baselines(player_type: str, sample: pd.DataFrame) -> tuple[list[str], list[str]]:
    if player_type == "hitter":
        weak, strong = list(HITTER_BASELINE_WEAK), list(HITTER_BASELINE)
    else:
        weak, strong = list(PITCHER_BASELINE_WEAK), list(PITCHER_BASELINE)
    if any(c not in sample.columns or sample[c].notna().mean() < 0.5 for c in strong):
        return weak, weak
    return weak, strong


def _eval_row(name: str, ev: dict, n_features: int, features: list[str], extra: dict | None = None) -> dict | None:
    if not ev.get("ok"):
        return None
    row = {
        "model": name,
        "mean_rmse": ev["mean_rmse"],
        "mean_mae": ev["mean_mae"],
        "n_features": n_features,
        "features": ",".join(features),
    }
    if extra:
        row.update(extra)
    return row


def _baseline_audit(player_type: str, sample: pd.DataFrame, weak: list[str], strong: list[str], target: str, current: str | None = None) -> dict:
    current = current or ("woba" if player_type == "hitter" else "fip")
    rows = []
    for name, feats in [("weak_current_season", weak), ("strong_with_history", strong)]:
        ev = evaluate_features(sample, feats, target, model="ridge")
        rec = _eval_row(name, ev, len(feats), feats)
        if rec:
            rows.append(rec)
    persist_rmse, persist_mae = [], []
    for train_idx, test_idx, year in expanding_folds(sample):
        test = sample.iloc[test_idx]
        p = persistence_predict(sample.iloc[train_idx], test, current, target)
        persist_rmse.append(rmse(p["y"], p["pred"], p["w"]))
        persist_mae.append(mae(p["y"], p["pred"], p["w"]))
    if persist_rmse:
        rows.append({"model": "persistence", "mean_rmse": float(np.mean(persist_rmse)), "mean_mae": float(np.mean(persist_mae)), "n_features": 1, "features": current})
    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / f"baseline_audit_{player_type}.csv", index=False)
    df.to_parquet(ARTIFACTS / f"baseline_audit_{player_type}.parquet", index=False)
    payload = {"player_type": player_type, "weak": weak, "strong": strong, "rows": rows}
    (ARTIFACTS / f"baseline_audit_{player_type}.json").write_text(json.dumps(payload, indent=2, default=str))
    return payload


def _family_tests(player_type: str, sample: pd.DataFrame, baseline: list[str], target: str, families: dict, stem: str | None = None) -> pd.DataFrame:
    rows = []
    for fam, feats in families.items():
        present = [f for f in feats if f in sample.columns and sample[f].notna().mean() >= 0.05]
        if not present:
            continue
        print(f"  family {player_type} {fam}...")
        pop = sample.dropna(subset=present)
        if len(pop) < 80:
            continue
        base = evaluate_features(pop, baseline, target)
        fam_ev = evaluate_features(pop, list(dict.fromkeys([*baseline, *present])), target)
        if base.get("ok") and fam_ev.get("ok"):
            rows.append(
                {
                    "player_type": player_type,
                    "family": fam,
                    "mode": "family_vs_baseline",
                    "dropped": "",
                    "features": ",".join(present),
                    "baseline_rmse": base["mean_rmse"],
                    "model_rmse": fam_ev["mean_rmse"],
                    "rmse_delta": fam_ev["mean_rmse"] - base["mean_rmse"],
                    "n": int(len(pop)),
                }
            )
        for feat in present:
            others = [f for f in present if f != feat]
            if not others:
                continue
            full = evaluate_features(pop, list(dict.fromkeys([*baseline, *present])), target)
            loo = evaluate_features(pop, list(dict.fromkeys([*baseline, *others])), target)
            if full.get("ok") and loo.get("ok"):
                rows.append(
                    {
                        "player_type": player_type,
                        "family": fam,
                        "mode": "family_minus_one",
                        "dropped": feat,
                        "features": ",".join(others),
                        "baseline_rmse": loo["mean_rmse"],
                        "model_rmse": full["mean_rmse"],
                        "rmse_delta": full["mean_rmse"] - loo["mean_rmse"],
                        "n": int(len(pop)),
                    }
                )
    fam_df = pd.DataFrame(rows)
    name = stem or player_type
    fam_df.to_parquet(ARTIFACTS / f"family_ablation_{name}.parquet", index=False)
    fam_df.to_csv(ARTIFACTS / f"family_ablation_{name}.csv", index=False)
    return fam_df


def _greedy_family_representatives(
    table: pd.DataFrame,
    sample: pd.DataFrame,
    baseline: list[str],
    target: str,
    families: dict,
) -> pd.DataFrame:
    """Keep the best family member, then add others only if they still lift OOS."""
    out = table.copy()
    out["family_representative"] = False
    out["family_redundant"] = False
    demote_idx = []
    keep_log = []
    material = None
    for fam, feats in families.items():
        cands = out[(out.family == fam) & (out.verdict.isin(["Projection", "Augmented Projection"])) & (~out.feature.isin(baseline))].copy()
        if cands.empty:
            continue
        cands = cands.sort_values("oos_rmse_delta", na_position="last")
        kept: list[str] = []
        for _, row in cands.iterrows():
            feat = row["feature"]
            if feat not in sample.columns:
                continue
            if not kept:
                kept.append(feat)
                keep_log.append({"family": fam, "feature": feat, "action": "keep_first", "rmse_delta": row["oos_rmse_delta"]})
                continue
            inc = incremental_oos(sample, list(dict.fromkeys([*baseline, *kept])), feat, target, do_bootstrap=False)
            br = inc.get("baseline_rmse") or row.get("baseline_rmse") or 0.04
            thresh = MATERIAL_LIFT_FRAC * br
            delta = inc.get("rmse_delta")
            useful = bool(inc.get("ok")) and delta is not None and delta < -thresh
            keep_log.append({"family": fam, "feature": feat, "action": "keep" if useful else "demote", "rmse_delta": delta})
            if useful:
                kept.append(feat)
            else:
                demote_idx.append((row.name, fam))
        for feat in kept:
            out.loc[out.feature == feat, "family_representative"] = True
    for idx, fam in demote_idx:
        if out.loc[idx, "verdict"] in {"Projection", "Augmented Projection"}:
            out.loc[idx, "verdict"] = "Diagnostic"
            out.loc[idx, "family_redundant"] = True
            prev = str(out.loc[idx, "rationale"] or "")
            out.loc[idx, "rationale"] = (
                "Family representative test: another member of this family already captures the incremental OOS value. "
                + prev
            )
    pd.DataFrame(keep_log).to_csv(ARTIFACTS / f"family_representatives_{out['player_type'].iloc[0] if len(out) else 'na'}.csv", index=False)
    return out


def _parse_json_cell(x):
    if isinstance(x, str) and x[:1] in "[{":
        try:
            return json.loads(x)
        except json.JSONDecodeError:
            return x
    return x


def parse_admission_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in JSON_OBJECT_COLS:
        if c in out.columns:
            out[c] = out[c].apply(_parse_json_cell)
    return out


def result_from_row(row: pd.Series) -> AdmissionResult:
    extra = row.get("extra") or {}
    if not isinstance(extra, dict):
        extra = _parse_json_cell(extra) or {}
    extra = dict(extra or {})

    def _cell(name, default=None):
        if name not in row.index:
            return default
        val = row[name]
        if name in JSON_OBJECT_COLS:
            val = _parse_json_cell(val)
        try:
            if val is None or (not isinstance(val, (dict, list)) and pd.isna(val)):
                return default
        except (ValueError, TypeError):
            pass
        if name in {"n_folds", "coef_sign_changes", "reliability_n", "same_pop_n", "full_pop_n"}:
            try:
                return int(val)
            except (TypeError, ValueError):
                return default
        if name in {"process", "missing_systematic"}:
            return bool(val)
        return val

    return AdmissionResult(
        player_type=str(row["player_type"]),
        feature=str(row["feature"]),
        family=_cell("family", ""),
        target=_cell("target", ""),
        role=_cell("role", "skill"),
        process=bool(_cell("process", False)),
        component=str(_cell("component", "") or ""),
        oos_rmse_delta=_cell("oos_rmse_delta"),
        oos_mae_delta=_cell("oos_mae_delta"),
        oos_rmse_ci_low=_cell("oos_rmse_ci_low"),
        oos_rmse_ci_high=_cell("oos_rmse_ci_high"),
        folds_improved=_cell("folds_improved"),
        n_folds=_cell("n_folds"),
        fold_rmse_deltas=_cell("fold_rmse_deltas"),
        reliability_pearson=_cell("reliability_pearson"),
        reliability_spearman=_cell("reliability_spearman"),
        reliability_n=_cell("reliability_n"),
        coef_mean=_cell("coef_mean"),
        coef_sign_changes=_cell("coef_sign_changes"),
        coef_path=_cell("coef_path"),
        max_corr_with_baseline=_cell("max_corr_with_baseline"),
        max_corr_partner=_cell("max_corr_partner"),
        vif=_cell("vif"),
        nested_rmse_delta=_cell("nested_rmse_delta"),
        coverage=_cell("coverage"),
        coverage_by_season=_cell("coverage_by_season"),
        coverage_by_pa_tier=_cell("coverage_by_pa_tier"),
        coverage_by_role=_cell("coverage_by_role"),
        missing_systematic=_cell("missing_systematic"),
        same_pop_n=_cell("same_pop_n"),
        full_pop_n=_cell("full_pop_n"),
        subgroup=_cell("subgroup"),
        in_sample_rmse_delta=_cell("in_sample_rmse_delta"),
        baseline_rmse=_cell("baseline_rmse"),
        extra=extra,
    )


def refresh_modeling_coverage(
    table: pd.DataFrame,
    sample: pd.DataFrame,
    seasons: pd.DataFrame,
    player_type: str,
) -> pd.DataFrame:
    """Coverage used for admission is the modeling sample, not the unfiltered seasons table."""
    out = table.copy()
    for idx, row in out.iterrows():
        feat = row["feature"]
        if feat not in sample.columns:
            continue
        cov = coverage_profile(sample, feat, player_type)
        out.at[idx, "coverage"] = cov["coverage"]
        out.at[idx, "coverage_by_season"] = cov["by_season"]
        out.at[idx, "coverage_by_pa_tier"] = cov["by_tier"]
        out.at[idx, "coverage_by_role"] = cov.get("by_role")
        out.at[idx, "missing_systematic"] = cov["systematic"]
        out.at[idx, "full_pop_n"] = int(len(sample))
        out.at[idx, "same_pop_n"] = int(sample[feat].notna().sum())
        extra = row.get("extra") or {}
        if isinstance(extra, str):
            extra = _parse_json_cell(extra) or {}
        extra = dict(extra or {})
        extra["modeling_coverage"] = cov["coverage"]
        extra["modeling_coverage_n"] = int(sample[feat].notna().sum())
        extra["modeling_coverage_d"] = int(len(sample))
        if feat in seasons.columns:
            extra["seasons_coverage"] = coverage_profile(seasons, feat, player_type)["coverage"]
            extra["seasons_coverage_n"] = int(len(seasons))
        out.at[idx, "extra"] = extra
    return out


def _redecide_rows(table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    preserve = [c for c in table.columns if c not in AdmissionResult.__dataclass_fields__]
    for _, row in table.iterrows():
        res = result_from_row(row)
        res.verdict, res.rationale = decide_verdict(res)
        d = res.to_dict()
        for c in preserve:
            d[c] = row[c]
        rows.append(d)
    return pd.DataFrame(rows)


def _cross_family_kbb_controls(
    table: pd.DataFrame,
    sample: pd.DataFrame,
    baseline: list[str],
    target: str,
) -> pd.DataFrame:
    """After K% + BB% on the same population, tracking metrics are Diagnostic, not Projection."""
    out = table.copy()
    controls = [c for c in ("k_pct", "bb_pct") if c in sample.columns]
    if not controls:
        return out
    log = []
    for feat in PITCHER_KBB_CONTROL_DEMOTIONS:
        hits = out.index[out.feature.eq(feat)]
        if hits.empty:
            continue
        idx = hits[0]
        if out.loc[idx, "verdict"] not in {"Projection", "Augmented Projection"}:
            log.append({"feature": feat, "action": "skip_not_projection", "rmse_delta": None})
            continue
        inc = incremental_oos(sample, list(dict.fromkeys([*baseline, *controls])), feat, target)
        br = inc.get("baseline_rmse") or out.loc[idx, "baseline_rmse"] or 0.05
        thresh = MATERIAL_LIFT_FRAC * br
        delta = inc.get("rmse_delta")
        ci = (inc.get("boot") or {}).get("rmse_ci", (None, None))
        useful = bool(inc.get("ok")) and delta is not None and delta < -thresh
        ci_excludes = ci[1] is not None and ci[1] < 0
        extra = out.loc[idx, "extra"] or {}
        if isinstance(extra, str):
            extra = _parse_json_cell(extra) or {}
        extra = dict(extra or {})
        extra["after_k_pct_bb_pct"] = {
            "ok": inc.get("ok"),
            "rmse_delta": delta,
            "n_folds": inc.get("n_folds"),
            "ci_low": ci[0],
            "ci_high": ci[1],
            "n": inc.get("n"),
        }
        out.at[idx, "extra"] = extra
        if useful and ci_excludes:
            log.append({"feature": feat, "action": "keep_after_kbb", "rmse_delta": delta})
            continue
        out.at[idx, "verdict"] = "Diagnostic"
        out.at[idx, "family_representative"] = False
        prev = str(out.at[idx, "rationale"] or "")
        out.at[idx, "rationale"] = (
            "After controlling for K% and BB% on the same covered pitcher-seasons, this metric "
            "does not add enough incremental out-of-time K-BB% information to earn Projection. "
            "It remains useful as a process descriptor (bat-missing ability, pitch quality, "
            "velocity profile, or development), but it should not materially drive the broad "
            "projection model based on the current evidence. "
            + prev
        )
        log.append({"feature": feat, "action": "demote_after_kbb", "rmse_delta": delta})
    pd.DataFrame(log).to_csv(ARTIFACTS / "cross_family_kbb_demotion.csv", index=False)
    return out


def _annotate_pitcher_identity(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    identity = (
        "K-BB% = K% − BB% exactly; any two of K%, BB%, and K-BB% fully determine the third. "
        "They are not three independent projection signals. Preferred representation: "
        "2-year K-BB% with current K%."
    )
    for feat in ("k_pct", "bb_pct", "k_bb_pct", "k_bb_pct_z", "k_bb_pct_w2"):
        hits = out.index[out.feature.eq(feat)]
        if hits.empty:
            continue
        idx = hits[0]
        extra = out.at[idx, "extra"] or {}
        if isinstance(extra, str):
            extra = _parse_json_cell(extra) or {}
        extra = dict(extra or {})
        extra["kbb_identity"] = identity
        out.at[idx, "extra"] = extra
        prev = str(out.at[idx, "rationale"] or "")
        if "K-BB% = K%" not in prev:
            out.at[idx, "rationale"] = identity + " " + prev
    for feat in ("stuff_plus", "extension"):
        hits = out.index[out.feature.eq(feat)]
        if hits.empty:
            continue
        idx = hits[0]
        extra = out.at[idx, "extra"] or {}
        if isinstance(extra, str):
            extra = _parse_json_cell(extra) or {}
        extra = dict(extra or {})
        n = extra.get("modeling_coverage_n")
        d = extra.get("modeling_coverage_d")
        n_folds = out.at[idx, "n_folds"]
        cov = out.at[idx, "coverage"]
        if n is None or d is None:
            n = int(round(float(cov or 0) * 2682))
            d = 2682
        extra["modeling_coverage_public"] = f"{n}/{d} ≈ {float(n) / float(d):.0%}" if d else None
        out.at[idx, "extra"] = extra
        label = "Stuff+" if feat == "stuff_plus" else "Release Extension"
        prev = str(out.at[idx, "rationale"] or "")
        note = (
            f"{label} modeling coverage is {n} / {d} pitcher-seasons "
            f"(approximately {float(n) / float(d):.0%} of the modeling sample), "
            f"with {n_folds} expanding-window fold(s). "
            "That is not proof the metric has no predictive value."
        )
        if note.split()[0] not in prev:
            out.at[idx, "rationale"] = note + " " + prev
    return out


def apply_post_admission_rules(
    table: pd.DataFrame,
    *,
    sample: pd.DataFrame,
    seasons: pd.DataFrame,
    baseline: list[str],
    target: str,
    families: dict,
    player_type: str,
    redecide: bool,
    apply_kbb_demotion: bool = False,
) -> pd.DataFrame:
    table = parse_admission_frame(table)
    table = refresh_modeling_coverage(table, sample, seasons, player_type)
    if redecide:
        table = _redecide_rows(table)
    table = _greedy_family_representatives(table, sample, baseline, target, families)
    if player_type == "pitcher":
        if apply_kbb_demotion:
            table = _cross_family_kbb_controls(table, sample, baseline, target)
        table = _annotate_pitcher_identity(table)
    return table


def train_fold_medians(train: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    """Imputation parameters from the training fold only. Validation rows must not enter."""
    med = {}
    for c in cols:
        if c not in train.columns or not pd.api.types.is_numeric_dtype(train[c]):
            continue
        if train[c].notna().any():
            med[c] = float(train[c].median())
    return med


def apply_trainonly_impute(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, float]]:
    med = train_fold_medians(train, cols)
    train = train.copy()
    test = test.copy()
    used = []
    for c in cols:
        if c not in med:
            continue
        if train[c].notna().mean() < 0.05:
            continue
        train[c] = train[c].fillna(med[c])
        test[c] = test[c].fillna(med[c])
        used.append(c)
    return train, test, used, med


def run_study(study: StudySpec | str) -> pd.DataFrame:
    catalog = studies()
    spec = catalog[study] if isinstance(study, str) else study
    if spec.study_id in ARCHIVAL_STUDIES:
        raise RuntimeError(
            f"{spec.study_id} is archival and is not a canonical public study. "
            "See docs/archive/kbb_target_study.md."
        )
    if not spec.sample_path.exists() or not spec.seasons_path.exists():
        raise FileNotFoundError(f"missing panels for {spec.study_id}: {spec.sample_path}")
    seasons = pd.read_parquet(spec.seasons_path)
    sample = pd.read_parquet(spec.sample_path)
    labeled = pd.read_parquet(spec.labeled_path) if spec.labeled_path and spec.labeled_path.exists() else None
    if spec.weight_col and spec.weight_col in sample.columns:
        sample = sample.copy()
        sample["model_weight"] = pd.to_numeric(sample[spec.weight_col], errors="coerce")

    weak, baseline = _baselines_for_study(spec, sample)
    print(f"  study {spec.study_id} target={spec.target} baseline={baseline}")
    _baseline_audit(spec.player_type, sample, weak, baseline, spec.target, current=spec.persistence_col)

    rel_df = flag_exact_relations(sample, spec.player_type)
    rel_df.to_csv(ARTIFACTS / f"exact_redundancy_{spec.study_id}.csv", index=False)

    rows = []
    for feat_spec in spec.features:
        if feat_spec.name not in sample.columns:
            print(f"  skip missing {spec.study_id} {feat_spec.name}")
            continue
        print(f"  admit {spec.study_id} {feat_spec.name}...")
        result = admit_feature(
            player_type=spec.player_type,
            spec=feat_spec,
            sample=sample,
            seasons=seasons,
            baseline=baseline,
            target=spec.target,
            family_cols=None,
            component=spec.component,
        )
        extra = dict(result.extra or {})
        extra["baseline_used"] = baseline
        extra["study_id"] = spec.study_id
        extra["target_label"] = spec.target_label
        extra["exact_relations"] = rel_df.loc[rel_df.derived == feat_spec.name].to_dict(orient="records")
        result.extra = extra
        rows.append(result.to_dict())

    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError(f"no admission rows for {spec.study_id}")
    _family_tests(spec.player_type, sample, baseline, spec.target, spec.families, stem=spec.study_id)
    table = apply_post_admission_rules(
        table,
        sample=sample,
        seasons=seasons,
        baseline=baseline,
        target=spec.target,
        families=spec.families,
        player_type=spec.player_type,
        redecide=False,
        apply_kbb_demotion=spec.apply_kbb_demotion,
    )
    table["component"] = spec.component
    table["target"] = spec.target
    table["study_id"] = spec.study_id

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    serial = _json_cols(table)
    serial.to_parquet(ARTIFACTS / f"{spec.output_stem}.parquet", index=False)
    serial.to_csv(ARTIFACTS / f"{spec.output_stem}.csv", index=False)
    if spec.study_id == "hitting_woba":
        serial.to_parquet(ARTIFACTS / "admission_hitter.parquet", index=False)
        serial.to_csv(ARTIFACTS / "admission_hitter.csv", index=False)
    if spec.study_id == "pitching_fip":
        serial.to_parquet(ARTIFACTS / "admission_pitcher.parquet", index=False)
        serial.to_csv(ARTIFACTS / "admission_pitcher.csv", index=False)

    extra = {
        "study_id": spec.study_id,
        "component": spec.component,
        "target": spec.target,
        "target_label": spec.target_label,
        "baseline": {"weak": weak, "strong": baseline},
        "secondary_targets": _secondary_targets_for(spec, sample, table, baseline),
    }
    if spec.study_id == "hitting_woba" and labeled is not None:
        extra["pa_sensitivity"] = _pa_sensitivity(labeled, baseline, spec.target)
    (ARTIFACTS / f"extras_{spec.study_id}.json").write_text(json.dumps(extra, indent=2, default=str))
    _model_comparison(
        spec.player_type,
        sample,
        table,
        baseline,
        spec.target,
        persistence_col=spec.persistence_col,
        stem=spec.study_id,
    )
    return table


def run_player_type(player_type: str) -> pd.DataFrame:
    if player_type == "hitter":
        return run_study("hitting_woba")
    return run_study("pitching_fip")


def _pa_sensitivity(labeled: pd.DataFrame, baseline: list[str], target: str) -> dict:
    out = {}
    for pa in HITTER_PA_SENSITIVITY:
        samp = filter_hitter_sample(labeled, min_pa=pa)
        if len(samp) < 200:
            out[str(pa)] = {"n": int(len(samp))}
            continue
        ev = evaluate_features(samp, baseline, target)
        out[str(pa)] = {
            "n": int(len(samp)),
            "baseline_rmse": ev.get("mean_rmse"),
            "baseline_mae": ev.get("mean_mae"),
        }
    return out


def _secondary_targets_for(spec: StudySpec, sample: pd.DataFrame, table: pd.DataFrame, baseline: list[str]) -> dict:
    focus = [r["feature"] for _, r in table.head(12).iterrows() if r.get("feature") in sample.columns]
    extra_focus = {
        "hitting_woba": ["xwoba", "xwobacon", "barrel_pct", "ev", "o_swing_pct", "k_pct", "bb_pct", "woba_w2"],
        "pitching_fip": ["stuff_plus", "avg_velo", "avg_spin", "whiff_rate", "fip", "k_bb_pct_w2", "xwoba_against", "fip_w2"],
        "pitching_kbb": ["stuff_plus", "avg_velo", "ff_velo", "avg_spin", "whiff_rate", "fip", "k_bb_pct_w2", "xwoba_against"],
    }.get(spec.study_id, [])
    focus = list(dict.fromkeys([*extra_focus, *focus]))
    results = {}
    for tgt in spec.secondary_targets:
        if tgt not in sample.columns or sample[tgt].notna().mean() < 0.5:
            continue
        results[tgt] = {}
        for feat in focus:
            if feat not in sample.columns:
                continue
            inc = incremental_oos(sample, [c for c in baseline if c != feat], feat, tgt, do_bootstrap=False)
            if inc.get("ok"):
                results[tgt][feat] = {
                    "rmse_delta": inc["rmse_delta"],
                    "folds_improved": inc["folds_improved"],
                    "n": inc["n"],
                }
    return results


def _evaluate_trainonly_imputed(df: pd.DataFrame, features: list[str], target: str, model: str = "ridge") -> dict:
    """Median-impute using the training fold only. Validation-year medians must not leak."""
    use = [c for c in features if c in df.columns]
    fold_rows = []
    preds_all = []
    for train_idx, test_idx, year in expanding_folds(df):
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        train, test, cols, _med = apply_trainonly_impute(train, test, use)
        if not cols:
            continue
        fit = fit_predict(train, test, cols, target, model=model)
        if not fit.get("ok"):
            continue
        fold_rows.append(
            {
                "test_year": year,
                "rmse": rmse(fit["y"], fit["pred"], fit["w"]),
                "mae": mae(fit["y"], fit["pred"], fit["w"]),
                "n": fit["n_test"],
                "n_features": len(cols),
            }
        )
        preds_all.append(fit)
    if not fold_rows:
        return {"ok": False}
    folds_df = pd.DataFrame(fold_rows)
    return {
        "ok": True,
        "mean_rmse": float(folds_df["rmse"].mean()),
        "mean_mae": float(folds_df["mae"].mean()),
        "n_features": int(folds_df["n_features"].iloc[-1]),
        "features": use,
        "folds": folds_df,
        "preds": preds_all,
        "imputation": "train_fold_median_only",
    }


def _aligned_bootstrap(ev_a: dict, ev_b: dict) -> dict:
    y_all, p_a, p_b, w_all = [], [], [], []
    if not ev_a.get("ok") or not ev_b.get("ok"):
        return {}
    for ap, bp in zip(ev_a.get("preds") or [], ev_b.get("preds") or []):
        common = np.intersect1d(ap["index"], bp["index"])
        if len(common) < 10:
            continue
        amap = {i: j for j, i in enumerate(ap["index"])}
        bmap = {i: j for j, i in enumerate(bp["index"])}
        for i in common:
            y_all.append(ap["y"][amap[i]])
            p_a.append(ap["pred"][amap[i]])
            p_b.append(bp["pred"][bmap[i]])
            w_all.append(ap["w"][amap[i]])
    if len(y_all) < 40:
        return {}
    boot = bootstrap_delta(np.array(y_all), np.array(p_a), np.array(p_b), np.array(w_all))
    # bootstrap_delta: rmse(b) - rmse(a). Here a=admitted, b=kitchen so positive means kitchen worse.
    return {
        "n": int(len(y_all)),
        "rmse_delta_kitchen_minus_admitted": boot["rmse_delta"],
        "rmse_ci_low": boot["rmse_ci"][0],
        "rmse_ci_high": boot["rmse_ci"][1],
        "ci_excludes_zero": boot["rmse_ci"][0] > 0 or boot["rmse_ci"][1] < 0,
        "ci_includes_zero": not (boot["rmse_ci"][0] > 0 or boot["rmse_ci"][1] < 0),
    }


def _model_comparison(player_type: str, sample: pd.DataFrame, table: pd.DataFrame, baseline: list[str], target: str, persistence_col: str | None = None, stem: str | None = None) -> None:
    current = persistence_col or ("woba" if player_type == "hitter" else "fip")
    out_name = stem or player_type
    admitted = table.loc[table["verdict"].isin(["Projection"]), "feature"].tolist()
    flag = table["family_representative"] if "family_representative" in table.columns else pd.Series(False, index=table.index)
    representatives = table.loc[flag.fillna(False) & table["verdict"].eq("Projection"), "feature"].tolist()
    if not representatives:
        representatives = admitted
    augmented = table.loc[table["verdict"].isin(["Augmented Projection"]), "feature"].tolist()
    skill = table.loc[table["role"].eq("skill"), "feature"].tolist()
    core_feats = list(dict.fromkeys([*baseline, *[f for f in representatives if f in sample.columns and f not in baseline]]))
    if player_type == "hitter" and target == "y_woba":
        audit_core = list(KITCHEN_ADMITTED_HITTER)
    elif player_type == "pitcher" and target == "y_k_bb_pct":
        audit_core = list(KITCHEN_ADMITTED_PITCHER)
    else:
        audit_core = core_feats
    audit_core = [f for f in audit_core if f in sample.columns]
    kitchen = list(dict.fromkeys([*baseline, *[f for f in skill if f in sample.columns]]))
    kitchen_use = []
    for c in kitchen:
        if c not in sample.columns or not pd.api.types.is_numeric_dtype(sample[c]):
            continue
        if sample[c].notna().mean() < 0.05:
            continue
        kitchen_use.append(c)
    kitchen = kitchen_use

    rows = []
    for name, feats, data in [
        ("baseline", baseline, sample),
        ("admitted_core", core_feats, sample),
        ("admitted_core_audit", audit_core, sample),
    ]:
        ev = evaluate_features(data, feats, target, model="ridge")
        rec = _eval_row(name, ev, len(feats), feats)
        if rec:
            rows.append(rec)
        ev2 = evaluate_features(data, feats, target, model="elasticnet")
        rec2 = _eval_row(name + "_elasticnet", ev2, len(feats), feats)
        if rec2:
            rows.append(rec2)

    kit = _evaluate_trainonly_imputed(sample, kitchen, target, model="ridge")
    rec = _eval_row("kitchen_sink_imputed", kit, kit.get("n_features") or len(kitchen), kitchen)
    if rec:
        rec["imputation"] = "train_fold_median_only"
        rows.append(rec)
    kit2 = _evaluate_trainonly_imputed(sample, kitchen, target, model="elasticnet")
    rec2 = _eval_row("kitchen_sink_imputed_elasticnet", kit2, kit2.get("n_features") or len(kitchen), kitchen)
    if rec2:
        rec2["imputation"] = "train_fold_median_only"
        rows.append(rec2)

    adm_ev = evaluate_features(sample, audit_core, target, model="ridge")
    kitchen_boot = _aligned_bootstrap(adm_ev, kit) if kit.get("ok") else {}
    payload = {
        "player_type": player_type,
        "admitted_audit_features": audit_core,
        "admitted_audit_n": len(audit_core),
        "kitchen_n": kit.get("n_features") or len(kitchen),
        "admitted_rmse": adm_ev.get("mean_rmse"),
        "kitchen_rmse": kit.get("mean_rmse"),
        "imputation": "train_fold_median_only",
        "bootstrap": kitchen_boot,
        "interpretation": (
            "Admitted-feature model performs better than kitchen-sink; confidence interval excludes zero."
            if player_type == "hitter"
            else (
                "The admitted pitcher model was slightly better on average, but the uncertainty "
                "interval included zero, so the evidence does not support a clear difference."
            )
        ),
    }
    (ARTIFACTS / f"kitchen_sink_comparison_{out_name}.json").write_text(json.dumps(payload, indent=2, default=str))

    persist_rmse, persist_mae, n = [], [], 0
    for train_idx, test_idx, year in expanding_folds(sample):
        test = sample.iloc[test_idx]
        p = persistence_predict(sample.iloc[train_idx], test, current, target)
        persist_rmse.append(rmse(p["y"], p["pred"], p["w"]))
        persist_mae.append(mae(p["y"], p["pred"], p["w"]))
        n = p["n_test"]
    if persist_rmse:
        rows.append({"model": "persistence", "mean_rmse": float(np.mean(persist_rmse)), "mean_mae": float(np.mean(persist_mae)), "n_features": 1, "features": current})

    if augmented:
        cover_cols = [c for c in augmented if c in sample.columns]
        covered = sample.dropna(subset=cover_cols) if cover_cols else sample.iloc[0:0]
        if len(covered) >= 80:
            core_on_cov = evaluate_features(covered, core_feats, target)
            aug_feats = list(dict.fromkeys([*core_feats, *cover_cols]))
            aug_on_cov = evaluate_features(covered, aug_feats, target)
            if core_on_cov.get("ok") and aug_on_cov.get("ok"):
                rows.append({"model": "core_on_tracking_population", "mean_rmse": core_on_cov["mean_rmse"], "mean_mae": core_on_cov["mean_mae"], "n_features": len(core_feats), "n": int(len(covered)), "features": ",".join(core_feats)})
                rows.append({"model": "augmented_on_tracking_population", "mean_rmse": aug_on_cov["mean_rmse"], "mean_mae": aug_on_cov["mean_mae"], "n_features": len(aug_feats), "n": int(len(covered)), "features": ",".join(aug_feats)})

    pd.DataFrame(rows).to_parquet(ARTIFACTS / f"model_comparison_{out_name}.parquet", index=False)
    pd.DataFrame(rows).to_csv(ARTIFACTS / f"model_comparison_{out_name}.csv", index=False)
    if out_name == "hitting_woba":
        pd.DataFrame(rows).to_parquet(ARTIFACTS / "model_comparison_hitter.parquet", index=False)
        pd.DataFrame(rows).to_csv(ARTIFACTS / "model_comparison_hitter.csv", index=False)
    if out_name == "pitching_fip":
        pd.DataFrame(rows).to_parquet(ARTIFACTS / "model_comparison_pitcher.parquet", index=False)
        pd.DataFrame(rows).to_csv(ARTIFACTS / "model_comparison_pitcher.csv", index=False)


def _slice_unique(table: pd.DataFrame, **filters) -> pd.DataFrame:
    t = table
    for col, val in filters.items():
        if col not in t.columns:
            continue
        t = t[t[col].fillna(val).astype(str).eq(str(val))]
    if t.empty:
        return t
    return t.drop_duplicates("feature").set_index("feature")


def assert_audited_admission_table(table: pd.DataFrame) -> None:
    """Refuse to write a canonical table that still has the audited-stale hitting labels."""
    need = {"player_type", "feature", "verdict", "oos_rmse_delta", "coverage", "n_folds"}
    missing = need - set(table.columns)
    if missing:
        raise AssertionError(f"admission table missing columns: {missing}")

    h = _slice_unique(table, player_type="hitter", component="hitting", target="y_woba")
    if h.empty:
        h = _slice_unique(table, player_type="hitter", target="y_woba")
    if h.empty:
        h = table[table.player_type == "hitter"].drop_duplicates("feature").set_index("feature")

    xw = h.loc["xwoba_w2"]
    if str(xw["verdict"]) != "Projection":
        raise AssertionError(f"2-year xwOBA must be Projection, got {xw['verdict']}")
    delta = float(xw["oos_rmse_delta"])
    if abs(delta - (-0.000931)) > 2e-5:
        raise AssertionError(f"2-year xwOBA ΔRMSE must match audited -0.000931, got {delta}")
    if int(xw["n_folds"]) != 7 or float(xw["folds_improved"]) < 0.99:
        raise AssertionError("2-year xwOBA must improve 7/7 folds")

    if str(h.loc["ev", "verdict"]) != "Projection":
        raise AssertionError("EV must remain Projection")
    if str(h.loc["hard_hit_pct", "verdict"]) != "Diagnostic":
        raise AssertionError("HardHit% must remain Diagnostic")
    if str(h.loc["barrel_pct", "verdict"]) != "Diagnostic":
        raise AssertionError("Barrel% must remain Diagnostic")
    if str(h.loc["o_swing_pct", "verdict"]) != "Diagnostic":
        raise AssertionError("Chase must remain Diagnostic")
    if str(h.loc["sprint_speed", "verdict"]) != "Diagnostic":
        raise AssertionError("Sprint speed must remain Diagnostic for hitting / next-season wOBA")
    if str(h.loc["woba", "verdict"]) != "Exclude":
        raise AssertionError("Current wOBA must remain Exclude")

    p_fip = _slice_unique(table, player_type="pitcher", component="pitching", target="y_fip")
    if "target" in table.columns:
        kbb_n = int(table["target"].astype(str).eq("y_k_bb_pct").sum())
        if kbb_n:
            raise AssertionError(
                f"canonical admission table must not include next-season K-BB% as a target ({kbb_n} rows)"
            )
        public_targets = set(table["target"].astype(str).dropna().unique())
        expected_targets = {"y_woba", "y_fip", "y_br_rv_rate", "y_def_rv_rate", "y_war_rate"}
        if public_targets != expected_targets:
            raise AssertionError(f"canonical targets {sorted(public_targets)} != {sorted(expected_targets)}")
        if "component" in table.columns:
            n_studies = int(table.groupby(["component", "target"]).ngroups)
            if n_studies != 5:
                raise AssertionError(f"expected 5 public component studies, got {n_studies}")
    p = p_fip
    if not p.empty:
        if "stuff_plus" in p.index and str(p.loc["stuff_plus", "verdict"]) == "Exclude":
            raise AssertionError("Stuff+ must not be Exclude under y_fip")
        kbb_proj = [
            f
            for f in ("k_pct", "bb_pct", "k_bb_pct")
            if f in p.index and str(p.loc[f, "verdict"]) == "Projection"
        ]
        if set(kbb_proj) >= {"k_pct", "bb_pct"} or set(kbb_proj) >= {"k_pct", "k_bb_pct"} or set(kbb_proj) >= {"bb_pct", "k_bb_pct"}:
            raise AssertionError(f"K%, BB%, and K-BB% must not be independent Projection signals for y_fip; got {kbb_proj}")


STUDY_OUTPUT_STEMS = (
    "admission_hitting_y_woba",
    "admission_pitching_y_fip",
    "admission_baserunning_y_br_rv_rate",
    "admission_defense_y_def_rv_rate",
    "admission_overall_y_war_rate",
    "admission_pitcher_overall_y_war_rate",
)


def combine_tables() -> pd.DataFrame:
    frames = []
    for stem in STUDY_OUTPUT_STEMS:
        p = ARTIFACTS / f"{stem}.parquet"
        if p.exists():
            frames.append(parse_admission_frame(pd.read_parquet(p)))
    if not frames:
        for pt in ("hitter", "pitcher"):
            p = ARTIFACTS / f"admission_{pt}.parquet"
            if p.exists():
                frames.append(parse_admission_frame(pd.read_parquet(p)))
    table = pd.concat(frames, ignore_index=True)
    if "component" not in table.columns:
        table["component"] = np.where(table.player_type.eq("hitter"), "hitting", "pitching")
    else:
        missing_c = table["component"].isna() | table["component"].astype(str).isin(["", "nan", "None"])
        table.loc[missing_c, "component"] = np.where(table.loc[missing_c, "player_type"].eq("hitter"), "hitting", "pitching")
    if "target" not in table.columns:
        table["target"] = np.where(table.player_type.eq("hitter"), "y_woba", "y_fip")
    else:
        missing_t = table["target"].isna() | table["target"].astype(str).isin(["", "nan", "None"])
        table.loc[missing_t, "target"] = np.where(table.loc[missing_t, "player_type"].eq("hitter"), "y_woba", "y_fip")
    if "target" in table.columns:
        table = table[~table["target"].astype(str).eq("y_k_bb_pct")].copy()
    assert_audited_admission_table(table)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    serial = _json_cols(table)
    serial.to_parquet(ARTIFACTS / "admission_table.parquet", index=False)
    serial.to_csv(ARTIFACTS / "admission_table.csv", index=False)
    summary = {
        "built_at": _now(),
        "n_metrics": int(len(table)),
        "components": sorted(str(x) for x in table["component"].dropna().unique()),
        "targets": sorted(str(x) for x in table["target"].dropna().unique()),
        "hitter_n": int((table.player_type == "hitter").sum()),
        "pitcher_n": int((table.player_type == "pitcher").sum()),
        "provisional_until_universe_audit": False,
        "audit_revision": "component_targets_2015_2025",
        "baseline": {
            "hitter_hitting": list(HITTER_BASELINE),
            "pitcher_fip": list(PITCHER_BASELINE),
        },
        "counts": table.groupby(["component", "target", "verdict"]).size().reset_index(name="n").to_dict(orient="records"),
    }
    (ARTIFACTS / "admission_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return table


def tag_and_preserve_hitting() -> pd.DataFrame:
    src = ARTIFACTS / "admission_hitter.parquet"
    if not src.exists():
        raise FileNotFoundError(src)
    table = parse_admission_frame(pd.read_parquet(src))
    table["component"] = "hitting"
    if "target" not in table.columns:
        table["target"] = "y_woba"
    else:
        table["target"] = table["target"].fillna("y_woba")
        table["target"] = table["target"].astype(str).replace({"nan": "y_woba", "None": "y_woba", "": "y_woba"})
    table["study_id"] = "hitting_woba"
    serial = _json_cols(table)
    serial.to_parquet(ARTIFACTS / "admission_hitting_y_woba.parquet", index=False)
    serial.to_csv(ARTIFACTS / "admission_hitting_y_woba.csv", index=False)
    serial.to_parquet(src, index=False)
    return table


def archive_kbb_pitcher_study() -> None:
    """Move the historical K-BB% target experiment out of the canonical artifact set."""
    hist = ARTIFACTS / "historical"
    hist.mkdir(parents=True, exist_ok=True)
    dest_parq = hist / "admission_pitching_y_k_bb_pct.parquet"
    dest_csv = hist / "admission_pitching_y_k_bb_pct.csv"
    for src_name, dest in (
        ("admission_pitching_y_k_bb_pct.parquet", dest_parq),
        ("admission_pitching_y_k_bb_pct.csv", dest_csv),
    ):
        src = ARTIFACTS / src_name
        if src.exists():
            if not dest.exists():
                shutil.copy2(src, dest)
            src.unlink()
    for extra_name in ("extras_pitching_fip.json", "extras_pitcher.json"):
        extra_path = ARTIFACTS / extra_name
        if not extra_path.exists():
            continue
        extra = json.loads(extra_path.read_text())
        sec = extra.get("secondary_targets")
        if not isinstance(sec, dict) or "y_k_bb_pct" not in sec:
            continue
        hist_extra = hist / "extras_pitching_fip_y_k_bb_pct_secondary.json"
        if not hist_extra.exists():
            hist_extra.write_text(json.dumps({"y_k_bb_pct": sec["y_k_bb_pct"]}, indent=2, default=str))
        del sec["y_k_bb_pct"]
        extra["secondary_targets"] = sec
        extra_path.write_text(json.dumps(extra, indent=2, default=str))
    kit = ARTIFACTS / "kitchen_sink_comparison_pitcher.json"
    if kit.exists():
        payload = json.loads(kit.read_text())
        rmse = payload.get("admitted_rmse")
        if rmse is not None and float(rmse) < 0.2:
            dest_kit = hist / "kitchen_sink_comparison_pitcher_y_k_bb_pct.json"
            if not dest_kit.exists():
                shutil.copy2(kit, dest_kit)
            fip_kit = ARTIFACTS / "kitchen_sink_comparison_pitching_fip.json"
            if fip_kit.exists():
                shutil.copy2(fip_kit, kit)
    (hist / "README.md").write_text(
        "Historical pitcher admission under a K-BB% outcome target.\n"
        "Archival only. Not combined into the canonical admission table.\n"
        "See docs/archive/kbb_target_study.md.\n"
    )


def snapshot_kbb_pitcher_study() -> pd.DataFrame | None:
    archive_kbb_pitcher_study()
    hist = ARTIFACTS / "historical" / "admission_pitching_y_k_bb_pct.parquet"
    if hist.exists():
        return parse_admission_frame(pd.read_parquet(hist))
    return None


def rebuild_cached_admission() -> pd.DataFrame:
    """Re-apply audited verdict rules to cached OOS rows without re-fitting every feature."""
    catalog = studies()
    mapping = {
        "hitter": catalog["hitting_woba"],
        "pitcher": catalog["pitching_fip"],
    }
    for player_type, spec in mapping.items():
        cached = ARTIFACTS / f"{spec.output_stem}.parquet"
        if not cached.exists():
            cached = ARTIFACTS / f"admission_{player_type}.parquet"
        if not cached.exists():
            raise FileNotFoundError(cached)
        seasons = pd.read_parquet(spec.seasons_path)
        sample = pd.read_parquet(spec.sample_path)
        _, baseline = _baselines_for_study(spec, sample)
        table = parse_admission_frame(pd.read_parquet(cached))
        table = apply_post_admission_rules(
            table,
            sample=sample,
            seasons=seasons,
            baseline=baseline,
            target=spec.target,
            families=spec.families,
            player_type=spec.player_type,
            redecide=True,
            apply_kbb_demotion=spec.apply_kbb_demotion,
        )
        table["component"] = spec.component
        table["target"] = spec.target
        serial = _json_cols(table)
        serial.to_parquet(ARTIFACTS / f"{spec.output_stem}.parquet", index=False)
        serial.to_csv(ARTIFACTS / f"{spec.output_stem}.csv", index=False)
        serial.to_parquet(ARTIFACTS / f"admission_{player_type}.parquet", index=False)
        extra_path = ARTIFACTS / f"extras_{spec.study_id}.json"
        extra = json.loads(extra_path.read_text()) if extra_path.exists() else {}
        extra["baseline"] = {"strong": baseline}
        extra_path.write_text(json.dumps(extra, indent=2, default=str))
        _model_comparison(player_type, sample, table, baseline, spec.target, persistence_col=spec.persistence_col, stem=spec.study_id)
    return combine_tables()


def run_all(resume: bool = False) -> pd.DataFrame:
    print("Preserve hitting / next-season wOBA study")
    if (ARTIFACTS / "admission_hitter.parquet").exists() and resume:
        tag_and_preserve_hitting()
    elif (ARTIFACTS / "admission_hitter.parquet").exists() and not resume:
        tag_and_preserve_hitting()
    else:
        run_study("hitting_woba")

    print("Archive historical pitcher K-BB% target study")
    archive_kbb_pitcher_study()

    print("Pitcher admission study vs next-season FIP")
    run_study("pitching_fip")

    catalog = studies()
    for sid in ("baserunning_rv", "defense_rv", "overall_war", "pitcher_war"):
        spec = catalog[sid]
        if spec.sample_path.exists():
            print(f"{spec.component} admission study vs {spec.target_label}")
            run_study(sid)
        else:
            print(f"skip {sid}: {spec.sample_path} not built yet")
    return combine_tables()


if __name__ == "__main__":
    run_all(resume=True)
