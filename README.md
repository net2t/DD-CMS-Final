# 🤖 DamaDam Scraper — v2.100.0.18

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Phase 1](https://img.shields.io/badge/Phase%201-Complete-brightgreen.svg)]()
[![Target Mode](https://github.com/net2t/DD-CMS-Final/actions/workflows/scrape-target.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/scrape-target.yml)
[![Online Mode](https://github.com/net2t/DD-CMS-Final/actions/workflows/scrape-online.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/scrape-online.yml)

Scrapes user profiles from **DamaDam.pk** and saves everything to Google Sheets.
Runs automatically in the cloud via GitHub Actions — no server, no PC needed.

---

## How It Works

```
You add usernames to the RunList sheet
         ↓
GitHub Actions wakes up on schedule
         ↓
Opens Chrome (invisibly, in the cloud)
         ↓
Logs into DamaDam with your account
         ↓
Visits each profile, reads the data
         ↓
Writes everything to your Google Sheet
         ↓
Done — just check the sheet!
```

**Two modes:**
- **Target Mode** — You give a list of usernames, it scrapes them
- **Online Mode** — Checks who is online right now and scrapes those profiles (runs every 15 min automatically)

---

## Project Structure

```
DD-CMS-Final/
│
├── main.py                        ← Run this to start everything
├── requirements.txt               ← Python packages
├── .env.sample                    ← Copy this to .env and fill in your details
│
├── config/
│   ├── config_common.py           ← All main settings (timeouts, columns, delays)
│   ├── config_manager.py          ← Loads the right config per mode
│   ├── config_online.py           ← Online mode overrides
│   ├── config_target.py           ← Target mode overrides
│   ├── config_test.py             ← Test mode settings
│   ├── config_mehfil.py           ← Mehfil phase settings (future)
│   ├── config_posts.py            ← Posts phase settings (future)
│   └── selectors.py               ← CSS/XPath selectors for the website
│
├── core/
│   ├── browser_manager.py         ← Starts and controls Chrome
│   ├── browser_context.py         ← Safe browser lifecycle wrapper
│   ├── login_manager.py           ← Login with cookie + fallback system
│   └── run_context.py             ← Shared state for one run
│
├── phases/
│   ├── phase_profile.py           ← Phase 1 router (online/target/test)
│   ├── phase_posts.py             ← Phase 2 stub (future)
│   ├── phase_mehfil.py            ← Phase 3 stub (future)
│   └── profile/
│       ├── target_mode.py         ← Core scraper + target list runner
│       └── online_mode.py         ← Online users fetcher
│
├── utils/
│   ├── sheets_manager.py          ← All Google Sheets operations
│   ├── sheets_batch_writer.py     ← Batch writer (faster writes)
│   ├── ui.py                      ← Terminal display and logging
│   ├── url_builder.py             ← Builds profile URLs
│   ├── dynamic_dashboard.py       ← Dashboard update logic
│   └── metrics.py                 ← Run performance tracking
│
├── .github/workflows/
│   ├── scrape-online.yml          ← Runs every 15 minutes (auto)
│   └── scrape-target.yml          ← Manual trigger only
│
├── Dashboard/
│   ├── index.html                 ← Web dashboard UI
│   ├── styles.css
│   └── app.js
│
└── docs/
    ├── guides/                    ← Setup and troubleshooting guides
    └── meta/
        └── CHANGELOG.md           ← Version history
```

---

## Quick Start (Local)

### Requirements
- Python 3.9+
- Google Chrome
- Google account (for Sheets API)
- DamaDam.pk account (2 accounts recommended)

### Step 1 — Clone and install

```bash
git clone https://github.com/net2t/DD-CMS-Final.git
cd DD-CMS-Final
pip install -r requirements.txt
```

### Step 2 — Create your `.env` file

```bash
copy .env.sample .env      # Windows
cp .env.sample .env        # Mac/Linux
```

Open `.env` and fill in your credentials (see Configuration section below).

### Step 3 — Set up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Sheets API** + **Google Drive API**
3. Create a **Service Account** → Download `credentials.json`
4. Place `credentials.json` in the project folder
5. Create a Google Sheet and **share it** with the service account email
6. Your sheet needs these tabs (auto-created if missing): `Profiles`, `RunList`, `OnlineLog`, `Dashboard`

### Step 4 — Test

```bash
python main.py test --max-profiles 3
```

---

## Configuration

Your `.env` file:

```env
# DamaDam accounts
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password
DAMADAM_USERNAME_2=backup_username     # Recommended
DAMADAM_PASSWORD_2=backup_password

# Google Sheet (full URL from browser)
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_ID/edit

# Leave these as-is
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
PAGE_LOAD_TIMEOUT=20
SHEET_WRITE_DELAY=1.0

# Speed setting: false = fast (recommended), true = fetches more last post data
LAST_POST_FETCH_PUBLIC_PAGE=false
```

| Setting | Default | Description |
|---|---|---|
| `MAX_PROFILES_PER_RUN` | `0` | Max profiles per run (0 = unlimited) |
| `BATCH_SIZE` | `20` | Profiles per batch before pausing |
| `MIN_DELAY` / `MAX_DELAY` | `0.3` / `0.5` | Wait between profiles (seconds) |
| `PAGE_LOAD_TIMEOUT` | `20` | Give up loading after this many seconds |
| `SHEET_WRITE_DELAY` | `1.0` | Wait between sheet writes (avoids 429 errors) |
| `LAST_POST_FETCH_PUBLIC_PAGE` | `false` | Also check public page for last post data |

---

## Running the Scraper

```bash
# Scrape your RunList
python main.py target

# Limit to 50 profiles
python main.py target --max-profiles 50

# Scrape currently online users
python main.py online --max-profiles 30

# Quick test (3 profiles)
python main.py test
```

**RunList sheet format:**

| A: NICKNAME | B: STATUS | C: REMARKS | D: SKIP |
|---|---|---|---|
| user123 | ⚡ Pending | | |
| user456 | Done 💀 | Updated: 20-Feb-26 | |
| skipme | | | YES |

---

## GitHub Actions (Auto Mode)

### Setup — Add these 6 Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value |
|---|---|
| `DAMADAM_USERNAME` | Your DamaDam username |
| `DAMADAM_PASSWORD` | Your DamaDam password |
| `DAMADAM_USERNAME_2` | Backup username |
| `DAMADAM_PASSWORD_2` | Backup password |
| `GOOGLE_SHEET_URL` | Full URL of your Google Sheet |
| `GOOGLE_CREDENTIALS_JSON` | Paste entire content of `credentials.json` |

### Schedules

| Workflow | When | What |
|---|---|---|
| Online Mode | Every 15 minutes (auto) | Scrapes currently online users |
| Target Mode | Manual only | Processes your RunList |

### Manual Trigger

Repo → **Actions** → **Target Mode** → **Run workflow** → Set max profiles → **Run workflow**

---

## Phase System

| Phase | Status | What It Does |
|---|---|---|
| Phase 1 — Profiles | ✅ Complete | Scrapes full profile data (23 fields) |
| Phase 2 — Posts | 🔜 Planned | Scrapes posts from eligible profiles |
| Phase 3 — Mehfils | 🔜 Planned | Scrapes group data |
| Phase 4 — Comments | 🔜 Future | Scrapes comments |

**Phase 2 Eligibility:** A profile is marked `Ready` if it has fewer than 100 posts and status is Active.

---

## Data Collected Per Profile

ID, Nickname, Tags, City, Gender, Married, Age, Joined, Followers, Status, Posts, Run Mode, Scrape DateTime, Last Post URL, Last Post Time, Profile Image, Profile Link, Public Posts URL, Rank Star, Mehfil Names, Mehfil Links, Mehfil Dates, Phase 2 Eligibility

---

## Troubleshooting

**Login keeps failing**
```bash
del damadam_cookies.pkl
python main.py test --max-profiles 1
```

**Google Sheets 429 error (rate limit)**
Set `SHEET_WRITE_DELAY=2.0` in your `.env`

**No pending targets found in Target mode**
Check `RunList` sheet — column B must say exactly `⚡ Pending`

**GitHub Actions fails immediately**
Make sure all 6 secrets are added. `GOOGLE_CREDENTIALS_JSON` must include the full JSON starting with `{`

---

## Security

Never commit these files — they contain your passwords:
- `.env`
- `credentials.json`
- `damadam_cookies.pkl`

These are already in `.gitignore`. For GitHub Actions, always use Secrets.

---

## Author

**Nadeem** · [net2outlawzz@gmail.com](mailto:net2outlawzz@gmail.com) · [@net2nadeem](https://instagram.com/net2nadeem)
AI Assistant: Claude (Anthropic)
