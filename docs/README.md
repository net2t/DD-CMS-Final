# DD-CMS-V3 Documentation

## Quick Start

### 1. Setup
```bash
pip install -r requirements.txt
cp .env.sample .env
# Fill in your credentials in .env
```

### 2. Run Modes

| Command | What it does |
|---|---|
| `python run.py online` | Online Mode — scrape current online users once |
| `python run.py target` | Target Mode — process RunList pending entries once |
| `python run.py scheduler` | Auto Online Mode every 15 min (no overlap) |
| `python run.py online --limit 20` | Online mode, max 20 profiles |
| `python run.py target --limit 10` | Target mode, max 10 profiles |
| `python run.py scheduler --limit 50` | Scheduler, max 50 profiles per run |

---

## How Each Mode Works

### Online Mode
1. Opens `damadam.pk/online_kon/` — fetches list of currently online users
2. For each user: scrapes profile → checks Tags sheet → writes to Profiles sheet (Row 2)
3. Col 9 (LIST) = empty | Col 11 (RUN MODE) = "Online"
4. Does NOT touch RunList
5. At the end: sorts Profiles sheet by DATETIME SCRAP descending
6. Updates Dashboard with run summary

### Target Mode
1. Reads RunList sheet — picks rows where Status = "⚡ Pending"
2. Skips rows where Col D has a value (ignore nick list)
3. For each pending nick: scrapes profile → writes to Profiles sheet (Row 2)
4. Marks RunList row "Done 💀" **immediately** after each profile (crash-safe)
5. Col 9 (LIST) = RunList Col F value | Col 11 (RUN MODE) = "Target"
6. At the end: sorts Profiles sheet by DATETIME SCRAP descending
7. Updates Dashboard with run summary

---

## Sheet Structure

### Profiles Sheet — Column Reference
```
Col  Index  Header          Notes
───  ─────  ──────────────  ───────────────────────────────────────────
A    0      ID              DamaDam user ID
B    1      NICK NAME       Username
C    2      TAGS            From Tags sheet (auto-matched)
D    3      CITY
E    4      GENDER
F    5      MARRIED
G    6      AGE
H    7      JOINED
I    8      FOLLOWERS
J    9      LIST            RunList Col F value (Target) / empty (Online)
K    10     POSTS
L    11     RUN MODE        "Online" or "Target"
M    12     DATETIME SCRAP  Used for date sort — Col M descending
N    13     LAST POST
O    14     LAST POST TIME
P    15     IMAGE
Q    16     PROFILE LINK
R    17     POST URL        Public profile page ?page=1
S    18     RURL            Rank image URL
T    19     MEH NAME
U    20     MEH LINK
V    21     MEH DATE
W    22     PHASE 2         "Ready" if Posts < 100, else "Not Eligible"
```

### RunList Sheet — Column Reference
```
Col  What
───  ──────────────────────────────────────────────────────
A    Nickname
B    Status (Pending / Done / Error / Skip)
C    Remarks (auto-filled by scraper)
D    Ignore Nick (if filled, that nick is skipped)
E    (reserved)
F    List Tag Value → goes to Profiles Col J (LIST)
```

### Dashboard Sheet
```
RUN# | TIMESTAMP | PROFILES | SUCCESS | FAILED | NEW | UPDATED | DIFF | UNCHANGED | TRIGGER | START | END
```

---

## Lock System

A file `run.lock` is created when a run starts and deleted when it finishes.

- If you try to start a run while one is active → it exits immediately
- Scheduler: if the 15-minute tick fires while a run is active → tick is silently skipped
- If a run crashes: **manually delete `run.lock`** before the next run

---

## Configuration (.env)

```env
DAMADAM_USERNAME=your_nick
DAMADAM_PASSWORD=your_pass
DAMADAM_USERNAME_2=backup_nick        # optional backup account
DAMADAM_PASSWORD_2=backup_pass

GOOGLE_SHEET_URL=https://docs.google.com/...
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
# OR use JSON string:
# GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}

MAX_PROFILES_PER_RUN=0               # 0 = unlimited
BATCH_SIZE=50                        # internal batch size (default 50)
MIN_DELAY=0.3                        # seconds between profiles (min)
MAX_DELAY=0.5                        # seconds between profiles (max)
PAGE_LOAD_TIMEOUT=10

LAST_POST_FETCH_PUBLIC_PAGE=false    # true = fetch page 1 for last post (slower)
LAST_POST_PUBLIC_PAGE_TIMEOUT=8
SORT_PROFILES_BY_DATE=true           # sort after each run
```

---

## Core Lock Policy

The following files must NOT be modified (by anyone or any AI):
- `core/browser_manager.py`
- `core/login_manager.py`
- `core/run_context.py`

These files handle browser startup and login — they are confirmed working and stable.
See `core/CORE_LOCK.md` for the full policy.

---

## Web View (Coming Soon)
The web view feature will be added in a future update once the scraping pipeline is stable.
