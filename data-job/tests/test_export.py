"""Snapshot folder writing and pruning."""
import json
from datetime import datetime, timedelta, timezone

import pandas as pd

from fantasy_job.export import LATEST_POINTER, prune_snapshots, write_snapshot

T0 = datetime(2026, 10, 15, 22, 30, tzinfo=timezone.utc)


def write(tmp_path, when=T0):
    tables = {"players": pd.DataFrame({"nba_player_id": [1, 2], "name": ["Nikola Jokić", "Rookie"],
                                       "last_fp": [62.2, float("nan")]})}
    return write_snapshot(tmp_path, when, manifest={"schema_version": 1}, tables=tables)


def test_writes_tables_and_manifest(tmp_path):
    path = write(tmp_path)
    assert path.name == "20261015T223000Z"
    assert json.loads((path / "manifest.json").read_text(encoding="utf-8")) == {"schema_version": 1}
    players = json.loads((path / "players.json").read_text(encoding="utf-8"))
    assert players[0]["name"] == "Nikola Jokić"  # unicode preserved
    assert players[1]["last_fp"] is None          # NaN -> null


def test_latest_pointer_and_no_temp_folder_left(tmp_path):
    path = write(tmp_path)
    assert (tmp_path / LATEST_POINTER).read_text(encoding="utf-8") == path.name
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".tmp")]


def test_prune_keeps_newest(tmp_path):
    for i in range(4):
        write(tmp_path, T0 + timedelta(minutes=i))
    removed = prune_snapshots(tmp_path, keep=2)
    remaining = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(removed) == 2
    assert remaining == ["20261015T223200Z", "20261015T223300Z"]
