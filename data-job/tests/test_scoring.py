"""Fantasy-point formula, checked against exact preseason totals from
NBA_Preseason_Top200_2026-27.md (FP column = generic formula on totals)."""
import pandas as pd
import pytest

from fantasy_job.scoring import fantasy_points, fantasy_points_frame

# (player, PTS, REB, AST, STL, BLK, TOV, expected FP)
PRESEASON_TOTALS = [
    ("Ty Jerome", 45, 2, 13, 0, 1, 3, 66.9),
    ("Jake LaRavia", 38, 10, 6, 6, 4, 3, 86.0),
    ("Charles Bassey", 29, 20, 4, 6, 6, 7, 88.0),
    ("Liam McNeeley", 14, 1, 0, 0, 0, 6, 9.2),  # turnovers subtract
    ("Aaron Nesmith", 19, 0, 0, 0, 0, 0, 19.0),
]


@pytest.mark.parametrize("player,pts,reb,ast,stl,blk,tov,expected", PRESEASON_TOTALS)
def test_generic_fp_matches_file(player, pts, reb, ast, stl, blk, tov, expected):
    line = {"PTS": pts, "REB": reb, "AST": ast, "STL": stl, "BLK": blk, "TOV": tov}
    assert fantasy_points(line) == pytest.approx(expected, abs=1e-9)


def test_missing_stats_count_as_zero():
    assert fantasy_points({"PTS": 10}) == 10


def test_custom_weights():
    # ESPN-style weights (Phase 1c) score with the same function.
    weights = {"PTS": 1, "REB": 1, "AST": 2, "STL": 4, "BLK": 4, "TOV": -2}
    assert fantasy_points({"PTS": 20, "REB": 5, "AST": 5, "STL": 1, "BLK": 1, "TOV": 2}, weights) == 39


def test_frame_matches_scalar():
    df = pd.DataFrame(
        [dict(PTS=p, REB=r, AST=a, STL=s, BLK=b, TOV=t) for _, p, r, a, s, b, t, _ in PRESEASON_TOTALS]
    )
    expected = [row[-1] for row in PRESEASON_TOTALS]
    assert fantasy_points_frame(df).tolist() == pytest.approx(expected)
