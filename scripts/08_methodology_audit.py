"""Skeptical methodological audit. Recomputes headline claims from canonical tables.

Does not add features. Writes artifacts/audit/*.csv and a JSON summary used
by docs/methodology_audit.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from psl.admission.engine import _vif, incremental_oos, subgroup_oos, year_to_year_reliability
from psl.catalog import HITTER_BASELINE, HITTER_BASELINE_WEAK, PITCHER_BASELINE, PITCHER_BASELINE_WEAK
from psl.config import (
    ARTIFACTS,
    COVID_YEAR,
    DATA_EXTERNAL,
    DATA_PROCESSED,
    DATA_RAW,
    HITTER_PA_PRIMARY,
    MATERIAL_LIFT_FRAC,
    N_BOOTSTRAP,
    PITCHER_IP_RP,
    PITCHER_IP_SP,
    RANDOM_SEED,
    RESEARCH_DIR,
)
from psl.data.assemble import _ip_threshold, filter_pitcher_sample
from psl.data.columns import parse_mlb_ip
from psl.models.baselines import (
    bootstrap_delta,
    evaluate_features,
    expanding_folds,
    fit_predict,
    mae,
    rmse,
)

OUT = ARTIFACTS / "audit"
OUT.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fail(issues: list[str], msg: str) -> None:
    issues.append(msg)
    print("FAIL:", msg)


def sample_identity(h: pd.DataFrame, p: pd.DataFrame, issues: list[str]) -> dict:
    def _one(df: pd.DataFrame, player_type: str, size_col: str) -> dict:
        dups = int(df.duplicated(["mlbam_id", "season"]).sum())
        if dups:
            raise AssertionError(
                f"{player_type} canonical sample has {dups} duplicate (mlbam_id, season) rows. "
                "A modeling table must have at most one row per player per season."
            )
        n_teams = coerce_num_teams(df)
        rec = {
            "player_type": player_type,
            "n_rows": int(len(df)),
            "n_unique_players": int(df["mlbam_id"].nunique()),
            "n_transitions": int(df["y_woba"].notna().sum() if player_type == "hitter" else df["y_fip"].notna().sum() if "y_fip" in df.columns else df["y_k_bb_pct"].notna().sum()),
            "min_season_t": int(df["season"].min()),
            "max_season_t": int(df["season"].max()),
            "min_target_season": int(df["target_season"].min()),
            "max_target_season": int(df["target_season"].max()),
            "by_season_t": {int(k): int(v) for k, v in df["season"].value_counts().sort_index().items()},
            "by_target_season": {int(k): int(v) for k, v in df["target_season"].value_counts().sort_index().items()},
            "size_col": size_col,
            "size_min": float(df[size_col].min()),
            "size_median": float(df[size_col].median()),
            "size_max": float(df[size_col].max()),
            "duplicate_player_seasons": dups,
            "multi_team_rows": int((n_teams > 1).sum()) if n_teams is not None else None,
            "num_teams_available": n_teams is not None,
        }
        return rec

    h_id = _one(h, "hitter", "pa")
    p_id = _one(p, "pitcher", "ip")
    h_id["filter"] = f"PA >= {HITTER_PA_PRIMARY} in season t and t+1; y_woba not null; season 2015-2024"
    p_id["filter"] = (
        f"starter GS/G>=0.5 and IP>={PITCHER_IP_SP} (2020: 25); "
        f"reliever IP>={PITCHER_IP_RP} (2020: 10); both t and t+1; y_fip not null"
    )
    # threshold actually applied?
    sp = p[p.starter_role == 1]
    rp = p[p.starter_role == 0]
    non_covid_sp = sp[sp.season != COVID_YEAR]
    covid_sp = sp[sp.season == COVID_YEAR]
    non_covid_rp = rp[rp.season != COVID_YEAR]
    covid_rp = rp[rp.season == COVID_YEAR]
    violations = []
    if len(non_covid_sp) and non_covid_sp["ip"].min() < PITCHER_IP_SP:
        violations.append(f"SP non-2020 min IP {non_covid_sp['ip'].min()} < {PITCHER_IP_SP}")
    if len(non_covid_rp) and non_covid_rp["ip"].min() < PITCHER_IP_RP:
        violations.append(f"RP non-2020 min IP {non_covid_rp['ip'].min()} < {PITCHER_IP_RP}")
    if len(covid_sp) and covid_sp["ip"].min() < 25:
        violations.append(f"SP 2020 min IP {covid_sp['ip'].min()} < 25")
    if len(covid_rp) and covid_rp["ip"].min() < 10:
        violations.append(f"RP 2020 min IP {covid_rp['ip'].min()} < 10")
    if h["pa"].min() < HITTER_PA_PRIMARY or h["y_pa"].min() < HITTER_PA_PRIMARY:
        violations.append("hitter PA filter not applied")
    for v in violations:
        _fail(issues, v)
    p_id["starter_n"] = int(len(sp))
    p_id["reliever_n"] = int(len(rp))
    p_id["starter_min_ip_non_covid"] = float(non_covid_sp["ip"].min()) if len(non_covid_sp) else None
    p_id["reliever_min_ip_non_covid"] = float(non_covid_rp["ip"].min()) if len(non_covid_rp) else None
    p_id["threshold_violations"] = violations
    # next-year IP threshold
    if "y_ip" in p.columns:
        thr_next = _ip_threshold(p["season"] + 1, p.get("y_starter_role", p["starter_role"]), PITCHER_IP_SP, PITCHER_IP_RP)
        under = p[p["y_ip"] < thr_next]
        if len(under):
            _fail(issues, f"pitcher y_ip below next-season threshold: {len(under)} rows")
        p_id["y_ip_below_threshold"] = int(len(under))
    # 2020 exception inflation: how many rows fail the non-COVID IP floors
    p_id["n_if_no_2020_exception"] = int(
        (
            ((p["starter_role"] == 1) & (p["ip"] >= PITCHER_IP_SP) & (p["y_ip"] >= PITCHER_IP_SP))
            | ((p["starter_role"] == 0) & (p["ip"] >= PITCHER_IP_RP) & (p["y_ip"] >= PITCHER_IP_RP))
        ).sum()
    )
    p_id["n_2020_feature_season"] = int((p["season"] == COVID_YEAR).sum())
    p_id["n_2020_target_season"] = int((p["target_season"] == COVID_YEAR).sum())
    p_id["mean_rows_per_feature_season"] = float(p.groupby("season").size().mean())
    h_id["n_2020_feature_season"] = int((h["season"] == COVID_YEAR).sum())
    pd.DataFrame(
        [
            {k: json.dumps(v) if isinstance(v, dict) else v for k, v in h_id.items()},
            {k: json.dumps(v) if isinstance(v, dict) else v for k, v in p_id.items()},
        ]
    ).to_csv(OUT / "sample_identity.csv", index=False)
    return {"hitter": h_id, "pitcher": p_id}


def coerce_num_teams(df: pd.DataFrame) -> pd.Series | None:
    if "num_teams" not in df.columns:
        return None
    return pd.to_numeric(df["num_teams"], errors="coerce")


def uniqueness_tables(issues: list[str]) -> dict:
    rec = {}
    for name, path, idc, seasonc in [
        ("hitter_seasons", DATA_PROCESSED / "hitter_seasons.parquet", "mlbam_id", "season"),
        ("pitcher_seasons", DATA_PROCESSED / "pitcher_seasons.parquet", "mlbam_id", "season"),
        ("baserunning_seasons", DATA_PROCESSED / "baserunning_seasons.parquet", "mlbam_id", "season"),
        ("defense_seasons", DATA_PROCESSED / "defense_seasons.parquet", "mlbam_id", "season"),
        ("war_hitter_seasons", DATA_PROCESSED / "war_hitter_seasons.parquet", "mlbam_id", "season"),
        ("war_pitcher_seasons", DATA_PROCESSED / "war_pitcher_seasons.parquet", "mlbam_id", "season"),
        ("hitter_labeled", DATA_PROCESSED / "hitter_labeled.parquet", "mlbam_id", "season"),
        ("pitcher_labeled", DATA_PROCESSED / "pitcher_labeled.parquet", "mlbam_id", "season"),
        ("hitter_sample", DATA_PROCESSED / "hitter_sample_pa150.parquet", "mlbam_id", "season"),
        ("pitcher_sample", DATA_PROCESSED / "pitcher_sample_role_ip.parquet", "mlbam_id", "season"),
    ]:
        if not path.exists():
            rec[name] = {"missing": True}
            continue
        df = pd.read_parquet(path)
        dups = int(df.duplicated([idc, seasonc]).sum())
        rec[name] = {
            "n": int(len(df)),
            "dups": dups,
            "unique_players": int(df[idc].nunique()),
            "min_season": int(df[seasonc].min()) if seasonc in df.columns else None,
            "max_season": int(df[seasonc].max()) if seasonc in df.columns else None,
        }
        if dups:
            raise AssertionError(f"{name} has {dups} duplicate ({idc}, {seasonc}) rows")
        if name.endswith("_seasons") and rec[name]["min_season"] is not None:
            if rec[name]["min_season"] > 2015 or rec[name]["max_season"] < 2025:
                _fail(issues, f"{name} seasons {rec[name]['min_season']}-{rec[name]['max_season']} do not span 2015-2025")
    for name, fname, idc, seasonc in [
        ("savant_batter", "savant_batter_custom_2015_2025.parquet", "player_id", "year"),
        ("savant_pitcher", "savant_pitcher_custom_2015_2025.parquet", "player_id", "year"),
        ("mlb_hitting", "mlb_hitting_2015_2025.parquet", "mlbam_id", "season"),
        ("mlb_pitching", "mlb_pitching_2015_2025.parquet", "mlbam_id", "season"),
    ]:
        p = DATA_RAW / fname
        if not p.exists():
            rec[name] = {"missing": True}
            continue
        df = pd.read_parquet(p)
        cols = [c for c in [idc, seasonc] if c in df.columns]
        if seasonc not in df.columns and "season" in df.columns:
            cols = [idc, "season"]
        dups = int(df.duplicated(cols).sum()) if len(cols) == 2 else None
        rec[name] = {"n": int(len(df)), "dups_id_season": dups, "nunique_keys": int(df[cols].drop_duplicates().shape[0]) if cols else None}
        if dups:
            rec[name]["note"] = "Raw source has player-season duplicates (stints or multi-team). Assemble must collapse them."
    return rec


def ip_parse_audit(p: pd.DataFrame, issues: list[str]) -> dict:
    """Savant IP is decimal innings; MLB API uses .1/.2 = outs."""
    rec = {
        "note": "Primary IP is Savant p_formatted_ip (decimal). MLB .1=1/3 only used when Savant IP is missing.",
    }
    if "ip" in p.columns:
        frac = p["ip"] - np.floor(p["ip"])
        rec["share_frac_in_0.01_0.19"] = float(((frac > 0.01) & (frac < 0.20)).mean())
        rec["share_frac_in_0.21_0.39"] = float(((frac > 0.20) & (frac < 0.40)).mean())
        rec["share_frac_exactly_1_or_2_tenths"] = float(frac.round(1).isin([0.1, 0.2]).mean())
        rec["min_ip"] = float(p["ip"].min())
        rec["max_ip"] = float(p["ip"].max())
        rec["n_ip_missing"] = int(p["ip"].isna().sum())
    if "ip_mlb" in p.columns:
        parsed = parse_mlb_ip(p["ip_mlb"])
        both = p["ip"].notna() & parsed.notna()
        rec["n_both_savant_and_mlb"] = int(both.sum())
        if both.any():
            rec["median_abs_savant_minus_parsed_mlb"] = float((p.loc[both, "ip"] - parsed.loc[both]).abs().median())
            rec["share_abs_diff_gt_0.05"] = float(((p.loc[both, "ip"] - parsed.loc[both]).abs() > 0.05).mean())
    return rec


def leakage_audit(h: pd.DataFrame, p: pd.DataFrame, hs: pd.DataFrame, ps: pd.DataFrame, issues: list[str]) -> dict:
    """Season-t features must not equal or use t+1 outcomes; park must be same-season."""
    findings = []
    # target join
    if not h["target_season"].equals(h["season"] + 1):
        _fail(issues, "hitter target_season is not season+1")
    if not p["target_season"].equals(p["season"] + 1):
        _fail(issues, "pitcher target_season is not season+1")
    # y_ columns vs current
    for col in ["xwoba", "ev", "barrel_pct", "hard_hit_pct", "o_swing_pct", "sprint_speed", "k_pct", "bb_pct", "woba"]:
        if col in h.columns:
            corr = float(h[col].corr(h["y_woba"]))
            findings.append({"player_type": "hitter", "feature": col, "corr_with_y_woba": corr, "equal_to_target": False})
            if corr > 0.95:
                _fail(issues, f"hitter {col} correlates {corr:.3f} with y_woba — possible leakage")
    for col in ["k_bb_pct", "k_pct", "bb_pct", "avg_velo", "avg_spin", "whiff_rate", "stuff_plus", "z_contact_pct", "fip"]:
        if col in p.columns and "y_fip" in p.columns:
            corr = float(p[col].corr(p["y_fip"]))
            findings.append({"player_type": "pitcher", "feature": col, "corr_with_y_fip": corr})
            if corr > 0.95:
                _fail(issues, f"pitcher {col} correlates {corr:.3f} with y_fip — possible leakage")
        if col in p.columns and "y_k_bb_pct" in p.columns:
            corr = float(p[col].corr(p["y_k_bb_pct"]))
            findings.append({"player_type": "pitcher", "feature": col, "corr_with_y_kbb": corr})
            if corr > 0.95:
                _fail(issues, f"pitcher {col} correlates {corr:.3f} with y_k_bb_pct — possible leakage")
    # history must not use t+1 of same player
    for df, col, ycol in [(h, "woba_w2", "y_woba"), (h, "xwoba_w2", "y_woba"), (p, "fip_w2", "y_fip"), (p, "k_bb_pct_w2", "y_k_bb_pct")]:
        if col in df.columns:
            # w2 should not equal next-season value
            eq = float((df[col] - df[ycol]).abs().median())
            findings.append({"check": f"{col}_vs_{ycol}_median_abs", "value": eq})
    # park: merge key is season t + team_id
    park = pd.read_parquet(DATA_EXTERNAL / "park_factors.parquet")
    mlb = park[park.sport_id == 1]
    rec = {
        "park_source": "Prospect_Lab estimate_park_factors: same-season team runs/PA vs league, shrunk to 1.0 with n0=3. Confounds team talent with park. Not a multi-year rolling factor.",
        "park_seasons": [int(mlb.season.min()), int(mlb.season.max())],
        "park_n_mlb_rows": int(len(mlb)),
        "uses_future_seasons_in_formula": False,
        "same_season_merge": True,
        "forward_looking": False,
        "hitter_park_filled_with_1": float((h["park_factor"] == 1.0).mean()) if "park_factor" in h.columns else None,
        "pitcher_park_filled_with_1": float((p["park_factor"] == 1.0).mean()) if "park_factor" in p.columns else None,
    }
    # confirm a 2018 park row does not need 2019+ data: construction is groupby season
    rec["construction"] = "df.rpg / season-sport mean(rpg); shrink (3*1 + 1*raw)/4"
    # Stuff+ seasons
    stuff = pd.read_parquet(DATA_EXTERNAL / "frozen_arsenal_scores_2023_2025.parquet")
    rec["stuff_seasons"] = sorted(int(x) for x in stuff["season"].unique())
    rec["stuff_n"] = int(len(stuff))
    rec["stuff_pooling"] = (
        "Stuff_Quality/precompute.py fits logistic models on pooled pitches loaded for 2023–2026, "
        "then z-scores within role×pitch_group across that pool. frozen_arsenal_scores_2023_2025.parquet "
        "locks 2023–2025 rows so 2026 updates do not overwrite them. Frozen ≠ season-t-only model. "
        "Coefficients and z-score means for 2023 scores likely include 2024–2025 pitches if the freeze "
        "was created from a pooled 2023–2025 (or 2023–2026) fit."
    )
    # season-t park is not next-season park when the player changes teams
    def _team_change(df: pd.DataFrame, seasons: pd.DataFrame, label: str) -> dict:
        nxt = seasons[["mlbam_id", "season", "team_id"]].rename(columns={"season": "target_season", "team_id": "y_team_id"})
        m = df.merge(nxt, on=["mlbam_id", "target_season"], how="left")
        both = m["team_id"].notna() & m["y_team_id"].notna()
        changed = both & (m["team_id"] != m["y_team_id"])
        return {
            "n_with_both_teams": int(both.sum()),
            "n_changed_team_t_to_t1": int(changed.sum()),
            "share_changed": float(changed.sum() / both.sum()) if both.sum() else None,
            "note": f"{label}: season-t park_factor is last year's team environment, not t+1 park. Not future leakage, but not the park of the outcome season for movers.",
        }

    rec["hitter_team_change"] = _team_change(h, hs, "hitter")
    rec["pitcher_team_change"] = _team_change(p, ps, "pitcher")
    rec["park_is_skill"] = False
    rec["park_interpretation"] = (
        "Same-season team runs/PA vs league, shrunk. Confounds roster talent with park. "
        "Must stay Context, not a skill input. A player's own runs enter team RPG slightly (circularity, not t+1 leak)."
    )
    pd.DataFrame(findings).to_csv(OUT / "leakage_feature_target_corr.csv", index=False)
    return rec


def fold_table(df: pd.DataFrame, player_type: str) -> pd.DataFrame:
    rows = []
    for train_idx, test_idx, year in expanding_folds(df):
        train = df.iloc[train_idx]
        test = df.iloc[test_idx]
        rows.append(
            {
                "player_type": player_type,
                "test_year_outcome": int(year),
                "validation_feature_season": int(year - 1),
                "train_seasons": f"{int(train.season.min())}-{int(train.season.max())}",
                "n_train": int(len(train)),
                "n_validation": int(len(test)),
                "train_max_season": int(train.season.max()),
                "val_season": int(test.season.iloc[0]) if len(test) else None,
                "leak_train_includes_val": bool(train.season.max() >= year - 1),
                "leak_train_includes_outcome": bool(train.season.max() >= year),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"folds_{player_type}.csv", index=False)
    return out


def signed_oos(df: pd.DataFrame, baseline: list[str], extra: list[str], target: str, label: str) -> dict:
    """Signed OOS. Negative rmse_delta = extra features improve RMSE (aug − baseline)."""
    if len(extra) == 1:
        inc = incremental_oos(df, baseline, extra[0], target)
    else:
        inc = None
    if len(extra) != 1:
        sub = df.dropna(subset=extra).copy()
        base = evaluate_features(sub, baseline, target)
        aug = evaluate_features(sub, list(dict.fromkeys([*baseline, *extra])), target)
        if not base.get("ok") or not aug.get("ok"):
            return {"label": label, "ok": False}
        bfolds = base["folds"].set_index("test_year")
        afolds = aug["folds"].set_index("test_year")
        years = sorted(set(bfolds.index) & set(afolds.index))
        deltas = [float(afolds.loc[y, "rmse"] - bfolds.loc[y, "rmse"]) for y in years]
        fold_rows = [
            {
                "test_year": int(y),
                "base_rmse": float(bfolds.loc[y, "rmse"]),
                "aug_rmse": float(afolds.loc[y, "rmse"]),
                "rmse_delta": float(afolds.loc[y, "rmse"] - bfolds.loc[y, "rmse"]),
                "base_mae": float(bfolds.loc[y, "mae"]),
                "aug_mae": float(afolds.loc[y, "mae"]),
                "n": int(afolds.loc[y, "n"]),
            }
            for y in years
        ]
        y_all, p_base, p_aug, w_all = [], [], [], []
        for bp, ap in zip(base["preds"], aug["preds"]):
            common = np.intersect1d(bp["index"], ap["index"])
            bmap = {i: j for j, i in enumerate(bp["index"])}
            amap = {i: j for j, i in enumerate(ap["index"])}
            for i in common:
                y_all.append(bp["y"][bmap[i]])
                p_base.append(bp["pred"][bmap[i]])
                p_aug.append(ap["pred"][amap[i]])
                w_all.append(bp["w"][bmap[i]])
        boot = bootstrap_delta(np.array(y_all), np.array(p_base), np.array(p_aug), np.array(w_all)) if len(y_all) >= 40 else {"rmse_delta": float(np.mean(deltas)), "rmse_ci": (None, None), "mae_delta": None, "mae_ci": (None, None)}
        out = {
            "label": label,
            "ok": True,
            "n": int(len(sub)),
            "features": extra,
            "baseline": baseline,
            "fold_table": fold_rows,
            "mean_delta": float(np.mean(deltas)),
            "median_delta": float(np.median(deltas)),
            "folds_improved": float(np.mean([d < 0 for d in deltas])),
            "n_folds": int(len(deltas)),
            "boot_rmse_delta": boot["rmse_delta"],
            "boot_ci_low": boot["rmse_ci"][0],
            "boot_ci_high": boot["rmse_ci"][1],
            "boot_mae_delta": boot.get("mae_delta"),
            "sign": "negative delta = improvement (aug RMSE − baseline RMSE)",
        }
        return out
    if not inc or not inc.get("ok"):
        return {"label": label, "ok": False, "reason": None if not inc else inc.get("reason")}
    ft = inc["fold_table"]
    deltas = ft["rmse_delta"].astype(float)
    return {
        "label": label,
        "ok": True,
        "n": inc["n"],
        "features": extra,
        "baseline": baseline,
        "fold_table": ft.to_dict(orient="records"),
        "mean_delta": float(deltas.mean()),
        "median_delta": float(deltas.median()),
        "folds_improved": float((deltas < 0).mean()),
        "n_folds": int(len(deltas)),
        "boot_rmse_delta": inc["boot"]["rmse_delta"],
        "boot_ci_low": inc["boot"]["rmse_ci"][0],
        "boot_ci_high": inc["boot"]["rmse_ci"][1],
        "boot_mae_delta": inc["boot"].get("mae_delta"),
        "sign": "negative delta = improvement (aug RMSE − baseline RMSE)",
    }


def dump_oos(payload: dict, name: str) -> None:
    if payload.get("fold_table"):
        pd.DataFrame(payload["fold_table"]).assign(label=name).to_csv(OUT / f"oos_{name}.csv", index=False)
    slim = {k: v for k, v in payload.items() if k != "fold_table"}
    (OUT / f"oos_{name}.json").write_text(json.dumps(slim, indent=2, default=str))


def evaluate_imputed(df: pd.DataFrame, features: list[str], target: str) -> dict:
    """Per-fold train-only median imputation. No test-year medians."""
    use = [c for c in features if c in df.columns]
    fold_rows = []
    preds = []
    for train_idx, test_idx, year in expanding_folds(df):
        train = df.iloc[train_idx].copy()
        test = df.iloc[test_idx].copy()
        cols = []
        for c in use:
            if not pd.api.types.is_numeric_dtype(train[c]):
                continue
            if train[c].notna().mean() < 0.05:
                continue
            med = train[c].median()
            train[c] = train[c].fillna(med)
            test[c] = test[c].fillna(med)
            cols.append(c)
        fit = fit_predict(train, test, cols, target, model="ridge")
        if not fit.get("ok"):
            continue
        fold_rows.append(
            {
                "test_year": year,
                "rmse": rmse(fit["y"], fit["pred"], fit["w"]),
                "mae": mae(fit["y"], fit["pred"], fit["w"]),
                "n": fit["n_test"],
                "n_train": fit["n_train"],
                "n_features": len(cols),
            }
        )
        preds.append(fit)
    if not fold_rows:
        return {"ok": False}
    folds_df = pd.DataFrame(fold_rows)
    return {"ok": True, "folds": folds_df, "mean_rmse": float(folds_df.rmse.mean()), "mean_mae": float(folds_df.mae.mean()), "preds": preds, "n_features": int(folds_df.n_features.iloc[-1])}


def compare_models_foldwise(a: dict, b: dict, name_a: str, name_b: str) -> dict:
    if not a.get("ok") or not b.get("ok"):
        return {"ok": False}
    af = a["folds"].set_index("test_year")
    bf = b["folds"].set_index("test_year")
    years = sorted(set(af.index) & set(bf.index))
    rows = []
    for y in years:
        rows.append(
            {
                "test_year": int(y),
                f"{name_a}_rmse": float(af.loc[y, "rmse"]),
                f"{name_b}_rmse": float(bf.loc[y, "rmse"]),
                "delta_b_minus_a": float(bf.loc[y, "rmse"] - af.loc[y, "rmse"]),
                "n": int(min(af.loc[y, "n"], bf.loc[y, "n"])),
            }
        )
    ddf = pd.DataFrame(rows)
    y_all, pa, pb, w_all = [], [], [], []
    for ap, bp in zip(a["preds"], b["preds"]):
        common = np.intersect1d(ap["index"], bp["index"])
        amap = {i: j for j, i in enumerate(ap["index"])}
        bmap = {i: j for j, i in enumerate(bp["index"])}
        for i in common:
            y_all.append(ap["y"][amap[i]])
            pa.append(ap["pred"][amap[i]])
            pb.append(bp["pred"][bmap[i]])
            w_all.append(ap["w"][amap[i]])
    boot = bootstrap_delta(np.array(y_all), np.array(pa), np.array(pb), np.array(w_all)) if len(y_all) >= 40 else {}
    return {
        "ok": True,
        "folds": ddf.to_dict(orient="records"),
        "mean_delta": float(ddf["delta_b_minus_a"].mean()),
        "median_delta": float(ddf["delta_b_minus_a"].median()),
        "boot": boot,
        "n_common_preds": int(len(y_all)),
        "sign": "delta = RMSE(b) − RMSE(a); negative means b is better",
    }


def vif_and_enet(df: pd.DataFrame, baseline: list[str], family: list[str], target: str, tag: str) -> dict:
    present = [c for c in family if c in df.columns]
    vif_rows = []
    for feat in present:
        others = [c for c in present if c != feat]
        vif_rows.append(
            {
                "feature": feat,
                "vif_vs_family": _vif(df, others, feat),
                "vif_vs_baseline_and_family": _vif(df, list(dict.fromkeys([*baseline, *others])), feat),
            }
        )
    vif_df = pd.DataFrame(vif_rows)
    vif_df.to_csv(OUT / f"vif_{tag}.csv", index=False)
    pop = df.dropna(subset=present + [target]).copy()
    enet_rows = []
    for train_idx, test_idx, year in expanding_folds(pop):
        fit = fit_predict(pop.iloc[train_idx], pop.iloc[test_idx], list(dict.fromkeys([*baseline, *present])), target, model="elasticnet")
        if not fit.get("ok"):
            continue
        enet_rows.append({"test_year": int(year), "n_test": fit["n_test"], **fit["coefs"]})
    enet = pd.DataFrame(enet_rows)
    enet.to_csv(OUT / f"elasticnet_path_{tag}.csv", index=False)
    return {"vif": vif_rows, "enet_folds": len(enet_rows)}


def permutation_last_fold(df: pd.DataFrame, features: list[str], target: str, permute: list[str], tag: str, n_repeats: int = 20) -> dict:
    folds = expanding_folds(df)
    if not folds:
        return {"ok": False}
    train_idx, test_idx, year = folds[-1]
    train, test = df.iloc[train_idx], df.iloc[test_idx]
    fit = fit_predict(train, test, features, target)
    if not fit.get("ok"):
        return {"ok": False}
    base_rmse = rmse(fit["y"], fit["pred"], fit["w"])
    rng = np.random.default_rng(RANDOM_SEED)
    cols = fit["features"]
    mask = test[cols].notna().all(axis=1) & test[target].notna()
    te = test.loc[mask].copy()
    est = fit["estimator"]
    rows = []
    wcol = "pa" if "pa" in te.columns else "ip"
    for feat in permute:
        if feat not in cols:
            continue
        deltas = []
        for _ in range(n_repeats):
            shuffled = te.copy()
            shuffled[feat] = rng.permutation(shuffled[feat].to_numpy())
            pred = est.predict(shuffled[cols])
            deltas.append(rmse(te[target].to_numpy(dtype=float), pred, np.clip(te[wcol].to_numpy(dtype=float), 1, None)) - base_rmse)
        rows.append(
            {
                "feature": feat,
                "test_year": int(year),
                "base_rmse": base_rmse,
                "mean_rmse_increase_on_permute": float(np.mean(deltas)),
                "n_repeats": n_repeats,
                "n_test": int(len(te)),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"permutation_{tag}.csv", index=False)
    return {"ok": True, "test_year": int(year), "rows": rows}


def stuff_audit(p: pd.DataFrame, seasons: pd.DataFrame, baseline: list[str]) -> dict:
    rel_all = year_to_year_reliability(seasons, "stuff_plus")
    rel_samp = year_to_year_reliability(p, "stuff_plus")
    cov = float(p["stuff_plus"].notna().mean()) if "stuff_plus" in p.columns else 0
    by_season = p.groupby("season")["stuff_plus"].apply(lambda s: float(s.notna().mean())).to_dict() if "stuff_plus" in p.columns else {}
    by_role = p.groupby("starter_role")["stuff_plus"].apply(lambda s: float(s.notna().mean())).to_dict() if "stuff_plus" in p.columns else {}
    inc_fip = incremental_oos(p, baseline, "stuff_plus", "y_fip") if "stuff_plus" in p.columns and "y_fip" in p.columns else {"ok": False}
    folds = []
    if inc_fip.get("ok"):
        folds = inc_fip["fold_table"].to_dict(orient="records")
    return {
        "reliability_definition": "Pearson correlation of stuff_plus in season t with stuff_plus in season t+1 on rows where both exist. Default function uses the unfiltered seasons table unless noted.",
        "reliability_unfiltered_seasons": rel_all,
        "reliability_modeling_sample": rel_samp,
        "coverage_modeling_sample": cov,
        "coverage_seasons_table": float(seasons["stuff_plus"].notna().mean()) if "stuff_plus" in seasons.columns else None,
        "coverage_seasons_n": int(len(seasons)),
        "coverage_modeling_n_observed": int(p["stuff_plus"].notna().sum()) if "stuff_plus" in p.columns else 0,
        "coverage_denominator_modeling": "pitcher modeling sample (role/IP filtered t and t+1), n=" + str(len(p)),
        "coverage_denominator_admission_engine": (
            "admit_feature calls coverage_profile on the unfiltered seasons table when the column exists. "
            "That denominator includes 2025 (no t→t+1 label) and all unfiltered pitcher-seasons. "
            "A 28% figure is therefore not the share of the 2,682-row modeling sample."
        ),
        "coverage_by_season_t": {int(k): v for k, v in by_season.items()},
        "coverage_by_role": {str(int(k)): v for k, v in by_role.items()},
        "available_score_seasons": [2023, 2024, 2025],
        "oos_fip": {
            "ok": inc_fip.get("ok"),
            "n_folds": inc_fip.get("n_folds"),
            "n": inc_fip.get("n"),
            "rmse_delta": inc_fip.get("rmse_delta"),
            "ci": inc_fip.get("boot", {}).get("rmse_ci") if inc_fip.get("ok") else None,
            "folds": folds,
        },
        "interpretation": (
            "Stuff+ is evaluated as a predictor of next-season FIP. "
            "Expanding-window Stuff+ scores use seasons ≤ t."
        ),
    }


def covid_sensitivity(h: pd.DataFrame, p: pd.DataFrame, h_base: list[str], p_base: list[str]) -> dict:
    def _run(df, base, target, feat):
        inc = incremental_oos(df, base, feat, target, do_bootstrap=False)
        return {
            "ok": inc.get("ok"),
            "n": inc.get("n"),
            "n_folds": inc.get("n_folds"),
            "rmse_delta": inc.get("rmse_delta"),
            "ci": inc.get("boot", {}).get("rmse_ci") if inc.get("ok") else None,
            "folds_improved": inc.get("folds_improved"),
        }

    def _drop_2020(df):
        return df[(df["season"] != COVID_YEAR) & (df["target_season"] != COVID_YEAR)].copy()

    out = {}
    for name, feat in [("xwoba_w2", "xwoba_w2"), ("ev", "ev"), ("xwoba", "xwoba")]:
        out[f"hitter_{name}_incl_2020"] = _run(h, h_base, "y_woba", feat)
        out[f"hitter_{name}_excl_2020_transitions"] = _run(_drop_2020(h), h_base, "y_woba", feat)
    for name, feat in [("k_bb_pct_w2", "k_bb_pct_w2"), ("k_pct", "k_pct"), ("whiff_rate", "whiff_rate"), ("avg_velo", "avg_velo"), ("fip_w2", "fip_w2"), ("stuff_plus", "stuff_plus")]:
        if feat not in p.columns:
            continue
        out[f"pitcher_{name}_incl_2020"] = _run(p, p_base, "y_fip", feat)
        out[f"pitcher_{name}_excl_2020_transitions"] = _run(_drop_2020(p), p_base, "y_fip", feat)
    hb = evaluate_features(h, h_base, "y_woba")
    hb2 = evaluate_features(_drop_2020(h), h_base, "y_woba")
    pb = evaluate_features(p, p_base, "y_fip")
    pb2 = evaluate_features(_drop_2020(p), p_base, "y_fip")
    out["hitter_baseline_rmse_incl"] = hb.get("mean_rmse")
    out["hitter_baseline_rmse_excl"] = hb2.get("mean_rmse")
    out["pitcher_baseline_rmse_incl"] = pb.get("mean_rmse")
    out["pitcher_baseline_rmse_excl"] = pb2.get("mean_rmse")
    out["hitter_n_incl"] = int(len(h))
    out["hitter_n_excl"] = int(len(_drop_2020(h)))
    out["pitcher_n_incl"] = int(len(p))
    out["pitcher_n_excl"] = int(len(_drop_2020(p)))
    return out


def gate_table(admission: pd.DataFrame, h: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in admission.iterrows():
        df = h if r.player_type == "hitter" else p
        base_rmse = r.baseline_rmse
        material = False
        if pd.notna(r.oos_rmse_delta) and pd.notna(base_rmse) and base_rmse:
            material = abs(r.oos_rmse_delta) >= MATERIAL_LIFT_FRAC * base_rmse and r.oos_rmse_delta < 0
        ci_good = pd.notna(r.oos_rmse_ci_high) and r.oos_rmse_ci_high < 0
        consistent = (r.folds_improved or 0) >= 0.6
        enough = (r.n_folds or 0) >= 3 or bool(ci_good)
        gate_a = bool(material and enough and (ci_good or consistent))
        if r.role in {"environment", "demographic"}:
            gate_a_label = "n/a (forced Context)"
        else:
            gate_a_label = "PASS" if gate_a else "FAIL"
        # B stability
        rel_ok = r.reliability_pearson is None or r.reliability_pearson >= 0.25 or r.role != "skill"
        coef_ok = (r.coef_sign_changes or 0) < 2
        gate_b = "PASS" if (rel_ok and coef_ok) else "FAIL"
        if r.reliability_pearson is not None and r.reliability_pearson < 0.25 and r.role == "skill":
            gate_b = "WEAK reliability"
        # C redundancy
        fam_red = bool(r.family_redundant) if "family_redundant" in r.index and pd.notna(r.family_redundant) else False
        gate_c = "FAMILY_REDUNDANT" if fam_red else "PASS"
        # D coverage
        cov = r.coverage or 0
        limited = cov < 0.70 or (bool(r.missing_systematic) and cov < 0.90)
        gate_d = "LIMITED" if limited else "PASS"
        # E subgroup — parse if json
        gate_e = "PASS"
        sub = r.subgroup
        if isinstance(sub, str) and sub.startswith("{"):
            try:
                sub = json.loads(sub)
            except json.JSONDecodeError:
                sub = {}
        if isinstance(sub, dict) and base_rmse:
            large = []
            for payload in sub.values():
                if not isinstance(payload, dict) or not payload.get("ok"):
                    continue
                if (payload.get("n") or 0) < 150 or payload.get("rmse_delta") is None:
                    continue
                large.append(payload["rmse_delta"])
            if len(large) >= 2:
                harmful = sum(d > MATERIAL_LIFT_FRAC * base_rmse for d in large)
                if harmful / len(large) >= 0.5:
                    gate_e = "FAIL"
        audit = r.verdict
        reason = ""
        if r.verdict == "Projection" and gate_a_label != "PASS" and r.role == "skill" and not r.get("extra"):
            audit = "REVIEW"
            reason = "Projection label but Gate A reconstruction failed"
        if r.feature == "extension" and (r.n_folds or 0) < 3:
            reason = (reason + " " if reason else "") + "Only one OOS fold; treat as insufficient evidence for a stable Projection-class claim even if Augmented."
        if r.feature == "stuff_plus":
            reason = "Stuff+ is evaluated as a predictor of next-season FIP."
        if r.feature in {"k_pct", "bb_pct", "k_bb_pct"} and r.player_type == "pitcher":
            reason = "Deterministic K-BB% = K% − BB%. Do not treat as three independent sources."
        if r.feature == "k_bb_pct_z":
            reason = "League-year z of current K-BB%; collinear with current K-BB% up to a season-level location/scale. Audit whether it adds more than a season intercept."
        if r.feature == "avg_velo" and pd.notna(r.oos_rmse_ci_high) and r.oos_rmse_ci_high >= 0:
            reason = "CI includes zero; Projection rests on fold-consistency (5/7) and barely-material mean delta."
        if r.feature == "woba_w3" and pd.notna(r.oos_rmse_ci_high) and r.oos_rmse_ci_high >= -1e-6:
            reason = "CI upper bound is essentially zero; Projection is marginal."
        rows.append(
            {
                "Metric": f"{r.player_type}:{r.get('component', '')}:{r.get('target', '')}:{r.feature}",
                "Current Verdict": r.verdict,
                "Gate A": gate_a_label,
                "Gate B": gate_b,
                "Gate C": gate_c,
                "Gate D": gate_d,
                "Gate E": gate_e,
                "Audit Verdict": audit,
                "Changed?": "pending",
                "Reason": reason or r.rationale,
                "oos_rmse_delta": r.oos_rmse_delta,
                "n_folds": r.n_folds,
                "coverage": r.coverage,
                "reliability_pearson": r.reliability_pearson,
            }
        )
    return pd.DataFrame(rows)


def component_revision_audit(admission: pd.DataFrame, issues: list[str]) -> dict:
    rec: dict = {}
    need = {"component", "target", "feature", "verdict", "player_type"}
    missing = need - set(admission.columns)
    if missing:
        _fail(issues, f"admission table missing component schema columns: {sorted(missing)}")
        return rec
    dups = int(admission.duplicated(["player_type", "component", "target", "feature"]).sum())
    rec["duplicate_keys"] = dups
    if dups:
        _fail(issues, f"admission table has {dups} duplicate (player_type, component, target, feature) rows")
    if (admission["target"] == "y_errors").any():
        _fail(issues, "official errors used as a modeling target")

    def _v(pt, comp, tgt, feat):
        sub = admission[
            admission.player_type.eq(pt)
            & admission.component.eq(comp)
            & admission.target.eq(tgt)
            & admission.feature.eq(feat)
        ]
        return None if sub.empty else str(sub.iloc[0]["verdict"])

    expected = [
        ("hitter", "hitting", "y_woba", "xwoba_w2", "Projection"),
        ("hitter", "hitting", "y_woba", "ev", "Projection"),
        ("hitter", "hitting", "y_woba", "sprint_speed", "Diagnostic"),
        ("hitter", "hitting", "y_woba", "woba", "Exclude"),
        ("hitter", "baserunning", "y_br_rv_rate", "sprint_speed", "Projection"),
        ("pitcher", "pitching", "y_fip", "stuff_plus", "Projection"),
        ("hitter", "defense", "y_def_rv_rate", "errors", "Diagnostic"),
        ("hitter", "defense", "y_def_rv_rate", "def_rv_rate_w2", "Projection"),
        ("hitter", "hitting", "y_woba", "barrel_pct", "Diagnostic"),
        ("hitter", "hitting", "y_woba", "o_swing_pct", "Diagnostic"),
    ]
    got = {}
    for pt, comp, tgt, feat, exp in expected:
        v = _v(pt, comp, tgt, feat)
        got[f"{pt}:{comp}:{tgt}:{feat}"] = v
        if v != exp:
            _fail(issues, f"{feat} under {comp}/{tgt} expected {exp}, got {v}")
    rec["verdict_locks"] = got

    idx = RESEARCH_DIR / "index.html"
    rec["website_present"] = idx.exists()
    if idx.exists():
        text = idx.read_text()
        if "A metric does not have one universal role" not in text:
            _fail(issues, "findings page missing the target-dependence lede")
        if "Stuff+ is Diagnostic—useful pitch quality, not a projection input" in text:
            _fail(issues, "findings still treat Stuff+ Diagnostic-for-K-BB% as the primary pitcher headline")
        if "next-season FIP" not in text:
            _fail(issues, "findings page does not name next-season FIP")
        if "next-season K-BB%" in text or "next season K-BB%" in text:
            _fail(issues, "findings page still treats next-season K-BB% as a target")
        if "Sprint Speed was Diagnostic" in text and "baserunning" not in text.lower():
            _fail(issues, "Sprint Speed hitting Diagnostic is stated without baserunning contrast")
        forbidden = ("Sprint Speed is Diagnostic.", "Velocity is Diagnostic for FIP.")
        for needle in forbidden:
            if needle in text:
                _fail(issues, f"findings contain universal verdict language: {needle}")
    rec["n_rows"] = int(len(admission))
    rec["studies"] = (
        admission.groupby(["component", "target"]).size().rename("n").reset_index().assign(
            key=lambda d: d.component.astype(str) + "|" + d.target.astype(str)
        )
        .set_index("key")["n"]
        .astype(int)
        .to_dict()
        if "component" in admission.columns
        else {}
    )
    return rec


def public_target_hygiene(admission: pd.DataFrame, issues: list[str]) -> dict:
    rec: dict = {}
    targets = set(admission["target"].astype(str).dropna().unique()) if "target" in admission.columns else set()
    rec["canonical_targets"] = sorted(targets)
    if any("k_bb" in t.lower() or "kbb" in t.lower() for t in targets):
        _fail(issues, f"canonical target contains K-BB: {sorted(targets)}")
    expected = {"y_woba", "y_fip", "y_br_rv_rate", "y_def_rv_rate", "y_war_rate"}
    if targets != expected:
        _fail(issues, f"canonical targets {sorted(targets)} != {sorted(expected)}")
    n_studies = int(admission.groupby(["component", "target"]).ngroups) if {"component", "target"} <= set(admission.columns) else 0
    rec["n_public_component_studies"] = n_studies
    if n_studies != 5:
        _fail(issues, f"number of public component studies is {n_studies}, expected 5")
    pit = admission[admission.component.eq("pitching")] if "component" in admission.columns else admission.iloc[0:0]
    rec["pitching_targets"] = sorted(pit["target"].astype(str).unique()) if len(pit) else []
    if set(rec["pitching_targets"]) != {"y_fip"}:
        _fail(issues, f"pitching primary target must be FIP only, got {rec['pitching_targets']}")
    pitch_feats = set(pit["feature"].astype(str)) if len(pit) else set()
    rec["kbb_feature_present"] = "k_bb_pct" in pitch_feats
    if not rec["kbb_feature_present"]:
        _fail(issues, "K-BB% missing from the pitching candidate feature universe")
    needles = ("next-season K-BB%", "next season K-BB%", "target_kbb", "kbb_target")
    public_hits = []
    if RESEARCH_DIR.exists():
        for path in RESEARCH_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".md", ".js", ".csv"}:
                continue
            text = path.read_text(errors="ignore")
            for needle in needles:
                if needle in text:
                    public_hits.append(f"{path.relative_to(RESEARCH_DIR)}:{needle}")
    rec["public_forbidden_hits"] = public_hits
    if public_hits:
        _fail(issues, "public site still contains a K-BB% target string: " + "; ".join(public_hits[:8]))
    model_hits = []
    for path in list(ARTIFACTS.glob("model_comparison*")) + list(ARTIFACTS.glob("kitchen_sink_comparison*")):
        blob = ""
        if path.suffix in {".csv", ".json"}:
            blob = path.read_text(errors="ignore")
        elif path.suffix == ".parquet":
            try:
                df = pd.read_parquet(path)
                blob = " ".join(map(str, df.columns))
                if "target" in df.columns:
                    blob += " " + " ".join(df["target"].astype(str).unique())
            except Exception:
                blob = ""
        if "y_k_bb_pct" in blob or "next-season K-BB%" in blob:
            model_hits.append(path.name)
    rec["model_kbb_outcome_files"] = model_hits
    if model_hits:
        _fail(issues, "public model comparison still uses K-BB% as an outcome: " + ", ".join(model_hits))
    return rec


FROZEN_VERDICTS = (
    ("hitter", "xwoba_w2", "hitting", "y_woba", "Projection"),
    ("hitter", "ev", "hitting", "y_woba", "Projection"),
    ("hitter", "woba_w2", "hitting", "y_woba", "Projection"),
    ("hitter", "sprint_speed", "hitting", "y_woba", "Diagnostic"),
    ("hitter", "sprint_speed", "baserunning", "y_br_rv_rate", "Projection"),
    ("pitcher", "stuff_plus", "pitching", "y_fip", "Projection"),
)


def future_relationship_audit(admission: pd.DataFrame, issues: list[str]) -> dict:
    rec: dict = {}
    needed = [
        "future_pearson_r",
        "future_spearman_rho",
        "partial_future_r",
        "future_pearson_r_pooled",
        "correlation_n",
        "correlation_folds",
        "correlation_direction_label",
        "dropone_oos_rmse",
        "oos_rmse_delta",
    ]
    missing = [c for c in needed if c not in admission.columns]
    rec["missing_columns"] = missing
    if missing:
        _fail(issues, f"admission table missing relationship columns: {missing}")
        return rec
    rec["n_with_pearson"] = int(admission["future_pearson_r"].notna().sum())
    rec["n_with_n"] = int(admission["correlation_n"].notna().sum())
    if rec["n_with_pearson"] < 50:
        _fail(issues, f"too few future Pearson values: {rec['n_with_pearson']}")
    if rec["n_with_n"] < rec["n_with_pearson"]:
        _fail(issues, "correlation_n missing on rows that have future Pearson r")

    frozen = []
    for pt, feat, comp, tgt, verdict in FROZEN_VERDICTS:
        sub = admission[
            admission.player_type.eq(pt)
            & admission.feature.eq(feat)
            & admission.component.eq(comp)
            & admission.target.eq(tgt)
        ]
        got = None if sub.empty else str(sub.iloc[0]["verdict"])
        frozen.append({"key": [pt, feat, comp, tgt], "expected": verdict, "got": got})
        if got != verdict:
            _fail(issues, f"verdict changed for {pt}/{feat}/{comp}/{tgt}: expected {verdict}, got {got}")
    rec["frozen_verdicts"] = frozen

    xw = admission[admission.player_type.eq("hitter") & admission.feature.eq("xwoba_w2") & admission.target.eq("y_woba")]
    if xw.empty:
        _fail(issues, "missing 2-Year xwOBA vs next-season wOBA row")
    else:
        delta = float(xw.iloc[0]["oos_rmse_delta"])
        rec["xwoba_w2_oos_rmse_delta"] = delta
        if abs(delta + 0.000931) > 5e-6:
            _fail(issues, f"xwOBA ΔRMSE changed: {delta}")

    h = pd.read_parquet(DATA_PROCESSED / "hitter_sample_pa150.parquet")
    p = pd.read_parquet(DATA_PROCESSED / "pitcher_sample_role_ip.parquet")
    if not (h["target_season"] == h["season"] + 1).all():
        _fail(issues, "hitter sample is not year-t features vs t+1 outcomes")
    if not (p["target_season"] == p["season"] + 1).all():
        _fail(issues, "pitcher sample is not year-t features vs t+1 outcomes")

    def _pooled(sample: pd.DataFrame, feature: str, target: str) -> float | None:
        if feature not in sample.columns or target not in sample.columns:
            return None
        pair = sample[[feature, target]].dropna()
        if len(pair) < 20:
            return None
        return float(pearsonr(pair[feature], pair[target])[0])

    checks = [
        (h, "hitter", "xwoba_w2", "hitting", "y_woba"),
        (h, "hitter", "ops", "hitting", "y_woba"),
        (p, "pitcher", "avg_velo", "pitching", "y_fip"),
        (p, "pitcher", "stuff_plus", "pitching", "y_fip"),
    ]
    pooled_ok = []
    for sample, pt, feat, comp, tgt in checks:
        row = admission[
            admission.player_type.eq(pt) & admission.feature.eq(feat) & admission.component.eq(comp) & admission.target.eq(tgt)
        ]
        if row.empty:
            _fail(issues, f"missing relationship row {pt}/{feat}")
            continue
        stored = row.iloc[0]["future_pearson_r_pooled"]
        computed = _pooled(sample, feat, tgt)
        rec[f"pooled_{pt}_{feat}"] = {"stored": None if pd.isna(stored) else float(stored), "computed": computed}
        if computed is None or pd.isna(stored) or abs(float(stored) - computed) > 1e-8:
            _fail(issues, f"pooled future r mismatch for {pt}/{feat}")
        else:
            pooled_ok.append(feat)
    rec["pooled_matches"] = pooled_ok

    velo = admission[admission.player_type.eq("pitcher") & admission.feature.eq("avg_velo") & admission.target.eq("y_fip")]
    if velo.empty or pd.isna(velo.iloc[0]["future_pearson_r"]):
        _fail(issues, "missing Average Velocity future correlation vs FIP")
    else:
        r_velo = float(velo.iloc[0]["future_pearson_r"])
        rec["avg_velo_future_r"] = r_velo
        if r_velo >= 0:
            _fail(issues, f"Average Velocity vs future FIP should be negative, got {r_velo}")
        label = str(velo.iloc[0].get("correlation_direction_label") or "")
        rec["avg_velo_label"] = label
        if "better" not in label.lower():
            _fail(issues, "FIP velocity copy does not explain that negative r can be better FIP")
        if "%" in label and "percent" in label.lower():
            _fail(issues, "correlation label interprets r as a percentage")

    method_path = ARTIFACTS / "future_relationships_method.json"
    rec["method_exists"] = method_path.exists()
    if not method_path.exists():
        _fail(issues, "missing artifacts/future_relationships_method.json")
    else:
        method = json.loads(method_path.read_text())
        rec["headline"] = (method.get("method") or {}).get("headline")
        if rec["headline"] != "fisher_z_mean_of_expanding_window_validation_folds":
            _fail(issues, f"unexpected correlation headline method: {rec['headline']}")

    forbidden = ("40% predictive", "affects wOBA by", "% predictive", "is 40% predictive")
    public_hits = []
    if RESEARCH_DIR.exists():
        for path in RESEARCH_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".html", ".md"}:
                continue
            text = path.read_text(errors="ignore")
            for needle in forbidden:
                if needle in text:
                    public_hits.append(f"{path.relative_to(RESEARCH_DIR)}:{needle}")
            if path.name in {"hitters.html", "pitchers.html", "baserunning.html", "defense.html", "overall.html"}:
                if "Correlation is not admission" not in text:
                    public_hits.append(f"{path.name}:missing correlation callout")
    rec["public_language_hits"] = public_hits
    if public_hits:
        _fail(issues, "public correlation language failed: " + "; ".join(public_hits[:8]))

    heat = ARTIFACTS / "figures" / "heatmap_hitter.html"
    if heat.exists():
        heat_txt = heat.read_text(errors="ignore")
        rec["heatmap_has_predictive_value"] = "Future Prediction" in heat_txt
        rec["heatmap_hover_compact"] = "INCREMENTAL PREDICTIVE VALUE" not in heat_txt and "WHY<br>" not in heat_txt
        if "Future Prediction" not in heat_txt:
            _fail(issues, "admission heatmap lost the Future Prediction criterion")
        if "INCREMENTAL PREDICTIVE VALUE" in heat_txt or "WHY<br>" in heat_txt:
            _fail(issues, "admission heatmap hover is no longer compact")
    return rec


def main() -> None:
    issues: list[str] = []
    h = pd.read_parquet(DATA_PROCESSED / "hitter_sample_pa150.parquet")
    p = pd.read_parquet(DATA_PROCESSED / "pitcher_sample_role_ip.parquet")
    hs = pd.read_parquet(DATA_PROCESSED / "hitter_seasons.parquet")
    ps = pd.read_parquet(DATA_PROCESSED / "pitcher_seasons.parquet")
    admission = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    h_base = list(HITTER_BASELINE)
    p_base = list(PITCHER_BASELINE)
    h_weak = list(HITTER_BASELINE_WEAK)
    p_weak = list(PITCHER_BASELINE_WEAK)

    print("1. sample identity")
    ident = sample_identity(h, p, issues)
    ident["uniqueness"] = uniqueness_tables(issues)
    ident["ip_parse"] = ip_parse_audit(p, issues)

    print("2. leakage")
    leak = leakage_audit(h, p, hs, ps, issues)

    print("3. folds")
    hf = fold_table(h, "hitter")
    pf = fold_table(p, "pitcher")
    if hf["leak_train_includes_val"].any() or pf["leak_train_includes_val"].any():
        _fail(issues, "A temporal fold has train seasons overlapping the validation feature season")

    print("4. xwOBA reproduction")
    xw_weak = signed_oos(h, h_weak, ["xwoba"], "y_woba", "xwoba_vs_weak")
    xw_strong = signed_oos(h, h_base, ["xwoba"], "y_woba", "xwoba_vs_strong")
    xw2 = signed_oos(h, h_base, ["xwoba_w2"], "y_woba", "xwoba_w2_vs_strong")
    dump_oos(xw_weak, "xwoba_vs_weak_baseline")
    dump_oos(xw_strong, "xwoba_vs_strong_baseline")
    dump_oos(xw2, "xwoba_w2_vs_strong_baseline")
    conditionals = {}
    for label, extra_base in [
        ("vs_base_plus_ev", h_base + ["ev"]),
        ("vs_base_plus_barrel", h_base + ["barrel_pct"]),
        ("vs_base_plus_hardhit", h_base + ["hard_hit_pct"]),
        ("vs_base_plus_ev_barrel_hardhit", h_base + ["ev", "barrel_pct", "hard_hit_pct"]),
        ("vs_base_plus_admitted_non_xwoba", h_base + ["ev", "woba_w3"]),
    ]:
        extra_base = [c for c in extra_base if c in h.columns]
        payload = signed_oos(h.dropna(subset=["xwoba"] + extra_base), extra_base, ["xwoba"], "y_woba", label)
        dump_oos(payload, f"xwoba_{label}")
        conditionals[label] = {k: payload.get(k) for k in ["ok", "mean_delta", "median_delta", "n_folds", "folds_improved", "boot_ci_low", "boot_ci_high", "n"]}
    xw2_vs_admitted = signed_oos(h.dropna(subset=["xwoba_w2", "ev", "woba_w3"]), h_base + ["ev", "woba_w3"], ["xwoba_w2"], "y_woba", "xwoba_w2_vs_other_admitted")
    dump_oos(xw2_vs_admitted, "xwoba_w2_vs_other_admitted")

    print("5. hitter contact-quality family")
    cq = h[["ev", "hard_hit_pct", "barrel_pct", "xwoba", "xwoba_w2", "y_woba"]].dropna()
    corr = cq.corr()
    corr.to_csv(OUT / "hitter_contact_corr.csv")
    year_corrs = []
    for yr, g in h.groupby("season"):
        c = g[["ev", "hard_hit_pct", "barrel_pct", "xwoba"]].corr()
        year_corrs.append({"season": int(yr), "ev_hardhit": c.loc["ev", "hard_hit_pct"], "ev_barrel": c.loc["ev", "barrel_pct"], "hardhit_barrel": c.loc["hard_hit_pct", "barrel_pct"], "xwoba_ev": c.loc["xwoba", "ev"], "xwoba_barrel": c.loc["xwoba", "barrel_pct"]})
    pd.DataFrame(year_corrs).to_csv(OUT / "hitter_contact_corr_by_year.csv", index=False)
    loo = {}
    family = ["ev", "hard_hit_pct", "barrel_pct", "xwoba"]
    pop = h.dropna(subset=family)
    full = evaluate_features(pop, h_base + family, "y_woba")
    for feat in family:
        others = [f for f in family if f != feat]
        loo_ev = evaluate_features(pop, h_base + others, "y_woba")
        loo[feat] = {
            "full_rmse": full.get("mean_rmse"),
            "without_rmse": loo_ev.get("mean_rmse"),
            "delta_full_minus_without": (full["mean_rmse"] - loo_ev["mean_rmse"]) if full.get("ok") and loo_ev.get("ok") else None,
        }
    addone = {}
    for feat in family:
        addone[feat] = {k: signed_oos(h, h_base, [feat], "y_woba", feat).get(k) for k in ["mean_delta", "n_folds", "folds_improved", "boot_ci_low", "boot_ci_high"]}
    contact_diag = vif_and_enet(h, h_base, family, "y_woba", "hitter_contact")
    perm_contact = permutation_last_fold(h.dropna(subset=family), h_base + family, "y_woba", family, "hitter_contact")
    admitted_h_feats = ["xwoba_w2", "ev", "woba_w3"]
    admitted_diag = vif_and_enet(h, h_base, admitted_h_feats, "y_woba", "hitter_admitted")
    perm_admitted = permutation_last_fold(h.dropna(subset=admitted_h_feats), h_base + admitted_h_feats, "y_woba", admitted_h_feats, "hitter_admitted")

    print("6. pitcher K-BB identities")
    kbb_pop = p.dropna(subset=["k_pct", "bb_pct", "k_bb_pct"]).copy()
    identity_err = float((kbb_pop["k_bb_pct"] - (kbb_pop["k_pct"] - kbb_pop["bb_pct"])).abs().median())
    kbb_specs = {
        "A_kbb_only": ["k_bb_pct"],
        "B_k_and_bb": ["k_pct", "bb_pct"],
        "C_kbb_plus_k": ["k_bb_pct", "k_pct"],
        "D_kbb_plus_bb": ["k_bb_pct", "bb_pct"],
        "E_all_three": ["k_bb_pct", "k_pct", "bb_pct"],
        "F_kbb_w2_only": ["k_bb_pct_w2"],
        "G_kbb_w2_plus_k": ["k_bb_pct_w2", "k_pct"],
        "H_kbb_w2_plus_k_bb": ["k_bb_pct_w2", "k_pct", "bb_pct"],
    }
    kbb_results = {"identity_median_abs_error": identity_err}
    # compare each spec vs a baseline WITHOUT k_bb history so A–E are fair; then vs strong baseline
    p_core = ["age", "ip", "starter_role", "park_factor"]
    for name, feats in kbb_specs.items():
        ev = evaluate_features(kbb_pop, p_core + feats, "y_fip")
        kbb_results[name] = {"mean_rmse": ev.get("mean_rmse"), "mean_mae": ev.get("mean_mae"), "ok": ev.get("ok"), "features": feats}
    pd.DataFrame(
        [{"spec": k, **{kk: vv for kk, vv in v.items() if kk != "features"}, "features": ",".join(v.get("features") or [])} for k, v in kbb_results.items() if isinstance(v, dict) and "mean_rmse" in v]
    ).to_csv(OUT / "pitcher_kbb_identity_specs.csv", index=False)
    # vs strong baseline (already has k_bb_w2)
    for name, feats in {
        "k_vs_strong": ["k_pct"],
        "bb_vs_strong": ["bb_pct"],
        "kbb_vs_strong": ["k_bb_pct"],
        "k_and_bb_vs_strong": ["k_pct", "bb_pct"],
    }.items():
        payload = signed_oos(kbb_pop, p_base if name != "k_and_bb_vs_strong" else p_base, feats[:1] if len(feats) == 1 else feats, "y_fip", name) if len(feats) == 1 else signed_oos(kbb_pop, p_base, feats, "y_fip", name)
        dump_oos(payload, name)
        kbb_results[name + "_delta"] = {k: payload.get(k) for k in ["mean_delta", "n_folds", "boot_ci_low", "boot_ci_high", "ok"]}
    kbb_diag = vif_and_enet(p, p_core, ["k_bb_pct", "k_pct", "bb_pct"], "y_fip", "pitcher_kbb")

    print("7. tracking same-population")
    tracking = {}
    for feat in ["avg_velo", "avg_spin", "whiff_rate", "z_contact_pct", "ff_velo", "extension", "stuff_plus"]:
        if feat not in p.columns:
            continue
        sub = p[p[feat].notna()].copy()
        by_s = p.groupby("season")[feat].apply(lambda s: float(s.notna().mean())).to_dict()
        by_r = p.groupby("starter_role")[feat].apply(lambda s: float(s.notna().mean())).to_dict()
        inc = incremental_oos(p, p_base, feat, "y_fip")
        after_k = signed_oos(p.dropna(subset=[feat, "k_pct", "bb_pct"]), list(dict.fromkeys([*p_base, "k_pct", "bb_pct"])), [feat], "y_fip", f"{feat}_after_kbb")
        after_stuff = None
        if feat != "stuff_plus" and p["stuff_plus"].notna().any():
            after_stuff = signed_oos(p.dropna(subset=[feat, "stuff_plus"]), list(dict.fromkeys([*p_base, "stuff_plus"])), [feat], "y_fip", f"{feat}_after_stuff")
        tracking[feat] = {
            "coverage": float(p[feat].notna().mean()),
            "coverage_by_season": {int(k): v for k, v in by_s.items()},
            "coverage_by_role": {str(int(k)): v for k, v in by_r.items()},
            "same_pop_n": inc.get("n"),
            "n_folds": inc.get("n_folds"),
            "rmse_delta": inc.get("rmse_delta"),
            "ci": inc.get("boot", {}).get("rmse_ci") if inc.get("ok") else None,
            "after_k_pct": {k: after_k.get(k) for k in ["mean_delta", "boot_ci_low", "boot_ci_high", "n"]},
            "after_stuff_plus_same_pop": None if not after_stuff else {k: after_stuff.get(k) for k in ["mean_delta", "boot_ci_low", "boot_ci_high", "n", "n_folds"]},
            "reliability": year_to_year_reliability(ps, feat),
        }

    print("8. Stuff+")
    stuff = stuff_audit(p, ps, p_base)

    print("9. 2020")
    covid = covid_sensitivity(h, p, h_base, p_base)
    (OUT / "covid_sensitivity.json").write_text(json.dumps(covid, indent=2, default=str))

    print("10-12. kitchen sink with train-only impute")
    h_admitted = list(dict.fromkeys([*h_base, "xwoba_w2", "ev", "woba_w3"]))
    fip_mask = admission.player_type.eq("pitcher") & admission.verdict.eq("Projection")
    if "target" in admission.columns:
        fip_mask &= admission.target.eq("y_fip")
    if "component" in admission.columns:
        fip_mask &= admission.component.fillna("pitching").eq("pitching")
    fip_proj = admission.loc[fip_mask, "feature"].tolist()
    p_admitted = list(dict.fromkeys([*p_base, *[f for f in fip_proj if f not in p_base]]))
    if len(p_admitted) <= len(p_base):
        p_admitted = list(dict.fromkeys([*p_base, "k_bb_pct_w3", "k_pct", "stuff_plus", "ff_velo", "extension"]))
    h_skill = admission[(admission.player_type == "hitter") & (admission.role == "skill")]
    if "component" in h_skill.columns:
        h_skill = h_skill[h_skill.component.eq("hitting") | h_skill.component.isna()]
    h_skill = h_skill.feature.tolist()
    p_skill = admission[(admission.player_type == "pitcher") & (admission.role == "skill")]
    if "target" in p_skill.columns:
        p_skill = p_skill[p_skill.target.eq("y_fip")]
    p_skill = p_skill.feature.tolist()
    h_kitchen = list(dict.fromkeys([*h_base, *[f for f in h_skill if f in h.columns]]))
    p_kitchen = list(dict.fromkeys([*p_base, *[f for f in p_skill if f in p.columns]]))
    h_adm_ev = evaluate_features(h, h_admitted, "y_woba")
    p_adm_ev = evaluate_features(p, p_admitted, "y_fip")
    h_adm_imp = evaluate_imputed(h, h_admitted, "y_woba")
    p_adm_imp = evaluate_imputed(p, p_admitted, "y_fip")
    h_kit = evaluate_imputed(h, h_kitchen, "y_woba")
    p_kit = evaluate_imputed(p, p_kitchen, "y_fip")
    h_kit_old = pd.read_csv(ARTIFACTS / "model_comparison_hitter.csv")
    p_kit_old = pd.read_csv(ARTIFACTS / "model_comparison_pitcher.csv")
    h_cmp = compare_models_foldwise(h_adm_ev, h_kit, "admitted", "kitchen")
    p_cmp = compare_models_foldwise(p_adm_ev, p_kit, "admitted", "kitchen")
    h_cmp_fair = compare_models_foldwise(h_adm_imp, h_kit, "admitted_imputed", "kitchen")
    p_cmp_fair = compare_models_foldwise(p_adm_imp, p_kit, "admitted_imputed", "kitchen")
    pd.DataFrame(h_cmp.get("folds") or []).to_csv(OUT / "kitchen_vs_admitted_hitter_folds.csv", index=False)
    pd.DataFrame(p_cmp.get("folds") or []).to_csv(OUT / "kitchen_vs_admitted_pitcher_folds.csv", index=False)
    pd.DataFrame(h_cmp_fair.get("folds") or []).to_csv(OUT / "kitchen_vs_admitted_imputed_hitter_folds.csv", index=False)
    pd.DataFrame(p_cmp_fair.get("folds") or []).to_csv(OUT / "kitchen_vs_admitted_imputed_pitcher_folds.csv", index=False)

    print("14. subgroups")
    sub_rows = []
    for feat, df, base, tgt, pt in [
        ("xwoba_w2", h, h_base, "y_woba", "hitter"),
        ("ev", h, h_base, "y_woba", "hitter"),
        ("xwoba", h, h_base, "y_woba", "hitter"),
        ("k_pct", p, p_base, "y_fip", "pitcher"),
        ("whiff_rate", p, p_base, "y_fip", "pitcher"),
        ("avg_velo", p, p_base, "y_fip", "pitcher"),
        ("avg_spin", p, p_base, "y_fip", "pitcher"),
        ("z_contact_pct", p, p_base, "y_fip", "pitcher"),
        ("stuff_plus", p, p_base, "y_fip", "pitcher"),
    ]:
        sg = subgroup_oos(df, base, feat, tgt, pt)
        for gname, payload in sg.items():
            sub_rows.append({"player_type": pt, "feature": feat, "group": gname, **{k: payload.get(k) for k in ["ok", "n", "rmse_delta", "folds_improved"]}})
    pd.DataFrame(sub_rows).to_csv(OUT / "subgroup_oos_recompute.csv", index=False)

    print("13. gate table")
    gates = gate_table(admission, h, p)
    # apply audit verdict changes from this run
    changes = []
    # xwoba vs family already Diagnostic
    # avg_velo CI includes 0
    # stuff+ insufficient
    # k_bb_pct_z maybe diagnostic if we find it's a season dummy
    kbbz = signed_oos(p, p_base, ["k_bb_pct_z"], "y_fip", "kbbz")
    dump_oos(kbbz, "k_bb_pct_z_recompute")
    # season dummies vs z
    p2 = p.copy()
    p2["season_num"] = p2["season"].astype(float)
    season_fe = evaluate_features(p2, p_base + ["season_num"], "y_fip")

    def _set_audit(metric, new, reason, changed=True):
        m = gates["Metric"] == metric
        gates.loc[m, "Audit Verdict"] = new
        gates.loc[m, "Changed?"] = "yes" if changed else "no"
        if reason:
            gates.loc[m, "Reason"] = reason
        changes.append({"metric": metric, "audit_verdict": new, "reason": reason})

    gates["Changed?"] = np.where(gates["Audit Verdict"] != gates["Current Verdict"], "yes", "no")
    _set_audit(
        "hitter:hitting:y_woba:woba_w3",
        "Projection (marginal)",
        "CI upper bound is ~0. Incremental lift vs 2-year wOBA is small. Not wrong, but not a headline-quality third wOBA term.",
        changed=False,
    )
    _set_audit(
        "pitcher:pitching:y_fip:k_pct",
        "Projection as decomposition of K-BB%, not a third source",
        f"K-BB% = K% − BB% (median abs error {identity_err}). Do not list K%, BB%, and K-BB% as three independent Projection inputs.",
        changed=False,
    )
    _set_audit(
        "hitter:hitting:y_woba:o_swing_pct",
        "Diagnostic (process: chase / plate discipline)",
        "Measures swings at pitches outside the zone. Incremental next-wOBA lift is below materiality vs the history-aware baseline. Keep Diagnostic for hitting, not Exclude.",
        changed=False,
    )
    _set_audit(
        "hitter:hitting:y_woba:sprint_speed",
        "Diagnostic for next-season wOBA",
        "Year-to-year r≈0.92. Does not improve next-season wOBA. That is not a universal Sprint Speed verdict.",
        changed=False,
    )

    gates["Changed?"] = np.where(
        gates["Audit Verdict"].astype(str).str.split().str[0].str.lower()
        != gates["Current Verdict"].astype(str).str.split().str[0].str.lower(),
        "yes",
        "no",
    )
    # After public revision, Insufficient Evidence / Diagnostic on the named pitcher
    # metrics should match the canonical table (first token).
    gates.to_csv(ARTIFACTS / "audit_verdicts.csv", index=False)
    gates.to_csv(OUT / "audit_verdicts.csv", index=False)

    # number tracing
    prose = {
        "2836": ident["hitter"]["n_rows"],
        "2682": ident["pitcher"]["n_rows"],
        "0.00121": "STALE — pre-universe-audit xwOBA vs weak baseline; not in current README. Recomputed xwoba_vs_weak mean_delta=" + str(xw_weak.get("mean_delta")),
        "7/7": {"xwoba_w2_folds_improved": xw2.get("folds_improved"), "xwoba_vs_weak": xw_weak.get("folds_improved")},
        "0.00013": "STALE — pre-audit chase vs weak baseline. Current o_swing vs strong is in admission_table.",
        "0.83": stuff["reliability_unfiltered_seasons"].get("pearson"),
        "28%": "STALE seasons-table Stuff+ coverage from the frozen 2023–2025 file. Current expanding-window modeling-sample coverage is "
        + str(stuff["coverage_modeling_sample"])
        + ".",
        "33 features": "STALE — pre-universe kitchen sink. Current skill-role kitchen is %d hitters / %d pitchers; admitted core %d / %d."
        % (len(h_kitchen), len(p_kitchen), len(h_admitted), len(p_admitted)),
        "0.000931": xw2.get("mean_delta"),
    }

    print("15. component revision schema")
    component = component_revision_audit(admission, issues)
    print("16. public target hygiene")
    hygiene = public_target_hygiene(admission, issues)
    print("17. future relationship hygiene")
    relationships = future_relationship_audit(admission, issues)

    summary = {
        "component_revision": component,
        "public_target_hygiene": hygiene,
        "future_relationships": relationships,
        "built_at": _now(),
        "issues": issues,
        "identity": ident,
        "leakage": leak,
        "folds_hitter": hf.to_dict(orient="records"),
        "folds_pitcher": pf.to_dict(orient="records"),
        "xwoba_vs_weak": {k: xw_weak.get(k) for k in ["ok", "mean_delta", "median_delta", "n_folds", "folds_improved", "boot_rmse_delta", "boot_ci_low", "boot_ci_high", "boot_mae_delta", "n"]},
        "xwoba_vs_strong": {k: xw_strong.get(k) for k in ["ok", "mean_delta", "median_delta", "n_folds", "folds_improved", "boot_rmse_delta", "boot_ci_low", "boot_ci_high", "n"]},
        "xwoba_w2_vs_strong": {k: xw2.get(k) for k in ["ok", "mean_delta", "median_delta", "n_folds", "folds_improved", "boot_rmse_delta", "boot_ci_low", "boot_ci_high", "n"]},
        "xwoba_conditionals": conditionals,
        "xwoba_w2_vs_other_admitted": {k: xw2_vs_admitted.get(k) for k in ["ok", "mean_delta", "median_delta", "boot_ci_low", "boot_ci_high", "n_folds"]},
        "contact_corr": corr.to_dict(),
        "contact_loo": loo,
        "contact_addone": addone,
        "contact_vif_enet": contact_diag,
        "contact_perm": perm_contact,
        "admitted_hitter_vif_enet": admitted_diag,
        "admitted_hitter_perm": perm_admitted,
        "kbb": kbb_results,
        "kbb_vif_enet": kbb_diag,
        "tracking": tracking,
        "stuff": stuff,
        "covid": covid,
        "kitchen": {
            "hitter_admitted_rmse": h_adm_ev.get("mean_rmse"),
            "hitter_admitted_mae": h_adm_ev.get("mean_mae"),
            "hitter_admitted_p": len(h_admitted),
            "hitter_kitchen_rmse_trainonly_impute": h_kit.get("mean_rmse"),
            "hitter_kitchen_mae": h_kit.get("mean_mae"),
            "hitter_kitchen_p": h_kit.get("n_features"),
            "hitter_old_csv": h_kit_old.to_dict(orient="records"),
            "hitter_cmp": {k: h_cmp.get(k) for k in ["mean_delta", "median_delta", "boot", "n_common_preds", "sign"]},
            "pitcher_admitted_rmse": p_adm_ev.get("mean_rmse"),
            "pitcher_admitted_mae": p_adm_ev.get("mean_mae"),
            "pitcher_admitted_p": len(p_admitted),
            "pitcher_kitchen_rmse_trainonly_impute": p_kit.get("mean_rmse"),
            "pitcher_kitchen_mae": p_kit.get("mean_mae"),
            "pitcher_kitchen_p": p_kit.get("n_features"),
            "pitcher_old_csv": p_kit_old.to_dict(orient="records"),
            "pitcher_cmp": {k: p_cmp.get(k) for k in ["mean_delta", "median_delta", "boot", "n_common_preds", "sign"]},
            "hitter_admitted_rmse_imputed": h_adm_imp.get("mean_rmse"),
            "hitter_cmp_fair_imputed": {k: h_cmp_fair.get(k) for k in ["mean_delta", "median_delta", "boot", "n_common_preds", "sign"]},
            "pitcher_admitted_rmse_imputed": p_adm_imp.get("mean_rmse"),
            "pitcher_cmp_fair_imputed": {k: p_cmp_fair.get(k) for k in ["mean_delta", "median_delta", "boot", "n_common_preds", "sign"]},
        },
        "kbbz": {k: kbbz.get(k) for k in ["mean_delta", "boot_ci_low", "boot_ci_high", "n_folds"]},
        "season_num_rmse": season_fe.get("mean_rmse"),
        "prose_number_trace": prose,
        "preprocessing": {
            "ridge_scaler": "StandardScaler fit on train fold only (sklearn Pipeline).",
            "elasticnet_cv": "ElasticNetCV 5-fold shuffled CV on the training matrix only; used in kitchen-sink elasticnet, not headline Ridge.",
            "league_z": "woba_z / k_bb_pct_z computed on the full season table before splitting, using same-season peers. Contemporaneous, not future. Includes players outside the modeling sample in the season mean.",
            "history_w2": "Player's own t and t-1 only; rookies fill with t.",
            "family_selection": "Greedy family demotion uses nested OOS on the full expanding-window sample, then admitted-core RMSE is reported on the same folds. Selection is slightly optimistic.",
            "imputation_bug": "Kitchen-sink median fill used the full sample. Corrected in this audit (train-only).",
        },
    }
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("issues:", issues)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
