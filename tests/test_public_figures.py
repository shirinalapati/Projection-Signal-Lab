import re
from pathlib import Path

import pandas as pd
import pytest

from psl.artifacts.figures import (
    HOVERTEXT_TEMPLATE,
    HITTER_COEF_DEFAULT,
    HITTER_COVERAGE_DEFAULT,
    PITCHER_COEF_DEFAULT,
    PITCHER_COVERAGE_DEFAULT,
    _load_table,
    admission_heatmap,
    coef_paths,
    coverage_from_admission,
    reliability_map,
    write_all,
)
from psl.artifacts.passports import write_passports
from psl.config import FIGURES, RESEARCH_DIR, ARTIFACTS
from psl.site.build import build_site

FORBIDDEN_HOVER = (
    "oos_rmse_delta",
    "verdict=",
    "max_corr_with_baseline",
    "family=",
    "μ",
)


def _visible(html: str) -> str:
    html = re.sub(r"<title>.*?</title>", "", html, flags=re.S)
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r'title="[^"]*"', "", html)
    html = re.sub(r"<code>.*?</code>", "", html, flags=re.S)
    html = re.sub(r"<footer>.*?</footer>", "", html, flags=re.S)
    html = re.sub(r"<details.*?</details>", "", html, flags=re.S)
    html = re.sub(
        r'<div id="(?:metrics|verdict)-glossary"[^>]*>.*?</div>',
        "",
        html,
        flags=re.S,
    )
    return html


@pytest.fixture(scope="module")
def rebuilt_public_site():
    table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    if "future_pearson_r" not in table.columns:
        from psl.artifacts.relationships import attach_relationships

        attach_relationships()
    write_all()
    write_passports()
    build_site()
    return RESEARCH_DIR


def test_reliability_map_hover_is_curated():
    fig = reliability_map(_load_table(), "hitter")
    assert fig.layout.hovermode == "closest"
    found = False
    for trace in fig.data:
        assert trace.hoverinfo == "none"
        for text in trace.hovertext or []:
            found = True
            for needle in FORBIDDEN_HOVER:
                assert needle not in text, needle
            assert "WHY" not in text
            assert "REDUNDANCY" not in text
            assert "METRIC" not in text
            assert "Verdict:" in text
            assert "Stability:" in text
            assert re.search(r"Stability: -?[\d.]+ \(\d+ of \d+\)", text)
            assert "Future value:" in text
            assert "Coverage:" in text
            assert "Takeaway:" in text
            assert text.count("<br>") <= 6
    assert found


def test_component_heatmaps_share_the_five_public_columns():
    table = _load_table()
    expected = [
        "Future Prediction",
        "Stable Over Time",
        "Unique Information",
        "Data Coverage",
        "Consistent Across Players",
    ]
    figs = (
        admission_heatmap(table, "pitcher"),
        admission_heatmap(table, "hitter", component="baserunning", target="y_br_rv_rate"),
        admission_heatmap(table, "hitter", component="defense", target="y_def_rv_rate"),
        admission_heatmap(table, "hitter", component="overall", target="y_war_rate"),
        admission_heatmap(table, "pitcher", component="overall", target="y_war_rate"),
    )
    for fig in figs:
        assert list(fig.data[0].x) == expected
        assert len(fig.data[0].y) >= 2


def test_hitter_heatmap_is_comprehensive_with_compact_hover():
    fig = admission_heatmap(_load_table(), "hitter")
    names = list(fig.data[0].y)
    assert "Sprint Speed" in names
    assert "Home-to-First Time" in names
    assert "Exit Velocity" in names
    assert "2-Year xwOBA" in names
    assert len(names) >= 50
    assert list(fig.data[0].x) == [
        "Future Prediction",
        "Stable Over Time",
        "Unique Information",
        "Data Coverage",
        "Consistent Across Players",
    ]
    assert fig.layout.xaxis.side == "top"
    bar_title = fig.data[0].colorbar.title.text
    assert "Percentile among" in bar_title
    assert "tested metrics" in bar_title
    found = False
    launch_coverage = None
    for row, name in zip(fig.data[0].hovertext, fig.data[0].y):
        for cell, col in zip(row, fig.data[0].x):
            found = True
            assert fig.data[0].hovertemplate == HOVERTEXT_TEMPLATE
            assert "WHY" not in cell
            assert "INCREMENTAL" not in cell
            assert "METRIC" not in cell
            assert cell.count("<br>") <= 3
            assert "Final verdict:" in cell
            assert "among tested metrics" not in cell
            if col == "Data Coverage":
                assert "Data Coverage:" in cell
                assert "Observed in" in cell
                assert "eligible seasons" in cell
                if name == "Launch Angle":
                    launch_coverage = cell
            assert "sprint_speed" not in cell
            assert "hp_to_1b" not in cell
            assert "Predictive value" not in cell
            assert "Temporal stability" not in cell
            assert "Subgroup consistency" not in cell
    assert found
    assert launch_coverage is not None
    assert launch_coverage.startswith("<b>Launch Angle</b>")
    assert "Data Coverage:" in launch_coverage
    assert "percentile" in launch_coverage
    assert "Observed in" in launch_coverage
    assert "Final verdict:" in launch_coverage


def test_hitter_coef_and_coverage_defaults_exclude_running_metrics():
    table = _load_table()
    coef = coef_paths(table, "hitter", HITTER_COEF_DEFAULT, component="hitting")
    coef_names = [tr.name for tr in coef.data]
    assert "Sprint Speed" not in coef_names
    assert "Home-to-First Time" not in coef_names
    for expected in (
        "2-Year wOBA",
        "3-Year wOBA",
        "2-Year xwOBA",
        "Exit Velocity",
        "Barrel Rate",
        "Hard-Hit Rate",
        "Chase Rate",
        "K%",
        "BB%",
    ):
        assert expected in coef_names, expected
    dashes = {tr.name: tr.line.dash for tr in coef.data}
    assert dashes["2-Year xwOBA"] == "solid"
    assert dashes["Barrel Rate"] == "dash"
    assert coef.layout.showlegend is False
    for tr in coef.data:
        assert tr.hovertemplate == HOVERTEXT_TEMPLATE
        for text in tr.hovertext:
            assert "WHY" not in text
            assert text.count("<br>") <= 3
            assert "Verdict:" in text
            assert "Standardized coefficient:" in text
    cov = coverage_from_admission(
        table,
        "hitter",
        component="hitting",
        target="y_woba",
        features=HITTER_COVERAGE_DEFAULT,
        title="Historical coverage for key hitting metrics",
    )
    cov_names = list(cov.data[0].y)
    assert "Sprint Speed" not in cov_names
    assert "Home-to-First Time" not in cov_names
    assert "SB Rate" not in cov_names
    for expected in (
        "2-Year wOBA",
        "2-Year xwOBA",
        "xwOBA",
        "Exit Velocity",
        "Barrel Rate",
        "Expected Slugging",
        "BB%",
    ):
        assert expected in cov_names, expected
    assert cov.layout.showlegend is False
    assert len(cov.data) == 1
    full = coverage_from_admission(table, "hitter", component="hitting", target="y_woba", title="all")
    full_names = list(full.data[0].y)
    assert "Sprint Speed" in full_names
    assert "Home-to-First Time" in full_names
    assert full.layout.showlegend is False


def test_pitcher_coef_and_coverage_use_curated_metrics():
    table = _load_table()
    coef = coef_paths(table, "pitcher", PITCHER_COEF_DEFAULT, component="pitching")
    coef_names = [tr.name for tr in coef.data]
    for expected in (
        "2-Year FIP",
        "3-Year K-BB%",
        "Stuff+",
        "Release Extension",
        "Four-Seam Velocity",
        "Average Velocity",
        "Average Spin Rate",
        "Whiff Rate",
    ):
        assert expected in coef_names, expected
    assert "mlbam_id" not in coef_names
    assert coef.layout.showlegend is False
    assert all(getattr(tr, "legendgroup", None) in (None, "") for tr in coef.data)
    cov = coverage_from_admission(
        table,
        "pitcher",
        component="pitching",
        target="y_fip",
        features=PITCHER_COVERAGE_DEFAULT,
        title="Historical coverage for key pitching metrics",
    )
    cov_names = list(cov.data[0].y)
    for expected in (
        "2-Year FIP",
        "2-Year K-BB%",
        "Stuff+",
        "Average Velocity",
        "Arm Angle",
        "Park Factor",
    ):
        assert expected in cov_names, expected
    assert "mlbam_id" not in cov_names
    assert len(cov_names) <= 12
    assert cov.layout.showlegend is False


def test_written_figure_html_hides_internal_hover_fields(rebuilt_public_site):
    del rebuilt_public_site
    for path in FIGURES.glob("*.html"):
        text = path.read_text()
        assert "verdict=" not in text
        assert "oos_rmse_delta" not in text
        assert "max_corr_with_baseline" not in text
        assert "μ" not in text
        if "plotly-graph-div" in text:
            uses_page_panel = path.name == "one_metric_jobs.html" or path.name.startswith("reliability_map")
            if uses_page_panel:
                assert "psl-metric-panel" in text
            else:
                assert "%{hovertext}" in text
    for name in (
        "coef_paths_hitter.html",
        "coef_paths_pitcher.html",
        "coef_paths_baserunning.html",
        "coef_paths_defense.html",
        "coef_paths_overall.html",
        "coef_paths_pitcher_war.html",
    ):
        text = (FIGURES / name).read_text()
        assert "psl-legend" in text, name


def test_hero_default_metric_has_target_dependent_verdicts():
    from psl.config import ARTIFACTS
    from psl.site.build import hero_catalog

    table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    metrics, default = hero_catalog(table)
    verdicts = {card["verdict"] for card in default["cards"]}
    assert len(default["cards"]) >= 2
    assert len(verdicts) >= 2
    sprint = next(m for m in metrics if m["feature"] == "sprint_speed")
    assert default["feature"] == "sprint_speed"
    assert sprint["primary"]["component"] == "Baserunning"
    assert sprint["primary"]["verdict"] == "Projection"
    assert [c["component"] for c in sprint["secondary"]] == ["Hitting", "Defense", "Overall Value"]
    assert {c["verdict"] for c in sprint["secondary"]} == {"Diagnostic"}
    assert sprint["notable"] == ""
    comps = [c["component"] for c in sprint["cards"]]
    assert comps == ["Hitting", "Baserunning", "Defense", "Overall Value"]
    assert {c["verdict"] for c in sprint["cards"]} >= {"Diagnostic", "Projection"}
    ev = next(m for m in metrics if m["player_type"] == "hitter" and m["feature"] == "ev")
    assert ev["primary"]["component"] == "Hitting"
    assert ev["primary"]["verdict"] == "Projection"
    assert any(c["component"] == "Overall Value" and c["verdict"] == "Projection" for c in ev["secondary"])
    assert "Overall Value" in ev["notable"]
    stuff = next(m for m in metrics if m["feature"] == "stuff_plus")
    assert stuff["primary"]["component"] == "Pitching"
    assert stuff["secondary"] == []
    velo = next(m for m in metrics if m["feature"] == "avg_velo")
    assert velo["primary"]["component"] == "Pitching"
    labels = {m["label"] for m in metrics}
    assert "Arm Strength" not in labels
    assert "K-BB%" not in labels
    assert all(m["feature"] != "k_bb_pct" for m in metrics)
    chip_labels = [m["label"] for m in metrics if (m["player_type"], m["feature"]) in {
        ("hitter", "ev"),
        ("hitter", "sprint_speed"),
        ("hitter", "o_swing_pct"),
        ("pitcher", "avg_velo"),
        ("pitcher", "stuff_plus"),
    }]
    assert "Exit Velocity" in chip_labels
    assert "Stuff+" in chip_labels
    assert "Sprint Speed" in chip_labels
    for metric in metrics:
        assert metric["primary"]["verdict"]
        assert metric["primary"]["why"]
        assert metric["passportHref"].startswith("passports/")
        for card in [metric["primary"], *metric["secondary"]]:
            assert card["verdict"]
            assert card["why"]
            assert card["href"].startswith("passports/")
            assert "#" in card["href"]


def test_public_pages_use_display_names(rebuilt_public_site):
    site = rebuilt_public_site
    index = (site / "index.html").read_text()
    assert "PA-weighted 2-Year xwOBA improved the next-season wOBA projection" in index
    assert "A metric can have different jobs depending on what you are trying to predict" in index
    assert "The same metric can play different roles depending on what is being projected" in index
    assert "One metric. Different jobs." in index
    assert "What are we projecting?" in index
    assert "Future wOBA" in index
    assert "Future FIP" in index
    assert "Open Metrics Glossary" in index
    assert "Hide Metrics Glossary" in index
    assert "Stuff+ is a pitch-quality score" in index
    assert "expected-whiff probabilities" in index
    assert 'href="#metrics-glossary"' in index
    assert "definitions of every metric" in index
    assert "Frozen Arsenal" not in _visible(index)
    metrics = index.split('id="metrics-glossary"', 1)[1].split('id="verdict-glossary"', 1)[0]
    hitting = metrics.split("<h3>Hitting</h3>", 1)[1].split("<h3>Pitching</h3>", 1)[0]
    pitching = metrics.split("<h3>Pitching</h3>", 1)[1].split("<h3>Baserunning</h3>", 1)[0]
    running = metrics.split("<h3>Baserunning</h3>", 1)[1].split("<h3>Defense</h3>", 1)[0]
    defense = metrics.split("<h3>Defense</h3>", 1)[1]
    assert "Sprint Speed" in running
    assert "Sprint Speed" not in hitting
    assert "Stuff+" in pitching
    assert "Stuff+ note:" in pitching
    assert "arsenalintelligence.streamlit.app" in pitching
    assert "Arsenal Intelligence" in pitching
    assert pitching.find("Stuff+ note:") < pitching.find("2-Year Fastball Velocity")
    assert "Outs Above Average" in defense or "OAA" in defense
    assert "Expected Weighted On-Base Average" in hitting
    assert "PA-weighted 2-year xwOBA" not in hitting
    assert "A hitter’s expected wOBA across the current and previous season" in hitting
    assert "<h3>Model and validation terms</h3>" in metrics
    assert "Baseline model" in metrics
    assert "Kitchen-sink model" in metrics
    assert "Expanding-window validation" in metrics
    assert "Temporal fold / Test period" in metrics
    assert "What the verdicts mean" in index
    assert "Arm Strength" not in index
    assert 'id="hero-name"' in index
    assert "Sprint Speed" in index
    assert ">Sprint Speed<" in index
    assert "Primary use" in index
    assert "View full metric passport" in index
    assert "Also tested in:" in index
    assert "Hitting ·" in index
    assert "Defense ·" in index
    assert "Overall Value ·" in index
    hero = index.split('<section class="jobs-hero"', 1)[1].split('<script type="application/json" id="hero-data">', 1)[0]
    assert hero.count('class="hero-primary"') == 1
    assert 'class="hero-job"' not in hero
    generic_diag = "This metric helps describe how a player succeeds or struggles, but did not add enough independent future-prediction value to the broad model."
    assert generic_diag not in hero
    assert "passports/hitter_sprint_speed.html#target-hitting" in index
    assert "passports/hitter_sprint_speed.html#target-baserunning" in index
    assert "passports/hitter_sprint_speed.html#target-defense" in index
    assert 'class="hero-chip' in index
    assert not re.search(r'class="hero-chip[^"]*"[^>]*>K-BB%<', index)
    assert 'value="K-BB%"' not in index
    visible_index = _visible(index)
    assert "Sprint Speed" in visible_index
    assert "Exit Velocity" in visible_index
    assert "Chase Rate" in visible_index
    assert "Average Velocity" in visible_index
    assert "Stuff+" in visible_index
    jobs = (FIGURES / "one_metric_jobs.html").read_text()
    assert "2-Year K-BB%" not in jobs
    assert "next-season K-BB%" not in jobs
    assert "Stuff+" not in jobs
    assert "Chase Rate" not in jobs
    assert "Sprint Speed" in jobs
    assert "Baserunning" in jobs
    assert "Exit Velocity" in jobs
    assert "2-Year xwOBA" in jobs
    assert "2-Year Baserunning Rate" in jobs
    assert "2-Year Defensive Rate" in jobs
    assert "psl-metric-panel" in jobs
    assert "jobs-panel" in jobs
    assert 'id="jobs-panel"' in index
    assert "Hover a metric on the chart to see details here" in index
    for page in (
        "index.html",
        "hitters.html",
        "pitchers.html",
        "baserunning.html",
        "defense.html",
        "overall.html",
        "passports.html",
        "models.html",
        "feature-audit.html",
        "methodology.html",
    ):
        html = (site / page).read_text()
        main = html.split("<main>", 1)[1]
        assert "What the verdicts mean" in html, page
        assert 'id="verdict-glossary"' in html, page
        assert "Hide Verdict Glossary" in html, page
        assert "Open Metrics Glossary" in html, page
        assert "Hide Metrics Glossary" in html, page
        assert 'id="metrics-glossary"' in html, page
        assert main.find('id="metrics-glossary-toggle"') != -1, page
        assert main.find('id="metrics-glossary-toggle"') < 400, page
        assert main.count('id="metrics-glossary-toggle"') == 1, page
        assert main.find('id="glossary-toggle"') != -1, page
        assert main.find('id="glossary-toggle"') < 800, page
        assert main.count('id="glossary-toggle"') == 1, page
        assert "Open Verdict Glossary" not in html, page
        for heading in ("Hitting", "Pitching", "Baserunning", "Defense"):
            assert f"<h3>{heading}</h3>" in html, (page, heading)
    assert "Universe audit" not in index
    assert "Feature Audit" in index
    assert "xwoba_w2" not in _visible(index)
    hitters = (site / "hitters.html").read_text()
    assert "View full research diagnostics" in hitters
    assert "What matters most in the final hitting projection?" in hitters
    assert "Coefficient stability for key hitting metrics" in hitters
    assert "Historical coverage for key hitting metrics" in hitters
    assert "How every hitter metric was evaluated" in hitters
    assert "How to read this chart." in hitters
    assert "not a measure of feature importance" in hitters
    assert "Future Prediction" in hitters
    assert "deserve to change a future projection" in hitters
    assert "selection bias" in hitters
    assert "Consistent Across Players" in hitters
    assert "Show all tested metrics" in hitters
    assert "figures/dropone_hitter.html" in hitters
    assert "figures/coef_paths_hitter_all.html" in hitters
    assert "Chase Rate" in hitters
    assert "<h2>4 Projections</h2>" in hitters
    assert "Correlation is not admission" in hitters
    assert "Future relationship" not in hitters
    assert "Unique OOS contribution" not in hitters
    assert "RMSE when removed" not in hitters
    assert "Model impact" in hitters
    assert "Role in forecast" in hitters
    assert "Relationship with next season" in hitters
    assert "What it adjusts for" in hitters
    assert "Why excluded" in hitters
    visible_hitters = _visible(hitters)
    assert "This metric helps describe how a player succeeds or struggles" not in visible_hitters
    assert "Use to adjust or display environment, role, or playing time" not in visible_hitters
    assert "The metric did not provide enough unique predictive or diagnostic value" not in visible_hitters
    assert "Closely overlaps with Exit Velocity" in hitters
    assert "2-Year xwOBA version provided a more stable history-aware signal" in hitters
    assert "offensive skills change with age" in hitters
    assert "Prediction error increased 1.1% without 2-Year xwOBA." in hitters
    assert "40% predictive" not in hitters
    assert "affects wOBA by" not in hitters.lower()
    assert re.search(r"<h2>\d+ Diagnostics</h2>", hitters)
    assert "o_swing_pct" not in _visible(hitters)
    assert "Sprint Speed" not in _visible(hitters)
    pitchers = (site / "pitchers.html").read_text()
    assert re.search(r"<h2>\d+ Projections</h2>", pitchers)
    assert re.search(r"<h2>\d+ Diagnostics</h2>", pitchers)
    assert "View full research diagnostics" in pitchers
    assert "Coefficient stability" in pitchers
    assert "Historical coverage" in pitchers
    assert "Historical coverage for key pitching metrics" in pitchers
    assert "Names wrap under the chart" in pitchers
    assert "iframe-coef" in pitchers
    assert "iframe-cov" in pitchers
    assert "figures/coef_paths_pitcher.html" in pitchers
    assert "figures/coef_paths_pitcher_all.html" in pitchers
    assert "Show all tested metrics" in pitchers
    assert "figures/coverage_pitcher.html" in pitchers
    assert "figures/coverage_pitcher_all.html" in pitchers
    assert "Key pitching metrics" in pitchers
    assert "How every pitcher metric was evaluated" in pitchers
    assert "How to read this chart." in pitchers
    assert "lower FIP is better" in pitchers
    assert "deserve to change a future FIP projection" in pitchers
    assert "figures/heatmap_pitcher.html" in pitchers
    assert "League-Adjusted K-BB%" in pitchers
    assert "standardized K-BB%" in pitchers
    assert "Model impact" in pitchers
    assert "Prediction error increased" in pitchers
    assert "Role in forecast" in pitchers
    assert "What it adjusts for" in pitchers
    assert "Why excluded" in pitchers
    assert "This metric helps describe how a player succeeds or struggles" not in _visible(pitchers)
    assert "Future relationship" not in pitchers
    assert "Unique OOS contribution" not in pitchers
    assert "RMSE when removed" not in pitchers
    baserunning = (site / "baserunning.html").read_text()
    assert "Sprint Speed" in _visible(baserunning)
    assert re.search(r"<h2>\d+ Projections</h2>", baserunning)
    assert "Model impact" in baserunning
    assert "Prediction error increased 2.0% without Sprint Speed." in baserunning
    assert "Role in forecast" in baserunning
    assert "Unique OOS contribution" not in baserunning
    assert "How every baserunning metric was evaluated" in baserunning
    assert "baserunning run-value rate" in baserunning
    assert "figures/heatmap_baserunning.html" in baserunning
    assert "figures/coef_paths_baserunning.html" in baserunning
    assert "figures/coef_paths_baserunning_all.html" in baserunning
    assert "Show all tested metrics" in baserunning
    assert "Coefficient stability" in baserunning
    assert "Historical coverage for key baserunning metrics" in baserunning
    assert "eligible baserunning-seasons" in baserunning
    assert "figures/coverage_baserunning.html" in baserunning
    assert "figures/coverage_baserunning_all.html" in baserunning
    assert "Key baserunning metrics" in baserunning
    assert "How to read this chart." in baserunning
    defense = (site / "defense.html").read_text()
    assert "Sprint Speed" not in _visible(defense)
    assert re.search(r"<h2>\d+ Projections</h2>", defense)
    assert "Model impact" in defense
    assert "Prediction error increased" in defense
    assert "Role in forecast" in defense
    assert "Unique OOS contribution" not in defense
    assert "How every defensive metric was evaluated" in defense
    assert "fielding run-value rate" in defense
    assert "figures/heatmap_defense.html" in defense
    assert "figures/coef_paths_defense.html" in defense
    assert "figures/coef_paths_defense_all.html" in defense
    assert "Show all tested metrics" in defense
    assert "Coefficient stability" in defense
    assert "Historical coverage for key defensive metrics" in defense
    assert "eligible defense-seasons" in defense
    assert "figures/coverage_defense.html" in defense
    assert "figures/coverage_defense_all.html" in defense
    assert "Key defensive metrics" in defense
    assert "How to read this chart." in defense
    overall = (site / "overall.html").read_text()
    assert "Sprint Speed" not in _visible(overall)
    assert "How every overall-value metric was evaluated" in overall
    assert "next-season WAR rate" in overall
    assert "figures/heatmap_overall.html" in overall
    assert "figures/heatmap_pitcher_war.html" in overall
    assert "figures/coef_paths_overall.html" in overall
    assert "figures/coef_paths_overall_all.html" in overall
    assert "figures/coef_paths_pitcher_war.html" in overall
    assert "figures/coef_paths_pitcher_war_all.html" in overall
    assert "Show all tested metrics" in overall
    assert "Coefficient stability" in overall
    assert "Historical coverage for key position-player WAR metrics" in overall
    assert "Historical coverage for key pitcher WAR metrics" in overall
    assert "figures/coverage_overall.html" in overall
    assert "figures/coverage_overall_all.html" in overall
    assert "figures/coverage_pitcher_war.html" in overall
    assert "figures/coverage_pitcher_war_all.html" in overall
    assert "Key position-player WAR metrics" in overall
    assert "Model impact" in overall
    assert "Prediction error increased 8.2% without 2-Year WAR Rate." in overall
    assert "How to read this chart." in overall
    assert "not a measure of feature importance" in overall
    models = (site / "models.html").read_text()
    assert "Lower error is better" in models
    assert "admitted-feature model" in models.lower()
    assert "Position-player WAR rate" in models
    assert "Pitcher WAR rate" in models
    assert "figures/models_overall.html" in models
    assert "figures/models_pitcher_war.html" in models
    assert "persistence" not in _visible(models)
    audit = (site / "feature-audit.html").read_text()
    assert "Did we cherry-pick" in audit
    assert "Feature Universe Audit" in audit
    assert "An exclusion is not a bad result" in audit
    assert "Context only" in audit or "Context rather than skill" in audit
    assert "Would leak future information" in audit or "Future leakage" in audit
    assert "LEAKAGE" not in _visible(audit)
    assert "Not baseball-relevant" not in audit
    assert "Registry rows" not in audit
    assert "Exclusion log (first 25)" not in audit
    passports = (site / "passports.html").read_text()
    assert "2-Year xwOBA" in passports
    assert 'href="passports/hitter_xwoba_w2.html"' in passports
    assert 'id="passport-search"' in passports
    assert 'list="passport-metric-list"' in passports
    assert 'id="passport-metric-list"' in passports
    assert "Search metrics" in passports
    assert 'value="2-Year xwOBA"' in passports
    assert "Walk Rate (Hitter)" in passports or "Walk Rate (Pitcher)" in passports
    assert "Canonical ID" not in passports.split('<div class="passport-grid"', 1)[1].split("<script", 1)[0]
    assert "Canonical ID" not in hitters
    assert "Canonical ID" not in pitchers
    assert "Canonical ID" not in index
    assert "Canonical metric IDs" not in index
    assert not list((site / "passports").glob("*.json"))
    html = (site / "passports" / "hitter_xwoba_w2.html").read_text()
    assert "<h1>2-Year xwOBA</h1>" in html
    assert "Why this verdict?" in html
    assert "Takeaway" in html
    assert "Technical details" not in html
    assert "Pearson r" not in html
    assert "Partial r after baseline" not in html
    assert "Canonical ID" not in html
    assert "negative = improvement vs baseline" not in html
    assert "#" not in html.split("<h1>")[1][:20]
    sprint = (site / "passports" / "hitter_sprint_speed.html").read_text()
    assert 'id="target-hitting"' in sprint
    assert 'id="target-baserunning"' in sprint
    assert 'id="target-defense"' in sprint
    assert 'id="target-overall"' in sprint
    stuff = (site / "passports" / "pitcher_stuff_plus.html").read_text()
    assert 'id="target-pitching"' in stuff
    assert 'id="target-pitching-k-bb"' not in stuff
    assert "next-season K-BB%" not in stuff
    kbb_pass = (site / "passports" / "pitcher_k_bb_pct.html").read_text()
    assert "next-season K-BB%" not in kbb_pass
    assert "PITCHING FORECAST" in kbb_pass
    assert "Target: next-season FIP" in kbb_pass
    assert "Why this verdict?" in kbb_pass
    assert "Takeaway" in kbb_pass
    assert "Technical details" not in kbb_pass
    assert "2-Year FIP" in kbb_pass  # redundancy partner appears in why/overlap
    dep = (FIGURES / "target_dependence_pitcher.html").read_text()
    assert "next-season K-BB%" not in dep
    assert "next-season K-BB%" not in _visible(index)
    assert "2-Year K-BB%" in dep
    assert "2-Year FIP" in dep
    assert "3-Year K-BB%" not in dep
    assert "Stuff+" not in dep
    assert "Whiff Rate" not in dep
    assert "Four-Seam Velocity" not in dep
    assert "Release Extension" not in dep
    hit_dep = (FIGURES / "target_dependence_hitter.html").read_text()
    assert "Sprint Speed" in hit_dep
    assert "Exit Velocity" in hit_dep
    assert "2-Year xwOBA" in hit_dep
    assert "2-Year Baserunning Rate" in hit_dep
    assert "2-Year Defensive Rate" in hit_dep
    assert "Chase Rate" not in hit_dep
    assert "Not evaluated for this target" in hit_dep
    assert "not evaluated for that target" in index
    assert "does not mean Exclude" in index
    methodology = (site / "methodology.html").read_text()
    assert "next-season K-BB%" not in methodology
    assert "K-BB% is therefore a candidate predictor" in methodology
    assert "Why these projection targets?" in methodology
    assert "What this study is trying to answer" in methodology
    assert "Fisher’s z" in methodology or "Fisher's z" in methodology
    assert "correlation alone does not earn" in methodology
    assert "do not assign verdicts" in methodology
    assert "every available field is inventoried" not in methodology.lower()
    assert "defined source tables" in methodology
    jobs = (FIGURES / "one_metric_jobs.html").read_text()
    assert "Stuff+" not in jobs
    assert "Pitching · next-season K-BB%" not in jobs
    table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    assert "y_k_bb_pct" not in set(table["target"].astype(str))
    assert table.groupby(["component", "target"]).ngroups == 5
    assert 'href="map.html"' not in index.split("<nav>", 1)[1].split("</nav>", 1)[0]
    assert ">Reliability Map<" not in index.split("<nav>", 1)[1].split("</nav>", 1)[0]
    assert 'id="reliability-map"' in index
    assert 'id="map-filters"' in index
    assert 'id="map-frame"' in index
    assert "how repeatable a metric is from one season to the next" in index
    assert "rank among the metrics on this map" in index
    assert "share of eligible player-seasons" in index
    assert "not 100% for every metric" in index
    assert 'data-src="figures/reliability_map_hitting.html"' in index
    rel_map = (FIGURES / "reliability_map.html").read_text()
    assert "psl-metric-panel" in rel_map
    assert "map-panel" in rel_map
    assert 'id="map-panel"' in index
    map_redirect = (site / "map.html").read_text()
    assert "index.html#reliability-map" in map_redirect
    assert "<nav>" not in map_redirect
