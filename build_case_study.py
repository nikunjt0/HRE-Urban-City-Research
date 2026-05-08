"""Filter all variables to the 13 priority case-study cities.

Output:
  output/case_study_priority13.csv   13 cities x 6 years = 78 rows

Adds:
  - notes column synthesizing key signals into prose
  - PASS/FAIL block validating the 1500 score against known historical facts
"""
from __future__ import annotations

import pandas as pd

from lib.paths import OUT
from lib.targets import PRIORITY_CITIES


def load_long(name: str, score_col: str = None, extras: list[str] = None) -> pd.DataFrame:
    if score_col is None:
        score_col = f"{name}_score"
    df = pd.read_csv(OUT / f"cities_{name}.csv")
    cols = ["city_id", "year", score_col] + (extras or [])
    cols = [c for c in cols if c in df.columns]
    return df[cols]


def main():
    priority_ids = [b for (_, b, _) in PRIORITY_CITIES]
    display = {b: name for (name, b, _) in PRIORITY_CITIES}

    base = pd.read_csv(OUT / "cities_legal_capacity.csv")[
        ["city_id", "name", "lat", "lon", "year"]]
    base = base[base["city_id"].isin(priority_ids)]

    legal = load_long("legal_capacity", extras=["has_formal_charter_by_y",
                                                "charter_withdrawn_by_y",
                                                "has_townhall_by_y",
                                                "legal_family", "city_status"])
    merchant = load_long("merchant_capital", extras=["is_hanseatic",
                                                     "best_fair_category",
                                                     "has_messe_by_y",
                                                     "has_staple"])
    agri = load_long("agricultural_surplus", extras=["population",
                                                     "pop_growth_50yr",
                                                     "dist_river_km"])
    mobility = load_long("peasant_mobility", extras=["imputed"])
    noble = load_long("noble_extraction", extras=["n_polity_changes_50yr",
                                                  "is_prince_bishop_seat"])
    conflict = load_long("conflict_risk", extras=["n_conflicts_50yr",
                                                  "n_major_conflicts_50yr"])
    composite = pd.read_csv(OUT / "cities_composite.csv")[
        ["city_id", "year", "composite_raw", "composite_0_3", "trade_access"]]

    df = base
    for p in [legal, merchant, agri, mobility, noble, conflict, composite]:
        df = df.merge(p, on=["city_id", "year"], how="left")

    df["display_name"] = df["city_id"].map(display)

    # Auto-generated notes per row
    def make_note(r):
        bits = []
        if r.get("city_status", 0) >= 3:
            bits.append("free imperial city")
        elif r.get("city_status", 0) == 2:
            bits.append("imperial city")
        if r.get("legal_family") in ("M05", "L04", "K03"):
            bits.append("Magdeburg/Lübeck/Kulm law")
        if r.get("is_hanseatic", 0) == 1:
            bits.append("Hanseatic")
        bf = r.get("best_fair_category", 0)
        if bf == 3:
            bits.append("interregional fair")
        elif bf == 2:
            bits.append("regional fair")
        if r.get("has_staple", 0) == 1:
            bits.append("staple right")
        elif r.get("has_messe_by_y", 0) == 1 and bf < 2:
            bits.append("annual fair (Messe)")
        if r.get("is_prince_bishop_seat", 0) == 1:
            bits.append("prince-bishop seat")
        if r.get("n_polity_changes_50yr", 0) >= 2:
            bits.append(f"{int(r['n_polity_changes_50yr'])} polity transitions in 50y")
        if r.get("n_major_conflicts_50yr", 0) >= 1:
            bits.append("major conflict in window")
        if pd.notna(r.get("population")) and r.get("population", 0) >= 20000:
            bits.append(f"pop ≈{int(r['population']) // 1000}k")
        return "; ".join(bits) if bits else "—"

    df["notes"] = df.apply(make_note, axis=1)

    # Re-order columns
    cols = [
        "display_name", "city_id", "year",
        "legal_capacity_score", "merchant_capital_score",
        "agricultural_surplus_score", "peasant_mobility_score",
        "noble_extraction_score", "conflict_risk_score", "trade_access",
        "composite_raw", "composite_0_3",
        "notes",
        # raw features for reference
        "has_formal_charter_by_y", "charter_withdrawn_by_y",
        "has_townhall_by_y", "legal_family", "city_status",
        "is_hanseatic", "best_fair_category", "has_messe_by_y", "has_staple",
        "population", "pop_growth_50yr", "dist_river_km",
        "n_polity_changes_50yr", "is_prince_bishop_seat",
        "n_conflicts_50yr", "n_major_conflicts_50yr",
        "imputed",
    ]
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values(["display_name", "year"]).reset_index(drop=True)

    out_path = OUT / "case_study_priority13.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df):,} rows = {df['city_id'].nunique()} cities x "
          f"{df['year'].nunique()} years)")

    # ---- validation: spot-check 1500 ---------------------------------------
    print("\n=== Validation against known 1500 facts ===")
    s = df[df["year"] == 1500].set_index("city_id")
    checks = [
        ("Cologne free imperial",  14060, ("noble_extraction_score", "<=", 1)),
        ("Cologne Hanseatic",       14060, ("merchant_capital_score", ">=", 3)),
        ("Frankfurt fair",          15027, ("merchant_capital_score", ">=", 3)),
        ("Würzburg bishop",         22145, ("noble_extraction_score", ">=", 2)),
        ("Magdeburg law",           11094, ("legal_capacity_score", "==", 3)),
        ("Nuremberg imperial",      22094, ("legal_capacity_score", "==", 3)),
        ("Nuremberg low extraction",22094, ("noble_extraction_score", "==", 0)),
        ("Augsburg merchant",       23006, ("merchant_capital_score", ">=", 1)),
        ("Leipzig fair attractor",  9070,  ("merchant_capital_score", ">=", 2)),
        ("Bamberg bishop",          22016, ("noble_extraction_score", ">=", 2)),
    ]
    passes = 0
    for name, cid, (col, op, val) in checks:
        v = s.loc[cid, col] if cid in s.index else None
        ok = False
        if v is not None:
            ok = (op == "==" and v == val) or (op == ">=" and v >= val) \
                 or (op == "<=" and v <= val)
        passes += int(ok)
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {name}: {col} {op} {val}   actual={v}")
    print(f"\n{passes}/{len(checks)} checks passed")

    # ---- summary -----------------------------------------------------------
    print("\n=== Composite ranking by year (top-13 priority cities) ===")
    pivot = df.pivot_table(index="display_name", columns="year",
                           values="composite_raw", aggfunc="first").round(2)
    print(pivot.to_string())


if __name__ == "__main__":
    main()
