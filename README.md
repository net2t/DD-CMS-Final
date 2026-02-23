# DD-CMS-V3

DamaDam (damadam.pk) profile scraper with two run modes:

- **Online mode**: scrape currently online users.
- **Target mode**: scrape nicknames from Google Sheet `RunList` where status is **⚡ Pending**.

## Status

- **Login**: Selenium + cookies
- **Writes**: Google Sheets (Profiles + Dashboard; Target also updates RunList)
- **Scheduler**: Online mode every 15 minutes (local scheduler + GitHub Actions cron)

## Badges

[![Online Mode (15 min)](https://github.com/net2t/DD-CMS-Final/actions/workflows/online-schedule.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/online-schedule.yml)
[![Target Mode (Manual)](https://github.com/net2t/DD-CMS-Final/actions/workflows/target-manual.yml/badge.svg)](https://github.com/net2t/DD-CMS-Final/actions/workflows/target-manual.yml)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?logo=selenium&logoColor=white)
![Google%20Sheets](https://img.shields.io/badge/Google%20Sheets-gspread-34A853?logo=google&logoColor=white)

![Last Commit](https://img.shields.io/github/last-commit/net2t/DD-CMS-Final)
![Issues](https://img.shields.io/github/issues/net2t/DD-CMS-Final)
![Stars](https://img.shields.io/github/stars/net2t/DD-CMS-Final)

## Quick start

### 1) Install

```bash
pip install -r requirements.txt
```

### 2) Configure

Copy `.env.sample` to `.env` and fill in values.

Required:

- `DAMADAM_USERNAME`
- `DAMADAM_PASSWORD`
- `GOOGLE_SHEET_URL`
- Google credentials either:
  - `GOOGLE_CREDENTIALS_JSON` (service account JSON string)
  - OR `GOOGLE_APPLICATION_CREDENTIALS=credentials.json` (file in repo root)

### 3) Run

#### A) Interactive menu (recommended)

```bash
python run.py
```

You’ll get:

- Mode select (Online / Target / Scheduler)
- Options:
  - limit (how many profiles)
  - batch size
  - min/max delay
  - page load timeout
  - sheet write delay

#### B) Direct CLI

```bash
python run.py online --limit 20
python run.py target --limit 10
python run.py scheduler --limit 50
```

## Run modes

### Online mode

- Fetches `https://damadam.pk/online_kon/`
- Scrapes each user’s profile
- Writes to **Profiles** sheet
- Updates **Dashboard**

### Target mode

- Reads `RunList` sheet
- Selects rows where status contains **pending**
- Scrapes each nickname
- Writes to **Profiles** sheet
- Updates `RunList` status + remarks immediately (crash-safe)
- Updates **Dashboard**

## Google Sheet tabs expected

- `Profiles`
- `RunList`
- `Dashboard`
- `Tags` (optional)

## GitHub Actions

### Online scheduled (every 15 minutes)

Workflow: `.github/workflows/online-schedule.yml`

- Triggered by cron every 15 minutes
- Also supports manual trigger with an optional `limit`

### Target manual

Workflow: `.github/workflows/target-manual.yml`

- Manual trigger only (`workflow_dispatch`)
- Optional `limit`

### Required repository secrets

Add these in **Repo → Settings → Secrets and variables → Actions**:

- `DAMADAM_USERNAME`
- `DAMADAM_PASSWORD`
- `DAMADAM_USERNAME_2` (optional)
- `DAMADAM_PASSWORD_2` (optional)
- `GOOGLE_SHEET_URL`
- `GOOGLE_CREDENTIALS_JSON`

## Troubleshooting

- If runs won’t start because of a stale lock:
  - delete `run.lock`
- If login is slow/timeouts:
  - increase `PAGE_LOAD_TIMEOUT` in `.env` (example: `60`)
  - increase delays (`MIN_DELAY`, `MAX_DELAY`)
- If Sheets auth fails:
  - ensure `GOOGLE_CREDENTIALS_JSON` is valid JSON
  - or provide `credentials.json` and set `GOOGLE_APPLICATION_CREDENTIALS=credentials.json`

## Docs

More detailed docs are in:

- `docs/README.md`
