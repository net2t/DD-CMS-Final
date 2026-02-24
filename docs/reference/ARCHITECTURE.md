# 🏗️ Architecture - DamaDam Scraper

**Simple visual guide to how everything works.**

---

## 🎯 Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER (You)                              │
│                        ↓                                    │
│              python main.py target                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    MAIN.PY                                  │
│  • Parse arguments                                          │
│  • Setup config                                             │
│  • Start browser & login                                    │
│  • Run Phase 1                                              │
│  • Generate reports                                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                  ↓
┌──────────────────┐           ┌──────────────────┐
│  BROWSER         │           │  GOOGLE SHEETS   │
│  (Selenium)      │           │  (gspread)       │
│                  │           │                  │
│  • Load pages    │           │  • Read RunList  │
│  • Extract data  │           │  • Write results │
│  • Handle login  │           │  • Update stats  │
└──────────────────┘           └──────────────────┘
        ↓                                  ↑
        └──────────────┬───────────────────┘
                       ↓
              ┌────────────────┐
              │  PROFILE DATA  │
              │  (23 columns)  │
              └────────────────┘
```

---

## 📁 File Organization (Layered)

```
DD-CMS-Final/
│
├─ 📋 LAYER 1: ENTRY POINT
│   └─ main.py                  ← Start here
│
├─ ⚙️  LAYER 2: CONFIGURATION
│   └─ config/
│       ├─ config_common.py     ← Base settings (LOCKED)
│       ├─ config_manager.py    ← Smart config loader
│       └─ selectors.py         ← CSS/XPath patterns
│
├─ 🔧 LAYER 3: CORE SERVICES
│   └─ core/
│       ├─ browser_manager.py   ← Browser setup
│       ├─ browser_context.py   ← Safe browser wrapper
│       ├─ login_manager.py     ← Authentication
│       └─ run_context.py       ← Shared state
│
├─ 🎯 LAYER 4: SCRAPING PHASES
│   └─ phases/
│       ├─ phase_profile.py     ← Phase 1 orchestrator
│       └─ profile/
│           ├─ online_mode.py   ← Online users scraper
│           └─ target_mode.py   ← Target list scraper
│
└─ 🛠️  LAYER 5: UTILITIES
    └─ utils/
        ├─ sheets_manager.py    ← Google Sheets
        ├─ validators.py        ← Input validation
        ├─ retry.py             ← Auto-retry
        ├─ metrics.py           ← Performance tracking
        ├─ profile_cache.py     ← Caching
        └─ ui.py                ← Terminal output
```

**Rule: Lower layers can't import higher layers!**
```
✅ phases/ can import core/, utils/, config/
✅ core/ can import utils/, config/
✅ utils/ can import config/
❌ config/ CANNOT import anything (bottom layer)
```

---

## 🔄 Data Flow (Step-by-Step)

### 1. **Start** → User runs command
```bash
python main.py target --max-profiles 10
```

### 2. **Parse** → main.py reads arguments
```
Mode: target
Max profiles: 10
Batch size: 20
```

### 3. **Config** → Load settings
```
Load .env file
  ↓
Set DAMADAM_USERNAME, PASSWORD
Set GOOGLE_SHEET_URL
  ↓
Validate all required settings
```

### 4. **Browser** → Start Chrome
```
Start Chrome (headless)
  ↓
Try cookie login
  ↓ (if failed)
Try fresh login
  ↓ (if failed)
Try backup account
```

### 5. **Sheets** → Connect to Google
```
Load credentials.json
  ↓
Authenticate with Google
  ↓
Open Profiles sheet
Open RunList sheet
```

### 6. **Phase 1** → Scrape profiles
```
Read RunList
  ↓
Filter: Status = "⚡ Pending"
  ↓
For each nickname:
  ├─ Check cache (if enabled)
  ├─ Scrape profile page
  ├─ Extract 23 data points
  ├─ Detect status (banned/verified)
  └─ Write to Profiles sheet
```

### 7. **Finish** → Clean up & report
```
Sort profiles by date
  ↓
Update Dashboard
  ↓
Generate summary
  ↓
Close browser
```

---

## 🎯 Phase System (Current + Future)

```
┌─────────────────────────────────────────────────────────┐
│                    PHASE SYSTEM                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Phase 1: PROFILES  ✅ DONE (LOCKED)                   │
│  ├─ Target mode    (from RunList)                      │
│  ├─ Online mode    (from online users)                 │
│  └─ Output: 23 columns in Profiles sheet               │
│                                                         │
│  Phase 2: POSTS  🔜 PLANNED                            │
│  ├─ Read Phase 1 "Ready" profiles (<100 posts)        │
│  ├─ Scrape individual posts                            │
│  └─ Output: New "Posts" sheet                          │
│                                                         │
│  Phase 3: MEHFILS  🔮 FUTURE                           │
│  ├─ Read mehfil links from Phase 1                     │
│  ├─ Scrape mehfil details                              │
│  └─ Output: New "Mehfils" sheet                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key Principle: Each phase is independent**
- ✅ Phase 2 doesn't modify Phase 1 data
- ✅ Each phase has its own sheet
- ✅ Phases can read other phases' output
- ❌ Phases cannot change other phases' schemas

---

## 🔐 Security Architecture

```
┌──────────────────────────────────────────┐
│         SENSITIVE DATA                   │
│  • Credentials                           │
│  • API Keys                              │
│  • Cookies                               │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│      LOCAL ENVIRONMENT                   │
│                                          │
│  .env file                               │
│  credentials.json                        │
│  *.pkl (cookies)                         │
│                                          │
│  ❌ NEVER commit to Git                 │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│      GITHUB ACTIONS                      │
│                                          │
│  GitHub Secrets                          │
│  • DAMADAM_USERNAME                      │
│  • DAMADAM_PASSWORD                      │
│  • GOOGLE_SHEET_URL                      │
│  • GOOGLE_CREDENTIALS_JSON               │
│                                          │
│  ✅ Encrypted by GitHub                 │
└──────────────────────────────────────────┘
```

**Protection Layers:**
1. `.gitignore` → Prevents accidental commits
2. Pre-commit hook → Blocks forbidden files
3. Environment variables → No hardcoding
4. GitHub Secrets → Encrypted storage

---

## 🔄 Dual Environment Support

```
┌─────────────────────────────────────────────────────────┐
│               LOCAL DEVELOPMENT                         │
├─────────────────────────────────────────────────────────┤
│  OS: Windows / Linux / Mac                              │
│  Chrome: User's installation                            │
│  ChromeDriver: Local binary                             │
│  Credentials: .env + credentials.json                   │
│  Cookies: damadam_cookies.pkl (persisted)              │
│  Logs: logs/*.log (saved locally)                       │
└─────────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────────┐
│               GITHUB ACTIONS                            │
├─────────────────────────────────────────────────────────┤
│  OS: Ubuntu (always)                                    │
│  Chrome: Auto-installed                                 │
│  ChromeDriver: Auto-installed                           │
│  Credentials: GitHub Secrets                            │
│  Cookies: None (fresh login each time)                  │
│  Logs: Uploaded as artifacts                            │
└─────────────────────────────────────────────────────────┘
```

**Auto-detection:**
```python
if Config.IS_GITHUB_ACTIONS:
    # Skip cookie persistence
    # Use minimal delays
    # Upload logs as artifacts
else:
    # Use cookie files
    # Detailed terminal output
    # Save logs locally
```

---

## 📊 Google Sheets Architecture

```
┌─────────────────────────────────────────────────────────┐
│           GOOGLE SHEETS WORKBOOK                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📄 Profiles (Main Data)                               │
│  ├─ Row 1: Headers (23 columns)                        │
│  ├─ Row 2+: Profile data                               │
│  └─ Sorted by: DATETIME SCRAP (newest first)           │
│                                                         │
│  📋 RunList (Target Queue)                             │
│  ├─ Col A: NICKNAME                                    │
│  ├─ Col B: STATUS (⚡ Pending / Done 💀)              │
│  ├─ Col C: REMARKS                                     │
│  └─ Col D: SKIP (nicknames to skip)                    │
│                                                         │
│  📝 OnlineLog (Online History)                         │
│  ├─ Date Time                                          │
│  ├─ Nickname                                           │
│  ├─ Last Seen                                          │
│  └─ Batch #                                            │
│                                                         │
│  📊 Dashboard (Run Stats)                              │
│  ├─ Run metrics (success/failed)                       │
│  ├─ Timing data                                        │
│  └─ Trend information                                  │
│                                                         │
│  🏷️  Tags (Optional)                                   │
│  └─ Nickname to tag mappings                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Performance Optimizations

### 1. **Batch Writing**
```
Without batching:
100 profiles = 100 API calls = High risk of rate limits

With batching:
100 profiles = 10 batches = 10 API calls = Safe
```

### 2. **Caching**
```
Without cache:
Same profile scraped twice = 2 × 5 seconds = 10 seconds

With cache (24h TTL):
Same profile scraped twice = 5s + 0.001s = 5 seconds
```

### 3. **Retry Logic**
```
Network error without retry:
❌ Scrape fails immediately

Network error with retry:
✅ Wait 2s → retry
✅ Wait 4s → retry
✅ Success!
```

---

## 🔧 Extension Points

**Want to add new features? Here's where:**

### Add New Field to Profile
```
❌ DON'T: Modify Phase 1 (LOCKED)
✅ DO: Create Phase 2 with new sheet
```

### Add New Scraping Mode
```
Location: phases/profile/
Create: new_mode.py
Pattern: Copy target_mode.py structure
Update: phase_profile.py to route to new mode
```

### Add New Utility
```
Location: utils/
Create: my_utility.py
Import: Can use config/ only
Test: Add to test suite
```

### Add New Phase
```
Location: phases/
Create: phase_myphase.py (orchestrator)
Create: phases/myphase/ (implementation)
Update: main.py to call new phase
```

---

## 🎓 Learning Path

**For beginners, read in this order:**

1. **README.md** - Overview + quick start
2. **ARCHITECTURE.md** (this file) - How it works
3. **docs/meta/project_rules.md** - What you can/can't change
4. **PHASE_GUIDE.md** - Phase system details
5. **SETUP_WINDOWS.md** - Platform setup
6. **Code files** - Start with main.py

**For troubleshooting:**
1. **LIMIT_HANDLING.md** - API rate limits
2. **TROUBLESHOOTING.md** - Common issues
3. **SECURITY.md** - Security best practices

---

## 📈 Scalability

**Current capacity:**
- ✅ ~1000 profiles/day (safe rate)
- ✅ 60 requests/minute limit (Google Sheets)
- ✅ Multiple accounts (backup failover)
- ✅ Batch processing (rate limit protection)

**If you need more:**
- 🔧 Use separate service accounts per phase
- 🔧 Increase delays between requests
- 🔧 Split RunList into multiple sheets
- 🔧 Run on multiple machines

---

## 🔍 Debugging Flow

```
Error occurs
  ↓
Check logs/
  ├─ Look for "ERROR" messages
  ├─ Look for "WARNING" messages
  └─ Find stack trace
  ↓
Identify layer:
  ├─ Browser error? → core/browser_*.py
  ├─ Login error? → core/login_manager.py
  ├─ Scraping error? → phases/profile/*.py
  ├─ Sheets error? → utils/sheets_manager.py
  └─ Config error? → config/*.py
  ↓
Read docs/meta/project_rules.md
  ├─ Is this a locked element?
  └─ What's the proper fix location?
  ↓
Make fix
  ↓
Test with 3 profiles
  ↓
Commit with clear message
```

---

## 🎯 Key Principles

1. **Separation of Concerns**
   - Each file has ONE job
   - No mixing of responsibilities

2. **Phase Isolation**
   - Phase 1 is locked (stable)
   - New features go in new phases

3. **Configuration Centralization**
   - All settings in config/
   - No hardcoded values

4. **Error Resilience**
   - Retry on transient failures
   - Graceful degradation
   - Always clean up resources

5. **Security First**
   - Never commit secrets
   - Environment variables only
   - Pre-commit hook protection

---

## 🎓 Glossary

**Phase** - Independent scraping module (Profile, Posts, Mehfil)

**Target Mode** - Scrape from RunList sheet

**Online Mode** - Scrape currently online users

**Batch Writer** - Queue multiple writes to avoid rate limits

**TTL** - Time To Live (cache expiration time)

**Selector** - CSS or XPath pattern to find HTML elements

**Rate Limit** - API request limit (60/minute for Google Sheets)

**Context Manager** - Python pattern for automatic cleanup (`with` statement)

**Artifact** - File saved by GitHub Actions after run

---

**Questions?** Read docs/meta/project_rules.md next!
