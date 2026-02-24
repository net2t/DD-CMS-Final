# Changelog

All notable changes are documented here. Latest version is always at the top.

---

## [2.100.0.19] - 2026-02-20

### Performance — Major Speed Improvements

- **Browser now blocks image loading** — saves 40-60% of page load time per profile
- **Switched to `eager` page load strategy** — browser stops waiting once DOM is ready (no waiting for images/fonts/CSS)
- **Disabled last post public page fetch by default** — this alone saves 15-25 seconds per profile
  - New config flag: `LAST_POST_FETCH_PUBLIC_PAGE=false` (default)
  - Set to `true` in GitHub Secrets only if you need full last post data
  - New config: `LAST_POST_PUBLIC_PAGE_TIMEOUT=8` (was hardcoded 12s)
- **Reduced page load timeout** from 30s → 20s
- **Reduced WebDriverWait** from 12s → 10s in main scrape
- **Added browser performance flags**: disable-extensions, disable-sync, disable-notifications, no-first-run

**Expected improvement:** 100 profiles in ~20-35 min (was 2-3 hours)

### Cleanup — Removed Unused Files

- Removed `config/_legacy_config.py` (old unused version)
- Removed `core/_legacy_browser.py` (old unused version)
- Removed `utils/ui_fixed.py` (duplicate stubs, never imported)
- Removed `utils/profile_cache.py` (built but never connected to scraper)
- Removed `utils/validator.py` (replaced by inline validation in target_mode.py)
- Removed `utils/retry.py` (decorators never applied anywhere)
- Removed `phases/phase_online.py` (duplicate, phase_profile.py handles this)
- Removed `phases/phase_target.py` (duplicate, phase_profile.py handles this)
- Removed `netlify.toml` (not deploying to Netlify)
- Removed `render.yaml` (not deploying to Render)
- Removed `SECURITY.txt` (covered in README)
- Removed `Dashboard/index1-4.html` (old test versions)
- Removed `docs/meta/CONTRIBUTING.md` (unnecessary)
- Removed `docs/meta/project_rules.md` (unnecessary)

### Documentation

- Rewrote `README.md` from scratch — plain English, beginner-friendly
- Added How It Works diagram
- Added complete file structure reference
- Added RunList sheet format guide
- Simplified configuration table

---

## [2.100.0.18] - 2026-01-02

### Fixed

- **Profiles sheet**: Column L header updated to RUN MODE
- **Profiles sheet**: Removed MEH TYPE column (was causing formatting issues)
- **IMAGE**: Profile photo extraction now prefers cloudfront avatar-imgs, ignores placeholder og_image.png
- **Sheets**: Header formatting now uses 429 retry/backoff wrapper

### Changed

- **GitHub Actions**: Removed optional backup secret references to eliminate invalid-context warnings

---

## [2.100.0.17] - 2025-12-30

### Fixed

- **Profile Phase**: Last post text/time now scraped from public profile page when private profile has no preview
- **Profile Phase**: Improved POSTS count extraction with additional selector fallbacks
- **Sheets**: Removed inline Before/Now diff text being written into cells
- **Sheets**: Preserve existing values for POSTS/LAST POST/LAST POST TIME when scrape returns blanks

### Changed

- **Mode Logging**: Online runs no longer show TARGET MODE banners
- **GitHub Actions**: Online schedule set to every 15 min; Target to every 55 min

---

## [2.100.0.16] - 2025-12-28

### Improved

- Only rows with `⚡ Pending` in column B are processed in Target mode
- Nicknames are used exactly as written (no changes to special characters)
- Minor README and workflow clarifications

---

## [2.100.0.15] - 2025-12-26 — Production Ready Release

### Fixed (Critical)

- FOLLOWERS, POSTS, LAST POST, IMAGE, RURL, MEH data extraction all restored
- INTRO column removed from column order
- Dashboard simplified (removed state count columns)
- Quantico font now applied to all rows, not just headers

### Added

- Cookie-based login persistence for local runs
- Dual account failover system
- Rich terminal UI with colors and emojis
- Comprehensive summary tables at end of run
- GitHub Actions Target and Online workflows

---

## [2.100.0.14] - 2025-12-25

### Fixed

- Sheet formatting: Quantico font applied to data rows
- Scraping: Restored FOLLOWERS, POSTS, LAST POST, IMAGE, MEHFIL fields
- Selectors: Fixed InvalidSelectorException in Mehfil section
- Mode consistency: Online mode now uses same ProfileScraper as target/test

---

## [2.100.0.13] - 2025-12-25 — Major Refactor

### Added

- CHANGELOG.md created
- Rich library for terminal output
- Centralized UI in utils/ui.py
- phase_profile.py orchestrator

### Changed

- Full project restructured into core/, phases/, utils/, config/
- SheetsManager rewritten (nickname-based duplicates, rate limit handling)
- main.py rewritten with phase-based architecture

### Removed

- Legacy files: Scraper.py, scraper_online.py, scraper_target.py

---

## [2.0.0] - 2025-12-20

- Initial modular architecture
- Dual mode support (Target + Online)
- Google Sheets integration

---

## [1.0.0] - 2025-12-01

- Initial release
- Basic scraping, single mode, manual config
