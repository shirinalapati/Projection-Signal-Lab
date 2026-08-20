import numpy as np
import pandas as pd
import pytest
from scipy.stats import pearsonr, spearmanr

from psl.artifacts.relationships import _fisher_mean, _pearson, _residualize, _spearman
from psl.config import ARTIFACTS, DATA_PROCESSED, RESEARCH_DIR
from psl.site.labels import (
    correlation_direction_label,
    fmt_pearson_r,
    future_relationship_short,
    r_band,
)


def test_r_bands_are_descriptive_only():
    assert r_band(0.09) == "Very weak"
    assert r_band(0.10) == "Weak"
    assert r_band(0.29) == "Weak"
    assert r_band(0.30) == "Moderate"
    assert r_band(0.50) == "Strong"
    assert r_band(0.70) == "Very strong"
    assert future_relationship_short(0.41) == "Moderate positive"
    assert future_relationship_short(-0.41) == "Moderate negative"


def test_correlation_copy_is_not_importance_or_percent():
    text = correlation_direction_label(0.40, "y_woba")
    assert "moderate positive" in text.lower()
    assert "next-season wOBA" in text
    assert "40%" not in text
    assert "predictive" not in text.lower()
    assert "causes" not in text.lower()
    assert "affects" not in text.lower()
    fip = correlation_direction_label(-0.35, "y_fip")
    assert "better" in fip
    assert "negative" in fip.lower()
    assert "bad" not in fip.lower()


def test_partial_residualization_fits_train_only():
    z_train = np.array([[1.0], [2.0], [3.0], [4.0]])
    y_train = np.array([2.0, 4.0, 6.0, 8.0])
    z_test = np.array([[5.0], [6.0]])
    y_test = np.array([12.0, 12.0])
    res = _residualize(y_train, z_train, y_test, z_test)
    np.testing.assert_allclose(res, [2.0, 0.0], atol=1e-10)


def test_fisher_mean_and_rank_correlation():
    assert abs(_fisher_mean([0.2, 0.4]) - np.tanh(np.mean([np.arctanh(0.2), np.arctanh(0.4)]))) < 1e-12
    a = np.array([1.0, 2.0, 3.0, 10.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] * 3)
    b = a + np.array([0, 1, -1, 2, 0, 0, 1, -2, 0, 0] * 3)
    assert abs(_pearson(a, b) - pearsonr(a, b)[0]) < 1e-12
    assert abs(_spearman(a, b) - spearmanr(a, b)[0]) < 1e-12


@pytest.fixture(scope="module")
def admission():
    path = ARTIFACTS / "admission_table.parquet"
    if not path.exists():
        pytest.skip("admission table missing")
    df = pd.read_parquet(path)
    if "future_pearson_r" not in df.columns:
        pytest.skip("relationship fields not attached")
    return df


def _row(table, pt, feat, tgt):
    sub = table[table.player_type.eq(pt) & table.feature.eq(feat) & table.target.eq(tgt)]
    assert len(sub) == 1, (pt, feat, tgt, len(sub))
    return sub.iloc[0]


def test_future_correlations_use_lead_targets(admission):
    h = pd.read_parquet(DATA_PROCESSED / "hitter_sample_pa150.parquet")
    p = pd.read_parquet(DATA_PROCESSED / "pitcher_sample_role_ip.parquet")
    assert (h["target_season"] == h["season"] + 1).all()
    assert (p["target_season"] == p["season"] + 1).all()
    for sample, pt, feat, tgt in (
        (h, "hitter", "xwoba_w2", "y_woba"),
        (h, "hitter", "ops", "y_woba"),
        (p, "pitcher", "avg_velo", "y_fip"),
    ):
        pair = sample[[feat, tgt]].dropna()
        computed = float(pearsonr(pair[feat], pair[tgt])[0])
        stored = float(_row(admission, pt, feat, tgt)["future_pearson_r_pooled"])
        assert abs(stored - computed) < 1e-8
        if "woba" in sample.columns and tgt == "y_woba":
            contemp = float(pearsonr(pair[feat], sample.loc[pair.index, "woba"])[0])
            assert abs(stored - contemp) > 1e-4


def test_verdicts_and_xwoba_delta_unchanged(admission):
    assert _row(admission, "hitter", "xwoba_w2", "y_woba")["verdict"] == "Projection"
    assert _row(admission, "hitter", "ev", "y_woba")["verdict"] == "Projection"
    assert _row(admission, "hitter", "sprint_speed", "y_woba")["verdict"] == "Diagnostic"
    assert _row(admission, "hitter", "sprint_speed", "y_br_rv_rate")["verdict"] == "Projection"
    assert _row(admission, "pitcher", "stuff_plus", "y_fip")["verdict"] == "Projection"
    delta = float(_row(admission, "hitter", "xwoba_w2", "y_woba")["oos_rmse_delta"])
    assert abs(delta + 0.000931) < 5e-6
    hit = admission[admission.component.eq("hitting") & admission.target.eq("y_woba") & admission.verdict.eq("Projection")]
    assert len(hit) == 4
    velo = float(_row(admission, "pitcher", "avg_velo", "y_fip")["future_pearson_r"])
    assert velo < 0
    n = _row(admission, "hitter", "xwoba_w2", "y_woba")["correlation_n"]
    assert int(n) >= 20


def test_partial_r_is_not_raw_r_for_redundant_metrics(admission):
    ops = _row(admission, "hitter", "ops", "y_woba")
    raw = abs(float(ops["future_pearson_r"]))
    part = abs(float(ops["partial_future_r"]))
    assert raw > 0.20
    assert part < raw


def test_public_pages_match_artifacts_and_keep_the_hierarchy(admission):
    hitters = RESEARCH_DIR / "hitters.html"
    if not hitters.exists():
        pytest.skip("site not built")
    html = hitters.read_text()
    xw = _row(admission, "hitter", "xwoba_w2", "y_woba")
    assert "Correlation is not admission" in html
    assert "Model impact" in html
    assert "Role in forecast" in html
    assert "Relationship with next season" in html
    assert "Prediction error increased 1.1% without 2-Year xwOBA." in html
    assert "Future relationship" not in html
    assert "Unique OOS contribution" not in html
    assert "RMSE when removed" not in html
    assert fmt_pearson_r(xw["future_pearson_r"]) not in html
    assert "40% predictive" not in html
    assert "affects wOBA by" not in html.lower()
    passport = (RESEARCH_DIR / "passports" / "hitter_xwoba_w2.html").read_text()
    assert "Why this verdict?" in passport
    assert "Takeaway" in passport
    assert "Technical details" not in passport
    assert "Pearson correlation" not in passport
    assert "Incremental OOS ΔRMSE" not in passport
    assert "negative = improvement vs baseline" not in passport
    methodology = (RESEARCH_DIR / "methodology.html").read_text()
    assert "Fisher’s z" in methodology or "Fisher's z" in methodology
    assert "do not assign verdicts" in methodology
    assert "Why these projection targets?" in methodology
    heat = (RESEARCH_DIR / "figures" / "heatmap_hitter.html").read_text()
    assert "Future Prediction" in heat
    assert "INCREMENTAL PREDICTIVE VALUE" not in heat
    assert "WHY<br>" not in heat
