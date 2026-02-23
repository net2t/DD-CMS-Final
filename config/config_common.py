"""
Central Configuration — DD-CMS-V3

All environment variables, column definitions, and run constants live here.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent.parent.absolute()
env_path = SCRIPT_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)


class Config:

    # ── DamaDam Credentials ──────────────────────────────────────────────────
    DAMADAM_USERNAME   = os.getenv('DAMADAM_USERNAME', '').strip()
    DAMADAM_PASSWORD   = os.getenv('DAMADAM_PASSWORD', '').strip()
    DAMADAM_USERNAME_2 = os.getenv('DAMADAM_USERNAME_2', '').strip()
    DAMADAM_PASSWORD_2 = os.getenv('DAMADAM_PASSWORD_2', '').strip()

    # ── Google Sheets ────────────────────────────────────────────────────────
    GOOGLE_SHEET_URL            = os.getenv('GOOGLE_SHEET_URL', '').strip()
    GOOGLE_CREDENTIALS_JSON     = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json').strip()

    # ── Run Settings ─────────────────────────────────────────────────────────
    MAX_PROFILES_PER_RUN  = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))
    BATCH_SIZE            = int(os.getenv('BATCH_SIZE', '50'))   # default 50
    MIN_DELAY             = float(os.getenv('MIN_DELAY', '0.3'))
    MAX_DELAY             = float(os.getenv('MAX_DELAY', '0.5'))
    PAGE_LOAD_TIMEOUT     = int(os.getenv('PAGE_LOAD_TIMEOUT', '10'))
    SHEET_WRITE_DELAY     = float(os.getenv('SHEET_WRITE_DELAY', '0.5'))

    # Last Post: fetch public profile page 1 to get most recent post.
    # false = fast mode (skip public page), true = full data but uses more API quota.
    LAST_POST_FETCH_PUBLIC_PAGE   = os.getenv('LAST_POST_FETCH_PUBLIC_PAGE', 'false').lower() == 'true'
    LAST_POST_PUBLIC_PAGE_TIMEOUT = int(os.getenv('LAST_POST_PUBLIC_PAGE_TIMEOUT', '8'))

    # Sort Profiles sheet by DATETIME SCRAP descending at end of each run.
    SORT_PROFILES_BY_DATE = os.getenv('SORT_PROFILES_BY_DATE', 'true').lower() == 'true'

    # ── Paths ─────────────────────────────────────────────────────────────────
    SCRIPT_DIR        = SCRIPT_DIR
    CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', '').strip()
    COOKIE_FILE       = SCRIPT_DIR / 'damadam_cookies.pkl'

    # ── URLs ──────────────────────────────────────────────────────────────────
    BASE_URL          = "https://damadam.pk"
    LOGIN_URL         = "https://damadam.pk/login/"
    HOME_URL          = "https://damadam.pk/"
    ONLINE_USERS_URL  = "https://damadam.pk/online_kon/"

    # ── Environment ───────────────────────────────────────────────────────────
    IS_CI             = bool(os.getenv('GITHUB_ACTIONS'))
    IS_GITHUB_ACTIONS = IS_CI
    SCRIPT_VERSION    = "v3.0.0"

    # ── Sheet Names ───────────────────────────────────────────────────────────
    SHEET_PROFILES  = "Profiles"
    SHEET_TARGET    = "RunList"
    SHEET_DASHBOARD = "Dashboard"
    SHEET_TAGS      = "Tags"

    # ── Column Order (Profiles Sheet) ─────────────────────────────────────────
    #
    #   Index  Header           Notes
    #   ─────  ──────────────   ──────────────────────────────────────────────
    #   0      ID
    #   1      NICK NAME
    #   2      TAGS             Matched from Tags sheet
    #   3      CITY
    #   4      GENDER
    #   5      MARRIED
    #   6      AGE
    #   7      JOINED
    #   8      FOLLOWERS
    #   9      LIST             ← RunList Col F value goes here
    #   10     POSTS
    #   11     RUN MODE         ← "Online" or "Target" (was SKIP/DEL)
    #   12     DATETIME SCRAP   ← Used for date sort (Col M)
    #   13     LAST POST
    #   14     LAST POST TIME
    #   15     IMAGE
    #   16     PROFILE LINK
    #   17     POST URL
    #   18     RURL
    #   19     MEH NAME
    #   20     MEH LINK
    #   21     MEH DATE
    #   22     PHASE 2
    #
    COLUMN_ORDER = [
        "ID",               # 0
        "NICK NAME",        # 1
        "TAGS",             # 2
        "CITY",             # 3
        "GENDER",           # 4
        "MARRIED",          # 5
        "AGE",              # 6
        "JOINED",           # 7
        "FOLLOWERS",        # 8
        "LIST",             # 9  ← RunList Col F value
        "POSTS",            # 10
        "RUN MODE",         # 11 ← "Online" / "Target"
        "DATETIME SCRAP",   # 12
        "LAST POST",        # 13
        "LAST POST TIME",   # 14
        "IMAGE",            # 15
        "PROFILE LINK",     # 16
        "POST URL",         # 17
        "RURL",             # 18
        "MEH NAME",         # 19
        "MEH LINK",         # 20
        "MEH DATE",         # 21
        "PHASE 2",          # 22
    ]

    # Column index shortcuts (0-based)
    COL_LIST     = 9   # "LIST"     — RunList Col F value
    COL_RUN_MODE = 11  # "RUN MODE" — Online / Target

    # ── Target / RunList Status Values ────────────────────────────────────────
    TARGET_STATUS_PENDING  = "⚡ Pending"
    TARGET_STATUS_DONE     = "Done 💀"
    TARGET_STATUS_ERROR    = "Error 💥"
    TARGET_STATUS_SKIP_DEL = "Skip/Del 🚫"

    # ── Suspension Detection ──────────────────────────────────────────────────
    SUSPENSION_INDICATORS = [
        "accounts suspend",
        "aik se zyada fake accounts",
        "abuse ya harassment",
        "kisi aur user ki identity apnana",
        "accounts suspend kiye",
    ]

    # ── Default Column Values ─────────────────────────────────────────────────
    DEFAULT_VALUES = {col: "" for col in [
        "ID", "NICK NAME", "TAGS", "CITY", "GENDER", "MARRIED", "AGE",
        "JOINED", "FOLLOWERS", "LIST", "POSTS", "RUN MODE", "DATETIME SCRAP",
        "LAST POST", "LAST POST TIME", "IMAGE", "PROFILE LINK", "POST URL",
        "RURL", "MEH NAME", "MEH LINK", "MEH DATE", "PHASE 2",
    ]}

    @classmethod
    def validate(cls):
        errors = []
        if not cls.DAMADAM_USERNAME:
            errors.append("DAMADAM_USERNAME is required")
        if not cls.DAMADAM_PASSWORD:
            errors.append("DAMADAM_PASSWORD is required")
        if not cls.GOOGLE_SHEET_URL:
            errors.append("GOOGLE_SHEET_URL is required")
        has_json = bool(cls.GOOGLE_CREDENTIALS_JSON)
        cred_path = cls.get_credentials_path()
        has_file  = cred_path and Path(cred_path).exists()
        if not has_json and not has_file:
            errors.append("Google credentials required (JSON env var or credentials.json file)")
        if errors:
            print("=" * 60)
            for e in errors:
                print(f"[CONFIG ERROR] {e}")
            print("=" * 60)
            sys.exit(1)
        return True

    @classmethod
    def get_credentials_path(cls):
        if cls.GOOGLE_APPLICATION_CREDENTIALS:
            p = Path(cls.GOOGLE_APPLICATION_CREDENTIALS)
            return p if p.is_absolute() else cls.SCRIPT_DIR / cls.GOOGLE_APPLICATION_CREDENTIALS
        return cls.SCRIPT_DIR / 'credentials.json'
