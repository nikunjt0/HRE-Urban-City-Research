"""Common helpers for variable builders: long → wide pivot and CSV write."""
from pathlib import Path
import pandas as pd

from .paths import OUT


def write_long_and_wide(
    long_df: pd.DataFrame,
    var_name: str,
    feature_cols: list[str],
    score_col: str,
    identity_cols: list[str] = None,
) -> tuple[Path, Path]:
    """Write the long CSV and a wide one-row-per-city CSV.

    `long_df` must have columns: city_id, name, lat, lon, year, plus features
    and `score_col`. `feature_cols` lists the per-year metrics to pivot in the
    wide file. `identity_cols` are the columns kept as-is in the wide file
    (default: city_id, name, lat, lon, nodesid if present).
    """
    long_path = OUT / f"cities_{var_name}.csv"
    wide_path = OUT / f"cities_{var_name}_wide.csv"
    long_df.to_csv(long_path, index=False)

    if identity_cols is None:
        identity_cols = [c for c in ["city_id", "name", "lat", "lon", "nodesid"]
                         if c in long_df.columns]

    pivot_cols = list(dict.fromkeys(feature_cols + [score_col]))
    identity = long_df.drop_duplicates("city_id")[identity_cols].set_index("city_id")
    parts = [identity]
    for col in pivot_cols:
        if col not in long_df.columns:
            continue
        p = long_df.pivot_table(index="city_id", columns="year", values=col, aggfunc="first")
        p.columns = [f"{col}_{int(y)}" for y in p.columns]
        parts.append(p)
    wide = pd.concat(parts, axis=1).reset_index()
    wide.to_csv(wide_path, index=False)
    return long_path, wide_path


def bucket_by_quartile(s: pd.Series) -> pd.Series:
    """Bucket a numeric series to 0-3 using quartiles. NaN → 0."""
    s = s.fillna(s.min() if s.notna().any() else 0)
    if s.nunique() <= 1:
        return pd.Series([0] * len(s), index=s.index)
    try:
        return pd.qcut(s.rank(method="first"), 4, labels=[0, 1, 2, 3]).astype(int)
    except ValueError:
        return pd.Series([0] * len(s), index=s.index)
