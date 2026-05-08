"""Crosswalk between Viabundus nodesid and Bairoch city_id.

Loads the cached crosswalk if available; otherwise raises asking the user to
run build_crosswalk.py first. Exposes lookup helpers in both directions.
"""
import pandas as pd
from .paths import CROSSWALK_CSV


def load_crosswalk() -> pd.DataFrame:
    if not CROSSWALK_CSV.exists():
        raise FileNotFoundError(
            f"Crosswalk not found at {CROSSWALK_CSV}. "
            "Run `python build_crosswalk.py` first."
        )
    df = pd.read_csv(CROSSWALK_CSV)
    return df


def attach_nodesid(df: pd.DataFrame, city_id_col: str = "city_id") -> pd.DataFrame:
    """Add a `nodesid` column to a city_id-keyed DataFrame using the crosswalk.

    Cities not in the crosswalk get nodesid = NaN.
    """
    cw = load_crosswalk()
    cw_subset = cw[["city_id", "nodesid"]].dropna(subset=["city_id"]).drop_duplicates("city_id")
    return df.merge(cw_subset, left_on=city_id_col, right_on="city_id", how="left",
                    suffixes=("", "_cw")).drop(columns=["city_id_cw"], errors="ignore")
