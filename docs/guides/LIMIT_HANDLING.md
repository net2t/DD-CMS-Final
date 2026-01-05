# ⚠️ API Limit Handling & Recovery Guide

## 📋 Table of Contents
- [Understanding Limits](#understanding-limits)
- [Detection & Symptoms](#detection--symptoms)
- [Immediate Actions](#immediate-actions)
- [Recovery Procedures](#recovery-procedures)
- [Prevention Strategies](#prevention-strategies)
- [Emergency Contacts](#emergency-contacts)

---

## 🎯 Understanding Limits

### Google Sheets API Limits

**Read Requests:**
- **Per Minute**: 60 requests
- **Per Day**: 50,000 requests

**Write Requests:**
- **Per Minute**: 60 requests
- **Per Day**: 50,000 requests

**What Counts as a Request:**
- ✅ Reading sheet rows
- ✅ Writing profile data
- ✅ Updating cell values
- ✅ Formatting operations
- ❌ Batch operations count as ONE request (we use these!)

### DamaDam Platform Limits

**Login Attempts:**
- **Suspicious Activity**: ~5 failed logins within 30 minutes
- **Consequence**: Temporary account suspension (1-24 hours)
- **Solution**: Use backup account + cookie persistence

**Page Requests:**
- **Rate**: Unknown (no official limit)
- **Detection**: Slower response times, timeouts
- **Solution**: Built-in delays (0.3-0.5s between requests)

---

## 🚨 Detection & Symptoms

### Google Sheets API Rate Limit (Error 429)

**Symptoms:**
```
⚠️ WARNING: API rate limit hit. Waiting 60s before retry...
⚠️ WARNING: API rate limit hit. Waiting 120s before retry...
❌ ERROR: Failed to perform write operation after multiple retries.
```

**Log Messages:**
- "API Error 429" or "Quota exceeded"
- Multiple retry attempts visible
- Sheet operations timing out

**What Happens:**
- ✅ Scraper automatically retries with backoff (60s, 120s, 180s)
- ✅ Already scraped data is preserved
- ❌ If retries fail, run stops gracefully

### DamaDam Login Limit

**Symptoms:**
```
❌ ERROR: Primary account login failed
⚠️ WARNING: Too many login attempts
✅ OK: Switching to backup account...
```

**What Happens:**
- ✅ Automatically switches to backup account (if configured)
- ✅ Cookie persistence prevents repeated logins
- ❌ Without backup: run stops

### Browser/Network Timeouts

**Symptoms:**
```
⏳ TIMEOUT: Timeout loading profile: user123
❌ ERROR: Page load timeout after 30 seconds
```

**What Happens:**
- ⚠️ Specific profile marked as failed
- ✅ Scraper continues with next profile
- ✅ You can retry failed profiles later

---

## 🛠️ Immediate Actions

### When You See Rate Limit Warnings

**Step 1: Let It Retry** ⏳
```
DO: Wait for automatic retries (60s, 120s, 180s)
DON'T: Stop the scraper manually
DON'T: Start another instance
```

**Step 2: Monitor Progress** 👀
```bash
# Watch the terminal output
# Look for:
✅ Successful retries: "Sheet updated successfully"
❌ Failed retries: "Failed to perform write operation"
```

**Step 3: If Retries Fail** ❌
```bash
# The scraper will stop gracefully
# You'll see final summary with stats

# Check what was completed:
# - Open Google Sheet
# - Check "Dashboard" tab for last run
# - Note last scrape timestamp in "Profiles" tab
```

### When Login Fails

**Option A: Backup Account Configured** ✅
```
DO: Nothing - scraper switches automatically
WAIT: For "Backup account login successful" message
```

**Option B: No Backup Account** ❌
```bash
# Immediate action required:

# 1. Stop current run (Ctrl+C)

# 2. Wait 30 minutes before retrying
#    (Let account cooldown)

# 3. Consider adding backup account:
nano .env
# Add:
# DAMADAM_USERNAME_2=your_backup_username
# DAMADAM_PASSWORD_2=your_backup_password

# 4. Retry with smaller batch
python main.py target --max-profiles 10 --batch-size 5
```

---

## 🔄 Recovery Procedures

### Scenario 1: Scraper Stopped Due to Rate Limit

**Situation:**
- Scraper hit Google Sheets API limit
- Stopped after multiple failed retries
- Some profiles processed, some pending

**Recovery Steps:**

**Step 1: Check What Was Completed** 📊
```bash
# Open Google Sheet
# Check "Profiles" tab - see latest "DATETIME SCRAP"
# Check "Dashboard" tab - see last run stats

# Example output:
# Last run: 04-jan-26 03:45 pm
# Success: 45
# Failed: 5
# New: 30
```

**Step 2: Wait for Quota Reset** ⏳
```
Google Sheets quotas reset after 1 minute (for per-minute limit)
For safety: Wait 5 minutes before resuming
```

**Step 3: Resume Scraping** ▶️
```bash
# Target mode - automatically skips completed profiles
python main.py target --max-profiles 0

# Online mode - can be safely re-run (handles duplicates)
python main.py online --max-profiles 20

# With increased delays to prevent recurrence
# Edit .env:
SHEET_WRITE_DELAY=2.0  # Increase from 1.0
BATCH_SIZE=10          # Reduce from 20

# Then run:
python main.py target --max-profiles 50 --batch-size 10
```

**Step 4: Verify Recovery** ✅
```
Watch terminal for:
✅ No rate limit warnings
✅ Profiles processing successfully
✅ "Run completed successfully" at end

Check Google Sheet:
✅ New profiles added
✅ Dashboard updated with latest run
✅ Timestamps progressing
```

### Scenario 2: All Accounts Blocked/Rate Limited

**Situation:**
- Primary account: Login failed
- Backup account: Also failed or not configured
- Cannot proceed with scraping

**Recovery Steps:**

**Step 1: Immediate Cooldown** 🧊
```bash
# Stop all running instances
# WAIT: Minimum 1 hour before retrying
# BEST: Wait 24 hours for full reset
```

**Step 2: Verify Account Status** 🔍
```bash
# Manual check:
# 1. Open browser
# 2. Visit https://damadam.pk/login/
# 3. Try logging in manually

If successful: Account is OK, temporary rate limit
If failed: Account may be suspended
```

**Step 3: Configure Additional Accounts** 👥
```bash
# Create additional DamaDam accounts (if needed)
# Add to .env:
DAMADAM_USERNAME_2=account2_username
DAMADAM_PASSWORD_2=account2_password

# Note: Keep backup accounts separate
#       (different email, IP if possible)
```

**Step 4: Resume with Caution** ⚠️
```bash
# Use smaller batches
python main.py target --max-profiles 20 --batch-size 5

# Monitor closely for 10-15 minutes
# If stable, gradually increase:
python main.py target --max-profiles 50 --batch-size 10
```

### Scenario 3: Partial Data / Incomplete Profiles

**Situation:**
- Some profile columns are blank (POSTS, IMAGE, etc.)
- "Failed to extract" warnings in logs
- Website HTML may have changed

**Recovery Steps:**

**Step 1: Check Recent Profiles** 🔍
```bash
# Open Google Sheet
# Sort by "DATETIME SCRAP" (newest first)
# Look at last 10-20 profiles

# Check which fields are blank:
# - If random: Likely individual profile issues
# - If consistent: Likely selector changed
```

**Step 2: Test with Known Good Profile** 🧪
```bash
# Find a profile you know has data
# Add to RunList with status "⚡ Pending"

# Run targeted scrape:
python main.py target --max-profiles 1

# Check if data extracted correctly
```

**Step 3: Report Issue** 🐛
```bash
# If selector issue suspected:
# 1. Note affected fields (POSTS, IMAGE, etc.)
# 2. Save example profile URL
# 3. Attach logs/target_*.log file
# 4. Create GitHub issue or contact maintainer

# Email: net2outlawzz@gmail.com
# Subject: "[SCRAPER] Blank fields: POSTS, IMAGE"
```

**Step 4: Wait for Fix or Apply Patch** 🔧
```bash
# If urgent, maintainer may provide hotfix:
git pull origin hotfix/selector-update
pip install -r requirements.txt
python main.py target --max-profiles 5  # Test
```

---

## 🛡️ Prevention Strategies

### 1. Use Backup Account

**Why:**
- Prevents total stoppage on rate limit
- Allows continuous operation
- Distributes load across accounts

**Setup:**
```bash
nano .env
# Add:
DAMADAM_USERNAME_2=backup_username
DAMADAM_PASSWORD_2=backup_password
```

### 2. Optimize Sheet Operations

**Reduce Write Frequency:**
```bash
# Edit .env:
SHEET_WRITE_DELAY=2.0  # Increase delay between writes
BATCH_SIZE=10          # Smaller batches = fewer writes per minute
```

**Use GitHub Actions for Large Jobs:**
- Scheduled runs prevent manual rate limit issues
- Automatic retry on failure
- Distributed across time

### 3. Smart Scheduling

**For Local Runs:**
```bash
# Don't run multiple instances simultaneously
# Check if previous run finished:
ps aux | grep "python main.py"  # Linux/Mac
tasklist | findstr python       # Windows

# Space out manual runs:
# Minimum 10 minutes between runs
```

**For GitHub Actions:**
```yaml
# Already optimized schedules:
# - Online: Every 15 minutes
# - Target: Every 55 minutes
# Don't manually trigger unless necessary
```

### 4. Monitor & Adjust

**Watch for Patterns:**
```bash
# After each run, check logs:
grep "WARNING" logs/target_*.log
grep "ERROR" logs/target_*.log

# If seeing frequent warnings:
# - Increase SHEET_WRITE_DELAY
# - Decrease BATCH_SIZE
# - Reduce MAX_PROFILES_PER_RUN
```

**Keep Track:**
```
Maintain a log of:
- Date/time of rate limit hits
- Settings used (batch size, delays)
- Number of profiles processed
- Recovery actions taken

Use this to optimize settings over time
```

### 5. Cookie Persistence

**Enable (Default):**
```bash
# Automatically enabled for local runs
# Cookie file: damadam_cookies.pkl
# Benefit: Skip login, save API calls

# If login issues, delete and refresh:
rm damadam_cookies.pkl
python main.py target --max-profiles 5
```

---

## 📞 Emergency Contacts

### Project Maintainer

**Nadeem**
- **Email**: net2outlawzz@gmail.com
- **Instagram**: @net2nadeem
- **Response Time**: Usually within 24 hours

### Reporting Format

```
Subject: [URGENT] Rate Limit Issue - <Brief Description>

Environment:
- OS: Windows 10 / Ubuntu 22.04
- Python Version: 3.9.5
- Scraper Version: v2.100.0.18
- Run Mode: Target / Online

Issue:
- Started at: 04-jan-26 03:45 pm
- Error message: [paste exact error]
- Profiles processed: 45 / 100
- Rate limit type: Google Sheets / DamaDam Login

What I've tried:
1. Waited 5 minutes
2. Increased SHEET_WRITE_DELAY to 2.0
3. Still failing after retry

Logs:
[Attach or paste relevant log snippets]

Request:
Need urgent help to resume scraping
```

---

## 📋 Quick Reference Checklist

### When Rate Limit Hits:

- [ ] ✋ Don't panic - scraper has built-in recovery
- [ ] ⏳ Let automatic retries complete (60s, 120s, 180s)
- [ ] 📊 Check what was completed in Google Sheet
- [ ] ⏸️ If failed, wait 5 minutes minimum
- [ ] 🔧 Adjust settings (increase delay, reduce batch)
- [ ] ▶️ Resume scraping (auto-skips completed)
- [ ] 👀 Monitor next run for stability

### When Login Fails:

- [ ] 🔄 Check if backup account kicked in
- [ ] ⏳ If no backup, wait 30 minutes
- [ ] 🔧 Consider adding backup account
- [ ] 🗑️ Delete cookies if persistent issues: `rm damadam_cookies.pkl`
- [ ] ▶️ Retry with smaller batch

### For Blank/Missing Data:

- [ ] 🔍 Check pattern (random vs consistent)
- [ ] 🧪 Test with known good profile
- [ ] 🐛 Report issue if selector problem
- [ ] ⏳ Wait for fix/patch
- [ ] 🔄 Re-scrape after fix applied

---

## 💡 Pro Tips

1. **Run During Off-Peak Hours**: 
   - Less competition for API quota
   - Better success rate
   - Recommended: Late night / early morning (your timezone)

2. **Start Small, Scale Up**:
   ```bash
   # Day 1: Test with 10 profiles
   python main.py target --max-profiles 10
   
   # Day 2: If stable, increase to 50
   python main.py target --max-profiles 50
   
   # Day 3+: Full automation
   python main.py target --max-profiles 0
   ```

3. **Use GitHub Actions for Heavy Lifting**:
   - Let cloud handle scheduled runs
   - Use local runs for urgent/small jobs
   - Benefit from automatic retries

4. **Keep Logs**:
   ```bash
   # Archive old logs periodically
   mkdir logs/archive
   mv logs/*.log logs/archive/
   
   # Review weekly for patterns
   grep "rate limit" logs/archive/*.log
   ```

5. **Monitor Dashboard**:
   - Weekly review of Dashboard tab
   - Track success/failure rates
   - Adjust strategy based on trends

---

**Last Updated:** January 2026  
**Version:** 1.0.0

**Need Help?** Contact: net2outlawzz@gmail.com
