# GitHub Actions Guide

This guide explains how the scraper runs automatically in the cloud via GitHub Actions — and how to configure, monitor, and trigger it.

---

## What GitHub Actions Does

GitHub Actions is a free service (for public repos) that runs code on GitHub's servers on a schedule. For this project:

- **Online Mode** runs automatically every 15 minutes, 24/7 — no PC needed
- **Target Mode** runs when you manually trigger it from the GitHub website

GitHub provides the server, Chrome browser, Python, and all dependencies fresh for each run. Your credentials are stored securely as GitHub Secrets and injected at runtime — they never appear in the code or logs.

---

## One-Time Setup

### Step 1 — Make sure your repo is on GitHub

If you cloned from `https://github.com/net2t/DD-CMS-Final`, this is already done.

If you forked it or created your own repo, push your code:
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2 — Add your secrets

Go to your GitHub repo page → **Settings → Secrets and variables → Actions → New repository secret**

Add each of these one at a time:

| Secret Name | What to put | Required? |
|---|---|---|
| `DAMADAM_USERNAME` | Your DamaDam username | ✅ Yes |
| `DAMADAM_PASSWORD` | Your DamaDam password | ✅ Yes |
| `GOOGLE_SHEET_URL` | Full URL of your Google Sheet | ✅ Yes |
| `GOOGLE_CREDENTIALS_JSON` | Your service account `.json` file contents — paste as one line, no line breaks | ✅ Yes |
| `DAMADAM_USERNAME_2` | Backup DamaDam username | Optional |
| `DAMADAM_PASSWORD_2` | Backup DamaDam password | Optional |

**For `GOOGLE_CREDENTIALS_JSON`:** Open your `credentials.json` file in Notepad, select all, copy, and paste directly into the secret value box. It must be on one continuous line.

### Step 3 — Enable Actions (if needed)

If this is a forked repo, GitHub may have disabled Actions by default.

Go to: **Your repo → Actions tab → click "I understand my workflows, go ahead and enable them"**

---

## The Two Workflows

### Online Mode — Runs automatically every 15 minutes

File: `.github/workflows/online-schedule.yml`

```
Triggers:
  - Cron schedule: every 15 minutes
  - Manual trigger (you can also run it by hand)

What it does:
  1. Spins up Ubuntu server
  2. Installs Python 3.11
  3. Installs Chrome
  4. Runs: python run.py online --limit 0  (unlimited)
  5. Results written to your Google Sheet
  6. Server shuts down
```

Each run takes about 5–8 minutes for 80–100 profiles.

### Target Mode — Manual trigger only

File: `.github/workflows/target-manual.yml`

```
Triggers:
  - Manual only — you click "Run workflow" on GitHub

What it does:
  1. Same setup as Online Mode
  2. Reads ⚡ Pending rows from your RunList sheet
  3. Scrapes each one
  4. Marks each row Done 💀 immediately after scraping (crash-safe)
```

---

## How to Trigger Target Mode Manually

1. Go to your GitHub repo
2. Click the **Actions** tab
3. In the left sidebar, click **Target Mode**
4. Click the **Run workflow** button (top right of the run list)
5. Optionally set a profile limit (0 = unlimited)
6. Click **Run workflow**

The run starts within ~30 seconds. Click on it to watch the live log.

---

## Monitoring Runs

### Checking if runs are working

1. Go to **Actions tab** in your repo
2. You'll see a list of recent runs — green ✅ = success, red ❌ = failed
3. Click any run to see the full log

### Reading the log

The most useful part of the log is the `Run Online mode` or `Run Target mode` step. Look for:

```
✅ Browser initialized successfully
✅ Primary account login successful
✅ Google Sheets connected
💠 Found 81 valid online users
[1/81] 1% SomeName (scraping)
✅ Updated SomeName → Row 2
...
✅ Profiles sorted by date
✅ Dashboard updated

Successful: 81
Failed:     0
```

If you see errors, the log shows exactly which step failed.

### Checking run history in your sheet

The **Dashboard** tab in your Google Sheet has one row per run:

| Column | Contents |
|---|---|
| RUN# | Run number |
| TIMESTAMP | When the run happened |
| PROFILES | How many profiles were processed |
| SUCCESS / FAILED / NEW / UPDATED | Counts |
| TRIGGER | "online-schedule" or "manual" |
| START / END | Run start and end times |

---

## Concurrency Protection

Both workflows have this setting:

```yaml
concurrency:
  group: dd-cms-online
  cancel-in-progress: false
```

This means if a run is still going when the next 15-minute tick arrives, the new run **waits** rather than cancelling the current one. Runs never overlap.

---

## Secrets Are Never Exposed

- Secrets appear as `***` in all logs
- Secrets are not accessible to fork pull requests
- Secrets are encrypted at rest by GitHub

The log will show lines like:
```
DAMADAM_USERNAME: ***
GOOGLE_CREDENTIALS_JSON: ***
```
This confirms the secrets were injected — the `***` is intentional masking.

---

## Troubleshooting Failed Runs

**Run fails immediately with "Error: Process completed with exit code 1"**
→ Click on the failed run → expand the `Run Online mode` step → read the error

**"No valid Google credentials found"**
→ Your `GOOGLE_CREDENTIALS_JSON` secret is missing, empty, or has line breaks in it
→ Re-paste it as a single line

**"Login failed" or "Login timeout"**
→ Check `DAMADAM_USERNAME` and `DAMADAM_PASSWORD` secrets are correct
→ Test your login on damadam.pk manually

**"SpreadsheetNotFound"**
→ Check `GOOGLE_SHEET_URL` is the full URL including `/edit`
→ Make sure the sheet is shared with your service account email (Editor permission)

**Runs succeed but sheet doesn't update**
→ Check the `ONLINE_GOOGLE_SHEET_URL` secret — if blank, it falls back to `GOOGLE_SHEET_URL` which is correct
→ Scroll up in the log and look for any `[WARNING]` or `[ERROR]` lines

**"Already up to date" when pushing fixes**
→ You edited files here in chat — download them from the output panel and replace manually on your PC, then `git add`, `git commit`, `git push`

→ More fixes: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
