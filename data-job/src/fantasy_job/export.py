"""Write a snapshot folder that the .NET API imports.

Layout: <data>/snapshots/<UTC timestamp>/{manifest,players,stat_lines,valuations}.json
plus <data>/snapshots/latest.txt naming the newest complete snapshot.

Files are written to a temp folder and renamed at the end, so a crash never
leaves a half-written snapshot that looks complete.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

LATEST_POINTER = "latest.txt"


def _records(df: pd.DataFrame) -> list[dict]:
    # to_json turns NaN into null, which plain json.dumps would not.
    return json.loads(df.to_json(orient="records", force_ascii=False))


def write_snapshot(
    snapshots_dir: Path,
    generated_at: datetime,
    *,
    manifest: dict,
    tables: dict[str, pd.DataFrame],
) -> Path:
    name = generated_at.strftime("%Y%m%dT%H%M%SZ")
    final = snapshots_dir / name
    tmp = snapshots_dir / f".tmp-{name}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    for table, df in tables.items():
        (tmp / f"{table}.json").write_text(
            json.dumps(_records(df), ensure_ascii=False, indent=1), encoding="utf-8"
        )
    (tmp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    tmp.rename(final)
    (snapshots_dir / LATEST_POINTER).write_text(name, encoding="utf-8")
    return final


def prune_snapshots(snapshots_dir: Path, keep: int) -> list[Path]:
    """Delete all but the newest `keep` snapshot folders. Returns what was deleted."""
    folders = sorted(p for p in snapshots_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    doomed = folders[:-keep] if keep > 0 else folders
    for p in doomed:
        shutil.rmtree(p)
    return doomed
