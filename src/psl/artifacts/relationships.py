"""Future correlation, partial correlation, and drop-one OOS importance.

Explanatory statistics only. These fields never assign or revise admission verdicts.

Headline Pearson r, Spearman rho, and partial r are Fisher-z averages of
expanding-window *validation-fold* statistics:

- Features are always year t; targets are always year t+1 (`y_*` columns).
- Partial-correlation residualization coefficients are fit on the training fold
  and applied to the validation fold (no future-season leakage into preprocessing).
- Pooled full-sample correlations are stored as robustness fields and are not
  the public headline.

Drop-one OOS importance for Projection metrics:

    RMSE(admitted model without the metric) − RMSE(full admitted model)

Positive values mean the forecast gets worse when the metric is removed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from psl.admission.run import _json_cols, parse_admission_frame
from psl.components import studies
from psl.config import ARTIFACTS
from psl.models.baselines import evaluate_features, expanding_folds
from psl.site.labels import (
    LOWER_IS_BETTER_TARGETS,
    correlation_direction_label,
    display_name,
    future_relationship_short,
    target_phrase,
)

MIN_CORR_N = 20
SCATTER_FEATURES = {
    ("hitter", "xwoba_w2"),
    ("hitter", "ev"),
    ("hitter", "woba_w2"),
    ("hitter", "ops"),
    ("hitter", "barrel_pct"),
    ("hitter", "sprint_speed"),
    ("pitcher", "stuff_plus"),
    ("pitcher", "avg_velo"),
    ("pitcher", "fip_w2"),
    ("pitcher", "k_bb_pct_w3"),
    ("pitcher", "k_pct"),
    ("hitter", "br_rv_rate_w2"),
    ("hitter", "def_rv_rate_w2"),
}

METHOD = {
    "headline": "fisher_z_mean_of_expanding_window_validation_folds",
    "feature_timing": "year_t",
    "target_timing": "year_t_plus_1",
    "partial_residualization": "LinearRegression with intercept; coefficients fit on train fold only",
    "pooled_fields": "robustness only; not the public headline",
    "dropone": "RMSE(without feature) - RMSE(full admitted model); expanding-window Ridge on rows complete for the admitted core",
    "scatter": "pooled year-t vs t+1 points; caption reports headline Fisher-z r/rho",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < MIN_CORR_N:
        return None
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    r = float(np.corrcoef(a, b)[0, 1])
    if not np.isfinite(r):
        return None
    return float(np.clip(r, -1.0, 1.0))


def _spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    ra = pd.Series(a).rank(method="average").to_numpy(dtype=float)
    rb = pd.Series(b).rank(method="average").to_numpy(dtype=float)
    return _pearson(ra, rb)


def _fisher_mean(values: list[float | None]) -> float | None:
    rs = [float(v) for v in values if v is not None and np.isfinite(v) and abs(float(v)) < 0.999999]
    if not rs:
        return None
    z = float(np.mean([np.arctanh(v) for v in rs]))
    return float(np.clip(np.tanh(z), -1.0, 1.0))


def _design(df: pd.DataFrame, cols: list[str]) -> np.ndarray | None:
    use = [c for c in cols if c in df.columns]
    if not use:
        return np.zeros((len(df), 0))
    x = df[use].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        return None
    return x


def _residualize(y_train: np.ndarray, z_train: np.ndarray, y_test: np.ndarray, z_test: np.ndarray) -> np.ndarray:
    y_train = np.asarray(y_train, dtype=float)
    y_test = np.asarray(y_test, dtype=float)
    if z_train.size == 0 or z_train.shape[1] == 0:
        return y_test - float(y_train.mean())
    model = LinearRegression()
    model.fit(z_train, y_train)
    return y_test - model.predict(z_test)


def _complete(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    use = [c for c in cols if c in df.columns]
    out = df.dropna(subset=use).copy()
    return out


def _baseline_controls(spec, feature: str) -> list[str]:
    return [c for c in spec.baseline if c != feature]


def _metric_relationships(sample: pd.DataFrame, spec, feature: str) -> dict:
    target = spec.target
    if feature not in sample.columns or target not in sample.columns:
        return {}
    pair = _complete(sample, [feature, target])
    x_all = pair[feature].to_numpy(dtype=float)
    y_all = pair[target].to_numpy(dtype=float)
    pooled_p = _pearson(x_all, y_all)
    pooled_s = _spearman(x_all, y_all) if pooled_p is not None else None

    controls = [c for c in _baseline_controls(spec, feature) if c in sample.columns]
    part_cols = [feature, target, *controls]
    part = _complete(sample, part_cols)
    pooled_partial = None
    if len(part) >= MIN_CORR_N:
        z = _design(part, controls)
        if z is not None:
            xr = _residualize(part[feature].to_numpy(dtype=float), z, part[feature].to_numpy(dtype=float), z)
            yr = _residualize(part[target].to_numpy(dtype=float), z, part[target].to_numpy(dtype=float), z)
            pooled_partial = _pearson(xr, yr)

    fold_rows = []
    for train_idx, test_idx, test_year in expanding_folds(sample):
        train = sample.iloc[train_idx]
        test = sample.iloc[test_idx]
        pair_te = _complete(test, [feature, target])
        fold_p = _pearson(pair_te[feature].to_numpy(dtype=float), pair_te[target].to_numpy(dtype=float)) if len(pair_te) else None
        fold_s = (
            _spearman(pair_te[feature].to_numpy(dtype=float), pair_te[target].to_numpy(dtype=float))
            if fold_p is not None
            else None
        )
        fold_partial = None
        n_partial = 0
        if controls:
            need = [feature, target, *controls]
            tr = _complete(train, need)
            te = _complete(test, need)
            n_partial = int(len(te))
            if len(tr) >= MIN_CORR_N and len(te) >= MIN_CORR_N:
                ztr = _design(tr, controls)
                zte = _design(te, controls)
                if ztr is not None and zte is not None:
                    xr = _residualize(tr[feature].to_numpy(dtype=float), ztr, te[feature].to_numpy(dtype=float), zte)
                    yr = _residualize(tr[target].to_numpy(dtype=float), ztr, te[target].to_numpy(dtype=float), zte)
                    fold_partial = _pearson(xr, yr)
        else:
            fold_partial = fold_p
            n_partial = int(len(pair_te))
        fold_rows.append(
            {
                "test_year": int(test_year),
                "pearson": fold_p,
                "spearman": fold_s,
                "partial": fold_partial,
                "n": int(len(pair_te)),
                "n_partial": n_partial,
            }
        )

    headline_p = _fisher_mean([r["pearson"] for r in fold_rows])
    headline_s = _fisher_mean([r["spearman"] for r in fold_rows])
    headline_part = _fisher_mean([r["partial"] for r in fold_rows])
    source = "fold_fisher_z"
    if headline_p is None:
        headline_p = pooled_p
        headline_s = pooled_s
        source = "pooled_fallback"
    if headline_part is None:
        headline_part = pooled_partial
        if source != "pooled_fallback":
            source = "fold_fisher_z_partial_pooled_fallback"

    return {
        "future_pearson_r": headline_p,
        "future_spearman_rho": headline_s,
        "partial_future_r": headline_part,
        "future_pearson_r_pooled": pooled_p,
        "future_spearman_rho_pooled": pooled_s,
        "partial_future_r_pooled": pooled_partial,
        "correlation_n": int(len(pair)),
        "correlation_n_partial": int(len(part)),
        "correlation_folds": fold_rows,
        "correlation_headline_source": source,
        "correlation_direction_label": correlation_direction_label(headline_p, target),
        "future_relationship_label": future_relationship_short(headline_p),
    }


def _dropone_for_study(sample: pd.DataFrame, spec, table: pd.DataFrame) -> dict[str, float | None]:
    proj = table.loc[table["verdict"].isin(["Projection", "Augmented Projection"]), "feature"].tolist()
    core = list(dict.fromkeys([*[c for c in spec.baseline if c in sample.columns], *[f for f in proj if f in sample.columns]]))
    if len(core) < 2:
        return {}
    need = [c for c in core if c in sample.columns] + [spec.target]
    sample_c = _complete(sample, need)
    if len(sample_c) < 80:
        return {}
    full = evaluate_features(sample_c, core, spec.target)
    if not full.get("ok"):
        return {}
    full_rmse = full["mean_rmse"]
    out: dict[str, float | None] = {}
    for feat in proj:
        if feat not in sample_c.columns:
            continue
        without = [c for c in core if c != feat]
        if not without:
            out[feat] = None
            continue
        wo = evaluate_features(sample_c, without, spec.target)
        if not wo.get("ok"):
            out[feat] = None
            continue
        out[feat] = float(wo["mean_rmse"] - full_rmse)
    return out


def _svg_scatter(sample: pd.DataFrame, feature: str, target: str, title: str, r: float | None, rho: float | None) -> str:
    sub = sample[[feature, target]].dropna()
    if len(sub) < 40:
        return ""
    if len(sub) > 700:
        sub = sub.sample(700, random_state=42)
    x = sub[feature].to_numpy(dtype=float)
    y = sub[target].to_numpy(dtype=float)
    xmin, xmax = float(np.nanpercentile(x, 1)), float(np.nanpercentile(x, 99))
    ymin, ymax = float(np.nanpercentile(y, 1)), float(np.nanpercentile(y, 99))
    if xmax <= xmin or ymax <= ymin:
        return ""
    w, h = 420, 280
    l, t, rgt, b = 48, 28, 16, 40
    pw, ph = w - l - rgt, h - t - b

    def sx(v):
        return l + (v - xmin) / (xmax - xmin) * pw

    def sy(v):
        return t + (1 - (v - ymin) / (ymax - ymin)) * ph

    dots = "".join(
        f'<circle cx="{sx(a):.1f}" cy="{sy(c):.1f}" r="1.6" fill="#1b4d3e" fill-opacity="0.35"/>'
        for a, c in zip(x, y)
    )
    coef = np.polyfit(x, y, 1)
    x0, x1 = xmin, xmax
    y0, y1 = coef[0] * x0 + coef[1], coef[0] * x1 + coef[1]
    r_txt = "n/a" if r is None else f"{r:+.2f}"
    rho_txt = "n/a" if rho is None else f"{rho:+.2f}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
  <rect width="{w}" height="{h}" fill="#fffdf8"/>
  <text x="{l}" y="18" font-size="12" font-family="Georgia, serif" fill="#15202b">{title}</text>
  <text x="{l}" y="{h - 8}" font-size="11" font-family="Georgia, serif" fill="#5c6b73">Pearson r = {r_txt} · Spearman rho = {rho_txt}</text>
  <line x1="{l}" y1="{t}" x2="{l}" y2="{t+ph}" stroke="#d7cfc2"/>
  <line x1="{l}" y1="{t+ph}" x2="{l+pw}" y2="{t+ph}" stroke="#d7cfc2"/>
  {dots}
  <line x1="{sx(x0):.1f}" y1="{sy(y0):.1f}" x2="{sx(x1):.1f}" y2="{sy(y1):.1f}" stroke="#b86b2a" stroke-width="1.5"/>
</svg>
"""


def attach_relationships(table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add explanatory correlation fields to the canonical admission table. Verdicts are unchanged."""
    path = ARTIFACTS / "admission_table.parquet"
    if table is None:
        table = parse_admission_frame(pd.read_parquet(path))
    else:
        table = parse_admission_frame(table)
    before = table["verdict"].astype(str).copy()
    catalog = studies()
    extras = []
    scatter_dir = ARTIFACTS / "passports" / "scatters"
    scatter_dir.mkdir(parents=True, exist_ok=True)

    for study_id, spec in catalog.items():
        if spec.study_id == "pitching_kbb":
            continue
        sub = table[table.study_id.eq(study_id)].copy() if "study_id" in table.columns else table.iloc[0:0]
        if sub.empty:
            continue
        if not spec.sample_path.exists():
            continue
        print(f"  relationships {study_id} n={len(sub)}")
        sample = pd.read_parquet(spec.sample_path)
        dropone = _dropone_for_study(sample, spec, sub)
        for _, row in sub.iterrows():
            feat = str(row["feature"])
            rec = _metric_relationships(sample, spec, feat)
            rec["dropone_oos_rmse"] = dropone.get(feat)
            rec["player_type"] = row["player_type"]
            rec["feature"] = feat
            rec["component"] = row.get("component")
            rec["target"] = row.get("target")
            rec["study_id"] = study_id
            extras.append(rec)
            if (row["player_type"], feat) in SCATTER_FEATURES:
                svg = _svg_scatter(
                    sample,
                    feat,
                    spec.target,
                    f"{display_name(feat, row['player_type'])} vs {target_phrase(spec.target)}",
                    rec.get("future_pearson_r"),
                    rec.get("future_spearman_rho"),
                )
                if svg:
                    (scatter_dir / f"{row['player_type']}_{feat}_{spec.target}.svg").write_text(svg)

    extra_df = pd.DataFrame(extras)
    if extra_df.empty:
        return table
    keys = ["player_type", "feature", "component", "target"]
    add_cols = [
        "future_pearson_r",
        "future_spearman_rho",
        "partial_future_r",
        "future_pearson_r_pooled",
        "future_spearman_rho_pooled",
        "partial_future_r_pooled",
        "correlation_n",
        "correlation_n_partial",
        "correlation_folds",
        "correlation_headline_source",
        "correlation_direction_label",
        "future_relationship_label",
        "dropone_oos_rmse",
    ]
    drop_existing = [c for c in add_cols if c in table.columns]
    if drop_existing:
        table = table.drop(columns=drop_existing)
    if extra_df.duplicated(keys).any():
        raise AssertionError("relationship rows are not unique on (player_type, feature, component, target)")
    merged = table.merge(extra_df[keys + add_cols], on=keys, how="left")
    if len(merged) != len(table):
        raise AssertionError("attach_relationships changed admission table length")
    check = table[keys + ["verdict"]].merge(merged[keys + ["verdict"]], on=keys, suffixes=("_before", "_after"))
    if (check["verdict_before"].astype(str) != check["verdict_after"].astype(str)).any():
        raise AssertionError("attach_relationships changed admission verdicts")
    if (merged["verdict"].astype(str).to_numpy() != before.to_numpy()).any():
        raise AssertionError("attach_relationships reordered or changed admission verdicts")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    serial = _json_cols(merged)
    serial.to_parquet(path, index=False)
    serial.to_csv(ARTIFACTS / "admission_table.csv", index=False)
    csv_df = extra_df.copy()
    csv_df["correlation_folds"] = csv_df["correlation_folds"].apply(
        lambda x: json.dumps(x, default=str) if isinstance(x, list) else x
    )
    csv_df.to_csv(ARTIFACTS / "future_relationships.csv", index=False)
    (ARTIFACTS / "future_relationships_method.json").write_text(
        json.dumps({"built_at": _now(), "method": METHOD, "lower_is_better_targets": sorted(LOWER_IS_BETTER_TARGETS)}, indent=2)
    )
    return merged
