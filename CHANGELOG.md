# Changelog

Changes are listed per phase. Nothing is committed by Claude; the owner reviews and commits.

## Phase 1b: NBA stats pull and rankings snapshot (2026-10-15)
**Added**
- `fantasy_job/config.py`: repo/data paths (`FANTASY_DATA_DIR` override), season constants (`2025-26`, `2026-27`), snapshot schema version, retention (10).
- `fantasy_job/sources/nba.py`: `fetch_player_totals()` using the bulk `LeagueDashPlayerStats` endpoint. 30 s timeout, 3 retries with exponential backoff (2 s, 4 s), 1 s pause between calls, JSON disk cache (7 days for finished seasons, 6 h otherwise), stale-cache fallback when the API is down, error if columns are missing.
- `fantasy_job/valuation.py`: `build_valuations()` merges the three sources on NBA player id, computes FP/G per source, takes name/team/age from the newest source, then blend → availability → score → rank.
- `fantasy_job/export.py`: atomic snapshot writer (temp folder + rename), `latest.txt` pointer, NaN → `null`, UTF-8 names, pruning.
- `fantasy_job/cli.py` + `__main__.py`: `python -m fantasy_job refresh [--no-cache]`. Forces UTF-8 console output and logs the top 10. Exit code 1 if the NBA pull fails.
- Tests: `test_nba_source.py` (9), `test_valuation.py` (5), `test_export.py` (3), plus 1 new blend test. **36 total, all passing. No network calls in tests.**
- `nba_api==1.11.4` in `requirements.txt`. `pyproject.toml` now builds as a package (`pip install -e .`).

**Changed**
- `blend.py`: **bug fix.** `SourceWeight.weight()` and `availability()` treated NaN games played as truthy, which would make a merged player's score NaN. They now treat None/NaN as 0.
- `blend.compute_scores()` now also outputs an `availability` column.
- README: setup, refresh command, snapshot layout, caching behavior, VS Code interpreter tip.

**Verified against live data (stats.nba.com, 2026-10-15)**
- 2025-26 regular season: 582 players. 2026-27 preseason: 569. 2026-27 regular season: 0 (not started). 714 unique players in the snapshot.
- All 200 players in the blended file are found. 2025-26 GP is identical for all 200, and FP/G is within 0.06 (rounding).
- For the 39 players with no new preseason games since Oct 10, the score matches the file within 0.052. The other 161 have played more preseason games since then, which explains their differences (largest: Keegan Murray 22.1 → 18.8 after 2 new games).
- A second run is served entirely from cache (~0.2 s, no API calls).

**Open for owner decision**
- Availability factor: keep 2025-26 GP, or switch to the current-season missed-games rate a few weeks in?
- Preseason games can move players who skipped preseason by up to ~3 points. This is how the file's formula behaves.

## Phase 1a: Scoring and blend formulas (2026-10-15)
**Added**
- `data-job/` Python project (`pyproject.toml`, pinned `requirements.txt`: pandas 3.0.6, python-dotenv 1.2.4, pytest 9.1.1).
- `fantasy_job/scoring.py`: generic FP formula (`PTS + 1.2·REB + 1.5·AST + 3·STL + 3·BLK − TOV`). Weights are a parameter, so ESPN league weights can reuse it in Phase 1c.
- `fantasy_job/blend.py`: the blend formula ported from the blended Top 200 file, with all constants in `BlendConfig`.
  - **New:** a 2026-27 regular-season term (max weight 1.6, full at 41 GP). It contributes zero with no games, so the original output is unchanged until opening night. **Constants need owner review.**
- `tests/fixtures/blended_top200_2026-10-10.csv`: formula inputs and outputs for the 200 rows of the blended file (no notes).
- 18 tests: FP formula vs exact preseason totals; blend + score vs all 200 rows (±0.11); top-10 order; prior, availability and source-weight behavior; current-season term.

**Findings**
- The blend's prior weight (0.15) was not stated in the file. I inferred it, and it reproduces every row (max score difference 0.084, mean 0.03).
- 39 players shift by 1–2 rank places compared with the file. They're ties at the file's 0.1 rounding, broken differently. No one moves more than 2 places.

## Phase 0: Repo scaffolding (2026-10-15)
**Added**
- `git init` (branch `main`). Nothing staged or committed.
- `.gitignore`: `.env`, `data/`, venvs, `bin/obj`, `node_modules`.
- `.env.example`: ESPN_LEAGUE_ID, ESPN_SEASON=2027, ESPN_S2, ESPN_SWID, ESPN_TEAM_ID.
- `README.md` skeleton with cookie instructions; `docs/PLAN.md` with the approved decisions.

**Notes**
- The `python` on PATH is MSYS2/MinGW (`C:\msys64\mingw64\bin\python.exe`) and can't install pandas. The venv uses the python.org 3.13 build through `py -3.13`.
