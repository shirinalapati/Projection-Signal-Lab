"""Public verdict-table copy is metric-specific and does not change admission results."""

from collections import Counter

import pandas as pd

from psl.config import ARTIFACTS
from psl.site.labels import without_kbb_outcome_target
from psl.site.table_copy import (
    GENERIC_BOILERPLATE,
    audit_table_copy,
    collect_public_rows,
    context_adjusts_for,
    context_why_matters,
    relationship_label,
    table_why,
)


def _table():
    return without_kbb_outcome_target(pd.read_parquet(ARTIFACTS / "admission_table.parquet"))


def test_every_public_row_has_a_nonempty_reason():
    table = _table()
    public = collect_public_rows(table)
    empty = []
    for _, row in public.iterrows():
        why = table_why(row, table)
        if not str(why).strip():
            empty.append((row.player_type, row.component, row.feature, row.verdict))
        assert "r = " not in why
        assert "RMSE" not in why
        for boiler in GENERIC_BOILERPLATE:
            assert boiler not in why
        rel = relationship_label(row)
        assert rel
        assert not rel.startswith("r =")
    assert empty == []


def test_why_does_not_contradict_canonical_verdicts():
    table = _table()
    public = collect_public_rows(table)
    for _, row in public.iterrows():
        why = table_why(row, table).lower()
        verdict = str(row.verdict)
        if verdict in {"Projection", "Augmented Projection"}:
            assert "did not earn" not in why
            assert "why excluded" not in why
        if verdict == "Exclude":
            assert "baseline for next-season" not in why
        if verdict == "Context":
            assert "projection input" not in why
            assert "not in the projection model" not in why


def test_hitting_diagnostic_and_context_examples():
    table = _table()
    hit = table[table.component.eq("hitting") & table.target.eq("y_woba") & table.player_type.eq("hitter")]

    def why(feat, verdict):
        row = hit[hit.feature.eq(feat) & hit.verdict.eq(verdict)].iloc[0]
        return table_why(row, table)

    assert "2-Year xwOBA" in why("xwoba", "Diagnostic")
    assert "Exit Velocity" in why("hard_hit_pct", "Diagnostic")
    assert "Barrel" in why("barrel_pct", "Diagnostic") or "contact-quality" in why("barrel_pct", "Diagnostic")
    age = hit[hit.feature.eq("age")].iloc[0]
    assert context_adjusts_for(age) == "Aging"
    assert "offensive skills change with age" in context_why_matters(age)
    park = hit[hit.feature.eq("park_factor")].iloc[0]
    assert context_adjusts_for(park) == "Home run environment"
    assert "on-base and power" in why("ops", "Exclude")
    assert "too unstable" in why("woba_yoy", "Exclude")


def test_reasons_are_target_specific_for_shared_metrics():
    table = _table()
    ev_hit = table[
        table.feature.eq("ev") & table.target.eq("y_woba") & table.verdict.eq("Projection")
    ].iloc[0]
    ev_war = table[
        table.feature.eq("ev") & table.target.eq("y_war_rate") & table.verdict.eq("Projection")
    ].iloc[0]
    assert table_why(ev_hit, table) != table_why(ev_war, table)
    avg_velo = table[table.feature.eq("avg_velo") & table.target.eq("y_fip")].iloc[0]
    assert "Four-Seam Velocity" in table_why(avg_velo, table)
    assert "wOBA" not in table_why(avg_velo, table)


def test_public_section_counts_match_filtered_artifacts():
    table = _table()
    public = collect_public_rows(table)
    expected = {
        ("hitting", "y_woba", "hitter", "Projection"): 4,
        ("hitting", "y_woba", "hitter", "Diagnostic"): 39,
        ("hitting", "y_woba", "hitter", "Context"): 9,
        ("hitting", "y_woba", "hitter", "Exclude"): 10,
        ("pitching", "y_fip", "pitcher", "Projection"): 11,
        ("pitching", "y_fip", "pitcher", "Diagnostic"): 41,
        ("pitching", "y_fip", "pitcher", "Context"): 10,
        ("pitching", "y_fip", "pitcher", "Exclude"): 7,
    }
    # Hitting diagnostics include speed metrics that are listed only on baserunning.
    raw = table
    for key, n in expected.items():
        comp, tgt, pt, verdict = key
        artifact_n = int(
            ((raw.component == comp) & (raw.target == tgt) & (raw.player_type == pt) & (raw.verdict == verdict)).sum()
        )
        assert artifact_n == n
    hit_diag_public = public[
        public.component.eq("hitting") & public.target.eq("y_woba") & public.verdict.eq("Diagnostic")
    ]
    hit_diag_raw = raw[
        raw.component.eq("hitting") & raw.target.eq("y_woba") & raw.verdict.eq("Diagnostic")
    ]
    assert len(hit_diag_public) <= len(hit_diag_raw)
    assert len(hit_diag_public) >= 30


def test_duplication_audit_is_near_zero():
    table = _table()
    audit = audit_table_copy(table)
    for verdict in ("Diagnostic", "Context", "Exclude"):
        stats = audit[verdict]
        assert stats["empty"] == 0
        assert stats["n"] > 0
        assert stats["identical_share"] == 0.0, (verdict, stats)
        assert stats["most_common_n"] == 1, (verdict, stats["most_common"], stats["most_common_n"])


def test_no_mass_identical_why_within_hitting_diagnostics():
    table = _table()
    public = collect_public_rows(table)
    texts = [
        table_why(row, table)
        for _, row in public[
            public.component.eq("hitting") & public.verdict.eq("Diagnostic")
        ].iterrows()
    ]
    counts = Counter(texts)
    assert max(counts.values()) <= 3
    assert "Did not add enough independent value." not in counts
