"""Blend formula, checked against every row of NBA_Top200_2026-27_Blended.md.

The file's inputs are rounded to 0.1, so a recomputed value can differ from the
printed one by about 0.1 even when the formula is exact.
"""
from pathlib import Path

import pandas as pd
import pytest

from fantasy_job.blend import (
    BlendConfig,
    SourceWeight,
    availability,
    blend_fp,
    compute_scores,
)

FIXTURE = Path(__file__).parent / "fixtures" / "blended_top200_2026-10-10.csv"
TOLERANCE = 0.11


@pytest.fixture(scope="module")
def blended_file() -> pd.DataFrame:
    return pd.read_csv(FIXTURE)


@pytest.fixture(scope="module")
def recomputed(blended_file) -> pd.DataFrame:
    # Drop the file's outputs so compute_scores produces fresh ones.
    return compute_scores(blended_file.drop(columns=["blend", "score", "rank"]))


def test_fixture_has_200_rows(blended_file):
    assert len(blended_file) == 200


def test_blend_and_score_match_file(blended_file):
    rows = []
    for r in blended_file.itertuples():
        b = blend_fp(r.last_fp, r.last_gp, r.pre_fp, r.pre_gp)
        s = b * availability(r.last_gp)
        rows.append((r.player, r.blend, b, r.score, s))
    mismatches = [
        f"{p}: blend file={fb} got={b:.2f}, score file={fs} got={s:.2f}"
        for p, fb, b, fs, s in rows
        if abs(fb - b) > TOLERANCE or abs(fs - s) > TOLERANCE
    ]
    assert not mismatches, "\n".join(mismatches)


def test_top_10_order_matches_file(recomputed):
    assert recomputed["player"].head(10).tolist() == [
        "Nikola Jokić", "Luka Dončić", "Victor Wembanyama", "Shai Gilgeous-Alexander",
        "Tyrese Maxey", "Jalen Johnson", "Cade Cunningham", "Kawhi Leonard",
        "Alperen Sengun", "Jaylen Brown",
    ]


# --- Behaviour of the individual pieces -----------------------------------

def test_no_data_returns_prior():
    assert blend_fp(None, 0, None, 0) == pytest.approx(15.0)


def test_rookie_with_only_preseason_is_shrunk_toward_prior():
    # Aday Mara: 2 preseason games -> blend 24.3, score 20.6 in the file.
    # Exact FP/G is 69.5 / 2 = 34.75; with that unrounded input the score is 20.65.
    b = blend_fp(None, 0, 34.75, 2)
    assert b == pytest.approx(24.3, abs=0.05)
    assert b * availability(0) == pytest.approx(20.6, abs=0.06)


def test_availability_range():
    assert availability(0) == pytest.approx(0.85)
    assert availability(65) == pytest.approx(1.0)
    assert availability(82) == pytest.approx(1.0)  # capped


def test_source_weight_ramps_and_caps():
    sw = SourceWeight(0.8, 70)
    assert sw.weight(0) == 0
    assert sw.weight(35) == pytest.approx(0.4)
    assert sw.weight(100) == pytest.approx(0.8)


# --- Current-season term (added for the 2026-27 regular season) --------------

def test_zero_current_games_reproduces_original_formula():
    original = blend_fp(62.2, 65, 21.2, 2)
    assert blend_fp(62.2, 65, 21.2, 2, cur_fp=10.0, cur_gp=0) == original


def test_current_season_pulls_blend_toward_current_form():
    base = blend_fp(40.0, 70, None, 0)
    early = blend_fp(40.0, 70, None, 0, cur_fp=50.0, cur_gp=5)
    mid = blend_fp(40.0, 70, None, 0, cur_fp=50.0, cur_gp=41)
    assert base < early < mid < 50.0


def test_current_season_weight_is_configurable():
    cfg = BlendConfig(current_season=SourceWeight(0.0, 41))
    assert blend_fp(40.0, 70, None, 0, 50.0, 41, cfg) == blend_fp(40.0, 70, None, 0)
