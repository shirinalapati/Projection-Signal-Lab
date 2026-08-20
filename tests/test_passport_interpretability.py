"""Passport interpretability presentation tests. No verdict/model changes."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from psl.artifacts.passports import passport_html_body, write_passports
from psl.config import ARTIFACTS, RESEARCH_DIR
from psl.site.labels import without_kbb_outcome_target
from psl.site.passport_copy import (
    build_forecast_peer_ranks,
    decision_line,
    forecast_impact_label,
    historical_consistency_label,
    relationship_signed_label,
    takeaway,
    why_this_verdict,
)


@pytest.fixture(scope="module")
def admission():
    table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    return without_kbb_outcome_target(table)


def _row(table, player_type, feature, target):
    hit = table[
        table.player_type.eq(player_type)
        & table.feature.eq(feature)
        & table.target.eq(target)
    ]
    assert not hit.empty
    return hit.iloc[0]


def test_passport_helpers_use_canonical_bands(admission):
    br = _row(admission, "hitter", "br_rv_rate_w2", "y_br_rv_rate")
    assert relationship_signed_label(br["future_pearson_r"]).startswith("Moderate")
    assert "Helped in all 7" in historical_consistency_label(br)
    assert "Reduced forecast error" in forecast_impact_label(br) or "No meaningful" in forecast_impact_label(br)
    assert "projection" in decision_line(br).lower()
    why = why_this_verdict(br)
    assert "Pearson" not in why
    assert "ΔRMSE" not in why
    assert "rmse" not in why.lower()
    assert takeaway(br)


def test_passport_html_leads_with_plain_english(admission):
    group = admission[
        admission.player_type.eq("hitter") & admission.feature.eq("br_rv_rate_w2")
    ]
    ranks = build_forecast_peer_ranks(admission)
    html = passport_html_body(group, ranks)
    assert "BASERUNNING FORECAST" in html
    assert "POSITION-PLAYER WAR FORECAST" in html or "OVERALL" in html
    assert "Why this verdict?" in html
    assert "Takeaway" in html
    assert "Technical details" not in html
    assert "tech-details" not in html
    assert "Evidence" in html
    assert "Forecast-impact rank" in html
    assert "among baserunning metrics" in html
    assert "How to read this" in html
    assert "Raw relationship vs unique information" in html
    assert "Pearson r" not in html
    assert "Spearman" not in html
    assert "Partial r after baseline" not in html
    assert "Incremental OOS" not in html
    assert "negative = improvement" not in html
    assert "Canonical ID" not in html
    assert "This metric helps describe how a player succeeds or struggles" not in html


def test_forecast_peer_rank_quantifies_standing(admission):
    ranks = build_forecast_peer_ranks(admission)
    war = ranks[("hitter", "war_rate_w2", "overall", "y_war_rate")]
    assert war["rank"] == 1
    assert war["n"] == 13
    assert "overall-value" in str(war["field"])
    br = ranks[("hitter", "br_rv_rate_w2", "baserunning", "y_br_rv_rate")]
    assert br["n"] == 26
    assert 1 <= int(br["rank"]) <= 26


def test_written_passports_match_artifacts_and_invariants(admission):
    write_passports(admission)
    from psl.site.build import build_site

    build_site()
    path = RESEARCH_DIR / "passports" / "hitter_br_rv_rate_w2.html"
    assert path.exists()
    html = path.read_text()
    assert "<h1>2-Year Baserunning Rate</h1>" in html
    assert "Use this metric in the baserunning projection." in html
    assert "Why this verdict?" in html
    assert re.search(r"Takeaway", html)
    assert "Technical details" not in html
    assert "Forecast-impact rank" in html
    assert "of 26" in html
    assert "among baserunning metrics" in html
    assert "Pearson r" not in html
    assert "negative = improvement vs baseline" not in html
    war = RESEARCH_DIR / "passports" / "hitter_war_rate_w2.html"
    assert war.exists()
    war_html = war.read_text()
    assert "1 of 13" in war_html
    assert "among position-player overall-value metrics" in war_html
    xw = RESEARCH_DIR / "passports" / "hitter_xwoba_w2.html"
    assert xw.exists()
    xw_html = xw.read_text()
    assert "Why this verdict?" in xw_html
    assert "Takeaway" in xw_html
    assert 'id="target-hitting"' in xw_html
    assert "Forecast-impact rank" in xw_html
    assert "among hitting metrics" in xw_html
