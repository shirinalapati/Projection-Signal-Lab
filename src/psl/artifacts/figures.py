"""Flagship figures from admission artifacts. Public hover copy only."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from psl.config import ARTIFACTS, DATA_PROCESSED, FIGURES, SITE_DIR
from psl.site.labels import (
    MAP_ANNOTATIONS,
    PUBLIC_MODEL_ORDER,
    VERDICT_SYMBOL,
    admitted_model_rmse,
    component_phrase,
    display_name,
    display_model,
    fmt_model_impact,
    hover_why,
    map_hover_text,
    fmt_coverage,
    target_phrase,
    verdict_for_target,
    without_kbb_outcome_target,
)

VERDICT_COLOR = {
    "Projection": "#1b4d3e",
    "Augmented Projection": "#2f6f9f",
    "Diagnostic": "#b86b2a",
    "Context": "#6b5b95",
    "Exclude": "#7a7a7a",
    "Insufficient Evidence": "#c4a035",
}

PLOTLY_CONFIG = {"responsive": True, "displaylogo": False}
JOBS_PLOTLY_CONFIG = {**PLOTLY_CONFIG, "displayModeBar": False}

HOVERTEXT_TEMPLATE = "%{hovertext}<extra></extra>"

HOVERLABEL = {
    "align": "left",
    "bgcolor": "white",
    "font": {"size": 13, "family": "Georgia, serif"},
    "bordercolor": "#d7cfc2",
}

HITTER_DIAG_LABELS = {"bb_pct": "BB%"}

HITTER_COEF_DEFAULT = (
    "woba_w2",
    "woba_w3",
    "xwoba_w2",
    "ev",
    "barrel_pct",
    "hard_hit_pct",
    "o_swing_pct",
    "k_pct",
    "bb_pct",
)
HITTER_COVERAGE_DEFAULT = (
    "woba_w2",
    "xwoba_w2",
    "xwoba",
    "ev",
    "barrel_pct",
    "hard_hit_pct",
    "o_swing_pct",
    "k_pct",
    "bb_pct",
    "xslg",
)
PITCHER_COEF_DEFAULT = (
    "fip_w2",
    "k_bb_pct_w3",
    "stuff_plus",
    "extension",
    "ff_velo",
    "avg_velo",
    "avg_spin",
    "whiff_rate",
)
PITCHER_COVERAGE_DEFAULT = (
    "fip_w2",
    "k_bb_pct_w2",
    "k_pct",
    "stuff_plus",
    "avg_velo",
    "ff_velo",
    "extension",
    "whiff_rate",
    "arm_angle",
    "park_factor",
)
BASERUNNING_COEF_DEFAULT = (
    "br_rv_rate_w2",
    "br_rv_rate_w3",
    "sprint_speed",
    "attempt_rate",
    "second_to_home_rate",
    "hp_to_1b",
    "sb_pct",
)
BASERUNNING_COVERAGE_DEFAULT = BASERUNNING_COEF_DEFAULT
DEFENSE_COEF_DEFAULT = (
    "def_rv_rate_w2",
    "def_rv_rate_w3",
    "oaa",
    "epcaa",
    "sprint_speed",
    "errors",
)
DEFENSE_COVERAGE_DEFAULT = DEFENSE_COEF_DEFAULT
OVERALL_HITTER_COEF_DEFAULT = (
    "war_rate_w2",
    "ev",
    "woba_w2",
    "xwoba_w2",
    "br_rv_rate_w2",
    "def_rv_rate_w2",
    "sprint_speed",
)
OVERALL_HITTER_COVERAGE_DEFAULT = OVERALL_HITTER_COEF_DEFAULT
OVERALL_PITCHER_COEF_DEFAULT = (
    "war_rate_w2",
    "k_bb_pct_w2",
    "fip_w2",
    "age",
    "ip",
    "starter_role",
)
OVERALL_PITCHER_COVERAGE_DEFAULT = OVERALL_PITCHER_COEF_DEFAULT
HEATMAP_CRITERIA = (
    ("oos_score", "Future Prediction"),
    ("stability", "Stable Over Time"),
    ("redundancy", "Unique Information"),
    ("cov", "Data Coverage"),
    ("subgroup", "Consistent Across Players"),
)
HEATMAP_TICKTEXT = (
    "Future<br>Prediction",
    "Stable Over<br>Time",
    "Unique<br>Information",
    "Data<br>Coverage",
    "Consistent Across<br>Players",
)


PLOT_MARGIN = {"l": 64, "r": 28, "t": 56, "b": 48}
PLOT_HEIGHT = 460

HTML_LEGEND_STYLE = """<style>
html,body{margin:0;background:#fffdf8;}
.plotly-graph-div,.js-plotly-plot{height:460px !important;width:100% !important;}
.psl-legend{display:flex;flex-wrap:wrap;gap:8px 10px;padding:12px 14px 20px;font-family:Georgia,serif;}
.psl-legend button{
  display:inline-flex;align-items:center;gap:8px;max-width:100%;
  margin:0;padding:6px 10px;border:1px solid #d7cfc2;background:#fffdf8;
  font:13px/1.3 Georgia,serif;color:#15202b;cursor:pointer;border-radius:3px;text-align:left;
}
.psl-legend button.is-off{opacity:0.38;}
.psl-legend i{width:22px;height:0;border-top:3px solid #15202b;display:inline-block;flex:0 0 22px;}
</style>
"""

HTML_LEGEND_SCRIPT = """
(function(){
  var gd=document.querySelector('.js-plotly-plot, .plotly-graph-div');
  if(!gd) return;
  function colorOf(i){
    var tr=(gd._fullData&&gd._fullData[i])||(gd.data&&gd.data[i]);
    if(!tr) return '#5c6b73';
    if(tr.line&&tr.line.color) return tr.line.color;
    if(tr.marker&&tr.marker.color) return tr.marker.color;
    return '#5c6b73';
  }
  function render(){
    var old=document.querySelector('.psl-legend');
    if(old) old.remove();
    var box=document.createElement('div');
    box.className='psl-legend';
    (gd.data||[]).forEach(function(tr,i){
      if(tr.showlegend===false) return;
      var btn=document.createElement('button');
      btn.type='button';
      var vis=tr.visible;
      if(vis==='legendonly'||vis===false) btn.classList.add('is-off');
      var sw=document.createElement('i');
      sw.style.borderTopColor=colorOf(i);
      if(tr.line&&tr.line.dash&&tr.line.dash!=='solid') sw.style.borderTopStyle='dashed';
      btn.appendChild(sw);
      btn.appendChild(document.createTextNode(tr.name||('Series '+(i+1))));
      btn.addEventListener('click', function(){
        var on=gd.data[i].visible!=='legendonly'&&gd.data[i].visible!==false;
        Plotly.restyle(gd,{visible:on?'legendonly':true},[i]).then(render);
      });
      box.appendChild(btn);
    });
    if(gd.parentNode) gd.parentNode.insertBefore(box, gd.nextSibling);
  }
  render();
})();
"""

HTML_LEGEND_FILES = {
    "coef_paths_hitter.html",
    "coef_paths_pitcher.html",
    "coef_paths_baserunning.html",
    "coef_paths_defense.html",
    "coef_paths_overall.html",
    "coef_paths_pitcher_war.html",
}


def _chart_name(feature, player_type: str) -> str:
    return HITTER_DIAG_LABELS.get(str(feature), display_name(feature, player_type))


def _ordinal_pct(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    n = int(round(float(value) * 100))
    n = min(100, max(0, n))
    if 11 <= (n % 100) <= 13:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf} percentile"


def _coverage_series(val) -> tuple[list[int], list[float]]:
    val = _parse_jsonish(val)
    if not isinstance(val, dict) or not val:
        return [], []
    years = sorted(int(y) for y in val)
    ys = []
    for year in years:
        raw = val.get(year, val.get(str(year)))
        ys.append(float(raw) if raw is not None else float("nan"))
    return years, ys

POST_SCRIPT = (
    "var plots=document.getElementsByClassName('js-plotly-plot');"
    "function resizePlots(){for(var i=0;i<plots.length;i++){Plotly.Plots.resize(plots[i]);}}"
    "window.addEventListener('resize', resizePlots);"
)


def _hover_panel_script(panel_id: str) -> str:
    """Send hover details to the parent page panel. Do not draw Plotly's floating box."""
    return f"""
(function(){{
  var plot=document.querySelector('.js-plotly-plot, .plotly-graph-div');
  if(!plot || !plot.on) return;
  var style=document.createElement('style');
  style.textContent='.hoverlayer,.hovertext,g.hoverlayer{{display:none !important;visibility:hidden !important;}}';
  document.head.appendChild(style);
  function send(html){{
    if(window.parent && window.parent!==window){{
      window.parent.postMessage({{type:'psl-metric-panel', panel:{panel_id!r}, html: html||''}}, '*');
    }}
  }}
  plot.on('plotly_hover', function(e){{
    var pt=e.points && e.points[0];
    if(!pt) return;
    var html=pt.hovertext || pt.text || '';
    if(!html && pt.data && pt.data.hovertext){{
      var idx=pt.pointIndex;
      html=Array.isArray(pt.data.hovertext) ? (pt.data.hovertext[idx]||'') : pt.data.hovertext;
    }}
    send(html);
  }});
  plot.on('plotly_unhover', function(){{ send(''); }});
}})();
"""

RELIABILITY_POST_SCRIPT = (
    POST_SCRIPT
    + """
(function(){
  var plots=document.getElementsByClassName('js-plotly-plot');
  for (var i=0;i<plots.length;i++){
    var gd=plots[i];
    gd.on('plotly_click', function(e){
      if(!e.points || !e.points.length) return;
      var d=e.points[0].customdata;
      if(!d) return;
      var pt=Array.isArray(d)?d[0]:d;
      var feat=Array.isArray(d)?d[1]:null;
      if(!pt || !feat) return;
      var url='../passports/'+pt+'_'+feat+'.html';
      if(window.parent && window.parent!==window){ window.parent.location.href=url; }
      else { window.location.href=url; }
    });
    gd.on('plotly_hover', function(){ gd.style.cursor='pointer'; });
    gd.on('plotly_unhover', function(){ gd.style.cursor='default'; });
  }
})();
"""
    + _hover_panel_script("map-panel")
)


def _parse_jsonish(x):
    if isinstance(x, str) and x[:1] in "[{":
        try:
            return json.loads(x)
        except json.JSONDecodeError:
            return x
    return x


def _load_table() -> pd.DataFrame:
    p = ARTIFACTS / "admission_table.parquet"
    if not p.exists():
        raise FileNotFoundError(p)
    df = pd.read_parquet(p)
    for c in ("coverage_by_season", "coverage_by_pa_tier", "coverage_by_role", "fold_rmse_deltas", "coef_path", "subgroup", "extra", "correlation_folds"):
        if c in df.columns:
            df[c] = df[c].apply(_parse_jsonish)
    return without_kbb_outcome_target(df)


PRIMARY_TARGETS = {
    "hitting": "y_woba",
    "pitching": "y_fip",
    "baserunning": "y_br_rv_rate",
    "defense": "y_def_rv_rate",
    "overall": "y_war_rate",
}

COMPONENT_LABEL = {
    "hitting": "Hitting",
    "pitching": "Pitching",
    "baserunning": "Baserunning",
    "defense": "Defense",
    "overall": "Overall value",
}


def primary_slice(table: pd.DataFrame) -> pd.DataFrame:
    df = table.copy()
    if "component" not in df.columns or "target" not in df.columns:
        return df
    parts = []
    for comp, tgt in PRIMARY_TARGETS.items():
        parts.append(df[df.component.eq(comp) & df.target.eq(tgt)])
    out = pd.concat(parts, ignore_index=True) if parts else df
    return out if len(out) else df


def reliability_map(table: pd.DataFrame, player_type: str | None = None, component: str | None = None) -> go.Figure:
    df = primary_slice(table).copy()
    if component:
        df = df[df.component == component]
    elif player_type:
        df = df[df.player_type == player_type]
        if player_type == "hitter" and "component" in df.columns:
            df = df[df.component.eq("hitting")]
        if player_type == "pitcher" and "target" in df.columns:
            df = df[df.target.eq("y_fip")]
    df = df[df.oos_rmse_delta.notna() & df.reliability_pearson.notna()].copy()
    df["oos_lift"] = -df["oos_rmse_delta"]
    df["coverage_size"] = (df["coverage"].fillna(0) * 40 + 8).clip(8, 48)
    df["stability_n"] = len(df)
    df["stability_rank"] = df["reliability_pearson"].rank(ascending=False, method="min").astype(int)
    fig = go.Figure()
    for verdict in VERDICT_COLOR:
        sub = df[df.verdict == verdict]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["reliability_pearson"],
                y=sub["oos_lift"],
                mode="markers",
                name=verdict,
                marker={
                    "size": sub["coverage_size"],
                    "color": VERDICT_COLOR[verdict],
                    "symbol": VERDICT_SYMBOL.get(verdict, "circle"),
                    "line": {"width": 0.6, "color": "#fff"},
                    "opacity": 0.9,
                },
                hovertext=[map_hover_text(row) for _, row in sub.iterrows()],
                customdata=sub[["player_type", "feature"]].astype(str).to_numpy(),
                hovertemplate=None,
                hoverinfo="none",
            )
        )
    fig.add_hline(y=0, line_dash="dot", line_color="#999")
    keys = MAP_ANNOTATIONS.get(component or player_type or "", ())
    if not player_type and not component:
        keys = MAP_ANNOTATIONS["hitter"] + MAP_ANNOTATIONS["pitcher"]
    for feat in keys:
        hit = df[df.feature == feat]
        if player_type:
            hit = hit[hit.player_type == player_type]
        if hit.empty:
            continue
        row = hit.iloc[0]
        fig.add_annotation(
            x=float(row["reliability_pearson"]),
            y=float(row["oos_lift"]),
            text=display_name(feat, row["player_type"]),
            showarrow=True,
            arrowhead=0,
            arrowcolor="#5c6b73",
            font={"size": 11, "color": "#15202b"},
            bgcolor="rgba(255,253,248,0.85)",
            borderpad=3,
            ax=18,
            ay=-18,
        )
    title = "Reliability Map"
    if component:
        title = f"Reliability Map — {COMPONENT_LABEL.get(component, component)}"
    elif player_type == "hitter":
        title = "Reliability Map — Hitters"
    elif player_type == "pitcher":
        title = "Reliability Map — Pitchers"
    fig.update_layout(
        template="plotly_white",
        legend_title="Verdict",
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
            "xanchor": "left",
            "x": 0,
        },
        height=620,
        margin={"l": 60, "r": 24, "t": 60, "b": 110},
        xaxis_title="Year-to-year stability",
        yaxis_title="Incremental future predictive value",
        title=title,
        hoverlabel={"align": "left", "bgcolor": "white", "font": {"size": 12}, "namelength": -1},
        autosize=True,
        hovermode="closest",
    )
    return fig


def admission_heatmap(
    table: pd.DataFrame,
    player_type: str,
    *,
    component: str | None = None,
    target: str | None = None,
) -> go.Figure:
    df = primary_slice(table)
    df = df[df.player_type == player_type].copy()
    if component:
        df = df[df.component.eq(component)]
    elif player_type == "hitter" and "component" in df.columns:
        df = df[df.component.eq("hitting")]
    if target:
        df = df[df.target.eq(target)]
    elif player_type == "pitcher" and "target" in df.columns:
        df = df[df.target.eq("y_fip")]
    df["display"] = [display_name(f, player_type) for f in df["feature"]]
    df["oos_score"] = -df["oos_rmse_delta"]
    df["stability"] = df["reliability_pearson"]
    df["redundancy"] = 1 - df["max_corr_with_baseline"].clip(0, 1)
    df["cov"] = df["coverage"]

    def _sub(x):
        if not isinstance(x, dict):
            return np.nan
        ok = [v.get("rmse_delta") for v in x.values() if isinstance(v, dict) and v.get("ok")]
        ok = [v for v in ok if v is not None]
        if not ok:
            return np.nan
        return float(np.mean([v < 0 for v in ok]))

    df["subgroup"] = df["subgroup"].apply(_sub)
    df = df.reset_index(drop=True)
    zcols = [c for c, _ in HEATMAP_CRITERIA]
    labels = [lab for _, lab in HEATMAP_CRITERIA]
    ranked = df[zcols].rank(pct=True)
    hover = []
    for i, row in df.iterrows():
        line = []
        name = row["display"]
        verdict = row["verdict"]
        for j, (col, lab) in enumerate(HEATMAP_CRITERIA):
            standing = ranked.iloc[i, j]
            detail = f"{lab}: {_ordinal_pct(standing)}"
            if col == "cov":
                detail += f"<br>Observed in {fmt_coverage(row.get('coverage'))} of eligible seasons"
            line.append(
                f"<b>{name}</b><br>"
                f"{detail}<br>"
                f"Final verdict: {verdict}"
            )
        hover.append(line)
    fig = go.Figure(
        data=go.Heatmap(
            z=ranked.to_numpy(),
            x=labels,
            y=df["display"].tolist(),
            zmin=0,
            zmax=1,
            colorscale="Tealgrn",
            colorbar={
                "title": {"text": "Percentile among<br>tested metrics", "side": "right"},
                "tickvals": [0, 0.25, 0.5, 0.75, 1],
                "ticktext": ["0", "25th", "50th", "75th", "100th"],
                "ticksuffix": "",
                "len": 0.55,
                "y": 0.5,
                "ypad": 12,
            },
            hovertext=hover,
            hoverinfo="text",
            hovertemplate=HOVERTEXT_TEMPLATE,
        )
    )
    fig.update_layout(
        title=None,
        height=max(480, 22 * len(df) + 48),
        template="plotly_white",
        hoverlabel=HOVERLABEL,
        autosize=True,
        margin={"l": 210, "r": 118, "t": 72, "b": 28},
        xaxis={
            "side": "top",
            "tickangle": 0,
            "tickmode": "array",
            "tickvals": labels,
            "ticktext": list(HEATMAP_TICKTEXT),
            "tickfont": {"size": 12},
            "automargin": True,
        },
        yaxis={"automargin": True, "tickfont": {"size": 11}},
    )
    return fig


def coef_paths(
    table: pd.DataFrame,
    player_type: str,
    features: list[str] | tuple[str, ...],
    *,
    component: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
) -> go.Figure:
    fig = go.Figure()
    sub = primary_slice(table)
    sub = sub[sub.player_type == player_type]
    if component:
        sub = sub[sub.component.eq(component)]
    elif player_type == "hitter":
        sub = sub[sub.component.eq("hitting")]
    elif player_type == "pitcher":
        sub = sub[sub.component.eq("pitching")]
    order = {name: i for i, name in enumerate(features)}
    sub = sub[sub.feature.isin(features)].copy()
    sub["_ord"] = sub["feature"].map(order)
    sub = sub.sort_values("_ord")
    for _, row in sub.iterrows():
        path = row.get("coef_path")
        if isinstance(path, np.ndarray):
            path = path.tolist()
        if not isinstance(path, list) or not path:
            continue
        years = [p.get("test_year") for p in path if isinstance(p, dict)]
        coefs = [p.get("coef") for p in path if isinstance(p, dict)]
        label = _chart_name(row["feature"], player_type)
        verdict = str(row.get("verdict") or "")
        projection = verdict.startswith("Projection")
        color = VERDICT_COLOR.get(verdict.split()[0], "#5c6b73")
        texts = []
        for year, coef in zip(years, coefs):
            coef_txt = "n/a" if coef is None or (isinstance(coef, float) and pd.isna(coef)) else f"{float(coef):+.3f}"
            texts.append(
                f"<b>{label}</b><br>"
                f"Test year: {year}<br>"
                f"Standardized coefficient: {coef_txt}<br>"
                f"Verdict: {verdict}"
            )
        fig.add_trace(
            go.Scatter(
                x=years,
                y=coefs,
                mode="lines+markers",
                name=label,
                line={"color": color, "dash": "solid" if projection else "dash", "width": 2.4 if projection else 1.8},
                marker={"color": color},
                hovertext=texts,
                hoverinfo="text",
                hovertemplate=HOVERTEXT_TEMPLATE,
            )
        )
    fig.add_hline(y=0, line_dash="dot", line_color="#999")
    who = "Hitters" if player_type == "hitter" else "Pitchers"
    title_txt = title or f"How each metric’s weight moved across test years — {who}"
    fig.update_layout(
        title={"text": title_txt, "x": 0, "xanchor": "left"},
        xaxis_title="Test year",
        yaxis_title="Standardized coefficient",
        template="plotly_white",
        height=PLOT_HEIGHT,
        hoverlabel=HOVERLABEL,
        autosize=True,
        showlegend=False,
        margin=PLOT_MARGIN,
        xaxis={"automargin": True},
        yaxis={"automargin": True},
    )
    return fig


_COVERAGE_SKIP = {
    "mlbam_id",
    "player_id",
    "season",
    "year",
    "name",
    "player_name",
    "team",
    "team_id",
    "role",
    "throws",
    "bats",
    "index",
}


def coverage_chart(player_type: str) -> go.Figure:
    path = DATA_PROCESSED / "panel_audit.json"
    audit = json.loads(path.read_text())
    key = "hitter_coverage" if player_type == "hitter" else "pitcher_coverage"
    cov = audit[key]
    fig = go.Figure()
    for metric, payload in cov.items():
        if str(metric) in _COVERAGE_SKIP or str(metric).endswith("_id"):
            continue
        by = payload.get("coverage_by_season") or {}
        if not by:
            continue
        years = sorted(int(y) for y in by)
        ys = [by[str(y)] if str(y) in by else by[y] for y in years]
        label = display_name(metric, player_type)
        texts = [
            f"<b>{label}</b><br>Season: {year}<br>Coverage: {float(val):.0%}"
            for year, val in zip(years, ys)
        ]
        fig.add_trace(
            go.Scatter(
                x=years,
                y=ys,
                mode="lines+markers",
                name=label,
                hovertext=texts,
                hoverinfo="text",
                hovertemplate=HOVERTEXT_TEMPLATE,
            )
        )
    who = "Hitters" if player_type == "hitter" else "Pitchers"
    fig.update_layout(
        title=f"How complete each metric is by season — {who}",
        xaxis_title="Season",
        yaxis_title="Share of player-seasons with the metric",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1.05],
        template="plotly_white",
        height=PLOT_HEIGHT,
        hoverlabel=HOVERLABEL,
        autosize=True,
        showlegend=False,
        margin=PLOT_MARGIN,
        xaxis={"automargin": True},
        yaxis={"automargin": True},
    )
    return fig


def coverage_from_admission(
    table: pd.DataFrame,
    player_type: str,
    *,
    component: str,
    target: str,
    features: tuple[str, ...] | list[str] | None = None,
    title: str,
    subtitle: str | None = None,
) -> go.Figure:
    sub = table[table.player_type.eq(player_type) & table.component.eq(component) & table.target.eq(target)].copy()
    if features is not None:
        order = {name: i for i, name in enumerate(features)}
        sub = sub[sub.feature.isin(features)].copy()
        sub["_ord"] = sub["feature"].map(order)
        sub = sub.sort_values("_ord")
    else:
        sub = sub.sort_values("feature")
    rows = []
    for _, row in sub.iterrows():
        years, ys = _coverage_series(row.get("coverage_by_season"))
        if not years:
            continue
        rows.append(
            (
                _chart_name(row["feature"], player_type),
                years,
                ys,
                str(row.get("verdict") or ""),
            )
        )
    all_years = sorted({year for _, years, _, _ in rows for year in years})
    z = []
    hover = []
    labels = []
    for label, years, ys, verdict in rows:
        lookup = dict(zip(years, ys))
        vals = [lookup.get(year) for year in all_years]
        z.append([float(v) if v is not None else np.nan for v in vals])
        labels.append(label)
        hover.append(
            [
                (
                    f"<b>{label}</b><br>"
                    f"Season: {year}<br>"
                    f"Coverage: {float(val):.0%}<br>"
                    f"Verdict: {verdict}"
                    if val is not None
                    else f"<b>{label}</b><br>Season: {year}<br>Coverage: n/a<br>Verdict: {verdict}"
                )
                for year, val in zip(all_years, vals)
            ]
        )
    # Plotly draws the first heatmap row at the bottom; reverse so catalog order reads top-down.
    z = z[::-1]
    labels = labels[::-1]
    hover = hover[::-1]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=[str(year) for year in all_years],
            y=labels,
            zmin=0,
            zmax=1,
            colorscale="Tealgrn",
            colorbar={
                "title": {"text": "Coverage", "side": "right"},
                "tickvals": [0, 0.5, 1],
                "ticktext": ["0%", "50%", "100%"],
                "len": 0.55,
                "y": 0.5,
            },
            hovertext=hover,
            hoverinfo="text",
            hovertemplate=HOVERTEXT_TEMPLATE,
        )
    )
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left"},
        xaxis_title="Season",
        yaxis_title=None,
        template="plotly_white",
        height=max(360, 24 * max(len(labels), 1) + 88),
        hoverlabel=HOVERLABEL,
        autosize=True,
        showlegend=False,
        margin={"l": 210, "r": 96, "t": 56, "b": 48},
        xaxis={"type": "category", "automargin": True},
        yaxis={"automargin": True, "tickfont": {"size": 11}},
    )
    return fig


def dropone_importance(
    table: pd.DataFrame,
    player_type: str,
    component: str,
    target: str,
) -> go.Figure:
    sub = table[
        table.player_type.eq(player_type)
        & table.component.eq(component)
        & table.target.eq(target)
        & table.verdict.eq("Projection")
    ].copy()
    sub = sub.dropna(subset=["dropone_oos_rmse"])
    sub = sub.sort_values("dropone_oos_rmse", ascending=True)
    names = [_chart_name(f, player_type) for f in sub["feature"]]
    deltas = [float(v) for v in sub["dropone_oos_rmse"]]
    study_id = str(sub.iloc[0].get("study_id") or "") if not sub.empty else ""
    full_rmse = admitted_model_rmse(study_id)
    if full_rmse and full_rmse > 0:
        vals = [100.0 * d / full_rmse for d in deltas]
        x_title = "Increase in prediction error when removed (%)"
        hover_vals = [
            fmt_model_impact(delta, full_rmse, name)
            for name, delta in zip(names, deltas)
        ]
    else:
        vals = deltas
        x_title = "RMSE increase when the metric is removed (larger = more needed)"
        hover_vals = [f"Drop-one OOS importance: {val:+.5f}" for val in vals]
    verdicts = sub["verdict"].astype(str).tolist()
    texts = [
        f"<b>{name}</b><br>"
        f"{impact}<br>"
        f"Verdict: {verdict}"
        for name, impact, verdict in zip(names, hover_vals, verdicts)
    ]
    fig = go.Figure(
        data=go.Bar(
            x=vals,
            y=names,
            orientation="h",
            marker_color="#1b4d3e",
            hovertext=texts,
            hoverinfo="text",
            hovertemplate=HOVERTEXT_TEMPLATE,
        )
    )
    fig.update_layout(
        title="What matters most in the final hitting projection?",
        xaxis_title=x_title,
        yaxis_title="",
        template="plotly_white",
        height=max(320, 56 * len(names) + 80),
        hoverlabel=HOVERLABEL,
        autosize=True,
        margin={"l": 140, "r": 24, "t": 60, "b": 50},
        showlegend=False,
    )
    fig.add_vline(x=0, line_dash="dot", line_color="#999")
    return fig


def write_coef_table_html(
    table: pd.DataFrame,
    dest: Path,
    player_type: str,
    component: str,
    target: str,
    *,
    audience: str | None = None,
) -> Path:
    sub = table[
        table.player_type.eq(player_type) & table.component.eq(component) & table.target.eq(target)
    ].copy()
    sub = sub.sort_values(["verdict", "feature"])
    rows = []
    years = set()
    parsed = []
    for _, row in sub.iterrows():
        path = row.get("coef_path")
        if isinstance(path, np.ndarray):
            path = path.tolist()
        by_year = {}
        if isinstance(path, list):
            for item in path:
                if isinstance(item, dict) and item.get("test_year") is not None:
                    by_year[int(item["test_year"])] = item.get("coef")
                    years.add(int(item["test_year"]))
        parsed.append((row, by_year))
    years_sorted = sorted(years)
    header = (
        "<th>Metric</th><th>Verdict</th>"
        + "".join(f"<th>{y}</th>" for y in years_sorted)
    )
    for row, by_year in parsed:
        cells = "".join(
            f"<td>{'' if by_year.get(y) is None else f'{float(by_year[y]):+.3f}'}</td>"
            for y in years_sorted
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(_chart_name(row['feature'], player_type))}</td>"
            f"<td>{html.escape(str(row['verdict']))}</td>"
            f"{cells}</tr>"
        )
    who = audience or ("hitter" if player_type == "hitter" else "pitcher")
    tgt = target_phrase(target)
    dest.write_text(
        f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Coefficient paths — all tested {html.escape(who)} metrics</title>
<style>
body {{ font-family: Georgia, serif; margin: 24px; background: #f6f1e8; color: #15202b; }}
h1 {{ font-size: 1.4rem; }}
p {{ max-width: 46rem; color: #5c6b73; }}
table {{ border-collapse: collapse; background: #fffdf8; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #d7cfc2; padding: 6px 8px; text-align: left; }}
th {{ font-variant: small-caps; }}
</style>
</head><body>
<h1>Coefficient stability — all tested {html.escape(who)} metrics</h1>
<p>Standardized coefficients from the expanding-window Ridge fits against {html.escape(tgt)}.
This table is the technical companion to the curated coefficient chart. Open a metric passport for interpretation.</p>
<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>
"""
    )
    return dest


VERDICT_RANK = {
    "Projection": 5,
    "Augmented Projection": 4,
    "Diagnostic": 3,
    "Context": 2,
    "Exclude": 1,
    "Insufficient Evidence": 0,
}

# Visual top-to-bottom on Findings. Curated for target dependence, not coverage.
HITTER_DEPENDENCE_METRICS = (
    "sprint_speed",
    "ev",
    "xwoba_w2",
    "br_rv_rate_w2",
    "def_rv_rate_w2",
    "age",
)
PITCHER_DEPENDENCE_METRICS = (
    "k_bb_pct_w2",
    "fip_w2",
    "age",
)
JOBS_METRICS = (
    "sprint_speed",
    "ev",
    "xwoba_w2",
    "br_rv_rate_w2",
    "def_rv_rate_w2",
)
NOT_EVALUATED = "—"
NOT_EVALUATED_HOVER = "Not evaluated for this target"


def _dependence_frame(table: pd.DataFrame, metrics: tuple[str, ...], columns: list[tuple[str, str, str | None]]) -> tuple[pd.DataFrame, list[str]]:
    df = table.copy()
    z = []
    text = []
    y_labels = []
    for feat in metrics:
        rows_z = []
        rows_t = []
        any_hit = False
        for _comp, tgt, pt in columns:
            sub = df[df.feature.eq(feat) & df.target.eq(tgt)]
            if pt:
                sub = sub[sub.player_type.eq(pt)]
            if _comp:
                sub = sub[sub.component.eq(_comp)]
            if sub.empty:
                rows_z.append(None)
                rows_t.append(NOT_EVALUATED)
            else:
                any_hit = True
                v = str(sub.iloc[0]["verdict"])
                rows_z.append(VERDICT_RANK.get(v))
                rows_t.append(v)
        if any_hit:
            y_labels.append(display_name(feat, columns[0][2]))
            z.append(rows_z)
            text.append(rows_t)
    x = []
    for comp, tgt, _pt in columns:
        x.append(f"{component_phrase(comp)}<br>{target_phrase(tgt)}")
    return pd.DataFrame(z, index=y_labels, columns=x), text


def target_dependence_heatmap(table: pd.DataFrame, kind: str) -> go.Figure:
    if kind == "hitter":
        cols = [
            ("hitting", "y_woba", "hitter"),
            ("baserunning", "y_br_rv_rate", "hitter"),
            ("defense", "y_def_rv_rate", "hitter"),
            ("overall", "y_war_rate", "hitter"),
        ]
        metrics = HITTER_DEPENDENCE_METRICS
        title = "Target-dependence matrix — position players"
    else:
        cols = [
            ("pitching", "y_fip", "pitcher"),
            ("overall", "y_war_rate", "pitcher"),
        ]
        metrics = PITCHER_DEPENDENCE_METRICS
        title = "Target-dependence matrix — pitchers"
    mat, text = _dependence_frame(table, metrics, cols)
    mat = mat.iloc[::-1]
    text = list(reversed(text))
    hover = []
    for i, feat_label in enumerate(mat.index):
        line = []
        for j, col in enumerate(mat.columns):
            v = text[i][j]
            col_label = col.replace("<br>", " · ")
            if v == NOT_EVALUATED:
                line.append(f"<b>{feat_label}</b><br>{col_label}<br>{NOT_EVALUATED_HOVER}")
            else:
                line.append(f"<b>{feat_label}</b><br>{col_label}<br>Verdict: {v}")
        hover.append(line)
    fig = go.Figure(
        data=go.Heatmap(
            z=mat.to_numpy(dtype=float),
            x=list(mat.columns),
            y=list(mat.index),
            text=text,
            texttemplate="%{text}",
            colorscale=[
                [0.0, "#c4a035"],
                [0.2, "#7a7a7a"],
                [0.4, "#6b5b95"],
                [0.6, "#b86b2a"],
                [0.8, "#2f6f9f"],
                [1.0, "#1b4d3e"],
            ],
            zmin=0,
            zmax=5,
            showscale=False,
            hovertext=hover,
            hoverinfo="text",
            hovertemplate=HOVERTEXT_TEMPLATE,
        )
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=max(360, 48 * len(mat.index) + 120),
        margin={"l": 180, "r": 24, "t": 60, "b": 80},
        hoverlabel={"align": "left", "bgcolor": "white"},
        autosize=True,
    )
    return fig


def one_metric_jobs(table: pd.DataFrame) -> go.Figure:
    df = primary_slice(without_kbb_outcome_target(table)).copy()
    traces_y = []
    traces_x = []
    colors = []
    texts = []
    comp_rank = {comp: i for i, comp in enumerate(PRIMARY_TARGETS)}
    for feat in JOBS_METRICS:
        sub = df[df.feature.eq(feat)].drop_duplicates("component")
        if len(sub) < 2:
            continue
        sub = sub.copy()
        sub["_ord"] = sub["component"].map(comp_rank).fillna(99)
        sub = sub.sort_values("_ord")
        shown = display_name(feat, sub.iloc[0]["player_type"])
        for _, row in sub.iterrows():
            label = component_phrase(row.get("component"))
            if label.lower() == "overall value":
                label = "Overall"
            traces_y.append(f"{shown}<br>{label}")
            traces_x.append(VERDICT_RANK.get(str(row.verdict), 0))
            colors.append(VERDICT_COLOR.get(str(row.verdict), "#999"))
            texts.append(
                f"<b>{display_name(feat, row.get('player_type'))}</b><br>"
                f"{verdict_for_target(row)}<br>"
                f"Takeaway: {hover_why(row)}"
            )
    tick_items = sorted(VERDICT_RANK.items(), key=lambda item: item[1])
    fig = go.Figure(
        data=go.Bar(
            x=traces_x,
            y=traces_y,
            orientation="h",
            marker_color=colors,
            hovertext=texts,
            hoverinfo="none",
            hovertemplate=None,
        )
    )
    fig.update_layout(
        title="One metric, different jobs",
        xaxis=dict(
            title=dict(text="Admission verdict", standoff=12),
            tickmode="array",
            tickvals=[rank for _name, rank in tick_items],
            ticktext=[name for name, _rank in tick_items],
            tickangle=-35,
            automargin=True,
            ticklabeloverflow="allow",
            range=[-0.5, 5.5],
            tickfont=dict(size=12),
        ),
        yaxis=dict(autorange="reversed", automargin=True, tickfont=dict(size=12)),
        template="plotly_white",
        height=max(620, 44 * len(traces_y) + 180),
        margin={"l": 8, "r": 16, "t": 48, "b": 100},
        hovermode="closest",
        autosize=True,
        showlegend=False,
        bargap=0.32,
    )
    return fig


def model_comparison_chart(player_type: str | None = None, stem: str | None = None, title: str | None = None) -> go.Figure:
    path = ARTIFACTS / f"model_comparison_{stem or player_type}.parquet"
    df = pd.read_parquet(path)
    show = df[df["model"].isin(PUBLIC_MODEL_ORDER)].copy()
    show["label"] = show["model"].map(display_model)
    show = show.drop_duplicates("label")
    order = [display_model(m) for m in PUBLIC_MODEL_ORDER if display_model(m) in set(show["label"])]
    show["label"] = pd.Categorical(show["label"], categories=order, ordered=True)
    show = show.sort_values("mean_rmse", ascending=True)
    texts = []
    for _, row in show.iterrows():
        nfeat = "" if pd.isna(row.get("n_features")) else str(int(row["n_features"]))
        texts.append(
            f"<b>{row['label']}</b><br>"
            f"Mean out-of-time RMSE: {float(row['mean_rmse']):.5f}<br>"
            f"Feature count: {nfeat}<br>"
            "Lower error is better."
        )
    fig = go.Figure(
        data=go.Bar(
            x=show["mean_rmse"],
            y=show["label"].astype(str),
            orientation="h",
            marker_color="#1b4d3e",
            hovertext=texts,
            hoverinfo="text",
            hovertemplate=HOVERTEXT_TEMPLATE,
        )
    )
    who = title or ("Hitters" if player_type == "hitter" else "Pitchers")
    fig.update_layout(
        title=f"Out-of-time prediction error — {who}",
        xaxis_title="Mean expanding-window RMSE (lower is better)",
        yaxis_title="",
        template="plotly_white",
        height=420,
        hoverlabel={"align": "left", "bgcolor": "white"},
        autosize=True,
        margin={"l": 200, "r": 24, "t": 60, "b": 50},
    )
    return fig


def write_all() -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    table = _load_table()
    fip_cmp = ARTIFACTS / "model_comparison_pitching_fip.parquet"
    pit_cmp = ARTIFACTS / "model_comparison_pitcher.parquet"
    if fip_cmp.exists():
        shutil.copy2(fip_cmp, pit_cmp)
        csv = ARTIFACTS / "model_comparison_pitching_fip.csv"
        if csv.exists():
            shutil.copy2(csv, ARTIFACTS / "model_comparison_pitcher.csv")
    fip_kit = ARTIFACTS / "kitchen_sink_comparison_pitching_fip.json"
    pit_kit = ARTIFACTS / "kitchen_sink_comparison_pitcher.json"
    if fip_kit.exists():
        shutil.copy2(fip_kit, pit_kit)
    written = []
    figs = {
        "reliability_map.html": reliability_map(table),
        "reliability_map_hitter.html": reliability_map(table, "hitter"),
        "reliability_map_pitcher.html": reliability_map(table, "pitcher"),
        "reliability_map_hitting.html": reliability_map(table, component="hitting"),
        "reliability_map_pitching.html": reliability_map(table, component="pitching"),
        "reliability_map_baserunning.html": reliability_map(table, component="baserunning"),
        "reliability_map_defense.html": reliability_map(table, component="defense"),
        "reliability_map_overall.html": reliability_map(table, component="overall"),
        "heatmap_hitter.html": admission_heatmap(table, "hitter"),
        "heatmap_pitcher.html": admission_heatmap(table, "pitcher"),
        "heatmap_baserunning.html": admission_heatmap(
            table, "hitter", component="baserunning", target="y_br_rv_rate"
        ),
        "heatmap_defense.html": admission_heatmap(
            table, "hitter", component="defense", target="y_def_rv_rate"
        ),
        "heatmap_overall.html": admission_heatmap(
            table, "hitter", component="overall", target="y_war_rate"
        ),
        "heatmap_pitcher_war.html": admission_heatmap(
            table, "pitcher", component="overall", target="y_war_rate"
        ),
        "target_dependence_hitter.html": target_dependence_heatmap(table, "hitter"),
        "target_dependence_pitcher.html": target_dependence_heatmap(table, "pitcher"),
        "one_metric_jobs.html": one_metric_jobs(table),
        "coef_paths_hitter.html": coef_paths(
            table,
            "hitter",
            HITTER_COEF_DEFAULT,
            component="hitting",
            title="Coefficient stability for key hitting metrics",
            subtitle=(
                "Final Projection metrics are shown alongside a small set of important diagnostic comparisons. "
                "Standardized coefficients show how each metric's modeled relationship with next-season wOBA changed across temporal folds."
            ),
        ),
        "coef_paths_pitcher.html": coef_paths(
            table,
            "pitcher",
            PITCHER_COEF_DEFAULT,
            component="pitching",
            title="Coefficient stability for key pitching metrics",
        ),
        "coef_paths_baserunning.html": coef_paths(
            table,
            "hitter",
            BASERUNNING_COEF_DEFAULT,
            component="baserunning",
            title="Coefficient stability for key baserunning metrics",
        ),
        "coef_paths_defense.html": coef_paths(
            table,
            "hitter",
            DEFENSE_COEF_DEFAULT,
            component="defense",
            title="Coefficient stability for key defensive metrics",
        ),
        "coef_paths_overall.html": coef_paths(
            table,
            "hitter",
            OVERALL_HITTER_COEF_DEFAULT,
            component="overall",
            title="Coefficient stability for key position-player WAR metrics",
        ),
        "coef_paths_pitcher_war.html": coef_paths(
            table,
            "pitcher",
            OVERALL_PITCHER_COEF_DEFAULT,
            component="overall",
            title="Coefficient stability for key pitcher WAR metrics",
        ),
        "coverage_hitter.html": coverage_from_admission(
            table,
            "hitter",
            component="hitting",
            target="y_woba",
            features=HITTER_COVERAGE_DEFAULT,
            title="Historical coverage for key hitting metrics",
            subtitle=(
                "Coverage shows the share of eligible hitter-seasons in which each metric was available. "
                "Differences in coverage matter because incomplete features may create selection bias or limit universal model use."
            ),
        ),
        "coverage_hitter_all.html": coverage_from_admission(
            table,
            "hitter",
            component="hitting",
            target="y_woba",
            title="Historical coverage — all tested hitter metrics",
        ),
        "coverage_pitcher.html": coverage_from_admission(
            table,
            "pitcher",
            component="pitching",
            target="y_fip",
            features=PITCHER_COVERAGE_DEFAULT,
            title="Historical coverage for key pitching metrics",
        ),
        "coverage_pitcher_all.html": coverage_from_admission(
            table,
            "pitcher",
            component="pitching",
            target="y_fip",
            title="Historical coverage — all tested pitcher metrics",
        ),
        "coverage_baserunning.html": coverage_from_admission(
            table,
            "hitter",
            component="baserunning",
            target="y_br_rv_rate",
            features=BASERUNNING_COVERAGE_DEFAULT,
            title="Historical coverage for key baserunning metrics",
        ),
        "coverage_baserunning_all.html": coverage_from_admission(
            table,
            "hitter",
            component="baserunning",
            target="y_br_rv_rate",
            title="Historical coverage — all tested baserunning metrics",
        ),
        "coverage_defense.html": coverage_from_admission(
            table,
            "hitter",
            component="defense",
            target="y_def_rv_rate",
            features=DEFENSE_COVERAGE_DEFAULT,
            title="Historical coverage for key defensive metrics",
        ),
        "coverage_defense_all.html": coverage_from_admission(
            table,
            "hitter",
            component="defense",
            target="y_def_rv_rate",
            title="Historical coverage — all tested defensive metrics",
        ),
        "coverage_overall.html": coverage_from_admission(
            table,
            "hitter",
            component="overall",
            target="y_war_rate",
            features=OVERALL_HITTER_COVERAGE_DEFAULT,
            title="Historical coverage for key position-player WAR metrics",
        ),
        "coverage_overall_all.html": coverage_from_admission(
            table,
            "hitter",
            component="overall",
            target="y_war_rate",
            title="Historical coverage — all tested position-player WAR metrics",
        ),
        "coverage_pitcher_war.html": coverage_from_admission(
            table,
            "pitcher",
            component="overall",
            target="y_war_rate",
            features=OVERALL_PITCHER_COVERAGE_DEFAULT,
            title="Historical coverage for key pitcher WAR metrics",
        ),
        "coverage_pitcher_war_all.html": coverage_from_admission(
            table,
            "pitcher",
            component="overall",
            target="y_war_rate",
            title="Historical coverage — all tested pitcher WAR metrics",
        ),
        "dropone_hitter.html": dropone_importance(table, "hitter", "hitting", "y_woba"),
        "models_hitter.html": model_comparison_chart("hitter"),
        "models_pitcher.html": model_comparison_chart("pitcher"),
        "models_baserunning.html": model_comparison_chart(stem="baserunning_rv", title="Baserunning"),
        "models_defense.html": model_comparison_chart(stem="defense_rv", title="Defense"),
        "models_overall.html": model_comparison_chart(stem="overall_war", title="Position-player WAR"),
        "models_pitcher_war.html": model_comparison_chart(stem="pitcher_war", title="Pitcher WAR"),
        "models_pitching_fip.html": model_comparison_chart(stem="pitching_fip", title="Pitching (FIP)"),
    }
    for name, fig in figs.items():
        dest = FIGURES / name
        use_html_legend = name in HTML_LEGEND_FILES
        html_kwargs = {
            "include_plotlyjs": "cdn",
            "config": JOBS_PLOTLY_CONFIG if name == "one_metric_jobs.html" else PLOTLY_CONFIG,
            "full_html": True,
            "post_script": (
                RELIABILITY_POST_SCRIPT if name.startswith("reliability_map")
                else (POST_SCRIPT + _hover_panel_script("jobs-panel") if name == "one_metric_jobs.html"
                      else (POST_SCRIPT + HTML_LEGEND_SCRIPT if use_html_legend else POST_SCRIPT))
            ),
        }
        if use_html_legend:
            html_kwargs["default_height"] = PLOT_HEIGHT
        fig.write_html(dest, **html_kwargs)
        if name == "one_metric_jobs.html" or name.startswith("reliability_map"):
            html = dest.read_text()
            hide = "<style>.hoverlayer,.hovertext,g.hoverlayer{display:none!important;visibility:hidden!important}</style>"
            dest.write_text(html.replace("<head>", "<head>" + hide, 1))
        if use_html_legend:
            html = dest.read_text()
            dest.write_text(html.replace("<head>", "<head>" + HTML_LEGEND_STYLE, 1))
        written.append(dest)
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_hitter_all.html", "hitter", "hitting", "y_woba", audience="hitter"))
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_pitcher_all.html", "pitcher", "pitching", "y_fip", audience="pitcher"))
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_baserunning_all.html", "hitter", "baserunning", "y_br_rv_rate", audience="baserunning"))
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_defense_all.html", "hitter", "defense", "y_def_rv_rate", audience="defensive"))
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_overall_all.html", "hitter", "overall", "y_war_rate", audience="position-player WAR"))
    written.append(write_coef_table_html(table, FIGURES / "coef_paths_pitcher_war_all.html", "pitcher", "overall", "y_war_rate", audience="pitcher WAR"))
    table.to_json(ARTIFACTS / "admission_table.json", orient="records")
    return written
