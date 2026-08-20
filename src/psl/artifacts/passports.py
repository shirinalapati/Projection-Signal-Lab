"""Per-metric Feature Passports generated from the admission table."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from psl.catalog import (
    BASERUNNING_FEATURES,
    DEFENSE_FEATURES,
    HITTER_FEATURES,
    PITCHER_FEATURES,
    WAR_HITTER_FEATURES,
    WAR_PITCHER_FEATURES,
)
from psl.config import ARTIFACTS, PASSPORTS
from psl.site.labels import (
    COMPONENT_TARGET_ORDER,
    component_phrase,
    display_family,
    display_name,
    display_player,
    target_phrase,
    target_section_id,
    verdict_for_target,
    without_kbb_outcome_target,
)
from psl.site.passport_copy import (
    build_forecast_peer_ranks,
    decision_line,
    evidence_items,
    forecast_heading,
    peer_rank_key,
    peer_standing_label,
    peer_standing_sentence,
    raw_vs_unique_blurb,
    relationship_signed_label,
    scatter_how_to_read,
    takeaway,
    what_it_measures,
    why_this_verdict,
)

SPECS = {}
for specs, pt in (
    (HITTER_FEATURES, "hitter"),
    (PITCHER_FEATURES, "pitcher"),
    (BASERUNNING_FEATURES, "hitter"),
    (DEFENSE_FEATURES, "hitter"),
    (WAR_HITTER_FEATURES, "hitter"),
    (WAR_PITCHER_FEATURES, "pitcher"),
):
    for s in specs:
        SPECS.setdefault((pt, s.name), s)


def passport_markdown(row: pd.Series) -> str:
    spec = SPECS.get((row["player_type"], row["feature"]))
    desc = what_it_measures(row, spec.description if spec else "")
    shown = display_name(row["feature"], row["player_type"])
    who = display_player(row["player_type"])
    return f"""# {shown}

**{who} · {display_family(row['family'])} · {row['verdict']}**

{decision_line(row)}

## What it measures
{desc}

## Why this verdict
{why_this_verdict(row)}

## Takeaway
{takeaway(row)}

## Evidence summary
- Future relationship: {relationship_signed_label(row.get('future_pearson_r'))}
- Independent signal / after baseline: see HTML passport
- Historical consistency / coverage / overlap: see HTML passport
"""


def _ordered_rows(group: pd.DataFrame) -> pd.DataFrame:
    g = group.copy()
    order = {pair: i for i, pair in enumerate(COMPONENT_TARGET_ORDER)}
    g["_ord"] = [
        order.get((str(c), str(t)), 99)
        for c, t in zip(g.get("component", pd.Series("")), g.get("target", pd.Series("")))
    ]
    return g.sort_values(["_ord", "player_type"]).drop(columns="_ord")


def _scatter_block(row: pd.Series) -> str:
    pt = row.get("player_type")
    feat = row.get("feature")
    tgt = row.get("target")
    path = PASSPORTS / "scatters" / f"{pt}_{feat}_{tgt}.svg"
    if not path.exists():
        return ""
    shown = html.escape(display_name(feat, pt))
    tgt_txt = html.escape(target_phrase(tgt))
    raw = html.escape(relationship_signed_label(row.get("future_pearson_r")))
    how = html.escape(scatter_how_to_read(row))
    vs = html.escape(raw_vs_unique_blurb(row))
    return f"""
        <figure class="passport-figure">
          <img class="passport-scatter" src="scatters/{pt}_{feat}_{tgt}.svg"
               alt="{shown} versus {tgt_txt}"/>
          <figcaption>
            <p class="axis-note"><span class="k">X</span> {shown}</p>
            <p class="axis-note"><span class="k">Y</span> {tgt_txt}</p>
            <p class="how-read"><span class="k">How to read this</span> {how}</p>
            <p class="raw-unique"><span class="k">Raw relationship vs unique information</span> {vs}</p>
            <p class="raw-label">Raw relationship: {raw}</p>
          </figcaption>
        </figure>
    """


def _evidence_grid(row: pd.Series, peer_info: dict | None = None) -> str:
    cards = []
    for item in evidence_items(row, peer_info):
        cards.append(
            "<div class=\"evidence-chip\">"
            f"<span class=\"k\">{html.escape(item['label'])}</span>"
            f"<strong>{html.escape(item['value'])}</strong>"
            f"<p>{html.escape(item['note'])}</p>"
            "</div>"
        )
    return f'<div class="evidence-grid">{"".join(cards)}</div>'


def _peer_rank_line(row: pd.Series, peer_info: dict | None) -> str:
    if not peer_info:
        return ""
    standing = html.escape(peer_standing_label(peer_info))
    field = html.escape(str(peer_info.get("field") or ""))
    note = html.escape(peer_standing_sentence(row, peer_info))
    return f"""
        <p class="peer-rank" title="{note}">
          <span class="k">Forecast-impact rank</span>
          <strong>{standing}</strong>
          <span class="peer-field">among {field}</span>
        </p>
    """


def _target_section_html(row: pd.Series, peer_info: dict | None = None) -> str:
    vclass = (str(row.get("verdict") or "")).split()[0]
    verdict = html.escape(verdict_for_target(row))
    anchor = html.escape(target_section_id(row.get("component"), row.get("target")))
    heading = html.escape(forecast_heading(row))
    target = html.escape(target_phrase(row.get("target")))
    decision = html.escape(decision_line(row))
    why = html.escape(why_this_verdict(row))
    take = html.escape(takeaway(row))
    return f"""
      <section class="target-card" id="{anchor}">
        <p class="forecast-kicker">{heading}</p>
        <p class="target-line">Target: {target}</p>
        <p class="verdict-line"><span class="verdict {vclass}">{verdict}</span></p>
        <p class="decision">{decision}</p>
        {_peer_rank_line(row, peer_info)}
        <h4>Why this verdict?</h4>
        <p class="why-verdict">{why}</p>
        {_scatter_block(row)}
        <h4>Evidence</h4>
        {_evidence_grid(row, peer_info)}
        <div class="takeaway">
          <span class="k">Takeaway</span>
          <p>{take}</p>
        </div>
      </section>
    """


def _why_verdicts_differ(group: pd.DataFrame) -> str:
    vs = group["verdict"].astype(str).unique().tolist()
    if len(vs) <= 1:
        v = vs[0] if vs else "n/a"
        return (
            f"The verdict is {html.escape(v)} for every target tested here. "
            "That still does not make it a universal baseball label; it is the result for these questions."
        )
    return (
        "Verdicts depend on the projection target. A metric can belong in one projection and be used "
        "only for explanation in another, because each target asks a different statistical question "
        "against a target-specific baseline."
    )


def passport_html_body(rows, peer_ranks: dict | None = None) -> str:
    if isinstance(rows, pd.Series):
        group = rows.to_frame().T
    else:
        group = pd.DataFrame(rows)
    public = without_kbb_outcome_target(group)
    if public is not None and len(public):
        group = public
    group = _ordered_rows(group)
    if peer_ranks is None:
        peer_ranks = build_forecast_peer_ranks(group)
    row0 = group.iloc[0]
    spec = SPECS.get((row0["player_type"], row0["feature"]))
    catalog_desc = spec.description if spec else ""
    desc = html.escape(what_it_measures(row0, catalog_desc))
    shown = html.escape(display_name(row0["feature"], row0["player_type"]))
    who = html.escape(display_player(row0["player_type"]))
    family = html.escape(display_family(row0["family"]))
    distinct = group["verdict"].astype(str).nunique()
    if distinct > 1:
        kicker_verdict = "Target-dependent"
        vclass = "Diagnostic"
        lede = (
            "Verdicts depend on the projection target. A metric can belong in one projection "
            "and be used only for explanation in another."
        )
    else:
        kicker_verdict = html.escape(str(row0.get("verdict") or ""))
        vclass = (str(row0.get("verdict") or "")).split()[0]
        lede = (
            "Each result below is relative to one projection target."
        )
    sections = "".join(
        _target_section_html(r, peer_ranks.get(peer_rank_key(r)))
        for _, r in group.iterrows()
    )
    return f"""
    <article class="passport-detail">
      <a class="back-link" href="../passports.html">All passports</a>
      <h1>{shown}</h1>
      <p class="kicker">{who} · {family} · <span class="verdict {vclass}">{kicker_verdict}</span></p>
      <p class="lede">{lede}</p>
      <h2>What it measures</h2>
      <p>{desc or "n/a"}</p>
      <h2>Results by projection target</h2>
      {sections}
      <h2>Why the verdicts differ</h2>
      <p>{_why_verdicts_differ(group)}</p>
    </article>
    """


def write_passports(table: pd.DataFrame | None = None) -> list[Path]:
    PASSPORTS.mkdir(parents=True, exist_ok=True)
    if table is None:
        table = pd.read_parquet(ARTIFACTS / "admission_table.parquet")
        from psl.artifacts.figures import _parse_jsonish

        for c in (
            "coverage_by_season",
            "fold_rmse_deltas",
            "coef_path",
            "subgroup",
            "extra",
            "correlation_folds",
        ):
            if c in table.columns:
                table[c] = table[c].apply(_parse_jsonish)
    table = without_kbb_outcome_target(table)
    written = []
    index = []
    keep_slugs = set()
    for (pt, feat), group in table.groupby(["player_type", "feature"], sort=False):
        group = _ordered_rows(group)
        slug = f"{pt}_{feat}"
        keep_slugs.add(slug)
        md_parts = [f"# {display_name(feat, pt)}", "", f"**{display_player(pt)}**", ""]
        for _, row in group.iterrows():
            md_parts.append(f"## {component_phrase(row.get('component'))}")
            md_parts.append(f"Verdict: {verdict_for_target(row)}")
            md_parts.append("")
            md_parts.append(decision_line(row))
            md_parts.append("")
            md_parts.append("### Why this verdict")
            md_parts.append(why_this_verdict(row))
            md_parts.append("")
            md_parts.append(f"**Takeaway:** {takeaway(row)}")
            md_parts.append("")
        md_parts.append("## Why the verdicts differ")
        md_parts.append(_why_verdicts_differ(group).replace("<", "").replace(">", ""))
        md = PASSPORTS / f"{slug}.md"
        js = PASSPORTS / f"{slug}.json"
        md.write_text("\n".join(md_parts))
        payload = {
            "player_type": pt,
            "feature": feat,
            "targets": group.to_dict(orient="records"),
        }
        js.write_text(json.dumps(payload, indent=2, default=str))
        written.extend([md, js])
        public = without_kbb_outcome_target(group)
        if public is None or public.empty:
            public = group
        verdicts = public["verdict"].astype(str).unique().tolist()
        index.append(
            {
                "player_type": pt,
                "feature": feat,
                "display_name": display_name(feat, pt),
                "verdict": "Target-dependent" if len(verdicts) > 1 else verdicts[0],
                "blurb": (
                    "Different jobs depending on the target."
                    if len(verdicts) > 1
                    else takeaway(public.iloc[0])
                ),
                "slug": slug,
                "n_targets": int(len(public)),
            }
        )
    for stale in list(PASSPORTS.glob("hitter_*.md")) + list(PASSPORTS.glob("pitcher_*.md")):
        if stale.stem not in keep_slugs:
            stale.unlink(missing_ok=True)
            stale.with_suffix(".json").unlink(missing_ok=True)
    (PASSPORTS / "index.json").write_text(json.dumps(index, indent=2))
    return written
