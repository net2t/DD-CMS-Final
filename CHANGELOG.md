# Changelog

All notable changes are listed here. Newest version at the top.

---

## [v3.0.2] — 2026-03-24

### Bug Fixes & Improvements

---

#### Fix 1 — Batch Writes Not Working (Speed)

**Problem:**
500 profiles in Target Mode were taking 20+ minutes and hitting Google Sheets API rate limits (429 errors). Scraping was stalling every few profiles.

**Root cause:**
`flush_batch()` existed but was always called with an empty buffer. The function `_queue_batch_update()` was defined but never called anywhere in the codebase. Every profile was being written one-by-one via individual API calls.

**Fix:**
All data cell writes are now queued via `_queue_row_data()` and flushed in one Sheets API `batchUpdate` call every `BATCH_SIZE` profiles. `moveDimension` (row move to top) still happens immediately per profile because the Sheets API requires it to be real-time. After every flush, the nickname→row cache is reloaded from the sheet to keep row numbers accurate.

**Files changed:**
- `utils/sheets_manager.py` — replaced `_queue_batch_update()` with `_queue_row_data()` and `_queue_cell_note()`; fixed `flush_batch()` to actually send queued requests
- `phases/profile/target_mode.py` — final `flush_batch()` call guaranteed at end of run

---

#### Fix 2 — Post Count Missing (Col K)

**Problem:**
Col K (POSTS) was frequently blank even for active users.

**Root cause:**
The XPath selector `//a[contains(@href, '/posts/')]/b` silently returns empty when the `<b>` tag is absent or the HTML structure varies. The single regex fallback (`[\d,\.]+\s+posts?`) was too narrow to catch all DamaDam page layouts. Additionally, `POSTS` was not in `_PRESERVE_IF_BLANK`, so a blank scrape result would overwrite a previously correct value.

**Fix:**
Added 3 additional regex fallback patterns to `_extract_stats()` covering different HTML structures. Added `POSTS` to `_PRESERVE_IF_BLANK` so if the scraper returns blank, the last known value is kept.

**Files changed:**
- `phases/profile/target_mode.py` — `_extract_stats()` method
- `utils/sheets_manager.py` — `_PRESERVE_IF_BLANK` set

---

#### Fix 3 — Duplicate Rows Being Inserted

**Problem:**
Running "Remove Duplicates" from the sheet was deleting 20–30 rows after every run, meaning duplicates were being created on every run.

**Root cause:**
The in-memory nickname→row cache went out of sync after batch flushes. When `insert_row` adds a new profile at Row 2, all existing row numbers shift down by 1. The cache wasn't being refreshed, so subsequent duplicate checks used stale row numbers, causing `_get_existing_record()` to return `None` for profiles that actually existed — and they were inserted again.

**Fix:**
After every `flush_batch()` call, `_load_existing_profile_rows()` is called to reload the full nickname→row mapping from the actual sheet. The `_cache_insert_at_top()` and `_cache_update_after_move()` methods are also corrected to shift rows accurately during a run.

**Files changed:**
- `utils/sheets_manager.py` — `flush_batch()`, `_cache_insert_at_top()`, `_cache_update_after_move()`

---

#### Fix 4 — Both Modes Running Simultaneously

**Problem:**
Online Mode (auto, every 15 min) and Target Mode (manual trigger) were sometimes running at the same time, causing data corruption and API conflicts.

**Root cause:**
Both workflow files had different `concurrency` groups (`dd-cms-online` and `dd-cms-target`). GitHub Actions concurrency only prevents overlap within the same group. Different groups run freely in parallel on separate VMs that don't share any state — including the `run.lock` file.

**Fix:**
Both workflow files now use the same concurrency group `dd-cms` with `cancel-in-progress: false`. GitHub Actions will queue the second mode and wait for the first to finish before starting it. No run is cancelled — it just waits.

**Files changed:**
- `.github/workflows/online-schedule.yml` — `concurrency.group` changed from `dd-cms-online` → `dd-cms`
- `.github/workflows/target-manual.yml` — `concurrency.group` changed from `dd-cms-target` → `dd-cms`

---

#### Fix 5 — Change Detection Note Not Written

**Problem:**
The scraper detected which fields changed between runs but never recorded it anywhere visible.

**Fix:**
When any tracked field changes (City, Age, Followers, Posts, Gender, Married, Tags, Mehfil data, etc.), a Google Sheets **cell note** is written on the NICK NAME cell (Col B). Open it with **Shift+F2** or hover over the cell to see the before/after values and the timestamp of the change.

Columns excluded from change detection (always changing or irrelevant): ID, NICK NAME, JOINED, DATETIME SCRAP, LAST POST, LAST POST TIME, PROFILE LINK, POST URL, PHASE 2, RUN MODE, LIST.

**Files changed:**
- `utils/sheets_manager.py` — `_build_change_note()`, `_queue_cell_note()`, `write_profile()`

---

#### Fix 6 — RunList Col D Ignore Flag Not Working

**Problem:**
Users added a value in RunList Col D to mark profiles as "ignore / do not scrape" but the scraper was processing them anyway.

**Root cause:**
`get_pending_targets()` only read Col A (nickname), Col B (status), and Col F (tag). Col D was never read.

**Fix:**
`get_pending_targets()` now reads Col D. Any row with any value in Col D is silently skipped with a log entry. Leave Col D empty for normal scraping.

**Files changed:**
- `utils/sheets_manager.py` — `get_pending_targets()`

---

#### Fix 7 — Row Not Always Moving to Top

**Problem:**
After scraping, profiles were not consistently appearing at Row 2 (top of sheet).

**Root cause:**
The cache update functions `_cache_insert()` and `_cache_move_to_top()` had incorrect shift logic. When two profiles were processed in quick succession, the second `moveDimension` call used a stale row number from the cache, causing it to move the wrong row or fail silently.

**Fix:**
Replaced both cache functions with `_cache_insert_at_top()` and `_cache_update_after_move()` with corrected shift direction and range. Every scraped profile (whether data changed or not) now reliably moves to Row 2.

**Files changed:**
- `utils/sheets_manager.py` — `_cache_insert_at_top()`, `_cache_update_after_move()`, `write_profile()`

---

**Migration:**
No migration script needed. Replace the 4 files and push. The sheet structure is unchanged.

---

## [v3.0.1] — 2026-03-08

### Bug Fix — Profiles Sheet Showing Old Dates

**Problem:**
The Profiles sheet appeared to stop updating after 01-Mar-2026. Data was actually being written correctly every 15 minutes, but the sort at the end of each run was reordering rows incorrectly — making old rows float to the top and hiding fresh data.

**Root cause:**
`DATETIME SCRAP` was stored as `08-Mar-26 05:00 PM`. Google Sheets' `sortRange` API sorts this as plain text, alphabetically. Alphabetical sort on this format compares the day number first (`01`, `02`... `31`), not the year or month. So `01-Apr-26` sorted above `31-Mar-26` — March entries disappeared below older data after every run.

**Fix:**
Changed `DATETIME SCRAP` format from `%d-%b-%y %I:%M %p` to `%Y-%m-%d %H:%M` (e.g. `2026-03-08 17:00`). This format sorts correctly as plain text because the year comes first.

**Files changed:**
- `utils/sheets_manager.py` — `_enrich_profile()` and `update_dashboard()` strptime
- `phases/profile/target_mode.py` — `scrape_profile()` timestamp stamp

**Migration:**
Run `python fix_datetime_format.py` once to convert all existing rows in your sheet from the old format to the new one. Only needs to be done once.

---

## [v3.0.0] — 2026-02-23

Complete rewrite from V2. New clean repo structure, all logic reorganized into modules.

### Structure Changes
- Root now contains only: `run.py`, `CHANGELOG.md`, `.gitignore`, `.env.sample`, `requirements.txt`
- All logic split into `core/`, `config/`, `phases/`, `utils/`, `docs/`
- `core/` is locked — browser and login code must not be modified

### New: Overlap Lock System
- `run.lock` file created at run start, deleted when run finishes
- If GitHub Actions triggers while a run is still going → new run is skipped (no overlap, no data corruption)
- If a run crashes and leaves a stale lock: manually delete `run.lock` to reset

### New: Online Mode Scheduler (local)
- `python run.py scheduler` runs Online Mode on your PC every 15 minutes
- Ctrl+C stops it cleanly

### Bug Fix: Data Lost on Crash (Critical)
- **Old behaviour:** All profiles scraped first, then written to sheet at the end → crash = all data lost
- **New behaviour:** Each profile is written to the sheet immediately after scraping → crash-safe

### Bug Fix: Row Movement
- Profile rows now move to Row 2 (top) after each scrape using Google Sheets `moveDimension` API
- Most recently scraped profile always appears first

### Bug Fix: Duplicate Detection
- Now uses on-demand single-row fetch instead of reading the full sheet on every check
- In-memory cache stays in sync with per-profile writes

### Column Changes (Profiles Sheet)

| Index | Old Name | New Name | Notes |
|---|---|---|---|
| 9 | STATUS | LIST | RunList Col F value (Target mode) or empty (Online mode) |
| 11 | SKIP/DEL | RUN MODE | "Online" or "Target" |

### Removed
- **OnlineLog sheet** — removed entirely. Dashboard is the only run summary destination
- **Auto-formatting** — no more colour/bold applied during scraping. Significantly speeds up runs. Only the header row gets Quantico white font on sheet initialisation
- Various unused files cleaned up (legacy configs, duplicate phase files, old dashboard HTML files)

### Defaults
- `BATCH_SIZE = 50`
- `MAX_PROFILES_PER_RUN = 0` (unlimited)
- `MIN_DELAY = 0.3s`, `MAX_DELAY = 0.5s`
- `PAGE_LOAD_TIMEOUT = 10s`

---

## [v2.100.0.19] — 2026-02-20

### Performance — Major Speed Improvements
- Browser now blocks image loading → saves 40–60% of page load time per profile
- Switched to `eager` page load strategy → browser stops waiting once DOM is ready
- `LAST_POST_FETCH_PUBLIC_PAGE` now defaults to `false` → saves 15–25 seconds per profile
- Reduced `PAGE_LOAD_TIMEOUT` from 30s → 20s
- Reduced `WebDriverWait` from 12s → 10s
- Added browser performance flags: disable-extensions, disable-sync, disable-notifications

**Result:** 100 profiles now takes ~20–35 min (was 2–3 hours)

### Cleanup
- Removed `utils/profile_cache.py` — never connected to scraper
- Removed `utils/validator.py` — replaced by inline validation in target_mode.py
- Removed `utils/retry.py` — decorators never applied
- Removed duplicate phase files
- Removed old dashboard HTML test files

---

## [v2.100.0.18] — 2026-01-02

### Fixed
- Profiles sheet Col L header updated to `RUN MODE`
- Removed `MEH TYPE` column (was causing formatting issues)
- Profile image extraction now prefers cloudfront avatar-imgs, ignores placeholder `og_image.png`
- Sheet header formatting now uses 429 retry/backoff wrapper
