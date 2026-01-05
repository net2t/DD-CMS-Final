# 🚀 DamaDam Scraper v2.100.0.18

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)
![Phase](https://img.shields.io/badge/phase-1%20Complete-success.svg)

**Professional automation bot for scraping DamaDam.pk user profiles**

[Features](#-features) • [Quick Start](#-quick-start-5-minutes) • [Documentation](#-documentation) • [Support](#-support)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start-5-minutes)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Dual Environment Support](#-dual-environment-support)
- [Phase System](#-phase-system)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🌟 Overview

DamaDam Scraper is a production-ready automation tool designed to efficiently scrape user profiles from DamaDam.pk. Built with reliability, security, and scalability in mind, it features a multi-phase architecture that allows for targeted data collection across different aspects of the platform.

### Current Status: Phase 1 Complete ✅

**Phase 1 (Profiles)** includes:
- ✅ Target Mode: Scrape profiles from a predefined list
- ✅ Online Mode: Scrape currently online users
- ✅ Dual account system for failover
- ✅ Cookie-based session persistence
- ✅ Comprehensive error handling and retry logic
- ✅ Beautiful terminal UI with progress tracking
- ✅ Google Sheets integration with duplicate detection
- ✅ GitHub Actions automation

**Upcoming Phases:**
- 🔜 Phase 2: Posts scraping
- 🔜 Phase 3: Mehfil (groups) scraping
- 🔜 Phase 4: Comments scraping

---

## ✨ Features

### 🎯 Multi-Mode Operation
- **Target Mode**: Process profiles from 'RunList' sheet (manual/scheduled)
- **Online Mode**: Scrape currently online users (auto-scheduled every 15 min)
- **Test Mode**: Quick testing with predefined profiles

### 🔐 Robust Authentication
- Cookie-based session persistence (faster subsequent runs)
- Dual account system with automatic failover
- Prevents account blocking from repeated logins
- GitHub Actions ready (no local file dependencies)

### 📊 Smart Data Management
- Nickname-based duplicate detection
- Profile state tracking (ACTIVE, UNVERIFIED, BANNED, DEAD)
- Phase 2 eligibility marking (< 100 posts)
- Automatic sorting by scrape date
- Preserves existing data when scraping returns blanks

### 🎨 Modern Terminal UI
- Rich color-coded output with emojis
- Real-time progress tracking with numeric emojis
- Comprehensive summary reports at end of run
- Important events log for quick issue identification

### 🛡️ Resilient & Scalable
- API rate limit handling with exponential backoff
- Session timeout recovery
- Multiple selector fallbacks for data extraction
- Centralized configuration management
- Comprehensive logging system

### 🔄 Dual Environment Support
- **Local Development**: Runs on Windows/Linux/Mac with local ChromeDriver
- **GitHub Actions**: Fully automated cloud execution
- Automatic environment detection and adaptation

---

## 📁 Project Structure

```
DD-CMS-Final/
├── .github/
│   └── workflows/              # GitHub Actions workflows
│       ├── scrape-online.yml   # Online mode (every 15 min)
│       └── scrape-target.yml   # Target mode (every 55 min)
│
├── .githooks/
│   └── pre-commit              # Security pre-commit hook
│
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── config_common.py        # Base configuration (LOCKED)
│   ├── config_online.py        # Online mode overrides
│   ├── config_target.py        # Target mode overrides
│   ├── config_test.py          # Test mode configuration
│   └── selectors.py            # CSS/XPath selectors
│
├── core/                       # Core components
│   ├── browser_manager.py      # Browser lifecycle management
│   ├── login_manager.py        # Authentication with fallback
│   └── run_context.py          # Shared run state
│
├── phases/                     # Scraping phases
│   ├── __init__.py
│   ├── phase_profile.py        # Phase 1 orchestrator
│   ├── phase_mehfil.py         # Phase 3 (stub)
│   ├── phase_posts.py          # Phase 2 (stub)
│   └── profile/
│       ├── online_mode.py      # Online users scraper
│       └── target_mode.py      # Target list scraper + core logic
│
├── utils/                      # Utility modules
│   ├── sheets_manager.py       # Google Sheets operations
│   ├── ui.py                   # Terminal UI and logging
│   └── url_builder.py          # URL construction helpers
│
├── logs/                       # Run logs (auto-generated)
│
├── docs/                       # Documentation
│   ├── guides/
│   │   ├── SETUP_WINDOWS.md       # Windows setup guide
│   │   ├── TESTING.md             # Testing guide
│   │   ├── LIMIT_HANDLING.md      # Rate limit recovery guide
│   │   ├── GITHUB_ACTIONS_GUIDE.md # GitHub Actions guide
│   │   └── TROUBLESHOOTING.md     # Common issues and solutions
│   ├── reference/
│   │   └── ARCHITECTURE.md        # System architecture overview
│   ├── notes/                    # Batch notes / internal notes (committed)
│   └── private/                  # Local-only notes (gitignored)
│
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── CHANGELOG.md               # Version history
├── ISSUE_DOC.md              # Issue tracking
├── LICENSE                    # License information
├── README.md                  # This file
├── SECURITY.txt              # Security guidelines
├── main.py                    # Application entry point
└── requirements.txt           # Python dependencies
```

---

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.9 or higher
- Google Chrome browser
- Git
- Google Service Account with Sheets API enabled

### Step 1: Clone Repository
```bash
git clone https://github.com/net2t/DD-CMS-Final.git
cd DD-CMS-Final
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Setup Credentials

#### A. Create `.env` file
```bash
cp .env.example .env
```

#### B. Edit `.env` with your credentials
```bash
# Use your preferred editor
nano .env  # or: code .env, vim .env, notepad .env
```

Required values:
```env
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password
DAMADAM_USERNAME_2=backup_username  # Optional but recommended
DAMADAM_PASSWORD_2=backup_password
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

#### C. Add Google Service Account
1. Download `credentials.json` from Google Cloud Console
2. Place it in project root directory
3. Share your Google Sheet with the service account email

### Step 4: Setup Security Hooks
```bash
# Make pre-commit hook executable
chmod +x .githooks/pre-commit

# Configure git to use custom hooks
git config core.hooksPath .githooks
```

### Step 5: Prepare Google Sheet

Create a Google Sheet with these tabs:
- **Profiles**: Main data storage (headers auto-created)
- **RunList**: Target queue (columns: NICKNAME, STATUS, REMARKS, SKIP)
- **OnlineLog**: Online users log (auto-created)
- **Dashboard**: Run statistics (auto-created)

### Step 6: Run Your First Scrape
```bash
# Test mode (3 profiles)
python main.py test --max-profiles 3

# Target mode (from RunList)
python main.py target --max-profiles 10

# Online mode (current online users)
python main.py online --max-profiles 20
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DAMADAM_USERNAME` | Yes | - | Primary DamaDam account username |
| `DAMADAM_PASSWORD` | Yes | - | Primary account password |
| `DAMADAM_USERNAME_2` | Recommended | - | Backup account username (prevents blocking) |
| `DAMADAM_PASSWORD_2` | Recommended | - | Backup account password |
| `GOOGLE_SHEET_URL` | Yes | - | Full URL of your Google Sheet |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `credentials.json` | Path to service account JSON |
| `GOOGLE_CREDENTIALS_JSON` | No | - | Raw JSON (for GitHub Actions) |
| `MAX_PROFILES_PER_RUN` | No | `0` | Max profiles per run (0 = unlimited) |
| `BATCH_SIZE` | No | `20` | Batch size for processing |
| `MIN_DELAY` | No | `0.3` | Minimum delay between requests (seconds) |
| `MAX_DELAY` | No | `0.5` | Maximum delay between requests (seconds) |
| `PAGE_LOAD_TIMEOUT` | No | `30` | Page load timeout (seconds) |
| `SHEET_WRITE_DELAY` | No | `1.0` | Delay between sheet writes (seconds) |

### Google Sheets Structure

#### Profiles Sheet (Auto-created)
Stores all scraped profile data with 23 columns:

| Column | Description | Example |
|--------|-------------|---------|
| ID | User ID | `3405367` |
| NICK NAME | Username | `user123` |
| TAGS | User tags | `VIP, Active` |
| CITY | City | `KARACHI` |
| GENDER | Gender | `MALE` |
| MARRIED | Marital status | `YES` |
| AGE | Age | `25` |
| JOINED | Join date | `01-jan-24` |
| FOLLOWERS | Follower count | `150` |
| STATUS | Account status | `Verified` |
| POSTS | Post count | `45` |
| RUN MODE | Source | `ONLINE` |
| DATETIME SCRAP | Scrape timestamp | `04-jan-26 03:45 pm` |
| LAST POST | Last post URL | `https://...` |
| LAST POST TIME | Post timestamp | `03-jan-26 11:20 pm` |
| IMAGE | Profile image URL | `https://...` |
| PROFILE LINK | Profile URL | `https://...` |
| POST URL | Public posts URL | `https://...` |
| RURL | Rank star image | `https://...` |
| MEH NAME | Mehfil names | Multi-line |
| MEH LINK | Mehfil URLs | Multi-line |
| MEH DATE | Mehfil join dates | Multi-line |
| PHASE 2 | Eligibility | `Ready` / `Not Eligible` |

#### RunList Sheet (Manual Setup)
Queue for Target mode:

| NICKNAME | STATUS | REMARKS | SKIP |
|----------|--------|---------|------|
| user123 | ⚡ Pending | | |
| user456 | Done 💀 | Profile updated | |
| skipme | Done 💀 | | YES |

**SKIP Column Usage:**
- Add nicknames to skip (one per line or comma-separated)
- Affects both Target and Online modes
- Useful for blocking unwanted profiles

#### OnlineLog Sheet (Auto-created)
Logs all online user sightings:

| Date Time | Nickname | Last Seen | Batch # |
|-----------|----------|-----------|---------|
| 04-jan-26 03:45 pm | user123 | 04-jan-26 03:45 pm | 20260104_1545 |

#### Dashboard Sheet (Auto-created)
Run statistics and metrics:

| RUN# | TIMESTAMP | PROFILES | SUCCESS | FAILED | NEW | UPDATED | DIFF | UNCHANGED | TRIGGER | START | END |
|------|-----------|----------|---------|--------|-----|---------|------|-----------|---------|-------|-----|

---

## Usage

### Command Line Interface

```bash
# Basic syntax
python main.py <mode> [options]

# Modes: target, online, test
# Options:
#   --max-profiles N    Limit to N profiles (0 = unlimited)
#   --batch-size N      Set batch size (default: 20)
```

### Examples

```bash
# Target mode: Process 50 profiles from RunList
python main.py target --max-profiles 50

# Target mode: Process ALL pending targets
python main.py target --max-profiles 0

# Online mode: Scrape 30 currently online users
python main.py online --max-profiles 30

# Test mode: Quick test with 3 profiles
python main.py test --max-profiles 3

# Custom batch size
python main.py target --max-profiles 100 --batch-size 10
```

### Expected Output

```
================================================================================
🚀 DamaDam Scraper - TARGET MODE 🚀
Version: v2.100.0.18
Powered by Selenium + Google Sheets
================================================================================

🎯 Mode                TARGET
🔢 Max Profiles        50
📦 Batch Size          20

🔐 Starting authentication...
✅ Cookie login successful

=== RUNNING PROFILE PHASE (TARGET MODE) ===
Processing 50 profile(s)...

1️⃣ [████████████████████] user123 (new)
2️⃣ [████████████████████] user456 (updated)
3️⃣ [████████████████████] user789 (unchanged)
...

📊 Scraping Run Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Metric            ┃      Value ┃  Status ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 🎯 Mode           │     TARGET │         │
│ ✅ Successful     │         48 │      ✅ │
│ ❌ Failed         │          2 │      ❌ │
│ 🆕 New Profiles   │         30 │         │
│ 🔄 Updated        │         18 │         │
│ 💤 Unchanged      │          0 │         │
│ 🚩 Phase 2 READY  │         45 │         │
│ ⛔ NOT ELIGIBLE   │          3 │         │
│ ⏱️ Duration       │   4m 23s  │      ⚡ │
└───────────────────┴────────────┴─────────┘

🎉 Run completed successfully!
```

---

## Dual Environment Support

The scraper intelligently adapts to its runtime environment:

### Local Development (Windows/Mac/Linux)

**Features:**
- Uses local ChromeDriver (auto-detected or from `CHROMEDRIVER_PATH`)
- Cookie-based session persistence (saves `damadam_cookies.pkl`)
- Detailed terminal output with colors and emojis
- Logs saved to `logs/` directory

**Setup:**
```bash
# Windows
python main.py target --max-profiles 10

# Linux/Mac
python3 main.py target --max-profiles 10

# With custom ChromeDriver
set CHROMEDRIVER_PATH=C:\path\to\chromedriver.exe  # Windows
export CHROMEDRIVER_PATH=/path/to/chromedriver      # Linux/Mac
python main.py target --max-profiles 10
```

### GitHub Actions (Cloud)

**Features:**
- Automatic ChromeDriver installation
- No cookie persistence (fresh login each time)
- Credentials from GitHub Secrets
- Automated scheduling (cron)
- Log artifacts uploaded after each run

**Setup:**

1. **Add Repository Secrets** (Settings → Secrets and variables → Actions):
   - `DAMADAM_USERNAME`
   - `DAMADAM_PASSWORD`
   - `DAMADAM_USERNAME_2` (recommended)
   - `DAMADAM_PASSWORD_2`
   - `GOOGLE_SHEET_URL`
   - `GOOGLE_CREDENTIALS_JSON` (full JSON content)

2. **Workflows are pre-configured:**
   - **Online Mode**: Runs every 15 minutes automatically
   - **Target Mode**: Runs every 55 minutes automatically
   - Both support manual triggering

3. **Manual Trigger:**
   - Go to **Actions** tab
   - Select workflow (Online or Target)
   - Click **Run workflow**
   - Set parameters (max_profiles, batch_size)

---

## Phase System

### Current: Phase 1 (Profiles) 

**Status**: Complete and locked  
**Target Lock Version**: v2.100.1.00

**What Phase 1 Does:**
- Scrapes complete user profiles
- Extracts 23 data points per profile
- Handles banned/unverified/suspended accounts
- Marks eligibility for Phase 2
- Supports both Target and Online modes

**Profile Data Extracted:**
- Basic info: ID, nickname, city, gender, age, marital status
- Activity: Followers, posts, join date, last post
- Status: Verified, banned, unverified
- Media: Profile image, rank star
- Community: Mehfil memberships
- Links: Profile URL, public posts URL

### Upcoming: Phase 2 (Posts) 

**Status**: Planned, not started  
**Prerequisites**: Phase 1 locked and approved

**What Phase 2 Will Do:**
- Scrape individual posts from eligible profiles
- Extract post content, images, timestamps
- Track likes, shares, comments count
- Link posts to profiles
- Support pagination and filtering

**Eligibility Criteria:**
- Profile must have < 100 posts
- Profile must be ACTIVE status
- Column "PHASE 2" = "Ready"

### Future: Phase 3 (Mehfils) 

**Status**: Planned for future release

**What Phase 3 Will Do:**
- Scrape Mehfil (group) details
- Extract member lists
- Track Mehfil activity
- Link Mehfils to profiles

### Architecture Benefits

**Why Phases?**
1. **Modularity**: Each phase is independent
2. **Scalability**: Add new phases without breaking existing ones
3. **Flexibility**: Run specific phases based on needs
4. **Maintainability**: Clear separation of concerns
5. **Evolution**: Easy to extend with new data types

**Phase Principles:**
- Each phase has dedicated configuration
- Each phase can use separate Google credentials
- Phases share core infrastructure (browser, login, sheets)
- Locked phases maintain output stability
- New phases added without modifying locked ones

---

## Troubleshooting

### Common Issues

#### 1. Login Fails

**Symptoms:**
- "Login failed" error
- Cookie login fails repeatedly

**Solutions:**
```bash
# Delete cookie file
rm damadam_cookies.pkl  # Linux/Mac
del damadam_cookies.pkl # Windows

# Run with fresh login
python main.py target --max-profiles 3

# If still failing, check credentials
nano .env  # Verify username/password
```

#### 2. Google Sheets API Rate Limit (429 Error)

**Symptoms:**
- "API rate limit hit" warnings
- Frequent retries during sheet writes

**Solutions:**
```bash
# Option 1: Increase delay in .env
SHEET_WRITE_DELAY=2.0  # Increase from 1.0

# Option 2: Reduce batch size
python main.py target --batch-size 10  # Instead of 20

# Option 3: Use separate service accounts for different phases
# (Advanced - see Phase System documentation)
```

#### 3. ChromeDriver Not Found

**Symptoms:**
- "ChromeDriver not found" error
- Browser fails to start

**Solutions:**
```bash
# Option 1: Install ChromeDriver globally
# Visit: https://chromedriver.chromium.org/
# Add to PATH

# Option 2: Specify path in .env
CHROMEDRIVER_PATH=/path/to/chromedriver

# Option 3: Let system find it
# (Works in GitHub Actions automatically)
```

#### 4. No Pending Targets Found

**Symptoms:**
- "No pending targets found" message
- Target mode exits immediately

**Solutions:**
```bash
# Check RunList sheet:
# 1. Ensure STATUS column contains "⚡ Pending" (exact text)
# 2. Verify nicknames are in column A
# 3. Remove SKIP column entries if present

# Test with specific profile
python main.py test --max-profiles 1
```

#### 5. Profiles Showing Blank Data

**Symptoms:**
- POSTS, FOLLOWERS, IMAGE columns empty
- "Failed to extract" warnings in logs

**Solutions:**
```bash
# This is usually due to HTML changes on the website
# Check logs for selector errors
cat logs/target_*.log | grep "WARNING"

# Report issue with:
# - Profile URL
# - Missing fields
# - Log file contents
```

### Recovery from Interruptions

If scraper stops unexpectedly:

1. **Check logs:**
```bash
# View latest log
tail -n 50 logs/target_*.log

# Search for errors
grep ERROR logs/*.log
```

2. **Resume from where it stopped:**
```bash
# Target mode automatically processes only "Pending" profiles
python main.py target --max-profiles 0

# Online mode can be re-run safely (logs duplicates)
python main.py online --max-profiles 20
```

3. **Verify sheet data:**
- Open Google Sheet
- Check last scrape timestamps
- Verify data integrity
- Check Dashboard for run statistics

### Debug Mode

For detailed debugging:

```bash
# Enable detailed logs (currently not configurable via CLI)
# Logs are automatically saved to logs/ directory

# View real-time logs
tail -f logs/target_*.log  # Linux/Mac
Get-Content logs\target_*.log -Wait  # Windows PowerShell
```

---

## Security

### Critical Rules

**NEVER commit these files:**
- `credentials.json`
- `.env`
- `*.pkl` (cookie files)
- Any file with real passwords/tokens

**ALWAYS use:**
- `.env.example` (templates only)
- GitHub Secrets (for CI/CD)
- `.gitignore` (properly configured)
- Pre-commit hooks (automatic checks)

### Security Checklist

Before committing:
- Run `git status` and verify no sensitive files staged
- Pre-commit hook passed
- No hardcoded credentials in code
- `.env` file is gitignored

Weekly:
- Rotate credentials if team member leaves
- Review GitHub Actions logs for exposed secrets
- Check repository access permissions

### Incident Response

If credentials leaked:
1. **Immediate**: Rotate all passwords (within 1 hour)
2. **Clean history**: Use `git-filter-repo` to remove secrets
3. **Monitor**: Check for abuse on DamaDam/Google Sheets
4. **Document**: Record incident and actions taken

 See [SECURITY.txt](SECURITY.txt) for detailed guidelines.

---

## Contributing

### Development Workflow

1. **Create feature branch:**
```bash
git checkout -b feature/my-feature
```

2. **Make changes and test:**
```bash
# Test with small dataset
python main.py test --max-profiles 3
```

3. **Commit with meaningful messages:**
```bash
git add .
git commit -m "feat: add XYZ feature"
```

4. **Push and create Pull Request:**
```bash
git push origin feature/my-feature
# Create PR on GitHub
```

### Code Standards

- **Python**: Follow PEP 8 style guide
- **Docstrings**: Use Google-style docstrings
- **Comments**: Explain why, not what
- **Naming**: Use descriptive variable names
- **Testing**: Test with 3-4 profiles before committing

### Reporting Issues

**Before reporting:**
 1. Check [TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)
 2. Search existing issues
 3. Test with latest version

**When reporting:**
```markdown
**Environment:**
- OS: Windows 10 / Ubuntu 22.04 / Mac OS
- Python: 3.9.5
- Scraper Version: v2.100.0.18

**Issue:**
Brief description of the problem

**Steps to Reproduce:**
1. Run command: python main.py target --max-profiles 10
2. Observe error: ...

**Expected:**
What should happen

**Actual:**
What actually happened

**Logs:**
```
Paste relevant log snippets
```
```

---

## 📄 License

This project is for **educational purposes only**. 

- ✅ Free to use for learning and research
- ✅ Free to modify for personal use
- ❌ Commercial use prohibited
- ❌ Redistribution without attribution prohibited

Please respect DamaDam.pk's Terms of Service and robots.txt.

---

## 💬 Support

### Get Help

- 📧 **Email**: net2outlawzz@gmail.com
- 📸 **Instagram**: [@net2nadeem](https://instagram.com/net2nadeem)
- 🐛 **Issues**: [GitHub Issues](https://github.com/net2t/DD-CMS-Final/issues)

### Documentation

- 📖 [Setup Guide](docs/guides/SETUP_WINDOWS.md) - Detailed installation instructions
- 🧪 [Testing Guide](docs/guides/TESTING.md) - Quick testing checklist
- 🔧 [Troubleshooting](docs/guides/TROUBLESHOOTING.md) - Common issues and solutions
- 🚦 [Rate Limit Handling](docs/guides/LIMIT_HANDLING.md) - Recovery steps for 429/limits
- 🔧 [GitHub Actions Guide](docs/guides/GITHUB_ACTIONS_GUIDE.md) - CI/CD troubleshooting
- 🏗️ [Architecture](docs/reference/ARCHITECTURE.md) - System design overview
- 🔒 [Security](SECURITY.txt) - Security best practices
- 📝 [Changelog](CHANGELOG.md) - Version history

---

## 🏆 Credits

**Developed by:**
- **Author**: Nadeem
- **Email**: net2outlawzz@gmail.com  
- **Social**: @net2nadeem (Instagram, Facebook)
- **AI Assistant**: Claude (Anthropic)

**Special Thanks:**
- Selenium community
- gspread contributors
- Rich library developers

---

## 📊 Project Stats

- **Lines of Code**: ~3,500
- **Modules**: 15
- **Test Coverage**: TBD (Phase 1 lock target)
- **Documentation Pages**: 7
- **Supported Platforms**: Windows, Linux, macOS
- **Deployment Options**: Local + GitHub Actions

---

<div align="center">

**Made with ❤️ by Nadeem**

[⬆ Back to Top](#-damadam-scraper-v21000018)

</div>
