# DamaDam Scraper v2.1 - Refactored

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
[![Contact](https://img.shields.io/badge/contact-net2outlawzz@gmail.com-brightgreen)](mailto:net2outlawzz@gmail.com)
[![Social](https://img.shields.io/badge/social-@net2nadeem-blueviolet)](https://instagram.com/net2nadeem)

Complete automation bot for scraping DamaDam.pk user profiles with a refactored, modular architecture and multi-mode operation.

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone & Install

```bash
git clone https://github.com/net2t/DD-CMS-Final.git
cd DD-CMS-Final
pip install -r requirements.txt
```

### 2. Setup Credentials

**A. Create `.env` file:**
```bash
cp .env.example .env
```

**B. Edit `.env` with your credentials:**
```env
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

**C. Add Google Service Account:**
1.  Download `credentials.json` from Google Cloud Console.
2.  Place it in the project root directory.
3.  Share your Google Sheet with the service account email (found in `credentials.json`).

### 3. Run

```bash
# Target Mode (from 'RunList' sheet)
python main.py target

# Online Mode (from online users)
python main.py online

# Test Mode (predefined list for testing)
python main.py test
```

---

## 📋 Features

-   **Multi-Mode Scraping**: `online`, `target`, and `test` modes for flexible operation.
-   **Smart Data Handling**: Nickname-based duplicate detection with inline diffs for changed data.
-   **Profile State Tracking**: Automatically categorizes profiles as `ACTIVE`, `UNVERIFIED`, `BANNED`, or `DEAD`.
-   **Modern UI**: Richly formatted terminal output for clear, readable logs.
-   **Resilient**: Handles API rate limits, session timeouts, and minor HTML changes.
-   **Centralized Configuration**: Easy-to-manage selectors and settings.

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DAMADAM_USERNAME` | ✅ Yes | - | DamaDam login username |
| `DAMADAM_PASSWORD` | ✅ Yes | - | DamaDam login password |
| `GOOGLE_SHEET_URL` | ✅ Yes | - | Your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | No | - | (Optional) Raw JSON for GitHub Actions |

### Google Sheets Setup

**Required Sheets:**
1.  **Profiles** - Main profile data is stored here.
2.  **RunList** - The queue for `target` mode.
3.  **OnlineLog** - A log of all users seen online.
4.  **Dashboard** - High-level statistics for each run.
5.  **Tags** (optional) - For mapping tags to users.

**RunList Sheet Format:**
| Nickname | Status | Remarks | Source |
|---|---|---|---|
| user123 | | | Target |

---

## 🏗️ Project Architecture

The project is organized into a modular structure for better maintainability.

-   `main.py`: Main entry point, handles argument parsing and orchestrates the run.
-   `config/`: Contains all configuration files, including common settings, selectors, and mode-specific configs.
-   `core/`: Holds core components like the `BrowserManager`, `LoginManager`, and `RunContext`.
-   `phases/`: Contains the logic for different scraping phases (`profile`, `mehfil`, `posts`).
    -   `profile/`: Includes the `ProfileScraper` and the runners for `online` and `target` modes.
-   `utils/`: Shared utilities for Google Sheets (`sheets_manager.py`), UI (`ui.py`), and URL building.

---

## ✨ Credits

This project was developed by:

-   **Author**: Nadeem
    -   **Email**: `net2outlawzz@gmail.com`
    -   **Social**: `@net2nadeem` (Instagram, Facebook, etc.)
-   **AI Pair Programmer**: Cascade

---

## 📄 License

This project is for educational purposes only. Please respect the website's terms of service.
