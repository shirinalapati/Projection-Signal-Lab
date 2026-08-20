import pandas as pd

from psl.catalog import (
    BASERUNNING_FEATURES,
    DEFENSE_FEATURES,
    HITTER_FEATURES,
    PITCHER_FEATURES,
    WAR_HITTER_FEATURES,
    WAR_PITCHER_FEATURES,
)
from psl.site.labels import (
    MODEL_DISPLAY,
    STATUS_DISPLAY,
    belongs_on_component,
    display_model,
    display_name,
    display_status,
    fmt_model_impact,
    fmt_rmse_delta,
    looks_like_raw_id,
    metric_primary_component,
)


def test_sprint_speed_lists_only_on_baserunning_unless_it_earns_a_job():
    assert belongs_on_component("hitter", "sprint_speed", "baserunning", "Projection")
    assert not belongs_on_component("hitter", "sprint_speed", "hitting", "Diagnostic")
    assert not belongs_on_component("hitter", "sprint_speed", "defense", "Diagnostic")
    assert not belongs_on_component("hitter", "sprint_speed", "overall", "Diagnostic")
    assert belongs_on_component("hitter", "ev", "hitting", "Projection")
    assert belongs_on_component("hitter", "ev", "overall", "Projection")
    assert belongs_on_component("hitter", "o_swing_pct", "hitting", "Diagnostic")
    assert not belongs_on_component("hitter", "xwoba_w2", "overall", "Diagnostic")
    assert belongs_on_component("pitcher", "stuff_plus", "pitching", "Diagnostic")
    assert belongs_on_component("hitter", "age", "hitting", "Context")
    assert metric_primary_component("hitter", "sprint_speed") == "baserunning"
    assert metric_primary_component("hitter", "ev") == "hitting"
    assert metric_primary_component("hitter", "o_swing_pct") == "hitting"
    assert metric_primary_component("pitcher", "avg_velo") == "pitching"
    assert metric_primary_component("pitcher", "stuff_plus") == "pitching"
    assert metric_primary_component("hitter", "arm_strength") == "defense"
    assert metric_primary_component("hitter", "oaa") == "defense"


def test_required_display_names():
    assert display_name("xwoba_w2", "hitter") == "2-Year xwOBA"
    assert display_name("woba_w2", "hitter") == "2-Year wOBA"
    assert display_name("k_bb_pct_w2", "pitcher") == "2-Year K-BB%"
    assert display_name("k_bb_pct_z", "pitcher") == "League-Adjusted K-BB%"
    assert display_name("o_swing_pct", "hitter") == "Chase Rate"
    assert display_name("z_contact_pct", "hitter") == "In-Zone Contact Rate"
    assert display_name("avg_velo", "pitcher") == "Average Velocity"
    assert display_name("avg_spin", "pitcher") == "Average Spin Rate"
    assert display_name("stuff_plus", "pitcher") == "Stuff+"
    assert display_name("ev", "hitter") == "Exit Velocity"


def test_catalog_features_have_non_snake_display_names():
    for spec in (
        *HITTER_FEATURES,
        *PITCHER_FEATURES,
        *BASERUNNING_FEATURES,
        *DEFENSE_FEATURES,
        *WAR_HITTER_FEATURES,
        *WAR_PITCHER_FEATURES,
    ):
        shown = display_name(spec.name)
        assert "_" not in shown, spec.name


def test_public_model_and_status_labels():
    assert display_model("persistence") == "Previous-Season Performance"
    assert display_model("baseline") == "Baseline Projection"
    assert display_model("kitchen_sink_imputed") == "All-Feature Model"
    assert display_status("CONTEXT_ONLY_CANDIDATE") == "Context only"
    assert display_status("LEAKAGE") == "Would leak future information"
    assert all("_" not in v for v in MODEL_DISPLAY.values())
    assert all("_" not in v for v in STATUS_DISPLAY.values())


def test_rmse_copy_avoids_micro_units_and_states_direction():
    assert fmt_rmse_delta(-0.000931).startswith("Improved RMSE by 0.00093")
    assert fmt_rmse_delta(0.00025).startswith("Worsened RMSE by")
    assert "μ" not in fmt_rmse_delta(0.00025)
    assert fmt_rmse_delta(1e-6) == "No meaningful change"
    assert fmt_rmse_delta(0.00002) == "No meaningful change"
    assert looks_like_raw_id("xwoba_w2")
    assert not looks_like_raw_id("2-Year xwOBA")


def test_model_impact_uses_percent_increase_not_raw_rmse():
    assert (
        fmt_model_impact(0.000378, 0.03426682, "2-Year xwOBA")
        == "Prediction error increased 1.1% without 2-Year xwOBA."
    )
    assert (
        fmt_model_impact(-0.000021, 0.03426682, "2-Year wOBA")
        == "Prediction error decreased 0.1% without 2-Year wOBA."
    )
    assert fmt_model_impact(None, 0.034, "Chase Rate") == "Not in the projection model"
    assert "RMSE" not in fmt_model_impact(0.000378, 0.03426682, "2-Year xwOBA")


def test_hover_copy_hides_internal_fields():
    from psl.site.labels import map_hover_text

    row = pd.Series(
        {
            "feature": "park_factor",
            "player_type": "hitter",
            "verdict": "Context",
            "reliability_pearson": 0.3339472,
            "oos_rmse_delta": 0.00002,
            "coverage": 1.0,
            "max_corr_with_baseline": 0.21,
            "family": "environment",
        }
    )
    text = map_hover_text(row)
    assert "Park Factor" in text
    assert "Verdict: Context" in text
    assert "Stability: 0.33" in text
    ranked = row.copy()
    ranked["stability_rank"] = 12
    ranked["stability_n"] = 40
    assert "Stability: 0.33 (12 of 40)" in map_hover_text(ranked)
    assert "Coverage: 100%" in text
    assert "Takeaway:" in text
    assert "WHY" not in text
    assert "REDUNDANCY" not in text
    assert "correlation" not in text.lower()
    assert "oos_rmse_delta" not in text
    assert "verdict=" not in text
    assert "max_corr_with_baseline" not in text
    assert "family=" not in text
    assert "μ" not in text
    assert "family" not in text.lower() or "environment" not in text

