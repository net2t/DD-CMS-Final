"""
Configuration Manager for DamaDam Scraper v4.0
Handles all environment variables and settings
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get script directory
SCRIPT_DIR = Path(__file__).parent.absolute()

# Load .env file
env_path = SCRIPT_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

class Config:
    """Central configuration class"""
    
    # ==================== DAMADAM CREDENTIALS ====================
    DAMADAM_USERNAME = os.getenv('DAMADAM_USERNAME', '').strip()
    DAMADAM_PASSWORD = os.getenv('DAMADAM_PASSWORD', '').strip()
    DAMADAM_USERNAME_2 = os.getenv('DAMADAM_USERNAME_2', '').strip()
    DAMADAM_PASSWORD_2 = os.getenv('DAMADAM_PASSWORD_2', '').strip()
    
    # ==================== GOOGLE SHEETS ====================
    GOOGLE_SHEET_URL = os.getenv('GOOGLE_SHEET_URL', '').strip()
    GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json').strip()
    
    # ==================== SCRAPING SETTINGS ====================
    MAX_PROFILES_PER_RUN = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))
    MIN_DELAY = float(os.getenv('MIN_DELAY', '0.3'))
    MAX_DELAY = float(os.getenv('MAX_DELAY', '0.5'))
    PAGE_LOAD_TIMEOUT = int(os.getenv('PAGE_LOAD_TIMEOUT', '30'))
    SHEET_WRITE_DELAY = float(os.getenv('SHEET_WRITE_DELAY', '1.0'))
    
    # ==================== PATHS ====================
    SCRIPT_DIR = SCRIPT_DIR
    CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', '').strip()
    COOKIE_FILE = SCRIPT_DIR / 'damadam_cookies.pkl'
    
    # ==================== URLS ====================
    LOGIN_URL = "https://damadam.pk/login/"
    HOME_URL = "https://damadam.pk/"
    ONLINE_USERS_URL = "https://damadam.pk/online_kon/"
    
    # ==================== ENVIRONMENT ====================
    IS_CI = bool(os.getenv('GITHUB_ACTIONS'))
    IS_GITHUB_ACTIONS = IS_CI
    
    # ==================== SHEET NAMES ====================
    SHEET_PROFILES = "ProfilesTarget"
    SHEET_TARGET = "Target"
    SHEET_DASHBOARD = "Dashboard"
    SHEET_TAGS = "Tags"
    SHEET_ONLINE_LOG = "OnlineLog"
    
    # ==================== COLUMN CONFIGURATION ====================
    # STEP-6: Cleaned and reordered columns
    # Order: 0 1 2 3 4 6 5 6 7 8 9 11 24 12 13 21 20 22 10 19 15 16 18 17 23
    # Removed: DELETE COL L, DELCOL U
    COLUMN_ORDER = [
        "ID",                  # 0
        "NICK NAME",          # 1
        "TAGS",               # 2
        "CITY",               # 3
        "GENDER",             # 4
        "AGE",                # 5 (was 6, swapped with MARRIED)
        "MARRIED",            # 6 (was 5, swapped with AGE)
        "JOINED",             # 7
        "FOLLOWERS",          # 8
        "STATUS",             # 9
        "INTRO",              # 10 (was 11, moved up)
        "PROFILE_STATE",      # 11 (was 24, moved up)
        "SOURCE",             # 12
        "DATETIME SCRAP",     # 13
        "RURL",               # 14 (was 21, moved up)
        "POST URL",           # 15 (was 20, moved up)
        "PROFILE LINK",       # 16 (was 22, moved up)
        "POSTS",              # 17 (was 10, moved down)
        "LAST POST TIME",     # 18 (was 19, moved up)
        "IMAGE",              # 19 (was 15, moved down)
        "LAST POST",          # 20 (was 16, moved down)
        "FRD",                # 21 (was 18, moved down)
        "FRIEND",             # 22 (was 17, moved down)
        "MEH NAME",           # 23 (was 23, same)
        "MEH TYPE",           # 24
        "MEH LINK",           # 25 - NEXT PHASE: Mehfil scraping source
        "MEH DATE"            # 26
    ]
    
    ONLINE_LOG_COLUMNS = ["Date Time", "Nickname", "Last Seen"]
    
    # ==================== TARGET STATUS ====================
    TARGET_STATUS_PENDING = "⚡ Pending"
    TARGET_STATUS_DONE = "Done 💀"
    TARGET_STATUS_ERROR = "Error 💥"
    
    # ==================== PROFILE STATES ====================
    PROFILE_STATE_ACTIVE = "ACTIVE"
    PROFILE_STATE_UNVERIFIED = "UNVERIFIED"
    PROFILE_STATE_BANNED = "BANNED"
    PROFILE_STATE_DEAD = "DEAD"
    
    # ==================== SUSPENSION DETECTION ====================
    SUSPENSION_INDICATORS = [
        "accounts suspend",
        "aik se zyada fake accounts",
        "abuse ya harassment",
        "kisi aur user ki identity apnana",
        "accounts suspend kiye",
    ]
    
    # ==================== DEFAULT VALUES ====================
    # STEP-6: Use "BLANK" instead of empty strings
    DEFAULT_VALUES = {
        "ID": "BLANK",
        "NICK NAME": "BLANK",
        "TAGS": "BLANK",
        "CITY": "BLANK",
        "GENDER": "BLANK",
        "MARRIED": "BLANK",
        "AGE": "BLANK",
        "JOINED": "BLANK",
        "FOLLOWERS": "BLANK",
        "STATUS": "Normal",
        "POSTS": "BLANK",
        "INTRO": "BLANK",
        "SOURCE": "BLANK",
        "DATETIME SCRAP": "BLANK",
        "LAST POST": "BLANK",
        "LAST POST TIME": "BLANK",
        "IMAGE": "BLANK",
        "PROFILE LINK": "BLANK",
        "POST URL": "BLANK",
        "FRIEND": "BLANK",
        "FRD": "BLANK",
        "RURL": "BLANK",
        "MEH NAME": "BLANK",
        "MEH TYPE": "BLANK",
        "MEH LINK": "BLANK",
        "MEH DATE": "BLANK",
        "PROFILE_STATE": "ACTIVE"
    }
    
    # ==================== VALIDATION ====================
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        print("=" * 70)
        print("CONFIGURATION VALIDATION")
        print("=" * 70)
        
        cred_path = cls._get_credentials_path()
        print(f"📍 Script Directory: {cls.SCRIPT_DIR}")
        print(f"📍 Credentials Path: {cred_path}")
        
        if cred_path:
            file_exists = Path(cred_path).exists() if cred_path else False
            print(f"📁 File exists: {file_exists}")
        
        if not cls.DAMADAM_USERNAME:
            errors.append("❌ DAMADAM_USERNAME is required")
        else:
            masked = cls.DAMADAM_USERNAME[:3] + "***" if len(cls.DAMADAM_USERNAME) > 3 else "***"
            print(f"✅ DamaDam Username: {masked}")
        
        if not cls.DAMADAM_PASSWORD:
            errors.append("❌ DAMADAM_PASSWORD is required")
        
        if not cls.GOOGLE_SHEET_URL:
            errors.append("❌ GOOGLE_SHEET_URL is required")
        else:
            print(f"✅ Google Sheet URL: Present")
        
        has_json = bool(cls.GOOGLE_CREDENTIALS_JSON)
        has_file = cred_path and Path(cred_path).exists()
        
        if not has_json and not has_file:
            errors.append("❌ Google credentials required (either JSON or file)")
        else:
            if has_json:
                print(f"✅ Google Credentials: Raw JSON found")
            if has_file:
                print(f"✅ Google Credentials: File found at {cred_path}")
        
        print("=" * 70)
        
        if errors:
            print("❌ VALIDATION FAILED")
            print("=" * 70)
            for error in errors:
                print(error)
            print("=" * 70)
            sys.exit(1)
        
        print("✅ VALIDATION PASSED")
        print("=" * 70)
        return True
    
    @classmethod
    def _get_credentials_path(cls):
        """Get the actual credentials file path"""
        if cls.GOOGLE_APPLICATION_CREDENTIALS:
            p = Path(cls.GOOGLE_APPLICATION_CREDENTIALS)
            if p.is_absolute():
                return p
            return cls.SCRIPT_DIR / cls.GOOGLE_APPLICATION_CREDENTIALS
        return cls.SCRIPT_DIR / 'credentials.json'
    
    @classmethod
    def get_credentials_path(cls):
        """Public method to get credentials path"""
        return cls._get_credentials_path()

# Validate on import
if not hasattr(Config, '_validated'):
    Config.validate()
    Config._validated = True
