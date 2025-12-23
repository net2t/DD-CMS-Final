# DamaDam Scraper v4.0 - Production Ready

Complete automation bot for scraping DamaDam.pk user profiles with dual-mode operation.

## 🚀 Quick Start (5 Minutes)

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd Damadam-Scraper_v_4.0
pip install -r requirements.txt
```

### 2. Setup Credentials

**A. Create `.env` file:**
```bash
cp .env.example .env
```

**B. Edit `.env` with your credentials:**
```env
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

**C. Add Google Service Account:**
1. Download `credentials.json` from Google Cloud Console
2. Place in project root directory
3. Share your Google Sheet with service account email

### 3. Run

```bash
# Target Mode (from Target sheet)
python main.py --mode target

# Online Mode (from online users)
python main.py --mode online
```

---

## 📋 Features

✅ **Dual Scraping Modes**
- Target Mode: Scrapes users from "Target" sheet
- Online Mode: Scrapes currently online users

✅ **Smart Data Management**
- ID-based updates (no duplicates on nickname change)
- Profile state tracking (ACTIVE/UNVERIFIED/BANNED/DEAD)
- Automatic change detection

✅ **Production Ready**
- Cookie-based session persistence
- Intelligent retry logic
- Rate limit handling
- Comprehensive logging

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DAMADAM_USERNAME` | ✅ Yes | - | DamaDam login username |
| `DAMADAM_PASSWORD` | ✅ Yes | - | DamaDam login password |
| `GOOGLE_SHEET_URL` | ✅ Yes | - | Your Google Sheet URL |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ Yes | `credentials.json` | Path to Google credentials |
| `MAX_PROFILES_PER_RUN` | No | `0` | Limit profiles (0 = unlimited) |
| `BATCH_SIZE` | No | `20` | Profiles per batch |
| `MIN_DELAY` | No | `0.3` | Min delay between requests (sec) |
| `MAX_DELAY` | No | `0.5` | Max delay between requests (sec) |

### Google Sheets Setup

**Required Sheets:**
1. **ProfilesTarget** - Main profile data
2. **Target** - Scraping queue (Target mode)
3. **OnlineLog** - Online user tracking
4. **Dashboard** - Run statistics
5. **Tags** (optional) - Tag mappings

**Target Sheet Format:**
| Nickname | Status | Remarks | Source |
|----------|--------|---------|--------|
| user123 | ⚡ Pending | | Target |

**Service Account Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable Google Sheets API
3. Create Service Account → Download JSON key
4. Share your Sheet with service account email (Editor access)

---

## 🎯 Usage

### Local Execution

**Target Mode:**
```bash
# Scrape all pending targets
python main.py --mode target

# Scrape only 50 profiles
python main.py --mode target --max-profiles 50

# Custom batch size
python main.py --mode target --batch-size 10
```

**Online Mode:**
```bash
# Scrape all online users
python main.py --mode online

# Custom batch size
python main.py --mode online --batch-size 15
```

### GitHub Actions

**Setup Secrets:**
Go to Settings → Secrets → Actions, add:
- `DAMADAM_USERNAME`
- `DAMADAM_PASSWORD`
- `GOOGLE_SHEET_URL`
- `GOOGLE_CREDENTIALS_JSON` (entire credentials.json content)

**Trigger Workflows:**
- Target Mode: Manual trigger from Actions tab
- Online Mode: Runs automatically every 15 minutes

---

## 📊 Data Structure

### ProfilesTarget Sheet

| Column | Type | Description |
|--------|------|-------------|
| ID | Primary Key | Immutable profile ID |
| NICK NAME | Metadata | Current nickname (mutable) |
| TAGS | Text | User tags |
| STATUS | Text | Verified/Unverified/Banned |
| PROFILE_STATE | Enum | ACTIVE/UNVERIFIED/BANNED/DEAD |
| DATETIME SCRAP | DateTime | Last scraped timestamp |
| ... | ... | (25+ total columns) |

**Profile States:**
- `ACTIVE` - Verified, functioning profile
- `UNVERIFIED` - Account not verified
- `BANNED` - Account suspended by platform
- `DEAD` - Profile deleted/not found

### Dashboard Metrics

| Metric | Description |
|--------|-------------|
| Profiles Processed | Total profiles attempted |
| Success / Failed | Scraping success rate |
| New / Updated / Unchanged | Data freshness |
| Active / Unverified / Banned / Dead | Profile state breakdown |

---

## 🔍 Troubleshooting

### Issue: Login Failed

**Solution:**
```bash
# 1. Verify credentials in .env
cat .env | grep DAMADAM

# 2. Clear cookies and retry
rm damadam_cookies.pkl
python main.py --mode target --max-profiles 1
```

### Issue: Permission Denied (Google Sheets)

**Solution:**
1. Open your Google Sheet
2. Click "Share"
3. Add service account email from credentials.json
4. Grant "Editor" access

### Issue: No Profiles Found

**Solution:**
```bash
# Check Target sheet has pending profiles
# Status should be "⚡ Pending" or empty
```

### Issue: Invalid JSON Credentials

**Solution:**
```bash
# For GitHub Actions only:
# Copy ENTIRE credentials.json content (including braces)
# Paste into GOOGLE_CREDENTIALS_JSON secret
# Do NOT modify or format the JSON
```

---

## 📝 Project Architecture

### Core Components

**config.py**
- Environment variable management
- Column definitions
- State constants

**browser.py**
- Chrome WebDriver setup
- Cookie management
- Login handling

**sheets_manager.py**
- Google Sheets API operations
- ID-based profile updates
- State computation

**scraper_target.py**
- Target mode scraping
- Profile data extraction
- Date normalization

**scraper_online.py**
- Online mode scraping
- Online user detection

**main.py**
- Entry point
- Mode orchestration
- Stats reporting

### Data Flow

```
1. main.py → Parse arguments
2. browser.py → Setup Chrome & Login
3. sheets_manager.py → Load existing profiles (ID-based)
4. scraper_*.py → Extract profile data
5. sheets_manager.py → Write/Update profiles
6. main.py → Update dashboard & report
```

---

## 🔐 Security

**Never commit these files:**
- `.env` (local credentials)
- `credentials.json` (Google service account)
- `damadam_cookies.pkl` (session cookies)

**Use GitHub Secrets for:**
- `DAMADAM_USERNAME`
- `DAMADAM_PASSWORD`
- `GOOGLE_SHEET_URL`
- `GOOGLE_CREDENTIALS_JSON`

---

## 📈 Performance

**Typical Run Times:**
- Target Mode (50 profiles): ~3-5 minutes
- Online Mode (100 users): ~5-8 minutes

**Rate Limits:**
- DamaDam: 0.3-0.5s delay between requests
- Google Sheets: 1s delay after writes

---

## 🐛 Known Limitations

1. **No 2FA Support** - Account must not have 2FA enabled
2. **Profile Images** - Image URLs logged, not downloaded
3. **Private Profiles** - Cannot scrape private profiles
4. **Rate Limits** - Aggressive scraping may trigger temporary blocks

---

## 📞 Support

**Common Issues:**
1. Check `.env` configuration
2. Verify Google Sheet permissions
3. Review GitHub Actions logs
4. Check DamaDam account status

**For new issues:**
1. Include error logs
2. Specify mode (target/online)
3. Environment (local/GitHub Actions)

---

## 📄 License

Educational purposes only. Respect website terms of service.

---

## 🔄 Version History

**v4.0** (Current)
- ✅ ID-based primary key
- ✅ Profile state normalization
- ✅ Date normalization layer
- ✅ Nickname sanitization
- ✅ Dual-mode operation

---

**Last Updated:** December 2024  
**Status:** Production Ready  
**Tested:** Local + GitHub Actions
