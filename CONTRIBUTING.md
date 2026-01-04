# 🤝 Contributing to DamaDam Scraper

Thank you for your interest in contributing to the DamaDam Scraper project! This document provides guidelines and workflows for contributors.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Phase System Rules](#phase-system-rules)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all.

### Our Standards

**✅ Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**❌ Unacceptable behavior includes:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Git knowledge
- Understanding of web scraping (Selenium)
- Familiarity with Google Sheets API

### Fork & Clone

```bash
# Fork the repository on GitHub (click "Fork" button)

# Clone your fork
git clone https://github.com/YOUR_USERNAME/DD-CMS-Final.git
cd DD-CMS-Final

# Add upstream remote
git remote add upstream https://github.com/net2t/DD-CMS-Final.git

# Verify remotes
git remote -v
```

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Setup git hooks
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks

# Verify setup
python main.py test --max-profiles 3
```

---

## 🔄 Development Workflow

### 1. Sync with Upstream

```bash
# Before starting work, sync with latest
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

### 2. Create Feature Branch

```bash
# Branch naming convention:
# feature/description  - New features
# fix/description      - Bug fixes
# docs/description     - Documentation changes
# refactor/description - Code refactoring

# Example:
git checkout -b feature/add-retry-decorator
```

### 3. Make Changes

```bash
# Edit files
nano phases/profile/target_mode.py

# Test locally
python main.py test --max-profiles 3

# Verify changes
python main.py target --max-profiles 5
```

### 4. Commit Changes

```bash
# Stage files
git add .

# Pre-commit hook runs automatically
# Commit with meaningful message (see Commit Guidelines)
git commit -m "feat: add retry decorator for network operations"
```

### 5. Push to Your Fork

```bash
git push origin feature/add-retry-decorator
```

### 6. Create Pull Request

- Go to your fork on GitHub
- Click "Pull Request" button
- Select base: `net2t/DD-CMS-Final` main ← head: `your-fork` feature-branch
- Fill out PR template
- Submit for review

---

## 🎯 Phase System Rules

### Critical: Phase 1 is LOCKED 🔒

**What "Locked" Means:**
- ✅ Bug fixes allowed (with tests)
- ✅ Documentation updates allowed
- ✅ Performance optimizations allowed (if output unchanged)
- ❌ Schema changes FORBIDDEN
- ❌ Column order changes FORBIDDEN
- ❌ New columns FORBIDDEN (use Phase 2+)
- ❌ Breaking changes FORBIDDEN

### Frozen Elements (DO NOT MODIFY)

**In `config/config_common.py`:**
```python
# LOCKED - Do not modify
COLUMN_ORDER = [
    "ID", "NICK NAME", "TAGS", # ... (23 columns)
]

# LOCKED - Do not modify
DEFAULT_VALUES = { ... }
```

**In `utils/sheets_manager.py`:**
```python
# LOCKED - Do not modify column mapping
def write_profile(self, profile_data):
    # Column order must remain: ID, NICK NAME, TAGS, ...
```

**Output Format:**
```
LOCKED: Profiles sheet structure
LOCKED: Date format: "dd-mmm-yy hh:mm a"
LOCKED: Status values: "ACTIVE", "BANNED", "UNVERIFIED", "DEAD"
LOCKED: URL normalization logic
```

### Adding New Features

**✅ Allowed in Phase 1:**
```python
# Internal optimizations (no output change)
def _extract_followers(self, page_source):
    # Add more fallback selectors
    # Add caching
    # Add retry logic
    pass

# New utility functions
def validate_url(url):
    # As long as output format unchanged
    pass
```

**❌ Requires New Phase:**
```python
# New data columns
def extract_comments(self):  # → Phase 2
    pass

def extract_mehfil_details(self):  # → Phase 3
    pass
```

### Version Numbering

**Current: v2.100.0.18**
- **2**: Major version (project rewrite)
- **100**: Phase number (1 = 100, 2 = 200, etc.)
- **0**: Minor version (features within phase)
- **18**: Patch version (bug fixes)

**When to Bump:**
- Patch (X.X.X.N): Bug fix, no behavior change
- Minor (X.X.N.0): New feature, backward compatible
- Phase (X.NNN.0.0): New phase started
- Major (N.0.0.0): Breaking changes (rare)

**Example:**
```bash
# Bug fix in Phase 1
v2.100.0.18 → v2.100.0.19

# New feature in Phase 1 (if allowed)
v2.100.0.19 → v2.100.1.0

# Phase 1 locked, start Phase 2
v2.100.1.0 → v2.200.0.0
```

---

## 💻 Coding Standards

### Python Style Guide

**Follow PEP 8:**
```python
# ✅ Good
def extract_profile_data(self, driver, nickname):
    """Extract complete profile data from page."""
    pass

# ❌ Bad
def ExtractProfileData(Self,Driver,NickName):
    """extract profile data"""
    pass
```

**Line Length:**
```python
# Maximum 100 characters per line
# Exception: URLs, long strings

# ✅ Good
error_message = (
    "Failed to extract profile data. "
    "This may be due to HTML changes on the website."
)

# ❌ Bad
error_message = "Failed to extract profile data. This may be due to HTML changes on the website which we cannot control."
```

### Docstring Standards

**Google-style docstrings:**
```python
def scrape_profile(self, nickname: str, source: str = "Target") -> dict | None:
    """
    Scrape complete user profile from DamaDam.
    
    This method navigates to the profile page, extracts all available
    information, and returns it in a structured format.
    
    Args:
        nickname: The DamaDam username to scrape. Must be sanitized.
        source: Origin of scrape request. Options: "Target", "Online", "Test".
    
    Returns:
        Dictionary with profile data matching Config.COLUMN_ORDER, or None
        if critical error (timeout, network failure).
        
        Example:
        {
            'NICK NAME': 'user123',
            'CITY': 'KARACHI',
            'STATUS': 'Verified',
            ...
        }
    
    Raises:
        TimeoutException: If profile page doesn't load in PAGE_LOAD_TIMEOUT.
        WebDriverException: For browser/network errors.
    
    Note:
        - Banned/unverified profiles return partial data with '__skip_reason'
        - Empty fields are empty strings, never None
        - URLs are automatically normalized
    
    Example:
        >>> scraper = ProfileScraper(driver)
        >>> profile = scraper.scrape_profile("testuser")
        >>> if profile:
        ...     print(f"Scraped: {profile['NICK NAME']}")
    """
    # Implementation...
```

### Naming Conventions

```python
# Variables: lowercase_with_underscores
profile_data = {}
max_retries = 3

# Constants: UPPERCASE_WITH_UNDERSCORES
MAX_TIMEOUT = 30
DEFAULT_DELAY = 0.5

# Classes: PascalCase
class ProfileScraper:
    pass

# Functions/Methods: lowercase_with_underscores
def extract_profile_data():
    pass

# Private methods: _leading_underscore
def _extract_internal_data():
    pass
```

### Import Organization

```python
# Standard library
import os
import sys
import time
from datetime import datetime

# Third-party
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By

# Local
from config.config_common import Config
from utils.ui import log_msg
```

### Error Handling

```python
# ✅ Good: Specific exceptions
try:
    profile = scraper.scrape_profile(nickname)
except TimeoutException:
    log_msg(f"Timeout for {nickname}", "TIMEOUT")
except WebDriverException as e:
    log_msg(f"Browser error: {e}", "ERROR")

# ❌ Bad: Bare except
try:
    profile = scraper.scrape_profile(nickname)
except:
    pass  # Silent failure!
```

### Logging

```python
# ✅ Good: Descriptive with context
log_msg(f"Scraping profile: {nickname} (attempt {attempt}/3)", "INFO")
log_msg(f"Failed to extract FOLLOWERS for {nickname}", "WARNING")

# ❌ Bad: Vague
log_msg("Error", "ERROR")
log_msg("Processing", "INFO")
```

---

## 🧪 Testing Guidelines

### Manual Testing Requirements

**Before ANY commit:**
```bash
# 1. Test mode (quick validation)
python main.py test --max-profiles 3

# 2. Target mode (with real RunList)
python main.py target --max-profiles 5

# 3. Online mode (if changes affect it)
python main.py online --max-profiles 5

# 4. Check logs for errors
cat logs/target_*.log | grep "ERROR"
cat logs/target_*.log | grep "WARNING"

# 5. Verify Google Sheet
# - Open sheet
# - Check last 5 profiles
# - Verify data integrity
# - Check Dashboard updated
```

### Test Cases to Cover

**Profile Scraping:**
```bash
# Test with:
# 1. Normal/verified profile
# 2. Banned profile
# 3. Unverified profile
# 4. Profile with < 100 posts (Phase 2 ready)
# 5. Profile with > 100 posts (Phase 2 not eligible)
# 6. Profile with no posts
# 7. Profile with no Mehfils
# 8. Profile with multiple Mehfils

# Add these to RunList:
normaluser
banneduser
unverifieduser
newuser
poweruser
inactiveuser
# etc.

# Run:
python main.py target --max-profiles 8
```

**Edge Cases:**
```python
# Test these scenarios:
# - Empty nickname
# - Nickname with special chars (@, ., -, _)
# - Very long nickname (50 chars)
# - Non-existent profile
# - Private profile (if applicable)
# - Temporarily unavailable profile
```

### What to Check

**✅ Data Integrity:**
- [ ] All 23 columns populated (or empty string)
- [ ] Dates in correct format: "dd-mmm-yy hh:mm a"
- [ ] Status uppercase: "VERIFIED", "BANNED", etc.
- [ ] URLs normalized correctly
- [ ] Numeric fields clean (no commas in POSTS)
- [ ] Multi-line fields (Mehfils) formatted correctly

**✅ Duplicate Handling:**
- [ ] Duplicate moved to Row 2
- [ ] Note added to DATETIME SCRAP cell
- [ ] Changed fields listed in note
- [ ] Old row deleted

**✅ Error Handling:**
- [ ] Timeouts handled gracefully
- [ ] Rate limits trigger retry
- [ ] Failed profiles don't crash scraper
- [ ] Summary shows correct counts

---

## 📝 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no functionality change)
- **perf**: Performance improvement
- **test**: Adding tests
- **chore**: Build process, dependencies, etc.

### Examples

**Feature:**
```
feat(profile): add retry decorator for network operations

Add @retry_on_failure decorator to handle transient network errors.
Configured with 3 attempts and exponential backoff (2s, 4s, 8s).

Resolves: #42
```

**Bug Fix:**
```
fix(sheets): preserve existing POSTS value when blank

When scraping returns blank POSTS value but existing row has data,
preserve the existing value instead of overwriting with blank.

Fixes: #38
```

**Documentation:**
```
docs: add troubleshooting guide for rate limits

Created LIMIT_HANDLING.md with detailed procedures for recovering
from Google Sheets API rate limits and DamaDam login limits.
```

**Refactor:**
```
refactor(core): extract selector logic to separate module

Moved all CSS/XPath selectors from inline code to config/selectors.py
for better maintainability. No functionality changes.
```

### Commit Dos and Don'ts

**✅ Do:**
- Write in present tense: "add feature" not "added feature"
- Start with lowercase letter (except proper nouns)
- Keep subject line under 72 characters
- Explain **why** in the body, not **what** (code shows what)
- Reference issues: "Fixes #123", "Resolves #456"

**❌ Don't:**
- Commit broken code
- Commit WIP (work in progress) to main branch
- Mix unrelated changes in one commit
- Commit sensitive files (pre-commit hook prevents this)
- Use vague messages: "fix bug", "update code"

---

## 🔀 Pull Request Process

### Before Creating PR

**Checklist:**
- [ ] Code tested with 3-5 profiles
- [ ] All tests pass
- [ ] Pre-commit hooks pass
- [ ] No sensitive data in commits
- [ ] Code follows style guide
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated
- [ ] Branch synced with upstream/main

### PR Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Phase Compliance
- [ ] No changes to Phase 1 locked schema
- [ ] No breaking changes to output format
- [ ] Backward compatible

## Testing
Describe how you tested this change:
- [ ] Tested with test mode (3 profiles)
- [ ] Tested with target mode (10 profiles)
- [ ] Tested with online mode (5 profiles)
- [ ] Verified in Google Sheet
- [ ] Checked logs for errors

## Test Profiles Used
- normaluser (verified, active)
- banneduser (suspended)
- newuser (< 100 posts)

## Screenshots (if applicable)
Before/After screenshots of terminal output or Google Sheet.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have updated documentation
- [ ] My changes generate no new warnings
- [ ] No sensitive data committed

## Related Issues
Fixes #123
Resolves #456
```

### Review Process

1. **Automated Checks**
   - Pre-commit hooks run
   - GitHub Actions run (if configured)
   - No merge conflicts

2. **Maintainer Review**
   - Code quality check
   - Phase compliance verification
   - Testing validation
   - Documentation review

3. **Feedback & Changes**
   - Address review comments
   - Push changes to same branch
   - Re-request review

4. **Merge**
   - Squash and merge (usually)
   - Delete branch after merge

---

## 🐛 Issue Reporting

### Before Creating Issue

**Check:**
1. Is this already reported? Search existing issues
2. Is this actually a bug? Test with latest version
3. Have you tried troubleshooting guide?

### Issue Template

```markdown
**Environment:**
- OS: Windows 10 / Ubuntu 22.04 / Mac OS
- Python Version: 3.9.5
- Scraper Version: v2.100.0.18
- Run Mode: Target / Online / Test

**Description:**
Clear and concise description of the bug.

**Steps to Reproduce:**
1. Run command: `python main.py target --max-profiles 10`
2. Observe profile: user123
3. See error: ...

**Expected Behavior:**
What should happen.

**Actual Behavior:**
What actually happened.

**Logs:**
```
Paste relevant log snippets from logs/target_*.log
```

**Screenshots:**
If applicable, add screenshots of terminal or Google Sheet.

**Additional Context:**
- First occurrence: Yesterday at 3:45 PM
- Frequency: Every time / Sometimes / Once
- Workaround: None / Described below
```

### Issue Labels

- **bug**: Something isn't working
- **enhancement**: New feature request
- **documentation**: Documentation improvements
- **good first issue**: Good for newcomers
- **help wanted**: Extra attention needed
- **question**: Further information requested
- **wontfix**: Will not be worked on
- **phase-1**: Related to Phase 1
- **phase-2**: Related to Phase 2

---

## 🏆 Recognition

Contributors will be recognized in:
- README.md Credits section
- CHANGELOG.md for each version
- GitHub Contributors page

---

## 📞 Questions?

- **Email**: net2outlawzz@gmail.com
- **Instagram**: @net2nadeem
- **GitHub Issues**: For public questions

---

**Thank you for contributing! 🎉**

Your contributions make this project better for everyone.
