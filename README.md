# NBA Fantasy Assistant

A personal tool for an ESPN H2H **points** fantasy basketball league (2026-27 season).

| Part | Tech | Folder | Status |
|---|---|---|---|
| Data job | Python, pandas, nba_api, espn-api | `data-job/` | Phase 1a: scoring + blend formulas |
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

```powershell
cd data-job
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

## How the rankings are computed
See [docs/PLAN.md › Valuation formula](docs/PLAN.md#valuation-formula).
