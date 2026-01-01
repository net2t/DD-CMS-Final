# Changelog

All notable changes to this project will be documented in this file.

---

## [2.100.0.18] - 2026-01-02

### ✅ Fixed

- **Profiles sheet**: Column L header display updated to **RUN MODE**.
- **IMAGE**: Profile photo URL extraction now prefers real avatar image (cloudfront/avatar-imgs) and ignores placeholder `og_image.png`.
- **Sheets**: Header formatting now uses the same 429 retry/backoff wrapper as other write operations.

### 🔧 Changed

- **GitHub Actions**: Removed optional backup secret references from workflows to eliminate invalid-context warnings.

## [2.100.0.17] - 2025-12-30

### ✅ Fixed

- **Profile Phase**: Last post text/time now scraped from the public profile page when private profile has no preview.
- **Profile Phase**: Improved POSTS count extraction with additional selector fallbacks.
- **Sheets**: Removed inline "Before/Now" diff text being written into cells (keeps sheet data clean).
- **Sheets**: Preserve existing values for POSTS/LAST POST/LAST POST TIME when a scrape returns blanks (prevents wiping good data).

### 🔧 Changed

- **Mode Logging**: Online runs no longer show "TARGET MODE" banners; runner logs are now mode-aware.
- **GitHub Actions**: Online schedule set to every 15 minutes; Target schedule set to every 55 minutes.

## [2.100.0.16] - 2025-12-28

### 🚀 Improvements

- **Pending-only Target Selection:** Now only rows with 'pending' in Col B are processed in Target mode; 'Error', 'Done', etc. are always skipped.
- **Literal Nickname Handling:** No changes are made to nicknames (including @ and special characters). URLs and scraping use the exact value from the sheet.
- **Auto GitHub Workflow:** After every successful run, all files are committed and merged to `main` (or a branch) for full traceability.
- **Docs:** Minor clarifications in README and workflow description.

---

## [2.100.0.15] - 2025-12-26

### 🎉 Major Release - Production Ready

This release fixes all critical data extraction issues and enhances the entire system for production deployment.

### ✅ Fixed - Data Extraction (Critical)

- **FOLLOWERS Extraction**: Restored working selectors from old codebase
  - Primary selector: `//a[contains(@href, '/followers/')]/b`
  - Fallback selectors added for resilience
  - Now extracts follower count correctly
  
- **POSTS Extraction**: Fixed multiple selector strategies
  - Primary: `//a[contains(@href, '/posts/')]/b`
  - Alternative: `//a[contains(@href, '/profile/public/')]/button/div[1]`
  - CSS fallback: `a[href*='/profile/public/'] button div:first-child`
  
- **LAST POST & LAST POST TIME**: Completely restored
  - Added `_scrape_recent_post()` method from old code
  - Navigates to `/profile/public/{nickname}` to fetch latest post
  - Extracts post URL and normalized timestamp
  
- **IMAGE (Profile Picture)**: Fixed with multiple fallbacks
  - Primary: `//img[contains(@class, 'dp')]`
  - Fallbacks: avatar-imgs, cloudfront.net selectors
  - Removes `/thumbnail/` from URLs for full resolution
  
- **RURL (Rank Star)**: Maintained working regex extraction
  - Extracts star image URL from page source
  - Identifies Red/Gold/Silver star ranks
  
- **MEH (Mehfil) Data**: Fixed CSS selectors
  - MEH NAME: `div.ow`
  - MEH TYPE: `div[style*='background:#f8f7f9']`
  - MEH LINK: Href from parent anchor
  - MEH DATE: `div.cs.sp` with date normalization

### ✅ Fixed - Column Management

- **Removed INTRO Column**: Deleted from `COLUMN_ORDER` (was position 11)
- **Dashboard Simplified**: Removed state count columns (L, M, N, O)
  - Removed: ACTIVE, UNVERIFIED, BANNED, DEAD counts
  - Kept: Run#, Timestamp, Profiles, Success, Failed, New, Updated, Unchanged, Trigger, Start, End

### ✅ Fixed - Font Formatting

- **Quantico Font Applied to ALL Rows**: Previously only headers had Quantico font
  - `_apply_row_format()` now called on every profile write
  - Applies to both new profiles and updated profiles
  - Consistent formatting across all sheets

### ✅ Enhanced - Login System

- **Cookie Persistence**: Implemented for local runs
  - Saves session cookies after successful login
  - Loads cookies on next run for instant authentication
  - Skipped in GitHub Actions (no file persistence)
  
- **Dual Account System**: Automatic failover
  - Primary account tries cookie login first
  - Falls back to fresh login if cookies fail
  - Automatically switches to backup account if primary fails
  - Prevents account blocking from repeated logins
  
- **Smart Login Flow**:

  ```
  1. Try cookie login (local only)
  2. Try primary account fresh login
  3. Try backup account fresh login
  4. Save cookies on success
  ```

### ✅ Enhanced - Terminal UI

- **Rich Library Integration**: Beautiful colored output
  - Color-coded log levels (INFO=cyan, OK=green, ERROR=red)
  - Emoji icons for each log type (🔍 SCRAPING, 🔑 LOGIN, ✅ OK, ❌ ERROR)
  
- **Animated Header**: Eye-catching start banner
  - Double-bordered panel with title
  - Version and credits displayed
  - Animated border drawing
  
- **Summary Tables**: Professional end-of-run reports
  - Rich Table with color-coded metrics
  - Duration breakdown (minutes + seconds)
  - Status icons (✅/❌) for quick visual feedback
  
- **Progress Indicators**: Real-time progress display
  - Shows current/total profiles being processed
  - Displays success/failure counts live

### ✅ Enhanced - GitHub Actions

- **Target Mode Workflow**: Manual trigger with inputs
  - Input: `max_profiles` (0 = all pending)
  - Input: `batch_size` (default: 20)
  - Uses both primary and backup accounts
  - Uploads logs as artifacts
  
- **Online Mode Workflow**: Auto-scheduled every 15 minutes
  - Cron: `*/15 * * * *`
  - Limits to 30 profiles per run (prevents timeouts)
  - Also supports manual trigger for testing
  - Rate-limited for stability

### ✅ Enhanced - Error Handling

- **API Rate Limit Resilience**: Automatic retry with exponential backoff
  - Catches 429 errors from Google Sheets API
  - Waits 60/120/180 seconds before retry
  - Prevents data loss from rate limiting
  
- **Selector Fallbacks**: Multiple strategies for each field
  - 3+ selector patterns per data point
  - Tries XPath, CSS, and regex approaches
  - Logs warnings but continues on failure

### 📝 Changed - Code Organization

- **Modular Phase System**: Prepared for future expansion
  - `phases/phase_profile.py` - Profile scraping orchestrator
  - `phases/phase_mehfil.py` - Stub for Mehfil phase
  - `phases/phase_posts.py` - Stub for Posts phase
  
- **Centralized Selectors**: All in `config/selectors.py`
  - ProfileSelectors class for profile page
  - OnlineUserSelectors for online users page
  - LoginSelectors for login page
  
- **URL Builder Utility**: Single source of truth for URLs
  - `get_profile_url(nickname)`
  - `get_public_profile_url(nickname)`
  - Easy to update if site structure changes

### 📚 Documentation

- **Enhanced README.md**: Complete production-ready guide
  - Quick start instructions (5 minutes)
  - GitHub Actions setup guide
  - Troubleshooting section
  - Architecture diagram
  - Terminal output examples
  
- **Updated CHANGELOG.md**: This file
  - Detailed version history
  - Breaking changes clearly marked
  - Migration guides included

### 🔧 Configuration Changes

- **COLUMN_ORDER Updated**:

  ```python
  # Old (24 columns including INTRO)
  ["ID", "NICK NAME", ..., "INTRO", ..., "PROFILE_STATE"]
  
  # New (23 columns, INTRO removed)
  ["ID", "NICK NAME", ..., "PROFILE_STATE"]
  ```

- **Dashboard Headers Simplified**:

  ```python
  # Old (15 columns)
  [..., "Trigger", "Start", "End", "Active", "Unverified", "Banned", "Dead"]
  
  # New (11 columns)
  [..., "Trigger", "Start", "End"]
  ```

### ⚠️ Breaking Changes

- **INTRO Column Removed**: If you have existing sheets with INTRO data, it will be ignored
- **Dashboard Format Changed**: Old dashboard data incompatible (create new sheet or manually remove columns L-O)

### 🐛 Known Issues

- None reported in this version

### 🔮 Coming Soon

- Phase 2: Posts scraping
- Phase 3: Comments scraping
- Phase 4: Advanced Mehfil scraping
- Phase 5: JSON-based custom phases

---

## [2.100.0.14] - 2025-12-25

### Fixed

- **Sheet Formatting**: Corrected an issue where the 'Quantico' font was only applied to headers and not to data rows.
- **Scraping Logic**: Restored scraping logic for several blank columns, including `FOLLOWERS`, `POSTS`, `LAST POST`, `IMAGE`, and all `MEHFIL` data.
- **Selectors**: Fixed an `InvalidSelectorException` by converting incorrect XPath selectors to the proper CSS selector format for the Mehfil section.
- **Mode Consistency**: Refactored the `online` mode to use the same centralized `ProfileScraper` as the `target` and `test` modes, ensuring all fixes are applied consistently.

---

## [2.100.0.13] - 2025-12-25

### Added

- Created a `CHANGELOG.md` to track versions and fixes.
- Modernized terminal output with the `rich` library for better readability.
- Centralized UI components in `utils/ui.py`.
- Unified profile scraping logic under a new `phase_profile.py` orchestrator.

### Changed

- **Major Refactor**: Overhauled the entire project structure for clarity and maintainability.
- Migrated core logic into `core`, `phases`, `utils`, and `config` directories.
- **SheetsManager Overhaul**: Rewrote `utils/sheets_manager.py` to handle nickname-based duplicates with an inline diff format, move new/updated profiles to the top, and manage API rate limits gracefully.
- Updated `config/config_common.py` with new sheet names (`Profiles`, `RunList`) and a streamlined column order.
- Refactored `main.py` to use the new phase-based architecture and modernized UI.

### Removed

- Deleted legacy files: `Scraper.py`, `scraper_online.py`, `scraper_target.py`, `sheets_manager.py`.
- Removed all "BLANK" value logic in favor of empty strings.
- Removed redundant logging functions from individual modules.

### Fixed

- Corrected a `ValueError` in the online mode runner.

---

## [2.0.0] - 2025-12-20

### Added

- Initial refactored version with modular architecture
- Dual mode support (Target and Online)
- Google Sheets integration
- Basic profile scraping functionality

### Changed

- Complete rewrite from v1.x
- New project structure
- Improved error handling

---

## [1.0.0] - 2025-12-01

### Added

- Initial release
- Basic scraping functionality
- Single-mode operation
- Manual configuration

---

**For detailed changes between versions, see the Git commit history.**
