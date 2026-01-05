# 🔧 GitHub Actions Quick Fix

## 🚨 Problem

Your GitHub Actions workflow is failing with:
```
❌ An error occurred: <Response [404]>
```

**Root Cause:** Workflow is using old file structure and secret names.

---

## ✅ Quick Fix (3 Steps)

### Step 1: Update Secrets (5 minutes)

Go to: `https://github.com/net2t/DD-CMS-Final/settings/secrets/actions`

**Add these NEW secrets:**

1. **`DAMADAM_USERNAME`** = Your DamaDam username
2. **`DAMADAM_PASSWORD`** = Your DamaDam password  
3. **`GOOGLE_SHEET_URL`** = `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit` (full URL!)
4. **`GOOGLE_CREDENTIALS_JSON`** = Paste entire `credentials.json` content

**Optional but recommended:**
5. **`DAMADAM_USERNAME_2`** = Backup account username
6. **`DAMADAM_PASSWORD_2`** = Backup account password

---

### Step 2: Update Workflow Files (2 minutes)

Replace these files in your repository:

#### File 1: `.github/workflows/scrape-target.yml`
```yaml
# Copy content from artifact: "scrape-target.yml - Fixed Target Mode Workflow"
```

#### File 2: `.github/workflows/scrape-online.yml`
```yaml
# Copy content from artifact: "scrape-online.yml - Fixed Online Mode Workflow"
```

**Delete old workflow if exists:**
- ❌ `.github/workflows/run-scraper.yml`

---

### Step 3: Test (2 minutes)

1. Go to **Actions** tab
2. Click **Target Mode 🔰**
3. Click **Run workflow**
4. Set `max_profiles` = `3`
5. Click **Run workflow**

**Expected output:**
```
✅ Credentials file created
🎯 Starting Target Mode...
✅ Login successful
🔍 Scraping: user1
✅ user1: new
```

---

## 🔍 What Changed?

### Old Workflow → New Workflow

| Old | New | Why |
|-----|-----|-----|
| `python Scraper.py` | `python main.py target` | New structure |
| `DD_LOGIN_EMAIL` | `DAMADAM_USERNAME` | Consistent naming |
| `DD_LOGIN_PASS` | `DAMADAM_PASSWORD` | Consistent naming |
| `DD_SHEET_ID` | `GOOGLE_SHEET_URL` | Need full URL |
| `DD_CREDENTIALS_JSON` | `GOOGLE_CREDENTIALS_JSON` | Consistent naming |
| `DD_MODE` env var | `target` CLI arg | Better control |

---

## 🐛 If Still Failing

### Check 1: Secret Names
```
✅ DAMADAM_USERNAME (not DD_LOGIN_EMAIL)
✅ DAMADAM_PASSWORD (not DD_LOGIN_PASS)
✅ GOOGLE_SHEET_URL (not DD_SHEET_ID)
✅ GOOGLE_CREDENTIALS_JSON (not DD_CREDENTIALS_JSON)
```

### Check 2: Sheet URL Format
```
✅ CORRECT: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
❌ WRONG: 1ABC...XYZ
❌ WRONG: https://docs.google.com/spreadsheets/d/1ABC...XYZ
```

### Check 3: Service Account Access
1. Open your Google Sheet
2. Click **Share**
3. Add: `your-service-account@project.iam.gserviceaccount.com`
4. Give **Editor** permission

### Check 4: Workflow File
```bash
# Make sure you're using:
python main.py target --max-profiles 3

# NOT:
python Scraper.py  ❌
```

---

## 📋 Complete Checklist

### Secrets Setup
- [ ] Added `DAMADAM_USERNAME`
- [ ] Added `DAMADAM_PASSWORD`
- [ ] Added `GOOGLE_SHEET_URL` (full URL!)
- [ ] Added `GOOGLE_CREDENTIALS_JSON` (full JSON!)
- [ ] (Optional) Added backup account secrets

### Files Updated
- [ ] Replaced `.github/workflows/scrape-target.yml`
- [ ] Replaced `.github/workflows/scrape-online.yml`
- [ ] Deleted old `.github/workflows/run-scraper.yml`
- [ ] Committed and pushed to GitHub

### Testing
- [ ] Manual test run successful (3 profiles)
- [ ] Profiles appear in Google Sheet
- [ ] No errors in workflow logs

---

## 🎯 Need More Help?

See detailed guides:
- **GITHUB_SECRETS_SETUP.md** - Complete secrets setup guide
- **LIMIT_HANDLING.md** - If you hit rate limits
- **TROUBLESHOOTING.md** - Common issues and solutions

Contact: net2outlawzz@gmail.com

---

**Quick Fix Time:** ~10 minutes  
**Difficulty:** Easy  
**Status:** Ready to deploy
