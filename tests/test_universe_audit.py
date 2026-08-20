"""Feature Universe Audit presentation tests. No registry/model changes."""

from __future__ import annotations

import pandas as pd
import pytest

from psl.config import ARTIFACTS, RESEARCH_DIR
from psl.site.universe_audit import (
    exclusion_reason_summary,
    fmt_coverage,
    funnel_counts,
    humanize_exclusion_reason,
    load_exclusions,
    load_registry,
    public_status_label,
    reconcile_funnel,
    registry_explorer_records,
    render_universe_audit_html,
)


@pytest.fixture(scope="module")
def registry():
    return load_registry()


@pytest.fixture(scope="module")
def exclusions():
    return load_exclusions()


def test_funnel_reconciles_with_registry(registry):
    reconcile_funnel(registry)
    funnel = funnel_counts(registry)
    assert funnel["reviewed"] == len(registry)
    assert funnel["reviewed"] == funnel["entered_pipeline"] + funnel["not_directly_tested"]
    assert funnel["reviewed"] == 402


def test_exclusion_reason_counts_reconcile(exclusions):
    summary = exclusion_reason_summary(exclusions)
    assert sum(row["n"] for row in summary) == len(exclusions)
    assert len(exclusions) == 192
    assert not exclusions["Feature"].astype(str).str.contains("arsenal_stuff").any()


def test_not_baseball_relevant_is_reworded():
    assert "Not baseball-relevant" != public_status_label("NOT_BASEBALL_RELEVANT")
    assert "independent player-skill" in public_status_label("NOT_BASEBALL_RELEVANT").lower()


def test_coverage_is_percent():
    assert fmt_coverage(1.0) == "100%"
    assert fmt_coverage(0.9981) == "99.8%"
    assert fmt_coverage(0.4678) == "46.8%"


def test_exclusion_reasons_are_humanized():
    text = humanize_exclusion_reason(
        "Team-dependent counting stat; not a rate talent input.",
        "STRUCTURAL_DUPLICATE",
    )
    assert "playing time" in text.lower() or "rate-based" in text.lower()
    assert "Team-dependent counting stat; not a rate talent input." not in text
    leak = humanize_exclusion_reason("Uses seasons after the prediction date.", "LEAKAGE")
    assert "leak future information" in leak.lower()
    park = humanize_exclusion_reason(
        "Sample size behind the park factor estimate.",
        "STRUCTURAL_DUPLICATE",
    )
    assert "park factor" in park.lower() and "sample size" in park.lower()


def test_registry_explorer_includes_every_row(registry):
    records = registry_explorer_records(registry)
    assert len(records) == len(registry)
    assert all(r["why"] for r in records)
    assert all(r["coverage"].endswith("%") or r["coverage"] == "n/a" for r in records)


def test_universe_page_copy_and_invariants(registry, exclusions):
    html = render_universe_audit_html(registry, exclusions)
    assert "Feature Universe Audit" in html
    assert "Did we cherry-pick the metrics we tested?" in html
    assert "fields available in the project’s defined data sources" in html
    assert "every available field" not in html.lower()
    assert "An exclusion is not a bad result" in html
    assert "Feature funnel" in html
    assert "What happened to each field?" in html
    assert "Explore the feature universe" in html
    assert "View all excluded fields" in html
    assert "Not baseball-relevant" not in html
    assert "Technical registry summary" not in html
    assert "CONTEXT_ONLY_CANDIDATE" not in html.split('id="universe-data"', 1)[0]
    assert "Feature-universe decisions happen before the admission verdict" in html
    assert "hitter" in html.lower() and "pitcher" in html.lower()
    assert "Baserunning" in html and "Defense" in html
    # no raw 1.0 coverage dumps in the static shell; explorer fills via JSON
    assert '"coverage": "100%"' in html or "100%" in html


def test_built_feature_audit_page_exists():
    from psl.site.build import build_site

    build_site()
    page = (RESEARCH_DIR / "feature-audit.html").read_text()
    assert "Feature Universe Audit" in page
    assert "Did we cherry-pick" in page
    assert "Registry rows" not in page
    assert "Exclusion log (first 25)" not in page
    assert "universe-data" in page
    assert "Canonical ID" not in page
    assert '"canonical"' not in page
    assert "Canonical IDs remain" not in page
