"""Feature Universe Audit presentation. Does not change registry or exclusion artifacts."""

from __future__ import annotations

import html
import json
import math
import re
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
from psl.config import ARTIFACTS
from psl.site.labels import display_name, display_player, display_status

PIPELINE_STATUSES = frozenset({"TEST", "DERIVE_AND_TEST", "CONTEXT_ONLY_CANDIDATE"})

STATUS_PUBLIC = {
    "TEST": {
        "label": "Tested",
        "blurb": "Entered the feature-admission study directly.",
    },
    "DERIVE_AND_TEST": {
        "label": "Derived and tested",
        "blurb": "The raw field was transformed into a more meaningful baseball metric before testing.",
    },
    "CONTEXT_ONLY_CANDIDATE": {
        "label": "Context only",
        "blurb": "Used to adjust or interpret performance, but not treated as player skill.",
    },
    "STRUCTURAL_DUPLICATE": {
        "label": "Duplicate representation",
        "blurb": "The information was already captured more cleanly by another tested feature.",
    },
    "LEAKAGE": {
        "label": "Future leakage",
        "blurb": "Would contain information unavailable at the time of prediction.",
    },
    "UNAVAILABLE_RELIABLY": {
        "label": "Insufficient historical coverage",
        "blurb": "Too incomplete across players/seasons for the required temporal study.",
    },
    "INSUFFICIENT_COVERAGE": {
        "label": "Insufficient historical coverage",
        "blurb": "Too incomplete across players/seasons for the required temporal study.",
    },
    "IDENTIFIER": {
        "label": "Identifier / metadata",
        "blurb": "Needed to identify, join, or organize records rather than evaluate player ability.",
    },
    "NOT_BASEBALL_RELEVANT": {
        "label": "Not suitable as an independent player-skill feature",
        "blurb": (
            "May be baseball-related, but unsuitable for direct use as an independent skill input "
            "(for example counting outcomes, administrative fields, or team-dependent totals)."
        ),
    },
}

EXCLUSION_REASON_GROUPS = (
    ("LEAKAGE", "Future leakage", "Would use information that was not available at the prediction date."),
    (
        "STRUCTURAL_DUPLICATE",
        "Duplicate representation",
        "A cleaner or more comparable version of the same information was already tested.",
    ),
    (
        "UNAVAILABLE_RELIABLY",
        "Insufficient historical coverage",
        "The field was unavailable for too many players or seasons to support the required temporal validation.",
    ),
    (
        "INSUFFICIENT_COVERAGE",
        "Insufficient historical coverage",
        "The field was unavailable for too many players or seasons to support the required temporal validation.",
    ),
    (
        "IDENTIFIER",
        "Identifier / metadata",
        "Useful for constructing the dataset but not a player-skill feature.",
    ),
    (
        "CONTEXT_ONLY_CANDIDATE",
        "Context rather than skill",
        "Useful for adjusting or interpreting performance but not treated as player ability.",
    ),
    (
        "DERIVE_AND_TEST",
        "Better represented by a derived/rate metric",
        "A raw field was replaced or accompanied by a derived representation intended for testing.",
    ),
    (
        "NOT_BASEBALL_RELEVANT",
        "Not suitable as an independent player-skill feature",
        "Recorded as unsuitable for direct use as an independent skill feature in this study.",
    ),
    (
        "TEST",
        "Inventoried but not admitted to a component catalog",
        (
            "Kept in the registry with TEST status so it was not silently dropped, but it was not "
            "added to the hitting/pitching/baserunning/defense/overall candidate catalogs."
        ),
    ),
)

FAMILY_COMPONENT = {
    "defense": "Defense",
    "catcher": "Defense",
    "position": "Defense",
    "speed": "Baserunning",
    "k_bb_skill": "Pitching",
    "velocity": "Pitching",
    "movement": "Pitching",
    "spin": "Pitching",
    "stuff": "Pitching",
    "release": "Pitching",
    "pitch_mix": "Pitching",
    "command": "Pitching",
    "whiff_chase": "Pitching",
    "contact_suppression": "Pitching",
    "workload": "Pitching",
    "role": "Pitching",
    "expected": "Hitting",
    "plate_discipline": "Hitting",
    "contact_quality": "Hitting",
    "contact_ability": "Hitting",
    "power": "Hitting",
    "batted_ball": "Hitting",
    "platoon": "Hitting",
}


def _catalog_keys() -> dict[str, set[tuple[str, str]]]:
    return {
        "Hitting": {("hitter", s.name) for s in HITTER_FEATURES},
        "Pitching": {("pitcher", s.name) for s in PITCHER_FEATURES},
        "Baserunning": {("hitter", s.name) for s in BASERUNNING_FEATURES},
        "Defense": {("hitter", s.name) for s in DEFENSE_FEATURES},
        "Overall value": (
            {("hitter", s.name) for s in WAR_HITTER_FEATURES}
            | {("pitcher", s.name) for s in WAR_PITCHER_FEATURES}
        ),
    }


def load_registry(path: Path | None = None) -> pd.DataFrame:
    p = path or (ARTIFACTS / "feature_registry.csv")
    return pd.read_csv(p)


def load_exclusions(path: Path | None = None) -> pd.DataFrame:
    p = path or (ARTIFACTS / "excluded_features.csv")
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def public_status_label(status: str) -> str:
    info = STATUS_PUBLIC.get(str(status))
    if info:
        return info["label"]
    return display_status(status)


def fmt_coverage(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(x):
        return "n/a"
    if x <= 1.0:
        pct = 100.0 * x
    else:
        pct = float(x)
    if abs(pct - round(pct)) < 0.05:
        return f"{pct:.0f}%"
    return f"{pct:.1f}%"


def field_display(feature: str, player_type: str | None = None) -> str:
    raw = str(feature or "")
    pt = player_type
    name = raw
    if ":" in raw:
        left, right = raw.split(":", 1)
        if left in {"hitter", "pitcher"}:
            pt = left
            name = right
    shown = display_name(name, pt)
    # Avoid ugly "Hitter:last Observed Season" from display_name on prefixed ids
    if shown.lower().startswith("hitter:") or shown.lower().startswith("pitcher:"):
        shown = display_name(name, pt)
    return shown


def source_panel(player_type: str) -> str:
    return f"{display_player(player_type)} source panel"


def infer_components(player_type: str, feature: str, family: str, panel_column: str = "") -> list[str]:
    """Components this registry field can feed. Never invent unsupported components."""
    catalogs = _catalog_keys()
    keys = {
        (str(player_type), str(feature)),
        (str(player_type), str(panel_column or feature)),
    }
    out: list[str] = []
    for comp, members in catalogs.items():
        if keys & members:
            out.append(comp)
    fam = str(family or "")
    hinted = FAMILY_COMPONENT.get(fam)
    if hinted and hinted not in out:
        # Family hint only when it matches the source panel's natural game
        if hinted == "Pitching" and player_type == "pitcher":
            out.append(hinted)
        elif hinted in {"Hitting", "Baserunning", "Defense"} and player_type == "hitter":
            out.append(hinted)
        elif hinted == "Overall value":
            out.append(hinted)
    if not out:
        out.append("Shared / panel inventory")
    return out


def funnel_counts(reg: pd.DataFrame) -> dict[str, int]:
    n = int(len(reg))
    entered = int(reg["candidate_status"].isin(PIPELINE_STATUSES).sum())
    return {
        "reviewed": n,
        "entered_pipeline": entered,
        "not_directly_tested": n - entered,
    }


def status_summary(reg: pd.DataFrame) -> list[dict]:
    counts = reg["candidate_status"].value_counts().to_dict()
    rows = []
    order = [
        "TEST",
        "DERIVE_AND_TEST",
        "CONTEXT_ONLY_CANDIDATE",
        "STRUCTURAL_DUPLICATE",
        "LEAKAGE",
        "UNAVAILABLE_RELIABLY",
        "INSUFFICIENT_COVERAGE",
        "IDENTIFIER",
        "NOT_BASEBALL_RELEVANT",
    ]
    seen = set()
    for status in order:
        if status not in counts:
            continue
        seen.add(status)
        info = STATUS_PUBLIC[status]
        example = _example_for_status(reg, status)
        rows.append(
            {
                "status": status,
                "label": info["label"],
                "blurb": info["blurb"],
                "n": int(counts[status]),
                "example": example,
            }
        )
    for status, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if status in seen:
            continue
        rows.append(
            {
                "status": status,
                "label": public_status_label(status),
                "blurb": "Recorded in the registry with this status.",
                "n": int(n),
                "example": _example_for_status(reg, status),
            }
        )
    return rows


def _example_for_status(reg: pd.DataFrame, status: str) -> str:
    hit = reg[reg.candidate_status.astype(str).eq(status)]
    if hit.empty:
        return ""
    row = hit.iloc[0]
    return field_display(row["feature"], row["player_type"])


def exclusion_reason_summary(excl: pd.DataFrame) -> list[dict]:
    if excl.empty or "candidate_status" not in excl.columns:
        return []
    counts = excl["candidate_status"].astype(str).value_counts().to_dict()
    rows = []
    used = set()
    for status, label, meaning in EXCLUSION_REASON_GROUPS:
        if status not in counts:
            continue
        used.add(status)
        rows.append({"status": status, "label": label, "meaning": meaning, "n": int(counts[status])})
    for status, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if status in used:
            continue
        rows.append(
            {
                "status": status,
                "label": public_status_label(status),
                "meaning": "Recorded exclusion/accounting note for this registry status.",
                "n": int(n),
            }
        )
    return rows


_REASON_REWRITE = [
    (
        re.compile(r"team-dependent counting stat.*", re.I),
        "Not tested directly because the total depends heavily on playing time, lineup context, and teammate quality. More comparable rate-based measures were tested instead.",
    ),
    (
        re.compile(r"lineup-dependent counting stat.*", re.I),
        "Not tested as a raw counting statistic because lineup position and opportunities drive the total. Rate-based offensive measures are used instead.",
    ),
    (
        re.compile(r"iso/slg already capture.*", re.I),
        "Not tested as a standalone counting statistic. Extra-base power is represented with rate-based measures such as ISO and SLG, which are easier to compare across different amounts of playing time.",
    ),
    (
        re.compile(r"uses seasons after the prediction date.*", re.I),
        "Not eligible because it can reveal seasons occurring after the prediction date. Using it would leak future information into the model.",
    ),
    (
        re.compile(r"sample size behind the park factor.*", re.I),
        "This is the sample size used to estimate a park factor rather than a player characteristic. The actual park factor is used as context instead.",
    ),
    (
        re.compile(r"pa is the playing-time feature.*", re.I),
        "Playing time is already represented by plate appearances in the model, so this related counting field was not added as a separate skill input.",
    ),
    (
        re.compile(r"counting hits; avg.*", re.I),
        "Hit totals were not tested as a standalone counting statistic. Batting average already captures hits per at-bat, and playing-time-contaminated counts are avoided.",
    ),
    (
        re.compile(r"hr counts; iso.*", re.I),
        "Home-run counts were not tested as a standalone total. Rate-based power measures such as ISO and expected ISO are the representations under study.",
    ),
    (
        re.compile(r"discovered counting/context column.*", re.I),
        "Treated as counting or context information; a rate representation is preferred for comparing players with different amounts of playing time.",
    ),
    (
        re.compile(r"numeric source column was not in the original plan.*", re.I),
        "Inventoried so it would not be silently dropped. It was not added to a component candidate catalog because a clearer representation already existed or the field was not selected for admission testing.",
    ),
    (
        re.compile(r"sensitive demographic.*", re.I),
        "Not used as a projection input. Age, handedness, position, and role are the baseball context fields retained for adjustment.",
    ),
    (
        re.compile(r"join key or label.*", re.I),
        "Used to identify or join records rather than to measure player skill.",
    ),
]


def humanize_exclusion_reason(reason: str, status: str) -> str:
    text = " ".join(str(reason or "").split())
    if not text:
        return STATUS_PUBLIC.get(status, {}).get("blurb", "Recorded in the exclusion log.")
    for pattern, rewrite in _REASON_REWRITE:
        if pattern.match(text):
            return rewrite
    # Soften the NOT_BASEBALL_RELEVANT implication without inventing facts
    if status == "NOT_BASEBALL_RELEVANT":
        return (
            f"Not treated as an independent player-skill feature in this study. "
            f"Registry note: {text}"
        )
    if text.endswith("."):
        return text
    return text + "."


def registry_explorer_records(reg: pd.DataFrame) -> list[dict]:
    records = []
    for _, r in reg.iterrows():
        status = str(r.get("candidate_status") or "")
        comps = infer_components(
            str(r.get("player_type") or ""),
            str(r.get("feature") or ""),
            str(r.get("feature_family") or ""),
            str(r.get("panel_column") or ""),
        )
        records.append(
            {
                "field": field_display(r["feature"], r["player_type"]),
                "panel": source_panel(str(r["player_type"])),
                "components": comps,
                "status": status,
                "statusLabel": public_status_label(status),
                "why": humanize_exclusion_reason(str(r.get("reason") or ""), status),
                "coverage": fmt_coverage(r.get("overall_coverage")),
                "source": str(r.get("source") or ""),
                "search": " ".join(
                    [
                        field_display(r["feature"], r["player_type"]),
                        str(r.get("source") or ""),
                        public_status_label(status),
                        " ".join(comps),
                    ]
                ).lower(),
            }
        )
    records.sort(key=lambda item: item["field"].lower())
    return records


def exclusion_explorer_records(excl: pd.DataFrame) -> list[dict]:
    if excl.empty:
        return []
    feat_col = "Feature" if "Feature" in excl.columns else excl.columns[0]
    reason_col = "Reason excluded" if "Reason excluded" in excl.columns else excl.columns[1]
    src_col = "Data source" if "Data source" in excl.columns else "source"
    cov_col = "Coverage" if "Coverage" in excl.columns else "coverage"
    records = []
    for _, r in excl.iterrows():
        raw = str(r[feat_col])
        pt = None
        feat = raw
        if ":" in raw:
            pt, feat = raw.split(":", 1)
        status = str(r.get("candidate_status") or "")
        comps = infer_components(pt or "", feat, str(r.get("feature_family") or ""), feat)
        records.append(
            {
                "field": field_display(feat, pt),
                "panel": source_panel(pt) if pt else "Shared / panel inventory",
                "components": comps,
                "status": status,
                "statusLabel": public_status_label(status),
                "why": humanize_exclusion_reason(str(r[reason_col]), status),
                "coverage": fmt_coverage(r.get(cov_col)),
                "source": str(r.get(src_col) or ""),
                "search": " ".join(
                    [
                        field_display(feat, pt),
                        str(r.get(src_col) or ""),
                        public_status_label(status),
                    ]
                ).lower(),
            }
        )
    records.sort(key=lambda item: item["field"].lower())
    return records


def reconcile_funnel(reg: pd.DataFrame) -> None:
    counts = funnel_counts(reg)
    assert counts["reviewed"] == counts["entered_pipeline"] + counts["not_directly_tested"]


def render_universe_audit_html(
    reg: pd.DataFrame | None = None,
    excl: pd.DataFrame | None = None,
) -> str:
    if reg is None:
        path = ARTIFACTS / "feature_registry.csv"
        if not path.exists():
            return "<p>Feature audit not generated yet.</p>"
        reg = load_registry(path)
    if excl is None:
        excl = load_exclusions()
    reconcile_funnel(reg)
    funnel = funnel_counts(reg)
    statuses = status_summary(reg)
    reasons = exclusion_reason_summary(excl)
    registry_records = registry_explorer_records(reg)
    exclusion_records = exclusion_explorer_records(excl)

    status_cards = "".join(
        f"""<article class="audit-card">
          <h3>{html.escape(row['label'])}</h3>
          <p class="audit-count">{row['n']}</p>
          <p>{html.escape(row['blurb'])}</p>
          <p class="note-inline">Example: {html.escape(row['example'] or 'n/a')}</p>
        </article>"""
        for row in statuses
    )
    reason_rows = "".join(
        "<tr>"
        f"<td><strong>{html.escape(row['label'])}</strong></td>"
        f"<td>{row['n']}</td>"
        f"<td>{html.escape(row['meaning'])}</td>"
        "</tr>"
        for row in reasons
    )
    payload = json.dumps(
        {
            "registry": registry_records,
            "exclusions": exclusion_records,
        },
        ensure_ascii=True,
    ).replace("<", "\\u003c")

    return f"""
    <h1 class="page-title">Feature Universe Audit</h1>
    <p class="lede"><b>Did we cherry-pick the metrics we tested?</b></p>
    <p>No. Before evaluating which metrics belonged in a projection, we inventoried the fields available in the project’s defined data sources. Each field had to be accounted for: test it, use it only as context, derive a more meaningful version, or record why it was not eligible for testing. Metrics were not removed simply because they produced weak results.</p>
    <div class="callout">
      <p><b>An exclusion is not a bad result.</b> A field may be left out because it would leak future information, duplicates another variable, is an identifier rather than baseball information, has unreliable historical coverage, or is better represented by another metric.</p>
    </div>
    <div class="callout callout-soft">
      <p><b>Weak and negative results remain in the study.</b> A metric failing to earn Projection status is not removed from the record. Exclusion decisions are based on data validity, leakage, representation, coverage, or modeling relevance — not whether a metric happened to improve the final model.</p>
    </div>

    <h2>What this inventory covers</h2>
    <p>The registry inventories source fields from the project’s defined <b>hitter</b> and <b>pitcher</b> panels ({funnel['reviewed']} rows). Baserunning, defense, and overall-value candidates are drawn from those panels and listed in the component catalogs; they are not a separate third/fourth/fifth raw-source dump. The five public projection questions still apply after a field becomes an eligible candidate.</p>
    <p><b>Feature-universe decisions happen before the admission verdict.</b> First we ask whether a field can be validly studied as a candidate. Then, for eligible candidates, we ask whether it earns Projection, Diagnostic, Context, Exclude, or Insufficient Evidence status for a specific target.</p>

    <div class="audit-flow" aria-label="Feature universe versus admission verdicts">
      <div class="audit-flow-step"><strong>Defined source fields</strong></div>
      <div class="audit-flow-arrow" aria-hidden="true">↓</div>
      <div class="audit-flow-step"><strong>Data / model eligibility review</strong></div>
      <div class="audit-flow-arrow" aria-hidden="true">↓</div>
      <div class="audit-flow-row">
        <div class="audit-flow-step">Test / derive</div>
        <div class="audit-flow-step">Context</div>
        <div class="audit-flow-step">Not directly tested<br/><span class="note-inline">Leakage · Duplicate · Coverage · Metadata · Representation</span></div>
      </div>
      <div class="audit-flow-arrow" aria-hidden="true">↓</div>
      <div class="audit-flow-step"><strong>Feature-admission study</strong><br/><span class="note-inline">Projection / Diagnostic / Context / Exclude / Insufficient Evidence</span></div>
      <p class="note-inline">Pre-test exclusion reasons are not the same as post-test admission verdicts.</p>
    </div>

    <h2>Feature funnel</h2>
    <p class="note-inline">Mapping: reviewed = all registry rows; entered the research pipeline = Tested + Derived and tested + Context only; not directly tested = all other registry statuses. The exclusion log below lists fields that were not added to a component candidate catalog.</p>
    <div class="funnel">
      <div class="funnel-step">
        <span class="audit-count">{funnel['reviewed']}</span>
        <strong>Source fields reviewed</strong>
        <p>Every field found in the defined project sources was assigned a research status.</p>
      </div>
      <div class="funnel-arrow" aria-hidden="true">↓</div>
      <div class="funnel-step">
        <span class="audit-count">{funnel['entered_pipeline']}</span>
        <strong>Entered the research pipeline</strong>
        <p>Fields tested directly, used as context, or transformed into meaningful testable metrics.</p>
      </div>
      <div class="funnel-arrow" aria-hidden="true">↓</div>
      <div class="funnel-step">
        <span class="audit-count">{funnel['not_directly_tested']}</span>
        <strong>Not directly tested</strong>
        <p>Every omission in this group has a recorded registry status and reason.</p>
      </div>
    </div>

    <h2>What happened to each field?</h2>
    <div class="audit-grid">{status_cards}</div>

    <h2>Why some fields were not added to a component catalog</h2>
    <p><b>These fields are not part of the metrics involved in any of the five skill categories</b> — Hitting, Pitching, Baserunning, Defense, or Overall value.</p>
    <p>These counts come from the exclusion log ({len(excl)} rows): registry fields that were not members of the hitting, pitching, baserunning, defense, or overall-value candidate catalogs. This is a pre-test accounting step, not a post-test admission verdict.</p>
    <table>
      <thead><tr><th>Reason</th><th>Number of fields</th><th>What it means</th></tr></thead>
      <tbody>{reason_rows}</tbody>
    </table>

    <details class="audit-details">
      <summary>View all excluded fields ({len(exclusion_records)})</summary>
      <div class="audit-tools">
        <label for="excl-search">Search excluded fields</label>
        <input id="excl-search" type="search" placeholder="Search field, source, or reason" autocomplete="off"/>
      </div>
      <p class="note-inline" title="Share of eligible player-seasons for which this field was available.">Historical coverage is the share of eligible player-seasons for which this field was available.</p>
      <div class="table-scroll">
        <table id="excl-table">
          <thead><tr>
            <th>Field</th>
            <th>Component</th>
            <th>Why it was not tested</th>
            <th title="Share of eligible player-seasons for which this field was available.">Historical coverage</th>
            <th>Source</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <p class="passport-empty" id="excl-empty" hidden>No excluded fields match that search.</p>
    </details>

    <h2>Explore the feature universe</h2>
    <p>Search and filter every registry row.</p>
    <div class="audit-tools audit-tools-grid">
      <div>
        <label for="reg-search">Search field or source</label>
        <input id="reg-search" type="search" placeholder="Search field or source…" autocomplete="off"/>
      </div>
      <div>
        <label for="reg-component">Component</label>
        <select id="reg-component">
          <option value="">All</option>
          <option>Hitting</option>
          <option>Pitching</option>
          <option>Baserunning</option>
          <option>Defense</option>
          <option>Overall value</option>
          <option>Shared / panel inventory</option>
        </select>
      </div>
      <div>
        <label for="reg-status">Research status</label>
        <select id="reg-status">
          <option value="">All</option>
          <option value="Tested">Tested</option>
          <option value="Context only">Context only</option>
          <option value="Derived and tested">Derived and tested</option>
          <option value="Future leakage">Future leakage</option>
          <option value="Duplicate representation">Duplicate representation</option>
          <option value="Insufficient historical coverage">Insufficient historical coverage</option>
          <option value="Identifier / metadata">Identifier / metadata</option>
          <option value="Not suitable as an independent player-skill feature">Not suitable as an independent player-skill feature</option>
        </select>
      </div>
    </div>
    <div class="table-scroll">
      <table id="reg-table">
        <thead><tr>
            <th>Field</th>
            <th>Component</th>
            <th>Research decision</th>
            <th>Why</th>
            <th title="Share of eligible player-seasons for which this field was available.">Historical coverage</th>
            <th>Source</th>
          </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <p class="passport-empty" id="reg-empty" hidden>No registry fields match those filters.</p>

    <script type="application/json" id="universe-data">{payload}</script>
    <script>
    (function(){{
      var raw = document.getElementById("universe-data");
      if (!raw) return;
      var data = JSON.parse(raw.textContent);
      function componentLabel(comps) {{
        var list = (comps || []).filter(function(c) {{ return c !== "Shared / panel inventory"; }});
        return list.length ? list.join(", ") : "";
      }}
      function addCell(tr, text, title) {{
        var td = document.createElement("td");
        td.textContent = text == null ? "" : String(text);
        if (title) td.title = title;
        tr.appendChild(td);
      }}
      function fillTable(tableId, emptyId, rows, mode) {{
        var table = document.getElementById(tableId);
        var empty = document.getElementById(emptyId);
        if (!table) return;
        var body = table.querySelector("tbody");
        body.replaceChildren();
        rows.forEach(function(r) {{
          var tr = document.createElement("tr");
          if (mode === "excl") {{
            addCell(tr, r.field);
            addCell(tr, componentLabel(r.components));
            addCell(tr, r.why);
            addCell(tr, r.coverage);
            addCell(tr, r.source);
          }} else {{
            addCell(tr, r.field);
            addCell(tr, (r.components || []).join(", "));
            addCell(tr, r.statusLabel);
            addCell(tr, r.why);
            addCell(tr, r.coverage);
            addCell(tr, r.source);
          }}
          body.appendChild(tr);
        }});
        if (empty) empty.hidden = rows.length > 0;
      }}
      function filterExcl() {{
        var q = (document.getElementById("excl-search").value || "").toLowerCase().trim();
        var rows = data.exclusions.filter(function(r) {{
          return !q || (r.search || "").indexOf(q) !== -1 || (r.why || "").toLowerCase().indexOf(q) !== -1;
        }});
        fillTable("excl-table", "excl-empty", rows, "excl");
      }}
      function filterReg() {{
        var q = (document.getElementById("reg-search").value || "").toLowerCase().trim();
        var comp = document.getElementById("reg-component").value;
        var status = document.getElementById("reg-status").value;
        var rows = data.registry.filter(function(r) {{
          if (q && (r.search || "").indexOf(q) === -1 && (r.why || "").toLowerCase().indexOf(q) === -1) return false;
          if (status && r.statusLabel !== status) return false;
          if (comp && (r.components || []).indexOf(comp) === -1) return false;
          return true;
        }});
        fillTable("reg-table", "reg-empty", rows, "reg");
      }}
      var exclSearch = document.getElementById("excl-search");
      if (exclSearch) exclSearch.addEventListener("input", filterExcl);
      ["reg-search", "reg-component", "reg-status"].forEach(function(id) {{
        var el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("input", filterReg);
        el.addEventListener("change", filterReg);
      }});
      filterExcl();
      filterReg();
    }})();
    </script>
    """
