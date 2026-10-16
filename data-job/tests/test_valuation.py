"""Merging per-source totals into valuations."""
import pandas as pd
import pytest

from fantasy_job.blend import blend_fp
from fantasy_job.sources.nba import KEEP_COLUMNS
from fantasy_job.valuation import build_valuations


def totals(rows: list[dict]) -> pd.DataFrame:
    base = {c: 0 for c in KEEP_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows], columns=KEEP_COLUMNS)


EMPTY = totals([])

VET_LAST = dict(PLAYER_ID=1, PLAYER_NAME="Vet", TEAM_ABBREVIATION="OLD", AGE=30, GP=70, PTS=1400, REB=350, AST=350)
VET_PRE = dict(PLAYER_ID=1, PLAYER_NAME="Vet", TEAM_ABBREVIATION="NEW", AGE=31, GP=2, PTS=30, REB=10, AST=6)
ROOKIE_PRE = dict(PLAYER_ID=2, PLAYER_NAME="Rookie", TEAM_ABBREVIATION="NEW", AGE=19, GP=2, PTS=40, REB=10, AST=4)


def test_fp_per_game_from_totals():
    v = build_valuations(totals([VET_LAST]), EMPTY, EMPTY)
    # (1400 + 1.2*350 + 1.5*350) / 70 = 33.5
    assert v.loc[0, "last_fp"] == pytest.approx(33.5)


def test_sources_merge_on_player_id_and_latest_team_wins():
    v = build_valuations(totals([VET_LAST]), totals([VET_PRE]), EMPTY).set_index("nba_player_id")
    assert v.loc[1, "team"] == "NEW"
    assert v.loc[1, "age"] == 31
    assert v.loc[1, "last_gp"] == 70 and v.loc[1, "pre_gp"] == 2


def test_rookie_without_last_season_gets_zero_gp_not_nan():
    v = build_valuations(totals([VET_LAST]), totals([VET_PRE, ROOKIE_PRE]), EMPTY).set_index("nba_player_id")
    rookie = v.loc[2]
    assert rookie["last_gp"] == 0
    assert pd.isna(rookie["last_fp"])
    # preseason FP/G = (40 + 1.2*10 + 1.5*4) / 2 = 29.0; no last season -> availability 0.85
    assert rookie["pre_fp"] == pytest.approx(29.0)
    assert rookie["score"] == pytest.approx(blend_fp(None, 0, 29.0, 2) * 0.85)


def test_rank_orders_by_score():
    v = build_valuations(totals([VET_LAST]), totals([VET_PRE, ROOKIE_PRE]), EMPTY)
    assert v["rank"].tolist() == [1, 2]
    assert v.loc[0, "name"] == "Vet"


def test_current_season_games_change_the_score():
    before = build_valuations(totals([VET_LAST]), EMPTY, EMPTY).loc[0, "score"]
    hot_start = dict(VET_LAST, GP=10, PTS=400, REB=100, AST=100)  # 55 FP/G
    after = build_valuations(totals([VET_LAST]), EMPTY, totals([hot_start])).loc[0, "score"]
    assert after > before
