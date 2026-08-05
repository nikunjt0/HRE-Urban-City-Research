"""Classify every terr_id lineage into a ruler type from its name.

Types (ruler_type):
  church      - ecclesiastical lords (bishoprics, monasteries, military orders...)
  self        - the city ruling itself (Reichsstadt / freie Stadt lineages)
  kingdom     - foreign or royal states (used mainly via foreign_rule joins)
  noble       - secular princes/counts/knights (default for plain family names)
  unknown     - 0U0001 'Unbekannte Herrschaft' and unclassifiable

Also emits finer subtype where the name allows (elector, duchy, county,
knight, bishopric, monastery, military_order, ...).

Output: papers/politics/out/ruler_types.csv  (terr_id, terr_name, ruler_type, subtype)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TC = ROOT / "docs/territorial_histories/territorial_hit/territories/territory_codes.csv"
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

# order matters: first hit wins
CHURCH = [
    (r"erzstift|erzbistum|erzbischof", "archbishopric"),
    (r"hochstift|bistum|bischof|fürstbischof|fuerstbischof", "bishopric"),
    (r"deutscher orden|deutschorden|deutschritter|johanniter|templer|"
     r"malteser|schwertbrüder|ritterorden|kommende|ballei", "military_order"),
    (r"kloster|abtei|abt |abtissin|äbtissin|reichsabtei|stift|domkapitel|"
     r"propstei|priorat|kartause|kanoniker|damenstift|frauenstift|"
     r"prämonstratenser|zisterzienser|benediktiner|augustiner|"
     r"johannis|kapitel", "monastery_chapter"),
    (r"patriarch|kurie|papst|päpstlich", "papacy"),
]
SELF = [
    (r"reichsstadt|reichstadt|freie stadt|freie und hansestadt|"
     r"reichsvogteistadt|freie reichsstadt", "imperial_city"),
]
NOBLE = [
    (r"kurfürst|kurfuerst|kurköln|kurmainz|kurtrier|kurpfalz|kursachsen|"
     r"kurbrandenburg|kurbayern", "elector"),
    (r"königreich|koenigreich|krone ", "kingdom"),
    (r"großherzog|grossherzog", "grand_duchy"),
    (r"herzog|herzogtum|hzt", "duchy"),
    (r"pfalzgraf", "count_palatine"),
    (r"markgraf", "margraviate"),
    (r"landgraf", "landgraviate"),
    (r"burggraf", "burgraviate"),
    (r"fürst|fuerst|reichsfürstentum", "principality"),
    (r"grafen|grafschaft|graf |gft", "county"),
    (r"reichsritter|ritter |herren von|edle von|freiherr|edelherr|"
     r"reichsfreiherr|von und zu", "knight_lord"),
    (r"herrschaft", "lordship"),
    (r"republik|kanton|eidgenossen", "republic"),
]


def classify(name: str) -> tuple[str, str]:
    n = f" {str(name).lower()} "
    for pat, sub in SELF:
        if re.search(pat, n):
            return "self", sub
    for pat, sub in CHURCH:
        if re.search(pat, n):
            return "church", sub
    for pat, sub in NOBLE:
        if re.search(pat, n):
            return "noble", sub
    return "noble", "family_line"  # plain dynasty names default to secular noble


def build() -> pd.DataFrame:
    tc = pd.read_csv(TC)
    rows = []
    for _, r in tc.iterrows():
        tid, name = r["terr_id"], r["terr_name"]
        if tid == "0U0001":
            rows.append((tid, name, "unknown", "unknown"))
            continue
        rt, sub = classify(name)
        rows.append((tid, name, rt, sub))
    out = pd.DataFrame(rows, columns=["terr_id", "terr_name", "ruler_type", "subtype"])
    out.to_csv(OUT / "ruler_types.csv", index=False)
    return out


if __name__ == "__main__":
    out = build()
    print(out.ruler_type.value_counts())
    print(out[out.ruler_type == "church"].subtype.value_counts())
    print(out[out.ruler_type == "noble"].subtype.value_counts())
