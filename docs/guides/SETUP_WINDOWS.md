# 🪟 Windows Setup Guide

**Complete step-by-step guide for Windows users (beginner-friendly).**

---

## 📋 What You Need

Before starting, have these ready:
- [ ] Windows 10 or 11
- [ ] Internet connection
- [ ] DamaDam account (username + password)
- [ ] Google account (for Google Sheets)
- [ ] 30-60 minutes of time

---

## 🎯 Quick Overview

```
Step 1: Install Python         (10 min)
Step 2: Install Git            (5 min)
Step 3: Download Project       (5 min)
Step 4: Install Dependencies   (5 min)
Step 5: Setup Credentials      (10 min)
Step 6: Test Run              (5 min)
```

**Total time: ~40 minutes**

---

## 📥 Step 1: Install Python (10 minutes)

### 1.1 Download Python

1. Open browser, go to: https://www.python.org/downloads/
2. Click big yellow button: **Download Python 3.11.x**
3. Save the file (e.g., `python-3.11.7-amd64.exe`)

### 1.2 Install Python

1. **Double-click** the downloaded file
2. **✅ IMPORTANT:** Check ☑️ "Add Python to PATH"
   ```
   ┌─────────────────────────────────┐
   │ ☑️ Add Python 3.11 to PATH     │  ← CHECK THIS!
   └─────────────────────────────────┘
   ```
3. Click **Install Now**
4. Wait for installation (~2 minutes)
5. Click **Close**

### 1.3 Verify Installation

1. Press `Win + R` keys
2. Type: `cmd` and press Enter
3. In the black window, type:
   ```cmd
   python --version
   ```
4. Should see: `Python 3.11.x`

**If you see error "python not recognized":**
- You forgot to check "Add to PATH"
- Uninstall Python and reinstall (check the box!)

---

## 🔧 Step 2: Install Git (5 minutes)

### 2.1 Download Git

1. Go to: https://git-scm.com/download/win
2. Download will start automatically
3. Save the file (e.g., `Git-2.43.0-64-bit.exe`)

### 2.2 Install Git

1. **Double-click** the downloaded file
2. Click **Next** for all screens (default settings OK)
3. Wait for installation (~2 minutes)
4. Click **Finish**

### 2.3 Verify Installation

1. Press `Win + R`
2. Type: `cmd` and press Enter
3. Type:
   ```cmd
   git --version
   ```
4. Should see: `git version 2.43.x`

---

## 📦 Step 3: Download Project (5 minutes)

### 3.1 Choose Location

1. Open **File Explorer** (Win + E)
2. Go to: `C:\Users\YourName\Documents\`
3. Create new folder: `Projects`
4. Open the `Projects` folder

### 3.2 Download Code

**Method A: Using Git (Recommended)**
1. Right-click in `Projects` folder
2. Click **Open in Terminal** (Windows 11) or **Git Bash Here** (Windows 10)
3. Type:
   ```bash
   git clone https://github.com/net2t/DD-CMS-Final.git
   ```
4. Press Enter
5. Wait for download (~1 minute)

**Method B: Download ZIP**
1. Go to: https://github.com/net2t/DD-CMS-Final
2. Click green **Code** button
3. Click **Download ZIP**
4. Save to `Projects` folder
5. Right-click ZIP → **Extract All**
6. Rename folder to `DD-CMS-Final`

### 3.3 Verify Download

You should now have:
```
C:\Users\YourName\Documents\Projects\DD-CMS-Final\
├── config/
├── core/
├── phases/
├── utils/
├── main.py
├── requirements.txt
└── README.md
```

---

## 🔌 Step 4: Install Dependencies (5 minutes)

### 4.1 Open Project in Terminal

1. Open **File Explorer**
2. Navigate to: `C:\Users\YourName\Documents\Projects\DD-CMS-Final`
3. Type `cmd` in the address bar
4. Press Enter

You should see:
```
C:\Users\YourName\Documents\Projects\DD-CMS-Final>
```

### 4.2 Install Requirements

Type this command:
```cmd
pip install -r requirements.txt
```

Press Enter and wait (~2 minutes).

You'll see:
```
Collecting selenium>=4.15.0
Downloading selenium-4.15.2.tar.gz
Installing collected packages: selenium, gspread, ...
Successfully installed ...
```

### 4.3 Verify Installation

Type:
```cmd
pip list
```

Should see these packages:
- selenium
- gspread
- google-auth
- python-dotenv
- rich

---

## 🔐 Step 5: Setup Credentials (10 minutes)

### 5.1 Create .env File

1. In project folder, find `.env.example`
2. Right-click → **Copy**
3. Right-click → **Paste**
4. Rename copy to `.env` (no ".example")

### 5.2 Edit .env File

1. Right-click `.env` → **Open with** → **Notepad**
2. Fill in your information:

```env
# Your DamaDam login
DAMADAM_USERNAME=your_username_here
DAMADAM_PASSWORD=your_password_here

# Backup account (optional but recommended)
DAMADAM_USERNAME_2=
DAMADAM_PASSWORD_2=

# Your Google Sheet URL (get from Step 5.3)
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

3. Save and close

### 5.3 Setup Google Sheet

**Create Sheet:**
1. Go to: https://sheets.google.com
2. Click **+ Blank** to create new sheet
3. Name it: `DamaDam Scraper Data`
4. Copy the URL from browser

**Create Tabs:**
Create these sheets (click + button at bottom):
- Profiles
- RunList
- OnlineLog
- Dashboard
- Tags (optional)

### 5.4 Get Google Credentials

**Create Service Account:**
1. Go to: https://console.cloud.google.com
2. Create new project: `DamaDam Scraper`
3. Enable Google Sheets API
4. Create Service Account
5. Download `credentials.json`
6. Move `credentials.json` to project folder

**Share Sheet:**
1. Open your Google Sheet
2. Click **Share** button
3. Paste service account email (from credentials.json)
4. Give **Editor** permission

**Detailed guide:** https://docs.gspread.org/en/latest/oauth2.html

---

## 🧪 Step 6: Test Run (5 minutes)

### 6.1 Add Test Profile

1. Open your Google Sheet
2. Go to **RunList** tab
3. Add header row:
   ```
   NICKNAME | STATUS | REMARKS | SKIP
   ```
4. Add test row:
   ```
   testuser | ⚡ Pending | | 
   ```

### 6.2 Run Scraper

In terminal (from project folder):
```cmd
python main.py test --max-profiles 1
```

### 6.3 Expected Output

```
================================================================================
🚀 DamaDam Scraper - TEST MODE 🚀
Version: v2.100.0.18
================================================================================

🔐 Starting authentication...
✅ Login successful

=== RUNNING PROFILE PHASE (TEST MODE) ===
Processing 1 profile(s)...

1️⃣ [████████████████████] testuser (new)

📊 Scraping Run Summary
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Metric       ┃   Value ┃ Status ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ ✅ Success   │       1 │     ✅ │
│ ❌ Failed    │       0 │     ✅ │
└──────────────┴─────────┴────────┘

🎉 Run completed successfully!
```

### 6.4 Verify Results

1. Open your Google Sheet
2. Check **Profiles** tab
3. Should see one row with scraped data

**If successful:** ✅ Setup complete!
**If errors:** See Troubleshooting section below

---

## 🐛 Troubleshooting

### Error: "python not recognized"

**Problem:** Python not in PATH

**Fix:**
1. Uninstall Python
2. Reinstall Python
3. ✅ Check "Add Python to PATH" during installation

### Error: "No module named 'selenium'"

**Problem:** Dependencies not installed

**Fix:**
```cmd
pip install -r requirements.txt
```

### Error: "credentials.json not found"

**Problem:** Missing Google credentials

**Fix:**
1. Download `credentials.json` from Google Cloud Console
2. Place in project root folder (same level as main.py)

### Error: "404 Not Found" (Google Sheets)

**Problem:** Wrong sheet URL or permissions

**Fix:**
1. Verify URL format: `https://docs.google.com/spreadsheets/d/.../edit`
2. Share sheet with service account email
3. Give Editor permission

### Error: "Login failed"

**Problem:** Wrong username/password

**Fix:**
1. Test credentials on DamaDam website manually
2. Check for typos in `.env` file
3. No extra spaces in username/password

### Browser Opens but Crashes

**Problem:** ChromeDriver version mismatch

**Fix:**
1. Update Chrome browser to latest
2. Reinstall selenium: `pip install --upgrade selenium`

---

## 🎓 Next Steps

### Daily Usage

```cmd
# Target mode (from RunList)
python main.py target --max-profiles 10

# Online mode (currently online users)
python main.py online --max-profiles 20
```

### Update Code

```cmd
# Pull latest changes
git pull origin main

# Reinstall dependencies (if changed)
pip install -r requirements.txt
```

### View Logs

```cmd
# Open logs folder
cd logs

# View latest log
type target_*.log
```

---

## 📁 Project Structure

```
C:\Users\YourName\Documents\Projects\DD-CMS-Final\
│
├── config/              ← Configuration files
├── core/                ← Browser & login
├── phases/              ← Scraping logic
├── utils/               ← Helper functions
├── logs/                ← Log files (auto-created)
│
├── .env                 ← Your credentials (DO NOT SHARE!)
├── credentials.json     ← Google credentials (DO NOT SHARE!)
├── main.py              ← Run this file
├── requirements.txt     ← Dependencies list
└── README.md            ← Documentation
```

---

## 🔒 Security Tips

**Protect these files:**
- ❌ `.env` - Contains passwords
- ❌ `credentials.json` - Contains API keys
- ❌ `*.pkl` - Contains cookies

**Never share or commit to GitHub!**

These are already in `.gitignore`, but be careful:
- Don't copy to public folders
- Don't upload to cloud drives
- Don't email these files

---

## 💡 Tips for Windows Users

### Open Terminal Quickly

1. Navigate to project folder in File Explorer
2. Type `cmd` in address bar
3. Press Enter

### Edit Files Easily

**Good editors:**
- Notepad++ (free, simple)
- VS Code (free, powerful)
- PyCharm (free community edition)

**Don't use:**
- Regular Notepad (might break formatting)
- Microsoft Word (wrong tool)

### Schedule Automatic Runs

Use Windows Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at specific time
4. Action: Start a program
5. Program: `python.exe`
6. Arguments: `C:\...\main.py target --max-profiles 10`

---

## 📞 Getting Help

**Still stuck?**

1. **Check documentation:**
   - README.md - Overview
   - TROUBLESHOOTING.md - Common issues
   - LIMIT_HANDLING.md - Rate limits

2. **Check logs:**
   - Open `logs/` folder
   - Look for ERROR messages
   - Copy exact error text

3. **Contact maintainer:**
   - Email: net2outlawzz@gmail.com
   - Include: Error message, what you tried, screenshots

---

## ✅ Setup Complete!

Congratulations! You're ready to start scraping.

**Recommended first run:**
```cmd
python main.py target --max-profiles 5
```

**What to read next:**
1. README.md - Full feature list
2. LIMIT_HANDLING.md - If you hit rate limits
3. PROJECT_RULES.md - If you want to modify code

**Happy scraping! 🚀**
