"""Paths and season constants. Secrets (Phase 1c) will load from the repo-root .env."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# nba_api season strings. LAST is complete; CURRENT is in progress.
LAST_SEASON = "2025-26"
CURRENT_SEASON = "2026-27"

SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOTS_TO_KEEP = 10


def data_dir() -> Path:
    """Where snapshots and caches live. Override with FANTASY_DATA_DIR (used by tests and later by .NET)."""
    return Path(os.environ.get("FANTASY_DATA_DIR", REPO_ROOT / "data"))
