"""Leakage, uniqueness, and split tests on synthetic and real panels."""

from __future__ import annotations

import numpy as np
import pandas as pd

from psl.admission.engine import AdmissionResult, decide_verdict
from psl.admission.run import apply_trainonly_impute, train_fold_medians
from psl.data.assemble import add_next_season_targets
from psl.models.baselines import expanding_folds


def test_next_season_join_is_t_plus_1():
    df = pd.DataFrame(
        {
            "mlbam_id": [1, 1, 1, 2, 2],
            "season": [2018, 2019, 2020, 2018, 2019],
            "woba": [0.300, 0.320, 0.310, 0.400, 0.350],
            "pa": [500, 520, 480, 200, 210],
        }
    )
    out = add_next_season_targets(df, {"woba": "y_woba", "pa": "y_pa"})
    row = out[(out.mlbam_id == 1) & (out.season == 2018)].iloc[0]
    assert abs(row["y_woba"] - 0.320) < 1e-12
    assert row["target_season"] == 2019
    # 2020 has no 2021
    last = out[(out.mlbam_id == 1) & (out.season == 2020)].iloc[0]
    assert pd.isna(last["y_woba"])


def test_features_do_not_contain_future_values():
    df = pd.DataFrame(
        {
            "mlbam_id": [1, 1],
            "season": [2018, 2019],
            "woba": [0.3, 0.4],
            "xwoba": [0.31, 0.41],
        }
    )
    out = add_next_season_targets(df, {"woba": "y_woba"})
    # season-t xwOBA must remain 0.31 for 2018 even though 2019 is 0.41
    row = out[out.season == 2018].iloc[0]
    assert abs(row["xwoba"] - 0.31) < 1e-12
    assert abs(row["y_woba"] - 0.4) < 1e-12
    feature_cols = [c for c in out.columns if not c.startswith("y_") and c != "target_season"]
    assert "y_woba" not in feature_cols


def test_expanding_folds_are_temporal():
    seasons = np.repeat([2017, 2018, 2019, 2020, 2021], 60)
    df = pd.DataFrame(
        {
            "season": seasons,
            "x": np.arange(len(seasons)),
            "y_woba": 0.3,
        }
    )
    folds = expanding_folds(df, test_years=[2020, 2021])
    assert folds
    for train_idx, test_idx, test_year in folds:
        train_seasons = set(df.iloc[train_idx]["season"])
        test_seasons = set(df.iloc[test_idx]["season"])
        assert max(train_seasons) < min(test_seasons)
        assert test_seasons == {test_year - 1}
        assert test_year not in train_seasons
        assert test_year - 1 not in train_seasons


def test_player_season_uniqueness_synthetic():
    df = pd.DataFrame({"mlbam_id": [1, 1, 2], "season": [2019, 2019, 2019], "woba": [1, 2, 3]})
    dups = df.duplicated(["mlbam_id", "season"]).sum()
    assert dups == 1


def test_environment_verdict_is_context():
    res = AdmissionResult(
        player_type="hitter",
        feature="park_factor",
        family="environment",
        target="y_woba",
        role="environment",
        process=False,
        oos_rmse_delta=-0.01,
        baseline_rmse=0.04,
        coverage=1.0,
        folds_improved=1.0,
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Context"


def test_train_fold_medians_ignore_validation_values():
    train = pd.DataFrame({"x": [0.0, 0.0, 0.0, 1.0], "season": [2018, 2018, 2018, 2018]})
    test = pd.DataFrame({"x": [100.0, 100.0, 100.0, np.nan], "season": [2019, 2019, 2019, 2019]})
    med = train_fold_medians(train, ["x"])
    leaked = float(pd.concat([train["x"], test["x"]], ignore_index=True).median())
    assert med["x"] == 0.0
    assert leaked != med["x"]
    _, filled_test, _, used_med = apply_trainonly_impute(train, test, ["x"])
    assert used_med["x"] == 0.0
    assert float(filled_test["x"].iloc[-1]) == 0.0
    assert leaked != float(filled_test["x"].iloc[-1])


def test_imputation_parameters_cannot_be_computed_from_validation():
    """If validation rows entered the median, the fill value would move."""
    train = pd.DataFrame({"metric": [0.0, 0.0, 0.0, 0.0, 1.0]})
    test = pd.DataFrame({"metric": [100.0, 100.0, 100.0, np.nan]})
    train_med = train_fold_medians(train, ["metric"])["metric"]
    full_med = float(pd.concat([train["metric"], test["metric"]], ignore_index=True).median())
    assert train_med == 0.0
    assert full_med != train_med
    _, filled, _, med = apply_trainonly_impute(train, test, ["metric"])
    assert med["metric"] == train_med
    assert float(filled["metric"].iloc[-1]) == train_med


def test_no_random_split_helper_uses_years():
    rng = np.random.default_rng(0)
    seasons = np.array([2018] * 50 + [2019] * 50 + [2020] * 50)
    df = pd.DataFrame({"season": seasons, "x": rng.normal(size=150), "y_woba": rng.normal(size=150)})
    folds = expanding_folds(df, test_years=[2020])
    assert len(folds) == 1
    train_idx, test_idx, year = folds[0]
    assert year == 2020
    assert set(df.iloc[test_idx]["season"].unique()) == {2019}
    assert df.iloc[train_idx]["season"].max() == 2018
