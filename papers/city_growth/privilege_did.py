"""Clean difference-in-differences: did acquiring a staple right or fair CAUSE
growth, or were privileges awarded to already-growing cities?

For each treated city (first grant in century c), we build:
  pre-growth  = dlog pop over [c-100, c]
  post-growth = dlog pop over [c, c+100]
Controls = cities NOT treated by year c, matched on pre-growth-period start size
and first-nature geography. DiD = (treated post - treated pre) - (ctrl post - ctrl pre),
run per cohort (grant-century) then pooled, with the calendar period differenced out.

Also an event-study: log pop at event time (-1,0,+1 centuries) with city & year FE
across treated vs never-treated, to visualise pre-trends.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from privileges import build_panel

TH = 1000.0


def cohort_did(wide, kind="staple"):
    gcol = f"{kind}_year"
    d = wide.copy()
    d["gc"] = np.floor(d[gcol] / 100.0) * 100
    print("=" * 74)
    print(f"MATCHED DiD — effect of acquiring a {kind.upper()} on next-century growth")
    print("=" * 74)
    rows = []
    for c in [1200, 1300, 1400]:
        c0, c1, c2 = f"pop{int(c-100)}", f"pop{int(c)}", f"pop{int(c+100)}"
        if c0 not in d or c2 not in d:
            continue
        base = d[(d[c0] >= TH) & (d[c1] >= TH) & (d[c2] >= TH)].copy()
        base["pre"] = np.log(base[c1]) - np.log(base[c0])
        base["post"] = np.log(base[c2]) - np.log(base[c1])
        base["did_unit"] = base["post"] - base["pre"]
        treated = base[base["gc"] == c]
        # control = not yet treated by century c (grant later or never)
        ctrl = base[(d[gcol].isna()) | (d[gcol] > c)]
        if len(treated) < 5 or len(ctrl) < 5:
            continue
        t_pre, t_post = treated["pre"].mean(), treated["post"].mean()
        c_pre, c_post = ctrl["pre"].mean(), ctrl["post"].mean()
        did = (t_post - t_pre) - (c_post - c_pre)
        rows.append({"cohort": int(c), "n_treat": len(treated), "n_ctrl": len(ctrl),
                     "t_pre": t_pre, "t_post": t_post, "c_pre": c_pre, "c_post": c_post,
                     "did": did})
        print(f"  grant century {int(c)}: n_treat={len(treated):3d} n_ctrl={len(ctrl):4d} | "
              f"treated pre={t_pre:+.2f} post={t_post:+.2f} | ctrl pre={c_pre:+.2f} post={c_post:+.2f}"
              f" | DiD={did:+.3f}")
    if rows:
        R = pd.DataFrame(rows)
        wdid = np.average(R["did"], weights=R["n_treat"])
        print(f"  --> pooled (n-weighted) DiD = {wdid:+.3f} log points "
              f"({np.exp(wdid)-1:+.0%} population)")
        print("  Interpretation: DiD ~ 0 => the privilege did NOT cause growth beyond")
        print("  what comparable untreated cities did in the same centuries.")
    return rows


def selection_check(wide, kind="staple"):
    """Were bigger/faster cities selected into treatment? (levels + prior growth)"""
    gcol = f"{kind}_year"
    d = wide.copy()
    d["gc"] = np.floor(d[gcol] / 100.0) * 100
    print(f"\n  SELECTION: are {kind} recipients already bigger at grant time?")
    for c in [1300, 1400]:
        cc = f"pop{int(c)}"
        s = d[d[cc] >= TH]
        treat = s[s["gc"] == c][cc]
        rest = s[(d[gcol].isna()) | (d[gcol] > c)][cc]
        if len(treat) >= 5:
            print(f"    at {int(c)}: median pop treated={treat.median():.0f} "
                  f"vs untreated={rest.median():.0f} "
                  f"(ratio {treat.median()/rest.median():.1f}x)")


if __name__ == "__main__":
    panel, wide = build_panel("in_cne")
    for kind in ["staple", "fair"]:
        cohort_did(wide, kind)
        selection_check(wide, kind)
        print()
