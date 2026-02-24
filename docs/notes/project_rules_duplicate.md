# 🔒 PROJECT RULES - GLOBAL ARCHITECTURE LOCK

**CRITICAL: READ THIS FIRST BEFORE ANY CODE CHANGES**

This document defines the **immutable rules** for the DamaDam Scraper project. These rules prevent code mixing, maintain consistency, and ensure stability.

---

## 🚨 PHASE 1 IS LOCKED - NO MODIFICATIONS ALLOWED

### What "LOCKED" Means

**Phase 1 (Profiles)** is **PRODUCTION STABLE** as of **v2.100.0.18**

```
┌─────────────────────────────────────────────────────┐
│  ⚠️  PHASE 1 IS LOCKED - READ CAREFULLY  ⚠️          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ✅ ALLOWED:                                        │
│     • Bug fixes (with tests)                       │
│     • Performance optimizations (if output same)   │
│     • Documentation updates                        │
│     • Internal refactoring (no API changes)        │
│                                                     │
│  ❌ FORBIDDEN:                                      │
│     • Schema changes (COLUMN_ORDER)                │
│     • New columns in Profiles sheet                │
│     • Changing output format                       │
│     • Modifying data types                         │
│     • Breaking changes to core functions           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📁 FILE ORGANIZATION RULES

### Rule #1: One Purpose Per File

**Each file has ONE clear purpose. DO NOT MIX concerns.**

```
❌ BAD: scraper.py
   - Browser management
   - Login logic
   - Profile scraping
   - Sheet operations
   - URL building
   (5 different concerns in one file = MIXING!)

✅ GOOD: 
   core/browser_manager.py      - Browser only
   core/login_manager.py         - Login only
   phases/profile/target_mode.py - Profile scraping only
   utils/sheets_manager.py       - Sheets only
   utils/url_builder.py          - URLs only
```

### Rule #2: File Location Must Match Purpose

```
config/          → Configuration ONLY
core/            → Core infrastructure (browser, login, context)
phases/          → Scraping phases (profile, posts, mehfil)
phases/profile/  → Phase 1 specific code
utils/           → Utilities (sheets, UI, validators, metrics)
```

**❌ NEVER put scraping code in config/**
**❌ NEVER put config code in phases/**
**❌ NEVER put browser code in utils/**

### Rule #3: Import Hierarchy

```
┌─────────────┐
│   main.py   │  ← Entry point only
└──────┬──────┘
       │
       ├─→ config/        → Can import: (nothing)
       ├─→ core/          → Can import: config, utils
       ├─→ phases/        → Can import: config, core, utils
       └─→ utils/         → Can import: config
```

**Rule: Lower layers CANNOT import higher layers**

```python
# ❌ FORBIDDEN
# In config/config_common.py:
from phases.profile.target_mode import scrape_profile  # NO!

# ✅ ALLOWED
# In phases/profile/target_mode.py:
from config.config_common import Config  # YES!
from utils.validators import NicknameValidator  # YES!
```

---

## 🔐 PHASE 1 LOCKED SCHEMA

### Locked: Column Order (23 columns)

```python
# config/config_common.py - LOCKED, DO NOT MODIFY

COLUMN_ORDER = [
    "ID",                  # 0  - LOCKED
    "NICK NAME",          # 1  - LOCKED
    "TAGS",               # 2  - LOCKED
    "CITY",               # 3  - LOCKED
    "GENDER",             # 4  - LOCKED
    "MARRIED",            # 5  - LOCKED
    "AGE",                # 6  - LOCKED
    "JOINED",             # 7  - LOCKED
    "FOLLOWERS",          # 8  - LOCKED
    "STATUS",             # 9  - LOCKED
    "POSTS",              # 10 - LOCKED
    "SKIP/DEL",           # 11 - LOCKED (displays as "RUN MODE")
    "DATETIME SCRAP",     # 12 - LOCKED
    "LAST POST",          # 13 - LOCKED
    "LAST POST TIME",     # 14 - LOCKED
    "IMAGE",              # 15 - LOCKED
    "PROFILE LINK",       # 16 - LOCKED
    "POST URL",           # 17 - LOCKED
    "RURL",               # 18 - LOCKED
    "MEH NAME",           # 19 - LOCKED
    "MEH LINK",           # 20 - LOCKED
    "MEH DATE",           # 21 - LOCKED
    "PHASE 2"             # 22 - LOCKED
]

# ⚠️ TO ADD NEW COLUMNS: Create Phase 2 with new sheet
# DO NOT modify COLUMN_ORDER above!
```

### Locked: Output Formats

```python
# LOCKED - DO NOT CHANGE THESE FORMATS

# Date format: "dd-mmm-yy hh:mm a"
# Example: "04-jan-26 03:45 pm"
DATETIME_FORMAT = "%d-%b-%y %I:%M %p"

# Status values (uppercase):
PROFILE_STATE_ACTIVE = "ACTIVE"
PROFILE_STATE_UNVERIFIED = "UNVERIFIED"
PROFILE_STATE_BANNED = "BANNED"
PROFILE_STATE_DEAD = "DEAD"

# Gender values (uppercase):
GENDER_MALE = "MALE"
GENDER_FEMALE = "FEMALE"

# Married values (uppercase):
MARRIED_YES = "YES"
MARRIED_NO = "NO"

# Phase 2 eligibility:
PHASE2_READY = "Ready"
PHASE2_NOT_ELIGIBLE = "Not Eligible"
```

### Locked: Sheet Names

```python
# LOCKED - DO NOT RENAME THESE SHEETS

SHEET_PROFILES = "Profiles"      # Main data
SHEET_TARGET = "RunList"         # Target queue
SHEET_DASHBOARD = "Dashboard"    # Run stats
SHEET_TAGS = "Tags"              # Tag mappings
SHEET_ONLINE_LOG = "OnlineLog"   # Online history
```

---

## 🎯 PHASE SYSTEM RULES

### Rule #4: Phase Isolation

**Each phase is INDEPENDENT. Phases cannot modify other phases' data.**

```
Phase 1 (Profiles) → Sheet: "Profiles"
Phase 2 (Posts)    → Sheet: "Posts"       (future)
Phase 3 (Mehfils)  → Sheet: "Mehfils"     (future)

❌ Phase 2 CANNOT add columns to "Profiles" sheet
❌ Phase 3 CANNOT modify Phase 1 code
✅ Phases share core infrastructure (browser, login)
✅ Phases can read other phases' output (read-only)
```

### Rule #5: Phase File Structure

```
phases/
├── __init__.py
├── phase_profile.py       ← Phase 1 orchestrator (LOCKED)
├── phase_posts.py         ← Phase 2 orchestrator (stub)
├── phase_mehfil.py        ← Phase 3 orchestrator (stub)
└── profile/               ← Phase 1 implementation
    ├── online_mode.py     ← LOCKED
    └── target_mode.py     ← LOCKED
```

**Adding Phase 2:**
```
phases/
└── posts/                 ← NEW directory for Phase 2
    ├── __init__.py
    ├── scraper.py        ← Post scraping logic
    └── processor.py      ← Post data processing
```

**❌ DO NOT mix Phase 2 code into profile/ directory!**

### Rule #6: Phase Activation

```python
# main.py - Phase activation pattern

def main():
    # Phase 1: ALWAYS active (locked)
    stats, sheets = phase_profile.run(context, mode, max_profiles)
    
    # Phase 2: Activate when ready (currently commented)
    # if phase2_enabled:
    #     phase_posts.run(context)
    
    # Phase 3: Activate when ready (currently commented)
    # if phase3_enabled:
    #     phase_mehfil.run(context)
```

---

## 🏗️ ARCHITECTURE RULES

### Rule #7: Core Components (STABLE)

**These files provide infrastructure. They are STABLE but not locked.**

```
core/
├── browser_manager.py      → Browser lifecycle
├── browser_context.py      → Context manager (NEW in BATCH 2)
├── login_manager.py        → Authentication
└── run_context.py          → Shared state

Changes allowed: Internal improvements only
Changes forbidden: Breaking API changes
```

### Rule #8: Configuration Layer (SEMI-LOCKED)

```
config/
├── config_common.py        → Base config (PHASE 1 LOCKED)
├── config_manager.py       → Config system (NEW in BATCH 2)
├── config_online.py        → Online overrides
├── config_target.py        → Target overrides
├── config_test.py          → Test mode config
└── selectors.py            → CSS/XPath selectors

LOCKED in config_common.py:
  - COLUMN_ORDER
  - DEFAULT_VALUES
  - PROFILE_STATE_* constants
  - SHEET_* names

NOT LOCKED:
  - Delays, timeouts
  - Browser settings
  - Selectors (can update for site changes)
```

### Rule #9: Utility Layer (FLEXIBLE)

```
utils/
├── sheets_manager.py       → Google Sheets operations
├── ui.py                   → Terminal UI
├── url_builder.py          → URL construction
├── validators.py           → Input validation (NEW in BATCH 2)
├── retry.py                → Retry decorator (NEW in BATCH 2)
└── metrics.py              → Performance tracking (NEW in BATCH 2)

Changes allowed: Add new utilities anytime
Changes forbidden: Breaking existing utility APIs
```

---

## 📝 CODING RULES

### Rule #10: No Magic Numbers

```python
# ❌ BAD
time.sleep(60)
if len(nickname) > 50:
    return False

# ✅ GOOD
from config.config_common import Config
time.sleep(Config.SHEET_WRITE_DELAY)

from utils.validators import NicknameValidator
if len(nickname) > NicknameValidator.MAX_LENGTH:
    return False
```

### Rule #11: All Functions Must Have Docstrings

```python
# ❌ BAD
def scrape(nick):
    # scrapes profile
    pass

# ✅ GOOD
def scrape_profile(nickname: str, source: str = "Target") -> dict | None:
    """
    Scrape complete user profile from DamaDam.
    
    Args:
        nickname: The DamaDam username to scrape.
        source: Origin of scrape request.
    
    Returns:
        Dictionary with profile data or None on failure.
    
    Example:
        >>> profile = scrape_profile("user123")
        >>> print(profile['CITY'])
    """
    pass
```

### Rule #12: Error Handling Pattern

```python
# Standard error handling pattern

from utils.ui import log_msg
from utils.retry import retry_on_failure

@retry_on_failure(max_attempts=3, delay=2)
def operation_that_may_fail():
    """Operation description."""
    try:
        # Main logic
        result = do_work()
        return result
    
    except SpecificException as e:
        log_msg(f"Specific error: {e}", "ERROR")
        raise  # Re-raise for retry
    
    except Exception as e:
        log_msg(f"Unexpected error: {e}", "ERROR")
        raise

# ❌ DO NOT use bare except:
except:
    pass  # Silent failure!
```

### Rule #13: Import Organization

```python
# Standard import order:

# 1. Standard library
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 2. Third-party
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By

# 3. Local (grouped by layer)
from config.config_common import Config
from core.browser_manager import BrowserManager
from phases.profile.target_mode import scrape_profile
from utils.ui import log_msg
from utils.validators import NicknameValidator
```

---

## 🔄 VERSION CONTROL RULES

### Rule #14: Branch Strategy

```
main                → Production-ready code only
├── feature/*       → New features
├── fix/*           → Bug fixes
├── docs/*          → Documentation
└── phase/*         → New phases

Examples:
  feature/add-retry-decorator
  fix/selector-update
  docs/update-readme
  phase/posts-scraping
```

### Rule #15: Commit Message Format

```
<type>(<scope>): <subject>

Types:
  feat     → New feature
  fix      → Bug fix
  docs     → Documentation
  style    → Code formatting
  refactor → Code restructuring
  perf     → Performance improvement
  test     → Adding tests
  chore    → Build/tooling changes

Examples:
  feat(profile): add retry decorator for network operations
  fix(sheets): preserve POSTS value when blank
  docs: update LIMIT_HANDLING.md with recovery steps
  refactor(core): extract browser context manager
```

### Rule #16: What to Commit

```
✅ ALWAYS COMMIT:
  - Source code (.py files)
  - Documentation (.md files)
  - Configuration templates (.env.example)
  - Requirements (requirements.txt)
  - Git hooks (.githooks/)

❌ NEVER COMMIT:
  - Credentials (credentials.json, .env)
  - Cookies (*.pkl)
  - Logs (*.log, logs/)
  - Cache (__pycache__, *.pyc)
  - Local data (output/, downloads/)
```

---

## 🧪 TESTING RULES

### Rule #17: Test Before Commit

```bash
# MANDATORY before every commit:

# 1. Test mode (quick smoke test)
python main.py test --max-profiles 3

# 2. Affected mode
python main.py target --max-profiles 5  # if changed target
python main.py online --max-profiles 5  # if changed online

# 3. Check logs
cat logs/*.log | grep "ERROR"
cat logs/*.log | grep "WARNING"

# 4. Verify sheet output
# Open Google Sheet, check last 5 profiles
```

### Rule #18: Test Cases (Minimum)

```python
# For any new validator/function, test these:

def test_nickname_validator():
    # Valid cases
    assert validate("user123") == "user123"
    assert validate("user@name") == "user@name"
    
    # Invalid cases
    assert validate("") is None
    assert validate("user name") is None  # whitespace
    assert validate("a" * 51) is None     # too long
    assert validate("user<script>") is None  # dangerous

# For any new scraper function, test these profiles:
TEST_PROFILES = [
    "normal_user",      # Standard profile
    "banned_user",      # Banned/suspended
    "unverified_user",  # Unverified
    "new_user",         # < 100 posts (Phase 2 ready)
    "power_user",       # > 100 posts (not eligible)
]
```

---

## 📊 PERFORMANCE RULES

### Rule #19: Rate Limiting

```python
# MANDATORY: Always respect rate limits

from config.config_common import Config
import time

# Between profile scrapes
time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

# Between sheet writes
time.sleep(Config.SHEET_WRITE_DELAY)

# After API 429 error
wait_times = [60, 120, 180]  # Exponential backoff
```

### Rule #20: Resource Cleanup

```python
# MANDATORY: Always clean up resources

# ✅ GOOD: Use context manager
with BrowserContext() as driver:
    scrape_profiles(driver)
# Browser automatically closed

# ❌ BAD: Manual cleanup (easy to forget)
driver = start_browser()
scrape_profiles(driver)
driver.quit()  # What if error occurs above?
```

---

## 🛡️ SECURITY RULES

### Rule #21: Never Hardcode Credentials

```python
# ❌ FORBIDDEN
username = "myuser123"
password = "mypassword"

# ✅ REQUIRED
username = os.getenv("DAMADAM_USERNAME")
password = os.getenv("DAMADAM_PASSWORD")

if not username or not password:
    raise ValueError("Credentials not found in environment")
```

### Rule #22: Input Sanitization

```python
# MANDATORY: Always validate user input

from utils.validators import NicknameValidator

def scrape_profile(nickname: str):
    # Validate BEFORE using
    valid, clean_nick, error = NicknameValidator.validate(nickname)
    if not valid:
        log_msg(f"Invalid nickname: {error}", "ERROR")
        return None
    
    # Use cleaned version
    url = get_profile_url(clean_nick)
```

---

## 📚 DOCUMENTATION RULES

### Rule #23: Update Documentation with Code

```
Code change checklist:
├─ [ ] Code written
├─ [ ] Docstrings added
├─ [ ] Tests written
├─ [ ] README.md updated (if user-facing)
├─ [ ] CHANGELOG.md updated
└─ [ ] Example added (if new feature)
```

### Rule #24: Documentation Structure

```
docs/
├── SETUP.md              → Installation guide
├── TROUBLESHOOTING.md    → Common issues
├── LIMIT_HANDLING.md     → API limit recovery
├── PHASE_GUIDE.md        → Phase system docs
└── API.md                → Code API reference

README.md                 → Overview + quick start
CONTRIBUTING.md           → Contribution guide
SECURITY.md               → Security guidelines
PROJECT_RULES.md          → This file (global rules)
```

---

## 🎯 AI ASSISTANT RULES

### Rule #25: AI Must Always Check

**Before making ANY changes, AI must verify:**

```
1. Is Phase 1 affected?
   └─ If yes: Is it a locked element?
      └─ If yes: STOP, suggest alternative

2. Does this mix concerns?
   └─ If yes: STOP, restructure

3. Does this break backward compatibility?
   └─ If yes: STOP, suggest migration

4. Is this a new phase?
   └─ If yes: Create new directory structure

5. Is documentation updated?
   └─ If no: STOP, update docs first
```

### Rule #26: AI Response Pattern

```
When asked to modify code, AI must:

1. State what is locked/unlocked
2. Explain approach (where to add code)
3. Show file structure
4. Provide code with proper location
5. Update related documentation
6. Provide testing steps

Example:
"This requires modifying profile scraping.
Phase 1 is LOCKED, but we can add retry decorator
without changing output.

Location: phases/profile/target_mode.py
Affected: scrape_profile() function only
Output format: Unchanged ✓
Backward compatible: Yes ✓

Code:
[shows code]

Testing:
python main.py test --max-profiles 3
"
```

---

## 🔄 CHANGE REQUEST TEMPLATE

**Use this template when requesting changes:**

```markdown
## Change Request

**Type**: Feature / Fix / Refactor
**Phase**: 1 / 2 / 3 / Core / Utils
**Priority**: High / Medium / Low

**Description**:
What needs to change and why.

**Locked Elements Affected**:
- None / List locked elements

**Files Affected**:
- path/to/file.py (new/modified/deleted)

**Backward Compatibility**:
- Yes / No / N/A

**Testing Plan**:
- Test case 1
- Test case 2

**Documentation Updates**:
- README.md (section X)
- CHANGELOG.md (added entry)
```

---

## 📋 QUICK REFERENCE CHECKLIST

### Before Starting Work

- [ ] Read PROJECT_RULES.md (this file)
- [ ] Check if Phase 1 is affected
- [ ] Identify correct file location
- [ ] Check import hierarchy
- [ ] Plan testing approach

### Before Committing

- [ ] Pre-commit hook passes
- [ ] Tests run successfully
- [ ] No credentials in code
- [ ] Docstrings added
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### Before Merging

- [ ] Code review completed
- [ ] All tests pass
- [ ] Phase 1 output unchanged
- [ ] Backward compatible
- [ ] Documentation complete

---

## 🚨 EMERGENCY CONTACTS

**If you need to break a rule (rare emergency):**

1. Document why in commit message
2. Add TODO to revert/fix properly
3. Notify maintainer immediately
4. Create issue to track technical debt

**Maintainer**: Nadeem (net2outlawzz@gmail.com)

---

## 📖 VERSION HISTORY

- **v1.0.0** (2026-01-05): Initial rules document
- Phase 1 locked at v2.100.0.18

---

**REMEMBER: These rules exist to maintain project stability and prevent code mixing. Follow them strictly!**
