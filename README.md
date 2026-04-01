# DD-CMS-Final — DamaDam Profile Scraper

A Python scraper that automatically collects user profile data from [damadam.pk](https://damadam.pk) and writes it to a Google Sheet. Runs automatically every 15 minutes via GitHub Actions no PC needs to be on.

[![Online Mode (15 min)](https://github.com/net2t/DD-CMS-Final/actions/workflows/online-schedule.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/online-schedule.yml)
[![Target Mode (Manual)](https://github.com/net2t/DD-CMS-Final/actions/workflows/target-manual.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/target-manual.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Last Commit](https://img.shields.io/github/last-commit/net2t/DD-CMS-Final)

---

## What It Does

```
GitHub Actions (every 15 min)
        ↓
Opens DamaDam in Chrome (headless — no screen needed)
        ↓
Logs in with your account
        ↓
Visits each online user's profile page
        ↓
Extracts: name, city, age, followers, posts, last post, photo, mehfil rooms...
        ↓
Writes data to your Google Sheet instantly (one row per profile)
        ↓
Sorts sheet so newest scrapes always appear at the top
```

**Two run modes:**

| Mode | What it does | When it runs |
|---|---|---|
| **Online Mode** | Scrapes whoever is currently online at damadam.pk/online_kon/ | Automatically every 15 min via GitHub Actions |
| **Target Mode** | Scrapes a list of nicknames you put in the RunList sheet | Manually — you trigger it |

> **Both modes cannot run at the same time.**
> - **GitHub Actions:** The second mode waits in queue and starts automatically after the first finishes (via `concurrency.group`).
> - **Local runs:** If a run is already active, the second attempt exits immediately with a warning (no queue).

---

## Google Sheet Structure

The scraper writes to these tabs in your sheet:

| Tab | Purpose |
|---|---|
| **Profiles** | Main data — one row per user, 23 columns |
| **RunList** | Target mode input — put nicknames here with status `⚡ Pending` |
| **Dashboard** | Run history — one row per run with stats |
| **Tags** | Optional — assign tag labels to nicknames |

### Profiles Tab — All 23 Columns

```
Col A  — ID               User's numeric ID on DamaDam
Col B  — NICK NAME        Username  ← Cell note shows before/after when data changes
Col C  — TAGS             Matched from Tags sheet
Col D  — CITY
Col E  — GENDER
Col F  — MARRIED
Col G  — AGE
Col H  — JOINED
Col I  — FOLLOWERS        Verified follower count
Col J  — LIST             RunList tag value (Target mode only)
Col K  — POSTS            Post count
Col L  — RUN MODE         "Online" or "Target"
Col M  — DATETIME SCRAP   When scraped — format: YYYY-MM-DD HH:MM
Col N  — LAST POST        URL of most recent post
Col O  — LAST POST TIME   Date/time of most recent post
Col P  — IMAGE            Profile photo URL
Col Q  — PROFILE LINK     Full profile URL
Col R  — POST URL         Public profile page URL
Col S  — RURL             Rank badge image URL
Col T  — MEH NAME         Mehfil room names (one per line)
Col U  — MEH LINK         Mehfil room links (one per line)
Col V  — MEH DATE         Mehfil join dates (one per line)
Col W  — PHASE 2          Reserved for future use
```

### Change Detection — Cell Notes

When a profile is re-scraped and any tracked field has changed, a **cell note** is automatically added to the NICK NAME cell (Col B). To view it:
- **Hover** over the cell — the note pops up
- Or press **Shift+F2** while the cell is selected

The note shows:
```
BEFORE:
  CITY: LAHORE
  FOLLOWERS: 120
AFTER:
  CITY: KARACHI
  FOLLOWERS: 145

Updated: 2026-03-24 17:00
```

Fields excluded from change tracking (always changing or not meaningful to track): ID, NICK NAME, JOINED, DATETIME SCRAP, LAST POST, LAST POST TIME, PROFILE LINK, POST URL, PHASE 2, RUN MODE, LIST.

### RunList Tab Format

To scrape specific users in Target Mode, add rows to the RunList tab:

```
Col A — NICKNAME    The DamaDam username to scrape
Col B — STATUS      Set to: ⚡ Pending  (scraper updates this to Done 💀 when finished)
Col C — REMARKS     Scraper writes result here (e.g. "Updated: 2026-03-24 17:00")
Col D — IGNORE      Put ANY value here to skip this row permanently (leave blank to scrape normally)
Col E — (unused)
Col F — TAG         Optional tag value — written to Col J (LIST) in Profiles sheet
```

> **Col D Ignore Flag:** If you want to keep a nickname in your RunList but never scrape it, put any value (e.g. `skip`, `x`, `ignore`) in Col D. The scraper will skip it every time without changing its status.

---

## Quick Start (Local / PC)

### Step 1 — Clone the repo

```bash
git clone https://github.com/net2t/DD-CMS-Final.git
cd DD-CMS-Final
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Create your `.env` file

Copy `.env.sample` to `.env` and fill in your values:

```env
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password

GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

→ For full setup instructions (Google credentials, sheet creation) see:
[`docs/guides/SETUP_WINDOWS.md`](docs/guides/SETUP_WINDOWS.md)

### Step 4 — Run it

```bash
# Interactive menu — prompts you to choose mode and options
python run.py

# Or run directly:
python run.py online             # Scrape currently online users
python run.py target             # Scrape your RunList
python run.py online --limit 20  # Limit to 20 profiles
```

---

## GitHub Actions — Automatic Cloud Runs

Once secrets are configured, GitHub runs the scraper every 15 minutes for you. Your PC does not need to be on.

### Required Secrets

Go to: **Your repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | What to put |
|---|---|
| `DAMADAM_USERNAME` | Your DamaDam username |
| `DAMADAM_PASSWORD` | Your DamaDam password |
| `GOOGLE_SHEET_URL` | Full URL of your Google Sheet |
| `GOOGLE_CREDENTIALS_JSON` | Your service account JSON — full file contents as one line |
| `DAMADAM_USERNAME_2` | Backup account username *(optional)* |
| `DAMADAM_PASSWORD_2` | Backup account password *(optional)* |

→ Full guide: [`docs/guides/GITHUB_ACTIONS_GUIDE.md`](docs/guides/GITHUB_ACTIONS_GUIDE.md)

### Workflows

| Workflow file | Trigger | What it runs |
|---|---|---|
| `online-schedule.yml` | Every 15 min (cron) + manual | Online Mode |
| `target-manual.yml` | Manual only | Target Mode |

Both workflows share the same concurrency group (`dd-cms`). They will never run simultaneously — the second one waits for the first to finish.

To trigger Target Mode manually: **Actions tab → Target Mode → Run workflow**

---

## Configuration Reference

All settings live in `.env` (local) or GitHub Secrets (cloud).

| Variable | Default | Description |
|---|---|---|
| `DAMADAM_USERNAME` | *(required)* | Primary DamaDam login username |
| `DAMADAM_PASSWORD` | *(required)* | Primary DamaDam login password |
| `DAMADAM_USERNAME_2` | — | Backup account (used if primary fails) |
| `DAMADAM_PASSWORD_2` | — | Backup account password |
| `GOOGLE_SHEET_URL` | *(required)* | Your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | *(required)* | Service account JSON string |
| `MIN_DELAY` | `0.3` | Minimum seconds between profile requests |
| `MAX_DELAY` | `0.5` | Maximum seconds between profile requests |
| `PAGE_LOAD_TIMEOUT` | `10` | Seconds to wait for a page to load |
| `SHEET_WRITE_DELAY` | `0.5` | Seconds between Google Sheets API calls |
| `DEBUG_MODE` | `false` | Set `true` to enable detailed debug logging for post count extraction |
| `LAST_POST_FETCH_PUBLIC_PAGE` | `false` | Set `true` for richer last-post data (slower) |
| `SORT_PROFILES_BY_DATE` | `true` | (Deprecated) No longer used; end-of-run sort has been removed |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Sheet not updating | GitHub Actions failing silently | Check **Actions tab → recent run → logs** |
| Profiles show old dates | DATETIME SCRAP sort bug (fixed v3.0.1) | Run `python fix_datetime_format.py` once |
| Login fails | Wrong credentials or site changed | Test login manually; check your secrets |
| `run.lock` stuck | Previous run crashed without cleanup | Delete `run.lock` from project root |
| 429 errors in logs | Google Sheets rate limit | Increase `SHEET_WRITE_DELAY` to `1.0` |
| 0 profiles found | DamaDam HTML structure changed | Check `config/selectors.py` |
| Both modes ran at same time | Old workflow files (fixed v3.0.2) | Replace both `.github/workflows/` files |
| Post count blank (Col K) | Scraper missed `<b>` tag (fixed v3.0.2) | Update `target_mode.py` and `sheets_manager.py` |
| Post count still blank | New HTML structure or pattern mismatch | Set `DEBUG_MODE=true` and run to see extraction details |
| Duplicates after every run | Cache sync bug (fixed v3.0.2) | Update `sheets_manager.py` |

→ Full guide: [`docs/guides/TROUBLESHOOTING.md`](docs/guides/TROUBLESHOOTING.md)

---

## Project Structure

```
DD-CMS-Final/
│
├── config/
│   ├── config_common.py      ← All settings & column definitions
│   ├── config_online.py      ← Online mode credential overrides
│   ├── config_target.py      ← Target mode credential overrides
│   └── selectors.py          ← CSS/XPath selectors for DamaDam pages
│
├── core/                     ← LOCKED — do not modify
│   ├── browser_manager.py    ← Chrome setup & launch options
│   ├── login_manager.py      ← DamaDam login & cookie handling
│   └── run_context.py        ← Connects browser + sheets
│
├── phases/
│   ├── phase_profile.py      ← Routes to online or target mode
│   └── profile/
│       ├── online_mode.py    ← Fetches online users list from site
│       └── target_mode.py    ← Profile scraper + main run loop
│
├── utils/
│   ├── sheets_manager.py     ← All Google Sheets read/write logic
│   ├── ui.py                 ← Logging, timestamps, progress display
│   └── url_builder.py        ← Builds profile & public page URLs
│
├── docs/
│   ├── guides/               ← Setup, GitHub Actions, Troubleshooting, Testing
│   └── reference/            ← Architecture details
│
├── .github/workflows/
│   ├── online-schedule.yml   ← Runs Online Mode every 15 min
│   └── target-manual.yml     ← Manual trigger for Target Mode
│
├── run.py                    ← Main entry point
├── fix_datetime_format.py    ← One-time migration script (run once after v3.0.1 upgrade)
├── requirements.txt          ← Python package list
├── .env.sample               ← Template — copy to .env and fill in
├── .githooks/                ← Git hooks (auto-push on commit)
│   └── post-commit           ← Automatically pushes to GitHub after each commit
├── README.md                 ← This file
```

---

## Git Hook Setup (Auto-Push)

This project includes a `post-commit` hook that automatically pushes to GitHub after each commit.

**To enable it (run once after cloning):**

```bash
# Windows (PowerShell)
git config core.hooksPath .githooks

# macOS / Linux
git config core.hooksPath .githooks && chmod +x .githooks/post-commit
```

Once enabled, every `git commit` will automatically trigger `git push`.

---

## Docs Index

| File | What's in it |
|---|---|
| [`docs/guides/SETUP_WINDOWS.md`](docs/guides/SETUP_WINDOWS.md) | Complete Windows setup from scratch |
| [`docs/guides/GITHUB_ACTIONS_GUIDE.md`](docs/guides/GITHUB_ACTIONS_GUIDE.md) | How to set up automatic cloud runs |
| [`docs/guides/TROUBLESHOOTING.md`](docs/guides/TROUBLESHOOTING.md) | Common errors and fixes |
| [`docs/guides/TESTING.md`](docs/guides/TESTING.md) | How to verify the scraper is working correctly |
| [`CHANGELOG.md`](CHANGELOG.md) | Full version history and bug fixes |
