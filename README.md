# DamaDam Scraper v2.100.0.15 - Production Ready

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
[![Contact](https://img.shields.io/badge/contact-net2outlawzz@gmail.com-brightgreen)](mailto:net2outlawzz@gmail.com)
[![Social](https://img.shields.io/badge/social-@net2nadeem-blueviolet)](https://instagram.com/net2nadeem)

🚀 **Complete automation bot for scraping DamaDam.pk user profiles** with enhanced UI, dual login system, and multi-mode operation.

---

## 🎯 What's New in v2.100.0.16

### 🚀 Improvements

- **Pending-only Target Selection:** Only rows with 'pending' in Col B are processed in Target mode; 'Error', 'Done', etc. are always skipped.
- **Literal Nickname Handling:** Nicknames (including @ and special characters) are used as-is for scraping and URLs. No modification.
- **Auto GitHub Workflow:** After every successful run, all files are committed and merged to `main` (or a branch) automatically.

---

## 🎯 What's New in v2.100.0.15

### ✅ **FIXED Issues**

- ✅ **Missing Data Extraction**: Restored all working selectors
  - FOLLOWERS count now extracted correctly
  - POSTS count now extracted correctly
  - LAST POST and LAST POST TIME fully working
  - IMAGE (profile picture) extraction fixed
  - RURL (rank star) extraction restored
  - MEH (Mehfil) data extraction working
  
- ✅ **Column Management**
  - Removed INTRO column (Column L) as requested
  - Removed Dashboard state columns (L, M, N, O)
  
- ✅ **Font Formatting**
  - "Quantico" font now applied to **ALL rows** (not just headers)
  - Consistent formatting across all sheets
  
- ✅ **Enhanced Login System**
  - Cookie-based session persistence (local runs)
  - Automatic backup account failover
  - GitHub Actions compatibility (no cookies needed)
  
- ✅ **Beautiful Terminal UI**
  - Emojis and colors for better readability
  - Progress indicators with animations
  - Comprehensive summary reports
  
- ✅ **GitHub Workflows**
  - **Target Mode**: Manual trigger with options
  - **Online Mode**: Auto-scheduled every 15 minutes

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
# Primary Account (Required)
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password

# Backup Account (Recommended - prevents blocking)
DAMADAM_USERNAME_2=backup_username
DAMADAM_PASSWORD_2=backup_password

# Google Sheets
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

**C. Add Google Service Account:**

1. Download `credentials.json` from Google Cloud Console
2. Place it in the project root directory
3. Share your Google Sheet with the service account email

### 3. Run Locally

```bash
# Target Mode (from 'RunList' sheet)
python main.py target --max-profiles 10

# Online Mode (from online users)
python main.py online --max-profiles 20

# Unlimited (all pending targets)
python main.py target --max-profiles 0
```

---

## 📋 Features

### 🎯 **Multi-Mode Scraping**

- **Online Mode**: Scrapes currently online users (auto-scheduled every 15 min)
- **Target Mode**: Scrapes from 'RunList' sheet (manual trigger)
- **Test Mode**: Quick testing with predefined profiles

### 🔐 **Robust Authentication**

- Cookie-based session persistence (faster login)
- Dual account system with automatic failover
- Prevents account blocking from repeated logins
- GitHub Actions ready (no file persistence needed)

### 📊 **Smart Data Handling**

- Nickname-based duplicate detection
- Inline diffs for changed data
- Profile state tracking (ACTIVE, UNVERIFIED, BANNED, DEAD)
- Automatic sorting by scrape date

### 🎨 **Modern Terminal UI**

- Rich color-coded output with emojis
- Progress bars with animations
- Comprehensive summary reports
- Beautiful formatted tables

### 🛡️ **Resilient & Scalable**

- API rate limit handling with retries
- Session timeout recovery
- Minor HTML change tolerance
- Centralized configuration

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DAMADAM_USERNAME` | ✅ Yes | - | Primary DamaDam login username |
| `DAMADAM_PASSWORD` | ✅ Yes | - | Primary DamaDam login password |
| `DAMADAM_USERNAME_2` | ⚠️ Recommended | - | Backup account username (prevents blocking) |
| `DAMADAM_PASSWORD_2` | ⚠️ Recommended | - | Backup account password |
| `GOOGLE_SHEET_URL` | ✅ Yes | - | Your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | No | - | (Optional) Raw JSON for GitHub Actions |
| `MAX_PROFILES_PER_RUN` | No | 0 | Max profiles per run (0 = unlimited) |
| `BATCH_SIZE` | No | 20 | Batch size for processing |

### Google Sheets Setup

**Required Sheets:**

1. **Profiles** - Main profile data storage
2. **RunList** - Queue for target mode
3. **OnlineLog** - Log of all users seen online
4. **Dashboard** - High-level run statistics
5. **Tags** (optional) - Tag-to-user mappings

**RunList Sheet Format:**

| Nickname | Status | Remarks | Source |
|---|---|---|---|
| user123 | ⚡ Pending | | Target |
| user456 | Done 💀 | Profile updated | Target |

---

## 🤖 GitHub Actions Setup

### 1. Add Repository Secrets

Go to **Settings → Secrets and variables → Actions** and add:

- `DAMADAM_USERNAME` - Primary account username
- `DAMADAM_PASSWORD` - Primary account password
- `DAMADAM_USERNAME_2` - Backup account username *(recommended)*
- `DAMADAM_PASSWORD_2` - Backup account password *(recommended)*
- `GOOGLE_SHEET_URL` - Your Google Sheet URL
- `GOOGLE_CREDENTIALS_JSON` - Full JSON content of `credentials.json`

### 2. Workflows

#### **Target Mode (Manual)**

- Navigate to **Actions → Target Mode Scraper**
- Click **Run workflow**
- Set options:
  - `max_profiles`: 0 = all pending, or specify number
  - `batch_size`: Processing batch size (default: 20)

#### **Online Mode (Automatic)**

- Runs every 15 minutes automatically
- Can also trigger manually for testing
- Recommended `max_profiles`: 20-50 (to avoid timeouts)

---

## 🏗️ Project Architecture

```
DD-CMS-Final/
├── .github/workflows/          # GitHub Actions
│   ├── scrape-target.yml      # Manual target mode
│   └── scrape-online.yml      # Scheduled online mode
├── config/                     # Configuration files
│   ├── config_common.py       # Main config (FIXED columns)
│   ├── config_online.py       # Online mode config
│   ├── config_target.py       # Target mode config
│   └── selectors.py           # CSS/XPath selectors
├── core/                       # Core components
│   ├── browser_manager.py     # Browser setup
│   ├── login_manager.py       # Login with cookies (FIXED)
│   └── run_context.py         # Shared run state
├── phases/                     # Scraping phases
│   ├── phase_profile.py       # Profile phase orchestrator
│   └── profile/               # Profile scraping logic
│       ├── online_mode.py     # Online mode runner
│       └── target_mode.py     # Target mode runner (FIXED)
├── utils/                      # Utilities
│   ├── sheets_manager.py      # Google Sheets (FIXED fonts)
│   ├── ui.py                  # Terminal UI (ENHANCED)
│   └── url_builder.py         # URL construction
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 📊 Data Columns

**Fixed Column Order (INTRO removed):**

| # | Column | Description |
|---|--------|-------------|
| 0 | ID | User ID |
| 1 | NICK NAME | Nickname |
| 2 | TAGS | Tags from Tags sheet |
| 3 | CITY | City |
| 4 | GENDER | Male/Female |
| 5 | MARRIED | Yes/No |
| 6 | AGE | Age |
| 7 | JOINED | Join date |
| 8 | FOLLOWERS | Follower count (FIXED) |
| 9 | STATUS | Normal/Banned/Unverified |
| 10 | POSTS | Post count (FIXED) |
| 11 | SOURCE | Online/Target |
| 12 | DATETIME SCRAP | Scrape timestamp |
| 13 | LAST POST | Last post URL (FIXED) |
| 14 | LAST POST TIME | Last post time (FIXED) |
| 15 | IMAGE | Profile image URL (FIXED) |
| 16 | PROFILE LINK | Profile URL |
| 17 | POST URL | Public posts URL |
| 18 | RURL | Rank star image (FIXED) |
| 19-22 | MEH NAME/TYPE/LINK/DATE | Mehfil data (FIXED) |
| 23 | PROFILE_STATE | ACTIVE/UNVERIFIED/BANNED/DEAD |

---

## 🎨 Terminal Output Examples

### Header

```
================================================================================
🚀 DamaDam Scraper - TARGET MODE 🚀
Version: v2.100.0.15
Powered by Selenium + Google Sheets
================================================================================
```

### During Run

```
12:34:56 🔐 [LOGIN] Attempting cookie-based login...
12:34:58 ✅ [OK] Cookie login successful
12:35:00 🔍 [SCRAPING] Scraping: user123
12:35:02 ✅ [OK] user123: new
```

### Summary Report

```
📊 Scraping Run Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Metric                 ┃         Value ┃   Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 🎯 Mode                │        TARGET │          │
│ ✅ Successful          │            45 │       ✅ │
│ ❌ Failed              │             2 │       ❌ │
│ 🆕 New Profiles        │            38 │          │
│ 🔄 Updated Profiles    │             7 │          │
│ ⏱️ Duration            │      3m 42s │       ⚡ │
└────────────────────────┴───────────────┴──────────┘
```

---

## 🔄 Future Phases (Coming Soon)

The scraper is designed for easy extension:

- **Phase 2**: Posts scraping (individual posts)
- **Phase 3**: Comments scraping
- **Phase 4**: Mehfil (group) scraping
- **Phase 5**: Custom phases via JSON config

---

## 🐛 Troubleshooting

### Missing Data in Sheets

**Issue**: FOLLOWERS, POSTS, IMAGE, etc. showing blank

**Solution**: ✅ **FIXED in v2.100.0.15** - All selectors restored

### Cookie Login Fails

**Issue**: "Cookie login failed" message

**Solution**: Delete `damadam_cookies.pkl` and run again. Fresh login will create new cookies.

### GitHub Actions Rate Limits

**Issue**: API quota exceeded errors

**Solution**: Reduce `max_profiles` or increase delay in config:

```python
SHEET_WRITE_DELAY = 2.0  # Increase from 1.0
```

### Account Blocked Warning

**Issue**: "Too many login attempts"

**Solution**: ✅ Use backup account (set `DAMADAM_USERNAME_2` and `DAMADAM_PASSWORD_2`)

---

## ✨ Credits

**Developed by:**

- **Author**: Nadeem
  - **Email**: `net2outlawzz@gmail.com`
  - **Social**: `@net2nadeem` (Instagram, Facebook)
- **AI Pair Programmer**: Claude (Anthropic)

---

## 📄 License

This project is for educational purposes only. Please respect the website's terms of service.

---

## 🆘 Support

For issues, questions, or feature requests:

- **Email**: <net2outlawzz@gmail.com>
- **Instagram**: @net2nadeem
- **Issues**: [GitHub Issues](https://github.com/net2t/DD-CMS-Final/issues)

---

**Happy Scraping! 🚀**
