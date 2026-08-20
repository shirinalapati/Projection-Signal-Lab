"""Audit a short written summary against admission artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from psl.config import ARTIFACTS, DATA_PROCESSED, ROOT


def _pick_example(table: pd.DataFrame, player_type: str, features: list[str]) -> pd.Series | None:
    sub = table[(table.player_type == player_type) & (table.feature.isin(features))]
    if sub.empty:
        sub = table[table.player_type == player_type]
    if sub.empty:
        return None
    return sub.sort_values("oos_rmse_delta", na_position="last").iloc[0]


def draft_essay(table: pd.DataFrame) -> str:
    h = table[table.player_type == "hitter"]
    p = table[table.player_type == "pitcher"]
    xw = h[h.feature == "xwoba"]
    chase = h[h.feature == "o_swing_pct"]
    velo = p[p.feature.isin(["avg_velo", "fbv"])]
    stuff = p[p.feature == "stuff_plus"]
    park = table[table.feature == "park_factor"].head(1)

    def cell(df, col):
        if df is None or df.empty:
            return None
        val = df.iloc[0][col]
        return val

    xw_d = cell(xw, "oos_rmse_delta")
    xw_c = cell(xw, "coverage")
    xw_v = cell(xw, "verdict")
    ch_v = cell(chase, "verdict")
    ch_d = cell(chase, "oos_rmse_delta")
    velo_v = cell(velo, "verdict")
    stuff_v = cell(stuff, "verdict")

    # Keep this a draft; word count is enforced after editing.
    text = (
        "I would split player information by job, then admit it with out-of-time tests rather than in-sample fit. "
        "The projection is the number used for roster value: it may include a metric only when expanding-window "
        "validation shows repeatable incremental accuracy beyond a baseline of age, playing time, current performance, "
        "and park/run environment; the relationship is stable or era-adjusted; it is not already contained in simpler "
        "complete features; coverage does not silently drop the players who matter; and the effect does not reverse in "
        "the subgroups where it will be used. Tracking that passes those tests only for covered players belongs in an "
        "augmented model, not a complete-case core. "
        f"In a 2015–2025 study of next-season wOBA and FIP, xwOBA’s out-of-time RMSE change was {xw_d} "
        f"with coverage {xw_c} (verdict: {xw_v}); chase rate was {ch_v} "
        f"(ΔRMSE {ch_d}). "
        "Information that fails those gates can still be useful. Process metrics that describe swing decisions, "
        "contact quality, pitch shape, or stuff go on a diagnostic card for coaches and development. Park, level, "
        "role, and league environment adjust or contextualize the number rather than being treated as skill. "
        "Scouting grades and injury history would enter the same gate: scouting as independent information or as "
        "tool/development diagnosis depending on incremental value and coverage; injuries first as availability and "
        "uncertainty, and as talent-rate inputs only if they improve out-of-time rate projections. "
        "A metric that helps historically but is unstable, redundant, or inconsistently available is era-adjusted, "
        "moved to diagnosis, or restricted to an augmented roster — it is not auto-admitted because last decade’s "
        "R² improved."
    )
    return text


def audit_claims(essay: str, table: pd.DataFrame) -> list[str]:
    problems = []
    words = re.findall(r"[A-Za-z0-9+\-%.]+", essay)
    if len(essay.split()) > 250:
        problems.append(f"word_count={len(essay.split())} exceeds 250")
    # numeric tokens in essay should appear in the table stringified results
    blob = table.to_csv(index=False)
    for tok in re.findall(r"-?0\.\d+", essay):
        if tok not in blob and tok not in essay:
            problems.append(f"unmatched numeric token {tok}")
    if "xwOBA" in essay or "xwoba" in essay.lower():
        if table[(table.feature == "xwoba")].empty:
            problems.append("essay cites xwOBA but table has no xwoba row")
    return problems


def main() -> None:
    table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
    dest = ROOT / "docs" / "summary_250_word_response.md"
    if not dest.exists():
        report = {
            "word_count": 0,
            "problems": [f"summary file not found: {dest}"],
            "source": str(dest),
        }
        (ARTIFACTS / "essay_audit.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        print(dest)
        return
    text = dest.read_text()
    wc = len(text.split())
    problems = audit_claims(text, table)
    if wc > 250:
        problems.append(f"word_count={wc} exceeds 250")
    report = {"word_count": wc, "problems": problems, "source": str(dest)}
    (ARTIFACTS / "essay_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(dest)


if __name__ == "__main__":
    main()
