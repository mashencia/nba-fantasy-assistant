"""Player season totals from stats.nba.com via nba_api.

stats.nba.com is unofficial and throttles or blocks aggressive clients, so:
- only the bulk LeagueDashPlayerStats endpoint is used (one call per season/type),
- every call has a timeout, retries with exponential backoff, and a pause between calls,
- responses are cached on disk; if the API fails, the last cached copy is used.
"""
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Columns kept from the endpoint (it returns ~70, mostly ranks).
KEEP_COLUMNS = [
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "AGE", "GP", "MIN",
    "FGM", "FGA", "FG3M", "FTM", "FTA", "REB", "AST", "STL", "BLK", "TOV", "PTS",
    "DD2", "TD3",
]

REQUEST_TIMEOUT_S = 30
PAUSE_BETWEEN_CALLS_S = 1.0


class NbaApiError(RuntimeError):
    pass


@dataclass
class FetchResult:
    season: str
    season_type: str
    frame: pd.DataFrame
    fetched_at: datetime
    from_cache: bool
    stale: bool  # True when the API failed and an expired cache was used


Fetcher = Callable[[str, str], pd.DataFrame]


def _fetch_from_api(season: str, season_type: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import leaguedashplayerstats

    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star=season_type,
        per_mode_detailed="Totals",
        timeout=REQUEST_TIMEOUT_S,
    )
    return endpoint.get_data_frames()[0]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in KEEP_COLUMNS if c not in df.columns]
    if missing and len(df):
        raise NbaApiError(f"nba_api response is missing columns: {missing}")
    if not len(df):
        return pd.DataFrame(columns=KEEP_COLUMNS)
    return df[KEEP_COLUMNS].copy()


def _cache_path(cache_dir: Path, season: str, season_type: str) -> Path:
    return cache_dir / f"{season}_{season_type.replace(' ', '')}.json"


def _read_cache(path: Path) -> tuple[pd.DataFrame, datetime] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(payload["rows"], columns=KEEP_COLUMNS)
    return frame, datetime.fromisoformat(payload["fetched_at"])


def _write_cache(path: Path, frame: pd.DataFrame, fetched_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": fetched_at.isoformat(), "rows": json.loads(frame.to_json(orient="records"))}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def fetch_player_totals(
    season: str,
    season_type: str,
    *,
    cache_dir: Path,
    max_age: timedelta,
    use_cache: bool = True,
    fetcher: Fetcher = _fetch_from_api,
    retries: int = 3,
    backoff_s: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> FetchResult:
    """Season totals for every player with at least one game. season_type: 'Regular Season' or 'Pre Season'."""
    path = _cache_path(cache_dir, season, season_type)
    cached = _read_cache(path)
    now = datetime.now(timezone.utc)

    if use_cache and cached and now - cached[1] < max_age:
        log.info("nba %s %s: cache hit (%d rows)", season, season_type, len(cached[0]))
        return FetchResult(season, season_type, cached[0], cached[1], from_cache=True, stale=False)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            frame = _normalize(fetcher(season, season_type))
            _write_cache(path, frame, now)
            log.info("nba %s %s: fetched %d rows", season, season_type, len(frame))
            sleep(PAUSE_BETWEEN_CALLS_S)
            return FetchResult(season, season_type, frame, now, from_cache=False, stale=False)
        except Exception as exc:  # requests timeouts, JSON errors, HTTP blocks
            last_error = exc
            log.warning("nba %s %s: attempt %d/%d failed: %s", season, season_type, attempt, retries, exc)
            if attempt < retries:
                sleep(backoff_s * 2 ** (attempt - 1))

    if cached:
        log.warning("nba %s %s: API unavailable, using cache from %s", season, season_type, cached[1].isoformat())
        return FetchResult(season, season_type, cached[0], cached[1], from_cache=True, stale=True)
    raise NbaApiError(f"Could not fetch {season} {season_type} and no cache exists") from last_error
