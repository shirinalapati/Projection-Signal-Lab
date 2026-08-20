"""Shared projection models and expanding-window validation."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNetCV, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from psl.config import (
    ELASTICNET_ALPHAS,
    ELASTICNET_L1_RATIO,
    EXPANDING_TEST_YEARS,
    N_BOOTSTRAP,
    RANDOM_SEED,
    RIDGE_ALPHA,
)


def make_ridge() -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=RIDGE_ALPHA)),
        ]
    )


def make_elasticnet() -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                ElasticNetCV(
                    l1_ratio=ELASTICNET_L1_RATIO,
                    alphas=ELASTICNET_ALPHAS,
                    cv=5,
                    max_iter=8000,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def expanding_folds(df: pd.DataFrame, test_years: list[int] | None = None) -> list[tuple[np.ndarray, np.ndarray, int]]:
    test_years = test_years or EXPANDING_TEST_YEARS
    folds = []
    seasons = df["season"].to_numpy()
    available = set(int(s) for s in df["season"].dropna().unique())
    for test_year in test_years:
        feature_season = test_year - 1
        if feature_season not in available:
            continue
        train_idx = np.where(seasons <= (test_year - 2))[0]
        test_idx = np.where(seasons == feature_season)[0]
        if len(train_idx) < 40 or len(test_idx) < 15:
            continue
        folds.append((train_idx, test_idx, test_year))
    return folds


def _xy(df: pd.DataFrame, features: list[str], target: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.Index]:
    cols = [c for c in features if c in df.columns]
    sub = df[cols + [target]].copy()
    mask = sub[cols].notna().all(axis=1) & sub[target].notna()
    x = sub.loc[mask, cols]
    y = sub.loc[mask, target].to_numpy(dtype=float)
    w = None
    for wcol in ("model_weight", "pa", "ip", "def_inn"):
        if wcol in df.columns:
            w = df.loc[mask, wcol].to_numpy(dtype=float)
            break
    if w is None:
        w = np.ones(len(y))
    w = np.clip(w, 1.0, None)
    return x, y, w, mask[mask].index


def fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    target: str,
    model: str = "ridge",
) -> dict:
    xtr, ytr, wtr, _ = _xy(train, features, target)
    cols = list(xtr.columns)
    xte = test[cols]
    mask = xte.notna().all(axis=1) & test[target].notna()
    xte = xte.loc[mask]
    yte = test.loc[mask, target].to_numpy(dtype=float)
    wte = None
    for wcol in ("model_weight", "pa", "ip", "def_inn"):
        if wcol in test.columns:
            wte = test.loc[mask, wcol].to_numpy(dtype=float)
            break
    if wte is None:
        wte = np.ones(len(yte))
    wte = np.clip(wte, 1.0, None)
    if len(xtr) < 30 or len(xte) < 10:
        return {"ok": False, "n_train": len(xtr), "n_test": len(xte)}
    est = make_elasticnet() if model == "elasticnet" else make_ridge()
    est.fit(xtr, ytr, model__sample_weight=wtr)
    pred = est.predict(xte)
    coefs = _coef_map(est, cols)
    return {
        "ok": True,
        "pred": pred,
        "y": yte,
        "w": wte,
        "index": xte.index.to_numpy(),
        "coefs": coefs,
        "n_train": int(len(xtr)),
        "n_test": int(len(xte)),
        "features": cols,
        "estimator": est,
    }


def _coef_map(est: Pipeline, cols: list[str]) -> dict[str, float]:
    model = est.named_steps["model"]
    coef = getattr(model, "coef_", None)
    if coef is None:
        return {}
    return {c: float(v) for c, v in zip(cols, coef)}


def rmse(y: np.ndarray, pred: np.ndarray, w: np.ndarray | None = None) -> float:
    err = (y - pred) ** 2
    if w is None:
        return float(np.sqrt(err.mean()))
    return float(np.sqrt(np.average(err, weights=w)))


def mae(y: np.ndarray, pred: np.ndarray, w: np.ndarray | None = None) -> float:
    err = np.abs(y - pred)
    if w is None:
        return float(err.mean())
    return float(np.average(err, weights=w))


def bootstrap_delta(
    y: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    w: np.ndarray,
    n_boot: int = N_BOOTSTRAP,
    seed: int = RANDOM_SEED,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y)
    deltas_rmse = np.empty(n_boot)
    deltas_mae = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        deltas_rmse[i] = rmse(y[idx], pred_b[idx], w[idx]) - rmse(y[idx], pred_a[idx], w[idx])
        deltas_mae[i] = mae(y[idx], pred_b[idx], w[idx]) - mae(y[idx], pred_a[idx], w[idx])
    return {
        "rmse_delta": float(deltas_rmse.mean()),
        "rmse_ci": (float(np.quantile(deltas_rmse, 0.025)), float(np.quantile(deltas_rmse, 0.975))),
        "mae_delta": float(deltas_mae.mean()),
        "mae_ci": (float(np.quantile(deltas_mae, 0.025)), float(np.quantile(deltas_mae, 0.975))),
    }


@dataclass
class FoldScore:
    test_year: int
    rmse: float
    mae: float
    n: int
    coefs: dict[str, float] = field(default_factory=dict)


def persistence_predict(train: pd.DataFrame, test: pd.DataFrame, current: str, target: str) -> dict:
    mask = test[current].notna() & test[target].notna()
    y = test.loc[mask, target].to_numpy(dtype=float)
    pred = test.loc[mask, current].to_numpy(dtype=float)
    if "pa" in test.columns:
        w = test.loc[mask, "pa"].to_numpy(dtype=float)
    elif "ip" in test.columns:
        w = test.loc[mask, "ip"].to_numpy(dtype=float)
    else:
        w = np.ones(len(y))
    return {"ok": True, "pred": pred, "y": y, "w": np.clip(w, 1, None), "index": test.loc[mask].index.to_numpy(), "n_test": int(mask.sum())}


def evaluate_features(
    df: pd.DataFrame,
    features: list[str],
    target: str,
    model: str = "ridge",
    current_col: str | None = None,
) -> dict:
    folds = expanding_folds(df)
    fold_rows = []
    coef_path = []
    preds_all = []
    for train_idx, test_idx, test_year in folds:
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        fit = fit_predict(train, test, features, target, model=model)
        if not fit.get("ok"):
            continue
        fold_rows.append(
            {
                "test_year": test_year,
                "rmse": rmse(fit["y"], fit["pred"], fit["w"]),
                "mae": mae(fit["y"], fit["pred"], fit["w"]),
                "n": fit["n_test"],
                "n_train": fit["n_train"],
            }
        )
        coef_path.append({"test_year": test_year, **fit["coefs"]})
        preds_all.append(fit)
    if not fold_rows:
        return {"ok": False, "folds": [], "features": features, "target": target}
    folds_df = pd.DataFrame(fold_rows)
    return {
        "ok": True,
        "features": features,
        "target": target,
        "model": model,
        "folds": folds_df,
        "mean_rmse": float(folds_df["rmse"].mean()),
        "mean_mae": float(folds_df["mae"].mean()),
        "coef_path": coef_path,
        "preds": preds_all,
    }
