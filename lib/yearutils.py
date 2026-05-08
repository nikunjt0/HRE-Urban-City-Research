"""Year-coercion helpers, lifted from build_trade_access.py."""
import pandas as pd


def to_int_year(s: pd.Series, default: int) -> pd.Series:
    """Coerce a year column with 'null', NaN, blank to int with default."""
    return pd.to_numeric(s, errors="coerce").fillna(default).astype(int)


def is_active(from_year, to_year, year: int,
              default_from: int = 1350, default_to: int = 1650) -> pd.Series:
    """Boolean mask: feature is active in `year` given its from/to bounds."""
    fy = to_int_year(from_year, default_from)
    ty = to_int_year(to_year, default_to)
    return (fy <= year) & (year <= ty)
