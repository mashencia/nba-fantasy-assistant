# NBA Fantasy Assistant

A personal tool for an ESPN H2H **points** fantasy basketball league (2026-27 season).

| Part | Tech | Folder | Status |
|---|---|---|---|
| Data job | Python, pandas, nba_api, espn-api | `data-job/` | Phase 1b: NBA stats → rankings snapshot (ESPN in 1c) |
| API | ASP.NET Core, EF Core, SQLite | `backend/` | not started |
| UI | Angular | `frontend/` | not started |

The plan and architecture decisions are in [docs/PLAN.md](docs/PLAN.md). The change history is in [CHANGELOG.md](CHANGELOG.md).

## Prerequisites (Windows)

- **Python 3.13 from python.org**, run through the `py` launcher.
  Don't use the `python` on PATH if it resolves to `C:\msys64\...`: the MSYS2/MinGW build can't install pandas.
- .NET 10 SDK (Phase 2), Node LTS + Angular CLI (Phase 3).

## Secrets

1. Copy `.env.example` to `.env` in the repo root.
2. Fill in `ESPN_LEAGUE_ID`, `ESPN_S2` and `ESPN_SWID`. `.env` is git-ignored; never commit it or paste it into chat or issues.

### Getting your ESPN cookies
1. Log in at https://fantasy.espn.com in Chrome or Edge and open your league.
2. Press F12 → **Application** tab → **Storage › Cookies** → `https://fantasy.espn.com`.
3. Copy the value of `espn_s2` (a long string) into `ESPN_S2`.
4. Copy the value of `SWID` (looks like `{XXXXXXXX-XXXX-...}`, braces included) into `ESPN_SWID`.
5. The league ID is the `leagueId=` number in your league page's URL.

`espn_s2` expires every so often. When the data job reports an ESPN auth error, repeat steps 1–3.

## Data job (Python)

### First-time setup
```powershell
cd data-job
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```
In VS Code, choose `data-job\.venv\Scripts\python.exe` as the interpreter (Ctrl+Shift+P → "Python: Select Interpreter").

### Refresh the data
```powershell
cd data-job
.\.venv\Scripts\python.exe -m fantasy_job refresh             # uses cached API responses when fresh
.\.venv\Scripts\python.exe -m fantasy_job refresh --no-cache  # force a new pull from stats.nba.com
```
Each run makes 3 calls to stats.nba.com (2025-26 regular season, 2026-27 preseason, 2026-27 regular season) and writes a snapshot to `data/snapshots/<UTC timestamp>/`:

| File | Contents |
|---|---|
| `manifest.json` | schema version, generation time, per-source row counts, cache/staleness flags, blend constants |
| `players.json` | NBA player id, name, team, age |
| `stat_lines.json` | season totals per player per season/type (GP, MIN, PTS, REB, AST, STL, BLK, TOV, FGM, FGA, FG3M, FTM, FTA, DD2, TD3) |
| `valuations.json` | per-source GP and FP/G, blend, availability, score, rank |

`data/snapshots/latest.txt` names the newest complete snapshot. The 10 newest are kept.

**Caching:** a finished season is cached for 7 days and in-progress seasons for 6 hours (`data/cache/nba/`). If stats.nba.com fails after 3 retries, the last cached copy is used and flagged `"stale": true` in the manifest. If there's no cache either, the refresh stops and the previous snapshot stays in place.

### Tests
```powershell
.\.venv\Scripts\python.exe -m pytest
```

## How the rankings are computed
See [docs/PLAN.md › Valuation formula](docs/PLAN.md#valuation-formula).
