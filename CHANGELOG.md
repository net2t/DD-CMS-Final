# DD-CMS-V3 Changelog

All notable changes from V2 → V3 are documented here.

---

## [v3.0.0] — 2026-02-23

### Project Structure
- Moved to clean new repo: `DD-CMS-V3`
- Root has only: `run.py`, `CHANGELOG.md`, `.gitignore`, `.env.sample`, `requirements.txt`
- All logic organized into `core/`, `config/`, `phases/`, `utils/`, `docs/`, `logs/`
- `core/` is fully locked — AI and contributors must not modify these files

### New Features

#### Overlap Lock System
- `run.lock` file created at run start, deleted at finish
- If Online Mode scheduler ticks while a run is active → tick is **skipped** (no cancellation, no overlap)
- Manual runs also check the lock — won't start if another run is active
- If a run crashes: delete `run.lock` manually to reset

#### Online Mode Scheduler
- `python run.py scheduler` starts Online Mode every 15 minutes automatically
- No overlap: if previous run is still going, next tick is skipped silently
- Ctrl+C or SIGTERM stops the scheduler cleanly

#### Manual Run Buttons (CLI)
- `python run.py online` — run Online Mode once
- `python run.py target` — run Target Mode once
- `python run.py online --limit 20` — limit profiles per run
- `python run.py scheduler --limit 50` — scheduler with profile cap

### Bug Fixes

#### Batch Mode Fixed (Critical)
- **Old behavior**: All profiles scraped first → all written to sheet at end (lost data on crash)
- **New behavior**: Each profile is written to sheet IMMEDIATELY after scraping
- RunList is marked "Done" right after each profile — crash-safe

#### Row Move to Row 2 — Fixed
- After scraping any profile (new or existing), it is moved to Row 2 of Profiles sheet
- Uses Google Sheets `moveDimension` API — one call, no delete/insert overhead
- In-memory cache updated correctly after each move

#### Duplicate Check — Fixed
- On-demand single-row fetch (not full sheet read on every check)
- Cache stays in sync because writes are per-profile (not batched)

#### Column Mapping — Fixed
- **Col 9 (LIST)**: RunList Col F value goes here (Target mode) or empty (Online mode)
  - Previously was called "STATUS" or "SKIP/DEL" — now renamed to "LIST"
- **Col 11 (RUN MODE)**: "Online" or "Target" — previously was broken/mixed with status
- **Col 9 (STATUS old)** no longer used for verified/unverified — unverified profiles are skipped entirely, no column needed

### Removals

#### OnlineLog Sheet — Removed
- No more OnlineLog sheet or any reference to it
- Dashboard is the only run summary destination

#### Dashboard Folder — Removed
- Removed internal dashboard folder and all references
- Dashboard = the Google Sheet tab only

#### Formatting — Removed
- No auto-formatting (color, bold, row highlighting) applied during scraping
- Only header row gets Quantico white font on sheet init
- This significantly speeds up runs

### Column Changes (Profiles Sheet)
```
Index  Old Name      New Name     Notes
─────  ────────────  ───────────  ───────────────────────────────────────────
9      STATUS        LIST         RunList Col F value (Target) / empty (Online)
11     SKIP/DEL      RUN MODE     "Online" or "Target"
```

### Sort
- Profiles sheet sorted by DATETIME SCRAP (Col M / index 12) **descending** at end of each run
- Most recently scraped profile appears at top
- Implemented via Google Sheets `sortRange` API (one batch call)

### Last Post Page
- Set to `?page=1` (was `?page=4` — reduced to minimize API usage)
- Controlled by `LAST_POST_FETCH_PUBLIC_PAGE` env var (default: false = fast mode)

### Defaults
- `BATCH_SIZE = 50` (default)
- `MAX_PROFILES_PER_RUN = 0` (unlimited by default)
- `MIN_DELAY = 0.3s`, `MAX_DELAY = 0.5s` between profile requests

### Core Lock Policy
- `core/CORE_LOCK.md` documents which files must not be modified
- All core files (`browser_manager.py`, `login_manager.py`, `run_context.py`) have lock headers
- Start and Login are confirmed working — not touched in V3
