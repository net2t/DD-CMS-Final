# Windows Setup Guide

Complete step-by-step guide to get DD-CMS-Final running on your Windows PC.

**Time required:** ~40 minutes
**Difficulty:** Beginner-friendly

---

## Before You Start

Have these ready:

- Windows 10 or 11
- Your DamaDam account username and password
- A Google account (for Google Sheets)
- Internet connection

---

## Step 1 — Install Python

### Download

1. Go to: https://www.python.org/downloads/
2. Click the big yellow **Download Python 3.11.x** button
3. Save the installer file

### Install

1. Double-click the downloaded `.exe` file
2. **⚠️ Important:** Before clicking anything else, check the box at the bottom:
   ```
   ☑️ Add Python 3.11 to PATH
   ```
   If you miss this, Python won't work from the terminal.
3. Click **Install Now**
4. Wait ~2 minutes, then click **Close**

### Verify

1. Press `Win + R`, type `cmd`, press Enter
2. In the black window, type:
   ```
   python --version
   ```
3. You should see something like: `Python 3.11.9`

**If you see "python is not recognized":** You missed the PATH checkbox. Uninstall Python from Windows Settings and reinstall — this time check the box.

---

## Step 2 — Install Git

### Download

1. Go to: https://git-scm.com/download/win
2. The download starts automatically
3. Save the installer file

### Install

1. Double-click the downloaded `.exe`
2. Click **Next** through all screens — default settings are fine
3. Click **Finish**

### Verify

Open a new `cmd` window and type:
```
git --version
```
You should see: `git version 2.x.x`

---

## Step 3 — Download the Project

Open `cmd` and navigate to where you want to keep the project. For example:
```
cd "C:\Users\NADEEM\3D Objects"
```

Then clone the repo:
```
git clone https://github.com/net2t/DD-CMS-Final.git
```

This creates a folder called `DD-CMS-Final`. To open a terminal inside it:
```
cd DD-CMS-Final
```

---

## Step 4 — Install Python Packages

From inside the `DD-CMS-Final` folder, run:
```
pip install -r requirements.txt
```

This installs Selenium, gspread, and all other dependencies. It takes about 2 minutes.

**Verify:** Type `pip list` — you should see `selenium`, `gspread`, `google-auth`, `python-dotenv`, `rich` in the list.

---

## Step 5 — Create Your `.env` File

The `.env` file holds your private credentials. It never gets uploaded to GitHub.

1. In File Explorer, go to your `DD-CMS-Final` folder
2. Find the file `.env.sample`
3. Copy it and rename the copy to `.env` (remove `.sample`)
4. Right-click `.env` → Open with → Notepad

Fill in your details:

```env
# Your DamaDam login
DAMADAM_USERNAME=YourUsernameHere
DAMADAM_PASSWORD=YourPasswordHere

# Optional backup account
DAMADAM_USERNAME_2=
DAMADAM_PASSWORD_2=

# Your Google Sheet URL (set up in Step 6)
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_ID_HERE/edit
```

Save and close.

---

## Step 6 — Set Up Google Sheets Access

This is the most involved step. It gives the scraper permission to write to your Google Sheet.

### 6a — Create a Google Sheet

1. Go to https://sheets.google.com
2. Click **+ Blank** to create a new sheet
3. Name it something like `DD-CMS Data`
4. At the bottom, create these tabs by clicking the `+` button:
   - `Profiles`
   - `RunList`
   - `Dashboard`
   - `Tags` (optional)
5. Copy the URL from your browser's address bar — you'll need it for `.env`

### 6b — Create a Service Account (Google Cloud)

A service account is a special Google account that lets scripts access your sheet without needing a browser login.

1. Go to: https://console.cloud.google.com
2. Click the project dropdown at the top → **New Project**
3. Name it `DD-CMS` → click **Create**
4. In the left menu: **APIs & Services → Library**
5. Search for `Google Sheets API` → click it → click **Enable**
6. Also enable `Google Drive API` the same way
7. In the left menu: **APIs & Services → Credentials**
8. Click **+ Create Credentials → Service Account**
9. Give it any name (e.g. `dd-cms-bot`) → click **Done**
10. Click on the service account you just created
11. Go to the **Keys** tab → **Add Key → Create new key → JSON**
12. A `.json` file downloads automatically — keep this safe

### 6c — Share Your Sheet with the Service Account

1. Open the downloaded `.json` file in Notepad
2. Find the line `"client_email"` — copy that email address (looks like `dd-cms-bot@your-project.iam.gserviceaccount.com`)
3. Open your Google Sheet
4. Click the **Share** button (top right)
5. Paste the service account email
6. Set permission to **Editor**
7. Uncheck "Notify people" → click **Share**

### 6d — Add Credentials to Your .env

You have two options:

**Option A — Use credentials.json file (easier for local use):**
1. Rename the downloaded `.json` file to `credentials.json`
2. Place it in the `DD-CMS-Final` folder (same level as `run.py`)
3. In `.env`, add:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=credentials.json
   ```

**Option B — Use JSON string (required for GitHub Actions):**
1. Open the `.json` file in Notepad
2. Select all text (`Ctrl+A`) → copy it
3. In `.env`, add:
   ```
   GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"...entire json here..."}
   ```
   It must be on one line with no line breaks.

---

## Step 7 — Test Run

Now test that everything works. From inside the `DD-CMS-Final` folder:

```
python run.py online --limit 3
```

This scrapes 3 currently-online DamaDam users and writes them to your Profiles sheet.

**Expected output:**
```
✅ Browser initialized successfully
✅ Primary account login successful
✅ Google Sheets connected
💠 Found 80+ valid online users
[1/3] 33% SomeNickname (scraping)
✅ New profile SomeNickname → Row 2
...
✅ Profiles sorted by date
✅ Dashboard updated
```

**Then check your Google Sheet** — the Profiles tab should have 3 new rows.

---

## Updating the Code

When there are fixes or new features pushed to GitHub:

```
cd "C:\Users\NADEEM\3D Objects\DD-CMS-Final"
git pull
pip install -r requirements.txt
```

---

## Common Errors

| Error message | What it means | Fix |
|---|---|---|
| `python is not recognized` | Python not in PATH | Reinstall Python — check "Add to PATH" |
| `No module named 'selenium'` | Packages not installed | Run `pip install -r requirements.txt` |
| `credentials.json not found` | Missing Google credentials file | Place `credentials.json` in project root |
| `Invalid GOOGLE_CREDENTIALS_JSON` | JSON string broken/incomplete | Re-copy from the `.json` file — must be one line |
| `Login failed` | Wrong username or password | Test credentials on damadam.pk manually |
| `Spreadsheet not found` | Wrong sheet URL or not shared | Share sheet with the service account email |

→ More detailed fixes: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

---

## Security Reminders

These files contain your passwords and API keys. **Never share them or commit them to GitHub.**

- `.env`
- `credentials.json`
- `damadam_cookies.pkl`

They are already listed in `.gitignore`, but double-check before pushing anything.
