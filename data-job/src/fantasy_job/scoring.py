"""Fantasy-point formulas.

GENERIC_WEIGHTS is the formula used by the blended Top 200 file. League-specific
weights (read from ESPN in Phase 1c) use the same functions with a different
weights mapping, keyed by the same stat names.
"""
from collections.abc import Mapping

import pandas as pd

# Stat keys follow nba_api column names so a stats DataFrame can be scored directly.
GENERIC_WEIGHTS: Mapping[str, float] = {
    "PTS": 1.0,
    "REB": 1.2,
    "AST": 1.5,
    "STL": 3.0,
    "BLK": 3.0,
    "TOV": -1.0,
}


def fantasy_points(stats: Mapping[str, float], weights: Mapping[str, float] = GENERIC_WEIGHTS) -> float:
    """Score one stat line (totals or per-game). Missing stats count as 0."""
    return sum(w * float(stats.get(stat, 0) or 0) for stat, w in weights.items())


def fantasy_points_frame(df: pd.DataFrame, weights: Mapping[str, float] = GENERIC_WEIGHTS) -> pd.Series:
    """Vectorized version of fantasy_points for a DataFrame of stat lines."""
    total = pd.Series(0.0, index=df.index)
    for stat, w in weights.items():
        if stat in df.columns:
            total = total + w * df[stat].fillna(0).astype(float)
    return total
