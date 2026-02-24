# 🧪 Testing Guide

**Simple testing guide - No complex frameworks, just practical tests.**

---

## 🎯 Testing Philosophy

```
Tests exist to give you confidence.
Keep tests simple, focused, and practical.
```

**We test:**
- ✅ Critical functions (validators, scrapers)
- ✅ Things that break often
- ✅ Things that are hard to debug

**We DON'T test:**
- ❌ Simple getters/setters
- ❌ External libraries (trust them)
- ❌ Configuration files

---

## 📋 Pre-Commit Testing (Required)

**Before EVERY commit, run these:**

### Test 1: Test Mode (1 minute)
```bash
python main.py test --max-profiles 3
```

**Expected:** All 3 profiles scraped successfully

### Test 2: Check Logs (30 seconds)
```bash
# Windows
type logs\*.log | findstr "ERROR"

# Linux/Mac
cat logs/*.log | grep "ERROR"
```

**Expected:** No ERROR messages (or only expected ones)

### Test 3: Verify Sheet (1 minute)
1. Open Google Sheet
2. Check last 3 profiles in Profiles tab
3. Verify data looks correct

**Expected:** All fields populated, no blanks in key columns

---

## 🔍 Manual Testing Scenarios

### Scenario 1: Normal Profile
```bash
# Add to RunList: normaluser | ⚡ Pending
python main.py target --max-profiles 1
```

**Expected:**
- ✅ Profile scraped
- ✅ STATUS = "Verified" or "Normal"
- ✅ All 23 columns populated
- ✅ PHASE 2 = "Ready" or "Not Eligible"

### Scenario 2: Banned Profile
```bash
# Add to RunList: banneduser | ⚡ Pending
python main.py target --max-profiles 1
```

**Expected:**
- ✅ Profile detected as banned
- ✅ STATUS = "Banned"
- ✅ Some fields may be blank (OK for banned)

### Scenario 3: Invalid Nickname
```bash
# Add to RunList: user with spaces | ⚡ Pending
python main.py target --max-profiles 1
```

**Expected:**
- ✅ Validation error logged
- ✅ Profile skipped
- ✅ No crash

### Scenario 4: Duplicate Profile
```bash
# Scrape same profile twice
python main.py target --max-profiles 1  # First time
python main.py target --max-profiles 1  # Second time (same profile)
```

**Expected:**
- ✅ First run: Status = "new"
- ✅ Second run: Status = "unchanged" or "updated"
- ✅ Duplicate moved to Row 2
- ✅ Old row deleted

### Scenario 5: Online Mode
```bash
python main.py online --max-profiles 5
```

**Expected:**
- ✅ At least 1-5 online users found
- ✅ Logged to OnlineLog sheet
- ✅ Profiles scraped and written

---

## 🐛 Validator Testing (Quick)

### Test Nicknames

```python
# Run in Python console
from utils.validators import NicknameValidator

# Valid cases
assert NicknameValidator.is_valid("user123")
assert NicknameValidator.is_valid("user@name")
assert NicknameValidator.is_valid("user-name")

# Invalid cases
assert not NicknameValidator.is_valid("user name")  # Space
assert not NicknameValidator.is_valid("")           # Empty
assert not NicknameValidator.is_valid("a" * 51)     # Too long
assert not NicknameValidator.is_valid("user<>")     # Dangerous chars

print("✅ All validator tests passed!")
```

**Run this:**
```bash
python -c "from utils.validators import NicknameValidator; \
assert NicknameValidator.is_valid('user123'); \
assert not NicknameValidator.is_valid('user name'); \
print('✅ Validator tests passed!')"
```

---

## 📊 Sheet Testing Checklist

### After Running Scraper

**Profiles Sheet:**
- [ ] Header row has 23 columns
- [ ] NICK NAME column not empty
- [ ] DATETIME SCRAP has valid date
- [ ] PHASE 2 is "Ready" or "Not Eligible"
- [ ] No "BLANK" or "Error" values in key fields

**RunList Sheet:**
- [ ] Processed profiles marked "Done 💀"
- [ ] Failed profiles marked "Error 💥"
- [ ] Pending profiles still "⚡ Pending"

**Dashboard Sheet:**
- [ ] New row added
- [ ] Success/Failed counts correct
- [ ] Timestamp recent

**OnlineLog Sheet (if online mode):**
- [ ] New entries added
- [ ] Nicknames logged
- [ ] Batch # present

---

## 🔄 Regression Testing (After Changes)

**After ANY code change, run these:**

### 1. Smoke Test (5 minutes)
```bash
# Test all modes
python main.py test --max-profiles 1
python main.py target --max-profiles 1
python main.py online --max-profiles 1
```

### 2. Data Integrity Test (3 minutes)
```bash
# Scrape known good profile
python main.py target --max-profiles 1

# Manually verify:
# - All 23 columns populated
# - Dates formatted correctly (dd-mmm-yy hh:mm am/pm)
# - Status values uppercase
# - URLs valid
```

### 3. Edge Cases (5 minutes)
```bash
# Test edge cases
# Add these to RunList:
# - Profile with special chars: user@123
# - Profile with dots: user.name
# - Very short name: ab
# - Long name: user12345678901234567890

python main.py target --max-profiles 4
```

---

## ⚡ Performance Testing (Optional)

### Measure Scraping Speed

```bash
# Time a 10-profile run
python main.py target --max-profiles 10 --metrics

# Check metrics file
type logs\metrics_*.json  # Windows
cat logs/metrics_*.json   # Linux/Mac
```

**Expected:**
- Average 3-5 seconds per profile
- Total time: 30-60 seconds for 10 profiles
- No rate limit errors

### Measure Cache Hit Rate

```bash
# First run (populate cache)
python main.py target --max-profiles 10

# Second run (use cache)
python main.py target --max-profiles 10

# Compare times
# Second run should be 50%+ faster if cache enabled
```

---

## 🐞 Bug Reproduction

**When you find a bug:**

### 1. Create Minimal Test Case
```bash
# Isolate the problem
# Instead of: python main.py target --max-profiles 100
# Try: python main.py test --max-profiles 1

# Find the smallest case that reproduces the bug
```

### 2. Document Steps
```markdown
## Bug: Profile with special chars fails

**Steps to Reproduce:**
1. Add profile to RunList: user@123
2. Run: python main.py target --max-profiles 1
3. Observe: ERROR in logs

**Expected:** Profile scraped successfully
**Actual:** Validation error

**Logs:**
[Paste relevant log snippet]
```

### 3. Share with Maintainer
- Email: net2outlawzz@gmail.com
- Include: Steps, expected, actual, logs
- Attach: Logs file if needed

---

## 📝 Testing Checklist Template

**Copy this for each release:**

```markdown
## Testing Checklist - v2.100.0.X

### Pre-Commit Tests
- [ ] Test mode (3 profiles) - PASSED
- [ ] No ERROR in logs
- [ ] Sheet data verified

### Smoke Tests
- [ ] Target mode (5 profiles)
- [ ] Online mode (5 profiles)
- [ ] Dashboard updated

### Edge Cases
- [ ] Special characters in nickname
- [ ] Banned profile
- [ ] Unverified profile
- [ ] Duplicate profile
- [ ] Invalid nickname

### Performance
- [ ] Average time per profile < 10s
- [ ] No rate limit errors
- [ ] Cache working (if enabled)

### Documentation
- [ ] CHANGELOG.md updated
- [ ] README.md accurate
- [ ] No broken links

### Security
- [ ] No credentials in code
- [ ] Pre-commit hook working
- [ ] .gitignore correct

**Tested by:** Your Name
**Date:** 2026-01-05
**Status:** ✅ PASSED / ❌ FAILED
```

---

## 🎯 Quick Testing Commands

```bash
# === Quick Tests (Use these daily) ===

# Test 1: Quick smoke test (30 seconds)
python main.py test --max-profiles 1

# Test 2: Check for errors (10 seconds)
grep -i error logs/*.log  # Linux/Mac
findstr /i error logs\*.log  # Windows

# Test 3: Validator test (5 seconds)
python -c "from utils.validators import NicknameValidator; \
assert NicknameValidator.is_valid('user123'); \
print('OK')"

# === Detailed Tests (Use before commits) ===

# Test 4: Full smoke test (5 minutes)
python main.py test --max-profiles 3
python main.py target --max-profiles 3
python main.py online --max-profiles 3

# Test 5: Performance test (2 minutes)
python main.py target --max-profiles 10 --metrics

# Test 6: Cache test (3 minutes)
python main.py target --max-profiles 5  # First run
python main.py target --max-profiles 5  # Second run (should be faster)
```

---

## 🚨 When Tests Fail

### 1. Don't Panic
- One failed test doesn't mean disaster
- Isolate the problem
- Check logs first

### 2. Debugging Steps
```bash
# Step 1: Find exact error
cat logs/target_*.log | grep -A 5 ERROR

# Step 2: Reproduce with 1 profile
python main.py test --max-profiles 1

# Step 3: Check recent changes
git diff HEAD~1

# Step 4: Revert if needed
git checkout HEAD~1 -- problematic_file.py
```

### 3. Ask for Help
- Include: Error message, logs, what you tried
- Email: net2outlawzz@gmail.com
- Be specific: "Profile scraping fails for user@123"
- Not vague: "It doesn't work"

---

## 💡 Testing Best Practices

### Do:
- ✅ Test with 3-5 profiles (not 100)
- ✅ Test edge cases
- ✅ Check logs after every run
- ✅ Verify sheet data manually
- ✅ Test on real data

### Don't:
- ❌ Test with production data initially
- ❌ Skip tests to save time (costs more later)
- ❌ Test with 100+ profiles on first try
- ❌ Ignore warnings in logs
- ❌ Assume tests pass because no crash

---

## 🎓 Learning Resources

**Want to learn more about testing?**

**Simple approach (recommended for this project):**
- Manual testing (this guide)
- Smoke tests before commits
- Visual verification in Google Sheets

**Advanced approach (if you want):**
- pytest framework
- Unit tests for validators
- Integration tests for scrapers
- Mock objects for APIs

**For this project, manual testing is sufficient!**

---

## ✅ Summary

**Minimum testing required:**
1. Run test mode with 3 profiles
2. Check logs for errors
3. Verify sheet data

**Time:** ~2 minutes per commit

**That's it!** Keep it simple and practical.

---

**Questions about testing?**
Email: net2outlawzz@gmail.com
