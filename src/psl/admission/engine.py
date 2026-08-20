"""Feature Admission Engine: five gates, six verdicts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression

from psl.config import MATERIAL_LIFT_FRAC, N_BOOTSTRAP, RANDOM_SEED
from psl.models.baselines import bootstrap_delta, evaluate_features, expanding_folds, mae, rmse


@dataclass
class AdmissionResult:
    player_type: str
    feature: str
    family: str
    target: str
    role: str
    process: bool
    component: str = ""
    oos_rmse_delta: float | None = None
    oos_mae_delta: float | None = None
    oos_rmse_ci_low: float | None = None
    oos_rmse_ci_high: float | None = None
    folds_improved: float | None = None
    n_folds: int | None = None
    fold_rmse_deltas: list | None = None
    reliability_pearson: float | None = None
    reliability_spearman: float | None = None
    reliability_n: int | None = None
    coef_mean: float | None = None
    coef_sign_changes: int | None = None
    coef_path: list | None = None
    max_corr_with_baseline: float | None = None
    max_corr_partner: str | None = None
    vif: float | None = None
    nested_rmse_delta: float | None = None
    coverage: float | None = None
    coverage_by_season: dict | None = None
    coverage_by_pa_tier: dict | None = None
    coverage_by_role: dict | None = None
    missing_systematic: bool | None = None
    same_pop_n: int | None = None
    full_pop_n: int | None = None
    subgroup: dict | None = None
    in_sample_rmse_delta: float | None = None
    baseline_rmse: float | None = None
    verdict: str | None = None
    rationale: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def year_to_year_reliability(seasons: pd.DataFrame, feature: str, id_col: str = "mlbam_id") -> dict:
    if feature not in seasons.columns:
        return {"pearson": None, "spearman": None, "n": 0}
    a = seasons[[id_col, "season", feature]].dropna()
    b = a.rename(columns={feature: f"{feature}_next"})
    b["season"] = b["season"] - 1
    m = a.merge(b, on=[id_col, "season"])
    m = m.dropna()
    if len(m) < 30:
        return {"pearson": None, "spearman": None, "n": int(len(m))}
    pr = float(pearsonr(m[feature], m[f"{feature}_next"]).statistic)
    sr = float(spearmanr(m[feature], m[f"{feature}_next"]).statistic)
    return {"pearson": pr, "spearman": sr, "n": int(len(m))}


def _vif(df: pd.DataFrame, cols: list[str], feature: str) -> float | None:
    if feature not in df.columns:
        return None
    use = [c for c in cols if c in df.columns] + ([feature] if feature not in cols else [])
    use = list(dict.fromkeys(use))
    if feature not in use or len(use) < 2:
        return None
    sub = df[use].dropna()
    if len(sub) < 40:
        return None
    y = sub[feature]
    x = sub[[c for c in use if c != feature]]
    if x.shape[1] == 0:
        return None
    lr = LinearRegression().fit(x, y)
    r2 = lr.score(x, y)
    if r2 >= 0.999:
        return float("inf")
    return float(1.0 / (1.0 - r2))


def coverage_profile(df: pd.DataFrame, feature: str, player_type: str) -> dict:
    if feature not in df.columns:
        return {"coverage": 0.0, "by_season": {}, "by_tier": {}, "systematic": True}
    s = df[feature]
    by_season = {int(k): float(v) for k, v in df.groupby("season")[feature].apply(lambda x: x.notna().mean()).items()}
    by_tier = {}
    if player_type == "hitter" and "pa" in df.columns:
        tiers = pd.cut(df["pa"], [0, 150, 300, 450, 10000], labels=["<150", "150-300", "300-450", "450+"])
        by_tier = {str(k): float(v) for k, v in df.groupby(tiers, observed=False)[feature].apply(lambda x: x.notna().mean()).items()}
    if player_type == "pitcher" and "ip" in df.columns:
        tiers = pd.cut(df["ip"], [0, 30, 80, 150, 10000], labels=["<30", "30-80", "80-150", "150+"])
        by_tier = {str(k): float(v) for k, v in df.groupby(tiers, observed=False)[feature].apply(lambda x: x.notna().mean()).items()}
    by_role = {}
    if "starter_role" in df.columns:
        by_role = {str(int(k)): float(v) for k, v in df.groupby("starter_role")[feature].apply(lambda x: x.notna().mean()).items()}
    cov = float(s.notna().mean())
    vals = list(by_season.values())
    systematic = (max(vals) - min(vals) > 0.25) if vals else True
    if by_tier:
        tvals = [v for v in by_tier.values() if not np.isnan(v)]
        if tvals and (max(tvals) - min(tvals) > 0.25):
            systematic = True
    return {"coverage": cov, "by_season": by_season, "by_tier": by_tier, "by_role": by_role, "systematic": systematic}


def _align_preds(base: dict, aug: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    if not base.get("ok") or not aug.get("ok"):
        return None
    # compare fold-wise using stored preds lists
    return None


def incremental_oos(
    df: pd.DataFrame,
    baseline: list[str],
    feature: str,
    target: str,
    do_bootstrap: bool = True,
) -> dict:
    """Same-population comparison: rows where feature is observed."""
    if feature not in df.columns:
        return {"ok": False}
    sub = df[df[feature].notna()].copy()
    if len(sub) < 80:
        return {"ok": False, "reason": "too few non-missing rows", "n": int(len(sub))}
    base = evaluate_features(sub, baseline, target, model="ridge")
    aug = evaluate_features(sub, list(dict.fromkeys([*baseline, feature])), target, model="ridge")
    if not base.get("ok") or not aug.get("ok"):
        return {"ok": False}
    bfolds = base["folds"].set_index("test_year")
    afolds = aug["folds"].set_index("test_year")
    years = sorted(set(bfolds.index) & set(afolds.index))
    deltas = []
    for y in years:
        deltas.append(
            {
                "test_year": int(y),
                "rmse_delta": float(afolds.loc[y, "rmse"] - bfolds.loc[y, "rmse"]),
                "mae_delta": float(afolds.loc[y, "mae"] - bfolds.loc[y, "mae"]),
                "base_rmse": float(bfolds.loc[y, "rmse"]),
                "aug_rmse": float(afolds.loc[y, "rmse"]),
                "n": int(afolds.loc[y, "n"]),
            }
        )
    ddf = pd.DataFrame(deltas)
    # pooled bootstrap from concatenated OOS preds
    y_all, p_base, p_aug, w_all = [], [], [], []
    for bp, ap in zip(base["preds"], aug["preds"]):
        common = np.intersect1d(bp["index"], ap["index"])
        if len(common) < 10:
            continue
        bmap = {i: j for j, i in enumerate(bp["index"])}
        amap = {i: j for j, i in enumerate(ap["index"])}
        for i in common:
            y_all.append(bp["y"][bmap[i]])
            p_base.append(bp["pred"][bmap[i]])
            p_aug.append(ap["pred"][amap[i]])
            w_all.append(bp["w"][bmap[i]])
    boot = {"rmse_delta": float(ddf["rmse_delta"].mean()), "rmse_ci": (None, None), "mae_delta": float(ddf["mae_delta"].mean()), "mae_ci": (None, None)}
    if do_bootstrap and len(y_all) >= 40:
        boot = bootstrap_delta(np.array(y_all), np.array(p_base), np.array(p_aug), np.array(w_all))
    coefs = []
    sign_changes = 0
    prev = None
    for row in aug.get("coef_path", []):
        val = row.get(feature)
        coefs.append({"test_year": row.get("test_year"), "coef": val})
        if val is not None and prev is not None and np.sign(val) != 0 and np.sign(prev) != 0 and np.sign(val) != np.sign(prev):
            sign_changes += 1
        if val is not None:
            prev = val
    # in-sample contrast on last train window (descriptive only)
    last_year = years[-1] if years else None
    return {
        "ok": True,
        "n": int(len(sub)),
        "full_n": int(len(df)),
        "baseline_rmse": float(base["mean_rmse"]),
        "aug_rmse": float(aug["mean_rmse"]),
        "rmse_delta": float(ddf["rmse_delta"].mean()),
        "mae_delta": float(ddf["mae_delta"].mean()),
        "folds_improved": float((ddf["rmse_delta"] < 0).mean()),
        "n_folds": int(len(ddf)),
        "fold_table": ddf,
        "boot": boot,
        "coef_path": coefs,
        "coef_mean": float(np.nanmean([c["coef"] for c in coefs if c["coef"] is not None])) if coefs else None,
        "coef_sign_changes": sign_changes,
        "last_test_year": last_year,
    }


def subgroup_oos(df: pd.DataFrame, baseline: list[str], feature: str, target: str, player_type: str) -> dict:
    results = {}
    if feature not in df.columns:
        return results
    sub = df[df[feature].notna()].copy()
    groups: dict[str, pd.Series] = {}
    if "age" in sub.columns:
        groups["age_young"] = sub["age"] <= 25
        groups["age_prime"] = (sub["age"] >= 26) & (sub["age"] <= 30)
        groups["age_old"] = sub["age"] >= 31
    if player_type == "hitter":
        if "bats_left" in sub.columns:
            groups["lhb"] = sub["bats_left"] == 1
            groups["rhb"] = sub["bats_left"] == 0
        if "pa" in sub.columns:
            groups["pa_low"] = sub["pa"] < 400
            groups["pa_high"] = sub["pa"] >= 400
        if "position_group" in sub.columns:
            for g in sorted(sub["position_group"].dropna().unique()):
                groups[f"pos_{g}"] = sub["position_group"] == g
    else:
        if "starter_role" in sub.columns:
            groups["starter"] = sub["starter_role"] == 1
            groups["reliever"] = sub["starter_role"] == 0
        if "throws_left" in sub.columns:
            groups["lhp"] = sub["throws_left"] == 1
            groups["rhp"] = sub["throws_left"] == 0
        if "ip" in sub.columns:
            groups["ip_low"] = sub["ip"] < 80
            groups["ip_high"] = sub["ip"] >= 80
    for name, mask in groups.items():
        part = sub[mask]
        if len(part) < 120:
            results[name] = {"ok": False, "n": int(len(part))}
            continue
        try:
            inc = incremental_oos(part, baseline, feature, target, do_bootstrap=False)
        except Exception as exc:  # noqa: BLE001
            results[name] = {"ok": False, "error": str(exc), "n": int(len(part))}
            continue
        results[name] = {
            "ok": inc.get("ok", False),
            "n": int(len(part)),
            "rmse_delta": inc.get("rmse_delta"),
            "folds_improved": inc.get("folds_improved"),
        }
    return results


def admit_feature(
    *,
    player_type: str,
    spec,
    sample: pd.DataFrame,
    seasons: pd.DataFrame,
    baseline: list[str],
    target: str,
    family_cols: list[str] | None = None,
    component: str = "",
) -> AdmissionResult:
    feature = spec.name
    res = AdmissionResult(
        player_type=player_type,
        feature=feature,
        family=spec.family,
        target=target,
        role=spec.role,
        process=spec.process,
        component=component,
    )
    # Modeling-sample coverage is the admission denominator, not the unfiltered seasons table.
    # Seasons-table coverage is stored as extra context and must not be the public figure.
    cov = coverage_profile(sample, feature, player_type)
    res.coverage = cov["coverage"]
    res.coverage_by_season = cov["by_season"]
    res.coverage_by_pa_tier = cov["by_tier"]
    res.coverage_by_role = cov.get("by_role")
    res.missing_systematic = cov["systematic"]
    res.full_pop_n = int(len(sample))
    extra = dict(res.extra or {})
    extra["modeling_coverage"] = cov["coverage"]
    extra["modeling_coverage_n"] = int(sample[feature].notna().sum()) if feature in sample.columns else 0
    extra["modeling_coverage_d"] = int(len(sample))
    if feature in seasons.columns:
        seas = coverage_profile(seasons, feature, player_type)
        extra["seasons_coverage"] = seas["coverage"]
        extra["seasons_coverage_n"] = int(len(seasons))
    res.extra = extra

    rel = year_to_year_reliability(seasons, feature)
    res.reliability_pearson = rel["pearson"]
    res.reliability_spearman = rel["spearman"]
    res.reliability_n = rel["n"]

    partners = [c for c in baseline if c in sample.columns and c != feature]
    if feature in sample.columns and partners and sample[feature].notna().any():
        corrs = sample[partners + [feature]].corr(numeric_only=True)[feature].drop(feature, errors="ignore")
        corrs = corrs.dropna()
        if len(corrs):
            res.max_corr_with_baseline = float(corrs.abs().max())
            res.max_corr_partner = str(corrs.abs().idxmax())
    res.vif = _vif(sample, baseline, feature)

    inc = incremental_oos(sample, [c for c in baseline if c != feature], feature, target)
    if inc.get("ok"):
        res.same_pop_n = inc["n"]
        res.oos_rmse_delta = inc["rmse_delta"]
        res.oos_mae_delta = inc["mae_delta"]
        boot = inc["boot"]
        res.oos_rmse_ci_low = boot.get("rmse_ci", (None, None))[0]
        res.oos_rmse_ci_high = boot.get("rmse_ci", (None, None))[1]
        res.folds_improved = inc["folds_improved"]
        res.n_folds = inc["n_folds"]
        res.fold_rmse_deltas = inc["fold_table"].to_dict(orient="records")
        res.coef_path = inc["coef_path"]
        res.coef_mean = inc["coef_mean"]
        res.coef_sign_changes = inc["coef_sign_changes"]
        res.baseline_rmse = inc["baseline_rmse"]
    else:
        res.extra["oos_error"] = inc.get("reason", "oos failed")

    if family_cols:
        others = [c for c in family_cols if c != feature and c in sample.columns]
        if others:
            nest = incremental_oos(sample, list(dict.fromkeys([*[c for c in baseline if c != feature], *others])), feature, target, do_bootstrap=False)
            if nest.get("ok"):
                res.nested_rmse_delta = nest["rmse_delta"]

    try:
        res.subgroup = subgroup_oos(sample, [c for c in baseline if c != feature], feature, target, player_type)
    except Exception as exc:  # noqa: BLE001
        res.subgroup = {"error": str(exc)}

    extra = dict(res.extra or {})
    extra["in_baseline"] = spec.name in baseline
    res.extra = extra
    res.verdict, res.rationale = decide_verdict(res)
    return res


def _ci_excludes_zero_negative(low, high) -> bool | None:
    if low is None or high is None:
        return None
    return high < 0


VERDICTS = (
    "Projection",
    "Augmented Projection",
    "Diagnostic",
    "Context",
    "Exclude",
    "Insufficient Evidence",
)

VERDICT_PUBLIC_COPY = {
    "Projection": "Adds repeatable out-of-time information beyond what the model already knows.",
    "Augmented Projection": "Predictive where observed, but coverage is too incomplete for a universal core model.",
    "Diagnostic": "This metric helps describe how a player succeeds or struggles, but did not add enough independent future-prediction value to the broad model.",
    "Context": "Use to adjust or display environment, role, or playing time — not as player skill.",
    "Exclude": "The metric did not provide enough unique predictive or diagnostic value in this study.",
    "Insufficient Evidence": "We do not yet have enough reliable coverage or temporal validation to make a confident projection decision.",
}

MIN_FOLDS_FOR_ADMISSION = 3


def decide_verdict(res: AdmissionResult) -> tuple[str, str]:
    """Transparent rule. Negative RMSE delta = improvement.

    Insufficient Evidence is not Exclude: Exclude means the evidence suggests
    the feature should not be used; Insufficient Evidence means this study
    cannot confidently decide yet.
    """
    if res.role == "environment":
        return (
            "Context",
            "Environment/exposure variable. Use to adjust or display context, not as player skill, even if it helps prediction.",
        )
    if res.role == "demographic":
        return (
            "Context",
            "Demographic, role, or playing-time adjustment that belongs in the core model as context, not as a skill metric.",
        )

    in_baseline = bool((res.extra or {}).get("in_baseline"))

    delta = res.oos_rmse_delta
    material = False
    if delta is not None and res.baseline_rmse:
        material = abs(delta) >= MATERIAL_LIFT_FRAC * res.baseline_rmse and delta < 0
    ci_good = _ci_excludes_zero_negative(res.oos_rmse_ci_low, res.oos_rmse_ci_high)
    consistent = (res.folds_improved or 0) >= 0.6
    n_folds = res.n_folds if res.n_folds is not None else 0
    enough_windows = n_folds >= MIN_FOLDS_FOR_ADMISSION
    predictive = bool(material and enough_windows and (ci_good or consistent))

    if predictive and in_baseline and res.role == "skill":
        return (
            "Projection",
            "Current-season version of the target (or a declared baseline input) improves next-season prediction and belongs in the core model.",
        )

    redundant = False
    if res.nested_rmse_delta is not None and res.baseline_rmse:
        redundant = res.nested_rmse_delta > -MATERIAL_LIFT_FRAC * res.baseline_rmse
    elif res.max_corr_with_baseline is not None and res.max_corr_with_baseline > 0.92 and not predictive:
        redundant = True

    unstable_rel = res.reliability_pearson is not None and res.reliability_pearson < 0.25
    unstable_coef = (res.coef_sign_changes or 0) >= 2
    coverage = res.coverage or 0
    limited_coverage = coverage < 0.70 or (bool(res.missing_systematic) and coverage < 0.90)

    subgroup_fail = False
    if res.subgroup:
        large = []
        for payload in res.subgroup.values():
            if not isinstance(payload, dict) or not payload.get("ok"):
                continue
            if (payload.get("n") or 0) < 150 or payload.get("rmse_delta") is None:
                continue
            large.append(payload["rmse_delta"])
        if len(large) >= 2:
            harmful = sum(d > MATERIAL_LIFT_FRAC * (res.baseline_rmse or 0) for d in large)
            if harmful / len(large) >= 0.5:
                subgroup_fail = True

    thin_temporal = n_folds < MIN_FOLDS_FOR_ADMISSION
    if thin_temporal and limited_coverage:
        return (
            "Insufficient Evidence",
            "Coverage, sample, or temporal evidence is not strong enough for a confident admission verdict. "
            "Too few out-of-time windows and/or too sparse coverage to generalize. "
            "This is not an Exclude decision and is not proof the metric has no value.",
        )

    if predictive and not redundant and not unstable_coef and not subgroup_fail:
        if limited_coverage:
            return (
                "Augmented Projection",
                "Adds repeatable out-of-time information on the covered population, but coverage is too incomplete for a universal core model.",
            )
        return (
            "Projection",
            "Adds repeatable out-of-time information beyond the baseline, with acceptable stability, coverage, and subgroup behavior.",
        )
    if predictive and limited_coverage:
        return (
            "Augmented Projection",
            "Predictive where observed, but missingness/coverage prevents using it as a universal projection input.",
        )
    if predictive and redundant:
        if res.process:
            return (
                "Diagnostic",
                "Looks predictive alone but does not add conditional information beyond simpler features already in the model. Keep for explanation.",
            )
        return (
            "Exclude",
            "Incremental historical/OOS signal is redundant with simpler available features.",
        )
    if res.process:
        why = []
        if not predictive:
            why.append("does not add reliable out-of-time projection value beyond the baseline")
        if unstable_rel:
            why.append("year-to-year reliability is low")
        if unstable_coef:
            why.append("the predictive relationship drifts or changes sign")
        if redundant:
            why.append("information is largely already contained in other features")
        return (
            "Diagnostic",
            "Useful for describing process, strengths, or development areas, but " + "; ".join(why or ["not admitted to the production projection"]) + ".",
        )
    if res.role == "demographic":
        return (
            "Context",
            "Player characteristic used for stratification or adjustment rather than as a skill input.",
        )
    return (
        "Exclude",
        "The metric did not provide enough unique predictive or diagnostic value in this study.",
    )
