"""Turn per-source season totals into one valuation row per player."""
import pandas as pd

from fantasy_job.blend import DEFAULT_CONFIG, BlendConfig, compute_scores
from fantasy_job.scoring import GENERIC_WEIGHTS, fantasy_points_frame

# Snapshot / valuation column prefix for each source.
SOURCES = ("last", "pre", "cur")


def _per_source(totals: pd.DataFrame, prefix: str, weights) -> pd.DataFrame:
    if totals.empty:
        return pd.DataFrame(columns=["PLAYER_ID", f"{prefix}_gp", f"{prefix}_fp"])
    gp = totals["GP"].astype(float)
    fp_total = fantasy_points_frame(totals, weights)
    return pd.DataFrame({
        "PLAYER_ID": totals["PLAYER_ID"],
        f"{prefix}_gp": gp,
        f"{prefix}_fp": fp_total / gp.where(gp > 0),
    })


def _identity(totals_by_source: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Name/team/age per player, preferring the most recent source (current > preseason > last)."""
    frames = [
        totals_by_source[s][["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "AGE"]]
        for s in ("cur", "pre", "last")
        if not totals_by_source[s].empty
    ]
    if not frames:
        return pd.DataFrame(columns=["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "AGE"])
    return pd.concat(frames).drop_duplicates("PLAYER_ID", keep="first")


def build_valuations(
    last: pd.DataFrame,
    pre: pd.DataFrame,
    cur: pd.DataFrame,
    config: BlendConfig = DEFAULT_CONFIG,
    weights=GENERIC_WEIGHTS,
) -> pd.DataFrame:
    """One row per player: per-source GP and FP/G, then blend, availability, score, rank."""
    totals = {"last": last, "pre": pre, "cur": cur}
    merged = _identity(totals)
    for prefix in SOURCES:
        merged = merged.merge(_per_source(totals[prefix], prefix, weights), on="PLAYER_ID", how="left")
    for prefix in SOURCES:
        merged[f"{prefix}_gp"] = merged[f"{prefix}_gp"].fillna(0)

    scored = compute_scores(merged, config)
    return scored.rename(columns={
        "PLAYER_ID": "nba_player_id",
        "PLAYER_NAME": "name",
        "TEAM_ABBREVIATION": "team",
        "AGE": "age",
    }).reset_index(drop=True)
