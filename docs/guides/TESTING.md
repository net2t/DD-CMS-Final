# Testing Guide

How to verify the scraper is working correctly — before and after making changes.

---

## Quick Sanity Check (2 minutes)

Run this from your project folder whenever you want to confirm everything is working:

```bash
python run.py online --limit 3
```

This scrapes 3 currently-online DamaDam users. Look for:

```
✅ Browser initialized successfully
✅ Primary account login successful
✅ Google Sheets connected
💠 Found XX valid online users
[1/3] SomeNickname (scraping)
✅ New profile SomeNickname → Row 2
...
✅ Profiles sorted by date
✅ Dashboard updated

Successful: 3 | Failed: 0
```

Then open your Google Sheet → Profiles tab. The 3 new rows should be at the top with today's date in Col M (DATETIME SCRAP).

---

## Testing Target Mode

Add a known DamaDam username to your RunList sheet:

```
NICKNAME       | STATUS      | REMARKS
SomeNickname   | ⚡ Pending  |
```

Then run:
```bash
python run.py target --limit 1
```

**Expected results:**
- The row in RunList changes from `⚡ Pending` to `Done 💀`
- A new row appears in Profiles with full data
- REMARKS column shows something like `Updated: 2026-03-08 17:00`

---

## Verifying Each Column Fills Correctly

After a test run, spot-check these columns in the Profiles sheet:

| Column | Should contain | Common issue |
|---|---|---|
| B — NICK NAME | The username | Never blank |
| D — CITY | City name or blank | OK if blank — user may not have set it |
| E — GENDER | MALE or FEMALE | Should not be blank for verified users |
| I — FOLLOWERS | A number | `0` is valid |
| K — POSTS | A number | `0` is valid |
| L — RUN MODE | ONLINE or TARGET | Depends which mode you used |
| M — DATETIME SCRAP | `2026-03-08 17:00` format | Old format means migration script hasn't been run |
| P — IMAGE | A URL (cloudfront.net/...) | Blank if user has no profile photo |
| Q — PROFILE LINK | Full damadam.pk URL | Never blank |

---

## Testing the Sort

The Profiles sheet should always have the most recently scraped profile in Row 2 (Row 1 is the header).

After running a scrape, check:
1. Row 2 shows today's date in Col M
2. Dates in Col M go from newest (top) to oldest (bottom) as you scroll down

If the sort looks wrong and old dates are appearing at the top, run the migration script:
```bash
python fix_datetime_format.py
```

---

## Before Pushing Code Changes

If you've edited any `.py` files, do a quick test before pushing to GitHub:

1. Run `python run.py online --limit 5` — confirm it completes without errors
2. Check the Profiles sheet — 5 new/updated rows with today's timestamp
3. Check the Dashboard sheet — a new row was added for this run
4. `git add` only the files you intentionally changed — don't accidentally commit `.env` or `credentials.json`

---

## Testing After Applying a Fix from Chat

After downloading and replacing fixed files:

1. Replace the files in your project folder
2. Run the local test: `python run.py online --limit 3`
3. If it passes, push to GitHub: `git add`, `git commit`, `git push`
4. Go to GitHub → Actions tab — watch the next automatic run complete successfully
5. Check your sheet for fresh data

---

## What "Success" Looks Like in the Log

```
✅ Browser initialized successfully        ← Chrome started OK
✅ Primary account login successful        ← DamaDam login worked
✅ Google Sheets connected                 ← Credentials valid, sheet found
💠 Found 81 valid online users             ← Site scraped, nicknames collected
[1/81] 1% NickName (scraping)             ← Per-profile progress
✅ Updated NickName → Row 2               ← Written to sheet
...
✅ Profiles sorted by date                 ← Sort completed
✅ Dashboard updated                       ← Run summary written
Successful: 81 | Failed: 0 | Skipped: 0  ← Final count
```

Any line with `[ERROR]` or `[WARNING]` is worth investigating. A few warnings (e.g. a single profile timing out) are normal. Consistent errors on every profile indicate a bigger problem.
