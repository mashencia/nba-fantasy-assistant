"""Command line entry point: python -m fantasy_job refresh [--no-cache]"""
import argparse
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import pandas as pd

from fantasy_job import config
from fantasy_job.blend import DEFAULT_CONFIG
from fantasy_job.export import prune_snapshots, write_snapshot
from fantasy_job.sources.nba import FetchResult, NbaApiError, fetch_player_totals
from fantasy_job.valuation import build_valuations

log = logging.getLogger("fantasy_job")

# A completed season never changes; in-progress ones are refetched after a few hours.
PULLS = [
    ("last", config.LAST_SEASON, "Regular Season", timedelta(days=7)),
    ("pre", config.CURRENT_SEASON, "Pre Season", timedelta(hours=6)),
    ("cur", config.CURRENT_SEASON, "Regular Season", timedelta(hours=6)),
]

STAT_LINE_COLUMNS = {
    "PLAYER_ID": "nba_player_id", "GP": "gp", "MIN": "min", "PTS": "pts", "REB": "reb", "AST": "ast",
    "STL": "stl", "BLK": "blk", "TOV": "tov", "FGM": "fgm", "FGA": "fga", "FG3M": "fg3m",
    "FTM": "ftm", "FTA": "fta", "DD2": "dd2", "TD3": "td3",
}


def _stat_lines(results: dict[str, FetchResult]) -> pd.DataFrame:
    frames = []
    for r in results.values():
        if r.frame.empty:
            continue
        df = r.frame[list(STAT_LINE_COLUMNS)].rename(columns=STAT_LINE_COLUMNS)
        df.insert(1, "season", r.season)
        df.insert(2, "season_type", r.season_type)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["nba_player_id"])


def refresh(use_cache: bool = True) -> int:
    data_dir = config.data_dir()
    cache_dir = data_dir / "cache" / "nba"
    generated_at = datetime.now(timezone.utc)

    try:
        results = {
            key: fetch_player_totals(season, stype, cache_dir=cache_dir, max_age=age, use_cache=use_cache)
            for key, season, stype, age in PULLS
        }
    except NbaApiError as exc:
        log.error("Refresh aborted, previous snapshot kept: %s", exc)
        return 1

    valuations = build_valuations(results["last"].frame, results["pre"].frame, results["cur"].frame)

    players = valuations[["nba_player_id", "name", "team", "age"]]
    value_cols = ["nba_player_id", "last_gp", "last_fp", "pre_gp", "pre_fp", "cur_gp", "cur_fp",
                  "blend", "availability", "score", "rank"]
    manifest = {
        "schema_version": config.SNAPSHOT_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "seasons": {"last": config.LAST_SEASON, "current": config.CURRENT_SEASON},
        "sources": {
            "nba": [
                {
                    "season": r.season, "season_type": r.season_type, "rows": len(r.frame),
                    "fetched_at": r.fetched_at.isoformat(), "from_cache": r.from_cache, "stale": r.stale,
                }
                for r in results.values()
            ],
            "espn": {"status": "not_run"},  # Phase 1c
        },
        "blend_config": asdict(DEFAULT_CONFIG),
        "counts": {"players": len(players)},
    }

    snapshots_dir = data_dir / "snapshots"
    path = write_snapshot(
        snapshots_dir, generated_at, manifest=manifest,
        tables={
            "players": players,
            "stat_lines": _stat_lines(results),
            "valuations": valuations[value_cols].round(4),
        },
    )
    removed = prune_snapshots(snapshots_dir, config.SNAPSHOTS_TO_KEEP)
    log.info("Snapshot written: %s (%d players; pruned %d old snapshots)", path, len(players), len(removed))

    top = valuations.head(10)
    for r in top.itertuples():
        log.info("  %3d. %-28s %-4s score %.1f", r.rank, r.name, r.team, r.score)
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252, which crashes on names like "Jokić".
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)

    parser = argparse.ArgumentParser(prog="fantasy_job")
    sub = parser.add_subparsers(dest="command", required=True)
    p_refresh = sub.add_parser("refresh", help="Pull stats, recompute rankings, write a snapshot")
    p_refresh.add_argument("--no-cache", action="store_true", help="Ignore cached API responses")
    args = parser.parse_args(argv)

    if args.command == "refresh":
        return refresh(use_cache=not args.no_cache)
    return 2
