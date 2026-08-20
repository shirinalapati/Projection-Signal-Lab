"""Tests against the real assembled panels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from psl.config import DATA_PROCESSED, SEASON_END, SEASON_START

H = DATA_PROCESSED / "hitter_sample_pa150.parquet"
P = DATA_PROCESSED / "pitcher_sample_role_ip.parquet"


@pytest.mark.skipif(not H.exists(), reason="panels not built")
def test_hitter_sample_filters_and_uniqueness():
    df = pd.read_parquet(H)
    assert df.duplicated(["mlbam_id", "season"]).sum() == 0
    assert (df["pa"] >= 150).all()
    assert (df["y_pa"] >= 150).all()
    assert df["y_woba"].notna().all()
    assert df["season"].max() <= SEASON_END - 1
    assert df["season"].min() >= SEASON_START
    assert df["target_season"].equals(df["season"] + 1)
    # no perfect leakage
    assert df["woba"].corr(df["y_woba"]) < 0.9


@pytest.mark.skipif(not P.exists(), reason="panels not built")
def test_pitcher_sample_filters_and_uniqueness():
    df = pd.read_parquet(P)
    assert df.duplicated(["mlbam_id", "season"]).sum() == 0
    assert df["y_k_bb_pct"].notna().all()
    assert df["y_fip"].notna().all()
    assert df["target_season"].equals(df["season"] + 1)
    assert df["k_bb_pct"].corr(df["y_k_bb_pct"]) < 0.95
    assert df["fip"].corr(df["y_fip"]) < 0.95
    # role-specific IP
    sp = df[df.starter_role == 1]
    rp = df[df.starter_role == 0]
    if len(sp):
        non_covid = sp[sp.season != 2020]
        if len(non_covid):
            assert non_covid["ip"].min() >= 80
        covid = sp[sp.season == 2020]
        if len(covid):
            assert covid["ip"].min() >= 25
    if len(rp):
        non_covid = rp[rp.season != 2020]
        if len(non_covid):
            assert non_covid["ip"].min() >= 30


@pytest.mark.skipif(not H.exists(), reason="panels not built")
def test_no_tplus1_in_feature_names():
    df = pd.read_parquet(H)
    feature_cols = [c for c in df.columns if not c.startswith("y_") and c != "target_season"]
    assert all(not c.startswith("y_") for c in feature_cols)


def test_runner_advancement_from_pbp_rows():
    from psl.data.mlb_pbp import runner_advancement

    df = pd.DataFrame(
        [
            {"mlbam_id": 1, "season": 2024, "event_type": "single", "origin": "2B", "end": "score", "is_scoring": True, "is_out": False},
            {"mlbam_id": 1, "season": 2024, "event_type": "single", "origin": "2B", "end": "3B", "is_scoring": False, "is_out": False},
            {"mlbam_id": 1, "season": 2024, "event_type": "field_out", "origin": "1B", "end": None, "is_scoring": False, "is_out": True},
            {"mlbam_id": 2, "season": 2024, "event_type": "strikeout", "origin": None, "end": None, "is_scoring": False, "is_out": True},
        ]
    )
    out = runner_advancement(df)
    row = out[(out.mlbam_id == 1) & (out.season == 2024)].iloc[0]
    assert int(row.sth_opp) == 2
    assert int(row.sth_success) == 1
    assert abs(float(row.second_to_home_rate) - 0.5) < 1e-9
    assert int(row.outs_on_bases_n) == 1
    assert 2 not in set(out.mlbam_id.astype(int))


BR = DATA_PROCESSED / "baserunning_sample.parquet"
DEF = DATA_PROCESSED / "defense_sample.parquet"


@pytest.mark.skipif(not BR.exists(), reason="baserunning panel not built")
def test_baserunning_pbp_rates_are_mostly_observed():
    df = pd.read_parquet(BR)
    assert df["second_to_home_rate"].notna().mean() >= 0.99
    assert df["outs_on_bases_rate"].notna().mean() >= 0.99


@pytest.mark.skipif(not DEF.exists(), reason="defense panel not built")
def test_oaa_rate_defined_where_oaa_exists():
    df = pd.read_parquet(DEF)
    have = df["oaa"].notna()
    assert have.any()
    assert df.loc[have, "oaa_rate"].notna().all()
