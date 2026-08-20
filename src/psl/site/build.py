"""Static research site generated from artifacts. Display names only in the public UI."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import pandas as pd

from psl.admission.engine import VERDICT_PUBLIC_COPY
from psl.catalog import (
    BASERUNNING_FEATURES,
    DEFENSE_FEATURES,
    HITTER_FEATURES,
    PITCHER_FEATURES,
    FeatureSpec,
)
from psl.config import ARTIFACTS, DATA_PROCESSED, FIGURES, RESEARCH_DIR
from psl.site.labels import (
    admitted_model_rmse,
    belongs_on_component,
    component_phrase,
    display_name,
    fmt_model_impact,
    metric_primary_component,
    display_player,
    display_status,
    passport_blurb,
    target_phrase,
    target_section_id,
    verdict_for_target,
    without_kbb_outcome_target,
)
from psl.site.metric_glossary import MODEL_VALIDATION_TERMS, glossary_description
from psl.site.universe_audit import render_universe_audit_html
from psl.site.methodology_copy import render_methodology_html
from psl.site.table_copy import (
    audit_table_copy,
    context_adjusts_for,
    context_why_matters,
    diagnostic_group,
    GROUP_ORDER,
    projection_role,
    relationship_label,
    table_why,
)

NAV = [
    ("index.html", "Findings"),
    ("hitters.html", "Hitting"),
    ("pitchers.html", "Pitching"),
    ("baserunning.html", "Baserunning"),
    ("defense.html", "Defense"),
    ("overall.html", "Overall Value"),
    ("passports.html", "Passports"),
    ("models.html", "Models"),
    ("feature-audit.html", "Feature Audit"),
    ("methodology.html", "Methodology"),
]


def _nav(current: str, prefix: str = "") -> str:
    links = []
    for href, label in NAV:
        cls = ' class="active"' if href == current else ""
        links.append(f'<a href="{prefix}{href}"{cls}>{label}</a>')
    return "\n".join(links)


def _page(title: str, current: str, body: str, prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title} · Projection Signal Lab</title>
  <link rel="stylesheet" href="{prefix}style.css"/>
</head>
<body>
  <header>
    <div class="brand">Projection Signal Lab</div>
    <div class="sub">Which metrics predict future performance — and which are better used to understand it?</div>
    <nav>{_nav(current, prefix)}</nav>
  </header>
  <main>
  {_glossary_chrome()}
  {body}
  </main>
  <footer>Public pages use display names for metrics and fields.</footer>
  <script>
  (function(){{
    function bindGlossary(btnId, panelId, key, closedLabel, openLabel) {{
      var btn = document.getElementById(btnId);
      var panel = document.getElementById(panelId);
      if (!btn || !panel) return;
      function setOpen(open) {{
        panel.hidden = !open;
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        btn.textContent = open ? openLabel : closedLabel;
        try {{ sessionStorage.setItem(key, open ? "1" : "0"); }} catch (e) {{}}
      }}
      btn.addEventListener("click", function() {{ setOpen(panel.hidden); }});
      try {{ if (sessionStorage.getItem(key) === "1") setOpen(true); }} catch (e) {{}}
    }}
    bindGlossary("metrics-glossary-toggle", "metrics-glossary", "psl-metrics-glossary-open", "Open Metrics Glossary", "Hide Metrics Glossary");
    bindGlossary("glossary-toggle", "verdict-glossary", "psl-glossary-open", "What the verdicts mean", "Hide Verdict Glossary");
    document.querySelectorAll('a[href="#metrics-glossary"]').forEach(function(link) {{
      link.addEventListener("click", function(e) {{
        e.preventDefault();
        var btn = document.getElementById("metrics-glossary-toggle");
        var panel = document.getElementById("metrics-glossary");
        if (btn && panel && panel.hidden) btn.click();
        if (panel) panel.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }});
    }});
    function fillMetricPanel(el, html) {{
      if (!el) return;
      if (!html) {{
        el.innerHTML = '<p class="placeholder">Hover a metric on the chart to see details here.</p>';
        return;
      }}
      var parts = String(html).replace(/<\\/?b>/g, "").split(/<br\\s*\\/?>/i).map(function(s){{ return s.trim(); }}).filter(Boolean);
      var title = parts.shift() || "";
      var rows = parts.map(function(line) {{
        var idx = line.indexOf(":");
        if (idx === -1) return "<dt>Verdict</dt><dd>" + line + "</dd>";
        return "<dt>" + line.slice(0, idx) + "</dt><dd>" + line.slice(idx + 1).trim() + "</dd>";
      }}).join("");
      el.innerHTML = "<h3>" + title + "</h3><dl>" + rows + "</dl>";
    }}
    window.addEventListener("message", function(ev) {{
      var data = ev.data || {{}};
      if (data.type !== "psl-metric-panel") return;
      fillMetricPanel(document.getElementById(data.panel), data.html);
    }});
  }})();
  </script>
</body>
</html>
"""


CSS = """
:root { --ink:#15202b; --muted:#5c6b73; --bg:#f6f1e8; --card:#fffdf8; --line:#d7cfc2; --accent:#1b4d3e; }
* { box-sizing:border-box; }
body { margin:0; font-family: "Iowan Old Style", Palatino, Georgia, serif; background:var(--bg); color:var(--ink); }
header { padding:28px 8vw 10px; border-bottom:1px solid var(--line); background:#efe7d6; }
.brand { font-size:clamp(22px, 4vw, 28px); font-weight:700; }
.sub { color:var(--muted); margin-top:4px; }
nav { margin-top:16px; display:flex; gap:16px; flex-wrap:wrap; }
nav a { color:var(--ink); text-decoration:none; font-size:14px; letter-spacing:.02em; }
nav a.active { border-bottom:2px solid var(--accent); font-weight:700; }
main { padding:28px 4vw 64px; max-width:1320px; }
footer { padding:24px 8vw; color:var(--muted); font-size:13px; border-top:1px solid var(--line); }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:18px 0 28px; }
.card { background:var(--card); border:1px solid var(--line); padding:16px; }
.card b { display:block; font-size:28px; }
.lede { font-size:clamp(18px, 2.4vw, 20px); line-height:1.45; max-width:46rem; }
.note { background:var(--card); border-left:3px solid var(--accent); padding:12px 16px; margin:16px 0 24px; max-width:48rem; }
.findings li { margin: 0 0 1rem; max-width: 46rem; }
.findings .tech { color:var(--muted); font-size:0.92rem; margin-top:0.35rem; }
.findings a { color: var(--accent); }
table { border-collapse:collapse; width:100%; font-size:14px; background:var(--card); }
th, td { border-bottom:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }
th { font-variant:small-caps; letter-spacing:.04em; }
td.impact { max-width: 28rem; }
td.why { max-width: 38rem; }
td.rel { white-space: nowrap; color: var(--muted); }
tr.group-row th {
  background: #efe7d6;
  font-variant: small-caps;
  letter-spacing: .04em;
  padding-top: 14px;
  border-bottom: 1px solid var(--line);
}
.iframe { width:100%; height:min(70vh, 640px); min-height:420px; border:1px solid var(--line); background:white; }
.chart-with-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 16px;
  align-items: stretch;
  margin: 0 0 1.4rem;
}
.chart-with-panel .iframe { margin: 0; height: min(70vh, 640px); }
.chart-with-panel-jobs {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
}
.chart-with-panel-jobs .iframe {
  flex: 1 0 720px;
  height: 720px;
  min-height: 640px;
}
.chart-with-panel-jobs .metric-panel {
  flex: 0 0 240px;
  max-width: 260px;
}
.metric-panel {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 18px 16px;
  min-height: 220px;
}
.metric-panel h3 { margin: 0 0 12px; font-size: 1.25rem; line-height: 1.2; }
.metric-panel .placeholder { color: var(--muted); margin: 0; }
.metric-panel dl { margin: 0; }
.metric-panel dt { color: var(--muted); font-size: 0.88rem; margin-top: 10px; }
.metric-panel dd { margin: 3px 0 0; }
@media (max-width: 860px) {
  .chart-with-panel { grid-template-columns: 1fr; }
  .chart-with-panel-jobs .iframe { flex-basis: 100%; }
  .chart-with-panel-jobs .metric-panel { flex: 1 1 100%; max-width: none; }
}
.iframe-deps { height: min(58vh, 520px); min-height: 380px; }
.iframe-deps-pitcher { height: 300px; min-height: 260px; }
.iframe-heat { height: min(80vh, 720px); }
.iframe-dropone { height: 380px; min-height: 320px; }
.iframe-coef { height: 780px; min-height: 640px; }
.iframe-cov { height: min(92vh, 1400px); min-height: 480px; }
.diag-caption { color: var(--muted); max-width: 46rem; margin: 0.2rem 0 0.75rem; }
.diag-copy { color: var(--muted); max-width: 46rem; }
.diag-copy p { margin: 0.45rem 0 0.75rem; line-height: 1.45; }
.diag-block h3 { margin-bottom: 0.2rem; }
.diag-block h4 { margin: 1rem 0 0.35rem; font-size: 1rem; }
.diag-link { font-size: 14px; margin: 0 0 10px; }
.diag-link a { color: var(--ink); }
.verdict { font-weight:700; }
.Projection { color:#1b4d3e; }
.Augmented { color:#2f6f9f; }
.Diagnostic { color:#b86b2a; }
.Context { color:#6b5b95; }
.Exclude { color:#7a7a7a; }
.Insufficient { color:#c4a035; }
h2 { margin-top:2.2rem; }
h3 { margin-top:1.4rem; }
code { font-family: ui-monospace, Menlo, monospace; font-size:12px; }
details.diagnostics { margin: 1.5rem 0; border: 1px solid var(--line); background: var(--card); padding: 8px 14px 14px; }
details.diagnostics summary { cursor: pointer; font-weight: 700; padding: 8px 0; }
.passport-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
.passport-card { background:var(--card); border:1px solid var(--line); padding:16px; display:flex; flex-direction:column; gap:6px; }
.passport-card.is-hidden { display:none; }
.passport-card.is-match { border-color: var(--accent); }
.passport-card a { color:var(--ink); text-decoration:none; font-weight:700; font-size:1.05rem; }
.passport-card a:hover { text-decoration:underline; }
.passport-card .meta { color:var(--muted); font-size:0.9rem; }
.passport-card .why { margin: 0; line-height:1.4; }
.passport-search { margin: 0 0 1rem; }
.passport-empty { color: var(--muted); margin: 0 0 1rem; }
.map-legend { max-width:46rem; }
.passport-scatter { width: 100%; max-width: 28rem; height: auto; margin: 8px 0 8px; background: #fff; border: 1px solid var(--line); }
.passport-figure { margin: 10px 0 14px; }
.passport-figure figcaption { max-width: 40rem; }
.passport-figure .k {
  display: block;
  font-size: 11px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 2px;
}
.passport-figure .axis-note,
.passport-figure .how-read,
.passport-figure .raw-unique,
.passport-figure .raw-label {
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.4;
}
main dl dt { font-weight: 700; margin-top: 0.75rem; }
main dl dd { margin: 0.15rem 0 0; }
.glossary-bar { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; }
.glossary-toggle {
  display: inline-block;
  margin: 0;
  padding: 8px 14px;
  border: 1px solid var(--line);
  background: var(--card);
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .02em;
  color: var(--ink);
  cursor: pointer;
}
.glossary-toggle:hover { border-color: var(--accent); }
.glossary-panel {
  display: none;
  margin: 0 0 28px;
  padding: 0 0 8px;
  border-bottom: 1px solid var(--line);
}
.glossary-panel:not([hidden]) { display: block; }
#metrics-glossary { max-height: min(70vh, 42rem); overflow: auto; }
#metrics-glossary h3 { margin: 1.15rem 0 0.4rem; }
#metrics-glossary h3:first-of-type { margin-top: 0.6rem; }
#metrics-glossary .glossary-note {
  margin: 0 0 0.85rem;
  max-width: 46rem;
  line-height: 1.45;
  font-size: 14px;
}
#metrics-glossary .glossary-note a { color: var(--accent); text-decoration: underline; }
.passport-detail { max-width: 52rem; }
.passport-detail h1 { margin: 0.4rem 0 0.35rem; }
.passport-detail .kicker { color: var(--muted); margin: 0 0 0.6rem; }
.passport-detail .lede { margin: 0 0 1rem; max-width: 44rem; }
.passport-detail dl { display: grid; grid-template-columns: minmax(10rem, 38%) 1fr; gap: 8px 16px; margin: 0 0 1.2rem; }
.passport-detail dt { color: var(--muted); }
.passport-detail dd { margin: 0; }
.back-link { display: inline-block; margin: 0 0 12px; color: var(--ink); }
.target-card { background: var(--card); border: 1px solid var(--line); padding: 14px 16px 16px; margin: 12px 0 20px; scroll-margin-top: 12px; }
.target-card h4 { margin: 12px 0 6px; font-size: 0.95rem; letter-spacing: .04em; text-transform: uppercase; }
.target-card .forecast-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
}
.target-card .target-line { margin: 2px 0 8px; color: var(--muted); }
.target-card .verdict-line { margin: 0 0 6px; }
.target-card .decision { margin: 0 0 10px; font-weight: 700; }
.target-card .peer-rank {
  margin: 0 0 12px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  background: #fff;
  line-height: 1.35;
}
.target-card .peer-rank .k {
  display: block;
  font-size: 11px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 2px;
}
.target-card .peer-rank strong { font-size: 1.15rem; margin-right: 6px; }
.target-card .peer-rank .peer-field { color: var(--muted); font-size: 14px; }
.target-card .why-verdict { margin: 0 0 10px; line-height: 1.45; max-width: 44rem; }
.evidence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 10px;
  margin: 0 0 12px;
}
.evidence-chip {
  border: 1px solid var(--line);
  background: #fffdf8;
  padding: 10px 12px;
}
.evidence-chip .k {
  display: block;
  font-size: 11px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 4px;
}
.evidence-chip strong { display: block; margin: 0 0 4px; font-size: 15px; }
.evidence-chip p { margin: 0; font-size: 13px; line-height: 1.35; color: var(--ink); }
.takeaway {
  border-top: 1px solid var(--line);
  padding-top: 10px;
  margin: 4px 0 10px;
}
.takeaway .k {
  display: block;
  font-size: 11px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 4px;
}
.takeaway p { margin: 0; font-weight: 700; line-height: 1.4; }
.tech-details { margin-top: 8px; }
.tech-details summary {
  cursor: pointer;
  font-weight: 700;
  margin-bottom: 8px;
}
.tech-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tech-table th {
  text-align: left;
  color: var(--muted);
  font-weight: 500;
  padding: 4px 10px 4px 0;
  width: 42%;
  vertical-align: top;
}
.tech-table td { padding: 4px 0; vertical-align: top; }
.page-title { font-size: clamp(1.6rem, 3vw, 2rem); margin: 0 0 0.4rem; }
.callout {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 12px 16px;
  margin: 0 0 14px;
  max-width: 48rem;
}
.callout-soft { background: #fffdf8; }
.funnel { max-width: 40rem; margin: 0 0 1.4rem; }
.funnel-step {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 14px 16px;
}
.funnel-arrow { text-align: center; font-size: 1.2rem; margin: 6px 0; color: var(--muted); }
.audit-count { display: block; font-size: 1.8rem; font-weight: 700; margin: 0 0 4px; }
.audit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 12px;
  margin: 0 0 1.4rem;
}
.audit-card {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 12px 14px;
}
.audit-card h3 { margin: 0 0 6px; font-size: 1rem; }
.audit-card p { margin: 0 0 6px; font-size: 14px; line-height: 1.4; }
.audit-details { margin: 1rem 0 1.4rem; }
.audit-details summary { cursor: pointer; font-weight: 700; margin-bottom: 10px; }
.audit-tools { margin: 0 0 10px; max-width: 28rem; }
.audit-tools label {
  display: block;
  font-size: 12px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 4px;
}
.audit-tools input,
.audit-tools select {
  width: 100%;
  font-family: inherit;
  font-size: 15px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
}
.audit-tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 12px;
  max-width: none;
  margin: 0 0 12px;
}
.table-scroll { overflow-x: auto; margin: 0 0 12px; }
.audit-flow {
  max-width: 48rem;
  margin: 0 0 1.4rem;
  padding: 14px 16px;
  border: 1px solid var(--line);
  background: var(--card);
}
.audit-flow-step {
  padding: 8px 10px;
  border: 1px solid var(--line);
  background: #fff;
  text-align: center;
  font-size: 14px;
}
.audit-flow-arrow { text-align: center; color: var(--muted); margin: 6px 0; }
.audit-flow-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
@media (max-width: 720px) {
  .audit-flow-row { grid-template-columns: 1fr; }
}
.methodology { max-width: 46rem; }
.methodology h2 { margin-top: 2rem; }
.methodology h3 { margin-top: 1.35rem; margin-bottom: 0.45rem; }
.methodology p { line-height: 1.5; }
.methodology ul,
.methodology ol { line-height: 1.5; }
.method-question {
  font-style: italic;
  border-left: 3px solid var(--accent);
  padding-left: 12px;
  margin: 0.85rem 0 1.1rem;
}
.map-filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; }
.map-filters button {
  font-family: inherit; font-size: 14px; padding: 6px 12px;
  border: 1px solid var(--line); background: var(--card); cursor: pointer;
}
.map-filters button.active { border-color: var(--accent); font-weight: 700; }
.jobs { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 16px 0 28px; }
.jobs .card b { font-size: 18px; }
.jobs-hero { margin: 0 0 1.6rem; padding: 0 0 1.2rem; border-bottom: 1px solid var(--line); }
.jobs-hero h1 {
  font-size: clamp(26px, 4vw, 38px);
  line-height: 1.05;
  letter-spacing: -0.03em;
  margin: 0 0 0.4rem;
}
.jobs-hero > .lede { max-width: 42rem; margin: 0 0 0.85rem; font-size: 16px; line-height: 1.4; }
.hero-pick label {
  display: block;
  font-size: 12px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 4px;
}
.hero-pick input {
  width: min(100%, 28rem);
  font-family: inherit;
  font-size: 16px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
}
.hero-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 0.7rem; }
.hero-chip {
  font-family: inherit;
  font-size: 13px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}
.hero-chip:hover { border-color: var(--accent); }
.hero-chip.active { border-color: var(--accent); background: var(--card); font-weight: 700; }
.hero-result-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 16px;
  flex-wrap: wrap;
  margin: 0 0 6px;
}
.hero-metric-name {
  font-size: clamp(18px, 2.4vw, 24px);
  letter-spacing: .08em;
  text-transform: uppercase;
  margin: 0;
}
.hero-passport {
  margin: 0;
  font-size: 14px;
}
.hero-passport a { color: var(--ink); font-weight: 700; text-decoration: none; }
.hero-passport a:hover { text-decoration: underline; }
.hero-primary {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 12px 16px 14px;
  margin: 0 0 10px;
}
.hero-primary-meta {
  display: grid;
  grid-template-columns: minmax(7.5rem, 0.7fr) minmax(12rem, 1.5fr) auto;
  gap: 8px 18px;
  margin: 0 0 8px;
  align-items: start;
}
.hero-primary-meta .k {
  display: block;
  font-size: 11px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 2px;
}
.hero-primary-meta .v { margin: 0; font-size: 16px; line-height: 1.25; }
.hero-primary .verdict {
  font-size: clamp(18px, 2vw, 22px);
  letter-spacing: .03em;
  text-transform: uppercase;
  line-height: 1.1;
}
.hero-primary .why { margin: 0; font-size: 15px; line-height: 1.35; max-width: 46rem; }
.hero-notable {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.35;
  max-width: 46rem;
  color: var(--accent);
}
.hero-also { margin: 0; }
.hero-also-label {
  font-size: 12px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 6px;
}
.hero-pills { display: flex; flex-wrap: wrap; gap: 6px; }
a.hero-pill {
  display: inline-block;
  font-size: 13px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  background: var(--card);
  color: inherit;
  text-decoration: none;
}
a.hero-pill:hover, a.hero-pill[aria-expanded="true"] { border-color: var(--accent); }
.hero-pill-detail {
  margin: 8px 0 0;
  padding: 8px 12px;
  border-left: 3px solid var(--accent);
  background: var(--card);
  font-size: 14px;
  line-height: 1.35;
  max-width: 46rem;
}
.hero-pill-detail p { margin: 0 0 6px; }
.hero-pill-detail a { color: var(--ink); font-weight: 700; }
@media (max-width: 700px) {
  .hero-primary-meta { grid-template-columns: 1fr; }
}
.projecting { margin: 0 0 2.2rem; }
.projecting .jobs { margin-top: 12px; }
.projecting .card span { color: var(--muted); font-size: 13px; }
.projecting .card .window { display: block; color: var(--muted); font-size: 13px; margin-top: 8px; }
.thesis { font-size: clamp(18px, 2.4vw, 22px); line-height: 1.4; max-width: 40rem; margin: 0 0 1.6rem; }
@media (max-width: 700px) {
  main { padding: 20px 5vw 48px; }
  .iframe { height: 460px; min-height: 360px; }
  table { font-size: 13px; }
}
"""


def _verdict_class(verdict: str) -> str:
    return (verdict or "").split()[0]


def _metric_cell(player_type: str, feature: str, note: str = "") -> str:
    name = display_name(feature, player_type)
    if note:
        return f'<span title="{html.escape(note)}">{html.escape(name)}</span>'
    return html.escape(name)


def _kitchen_blurb() -> str:
    h_path = ARTIFACTS / "kitchen_sink_comparison_hitter.json"
    p_path = ARTIFACTS / "kitchen_sink_comparison_pitcher.json"
    h = json.loads(h_path.read_text()) if h_path.exists() else {}
    p = json.loads(p_path.read_text()) if p_path.exists() else {}
    h_adm = h.get("admitted_rmse")
    h_kit = h.get("kitchen_rmse")
    p_adm = p.get("admitted_rmse")
    p_kit = p.get("kitchen_rmse")
    return f"""
    <p>The admitted-feature model generalized better than the 56-feature all-feature model
    (RMSE {h_adm and f'{h_adm:.5f}'} vs {h_kit and f'{h_kit:.5f}'}); uncertainty around the difference excluded zero.</p>
    <p>The admitted-feature model was slightly better on average than the 57-feature all-feature model
    (RMSE {p_adm and f'{p_adm:.5f}'} vs {p_kit and f'{p_kit:.5f}'}), but uncertainty included zero,
    so the study does not support a clear difference.</p>
    """


def _verdict_glossary_body() -> str:
    items = "".join(
        f"<tr><td class=\"verdict {k.split()[0]}\">{k}</td><td>{v}</td></tr>"
        for k, v in VERDICT_PUBLIC_COPY.items()
    )
    return f"""
    <table><thead><tr><th>Verdict</th><th>Plain language</th></tr></thead><tbody>{items}</tbody></table>
    <p>Insufficient Evidence is not Exclude. Exclude means the study suggests the feature should not be used.
    Insufficient Evidence means the study cannot confidently decide yet.</p>
    <h2>Future correlation is not admission</h2>
    <p>Future correlation measures how strongly a metric in one season is associated with the player's
    performance the following season. Values range from −1 to +1. Positive values mean higher metric values
    tend to accompany higher future target values; negative values mean the opposite. A correlation near
    zero means little linear relationship.</p>
    <p>For targets where lower is better, especially FIP, a negative correlation can be the useful direction:
    higher velocity associated with lower (better) future FIP is not a “bad” relationship. Positive is not
    automatically good. A correlation is not a percentage of performance explained, not a causal effect,
    and not feature importance.</p>
    <p>Partial correlation asks how much of that linear association remains after the target-specific baseline.
    Drop-one out-of-sample importance asks whether the admitted forecast actually gets worse without the metric.
    Admission still requires out-of-time RMSE lift, stability, redundancy, coverage, and subgroup checks.</p>
    <h2>How a metric gets each verdict</h2>
    <p>Skill metrics all take the same test. The metric is added to a strong baseline (age, playing time,
    multi-year performance, park) and used to predict next-season wOBA or FIP in an expanding window.
    A metric <i>passes the prediction test</i> only if it improves out-of-time RMSE by at least 0.5% of
    baseline RMSE, in at least 3 future-season windows, and either the 95% CI excludes zero or it improves
    in at least 60% of those windows. Related metrics are then checked as a family so several versions of
    the same idea do not all get Projection. Verdicts are always relative to a named target
    (next-season wOBA, FIP, baserunning run value, fielding run value, or WAR rate).</p>
    <table>
      <thead><tr><th>Verdict</th><th>Criteria</th></tr></thead>
      <tbody>
        <tr>
          <td class="verdict Context">Context</td>
          <td>Assigned by role before the prediction test: park, league environment, age, playing time,
          role, or handedness. These adjust the number. They are not treated as skill even if they help prediction.</td>
        </tr>
        <tr>
          <td class="verdict Insufficient">Insufficient Evidence</td>
          <td>Fewer than 3 out-of-time windows <i>and</i> coverage below the core-model threshold
          (under 70% of the modeling sample, or systematic missingness with under 90%).
          Too little evidence to decide. This is not proof the metric has no value.</td>
        </tr>
        <tr>
          <td class="verdict Projection">Projection</td>
          <td>Passes the prediction test, is observed on a broad enough share of the modeling sample for a
          core model, is not redundant with simpler features already in the model, the coefficient does not
          flip sign across folds, and it does not harm large subgroups. Baseline skill histories that
          themselves predict next season also sit here.</td>
        </tr>
        <tr>
          <td class="verdict Augmented">Augmented Projection</td>
          <td>Same prediction pass as Projection, but coverage is too incomplete for a universal core model.
          Keep it for the covered population only.</td>
        </tr>
        <tr>
          <td class="verdict Diagnostic">Diagnostic</td>
          <td>A process metric (contact quality, chase, velocity, Stuff+, sprint speed, and similar) that is
          useful for describing how a player works, but does not earn Projection: the lift is too small or
          unstable, the CI includes zero, or a stronger cousin already contains the information
          (family test). Keep for explanation and development, not as a broad
          projection input for that target.</td>
        </tr>
        <tr>
          <td class="verdict Exclude">Exclude</td>
          <td>Not Context, not a process descriptor kept for explanation, and it does not earn Projection.
          Typical cases: redundant with a simpler feature already in the model (for example current-season
          wOBA once 2-Year wOBA is present), or no unique predictive value for this target
          (for example current-season FIP once 2-Year FIP is present).</td>
        </tr>
      </tbody>
    </table>
    """


_GLOSSARY_SKIP = {
    "hitting": frozenset({"sprint_speed", "hp_to_1b", "sb_rate", "sb_pct"}),
    "pitching": frozenset(),
    "baserunning": frozenset({"age", "bats_left", "pa", "park_factor", "covid_season"}),
    "defense": frozenset({"sprint_speed", "age", "park_factor", "covid_season"}),
}


def _glossary_sentence(text: str) -> str:
    desc = " ".join(str(text or "").split())
    if not desc:
        return ""
    desc = desc[0].upper() + desc[1:]
    if desc[-1] not in ".!?":
        desc += "."
    return desc


def _metrics_glossary_rows(
    specs: tuple[FeatureSpec, ...],
    player_type: str,
    skip: frozenset[str],
) -> list[tuple[str, str]]:
    rows = []
    seen = set()
    for spec in specs:
        if spec.name in skip:
            continue
        shown = display_name(spec.name, player_type)
        if shown in seen:
            continue
        seen.add(shown)
        fallback = _glossary_sentence(spec.description)
        rows.append((shown, glossary_description(spec.name, player_type, fallback)))
    rows.sort(key=lambda item: item[0].lower())
    return rows


def _metrics_glossary_table(
    title: str,
    specs: tuple[FeatureSpec, ...],
    player_type: str,
    skip: frozenset[str],
    preamble: str = "",
) -> str:
    rows = _metrics_glossary_rows(specs, player_type, skip)
    if not rows:
        return ""
    body = "".join(
        f"<tr><td><strong>{html.escape(name)}</strong></td><td>{html.escape(desc)}</td></tr>"
        for name, desc in rows
    )
    intro = f'<p class="glossary-note">{preamble}</p>' if preamble else ""
    return (
        f"<h3>{html.escape(title)}</h3>"
        f"{intro}"
        "<table><thead><tr><th>Metric</th><th>What it measures</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _model_validation_glossary_table() -> str:
    body = "".join(
        f"<tr><td><strong>{html.escape(term)}</strong></td><td>{html.escape(desc)}</td></tr>"
        for term, desc in MODEL_VALIDATION_TERMS
    )
    return (
        "<h3>Model and validation terms</h3>"
        "<table><thead><tr><th>Term</th><th>What it means</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


_STUFF_PLUS_GLOSSARY_NOTE = (
    "<b>Stuff+ note:</b> All Stuff+ metrics in this study are generated from my "
    '<a href="https://arsenalintelligence.streamlit.app/" '
    'target="_blank" rel="noopener noreferrer">'
    "<u>Arsenal Intelligence</u></a> project, which models pitch quality using "
    "pitch-level Statcast data such as velocity, movement, spin, extension, and location. "
    "Here, those scores are treated as candidate pitching features and tested for whether "
    "they add future predictive value beyond the rest of the projection model."
)


def _metrics_glossary_body() -> str:
    return (
        "<p>Definitions for the public display names used in this study. "
        "Use this glossary for every metric on the site. "
        "Metrics are grouped by baseball component. Speed and steal metrics live under "
        "Baserunning; shared context such as age and park factor is listed with Hitting "
        "or Pitching. Model and validation vocabulary used throughout the study is listed "
        "at the end.</p>"
        + _metrics_glossary_table("Hitting", HITTER_FEATURES, "hitter", _GLOSSARY_SKIP["hitting"])
        + _metrics_glossary_table(
            "Pitching",
            PITCHER_FEATURES,
            "pitcher",
            _GLOSSARY_SKIP["pitching"],
            preamble=_STUFF_PLUS_GLOSSARY_NOTE,
        )
        + _metrics_glossary_table(
            "Baserunning", BASERUNNING_FEATURES, "hitter", _GLOSSARY_SKIP["baserunning"]
        )
        + _metrics_glossary_table("Defense", DEFENSE_FEATURES, "hitter", _GLOSSARY_SKIP["defense"])
        + _model_validation_glossary_table()
    )


def _glossary_button() -> str:
    return (
        '<div class="glossary-bar">'
        '<button type="button" class="glossary-toggle" id="metrics-glossary-toggle" '
        'aria-expanded="false" aria-controls="metrics-glossary">'
        "Open Metrics Glossary</button>"
        '<button type="button" class="glossary-toggle" id="glossary-toggle" '
        'aria-expanded="false" aria-controls="verdict-glossary">'
        "What the verdicts mean</button>"
        "</div>"
    )


def _glossary_panel() -> str:
    return f"""
    <div id="metrics-glossary" class="glossary-panel" hidden>
      <h2>Metrics glossary</h2>
      {_metrics_glossary_body()}
    </div>
    <div id="verdict-glossary" class="glossary-panel" hidden>
      <h2>What the verdicts mean</h2>
      {_verdict_glossary_body()}
    </div>
    """


def _glossary_chrome() -> str:
    return f"""
    {_glossary_button()}
    {_glossary_panel()}
    """


HERO_CHIP_KEYS = (
    ("hitter", "ev"),
    ("hitter", "sprint_speed"),
    ("hitter", "o_swing_pct"),
    ("pitcher", "avg_velo"),
    ("pitcher", "stuff_plus"),
    ("hitter", "arm_strength"),
    ("pitcher", "arm_strength"),
)

HERO_EXCLUDE_FEATURES = frozenset({"k_bb_pct"})
HERO_CROSS_COMPONENT_LABELS = frozenset({
    "Hitting",
    "Baserunning",
    "Defense",
    "Overall Value",
})

HERO_CARD_SPECS = (
    ("hitting", "y_woba", "Hitting", "Next-season wOBA"),
    ("pitching", "y_fip", "Pitching", "Next-season FIP"),
    ("baserunning", "y_br_rv_rate", "Baserunning", "Next-season baserunning run-value rate"),
    ("defense", "y_def_rv_rate", "Defense", "Next-season fielding run-value rate"),
    ("overall", "y_war_rate", "Overall Value", "Next-season WAR rate"),
)
HERO_COMPONENT_LABEL = {comp: label for comp, _tgt, label, _tl in HERO_CARD_SPECS}
HERO_EARNED_JOBS = frozenset({"Projection", "Augmented Projection"})


def _hero_sentence(row: pd.Series) -> str:
    blurb = passport_blurb(row).strip()
    verdict = str(row.get("verdict") or "")
    prefixes = (
        f"{verdict} for {target_phrase(row.get('target'))}.",
        f"{verdict_for_target(row)}.",
    )
    for prefix in prefixes:
        if blurb.startswith(prefix):
            blurb = blurb[len(prefix) :].strip()
            break
    if ". " in blurb:
        blurb = blurb.split(". ", 1)[0].rstrip(".") + "."
    elif blurb and not blurb.endswith("."):
        blurb += "."
    return blurb


def _hero_cards_for_group(group: pd.DataFrame) -> list[dict]:
    cards = []
    pt = str(group.iloc[0]["player_type"])
    feat = str(group.iloc[0]["feature"])
    slug = f"{pt}_{feat}"
    for component, target, comp_label, target_label in HERO_CARD_SPECS:
        hit = group[group.component.eq(component) & group.target.eq(target)]
        if hit.empty:
            continue
        row = hit.iloc[0]
        verdict = str(row.get("verdict") or "")
        cards.append(
            {
                "component": comp_label,
                "componentKey": component,
                "target": target_label,
                "verdict": verdict,
                "verdictClass": _verdict_class(verdict),
                "why": _hero_sentence(row),
                "href": f"passports/{slug}.html#{target_section_id(component, target)}",
            }
        )
    return cards


def _join_and(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _hero_notable_text(secondary: list[dict]) -> str:
    earned = [c for c in secondary if c["verdict"] in HERO_EARNED_JOBS]
    if not earned:
        return ""
    parts = []
    for verdict in ("Projection", "Augmented Projection"):
        names = [c["component"] for c in earned if c["verdict"] == verdict]
        if names:
            parts.append(f"{verdict} status for {_join_and(names)}")
    return "Notable result: this metric also earned " + " and ".join(parts) + "."


def _hero_role_layout(player_type: str, feature: str, cards: list[dict]) -> tuple[dict, list[dict], str]:
    home_label = HERO_COMPONENT_LABEL[metric_primary_component(player_type, feature)]
    primary = next((c for c in cards if c["component"] == home_label), cards[0])
    secondary = [c for c in cards if c["component"] != primary["component"]]
    return primary, secondary, _hero_notable_text(secondary)


def _hero_label(player_type: str, feature: str, counts: dict[str, int]) -> str:
    name = display_name(feature, player_type)
    if counts.get(name, 0) > 1:
        return f"{name} ({display_player(player_type)})"
    return name


def hero_catalog(table: pd.DataFrame) -> tuple[list[dict], dict]:
    """Build selector records from the canonical admission table. No new verdicts."""
    name_counts: dict[str, int] = {}
    groups = []
    for (pt, feat), group in table.groupby(["player_type", "feature"], sort=False):
        shown = display_name(feat, pt)
        name_counts[shown] = name_counts.get(shown, 0) + 1
        groups.append((str(pt), str(feat), group))
    metrics = []
    for i, (pt, feat, group) in enumerate(groups):
        if feat in HERO_EXCLUDE_FEATURES:
            continue
        cards = _hero_cards_for_group(group)
        if not cards:
            continue
        primary, secondary, notable = _hero_role_layout(pt, feat, cards)
        metrics.append(
            {
                "id": f"m{i}",
                "player_type": pt,
                "feature": feat,
                "label": _hero_label(pt, feat, name_counts),
                "cards": cards,
                "primary": primary,
                "secondary": secondary,
                "notable": notable,
                "passportHref": f"passports/{pt}_{feat}.html",
            }
        )
    default = pick_default_hero_metric(metrics)
    return metrics, default


def pick_default_hero_metric(metrics: list[dict]) -> dict:
    """Prefer Sprint Speed when audited jobs differ across player-value components."""
    if not metrics:
        raise ValueError("No evaluated metrics for the hero.")
    chip_rank = {key: i for i, key in enumerate(HERO_CHIP_KEYS)}

    def cross_component_verdicts(m: dict) -> set[str]:
        return {c["verdict"] for c in m["cards"] if c["component"] in HERO_CROSS_COMPONENT_LABELS}

    sprint = next(
        (m for m in metrics if m["player_type"] == "hitter" and m["feature"] == "sprint_speed"),
        None,
    )
    if sprint and len(cross_component_verdicts(sprint)) >= 2:
        return sprint

    varying = [m for m in metrics if len({c["verdict"] for c in m["cards"]}) >= 2]
    chip_varying = [
        m for m in varying
        if (m["player_type"], m["feature"]) in chip_rank
    ]
    pool = chip_varying or varying or metrics

    def sort_key(m: dict):
        return (
            -len(m["cards"]),
            -len({c["verdict"] for c in m["cards"]}),
            chip_rank.get((m["player_type"], m["feature"]), 99),
            m["label"],
        )

    return sorted(pool, key=sort_key)[0]


def _hero_primary_html(card: dict) -> str:
    vclass = html.escape(card["verdictClass"])
    return f"""
      <article class="hero-primary" id="hero-primary">
        <div class="hero-primary-meta">
          <div>
            <span class="k">Primary use</span>
            <p class="v">{html.escape(card["component"])}</p>
          </div>
          <div>
            <span class="k">Target</span>
            <p class="v">{html.escape(card["target"])}</p>
          </div>
          <div>
            <span class="k">Verdict</span>
            <p class="v"><span class="verdict {vclass}">{html.escape(card["verdict"])}</span></p>
          </div>
        </div>
        <p class="why">{html.escape(card["why"])}</p>
      </article>
    """


def _hero_secondary_html(secondary: list[dict]) -> str:
    if not secondary:
        return '<div class="hero-also" id="hero-also" hidden></div>'
    pills = "".join(
        f'<a class="hero-pill" href="{html.escape(card["href"], quote=True)}">'
        f'{html.escape(card["component"])} · '
        f'<span class="verdict {html.escape(card["verdictClass"])}">{html.escape(card["verdict"])}</span>'
        f"</a>"
        for card in secondary
    )
    return f"""
      <div class="hero-also" id="hero-also">
        <div class="hero-also-label">Also tested in:</div>
        <div class="hero-pills" id="hero-pills">{pills}</div>
        <div class="hero-pill-detail" id="hero-pill-detail" hidden></div>
      </div>
    """


def _hero_result_html(metric: dict) -> str:
    notable = metric.get("notable") or ""
    notable_html = (
        f'<p class="hero-notable" id="hero-notable">{html.escape(notable)}</p>'
        if notable
        else '<p class="hero-notable" id="hero-notable" hidden></p>'
    )
    return (
        _hero_primary_html(metric["primary"])
        + notable_html
        + _hero_secondary_html(metric["secondary"])
    )


def _hero_html(table: pd.DataFrame) -> str:
    metrics, default = hero_catalog(table)
    chips = []
    present = {(m["player_type"], m["feature"]) for m in metrics}
    for key in HERO_CHIP_KEYS:
        if key not in present:
            continue
        metric = next(m for m in metrics if (m["player_type"], m["feature"]) == key)
        active = " active" if metric["id"] == default["id"] else ""
        chips.append(
            f'<button type="button" class="hero-chip{active}" data-hero-id="{html.escape(metric["id"])}">'
            f'{html.escape(metric["label"])}</button>'
        )
    options = "".join(
        f'<option value="{html.escape(m["label"], quote=True)}"></option>'
        for m in sorted(metrics, key=lambda m: m["label"].lower())
    )
    public = [
        {
            "id": m["id"],
            "label": m["label"],
            "passportHref": m["passportHref"],
            "primary": m["primary"],
            "secondary": m["secondary"],
            "notable": m["notable"],
        }
        for m in metrics
    ]
    payload = json.dumps(
        {"defaultId": default["id"], "metrics": public},
        ensure_ascii=True,
    ).replace("<", "\\u003c")
    return f"""
    <section class="jobs-hero" id="jobs-hero">
      <h1>One metric. Different jobs.</h1>
      <p class="lede">The same metric can play different roles depending on what is being projected. Each metric has a natural baseball use; other tested targets can assign it a different job.</p>
      <div class="hero-pick">
        <label for="hero-search">Search metrics</label>
        <input id="hero-search" list="hero-metric-list" value="{html.escape(default["label"], quote=True)}" autocomplete="off" spellcheck="false"/>
        <datalist id="hero-metric-list">{options}</datalist>
      </div>
      <div class="hero-chips">{''.join(chips)}</div>
      <div class="hero-result-head">
        <h2 class="hero-metric-name" id="hero-name">{html.escape(default["label"])}</h2>
        <p class="hero-passport"><a id="hero-passport" href="{html.escape(default["passportHref"], quote=True)}">View full metric passport →</a></p>
      </div>
      <div id="hero-result">{_hero_result_html(default)}</div>
      <p class="note-inline">Each verdict comes from expanding-window, next-season validation — not a same-year correlation.</p>
      <script type="application/json" id="hero-data">{payload}</script>
      <script>
      (function(){{
        var raw = document.getElementById("hero-data");
        if (!raw) return;
        var data = JSON.parse(raw.textContent);
        var byId = {{}};
        var byLabel = {{}};
        data.metrics.forEach(function(m){{ byId[m.id] = m; byLabel[m.label.toLowerCase()] = m; }});
        var nameEl = document.getElementById("hero-name");
        var passportEl = document.getElementById("hero-passport");
        var resultEl = document.getElementById("hero-result");
        var search = document.getElementById("hero-search");
        var chips = document.querySelectorAll(".hero-chip");
        var openIdx = -1;
        function metaCell(label, inner, isHtml) {{
          var wrap = document.createElement("div");
          var k = document.createElement("span");
          k.className = "k";
          k.textContent = label;
          wrap.appendChild(k);
          if (isHtml) {{ wrap.appendChild(inner); }}
          else {{
            var p = document.createElement("p");
            p.className = "v";
            p.textContent = inner;
            wrap.appendChild(p);
          }}
          return wrap;
        }}
        function bindPills(metric) {{
          var pills = resultEl.querySelectorAll(".hero-pill");
          var detail = document.getElementById("hero-pill-detail");
          openIdx = -1;
          pills.forEach(function(pill, idx) {{
            pill.addEventListener("click", function(ev) {{
              if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
              ev.preventDefault();
              var card = metric.secondary[idx];
              if (!card || !detail) return;
              if (openIdx === idx) {{
                openIdx = -1;
                detail.hidden = true;
                detail.replaceChildren();
                pills.forEach(function(p){{ p.setAttribute("aria-expanded", "false"); }});
                return;
              }}
              openIdx = idx;
              pills.forEach(function(p, i){{ p.setAttribute("aria-expanded", i === idx ? "true" : "false"); }});
              var lead = document.createElement("p");
              lead.appendChild(document.createTextNode(card.component + " · " + card.target + " · "));
              var v = document.createElement("span");
              v.className = "verdict " + card.verdictClass;
              v.textContent = card.verdict;
              lead.appendChild(v);
              var why = document.createElement("p");
              why.textContent = card.why;
              var link = document.createElement("a");
              link.href = card.href;
              link.textContent = "Open this result in the passport →";
              detail.replaceChildren(lead, why, link);
              detail.hidden = false;
            }});
          }});
        }}
        function render(metric) {{
          if (!metric) return;
          nameEl.textContent = metric.label;
          search.value = metric.label;
          passportEl.href = metric.passportHref;
          chips.forEach(function(btn){{
            btn.classList.toggle("active", btn.getAttribute("data-hero-id") === metric.id);
          }});
          var primary = metric.primary;
          var article = document.createElement("article");
          article.className = "hero-primary";
          article.id = "hero-primary";
          var meta = document.createElement("div");
          meta.className = "hero-primary-meta";
          meta.appendChild(metaCell("Primary use", primary.component, false));
          meta.appendChild(metaCell("Target", primary.target, false));
          var verdictWrap = document.createElement("p");
          verdictWrap.className = "v";
          var verdict = document.createElement("span");
          verdict.className = "verdict " + primary.verdictClass;
          verdict.textContent = primary.verdict;
          verdictWrap.appendChild(verdict);
          meta.appendChild(metaCell("Verdict", verdictWrap, true));
          var why = document.createElement("p");
          why.className = "why";
          why.textContent = primary.why;
          article.appendChild(meta);
          article.appendChild(why);
          var notable = document.createElement("p");
          notable.className = "hero-notable";
          notable.id = "hero-notable";
          if (metric.notable) {{ notable.textContent = metric.notable; }}
          else {{ notable.hidden = true; }}
          var also = document.createElement("div");
          also.className = "hero-also";
          also.id = "hero-also";
          if (!metric.secondary || !metric.secondary.length) {{
            also.hidden = true;
          }} else {{
            var label = document.createElement("div");
            label.className = "hero-also-label";
            label.textContent = "Also tested in:";
            var pills = document.createElement("div");
            pills.className = "hero-pills";
            pills.id = "hero-pills";
            metric.secondary.forEach(function(card) {{
              var a = document.createElement("a");
              a.className = "hero-pill";
              a.href = card.href;
              a.setAttribute("aria-expanded", "false");
              a.appendChild(document.createTextNode(card.component + " · "));
              var vs = document.createElement("span");
              vs.className = "verdict " + card.verdictClass;
              vs.textContent = card.verdict;
              a.appendChild(vs);
              pills.appendChild(a);
            }});
            var detail = document.createElement("div");
            detail.className = "hero-pill-detail";
            detail.id = "hero-pill-detail";
            detail.hidden = true;
            also.appendChild(label);
            also.appendChild(pills);
            also.appendChild(detail);
          }}
          resultEl.replaceChildren(article, notable, also);
          bindPills(metric);
        }}
        function findMetric(q) {{
          q = (q || "").trim().toLowerCase();
          if (!q) return null;
          if (byLabel[q]) return byLabel[q];
          var starts = data.metrics.filter(function(m){{ return m.label.toLowerCase().indexOf(q) === 0; }});
          if (starts.length === 1) return starts[0];
          var has = data.metrics.filter(function(m){{ return m.label.toLowerCase().indexOf(q) !== -1; }});
          return has.length === 1 ? has[0] : null;
        }}
        chips.forEach(function(btn){{
          btn.addEventListener("click", function(){{ render(byId[btn.getAttribute("data-hero-id")]); }});
        }});
        search.addEventListener("change", function(){{ render(findMetric(search.value) || byId[data.defaultId]); }});
        search.addEventListener("keydown", function(ev){{
          if (ev.key === "Enter") {{ ev.preventDefault(); render(findMetric(search.value) || byId[data.defaultId]); }}
        }});
        bindPills(byId[data.defaultId]);
      }})();
      </script>
    </section>
    """


def _parquet_n(name: str) -> int | None:
    path = DATA_PROCESSED / name
    if not path.exists():
        return None
    return int(len(pd.read_parquet(path)))


def _projecting_html(audit: dict) -> str:
    seasons = audit.get("hitter_seasons") or [2015, 2025]
    window = f"{seasons[0]}–{seasons[-1]}"
    n_h = audit.get("hitter_sample_n") or _parquet_n("hitter_sample_pa150.parquet")
    n_p = audit.get("pitcher_sample_n") or _parquet_n("pitcher_sample_role_ip.parquet")
    n_br = _parquet_n("baserunning_sample.parquet") or n_h
    n_def = _parquet_n("defense_sample.parquet") or n_h
    n_war = _parquet_n("war_hitter_sample.parquet") or n_h

    def card(title: str, target: str, n) -> str:
        sample = f"{window} · {int(n):,} player-seasons" if n else window
        return (
            f'<div class="card"><b>{html.escape(title)}</b>'
            f"<span>{html.escape(target)}</span>"
            f'<span class="window">{html.escape(sample)}</span></div>'
        )

    return f"""
    <section class="projecting">
      <h2>What are we projecting?</h2>
      <div class="jobs">
        {card("Hitting", "Future wOBA", n_h)}
        {card("Pitching", "Future FIP", n_p)}
        {card("Baserunning", "Future baserunning run-value rate", n_br)}
        {card("Defense", "Future fielding run-value rate", n_def)}
        {card("Overall Value", "Future WAR rate", n_war)}
      </div>
      <p class="thesis">A metric does not have one universal role. Its value depends on the question being projected.</p>
    </section>
    """


def _taxonomy_html() -> str:
    return f"""
    <h2>What the verdicts mean</h2>
    {_verdict_glossary_body()}
    """


def _headline_html(_table: pd.DataFrame) -> str:
    return """
    <h2>What we found</h2>
    <ul class="findings">
      <li>
        <b>A metric can have different jobs depending on what you are trying to predict.</b>
        Sprint Speed helped predict future baserunning value, but it was more useful for explaining than
        forecasting future hitting or defense. Stuff+ helped predict future FIP, while average velocity
        did not add enough unique information once related pitching metrics were considered.
      </li>
      <li>
        <b>Recent expected hitting performance carried useful information about the future.</b>
        PA-weighted 2-Year xwOBA improved the next-season wOBA projection even after the model already
        knew a hitter’s recent actual wOBA history.
      </li>
      <li>
        <b>Exit Velocity was more useful for forecasting future hitting than Barrel Rate or Hard-Hit Rate.</b>
        Barrel Rate and Hard-Hit Rate describe contact quality well, but much of their information overlapped
        with Exit Velocity. Once Exit Velocity was known, they added little to the forecast.
      </li>
      <li>
        <b>Some metrics are better for explaining a hitter than projecting him.</b>
        Chase Rate helps describe plate discipline, but it did not add enough unique information to the
        next-season wOBA forecast. A hitter’s single-season wOBA was also unnecessary once the model already
        had a more stable multi-year wOBA history.
      </li>
      <li>
        <b>For pitchers, the goal is to predict next-season FIP.</b>
        Recent FIP history was important, but other information still helped. Longer-term K-BB% and current
        strikeout rate added useful information about future FIP. Current K-BB% itself did not add enough
        once the model already knew related information. Because K-BB% is simply K% minus BB%, those three
        statistics are not three independent signals.
      </li>
      <li>
        <b>Stuff+ helped forecast future pitching performance.</b>
        Stuff+ and release extension added useful information about next-season FIP beyond recent FIP history.
        Fastball velocity, in-zone contact allowed, and called-strike-plus-whiff rate also contributed.
        Average velocity, average spin, and overall whiff rate were more useful for describing how a pitcher
        gets results than for improving the final FIP projection.
        <p class="tech">Stuff+ is a pitch-quality score. For each season, a logistic model trained only on
        Statcast pitches from that season and earlier predicts the chance a swing misses from the pitch’s
        perceived velocity, movement, spin, extension, and location. Those expected-whiff probabilities are
        then scaled so 100 is average within that season, pitcher role, and pitch group.
        See the <a href="#metrics-glossary">Metrics Glossary</a> for definitions of every metric in this study.</p>
      </li>
      <li>
        <b>Speed mattered most when the question was baserunning.</b>
        Sprint Speed and steal-attempt rate helped predict next-season baserunning value, along with a player’s
        recent baserunning history. This is a good example of a metric being much more valuable for one
        projection target than another.
      </li>
      <li>
        <b>Past defensive performance was the strongest foundation for projecting future defense.</b>
        Multi-year fielding run value helped predict next-season defensive value. Outs Above Average remained
        useful for describing defensive skill, but added little once the model already knew a player’s recent
        fielding-run-value history. Official errors were not used as the defensive target because a defender
        can make a costly mistake without being charged with an error.
      </li>
      <li>
        <b>Overall player value is a different forecasting problem.</b>
        Previous WAR rate was useful for predicting future WAR rate, while some component metrics added
        information on top of it. Exit Velocity helped with position-player WAR projections, while 2-Year K-BB%
        helped with pitcher WAR projections. A metric being useful for hitting, pitching, baserunning, or
        defense did not automatically mean it improved the broader WAR forecast.
      </li>
    </ul>
    """


def _surprise_html() -> str:
    return """
    <h2>What surprised me?</h2>
    <ul class="findings">
      <li>Sprint Speed does not have one job. It was Diagnostic for next-season wOBA and
      Projection for next-season baserunning run value. The job depends on the target.</li>
      <li>Stuff+ earned Projection for next-season FIP after family tests against a FIP-history baseline.</li>
      <li>More data was not always better. Selective feature models outperformed models that used nearly every available metric when predicting next-season hitting and pitching. For baserunning and defense, there was no clear winner. Overall value was different: the larger all-feature model predicted hitter WAR rate better. The takeaway is that feature selection should depend on the projection target rather than assuming either simpler or larger models will always perform best.</li>
    </ul>
    """


def _map_explainer() -> str:
    return """
    <div class="map-legend">
      <p><b>How to read the Reliability Map.</b>
      Farther right = more stable year to year.
      Higher = more incremental future predictive value.
      Larger = broader player-season coverage.
      Shape/color = final verdict.</p>
      <p><b>Stability</b> is how repeatable a metric is from one season to the next, measured as year-to-year
      correlation. 1.00 means this year’s value is essentially determined by last year’s; lower values mean
      more noise. Farther right on the map is higher stability. The number in parentheses is this metric’s
      rank among the metrics on this map, from most stable to least.</p>
      <p><b>Coverage</b> is the share of eligible player-seasons in the modeling sample where this metric was
      available. 100% means we observed it for every season in that sample. Marker size on the map is this
      same coverage. It is not 100% for every metric. Lag and multi-year history need a prior season,
      catcher-only stats do not apply to other positions, pitch-type stats need that pitch in the arsenal,
      and some tracking fields did not exist for the full 2015–2025 window.</p>
      <p>Hover a metric to see its details in the panel to the right. Click a point to open its passport.</p>
    </div>
    """


def _reliability_map_html() -> str:
    return f"""
    <h2 id="reliability-map">Reliability Map</h2>
    {_map_explainer()}
    <div class="map-filters" id="map-filters">
      <button type="button" class="active" data-src="figures/reliability_map.html">All primary targets</button>
      <button type="button" data-src="figures/reliability_map_hitting.html">Hitting</button>
      <button type="button" data-src="figures/reliability_map_pitching.html">Pitching</button>
      <button type="button" data-src="figures/reliability_map_baserunning.html">Baserunning</button>
      <button type="button" data-src="figures/reliability_map_defense.html">Defense</button>
      <button type="button" data-src="figures/reliability_map_overall.html">Overall Value</button>
    </div>
    <div class="chart-with-panel">
      <iframe class="iframe" id="map-frame" title="Reliability map" src="figures/reliability_map.html"></iframe>
      <aside class="metric-panel" id="map-panel">
        <p class="placeholder">Hover a metric on the chart to see details here.</p>
      </aside>
    </div>
    <script>
    (function(){{
      var frame = document.getElementById("map-frame");
      var buttons = document.querySelectorAll("#map-filters button");
      buttons.forEach(function(btn){{
        btn.addEventListener("click", function(){{
          buttons.forEach(function(b){{ b.classList.remove("active"); }});
          btn.classList.add("active");
          frame.src = btn.getAttribute("data-src");
        }});
      }});
    }})();
    </script>
    """


def _counts(table: pd.DataFrame) -> str:
    table = without_kbb_outcome_target(table)
    rows = []
    cols = ["component", "target", "verdict"]
    if not set(cols).issubset(table.columns):
        cols = ["player_type", "verdict"]
    for keys, n in table.groupby(cols).size().items():
        if len(cols) == 3:
            comp, tgt, v = keys
            rows.append(
                f"<tr><td>{component_phrase(comp)}</td><td>{target_phrase(tgt)}</td><td>{v}</td><td>{n}</td></tr>"
            )
        else:
            pt, v = keys
            rows.append(f"<tr><td>{display_player(pt)}</td><td>{v}</td><td>{n}</td></tr>")
    header = (
        "<th>Component</th><th>Target</th><th>Verdict</th><th>n</th>"
        if len(cols) == 3
        else "<th>Type</th><th>Verdict</th><th>n</th>"
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _correlation_callout() -> str:
    return """
    <div class="note">
      <p><b>Correlation is not admission.</b>
      A metric can move with next-season performance and still add little to a projection
      once the model already knows similar information. Each row explains why this metric
      received its verdict — not the glossary definition of that verdict.</p>
    </div>
    """


def _verdict_section_title(verdict: str, n: int) -> str:
    if n == 1:
        return f"1 {verdict}"
    plurals = {
        "Projection": "Projections",
        "Augmented Projection": "Augmented Projections",
        "Diagnostic": "Diagnostics",
        "Context": "Context",
        "Exclude": "Exclude",
        "Insufficient Evidence": "Insufficient Evidence",
    }
    return f"{n} {plurals.get(verdict, verdict)}"


def _category_table(table: pd.DataFrame, player_type: str, verdict: str, all_rows: pd.DataFrame | None = None) -> str:
    sub = table[(table.player_type == player_type) & (table.verdict == verdict)].copy()
    if sub.empty:
        return "<p>None in this sample.</p>"
    peers = all_rows if all_rows is not None else table
    if verdict == "Projection":
        sub = sub.sort_values("oos_rmse_delta", na_position="last")
    else:
        sub["lift"] = -sub["oos_rmse_delta"]
        sub = sub.sort_values("lift", ascending=False)

    def metric_cell(r) -> str:
        shown = _metric_cell(player_type, r.feature)
        if r.feature == "k_bb_pct_z":
            note = "League-adjusted representation of K-BB%, not an independent skill"
            shown = (
                f"{_metric_cell(player_type, r.feature, note)}"
                " <span class=\"note-inline\">(standardized K-BB%, not a separate skill)</span>"
            )
        return shown

    if verdict in {"Projection", "Augmented Projection"}:
        header = (
            "<th>Metric</th><th>Relationship with next season</th>"
            "<th>Role in forecast</th><th>Model impact</th><th>Why</th>"
        )
        rows = []
        for _, r in sub.iterrows():
            name = display_name(r.feature, player_type)
            impact = fmt_model_impact(
                r.get("dropone_oos_rmse"),
                admitted_model_rmse(r.get("study_id")),
                name,
            )
            rows.append(
                "<tr>"
                f"<td>{metric_cell(r)}</td>"
                f'<td class="rel">{html.escape(relationship_label(r), quote=False)}</td>'
                f"<td>{html.escape(projection_role(r, peers), quote=False)}</td>"
                f"<td>{html.escape(impact)}</td>"
                f'<td class="why">{html.escape(table_why(r, peers), quote=False)}</td>'
                "</tr>"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"

    if verdict == "Diagnostic":
        header = "<th>Metric</th><th>Relationship with next season</th><th>Why</th>"
        group = len(sub) >= 20
        if group:
            sub = sub.copy()
            sub["_grp"] = [diagnostic_group(r) for _, r in sub.iterrows()]
            order = {name: i for i, name in enumerate(GROUP_ORDER)}
            sub["_gord"] = sub["_grp"].map(lambda g: order.get(g, 99))
            sub = sub.sort_values(["_gord", "lift"], ascending=[True, False])
        rows = []
        last_grp = None
        for _, r in sub.iterrows():
            if group:
                grp = r["_grp"]
                if grp != last_grp:
                    rows.append(f'<tr class="group-row"><th colspan="3">{html.escape(str(grp))}</th></tr>')
                    last_grp = grp
            rows.append(
                "<tr>"
                f"<td>{metric_cell(r)}</td>"
                f'<td class="rel">{html.escape(relationship_label(r), quote=False)}</td>'
                f'<td class="why">{html.escape(table_why(r, peers), quote=False)}</td>'
                "</tr>"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"

    if verdict == "Context":
        header = "<th>Metric</th><th>What it adjusts for</th><th>Why it matters</th>"
        rows = []
        for _, r in sub.iterrows():
            rows.append(
                "<tr>"
                f"<td>{metric_cell(r)}</td>"
                f"<td>{html.escape(context_adjusts_for(r), quote=False)}</td>"
                f'<td class="why">{html.escape(context_why_matters(r), quote=False)}</td>'
                "</tr>"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"

    if verdict == "Exclude":
        header = "<th>Metric</th><th>Relationship with next season</th><th>Why excluded</th>"
        rows = []
        for _, r in sub.iterrows():
            rows.append(
                "<tr>"
                f"<td>{metric_cell(r)}</td>"
                f'<td class="rel">{html.escape(relationship_label(r), quote=False)}</td>'
                f'<td class="why">{html.escape(table_why(r, peers), quote=False)}</td>'
                "</tr>"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"

    header = "<th>Metric</th><th>Why</th>"
    rows = []
    for _, r in sub.iterrows():
        rows.append(
            "<tr>"
            f"<td>{metric_cell(r)}</td>"
            f'<td class="why">{html.escape(table_why(r, peers), quote=False)}</td>'
            "</tr>"
        )
    return f"<table><thead><tr>{header}</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _component_page(
    table: pd.DataFrame,
    component: str,
    target: str,
    player_type: str,
    heat: str,
    coef: str | None,
    cov: str | None,
    show_callout: bool = True,
) -> str:
    sub = table[table.component.eq(component) & table.target.eq(target)].copy()
    if not sub.empty:
        mask = [
            belongs_on_component(r.player_type, r.feature, r.component, r.verdict)
            for r in sub.itertuples()
        ]
        sub = sub.iloc[[i for i, ok in enumerate(mask) if ok]].copy()
    lead = (
        f"<p class=\"lede\">Metrics listed here belong to {component_phrase(component).lower()}, "
        f"or earned a projection job for {target_phrase(target)}. "
        "Passports keep the full target-by-target record.</p>"
    )
    if component == "pitching":
        lead += (
            "<p>League-Adjusted K-BB% is a standardized representation of K-BB%, not a separate skill. "
            "K-BB% equals K% minus BB%.</p>"
        )
    sections = []
    for verdict in ("Projection", "Diagnostic", "Context", "Insufficient Evidence", "Exclude", "Augmented Projection"):
        shown = sub[sub.player_type.eq(player_type) & sub.verdict.eq(verdict)]
        n = int(len(shown))
        if n == 0:
            continue
        sections.append(f"<h2>{_verdict_section_title(verdict, n)}</h2>" + _category_table(sub, player_type, verdict, table))
    diags = ""
    if heat:
        blocks = [
            (
                f'<div class="diag-block">'
                f"<h3>Admission diagnostics</h3>"
                f'<p class="diag-caption">Each column is one admission criterion. Darker cells ranked better among tested metrics on that criterion. Hover for the percentile and verdict.</p>'
                f'<iframe class="iframe iframe-heat" title="{component_phrase(component)} admission heatmap" src="{heat}"></iframe>'
                f"</div>"
            )
        ]
        if coef:
            blocks.append(
                '<div class="diag-block">'
                "<h3>Coefficient stability</h3>"
                '<p class="diag-caption">Solid lines are Projection metrics; dashed lines are diagnostic comparisons. '
                "Names wrap under the chart so every series stays visible. Click a name to hide or show it. Hover a line for the exact coefficient.</p>"
                f'<iframe class="iframe iframe-coef" title="Coefficient stability" src="{coef}"></iframe>'
                "</div>"
            )
        if cov:
            blocks.append(
                '<div class="diag-block">'
                "<h3>Historical coverage</h3>"
                '<p class="diag-caption">Coverage is the share of eligible player-seasons in which the metric was available. '
                "Each row is a metric and each column is a season. Hover a cell for the exact rate.</p>"
                f'<iframe class="iframe iframe-cov" title="Coverage" src="{cov}"></iframe>'
                "</div>"
            )
        diags = (
            '<details class="diagnostics"><summary>View full research diagnostics</summary>'
            + "".join(blocks)
            + "</details>"
        )
    return f"""
    {lead}
    {_correlation_callout() if show_callout else ""}
    {''.join(sections)}
    {diags}
    """


def _five_test_guide(how_to_read: str, tests: tuple[str, ...]) -> str:
    paras = "\n".join(f"          <p>{p}</p>" for p in tests)
    return f"""
        <div class="diag-copy">
          <p><b>How to read this chart.</b> {how_to_read}</p>
{paras}
          <p>This chart shows why a metric did or did not earn a place in the projection; it is not a measure of feature importance. Hover for the individual result, or open the metric passport for the full evidence.</p>
        </div>
    """


HITTING_MATRIX_TESTS = (
    "Future Prediction asks whether adding the metric helps the model predict a hitter’s next-season wOBA, which is the primary hitting target in this study. A metric can look useful in the same season and still fail here if it does not improve forecasts on future seasons the model has not seen.",
    "Stable Over Time asks whether the metric’s relationship with next-season wOBA stays reasonably similar from one historical test period to another. For example, if a metric appears strongly useful in 2019–2020 but its effect disappears or reverses in later seasons, relying on it may make the projection fragile. Stability matters because a projection should keep working as the league changes.",
    "Unique Information asks whether the metric contributes something the model does not already know from other variables. Two statistics can both correlate with future performance but largely measure the same underlying skill. If Exit Velocity already captures most of the information contained in Hard-Hit Rate, adding both may provide little extra forecasting value. This helps prevent the model from treating redundant statistics as separate signals.",
    "Data Coverage asks how consistently the metric is available across the eligible hitter-seasons in the study. Some statistics exist for nearly every player and season, while others are missing for certain years, players, tracking systems, or sample sizes. A metric with limited coverage may look predictive only for the subset of players for whom it is available, which can create selection bias and make it difficult to use in a projection for everyone.",
    "Consistent Across Players asks whether the metric’s usefulness holds across meaningful groups of hitters rather than being driven by one narrow subset. For example, the model can check whether the relationship is reasonably similar for younger and older hitters, left- and right-handed batters, or different playing-time groups. This matters because a metric that works only for one type of player may not be reliable enough for a broad player-projection system.",
    "Together, these five tests answer a broader question: does this metric not only look useful, but actually deserve to change a future projection? A metric is most convincing when it improves next-season prediction, remains stable over time, adds information beyond existing features, is available for a broad population, and works reasonably well across different types of players.",
)

PITCHING_MATRIX_TESTS = (
    "Future Prediction asks whether adding the metric helps the model predict a pitcher’s next-season FIP, which is the primary pitching target in this study. Because lower FIP is better, a metric can have a negative relationship with FIP and still be favorable—for example, higher velocity could be associated with lower future FIP. A metric can describe a pitcher extremely well in the current season and still fail this test if it does not improve forecasts on future seasons the model has not seen.",
    "Stable Over Time asks whether the metric’s relationship with next-season FIP stays reasonably similar from one historical test period to another. For example, if velocity appears strongly useful in one group of seasons but its effect becomes much smaller or reverses after league-wide changes in pitch design, training, or the run environment, relying heavily on it could make the projection fragile. Stability matters because a projection should continue working as the league and the way pitchers train and throw change.",
    "Unique Information asks whether the metric contributes something the model does not already know from other pitching variables. Many pitching statistics describe related parts of the same skill. Whiff Rate, K%, CSW%, Stuff+, and velocity may all contain overlapping information about bat-missing ability or pitch quality. A metric can be strongly associated with future FIP but still add little once stronger related variables are already known. This prevents the model from counting the same underlying pitching skill multiple times.",
    "Data Coverage asks how consistently the metric is available across the eligible pitcher-seasons in the study. Traditional results such as strikeouts and walks may exist for nearly every pitcher, while certain tracking or pitch-shape variables may be missing for particular seasons, pitch types, or players. A metric with limited coverage can appear valuable only for the subset of pitchers with good tracking data, creating selection bias and making it difficult to use in a projection for every pitcher.",
    "Consistent Across Players asks whether the metric’s usefulness holds across meaningful groups of pitchers rather than being driven by one narrow population. For example, the study can check whether a relationship is reasonably consistent for starters and relievers, left- and right-handed pitchers, younger and older pitchers, or different workload groups. This matters because a metric that works well only for hard-throwing relievers, for example, may not be reliable enough for a projection intended to evaluate all pitchers.",
    "Together, these five tests answer a broader question: does this metric not only describe pitching ability, but actually deserve to change a future FIP projection? A metric is most convincing when it improves next-season prediction, remains stable over time, adds information beyond existing features, is available for a broad population, and works reasonably well across different types of pitchers.",
)

BASERUNNING_MATRIX_TESTS = (
    "Future Prediction asks whether adding the metric helps the model predict a player’s next-season baserunning run-value rate, which is the primary baserunning target in this study. Metrics such as Sprint Speed, steal-attempt rate, or previous baserunning performance may describe what a runner did this season, but they earn projection value only if they help forecast how much baserunning value that player will create in a future season the model has not seen.",
    "Stable Over Time asks whether the metric’s relationship with next-season baserunning value stays reasonably similar across historical test periods. For example, Sprint Speed might consistently relate to future baserunning performance, while another metric could look useful in only one or two seasons because of rule changes, playing style, or small samples. Stability matters because a useful projection signal should persist across different seasons rather than depending on one particular run environment.",
    "Unique Information asks whether the metric contributes something the model does not already know from other baserunning variables. Sprint Speed, Home-to-First Time, stolen-base attempts, and previous baserunning run value can all describe related aspects of speed and aggressiveness. If Sprint Speed already captures most of the useful information contained in another speed metric, including both may add very little. This helps distinguish genuinely new information from multiple statistics describing the same underlying baserunning ability.",
    "Data Coverage asks how consistently the metric is available across the eligible player-seasons in the study. Stolen-base statistics are broadly available, while tracking-based speed or advancement measures may not be observed as consistently for every player or season. Limited coverage matters because a metric can appear predictive among the players for whom it is measured while performing differently for players who are missing that information. A projection intended for an entire player population needs to account for that risk.",
    "Consistent Across Players asks whether the metric’s usefulness holds across different types of baserunners rather than being driven by one group. For example, the study can check younger versus older players, high- versus low-opportunity runners, left- versus right-handed hitters, or different speed groups. This matters because a metric that predicts future baserunning well only for elite-speed players may not generalize to average or slower runners.",
    "Together, these five tests answer a broader question: does this metric not only describe speed or baserunning behavior, but actually deserve to change a future baserunning projection? A metric is most convincing when it improves next-season prediction, remains stable over time, adds information beyond existing features, is broadly available, and works reasonably well across different kinds of baserunners.",
)

DEFENSE_MATRIX_TESTS = (
    "Future Prediction asks whether adding the metric helps the model predict a player’s next-season fielding run-value rate, which is the primary defensive target in this study. A defensive metric can describe what happened this season without necessarily forecasting what will happen next season. OAA, Sprint Speed, arm-related measures, previous fielding value, and other defensive information earn projection value only if they improve forecasts on future seasons the model has not seen.",
    "Stable Over Time asks whether the metric’s relationship with next-season defensive value stays reasonably similar across historical test periods. Defensive measurements can be noisy because opportunities, positioning, ball distribution, and tracking systems change from year to year. If a metric appears strongly useful in one period but its relationship weakens or reverses in another, it may be too unstable to drive a projection. Stability matters because future defensive evaluation should not depend heavily on a pattern that existed only temporarily.",
    "Unique Information asks whether the metric contributes something the model does not already know from other defensive variables. For example, previous fielding run value, OAA history, Sprint Speed, arm strength, and position can overlap in the defensive information they provide. OAA may be an excellent description of range but still add little to a future projection if multi-year fielding history already captures most of the same signal. This prevents the model from treating several measurements of similar defensive ability as independent evidence.",
    "Data Coverage asks how consistently the metric is available across the eligible fielder-seasons in the study. Some defensive information is recorded for nearly every player, while tracking-based measurements can depend on season, position, opportunity count, or the availability of the underlying tracking system. Coverage is especially important for defense because different positions are measured through different types of opportunities. A metric that exists mainly for a particular position or subset of fielders may not be suitable for a universal defensive projection.",
    "Consistent Across Players asks whether the metric’s usefulness holds across meaningful groups of defenders rather than being driven by one position or type of player. For example, the study can examine infielders versus outfielders, younger versus older defenders, different playing-time groups, or position-specific populations. This matters because a metric that works well for center fielders may not measure the same defensive process for shortstops or catchers. A broad projection must respect those differences rather than assuming every defender is evaluated in exactly the same way.",
    "Together, these five tests answer a broader question: does this metric not only describe defensive performance, but actually deserve to change a future fielding projection? A metric is most convincing when it improves next-season prediction, remains stable over time, contributes information beyond existing defensive measures, has adequate coverage, and works reasonably well across the player groups for which it is intended.",
)

OVERALL_MATRIX_TESTS = (
    "Future Prediction asks whether adding the metric helps the model predict a player’s next-season WAR rate, which is the overall-value target in this study. WAR combines contributions from several parts of the game, so a metric that is valuable for predicting hitting, pitching, baserunning, or defense does not automatically improve the broader WAR forecast. A feature earns value here only if it helps predict future overall production beyond the information the model already has.",
    "Stable Over Time asks whether the metric’s relationship with next-season WAR rate stays reasonably similar across historical test periods. A metric might help explain overall value during one period but become less informative as player usage, run environments, defensive measurement, or roster construction changes. Stability matters because an overall player-value projection should remain useful across seasons rather than depending on one particular era or style of play.",
    "Unique Information asks whether the metric contributes something the overall-value model does not already know. WAR combines multiple components, so there is substantial opportunity for overlap. For a hitter, Exit Velocity may add offensive information beyond prior WAR, while a baserunning or defensive metric may already be partly reflected in past WAR history. For a pitcher, K-BB%, Stuff+, or FIP-related information may overlap with prior pitching value. This test asks whether a component metric still contributes something new after broader performance history is already known.",
    "Data Coverage asks how consistently the metric is available across the eligible player-seasons used for the WAR projection. Overall-value models combine information from several areas of the game, and those sources do not always have equal historical coverage. A feature that exists only for recent Statcast seasons or a particular type of player can make the model dependent on a narrower population. Broad and consistent coverage matters if the goal is to compare player value across the full eligible population.",
    "Consistent Across Players asks whether the metric’s usefulness holds across meaningful player groups rather than being driven by one type of player. For position players, that can include different positions, ages, playing-time levels, or offensive profiles. For pitchers, it can include starters and relievers, handedness groups, ages, and workloads. This matters especially for WAR because overall value can be accumulated in very different ways. A feature that helps predict WAR for power hitters, for example, may not provide the same information for defense-first players.",
    "Together, these five tests answer a broader question: does this metric provide enough reliable information to change an overall-value projection, rather than simply being important within one part of the game? A metric is most convincing when it improves next-season WAR prediction, remains stable over time, adds information beyond prior overall and component performance, is broadly available, and generalizes across the kinds of players the model is intended to evaluate.",
)


def _hitting_research_visuals() -> str:
    guide = _five_test_guide(
        "Each row is a metric tested for predicting next-season wOBA. Each column represents one part of the feature-admission process. Darker cells mean the metric ranked better relative to the other tested hitter metrics on that criterion.",
        HITTING_MATRIX_TESTS,
    )
    return (
        """
    <h2>What matters most in the final hitting projection?</h2>
    <p class="diag-caption">Each bar is the increase in out-of-sample prediction error when that Projection metric is removed from the admitted model.
    A larger positive value means the forecast got worse without that information.</p>
    <iframe class="iframe iframe-dropone" title="Drop-one out-of-sample importance for hitting Projection metrics" src="figures/dropone_hitter.html"></iframe>
    <details class="diagnostics">
      <summary>View full research diagnostics</summary>
      <div class="diag-block">
        <h3>A. How every hitter metric was evaluated</h3>
        """
        + guide
        + """
        <iframe class="iframe iframe-heat" title="Hitting admission heatmap" src="figures/heatmap_hitter.html"></iframe>
      </div>
      <div class="diag-block">
        <h3>B. Coefficient stability for key hitting metrics</h3>
        <p class="diag-caption">Final Projection metrics are shown alongside a small set of important diagnostic comparisons.
        Standardized coefficients show how each metric’s modeled relationship with next-season wOBA changed across temporal folds.
        Solid lines are Projection metrics; dashed lines are diagnostic comparisons.</p>
        <p class="diag-link"><a href="figures/coef_paths_hitter_all.html">Show all tested metrics</a> (technical coefficient table)</p>
        <iframe class="iframe iframe-coef" title="Coefficient stability for key hitting metrics" src="figures/coef_paths_hitter.html"></iframe>
      </div>
    """
        + _coverage_block(
            "C. Historical coverage for key hitting metrics",
            (
                "Coverage shows the share of eligible hitter-seasons in which each metric was available. "
                "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                "create selection bias or limit universal model use."
            ),
            "coverage-filters-hitter",
            "coverage-hitter-frame",
            "Key hitting metrics",
            "figures/coverage_hitter.html",
            "figures/coverage_hitter_all.html",
            "Historical coverage for key hitting metrics",
        )
        + """
    </details>
    """
    )


def _pitching_research_visuals() -> str:
    guide = _five_test_guide(
        "Each row is a metric tested for predicting next-season FIP. Each column represents one part of the feature-admission process. Darker cells mean the metric ranked better relative to the other tested pitcher metrics on that criterion.",
        PITCHING_MATRIX_TESTS,
    )
    return (
        """
    <details class="diagnostics">
      <summary>View full research diagnostics</summary>
      <div class="diag-block">
        <h3>A. How every pitcher metric was evaluated</h3>
        """
        + guide
        + """
        <iframe class="iframe iframe-heat" title="Pitching admission heatmap" src="figures/heatmap_pitcher.html"></iframe>
      </div>
      <div class="diag-block">
        <h3>B. Coefficient stability for key pitching metrics</h3>
        <p class="diag-caption">Final Projection metrics are shown alongside a small set of important diagnostic comparisons.
        Standardized coefficients show how each metric’s modeled relationship with next-season FIP changed across temporal folds.
        Solid lines are Projection metrics; dashed lines are diagnostic comparisons.
        Names wrap under the chart so every series stays visible. Click a name to hide or show it. Hover a line for the exact coefficient.</p>
        <p class="diag-link"><a href="figures/coef_paths_pitcher_all.html">Show all tested metrics</a> (technical coefficient table)</p>
        <iframe class="iframe iframe-coef" title="Coefficient stability for key pitching metrics" src="figures/coef_paths_pitcher.html"></iframe>
      </div>
    """
        + _coverage_block(
            "C. Historical coverage for key pitching metrics",
            (
                "Coverage shows the share of eligible pitcher-seasons in which each metric was available. "
                "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                "create selection bias or limit universal model use."
            ),
            "coverage-filters-pitcher",
            "coverage-pitcher-frame",
            "Key pitching metrics",
            "figures/coverage_pitcher.html",
            "figures/coverage_pitcher_all.html",
            "Historical coverage for key pitching metrics",
        )
        + """
    </details>
    """
    )


def _coef_stability_block(
    heading: str,
    caption: str,
    table_href: str,
    iframe_src: str,
    iframe_title: str,
) -> str:
    return (
        f'<div class="diag-block">'
        f"<h3>{heading}</h3>"
        f'<p class="diag-caption">{caption}</p>'
        f'<p class="diag-link"><a href="{table_href}">Show all tested metrics</a> (technical coefficient table)</p>'
        f'<iframe class="iframe iframe-coef" title="{iframe_title}" src="{iframe_src}"></iframe>'
        "</div>"
    )


def _coverage_block(
    heading: str,
    caption: str,
    filter_id: str,
    frame_id: str,
    key_label: str,
    key_src: str,
    all_src: str,
    iframe_title: str,
) -> str:
    return f"""
      <div class="diag-block">
        <h3>{heading}</h3>
        <p class="diag-caption">{caption}</p>
        <div class="map-filters" id="{filter_id}">
          <button type="button" class="active" data-src="{key_src}">{key_label}</button>
          <button type="button" data-src="{all_src}">Show all tested metrics</button>
        </div>
        <iframe class="iframe iframe-cov" id="{frame_id}" title="{iframe_title}" src="{key_src}"></iframe>
        <script>
        (function(){{
          var frame = document.getElementById("{frame_id}");
          var buttons = document.querySelectorAll("#{filter_id} button");
          buttons.forEach(function(btn){{
            btn.addEventListener("click", function(){{
              buttons.forEach(function(b){{ b.classList.remove("active"); }});
              btn.classList.add("active");
              frame.src = btn.getAttribute("data-src");
            }});
          }});
        }})();
        </script>
      </div>
    """


def _component_matrix_visuals(
    heading: str,
    how_to_read: str,
    tests: tuple[str, ...],
    iframe_src: str,
    iframe_title: str,
    extra_heat: tuple[str, str, str] | None = None,
    extra_html: str = "",
) -> str:
    guide = _five_test_guide(how_to_read, tests)
    extra = ""
    first_heading = ""
    if extra_heat:
        extra_heading, extra_src, extra_title = extra_heat
        first_heading = "<h4>Position-player WAR rate</h4>"
        extra = (
            f'<h4>{extra_heading}</h4>'
            f'<iframe class="iframe iframe-heat" title="{extra_title}" src="{extra_src}"></iframe>'
        )
    return (
        """
    <details class="diagnostics">
      <summary>View full research diagnostics</summary>
      <div class="diag-block">
        <h3>"""
        + heading
        + """</h3>
        """
        + guide
        + first_heading
        + f"""
        <iframe class="iframe iframe-heat" title="{iframe_title}" src="{iframe_src}"></iframe>
        {extra}
      </div>
      {extra_html}
    </details>
    """
    )


def _player_page(table: pd.DataFrame, player_type: str) -> str:
    if player_type == "hitter":
        return _component_page(
            table, "hitting", "y_woba", "hitter",
            "",
            None,
            None,
        ) + _hitting_research_visuals()
    return _component_page(
        table, "pitching", "y_fip", "pitcher",
        "",
        None,
        None,
    ) + _pitching_research_visuals()


def _kitchen_sentence(path: Path, admitted_label: str, kitchen_label: str) -> str:
    if not path.exists():
        return ""
    k = json.loads(path.read_text())
    adm = k.get("admitted_rmse")
    kit = k.get("kitchen_rmse")
    boot = k.get("bootstrap") or {}
    excludes = boot.get("ci_excludes_zero")
    delta = boot.get("rmse_delta_kitchen_minus_admitted")
    adm_txt = f"{adm:.5f}" if adm is not None else "n/a"
    kit_txt = f"{kit:.5f}" if kit is not None else "n/a"
    if excludes and delta is not None and delta > 0:
        return (
            f"The {admitted_label} generalized better than the {kitchen_label} "
            f"(RMSE {adm_txt} vs {kit_txt}); uncertainty around the difference excluded zero."
        )
    if excludes and delta is not None and delta < 0:
        return (
            f"The {kitchen_label} had lower error than the {admitted_label} "
            f"(RMSE {kit_txt} vs {adm_txt}); uncertainty around the difference excluded zero."
        )
    return (
        f"The {admitted_label} and {kitchen_label} were close "
        f"(RMSE {adm_txt} vs {kit_txt}); uncertainty included zero, so the study does not support a clear difference."
    )


def _models_page() -> str:
    return f"""
    <p class="lede"><b>Lower error is better.</b> Each bar is mean expanding-window RMSE for that component's next-season target.</p>
    <h2>Hitting (next-season wOBA)</h2>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_hitter.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Hitting model comparison" src="figures/models_hitter.html"></iframe>
    <h2>Pitching (next-season FIP)</h2>
    <p>How well do different feature sets predict next-season FIP?</p>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_pitching_fip.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Pitching FIP model comparison" src="figures/models_pitching_fip.html"></iframe>
    <h2>Baserunning</h2>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_baserunning_rv.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Baserunning model comparison" src="figures/models_baserunning.html"></iframe>
    <h2>Defense</h2>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_defense_rv.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Defense model comparison" src="figures/models_defense.html"></iframe>
    <h2>Position-player WAR rate</h2>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_overall_war.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Position-player WAR model comparison" src="figures/models_overall.html"></iframe>
    <h2>Pitcher WAR rate</h2>
    <p>{_kitchen_sentence(ARTIFACTS / "kitchen_sink_comparison_pitcher_war.json", "admitted-feature model", "all-feature model")}</p>
    <iframe class="iframe" title="Pitcher WAR model comparison" src="figures/models_pitcher_war.html"></iframe>
    """


def _passports_html(table: pd.DataFrame) -> str:
    idx_path = ARTIFACTS / "passports" / "index.json"
    if not idx_path.exists():
        from psl.config import PASSPORTS
        idx_path = PASSPORTS / "index.json"
    if not idx_path.exists():
        return "<p>Passports not generated yet.</p>"
    index = json.loads(idx_path.read_text())
    order = {
        "Target-dependent": 0,
        "Projection": 1,
        "Augmented Projection": 2,
        "Diagnostic": 3,
        "Insufficient Evidence": 4,
        "Context": 5,
        "Exclude": 6,
    }
    index = sorted(
        index,
        key=lambda r: (order.get(r["verdict"], 9), r.get("display_name") or display_name(r["feature"], r["player_type"])),
    )
    name_counts: dict[str, int] = {}
    for r in index:
        shown = r.get("display_name") or display_name(r["feature"], r["player_type"])
        name_counts[shown] = name_counts.get(shown, 0) + 1
    cards = []
    search_items = []
    for r in index:
        sub = table[(table.player_type == r["player_type"]) & (table.feature == r["feature"])]
        blurb = r.get("blurb") or (passport_blurb(sub.iloc[0]) if len(sub) else "")
        name = r.get("display_name") or display_name(r["feature"], r["player_type"])
        label = _hero_label(r["player_type"], r["feature"], name_counts)
        href = f'passports/{r["slug"]}.html'
        vclass = _verdict_class(r["verdict"])
        cards.append(
            f'<article class="passport-card" data-label="{html.escape(label, quote=True)}" '
            f'data-name="{html.escape(name, quote=True)}">'
            f'<a href="{html.escape(href, quote=True)}">'
            f"{html.escape(name)}</a>"
            f'<div class="meta">{display_player(r["player_type"])} · '
            f'<span class="verdict {vclass}">{html.escape(str(r["verdict"]))}</span></div>'
            f'<p class="why">{html.escape(str(blurb))}</p>'
            f"</article>"
        )
        search_items.append({"label": label, "href": href})
    search_items = sorted(search_items, key=lambda item: item["label"].lower())
    options = "".join(
        f'<option value="{html.escape(item["label"], quote=True)}"></option>'
        for item in search_items
    )
    payload = json.dumps({"metrics": search_items}, ensure_ascii=True).replace("<", "\\u003c")
    return f"""
    <p class="lede">Each passport is one metric’s admission record. Open a card for the full evidence; the sentence is the public takeaway.</p>
    <div class="hero-pick passport-search">
      <label for="passport-search">Search metrics</label>
      <input id="passport-search" list="passport-metric-list" placeholder="Search or select a metric" autocomplete="off" spellcheck="false"/>
      <datalist id="passport-metric-list">{options}</datalist>
    </div>
    <p class="passport-empty" id="passport-empty" hidden>No passports match that search.</p>
    <div class="passport-grid" id="passport-grid">{''.join(cards)}</div>
    <script type="application/json" id="passport-search-data">{payload}</script>
    <script>
    (function(){{
      var raw = document.getElementById("passport-search-data");
      var search = document.getElementById("passport-search");
      var grid = document.getElementById("passport-grid");
      var empty = document.getElementById("passport-empty");
      if (!raw || !search || !grid) return;
      var data = JSON.parse(raw.textContent);
      var byLabel = {{}};
      data.metrics.forEach(function(m){{ byLabel[m.label.toLowerCase()] = m; }});
      var cards = Array.prototype.slice.call(grid.querySelectorAll(".passport-card"));
      function findMetric(q) {{
        var key = String(q || "").trim().toLowerCase();
        if (!key) return null;
        if (byLabel[key]) return byLabel[key];
        var hits = data.metrics.filter(function(m){{ return m.label.toLowerCase() === key; }});
        return hits.length === 1 ? hits[0] : null;
      }}
      function filterCards(q) {{
        var key = String(q || "").trim().toLowerCase();
        var shown = 0;
        cards.forEach(function(card){{
          var label = (card.getAttribute("data-label") || "").toLowerCase();
          var name = (card.getAttribute("data-name") || "").toLowerCase();
          var ok = !key || label.indexOf(key) !== -1 || name.indexOf(key) !== -1;
          card.classList.toggle("is-hidden", !ok);
          card.classList.toggle("is-match", ok && !!key && (label === key || name === key));
          if (ok) shown += 1;
        }});
        if (empty) empty.hidden = shown > 0;
      }}
      function goToMetric(q) {{
        var metric = findMetric(q);
        if (metric) {{
          window.location.href = metric.href;
          return true;
        }}
        filterCards(q);
        return false;
      }}
      search.addEventListener("input", function(){{ filterCards(search.value); }});
      search.addEventListener("change", function(){{ goToMetric(search.value); }});
      search.addEventListener("keydown", function(ev){{
        if (ev.key === "Enter") {{
          ev.preventDefault();
          goToMetric(search.value);
        }}
      }});
    }})();
    </script>
    """


def _universe_html() -> str:
    return render_universe_audit_html()


def _methodology_html(audit: dict) -> str:
    return render_methodology_html(audit)


def build_site() -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    table = without_kbb_outcome_target(pd.read_parquet(ARTIFACTS / "admission_table.parquet"))
    audit = json.loads((DATA_PROCESSED / "panel_audit.json").read_text())

    index_body = f"""
    {_hero_html(table)}
    {_projecting_html(audit)}
    <h2>The same pattern across the catalog</h2>
    <p>The same baseball metric can have a different role depending on what future outcome we are projecting.
    These charts show the clearest examples, not every tested metric. Full catalogs live on the component pages, Feature Audit, and passports.</p>
    <div class="chart-with-panel chart-with-panel-jobs">
      <iframe class="iframe" id="jobs-frame" title="One metric, different jobs" src="figures/one_metric_jobs.html"></iframe>
      <aside class="metric-panel" id="jobs-panel">
        <p class="placeholder">Hover a metric on the chart to see details here.</p>
      </aside>
    </div>
    <h2>Target-dependence matrix</h2>
    <iframe class="iframe iframe-deps" title="Position-player target dependence" src="figures/target_dependence_hitter.html"></iframe>
    <p class="diag-caption">A dash (—) means the metric was <b>not evaluated for that target</b>.
    It does not mean Exclude, it does not mean the metric has no predictive value, and it does not mean the data are missing.</p>
    <iframe class="iframe iframe-deps-pitcher" title="Pitcher target dependence" src="figures/target_dependence_pitcher.html"></iframe>
    <p class="diag-caption">The pitcher matrix only includes metrics evaluated for both next-season FIP and next-season pitcher WAR rate.
    Stuff+, four-seam velocity, whiff rate, release extension, and spin were evaluated for FIP and appear on the Pitching page;
    they are omitted here so empty cells are not mistaken for results.</p>
    {_headline_html(table)}
    {_surprise_html()}
    <h2>Verdict counts</h2>
    {_counts(table)}
    {_reliability_map_html()}
    """

    pages = {
        "index.html": ("Findings", index_body),
        "hitters.html": ("Hitting", _player_page(table, "hitter")),
        "pitchers.html": ("Pitching", _player_page(table, "pitcher")),
        "baserunning.html": (
            "Baserunning",
            _component_page(table, "baserunning", "y_br_rv_rate", "hitter", "", None, None)
            + _component_matrix_visuals(
                "A. How every baserunning metric was evaluated",
                "Each row is a metric tested for predicting next-season baserunning run-value rate. Each column represents one part of the feature-admission process. Darker cells mean the metric ranked better relative to the other tested baserunning metrics on that criterion.",
                BASERUNNING_MATRIX_TESTS,
                "figures/heatmap_baserunning.html",
                "Baserunning admission heatmap",
                extra_html=(
                    _coef_stability_block(
                        "B. Coefficient stability for key baserunning metrics",
                        "Final Projection metrics are shown alongside a small set of important diagnostic comparisons. Standardized coefficients show how each metric’s modeled relationship with next-season baserunning value changed across temporal folds. Solid lines are Projection metrics; dashed lines are diagnostic comparisons.",
                        "figures/coef_paths_baserunning_all.html",
                        "figures/coef_paths_baserunning.html",
                        "Coefficient stability for key baserunning metrics",
                    )
                    + _coverage_block(
                        "C. Historical coverage for key baserunning metrics",
                        (
                            "Coverage shows the share of eligible baserunning-seasons in which each metric was available. "
                            "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                            "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                            "create selection bias or limit universal model use."
                        ),
                        "coverage-filters-baserunning",
                        "coverage-baserunning-frame",
                        "Key baserunning metrics",
                        "figures/coverage_baserunning.html",
                        "figures/coverage_baserunning_all.html",
                        "Historical coverage for key baserunning metrics",
                    )
                ),
            ),
        ),
        "defense.html": (
            "Defense",
            _component_page(table, "defense", "y_def_rv_rate", "hitter", "", None, None)
            + _component_matrix_visuals(
                "A. How every defensive metric was evaluated",
                "Each row is a metric tested for predicting next-season fielding run-value rate. Each column represents one part of the feature-admission process. Darker cells mean the metric ranked better relative to the other tested defensive metrics on that criterion.",
                DEFENSE_MATRIX_TESTS,
                "figures/heatmap_defense.html",
                "Defense admission heatmap",
                extra_html=(
                    _coef_stability_block(
                        "B. Coefficient stability for key defensive metrics",
                        "Final Projection metrics are shown alongside a small set of important diagnostic comparisons. Standardized coefficients show how each metric’s modeled relationship with next-season fielding value changed across temporal folds. Solid lines are Projection metrics; dashed lines are diagnostic comparisons.",
                        "figures/coef_paths_defense_all.html",
                        "figures/coef_paths_defense.html",
                        "Coefficient stability for key defensive metrics",
                    )
                    + _coverage_block(
                        "C. Historical coverage for key defensive metrics",
                        (
                            "Coverage shows the share of eligible defense-seasons in which each metric was available. "
                            "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                            "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                            "create selection bias or limit universal model use."
                        ),
                        "coverage-filters-defense",
                        "coverage-defense-frame",
                        "Key defensive metrics",
                        "figures/coverage_defense.html",
                        "figures/coverage_defense_all.html",
                        "Historical coverage for key defensive metrics",
                    )
                ),
            ),
        ),
        "overall.html": (
            "Overall Value",
            _component_page(table, "overall", "y_war_rate", "hitter", "", None, None)
            + "<h2>Pitcher WAR rate</h2>"
            + _component_page(
                table[table.player_type.eq("pitcher")],
                "overall",
                "y_war_rate",
                "pitcher",
                "",
                None,
                None,
                show_callout=False,
            )
            + _component_matrix_visuals(
                "A. How every overall-value metric was evaluated",
                "Each row is a metric tested for predicting next-season WAR rate. The first matrix is position-player WAR rate; the second is pitcher WAR rate. Each column represents one part of the feature-admission process. Darker cells mean the metric ranked better relative to the other tested metrics in that matrix.",
                OVERALL_MATRIX_TESTS,
                "figures/heatmap_overall.html",
                "Overall-value admission heatmap",
                extra_heat=("Pitcher WAR rate", "figures/heatmap_pitcher_war.html", "Pitcher WAR admission heatmap"),
                extra_html=(
                    _coef_stability_block(
                        "B. Coefficient stability for key position-player WAR metrics",
                        "Final Projection metrics are shown alongside a small set of important diagnostic comparisons. Standardized coefficients show how each metric’s modeled relationship with next-season position-player WAR rate changed across temporal folds. Solid lines are Projection metrics; dashed lines are diagnostic comparisons.",
                        "figures/coef_paths_overall_all.html",
                        "figures/coef_paths_overall.html",
                        "Coefficient stability for key position-player WAR metrics",
                    )
                    + _coef_stability_block(
                        "C. Coefficient stability for key pitcher WAR metrics",
                        "Final Projection metrics are shown alongside a small set of important diagnostic comparisons. Standardized coefficients show how each metric’s modeled relationship with next-season pitcher WAR rate changed across temporal folds. Solid lines are Projection metrics; dashed lines are diagnostic comparisons.",
                        "figures/coef_paths_pitcher_war_all.html",
                        "figures/coef_paths_pitcher_war.html",
                        "Coefficient stability for key pitcher WAR metrics",
                    )
                    + _coverage_block(
                        "D. Historical coverage for key position-player WAR metrics",
                        (
                            "Coverage shows the share of eligible position-player seasons in which each metric was available. "
                            "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                            "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                            "create selection bias or limit universal model use."
                        ),
                        "coverage-filters-overall",
                        "coverage-overall-frame",
                        "Key position-player WAR metrics",
                        "figures/coverage_overall.html",
                        "figures/coverage_overall_all.html",
                        "Historical coverage for key position-player WAR metrics",
                    )
                    + _coverage_block(
                        "E. Historical coverage for key pitcher WAR metrics",
                        (
                            "Coverage shows the share of eligible pitcher-seasons in which each metric was available. "
                            "Each row is a metric and each column is a season, so metrics with the same coverage stay visible "
                            "instead of stacking on one line. Differences in coverage matter because incomplete features may "
                            "create selection bias or limit universal model use."
                        ),
                        "coverage-filters-pitcher-war",
                        "coverage-pitcher-war-frame",
                        "Key pitcher WAR metrics",
                        "figures/coverage_pitcher_war.html",
                        "figures/coverage_pitcher_war_all.html",
                        "Historical coverage for key pitcher WAR metrics",
                    )
                ),
            ),
        ),
        "models.html": ("Models", _models_page()),
        "methodology.html": ("Methodology", _methodology_html(audit)),
        "passports.html": ("Passports", _passports_html(table)),
        "feature-audit.html": ("Feature Universe Audit", _universe_html()),
    }
    (RESEARCH_DIR / "style.css").write_text(CSS)
    for name, (title, body) in pages.items():
        (RESEARCH_DIR / name).write_text(_page(title, name, body))
    (RESEARCH_DIR / "universe.html").write_text(
        """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta http-equiv="refresh" content="0; url=feature-audit.html"/>
<link rel="canonical" href="feature-audit.html"/>
<title>Feature Audit · Projection Signal Lab</title>
</head><body><p><a href="feature-audit.html">Feature Audit</a></p></body></html>
"""
    )
    (RESEARCH_DIR / "map.html").write_text(
        """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta http-equiv="refresh" content="0; url=index.html#reliability-map"/>
<link rel="canonical" href="index.html#reliability-map"/>
<title>Reliability Map · Projection Signal Lab</title>
</head><body><p><a href="index.html#reliability-map">Reliability Map</a></p></body></html>
"""
    )
    from psl.config import PASSPORTS
    from psl.artifacts.passports import passport_html_body
    from psl.site.passport_copy import build_forecast_peer_ranks

    dest = RESEARCH_DIR / "passports"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    src = PASSPORTS
    if src.exists():
        scatter_src = src / "scatters"
        if scatter_src.exists():
            shutil.copytree(scatter_src, dest / "scatters")
    peer_ranks = build_forecast_peer_ranks(table)
    for (pt, feat), group in table.groupby(["player_type", "feature"], sort=False):
        slug = f"{pt}_{feat}"
        shown = display_name(feat, pt)
        (dest / f"{slug}.html").write_text(
            _page(shown, "passports.html", passport_html_body(group, peer_ranks), prefix="../")
        )
    fig_dest = RESEARCH_DIR / "figures"
    if fig_dest.exists():
        shutil.rmtree(fig_dest)
    if FIGURES.exists():
        shutil.copytree(FIGURES, fig_dest)
    audit = audit_table_copy(table)
    print("Public table Why audit:")
    for verdict, stats in audit.items():
        share = 100.0 * stats["identical_share"]
        print(
            f"  {verdict}: n={stats['n']} identical_share={share:.1f}% "
            f"empty={stats['empty']} unique={stats.get('unique')} "
            f"most_common_n={stats['most_common_n']}"
        )
        if stats["most_common_n"] > 1:
            print(f"    most_common: {stats['most_common']}")
    return RESEARCH_DIR
