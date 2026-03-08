# Troubleshooting Guide

Solutions for the most common problems with DD-CMS-Final.

---

## Sheet Not Updating

**Symptom:** GitHub Actions runs show green (success) but no new data appears in the Profiles sheet.

**Step 1 — Check the actual run log:**
1. Go to your repo → **Actions** tab
2. Click the most recent run
3. Expand the **Run Online mode** step
4. Look for `[ERROR]` or `[WARNING]` lines

**Step 2 — Check the Dashboard sheet:**
The Dashboard tab in your Google Sheet has one row per run. If the last row is from weeks ago, the run is failing before it reaches the sheet-write step.

**Step 3 — Common causes:**

| What the log shows | Cause | Fix |
|---|---|---|
| `No valid Google credentials found` | `GOOGLE_CREDENTIALS_JSON` secret missing or broken | Re-add the secret as one continuous line |
| `SpreadsheetNotFound` | Wrong sheet URL or sheet not shared | Fix `GOOGLE_SHEET_URL` secret; share sheet with service account |
| `Login failed` | Wrong DamaDam credentials | Check `DAMADAM_USERNAME` / `DAMADAM_PASSWORD` secrets |
| `Found 0 valid online users` | DamaDam page HTML changed | See "0 profiles found" section below |
| Run completes, sheet updated, but dates look old | DATETIME SCRAP sort bug | See "Profiles show old dates" section below |

---

## Profiles Show Old Dates (Stuck at 1-Mar or Earlier)

**Symptom:** The DATETIME SCRAP column (Col M) shows old dates like `01-Mar-26` even though the scraper is running.

**Cause:** This was a bug in v3.0.0 where dates were stored as `08-Mar-26 05:00 PM`. Google Sheets sorts this alphabetically, putting older data at the top and burying fresh data. Fixed in v3.0.1.

**Fix — two parts:**

Part 1 — Get the latest code:
```bash
cd "C:\Users\NADEEM\3D Objects\DD-CMS-Final"
git pull
```
If git pull says "Already up to date" but the fix isn't in your files, download the updated files from the project maintainer and replace them manually.

Part 2 — Run the migration script once to fix existing sheet data:
```bash
python fix_datetime_format.py
```
This converts all existing rows from `08-Mar-26 05:00 PM` to `2026-03-08 17:00` format. It only needs to be run once.

After this, the next GitHub Actions run will write fresh dates correctly and sort will work.

---

## Login Failed

**Symptom:** Log shows `Login failed` or `Login timeout`.

**Checks:**
1. Go to damadam.pk in your browser and log in manually with the same credentials — confirms the account works
2. Check your `.env` file (local) or GitHub secret — no extra spaces, no quotes around the value
3. If your password contains special characters (`@`, `#`, `&`, etc.), try wrapping it in quotes in `.env`:
   ```
   DAMADAM_PASSWORD="p@ss#word"
   ```
4. Check if DamaDam changed their login page. If the login button or form fields look different, the selectors in `core/login_manager.py` may need updating.

---

## `run.lock` File Stuck

**Symptom:** Running `python run.py` immediately exits with a message about a lock file.

**Cause:** A previous run crashed or was force-stopped without cleaning up.

**Fix:** Delete the file:
```bash
# Windows
del run.lock

# Or in File Explorer — just delete run.lock from the project folder
```

---

## 0 Profiles Found

**Symptom:** Log shows `Found 0 valid online users` and the run completes instantly with no data written.

**Most likely cause:** DamaDam updated their website HTML, and the CSS selectors used to find online users no longer match.

**Fix:**
1. Open damadam.pk/online_kon/ in Chrome
2. Right-click a user's name → **Inspect**
3. Look at the HTML structure around the username
4. Compare it to the selectors in `config/selectors.py` — specifically `OnlineUserSelectors`
5. Update the selectors to match what you see in the HTML

The three fallback strategies in `online_mode.py` mean one selector can fail and it still tries the others. If all three fail, the HTML has changed significantly.

---

## Google Sheets 429 Rate Limit Errors

**Symptom:** Log shows `Rate limit hit — waiting 60s...` repeatedly.

**Cause:** Too many API calls to Google Sheets in a short time. Google allows ~100 requests per 100 seconds per project.

**Fix — increase delays in GitHub Secrets:**
```
SHEET_WRITE_DELAY = 1.0    (was 0.5)
MIN_DELAY = 1.5
MAX_DELAY = 2.5
```

The scraper already has a built-in retry with backoff (waits 60s, 120s, 180s on successive 429s), but if you're hitting it regularly, increasing the delays prevents it from happening at all.

---

## `credentials.json` Not Found

**Symptom:** Error like `No such file: credentials.json` when running locally.

**Fixes:**
- Make sure `credentials.json` is in the project root folder (same level as `run.py`) — not in a subfolder
- Or use the JSON string approach instead: copy the full contents of `credentials.json` into `GOOGLE_CREDENTIALS_JSON` in your `.env` file (all on one line)

---

## Browser Crashes or Won't Start

**Symptom:** Error during Chrome startup, or `selenium.common.exceptions.WebDriverException`.

**Likely cause:** Chrome version mismatch with ChromeDriver.

**Fix:**
```bash
pip install --upgrade selenium
```

Selenium 4.x automatically manages ChromeDriver — it downloads the correct version for your installed Chrome. If you're using an old version of selenium, it may try to use an incompatible ChromeDriver.

Also check: is Chrome installed? On GitHub Actions, Chrome is installed automatically by the `setup-chrome` step. Locally, you need Chrome installed on your PC.

---

## Data Looks Wrong or Columns Are Shifted

**Symptom:** Data appears in the wrong columns, or columns look shifted compared to the header.

**Cause:** The Profiles sheet has a different number of columns than what `config_common.py` expects (23 columns).

**Fix:**
1. Open your Profiles sheet
2. Check that Row 1 has exactly 23 headers matching `Config.COLUMN_ORDER`
3. If there are extra columns or missing columns, the sheet needs to be reset
4. Delete all rows in the Profiles sheet (keep the header) and let the next scrape rebuild it

**The column order is (A → W):**
```
ID | NICK NAME | TAGS | CITY | GENDER | MARRIED | AGE | JOINED |
FOLLOWERS | LIST | POSTS | RUN MODE | DATETIME SCRAP | LAST POST |
LAST POST TIME | IMAGE | PROFILE LINK | POST URL | RURL |
MEH NAME | MEH LINK | MEH DATE | PHASE 2
```

---

## `git pull` Says "Already Up to Date" But Files Are Old

This happens because fixes made in a chat session live in a temporary environment — they can't push directly to your GitHub repo.

**How to apply fixes manually:**
1. Download the updated files from the output panel in the chat
2. Replace the corresponding files in your project folder:
   - `utils/sheets_manager.py`
   - `phases/profile/target_mode.py`
   - etc.
3. Then push to GitHub yourself:
   ```bash
   git add .
   git commit -m "Apply fix from chat session"
   git push
   ```
