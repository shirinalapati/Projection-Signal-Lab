"""Universe audit, history leakage, and exact-redundancy tests."""

from __future__ import annotations

import pandas as pd

from psl.admission.engine import AdmissionResult, decide_verdict
from psl.admission.redundancy import flag_exact_relations
from psl.catalog import HITTER_FEATURES, PITCHER_FEATURES
from psl.data.history import add_history_features
from psl.data.registry import STATUSES, _seed_notes, NOTES


def test_history_does_not_use_future_seasons():
    df = pd.DataFrame(
        {
            "mlbam_id": [1, 1, 1],
            "season": [2018, 2019, 2020],
            "woba": [0.300, 0.320, 0.400],
            "pa": [500, 520, 480],
        }
    )
    out = add_history_features(df, ["woba"], weight_col="pa")
    r2018 = out[out.season == 2018].iloc[0]
    r2019 = out[out.season == 2019].iloc[0]
    assert pd.isna(r2018["woba_lag1"])
    assert abs(r2018["woba_w2"] - 0.300) < 1e-12  # rookies fall back to current
    assert abs(r2019["woba_lag1"] - 0.300) < 1e-12
    # 2019 two-year mean uses 2018+2019, never 2020
    w = (0.320 * 520 + 0.300 * 500) / (520 + 500)
    assert abs(r2019["woba_w2"] - w) < 1e-12
    assert abs(r2019["woba_yoy"] - 0.020) < 1e-12


def test_kbb_identity_holds():
    df = pd.DataFrame(
        {
            "k_pct": [0.25, 0.20],
            "bb_pct": [0.08, 0.10],
            "k_bb_pct": [0.17, 0.10],
        }
    )
    rel = flag_exact_relations(df, "pitcher")
    row = rel[rel.derived == "k_bb_pct"].iloc[0]
    assert bool(row["holds_on_panel"])


def test_ops_identity_holds():
    df = pd.DataFrame({"ops": [0.800], "obp": [0.350], "slg": [0.450]})
    rel = flag_exact_relations(df, "hitter")
    row = rel[rel.derived == "ops"].iloc[0]
    assert bool(row["holds_on_panel"])


def test_demographic_verdict_is_context_even_if_predictive():
    res = AdmissionResult(
        player_type="hitter",
        feature="is_catcher",
        family="position",
        target="y_woba",
        role="demographic",
        process=False,
        oos_rmse_delta=-0.01,
        baseline_rmse=0.04,
        coverage=1.0,
        folds_improved=1.0,
        n_folds=7,
        oos_rmse_ci_low=-0.02,
        oos_rmse_ci_high=-0.005,
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Context"


def test_registry_notes_use_allowed_statuses():
    _seed_notes()
    statuses = {n.candidate_status for n in NOTES}
    assert statuses <= set(STATUSES)
    assert "TEST" in statuses
    assert "UNAVAILABLE_RELIABLY" in statuses
    catalog = {s.name for s in HITTER_FEATURES} | {s.name for s in PITCHER_FEATURES}
    assert "woba" in catalog and "k_bb_pct_w2" in catalog
    assert "xwobacon" in catalog and "stuff_fb" in catalog
