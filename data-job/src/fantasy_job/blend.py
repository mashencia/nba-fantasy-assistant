"""Blended player valuation (see docs/PLAN.md > Valuation formula).

blend = (sum of w_src * FP_src + prior_weight * prior_fp) / (sum of w_src + prior_weight)
score = blend * availability(last-season GP)

Each source's weight ramps linearly with games played up to its max_weight, so a
player with few games leans on the prior rather than on a tiny sample.
"""
from dataclasses import dataclass, field

import pandas as pd


def _num(x: float | None) -> float:
    """None/NaN -> 0. Merged DataFrames use NaN for 'no games in this source'."""
    return 0.0 if x is None or pd.isna(x) else float(x)


@dataclass(frozen=True)
class SourceWeight:
    max_weight: float
    full_gp: float

    def weight(self, gp: float | None) -> float:
        gp = _num(gp)
        if gp <= 0:
            return 0.0
        return self.max_weight * min(gp / self.full_gp, 1.0)


@dataclass(frozen=True)
class BlendConfig:
    last_season: SourceWeight = field(default_factory=lambda: SourceWeight(0.8, 70))
    preseason: SourceWeight = field(default_factory=lambda: SourceWeight(0.2, 3))
    # Added for the 2026-27 regular season. Weight 0 until games are played,
    # so the original file's formula is reproduced exactly before opening night.
    current_season: SourceWeight = field(default_factory=lambda: SourceWeight(1.6, 41))
    prior_fp: float = 15.0
    prior_weight: float = 0.15
    availability_floor: float = 0.85
    availability_full_gp: float = 65


DEFAULT_CONFIG = BlendConfig()


def blend_fp(
    last_fp: float | None,
    last_gp: float | None,
    pre_fp: float | None,
    pre_gp: float | None,
    cur_fp: float | None = None,
    cur_gp: float | None = None,
    config: BlendConfig = DEFAULT_CONFIG,
) -> float:
    """Shrunk, games-weighted average of FP/G across sources."""
    parts = [
        (config.last_season.weight(last_gp), last_fp),
        (config.preseason.weight(pre_gp), pre_fp),
        (config.current_season.weight(cur_gp), cur_fp),
    ]
    num = config.prior_weight * config.prior_fp
    den = config.prior_weight
    for w, fp in parts:
        if w > 0 and fp is not None and not pd.isna(fp):
            num += w * fp
            den += w
    return num / den


def availability(last_gp: float | None, config: BlendConfig = DEFAULT_CONFIG) -> float:
    gp = max(_num(last_gp), 0)
    ratio = min(gp / config.availability_full_gp, 1.0)
    return config.availability_floor + (1 - config.availability_floor) * ratio


def score(blend: float, last_gp: float | None, config: BlendConfig = DEFAULT_CONFIG) -> float:
    return blend * availability(last_gp, config)


def compute_scores(df: pd.DataFrame, config: BlendConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Add blend, availability, score and rank columns.

    Expected columns: last_fp, last_gp, pre_fp, pre_gp; optional cur_fp, cur_gp.
    """
    out = df.copy()
    for col in ("cur_fp", "cur_gp"):
        if col not in out.columns:
            out[col] = None
    out["blend"] = [
        blend_fp(r.last_fp, r.last_gp, r.pre_fp, r.pre_gp, r.cur_fp, r.cur_gp, config)
        for r in out.itertuples()
    ]
    out["availability"] = [availability(gp, config) for gp in out["last_gp"]]
    out["score"] = out["blend"] * out["availability"]
    out["rank"] = out["score"].rank(ascending=False, method="first").astype(int)
    return out.sort_values("rank")
