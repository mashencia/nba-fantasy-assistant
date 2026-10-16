# Changelog

Changes are listed per phase. Nothing is committed by Claude; the owner reviews and commits.

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
