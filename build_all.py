"""Run the full HRE city-variable pipeline end-to-end.

Order:
  1. build_crosswalk.py       (Viabundus nodesid <-> Bairoch city_id)
  2. build_legal_capacity.py
  3. build_merchant_capital.py
  4. build_agricultural_surplus.py
  5. build_noble_extraction.py
  6. build_conflict_risk.py
  7. build_peasant_mobility.py     (depends on legal/merchant/noble)
  8. build_composite.py            (joins all + TradeAccess via crosswalk)
  9. build_case_study.py           (priority-13 narrative CSV)
 10. map_variable.py for each variable + composite

Each step shells out so failures abort the pipeline.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

STEPS = [
    ["python3", "build_crosswalk.py"],
    ["python3", "build_legal_capacity.py"],
    ["python3", "build_merchant_capital.py"],
    ["python3", "build_agricultural_surplus.py"],
    ["python3", "build_noble_extraction.py"],
    ["python3", "build_conflict_risk.py"],
    ["python3", "build_peasant_mobility.py"],
    ["python3", "build_trade_access.py"],
    ["python3", "build_composite.py"],
    ["python3", "build_predictive_model.py"],
    ["python3", "build_case_study.py"],
]

MAPS = [
    "legal_capacity",
    "merchant_capital",
    "agricultural_surplus",
    "peasant_mobility",
    "noble_extraction",
    "conflict_risk",
    "composite",
]


def run(cmd):
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"\nABORT: {' '.join(cmd)} returned {r.returncode}", file=sys.stderr)
        sys.exit(r.returncode)


def main():
    for step in STEPS:
        run(step)
    for v in MAPS:
        run(["python3", "map_variable.py", v])
    print("\n=== DONE ===")
    print("Outputs in /Users/nikunjtyagi/HistoryResearch/output/")


if __name__ == "__main__":
    main()
