# Changelog

All notable changes to this project will be documented in this file.

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
