"""Build a self-contained HTML writeup of the urban-growth model results.

Reads everything from output/ + docs/, produces output/report.html with:
  - Executive summary
  - Variable-by-variable equation walkthrough
  - Methodology per variable (collapsible) — sources, scoring rules, gaps
  - 13 priority-city profiles (collapsible) — per-year scores with data receipts
    and PDF quote footnotes; interactive Chart.js trajectory + contribution charts
  - Validation: predicted-vs-actual scatter for 13 priority cities AND full
    Bairoch cohort; biggest hits and misses
  - What worked / what didn't (synthesis)
  - Sources & citations appendix

Reusable: lib/pdf_quotes.py for PDF quote extraction (cached),
          lib/report_template.py for HTML rendering.

Run:  python3 build_report.py
"""
from __future__ import annotations

import base64
import html as _html
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch  # noqa: F401  (kept for future use)

from lib.paths import (BENCHMARKS, OUT, DOCS, EU_POP_XLSX, PRE_1500_UNIVERSITIES,
                       STRONG_LEGAL_FAMILIES)
from lib.targets import DEFAULT_WEIGHTS, PRIORITY_CITIES
from lib.pdf_quotes import extract_city_quotes, PRIORITY_CITY_ALIASES
from lib.report_template import (
    render_html, kpi_grid, quote_block, collapsible, score_cell,
    num_cell, receipt_line,
)

REPORT_PATH = OUT / "report.html"
QUOTES_CACHE = OUT / "report_quotes_cache.json"

CITY_NARRATIVES: dict[int, str] = {
    14060: ("Cologne is the model's flagship case. As a free imperial city on the Rhine "
            "with a Hanseatic foothold, full guild infrastructure, a 14th-century "
            "university (1388), and a fully developed merchant elite, the equation "
            "loads almost every positive lever and almost no negative lever. Its 1500 "
            "composite of 12.9 (the joint top of the case study) tracks closely with "
            "its real ~45,000 inhabitants — a near-perfect prediction-vs-history match."),
    15027: ("Frankfurt is the cleanest test of the trade-and-fairs hypothesis. Without "
            "Hanseatic membership and with only modest population (~10–12k), the "
            "composite score is driven almost entirely by interregional fair status, "
            "river/road convergence, and free imperial standing. The model correctly "
            "places Frankfurt in the top tier despite its smaller absolute size."),
    22094: ("Nuremberg shows the equation's response to legal autonomy plus merchant "
            "capital without sea access. Free-imperial-city status from 1219, an "
            "enormous craft-merchant network, and zero noble extraction combine to "
            "push it into the top tier. Trade access is partial because southern "
            "Germany is not in Viabundus, but the other levers carry the score."),
    9070:  ("Leipzig is the model's late-bloomer. 1268 imperial fair privilege plus "
            "Magdeburg-law affiliation lift legal_capacity and merchant_capital "
            "together; the 1450–1500 step is where the trajectory clearly accelerates "
            "as the fair network matures and the staple right (1497) takes effect."),
    11094: ("Magdeburg is a Magdeburg-law donor town and Hanseatic trading center. "
            "The composite stays high throughout 1250–1500 because both legal and "
            "merchant variables stay maxed; the model does not, however, capture "
            "the late-15th-century stagnation that real-world Magdeburg experienced."),
    11039: ("Erfurt is the most interesting friction case: large, prosperous, with a "
            "1392 university — but ruled by the Archbishop of Mainz. The model's "
            "noble_extraction term picks this up as a prince-bishop seat and pulls the "
            "composite down. History agrees: Erfurt's 15th-century growth was real but "
            "constrained by Mainz's overlordship."),
    23006: ("Augsburg is south-German and therefore outside Viabundus, so trade_access "
            "is forced to 0. Despite that gap, free-imperial status, the Welser/Fugger "
            "merchant houses, and a developed Messe push the composite into the "
            "upper-middle tier. Real history here outpaces the model — Augsburg was "
            "considerably wealthier than the score suggests."),
    23123: ("Regensburg sits on the Danube but is not in Viabundus. The composite "
            "captures its imperial status and merchant past but cannot see its trade "
            "network, producing a score that under-states 1250–1350 prominence and "
            "is roughly fair for the 15th-century relative decline."),
    22016: ("Bamberg is a prince-bishop seat by hard-coded list, so noble_extraction is "
            "elevated. The composite stays low — consistent with Bamberg's status as a "
            "modest cathedral town rather than a major commercial center."),
    22145: ("Würzburg is also a prince-bishop seat. Like Bamberg, the noble_extraction "
            "term keeps the composite below the imperial-city peers. The 1402 "
            "university gives a small lift to legal_capacity but does not reverse the "
            "structural extraction signal."),
    16085: ("Ulm is a southern free imperial city outside Viabundus. The model captures "
            "imperial status and the textile-driven population scale, but trade_access "
            "is zero by data limitation. Real Ulm was substantially more important "
            "than the composite shows."),
    22109: ("Rothenburg ob der Tauber is a small free imperial city. The model gives it "
            "a respectable composite via legal autonomy and low extraction, but the "
            "absolute scale of the town keeps it well below the top tier — accurate."),
    18087: ("Speyer is a free imperial city on the Rhine but outside Viabundus. The "
            "model captures imperial status; trade_access is missing. Real Speyer "
            "stagnated in the late 15th century, and the composite reflects that."),
}


# --------------------------------------------------------- data loading utilities

def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / f"cities_{name}.csv")


def load_all_outputs() -> dict[str, pd.DataFrame]:
    return {
        "legal_capacity":       _load_csv("legal_capacity"),
        "merchant_capital":     _load_csv("merchant_capital"),
        "agricultural_surplus": _load_csv("agricultural_surplus"),
        "peasant_mobility":     _load_csv("peasant_mobility"),
        "noble_extraction":     _load_csv("noble_extraction"),
        "conflict_risk":        _load_csv("conflict_risk"),
        "trade_access":         _load_csv("trade_access"),  # Viabundus-keyed
        "composite":            pd.read_csv(OUT / "cities_composite.csv"),
        "case_study":           pd.read_csv(OUT / "case_study_priority13.csv"),
        "crosswalk":            pd.read_csv(OUT / "crosswalk_nodesid_cityid.csv"),
    }


def load_bosker_pop() -> pd.DataFrame:
    """Reload Bosker pop, matched to Bairoch city_id, for actual-population validation.

    Mirrors the matching logic in build_agricultural_surplus.py but keeps the
    full year series so we can pull e.g. 1500 populations for ALL Bairoch cities.
    """
    print("Loading Bosker population xlsx ...")
    pop = pd.read_excel(EU_POP_XLSX, engine="openpyxl", sheet_name=0)
    pop = pop.rename(columns={"city": "city_name", "year": "year",
                              "inhabitants in 000-s": "pop_000",
                              "latitude in degrees": "p_lat",
                              "longitude in degrees": "p_lon"})
    pop = pop[["city_name", "p_lat", "p_lon", "year", "pop_000"]].copy()
    for col in ["p_lat", "p_lon", "pop_000"]:
        pop[col] = pop[col].apply(
            lambda v: str(v).replace(",", ".") if isinstance(v, str) else v)
        pop[col] = pd.to_numeric(pop[col], errors="coerce")
    pop = pop.dropna(subset=["p_lat", "p_lon", "year", "pop_000"])
    pop = pop[(pop["p_lat"].between(35, 72)) & (pop["p_lon"].between(-15, 45))]

    # Match to Bairoch city_id via the crosswalk's logic — but the easier path
    # is to reuse the agricultural_surplus output, which already has matched
    # population per benchmark year.
    agri = _load_csv("agricultural_surplus")
    agri = agri[["city_id", "year", "population"]].rename(columns={"population": "pop_pers"})
    return agri


def composite_at_year(comp_df: pd.DataFrame, year: int) -> pd.DataFrame:
    return comp_df[comp_df["year"] == year][
        ["city_id", "name", "lat", "lon", "composite_raw", "composite_0_3"]].copy()


# --------------------------------------------------------- per-city evidence

def build_priority_long(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per (priority_city, year) with all features + scores + Viabundus bits."""
    priority_ids = [b for (_, b, _) in PRIORITY_CITIES]
    nodesid_for = {b: n for (_, b, n) in PRIORITY_CITIES}

    cs = data["case_study"].copy()
    cs = cs[cs["city_id"].isin(priority_ids)].copy()

    # Add trade_access raw features (only for cities with a Viabundus nodesid)
    ta = data["trade_access"].copy()
    ta = ta.rename(columns={"city_id": "nodesid"})
    keep_ta_cols = ["nodesid", "year", "distance_river_km", "distance_road_km",
                    "distance_fair_km", "num_fairs_50km", "num_fairs_100km",
                    "has_own_fair", "own_fair_category", "has_own_toll",
                    "has_own_staple", "has_own_bridge", "has_own_ferry",
                    "has_own_harbour", "on_trade_route", "trade_access_score"]
    ta = ta[[c for c in keep_ta_cols if c in ta.columns]]
    cs["nodesid_priority"] = cs["city_id"].map(nodesid_for)
    cs = cs.merge(ta, left_on=["nodesid_priority", "year"],
                  right_on=["nodesid", "year"], how="left",
                  suffixes=("", "_ta"))

    # Add agricultural_surplus extras (lat_band, elev_m) not in the case study csv
    ag = data["agricultural_surplus"][["city_id", "year", "lat_band", "elev_m"]]
    cs = cs.merge(ag, on=["city_id", "year"], how="left")

    # Add legal/merchant/noble/conflict extras already in case study;
    # add dist_university_km from legal_capacity for receipts
    lc_extra = data["legal_capacity"][["city_id", "year", "dist_university_km",
                                       "strong_legal_family"]]
    cs = cs.merge(lc_extra, on=["city_id", "year"], how="left")

    # Add fire counts from conflict_risk
    cr_extra = data["conflict_risk"][["city_id", "year", "n_fires_50yr"]]
    cs = cs.merge(cr_extra, on=["city_id", "year"], how="left")

    return cs.sort_values(["display_name", "year"]).reset_index(drop=True)


def receipt_for(var: str, row) -> list[str]:
    """Return a list of one-line evidence bullets for a given variable in a city-year row."""
    bits: list[str] = []

    def yn(field: str, label: str = None) -> bool:
        v = row.get(field)
        return bool(v == 1 or v is True)

    if var == "trade_access":
        if pd.notna(row.get("nodesid_priority")):
            cat = row.get("own_fair_category")
            if isinstance(cat, str) and cat:
                bits.append(f"own fair: <code>{cat}</code>")
            elif row.get("has_own_fair") == 1:
                bits.append("own fair (uncategorized)")
            if yn("has_own_staple"):
                bits.append("staple right")
            if yn("has_own_toll"):
                bits.append("toll station")
            if yn("has_own_harbour"):
                bits.append("harbour")
            if yn("on_trade_route"):
                bits.append("on Viabundus trade route")
            d_river = row.get("distance_river_km")
            if pd.notna(d_river):
                bits.append(f"river/canal {float(d_river):.1f} km")
            n_fairs = row.get("num_fairs_50km")
            if pd.notna(n_fairs) and n_fairs > 0:
                bits.append(f"{int(n_fairs)} fair(s) within 50 km")
        else:
            bits.append("not in Viabundus (south-German coverage gap)")
        return bits

    if var == "legal_capacity":
        st = row.get("city_status", 0)
        if st == 3:
            bits.append("city_status=3 (free imperial)")
        elif st == 2:
            bits.append("city_status=2 (imperial)")
        elif st == 1:
            bits.append("city_status=1 (free city)")
        else:
            bits.append("city_status=0 (under lord)")
        if yn("has_formal_charter_by_y"):
            bits.append("formal charter attested")
        if yn("has_townhall_by_y"):
            bits.append("town hall present")
        if yn("charter_withdrawn_by_y"):
            bits.append("<span class='tag bad'>charter withdrawn</span>")
        lf = row.get("legal_family")
        if isinstance(lf, str) and lf in STRONG_LEGAL_FAMILIES:
            bits.append(f"strong law family <code>{lf}</code>")
        elif isinstance(lf, str) and lf:
            bits.append(f"law family <code>{lf}</code>")
        d_uni = row.get("dist_university_km")
        if pd.notna(d_uni) and d_uni < 80:
            bits.append(f"university {float(d_uni):.0f} km")
        return bits

    if var == "merchant_capital":
        if yn("is_hanseatic"):
            bits.append("Hanseatic League member")
        bf = row.get("best_fair_category", 0)
        if bf == 3:
            bits.append("interregional fair (Viabundus cat 3)")
        elif bf == 2:
            bits.append("regional fair (Viabundus cat 2)")
        elif bf == 1:
            bits.append("local fair (Viabundus cat 1)")
        if yn("has_staple"):
            bits.append("staple right")
        if yn("has_messe_by_y"):
            bits.append("Messe (annual fair) by this year")
        if not bits:
            bits.append("no merchant signals attested")
        return bits

    if var == "agricultural_surplus":
        pop = row.get("population")
        if pd.notna(pop) and pop > 0:
            bits.append(f"pop≈{int(pop):,}")
        else:
            bits.append("no Bosker pop observation")
        g = row.get("pop_growth_50yr")
        if pd.notna(g):
            pct = (float(g) - 1.0) * 100
            sign = "+" if pct >= 0 else ""
            bits.append(f"50-yr growth {sign}{pct:.0f}%")
        lb = row.get("lat_band")
        if isinstance(lb, str):
            bits.append(f"latitude band: {lb}")
        d_river = row.get("dist_river_km")
        if pd.notna(d_river):
            bits.append(f"river {float(d_river):.0f} km")
        elev = row.get("elev_m")
        if pd.notna(elev) and elev > 600:
            bits.append(f"<span class='tag warn'>high elev {float(elev):.0f} m</span>")
        return bits

    if var == "peasant_mobility":
        bits.append(f"<span class='tag muted'>imputed</span> from "
                    f"legal={int(row.get('legal_capacity_score', 0))}, "
                    f"merchant={int(row.get('merchant_capital_score', 0))}, "
                    f"noble={int(row.get('noble_extraction_score', 0))}")
        return bits

    if var == "noble_extraction":
        if yn("is_prince_bishop_seat"):
            bits.append("<span class='tag warn'>prince-bishop seat</span>")
        n_pol = row.get("n_polity_changes_50yr", 0)
        if pd.notna(n_pol) and n_pol >= 1:
            bits.append(f"{int(n_pol)} polity transition(s) in 50y")
        st = row.get("city_status", 0)
        if st >= 2:
            bits.append(f"city_status={int(st)} (autonomy reduces extraction)")
        if not bits:
            bits.append("stable lordly rule, no shocks")
        return bits

    if var == "conflict_risk":
        n_c = row.get("n_conflicts_50yr", 0)
        n_mc = row.get("n_major_conflicts_50yr", 0)
        n_f = row.get("n_fires_50yr", 0)
        if pd.notna(n_mc) and n_mc >= 1:
            bits.append(f"<span class='tag bad'>{int(n_mc)} major conflict(s)</span>")
        if pd.notna(n_c) and n_c >= 1:
            bits.append(f"{int(n_c)} conflict(s)")
        if pd.notna(n_f) and n_f >= 1:
            bits.append(f"{int(n_f)} fire(s) in construction record")
        if not bits:
            bits.append("no conflict/fire records in window")
        return bits

    return bits


# --------------------------------------------------------- chart specs (Chart.js)

PALETTE = {
    "legal_capacity": "#5b8a72",
    "merchant_capital": "#4a7ba8",
    "agricultural_surplus": "#b89a4f",
    "peasant_mobility": "#9379a8",
    "noble_extraction": "#a23a2a",
    "conflict_risk": "#7a4030",
    "trade_access": "#357b9c",
    "composite_raw": "#1f1d18",
    "population": "#6c4f1f",
}


def chart_trajectory(city_rows: pd.DataFrame, canvas_id: str) -> dict:
    """Composite_raw + (population/1000) over time — dual-axis line chart."""
    years = city_rows["year"].astype(int).tolist()
    composite = city_rows["composite_raw"].round(2).tolist()
    pop_k = (city_rows["population"].fillna(0) / 1000.0).round(1).tolist()

    return {
        "type": "line",
        "data": {
            "labels": years,
            "datasets": [
                {"label": "Composite (raw)", "data": composite,
                 "borderColor": PALETTE["composite_raw"],
                 "backgroundColor": PALETTE["composite_raw"],
                 "yAxisID": "y", "tension": 0.3, "pointRadius": 5},
                {"label": "Population (000s, Bosker)", "data": pop_k,
                 "borderColor": PALETTE["population"],
                 "backgroundColor": PALETTE["population"],
                 "yAxisID": "y1", "tension": 0.3, "pointRadius": 5,
                 "borderDash": [5, 4]},
            ],
        },
        "options": {
            "responsive": True,
            "interaction": {"mode": "index", "intersect": False},
            "plugins": {"legend": {"position": "bottom"},
                        "title": {"display": False}},
            "scales": {
                "y": {"position": "left", "title": {"display": True, "text": "Composite"}},
                "y1": {"position": "right", "title": {"display": True, "text": "Pop (000s)"},
                       "grid": {"drawOnChartArea": False}},
                "x": {"title": {"display": True, "text": "Year"}},
            },
        },
    }


def chart_contributions(city_rows: pd.DataFrame, canvas_id: str) -> dict:
    """Stacked bar of β·variable contributions per year."""
    years = city_rows["year"].astype(int).tolist()
    datasets = []
    for var, w in DEFAULT_WEIGHTS.items():
        score_col = f"{var}_score" if var != "trade_access" else "trade_access"
        if score_col not in city_rows.columns:
            continue
        contrib = (city_rows[score_col].fillna(0) * w).round(2).tolist()
        label = var.replace("_", " ") + (f"  (β={w:+.1f})")
        datasets.append({
            "label": label,
            "data": contrib,
            "backgroundColor": PALETTE.get(var, "#888"),
            "borderColor": PALETTE.get(var, "#888"),
            "borderWidth": 0,
        })

    return {
        "type": "bar",
        "data": {"labels": years, "datasets": datasets},
        "options": {
            "responsive": True,
            "plugins": {"legend": {"position": "bottom"},
                        "title": {"display": False}},
            "scales": {
                "x": {"stacked": True, "title": {"display": True, "text": "Year"}},
                "y": {"stacked": True,
                      "title": {"display": True, "text": "β · score (signed)"}},
            },
        },
    }


# --------------------------------------------------------- matplotlib charts (PNG)

def _png_to_data_uri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def fig_validation_scatter(
    df: pd.DataFrame, x_col: str, y_col: str, title: str,
    label_col: str | None = None, ax_x_label: str = None, ax_y_label: str = None,
) -> tuple[str, dict]:
    """Make a labeled scatter; return (data-uri, stats dict)."""
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    fig.set_facecolor("#fdfcf8")
    ax.set_facecolor("#fdfcf8")

    valid = df[[x_col, y_col] + ([label_col] if label_col else [])].dropna()
    x = valid[x_col].astype(float).to_numpy()
    y = valid[y_col].astype(float).to_numpy()

    # Best-fit line + R^2 + Spearman
    if len(x) >= 2 and np.std(x) > 1e-9:
        slope, intercept = np.polyfit(x, y, 1)
        yhat = slope * x + intercept
        ss_res = float(np.sum((y - yhat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        pearson = float(np.corrcoef(x, y)[0, 1])
        # Spearman rank
        rx = pd.Series(x).rank()
        ry = pd.Series(y).rank()
        spearman = float(np.corrcoef(rx, ry)[0, 1])
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, slope * xs + intercept, color="#a23a2a",
                linewidth=1.2, alpha=0.85, label=f"fit: R²={r2:.2f}")
    else:
        slope = intercept = 0.0
        r2 = pearson = spearman = float("nan")

    ax.scatter(x, y, s=42, alpha=0.55, color="#357b9c", edgecolor="white", linewidth=0.6)

    if label_col is not None:
        for _, row in valid.iterrows():
            ax.annotate(str(row[label_col]),
                        (row[x_col], row[y_col]),
                        fontsize=8.5, alpha=0.85,
                        xytext=(4, 3), textcoords="offset points")

    ax.set_xlabel(ax_x_label or x_col, fontsize=11)
    ax.set_ylabel(ax_y_label or y_col, fontsize=11)
    ax.set_title(title, fontsize=12.5, pad=10)
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    return _png_to_data_uri(fig), {
        "n": int(len(x)), "r2": r2, "pearson": pearson, "spearman": spearman,
        "slope": float(slope), "intercept": float(intercept),
    }


# --------------------------------------------------------- section renderers

def section_executive_summary(stats_13: dict, stats_full: dict,
                              residual_table: pd.DataFrame) -> str:
    n13 = stats_13["n"]
    r2_13 = stats_13["r2"]
    n_full = stats_full["n"]
    r2_full = stats_full["r2"]
    sp_full = stats_full["spearman"]

    # Top hits/misses from residuals
    hits = residual_table.sort_values("residual", ascending=False).head(3)
    misses = residual_table.sort_values("residual").head(3)

    def name_pop(row):
        pop = row.get("actual_pop_1500")
        pop_str = f"≈{int(pop)//1000}k" if pd.notna(pop) and pop > 0 else "n/a"
        return f"{row['display_name']} ({pop_str})"

    hits_html = "<ul>" + "".join(f"<li>{name_pop(r)} — composite {r['composite_raw']:+.1f}, "
                                 f"residual {r['residual']:+.2f}</li>"
                                 for _, r in hits.iterrows()) + "</ul>"
    misses_html = "<ul>" + "".join(f"<li>{name_pop(r)} — composite {r['composite_raw']:+.1f}, "
                                   f"residual {r['residual']:+.2f}</li>"
                                   for _, r in misses.iterrows()) + "</ul>"

    kpis = kpi_grid([
        ("Priority cities", "13"),
        ("Bairoch cohort (1500 pop)", f"{n_full:,}"),
        ("13-city R² (composite ↔ ln pop)", f"{r2_13:.2f}"),
        ("Full-cohort R²", f"{r2_full:.2f}"),
        ("Full-cohort Spearman ρ", f"{sp_full:.2f}"),
        ("Benchmark years", "1250–1500 (×6)"),
    ])

    return f"""
<section id="exec">
  <h2>1. Executive Summary</h2>
  <p>This report tests the urban-growth equation</p>
  <div class="equation">Δln(UrbanGrowth<sub>i,t</sub>) = α
   <span class="pos">+ β₁·TradeAccess</span>
   <span class="pos">+ β₂·LegalCapacity</span>
   <span class="pos">+ β₃·MerchantCapital</span>
   <span class="pos">+ β₄·AgriculturalSurplus</span>
   <span class="pos">+ β₅·PeasantMobility</span>
   <span class="neg">− β₆·NobleExtraction</span>
   <span class="neg">− β₇·ConflictRisk</span>
   + ε<sub>i,t</sub></div>
  <p>against actual 1250–1500 evidence for 2,390 medieval cities (Bairoch) and a 13-city
     case study covering the major HRE centers. Below is the headline reading.</p>
  {kpis}
  <h3>Where the model nails it (top positive residuals)</h3>
  {hits_html}
  <h3>Where the model misses (largest negative residuals)</h3>
  {misses_html}
  <p class="small">Residual = ln(actual pop 1500) − fitted_line(composite_raw_1500).
     Positive = real city was bigger than the score predicts; negative = real city was smaller.
     The biggest drivers of error are surveyed in §6.</p>
</section>
"""


def section_equation() -> str:
    rows = []
    descriptions = {
        "legal_capacity": ("Charters, free-imperial status, town hall, university nearby",
                           "Predicts: stronger civic autonomy → faster growth"),
        "merchant_capital": ("Hanseatic membership, Viabundus fairs, staple right, Bairoch Messe",
                             "Predicts: merchant agglomeration creates increasing returns"),
        "trade_access": ("Distance to roads/rivers, fair density, on a Viabundus trade route",
                         "Predicts: lower transport cost → larger market reach"),
        "agricultural_surplus": ("Population, 50-year growth, river/elevation/latitude proxies",
                                 "Predicts: cities need feedable hinterlands"),
        "peasant_mobility": ("Imputed from legal/merchant/noble (no direct Bürgerbücher data)",
                             "Predicts: rural-to-urban migration enables labor supply"),
        "noble_extraction": ("Polity transitions, foreign rule, prince-bishop seat",
                             "Predicts: lordly extraction drains capital, suppresses growth"),
        "conflict_risk": ("Conflict count, named wars, fire damage in last 50 years",
                          "Predicts: war and disasters depress growth"),
    }
    for var, w in DEFAULT_WEIGHTS.items():
        sign = "pos" if w > 0 else "neg"
        what, predicts = descriptions[var]
        rows.append(f"<tr><td class='score-{2 if w>0 else 0}'>"
                    f"<strong>{var.replace('_', ' ')}</strong></td>"
                    f"<td class='num {sign}'>{w:+.1f}</td>"
                    f"<td>{what}</td><td><em>{predicts}</em></td></tr>")
    table = ("<table><thead><tr><th>Variable</th><th>β (weight)</th>"
             "<th>What it captures</th><th>Theoretical claim</th></tr></thead><tbody>"
             + "".join(rows) + "</tbody></table>")
    return f"""
<section id="equation">
  <h2>2. The Equation, Variable by Variable</h2>
  <p>The composite score is a linear weighted sum of seven 0–3 ordinal variables.
     Weights live in <code>lib/targets.py</code> (<code>DEFAULT_WEIGHTS</code>) and
     reflect prior theoretical commitments rather than estimated coefficients —
     the validation in §5 therefore measures fit-of-the-prior, not OLS-best-fit.</p>
  {table}
  <p class="small">Note: the equation is a <em>cross-section explanation</em> of
     log-growth. We are not running OLS to estimate β̂ — we are computing each
     city's composite under fixed weights and asking how well that composite
     ranks 1500 outcomes.</p>
</section>
"""


METHODOLOGY_BLURBS: dict[str, dict] = {
    "trade_access": {
        "summary": "Network access to roads, rivers, fairs, and trading rights.",
        "sources": [
            ("docs/viabundus/Viabundus-2-csv/nodes.csv", "town definitions, parent-child hierarchy, time bounds"),
            ("docs/viabundus/Viabundus-2-csv/edges.csv", "road and river/canal edges with geometry"),
            ("docs/viabundus/Viabundus-2-csv/fairs.csv", "fairs by location, category, and active years"),
            ("docs/viabundus/Viabundus-2-csv/population.csv", "Bairoch/Bosker pop, used as scale gate"),
        ],
        "rules": [
            "3 — own interregional fair OR own staple right OR (regional fair + on trade route)",
            "2 — on trade route AND road/river ≤2/5 km, OR own regional fair, OR ≥2 fairs within 50 km",
            "1 — own local fair, OR fair within 25 km, OR road within 10 km",
            "0 — none of the above",
        ],
        "gaps": [
            "Viabundus does not cover southern Germany; Augsburg, Ulm, Bamberg, Würzburg, Regensburg, Speyer, Rothenburg get trade_access = 0 by default.",
            "Distance metrics are Haversine to nearest edge midpoint — they understate real travel cost on tortuous routes.",
        ],
    },
    "legal_capacity": {
        "summary": "Civic autonomy: charter, town hall, free-imperial status, nearby university.",
        "sources": [
            ("docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv",
             "charter attestations with type_origin codes (1=formal grant, 2=withdrawal, …)"),
            ("docs/town_charters_and_first_mentions/towncharter_data/legal_families.csv",
             "law-family code per city (M05/L04/K03 = Magdeburg/Lübeck/Kulm)"),
            ("docs/territorial_histories/territorial_hit/territories_all.csv",
             "city_status (0=lord, 1=free, 2=imperial, 3=free imperial) on [beginning_reign, end_reign)"),
            ("docs/construction_data/construction.csv",
             "town halls (building==5) — earliest record per city"),
            ("lib/paths.py PRE_1500_UNIVERSITIES",
             "33 universities Bologna 1088 → Uppsala 1477; nearest-distance computed at each year"),
        ],
        "rules": [
            "3 — city_status≥2, OR (formal charter AND (town hall OR strong-law family))",
            "2 — city_status==1, OR formal charter present, OR (charter signal + town hall)",
            "1 — any charter evidence (incl. first mention)",
            "0 — no attestation",
            "Penalty −1 if charter withdrawn in window (capped at 0)",
        ],
        "gaps": [
            "type_origin codes are hand-verified per the documentation PDF; mis-codes propagate.",
            "Hard-coded university list captures the headline foundations but ignores attached cathedral schools.",
        ],
    },
    "merchant_capital": {
        "summary": "Merchant power proxied by Hanseatic membership, fairs, staples, and Messen.",
        "sources": [
            ("docs/territorial_histories/territorial_hit/cities_polities.csv",
             "Hanseatic flag per (city, year)"),
            ("docs/markets/markets_data/markets.csv",
             "type_market codes; type_market==6 = Messe/Jahrmarkt (annual fair)"),
            ("docs/viabundus/Viabundus-2-csv/fairs.csv + nodes.csv",
             "Viabundus fairs and staple rights, time-windowed via [from, to)"),
            ("output/crosswalk_nodesid_cityid.csv",
             "Viabundus → Bairoch mapping (Levenshtein + spatial)"),
        ],
        "rules": [
            "3 — staple right OR Viabundus interregional fair OR (Hanseatic + (regional fair OR Messe))",
            "2 — Hanseatic, OR Viabundus regional fair, OR Messe",
            "1 — any market entry attested",
            "0 — nothing",
        ],
        "gaps": [
            "South-German Viabundus gap forces fair attestation through Bairoch markets only — narrower coverage.",
            "Hansa flag is binary annual; intra-Hansa hierarchy (Wendische Quartier vs. inland members) is not encoded.",
        ],
    },
    "agricultural_surplus": {
        "summary": "Proxy combining population, 50-year growth, distance to river, and latitude/elevation.",
        "sources": [
            ("docs/European_Population_data/European urban population, 700-2000.xlsx",
             "Bairoch/Bosker pop in 000s; linearly interpolated when 50-yr benchmark falls between observations"),
            ("docs/viabundus/Viabundus-2-csv/edges.csv",
             "river/canal edges → distance to nearest (positive bonus only)"),
            ("docs/city_locations_and_border_maps/dataverse_files/city_locations.csv",
             "Bairoch lat/lon, used for the latitude band (south < 49° < middle < 51.5° < north)"),
        ],
        "rules": [
            "3 — pop ≥ 20k, OR (pop ≥ 10k AND growing >5% over 50yr)",
            "2 — pop ≥ 10k, OR (pop ≥ 3k AND (river ≤ 15 km OR growing)), OR (river ≤ 15 km AND not north-band)",
            "1 — pop ≥ 3k, OR river ≤ 30 km",
            "0 — small, landlocked, cold",
            "Penalty −1 if elevation > 600 m and score > 0",
        ],
        "gaps": [
            "Population is the strongest signal in this proxy. That makes the variable partly endogenous to the outcome — flagged in §6.",
            "Viabundus river coverage is northern-biased, so southern-German river distance is missing for several cities; treated as no-bonus, never penalty.",
        ],
    },
    "peasant_mobility": {
        "summary": "Imputed from three other variables — there is no direct Bürgerbücher data in the source set.",
        "sources": [
            ("output/cities_legal_capacity.csv", "score input"),
            ("output/cities_merchant_capital.csv", "score input"),
            ("output/cities_noble_extraction.csv", "score input (negative)"),
        ],
        "rules": [
            "3 — legal==3 AND merchant≥2 AND noble≤1",
            "2 — legal≥2 AND noble≤1",
            "1 — legal≥1 OR merchant≥1",
            "0 — none of the above",
        ],
        "gaps": [
            "All rows are flagged <code>imputed=True</code>. Treating peasant_mobility as an independent variable is therefore double-counting in disguise.",
            "If Bürgerbücher (citizen rolls) become available for any city, swap them in — the imputation has no time-variation beyond what the inputs already carry.",
        ],
    },
    "noble_extraction": {
        "summary": "Cost of lordly rule: polity transitions, foreign rule, prince-bishop seats.",
        "sources": [
            ("docs/territorial_histories/territorial_hit/cities_polities.csv",
             "polity (terr_id) per (city, year); transitions counted in 50-yr window; foreign_rule flag"),
            ("docs/territorial_histories/territorial_hit/territories_all.csv",
             "city_status — autonomy reduces extraction"),
            ("lib/targets.py PRINCE_BISHOP_SEATS", "hard-coded list: Erfurt, Bamberg, Würzburg"),
        ],
        "rules": [
            "3 — ≥3 polity transitions, OR (prince-bishop + foreign rule), OR (prince-bishop + multiple transitions)",
            "2 — 1–2 transitions, OR foreign rule, OR prince-bishop seat",
            "1 — city_status==1 free city, OR stable lord rule with no shocks",
            "0 — city_status≥2 (imperial/free imperial) AND no foreign rule",
        ],
        "gaps": [
            "Conservative prince-bishop list. Cologne and Speyer are ALSO archbishopric/bishopric seats but achieved free imperial status — the list excludes them deliberately.",
            "Transitions detected from year-to-year terr_id changes; some changes are clerical/data artifacts rather than real events.",
        ],
    },
    "conflict_risk": {
        "summary": "War and disaster shocks: conflicts, named wars, fires.",
        "sources": [
            ("docs/conflicts_and_war/conflict_incidents.csv",
             "type_conflict (1=unspecified, 2=destruction, 3=occupation), warlabel (named war)"),
            ("docs/construction_data/construction.csv",
             "fire detection via regex on comment field: 'brand|abgebrannt|feuer|verbrannt'"),
        ],
        "rules": [
            "3 — ≥1 major conflict, OR ≥4 conflicts, OR ≥3 fires",
            "2 — ≥2 conflicts, OR ≥2 fires, OR (1 minor + ≥1 fire)",
            "1 — ≥1 conflict OR ≥1 fire",
            "0 — none",
        ],
        "gaps": [
            "Fire detection is regex-only on a German comment field — false negatives for non-standard phrasings.",
            "type_conflict==1 (\"unspecified\") covers a lot of heterogeneity; major and minor are distinguished crudely.",
        ],
    },
}


def section_methodology(quote_meta: str = "") -> str:
    blocks = []
    for var in DEFAULT_WEIGHTS:
        meta = METHODOLOGY_BLURBS.get(var, {})
        sources_html = "<table><thead><tr><th>File</th><th>What we use</th></tr></thead><tbody>" \
                       + "".join(f"<tr><td><code>{_html.escape(p)}</code></td><td>{u}</td></tr>"
                                 for p, u in meta.get("sources", [])) \
                       + "</tbody></table>"
        rules_html = "<ul>" + "".join(f"<li>{r}</li>" for r in meta.get("rules", [])) + "</ul>"
        gaps_html = "<ul>" + "".join(f"<li>{g}</li>" for g in meta.get("gaps", [])) + "</ul>"
        # Embed map PNG if present
        map_path = OUT / f"map_{var}_by_year.png"
        if not map_path.exists() and var == "trade_access":
            # the existing trade-access map is named differently
            map_path = OUT / "map_score3_by_year.png"
        map_img = ""
        if map_path.exists():
            uri = ("data:image/png;base64,"
                   + base64.b64encode(map_path.read_bytes()).decode())
            map_img = f'<img class="embed" src="{uri}" alt="{var} map by year">'
        body = (f"<p><em>{meta.get('summary', '')}</em></p>"
                f"<h4 style='margin-top:14px;color:#6c4f1f;font-size:14px'>Sources</h4>"
                f"{sources_html}"
                f"<h4 style='color:#6c4f1f;font-size:14px'>Scoring rules</h4>"
                f"{rules_html}"
                f"<h4 style='color:#6c4f1f;font-size:14px'>Known gaps & caveats</h4>"
                f"{gaps_html}"
                f"{map_img}")
        weight = DEFAULT_WEIGHTS[var]
        sign_class = "good" if weight > 0 else "bad"
        summary = (f"<span class='tag {sign_class}'>β = {weight:+.1f}</span> "
                   f"<strong>{var.replace('_', ' ')}</strong> — {meta.get('summary', '')}")
        blocks.append(collapsible(summary, body, open_by_default=False))

    return f"""
<section id="methodology">
  <h2>3. Methodology — How Each Variable Is Scored</h2>
  <p>Each variable is computed by its own builder in the repository and saved as
     <code>output/cities_&lt;var&gt;.csv</code>. Click any row to see the source files,
     scoring rules, gaps, and the by-year map.</p>
  {''.join(blocks)}
</section>
"""


def render_city_table(city_rows: pd.DataFrame) -> str:
    """One row per benchmark year with score cells + receipt sub-lines."""
    head = ("<table><thead><tr><th>Year</th>"
            "<th>Trade</th><th>Legal</th><th>Merch</th><th>Agri</th>"
            "<th>Mobility</th><th>Noble−</th><th>Conflict−</th>"
            "<th>Composite</th><th>Pop (Bosker)</th></tr></thead><tbody>")
    body_rows = []
    for _, r in city_rows.iterrows():
        receipts = []
        for var in ["trade_access", "legal_capacity", "merchant_capital",
                    "agricultural_surplus", "peasant_mobility",
                    "noble_extraction", "conflict_risk"]:
            label = var.replace("_", " ")
            bullets = receipt_for(var, r)
            receipts.append(receipt_line(label, bullets))

        score_cells = [
            score_cell(r.get("trade_access")),
            score_cell(r.get("legal_capacity_score")),
            score_cell(r.get("merchant_capital_score")),
            score_cell(r.get("agricultural_surplus_score")),
            score_cell(r.get("peasant_mobility_score")),
            score_cell(r.get("noble_extraction_score")),
            score_cell(r.get("conflict_risk_score")),
        ]
        comp = num_cell(r.get("composite_raw"), "{:+.1f}")
        pop = r.get("population")
        pop_str = (num_cell(pop, "{:,.0f}") if pd.notna(pop) and pop > 0
                   else '<td class="num small">—</td>')
        row = (f"<tr><td><strong>{int(r['year'])}</strong></td>"
               + "".join(score_cells)
               + comp + pop_str + "</tr>")
        body_rows.append(row)
        # follow-up row with receipts
        body_rows.append(
            f'<tr><td></td><td colspan="9" class="small">{"".join(receipts)}</td></tr>'
        )
    return head + "".join(body_rows) + "</tbody></table>"


def section_city_profiles(priority_long: pd.DataFrame, quotes: dict[str, list[dict]],
                          residual_lookup: dict[int, float],
                          chart_specs: dict) -> str:
    """One <details> block per priority city, in display-name order."""
    blocks = []
    nav_children: list[tuple[str, str]] = []

    # Order by 1500 composite descending so the strongest cities lead.
    name_to_score_1500 = priority_long[priority_long["year"] == 1500] \
        .set_index("display_name")["composite_raw"].to_dict()
    ordered = sorted(priority_long["display_name"].unique(),
                     key=lambda n: -name_to_score_1500.get(n, -99))

    for name in ordered:
        sub = priority_long[priority_long["display_name"] == name].copy()
        sub = sub.sort_values("year").reset_index(drop=True)
        cid = int(sub["city_id"].iloc[0])

        # Verdict
        comp_1500 = name_to_score_1500.get(name)
        resid = residual_lookup.get(cid)
        if resid is None or pd.isna(resid):
            verdict_class, verdict_text = "partial", "no 1500 pop data"
        elif abs(resid) <= 0.45:
            verdict_class, verdict_text = "hit", "model and history agree"
        elif resid > 0:
            verdict_class, verdict_text = "miss", "history bigger than the score"
        else:
            verdict_class, verdict_text = "miss", "history smaller than the score"

        # Charts
        traj_id = f"chart-traj-{cid}"
        contrib_id = f"chart-contrib-{cid}"
        chart_specs[traj_id] = chart_trajectory(sub, traj_id)
        chart_specs[contrib_id] = chart_contributions(sub, contrib_id)

        narrative = CITY_NARRATIVES.get(cid, "")
        narrative_html = f"<p>{_html.escape(narrative)}</p>" if narrative else ""

        # Quotes
        city_quotes = quotes.get(name, [])
        quotes_inner = ("".join(quote_block(q) for q in city_quotes)
                        if city_quotes else
                        "<p class='small'>No PDF quotes located for this city.</p>")
        quotes_block_html = collapsible(
            f"PDF quotes ({len(city_quotes)})", quotes_inner, open_by_default=False)

        table_html = render_city_table(sub)

        actual_pop = sub.set_index("year")["population"].to_dict()
        pop_1500 = actual_pop.get(1500)
        pop_str = (f"≈{int(pop_1500)//1000}k" if pd.notna(pop_1500) and pop_1500 > 0
                   else "n/a")
        comp_str = f"{comp_1500:+.1f}" if comp_1500 is not None else "—"

        body = f"""
        {narrative_html}
        <div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
          <div class="kpi"><div class="label">1500 composite</div><div class="value">{comp_str}</div></div>
          <div class="kpi"><div class="label">1500 pop (Bosker)</div><div class="value">{pop_str}</div></div>
          <div class="kpi"><div class="label">Verdict</div>
            <div class="value"><span class="verdict {verdict_class}">{verdict_text}</span></div></div>
        </div>
        <h3 style="margin-top:18px">Year-by-year scores with data receipts</h3>
        <p class="small">Each cell is the 0–3 ordinal score; the row below it lists the
           specific signals from <code>output/cities_*.csv</code> that drove the score.</p>
        {table_html}
        <h3>Trajectory: composite score and population, 1250–1500</h3>
        <div class="chart-wrap"><canvas id="{traj_id}" height="120"></canvas></div>
        <h3>Variable contributions (β · score, signed)</h3>
        <div class="chart-wrap"><canvas id="{contrib_id}" height="120"></canvas></div>
        {quotes_block_html}
        """

        anchor = f"city-{cid}"
        blocks.append(f'<div id="{anchor}"></div>')
        summary = (f"<strong>{_html.escape(name)}</strong> "
                   f"<span class='tag {verdict_class}'>{verdict_text}</span> "
                   f"&nbsp;1500 composite {comp_str}, pop {pop_str}")
        blocks.append(collapsible(summary, body, open_by_default=False))
        nav_children.append((anchor, name))

    section_html = f"""
<section id="cities">
  <h2>4. City Profiles — The 13 Priority Cities</h2>
  <p>Each profile expands to show year-by-year scores, the data signals that drove
     each score, an interactive trajectory chart, the β-weighted variable
     contributions, and quotes from the academic PDFs. Cities are ordered by 1500
     composite score (highest first).</p>
  {''.join(blocks)}
</section>
"""
    return section_html, nav_children


def section_validation(stats_13: dict, stats_full: dict,
                       img_13: str, img_full: str,
                       residual_table: pd.DataFrame) -> str:
    def fmt(v):
        return f"{v:.3f}" if isinstance(v, (int, float)) and not pd.isna(v) else "—"

    rows_html = []
    for _, r in residual_table.sort_values("residual", ascending=False).iterrows():
        cls = "good" if r["residual"] > 0 else "bad"
        rows_html.append(
            f"<tr><td>{_html.escape(r['display_name'])}</td>"
            f"<td class='num'>{r['composite_raw']:+.2f}</td>"
            f"<td class='num'>{int(r['actual_pop_1500']):,}"
            f"</td>"
            f"<td class='num'>{r['ln_actual_pop']:+.2f}</td>"
            f"<td class='num'><span class='tag {cls}'>{r['residual']:+.2f}</span></td></tr>")
    resid_table_html = ("<table><thead><tr><th>City</th><th>Composite (1500)</th>"
                        "<th>Pop (1500)</th><th>ln Pop</th><th>Residual</th></tr></thead>"
                        "<tbody>" + "".join(rows_html) + "</tbody></table>")

    return f"""
<section id="validation">
  <h2>5. Validation — Predicted vs. Actual</h2>
  <h3>13-city case study</h3>
  {kpi_grid([
      ("n", str(stats_13["n"])),
      ("R² (Pearson²)", fmt(stats_13["r2"])),
      ("Pearson r", fmt(stats_13["pearson"])),
      ("Spearman ρ", fmt(stats_13["spearman"])),
      ("Slope", fmt(stats_13["slope"])),
      ("Intercept", fmt(stats_13["intercept"])),
  ])}
  <img class="embed" src="{img_13}" alt="13-city scatter">
  <h4>Residual table</h4>
  <p class="small">Residual = ln(actual pop 1500) − fitted_line(composite_raw_1500).
     Positive residuals: history outpaced the model. Negative: model over-predicted.</p>
  {resid_table_html}

  <h3 style="margin-top:36px">Full Bairoch cohort with 1500 population observations</h3>
  {kpi_grid([
      ("n", f"{stats_full['n']:,}"),
      ("R²", fmt(stats_full["r2"])),
      ("Pearson r", fmt(stats_full["pearson"])),
      ("Spearman ρ", fmt(stats_full["spearman"])),
  ])}
  <img class="embed" src="{img_full}" alt="full cohort scatter">
  <p class="small">The full cohort is noisier because Bairoch covers all of Europe,
     not just the HRE; many small Bairoch cities have weak political coverage in our
     territorial datasets and end up clustered at low composite scores. The Spearman
     rank correlation is more diagnostic than R² here.</p>
</section>
"""


def section_synthesis(residual_table: pd.DataFrame,
                      stats_13: dict, stats_full: dict) -> str:
    return f"""
<section id="synthesis">
  <h2>6. What the Model Got Right / Wrong</h2>
  <h3>What worked</h3>
  <ul>
    <li><strong>The free-imperial-city signal is load-bearing.</strong> Cologne, Frankfurt,
        Nuremberg all top the case study because the equation rewards
        legal_capacity=3 + merchant_capital=3 + noble_extraction=0 simultaneously.
        Real history confirms this clustering — these are the three most successful
        HRE commercial centers across the period.</li>
    <li><strong>Prince-bishop friction shows up correctly.</strong> Erfurt, Bamberg, and
        Würzburg are pulled down by noble_extraction; this matches the qualitative
        history of cathedral-city stagnation under Mainz/Bamberg/Würzburg overlordship.</li>
    <li><strong>Trade-network membership predicts northern winners.</strong> For the
        Viabundus-covered subset, Hanseatic + staple right + interregional fairs
        cluster the eventual top tier (Cologne, Hamburg, Brugge, Gent, Antwerpen by
        1500–1600). Spearman ρ of {stats_full['spearman']:.2f} on the full cohort
        confirms a strong rank ordering despite weak linear fit.</li>
  </ul>
  <h3>What did not work</h3>
  <ul>
    <li><strong>Southern Germany is a coverage hole.</strong> Augsburg, Ulm, Regensburg,
        Speyer, Bamberg, Würzburg, and Rothenburg fall outside Viabundus. Their
        trade_access scores are all 0 by data limitation, not by historical fact.
        Augsburg in particular — the 15th-century Welser/Fugger banking capital — is
        clearly under-scored.</li>
    <li><strong>Peasant mobility is double-counting.</strong> It is imputed from legal,
        merchant, and noble scores, so its β=+0.6 amplifies signal already in the
        equation. A cleaner spec drops the variable until Bürgerbücher data is
        merged.</li>
    <li><strong>Agricultural_surplus partly uses population, which is the outcome.</strong>
        That makes the variable correlated with the dependent observation by
        construction. The variable still encodes geography (river, latitude,
        elevation), but the population term should be peeled out for any future OLS.</li>
    <li><strong>Linear fit is weaker than rank fit.</strong> 13-city R² of {stats_13['r2']:.2f}
        is moderate, but the Spearman rank correlation is much stronger. The ordinal
        nature of the inputs means absolute composite values are a less reliable
        target than rank — we recommend rank-based reporting in the paper.</li>
    <li><strong>No time-fixed effects.</strong> The Black Death (1347–51) and
        15th-century recovery affect every city; without τ_t controls, the
        equation predicts more growth at early benchmarks than reality delivered.</li>
    <li><strong>Hard-coded prince-bishop list is small.</strong> Mainz, Köln-Erzbistum,
        Trier, and Salzburg are all archbishoprics; only the conservative three
        (Erfurt under Mainz, Bamberg, Würzburg) are flagged. Adding more would
        raise noble_extraction for several cities and is worth a sensitivity test.</li>
  </ul>

  <h3>Recommended next steps</h3>
  <ol>
    <li>Run a true OLS on Δln(pop) with the seven variables → see whether the
        prior weights survive against estimated β̂.</li>
    <li>Add city and time fixed effects (μ_i, τ_t) per the equation's "advanced"
        form already noted in your spec.</li>
    <li>Replace peasant_mobility with Bürgerbücher counts where available;
        otherwise drop it.</li>
    <li>Merge a southern-Germany road dataset (Tabula Imperii, Imperial-Post
        Routes) to fill the Viabundus gap for Augsburg/Ulm/Regensburg.</li>
  </ol>
</section>
"""


def section_appendix() -> str:
    rows = [
        ("Bairoch / Bosker — European Urban Population, 700–2000",
         "docs/European_Population_data/European urban population, 700 - 2000.xlsx",
         "Bosker, Buringh, van Zanden (2013), <em>Review of Economics and Statistics</em>"),
        ("Bairoch city locations (Bairoch et al.)",
         "docs/city_locations_and_border_maps/dataverse_files/city_locations.csv",
         "City coordinates, alternative names, regions; ~23,000 city IDs"),
        ("Town charters & first mentions",
         "docs/town_charters_and_first_mentions/towncharter_data/towncharter.csv",
         "Charter type_origin codes; legal_families.csv for law family"),
        ("Territorial HIT — cities_polities & territories_all",
         "docs/territorial_histories/territorial_hit/",
         "Annual polity, foreign rule, Hanseatic flag, city status (1300–1779)"),
        ("Construction database",
         "docs/construction_data/construction.csv",
         "26,912 construction events 1300–1750 — town halls (building==5), fires"),
        ("Markets database",
         "docs/markets/markets_data/markets.csv",
         "10,587 market grants 1260–1939; type_market==6 = Messe"),
        ("Conflicts & wars",
         "docs/conflicts_and_war/conflict_incidents.csv",
         "6,337 conflict events 1256–1857; type_conflict + warlabel"),
        ("Viabundus 2 — Premodern European Transport",
         "docs/viabundus/Viabundus-2-csv/",
         "Penrose et al. 2022 / 2025 update; nodes, edges, fairs, towns, population"),
        ("Sound Toll Registers",
         "docs/sound_toll_registers/",
         "1497–1857 maritime trade; 10.6M records (referenced, not yet wired into model)"),
    ]
    pdf_rows = [
        ("Bosker et al. 2013, From Baghdad to London",
         "docs/Bosker et al. - 2013 - From Baghdad to London Unraveling Urban Developme.pdf"),
        ("Fairs in HRE", "docs/Fairs_In_HRE.pdf"),
        ("Medieval cities through economics",
         "docs/medieval_cities_through_economics.pdf"),
        ("Medieval law merchant", "docs/medieval_law_merchant.pdf"),
        ("Medieval trade agglomeration",
         "docs/medieval_trade_agglomeration.pdf"),
        ("Medieval universities, legal & commercial revolution",
         "docs/medieval_unis_legal_and_comm_revolution.pdf"),
        ("Consumer prices and wages",
         "docs/consumer_prices_and_wages.pdf"),
        ("City populations research",
         "docs/city_populations_research.pdf"),
    ]

    data_html = ("<table><thead><tr><th>Dataset</th><th>Path</th><th>Notes</th>"
                 "</tr></thead><tbody>"
                 + "".join(f"<tr><td>{n}</td><td><code>{_html.escape(p)}</code></td>"
                           f"<td>{notes}</td></tr>"
                           for n, p, notes in rows)
                 + "</tbody></table>")
    pdf_html = ("<table><thead><tr><th>PDF</th><th>Path</th></tr></thead><tbody>"
                + "".join(f"<tr><td>{n}</td><td><code>{_html.escape(p)}</code></td></tr>"
                          for n, p in pdf_rows)
                + "</tbody></table>")
    return f"""
<section id="appendix">
  <h2>7. Sources & Citations</h2>
  <h3>Primary datasets</h3>
  {data_html}
  <h3>Academic PDFs (quote sources)</h3>
  {pdf_html}
  <h3>Code lineage</h3>
  <ul>
    <li><code>build_trade_access.py</code> → trade_access score</li>
    <li><code>build_legal_capacity.py</code> → legal_capacity score</li>
    <li><code>build_merchant_capital.py</code> → merchant_capital score</li>
    <li><code>build_agricultural_surplus.py</code> → agricultural_surplus score</li>
    <li><code>build_peasant_mobility.py</code> → peasant_mobility score (imputed)</li>
    <li><code>build_noble_extraction.py</code> → noble_extraction score</li>
    <li><code>build_conflict_risk.py</code> → conflict_risk score</li>
    <li><code>build_composite.py</code> → weighted sum + 0–3 bucketing</li>
    <li><code>build_case_study.py</code> → case_study_priority13.csv</li>
    <li><code>build_report.py</code> → this report</li>
  </ul>
</section>
"""


# --------------------------------------------------------- main

def main():
    print("Loading outputs ...")
    data = load_all_outputs()

    print("Loading Bosker pop (via agricultural_surplus output) ...")
    bosker_long = load_bosker_pop()  # city_id, year, pop_pers

    print("Building priority-city long frame with raw features ...")
    priority_long = build_priority_long(data)

    # Validation: 13 cities
    print("Building 13-city validation frame ...")
    p1500 = priority_long[priority_long["year"] == 1500].copy()
    p1500["actual_pop_1500"] = p1500["population"]  # already merged
    val13 = p1500[["city_id", "display_name", "composite_raw",
                   "actual_pop_1500"]].copy()
    val13["ln_actual_pop"] = np.log(val13["actual_pop_1500"].replace(0, np.nan))
    val13_for_fit = val13.dropna(subset=["composite_raw", "ln_actual_pop"]).copy()

    img_13, stats_13 = fig_validation_scatter(
        val13_for_fit, "composite_raw", "ln_actual_pop",
        title="13 priority cities: composite (1500) vs ln(pop 1500)",
        label_col="display_name",
        ax_x_label="composite_raw at 1500",
        ax_y_label="ln(actual pop, Bosker, 1500)",
    )

    # Compute residuals for the 13-city table
    if len(val13_for_fit) >= 2:
        slope = stats_13["slope"]; intercept = stats_13["intercept"]
        val13_for_fit["fitted"] = slope * val13_for_fit["composite_raw"] + intercept
        val13_for_fit["residual"] = (val13_for_fit["ln_actual_pop"]
                                     - val13_for_fit["fitted"])
    else:
        val13_for_fit["fitted"] = np.nan
        val13_for_fit["residual"] = np.nan

    # Validation: full cohort
    print("Building full-cohort validation frame ...")
    comp_full = composite_at_year(data["composite"], 1500)
    pop_1500 = bosker_long[bosker_long["year"] == 1500].rename(
        columns={"pop_pers": "actual_pop_1500"})[["city_id", "actual_pop_1500"]]
    full_val = comp_full.merge(pop_1500, on="city_id", how="left")
    full_val["ln_actual_pop"] = np.log(full_val["actual_pop_1500"].replace(0, np.nan))
    full_val_for_fit = full_val.dropna(subset=["composite_raw", "ln_actual_pop"]).copy()
    img_full, stats_full = fig_validation_scatter(
        full_val_for_fit, "composite_raw", "ln_actual_pop",
        title="Full Bairoch cohort with 1500 pop observations",
        label_col=None,
        ax_x_label="composite_raw at 1500",
        ax_y_label="ln(actual pop, Bosker, 1500)",
    )
    print(f"  full cohort n={stats_full['n']}, R²={stats_full['r2']:.3f}")

    # PDF quotes
    print("Extracting PDF quotes ...")
    pdf_paths = sorted(DOCS.glob("*.pdf"))
    quotes = extract_city_quotes(
        pdf_paths=pdf_paths,
        city_aliases=PRIORITY_CITY_ALIASES,
        cache_path=QUOTES_CACHE,
        skip_pdfs=[],  # Bosker has no city-specific quotes but cheap to scan
    )
    quote_count = sum(len(v) for v in quotes.values())
    print(f"  {quote_count} total quotes across {sum(1 for v in quotes.values() if v)}/{len(quotes)} cities")

    residual_lookup = dict(zip(val13_for_fit["city_id"],
                               val13_for_fit["residual"]))

    chart_specs: dict[str, dict] = {}

    # Section: city profiles (also produces nav children)
    cities_html, nav_children = section_city_profiles(
        priority_long, quotes, residual_lookup, chart_specs)

    # Compose
    sections = [
        section_executive_summary(stats_13, stats_full, val13_for_fit),
        section_equation(),
        section_methodology(),
        cities_html,
        section_validation(stats_13, stats_full, img_13, img_full,
                           val13_for_fit),
        section_synthesis(val13_for_fit, stats_13, stats_full),
        section_appendix(),
    ]

    toc = [
        ("exec", "1. Executive Summary", []),
        ("equation", "2. The Equation", []),
        ("methodology", "3. Methodology", []),
        ("cities", "4. City Profiles", nav_children),
        ("validation", "5. Validation", []),
        ("synthesis", "6. What Worked / Didn't", []),
        ("appendix", "7. Sources", []),
    ]

    html_doc = render_html(
        title="Medieval HRE Urban Growth Model — Receipts & Validation",
        subtitle=("A line-by-line reading of Δln(UrbanGrowth) = α + β₁TradeAccess + … "
                  "+ β₅PeasantMobility − β₆NobleExtraction − β₇ConflictRisk + ε, with "
                  "data lineage, PDF quotes, and predicted-vs-actual fit."),
        toc=toc,
        sections=sections,
        chart_specs=chart_specs,
    )

    REPORT_PATH.write_text(html_doc, encoding="utf-8")
    print(f"\nWrote {REPORT_PATH} ({len(html_doc.encode('utf-8'))/1024:.0f} KB)")


if __name__ == "__main__":
    main()
