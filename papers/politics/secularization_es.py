"""Secularization event study: church -> secular rule (type_change=8),
plus all church->noble transitions as a broader treatment.

Outcome: decadal construction (all / new / economic). Stacked ES as in
event_studies.py, reusing its machinery.
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

from event_studies import load, stacked_es

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

if __name__ == "__main__":
    d = load()
    ev = pd.read_csv(OUT / "regime_events.csv")
    sec = ev[ev.type_change == 8].copy()
    sec["dec"] = (sec.year // 10) * 10
    first_sec = sec.groupby("city_id")["dec"].min()
    ch2nb = ev[(ev.old_type == "church") & (ev.new_type == "noble")].copy()
    ch2nb["dec"] = (ch2nb.year // 10) * 10
    first_ch = ch2nb.groupby("city_id")["dec"].min()
    print("secularization cities:", len(first_sec),
          " church->noble cities:", len(first_ch))
    results = {}
    stacked_es(d, first_sec, "SECULARIZE", results, outcome="y")
    stacked_es(d, first_sec, "SECULARIZE", results, outcome="yecon")
    stacked_es(d, first_ch, "CHURCH2NOBLE", results, outcome="y")
    stacked_es(d, first_ch, "CHURCH2NOBLE", results, outcome="yecon")
    (OUT / "secularization_es.json").write_text(json.dumps(results, indent=2))
    print("\nwrote", OUT / "secularization_es.json")
