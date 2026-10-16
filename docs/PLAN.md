# MVP Plan (approved 2026-10-15)

## Decisions
| Topic | Decision | Why |
|---|---|---|
| League scoring | H2H **points** only | The user's league. Categories math is out of scope. |
| Python ↔ .NET | Python writes a JSON snapshot folder; .NET imports it into SQLite | EF Core is the only schema owner; the snapshot is a reviewable contract; a failed refresh never corrupts the DB |
| Player data shown | Computed stats + ESPN data only | The hand-written style/injury notes in the ranking markdown were unverified, so they're dropped |
| Injuries | ESPN injury status | Already authenticated, no scraping |
| Positions | ESPN eligible positions | Neither ranking file has positions |
| Secrets | Repo-root `.env` only (git-ignored) | Only Python talks to ESPN, so there's one place to rotate an expired cookie |
| Regular season | A current-season term is added to the blend | See below |
| Git | Claude never commits; the user reviews and commits | User's rule |

## Valuation formula
Ported from `NBA_Top200_2026-27_Blended.md`. That file describes the method in words only, so the exact constants were reverse-engineered and are checked against all 200 rows in `data-job/tests/test_blend.py`.

```
FP        = PTS + 1.2·REB + 1.5·AST + 3·STL + 3·BLK − TOV        (generic)
w(src)    = max_weight · min(GP_src / full_gp, 1)
blend     = Σ w(src)·FP_src + prior_weight·prior_fp
            ─────────────────────────────────────────
                     Σ w(src) + prior_weight
Score     = blend · (0.85 + 0.15 · min(GP_last / 65, 1))         (availability)
```

| Source | max_weight | full_gp | Notes |
|---|---|---|---|
| 2025-26 regular season | 0.8 | 70 | from the file |
| 2026-27 preseason | 0.2 | 3 | from the file |
| **2026-27 regular season** | **1.6** | **41** | **new, proposed; review** |
| prior (15 FP/G) | 0.15 | n/a | inferred from the file's numbers |

**Current-season term.** With 0 games it contributes nothing, so the output equals the original file. As games accumulate its weight ramps up linearly. At the halfway point (41 GP) it's about 58% of the blend (1.6 / 2.75), and last season drops to about 29%. The constants are config (`BlendConfig`), not code.

**League Score** (Phase 1c): the same blend, but FP is computed with the ESPN league's point weights, and `prior_fp` is rescaled to the league's FP scale.

## Phases
0. Repo scaffolding: done
1a. Scoring + blend formulas + tests: done
1b. nba_api pulls (2025-26 regular, 2026-27 preseason and regular) → snapshot: done
1c. ESPN: league settings, scoring weights, rosters, FAs, matchup, injuries, positions → League Score
2a. .NET API: EF model, snapshot importer, `/rankings`, `/players/{id}`
2b. `/league`, `/my-team`, `/waivers`, `/matchup/current`, `/refresh`
3a. Angular rankings table + detail panel
3b. My team, waivers, matchup, refresh button
4. README completion

## Open items
- Availability still uses 2025-26 GP. Once the regular season is a few weeks in, consider using the current-season games-missed rate instead. **Waiting on owner decision** (raised in 1b).
- Preseason weight: a player who skipped preseason and then plays 2–3 low-minute games can drop up to ~3 points (e.g. Keegan Murray 22.1 → 18.8). This is how the file's formula behaves; flagged for owner review.
