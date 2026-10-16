"""Caching, retry and fallback behaviour of the nba_api source. No network calls."""
from datetime import timedelta

import pandas as pd
import pytest

from fantasy_job.sources.nba import KEEP_COLUMNS, NbaApiError, fetch_player_totals


def api_frame(n_rows: int = 2) -> pd.DataFrame:
    row = {c: 1 for c in KEEP_COLUMNS}
    rows = [{**row, "PLAYER_ID": i, "PLAYER_NAME": f"Player {i}", "TEAM_ABBREVIATION": "AAA", "EXTRA_RANK": 5}
            for i in range(n_rows)]
    return pd.DataFrame(rows)


class FakeFetcher:
    def __init__(self, failures: int = 0, frame: pd.DataFrame | None = None):
        self.failures = failures
        self.calls = 0
        self.frame = api_frame() if frame is None else frame

    def __call__(self, season, season_type):
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError("stats.nba.com timed out")
        return self.frame


def fetch(tmp_path, fetcher, **kw):
    kw.setdefault("max_age", timedelta(hours=6))
    return fetch_player_totals("2025-26", "Regular Season", cache_dir=tmp_path, fetcher=fetcher,
                               sleep=lambda s: None, **kw)


def test_keeps_only_needed_columns(tmp_path):
    result = fetch(tmp_path, FakeFetcher())
    assert list(result.frame.columns) == KEEP_COLUMNS
    assert not result.from_cache


def test_second_call_is_served_from_cache(tmp_path):
    fetcher = FakeFetcher()
    fetch(tmp_path, fetcher)
    result = fetch(tmp_path, fetcher)
    assert fetcher.calls == 1
    assert result.from_cache and not result.stale
    assert len(result.frame) == 2


def test_expired_cache_is_refetched(tmp_path):
    fetcher = FakeFetcher()
    fetch(tmp_path, fetcher)
    fetch(tmp_path, fetcher, max_age=timedelta(0))
    assert fetcher.calls == 2


def test_no_cache_flag_forces_fetch(tmp_path):
    fetcher = FakeFetcher()
    fetch(tmp_path, fetcher)
    fetch(tmp_path, fetcher, use_cache=False)
    assert fetcher.calls == 2


def test_retries_then_succeeds(tmp_path):
    fetcher = FakeFetcher(failures=2)
    result = fetch(tmp_path, fetcher, retries=3)
    assert fetcher.calls == 3
    assert len(result.frame) == 2


def test_falls_back_to_stale_cache_when_api_is_down(tmp_path):
    fetch(tmp_path, FakeFetcher())
    result = fetch(tmp_path, FakeFetcher(failures=99), max_age=timedelta(0), retries=2)
    assert result.from_cache and result.stale
    assert len(result.frame) == 2


def test_raises_when_api_is_down_and_no_cache(tmp_path):
    with pytest.raises(NbaApiError):
        fetch(tmp_path, FakeFetcher(failures=99), retries=2)


def test_empty_season_is_valid(tmp_path):
    # e.g. 2026-27 regular season before opening night
    result = fetch(tmp_path, FakeFetcher(frame=pd.DataFrame()))
    assert result.frame.empty
    assert list(result.frame.columns) == KEEP_COLUMNS


def test_missing_columns_is_an_error(tmp_path):
    broken = api_frame().drop(columns=["PTS"])
    with pytest.raises(NbaApiError):
        fetch(tmp_path, FakeFetcher(frame=broken), retries=1)
