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
    COLUMN_ORDER = [
        "ID",
        "NICK NAME",
        "TAGS",
        "CITY",
        "GENDER",
        "MARRIED",
        "AGE",
        "JOINED",
        "FOLLOWERS",
        "STATUS",
        "POSTS",
        "INTRO",
        "SOURCE",
        "DATETIME SCRAP",
        "LAST POST",
        "LAST POST TIME",
        "IMAGE",
        "PROFILE LINK",
        "POST URL",
        "FRIEND",
        "FRD",
        "RURL",
        "MEH NAME",
        "MEH TYPE",
        "MEH LINK",
        "MEH DATE",
        "PROFILE_STATE"
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
    DEFAULT_VALUES = {
        "ID": "",
        "NICK NAME": "",
        "TAGS": "",
        "CITY": "",
        "GENDER": "",
        "MARRIED": "",
        "AGE": "",
        "JOINED": "",
        "FOLLOWERS": "",
        "STATUS": "Normal",
        "POSTS": "",
        "INTRO": "",
        "SOURCE": "",
        "DATETIME SCRAP": "",
        "LAST POST": "",
        "LAST POST TIME": "",
        "IMAGE": "",
        "PROFILE LINK": "",
        "POST URL": "",
        "FRIEND": "",
        "FRD": "",
        "RURL": "",
        "MEH NAME": "",
        "MEH TYPE": "",
        "MEH LINK": "",
        "MEH DATE": "",
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
