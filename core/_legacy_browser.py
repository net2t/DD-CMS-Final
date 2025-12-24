# LEGACY FILE
# DO NOT IMPORT
# Used only as reference during refactor
"""
Browser Manager - Chrome setup and login handling
"""

import time
import pickle
from pathlib import Path
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import Config

# ==================== TIME HELPERS ====================

def get_pkt_time():
    """Get current Pakistan time (UTC+5)"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log_msg(msg, level="INFO"):
    """Simple logger with timestamp"""
    ts = get_pkt_time().strftime('%H:%M:%S')
    print(f"[{ts}] [{level}] {msg}")
    import sys
    sys.stdout.flush()

# ==================== BROWSER SETUP ====================

class BrowserManager:
    """Manages Chrome browser instance"""
    
    def __init__(self):
        self.driver = None
    
    def setup(self):
        """Initialize Chrome browser"""
        log_msg("Initializing Chrome browser...")
        try:
            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option('excludeSwitches', ['enable-automation'])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--log-level=3")
            
            # Use custom ChromeDriver path if provided
            if Config.CHROMEDRIVER_PATH and Path(Config.CHROMEDRIVER_PATH).exists():
                log_msg(f"Using custom ChromeDriver: {Config.CHROMEDRIVER_PATH}")
                service = Service(executable_path=Config.CHROMEDRIVER_PATH)
                self.driver = webdriver.Chrome(service=service, options=opts)
            else:
                log_msg("Using system ChromeDriver")
                self.driver = webdriver.Chrome(options=opts)
            
            self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
            self.driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            
            log_msg("Browser initialized successfully", "OK")
            return self.driver
        
        except Exception as e:
            log_msg(f"Browser setup failed: {e}", "ERROR")
            return None
    
    def close(self):
        """Close browser safely"""
        if self.driver:
            try:
                self.driver.quit()
                log_msg("Browser closed")
            except:
                pass

# ==================== COOKIE MANAGEMENT ====================

def save_cookies(driver):
    """Save cookies to file"""
    try:
        with open(Config.COOKIE_FILE, 'wb') as f:
            cookies = driver.get_cookies()
            pickle.dump(cookies, f)
            log_msg(f"Cookies saved ({len(cookies)} items)", "OK")
        return True
    except Exception as e:
        log_msg(f"Cookie save failed: {e}", "ERROR")
        return False

def load_cookies(driver):
    """Load cookies from file"""
    try:
        if not Config.COOKIE_FILE.exists():
            log_msg("No saved cookies found")
            return False
        
        with open(Config.COOKIE_FILE, 'rb') as f:
            cookies = pickle.load(f)
        
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except:
                pass
        
        log_msg(f"Cookies loaded ({len(cookies)} items)", "OK")
        return True
    
    except Exception as e:
        log_msg(f"Cookie load failed: {e}")
        return False

# ==================== LOGIN HANDLER ====================

class LoginManager:
    """Handles DamaDam login"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def login(self):
        """Attempt login with saved cookies or credentials"""
        log_msg("Starting authentication...", "LOGIN")
        
        try:
            # Try cookie login first
            if self._try_cookie_login():
                return True
            
            # Fresh login
            return self._fresh_login()
        
        except Exception as e:
            log_msg(f"Login failed: {e}", "ERROR")
            return False
    
    def _try_cookie_login(self):
        """Try logging in with saved cookies"""
        log_msg("Attempting cookie-based login...", "LOGIN")
        
        try:
            self.driver.get(Config.HOME_URL)
            time.sleep(2)
            
            if not load_cookies(self.driver):
                return False
            
            self.driver.refresh()
            time.sleep(3)
            
            # Check if we're logged in
            if 'login' not in self.driver.current_url.lower():
                log_msg("Cookie login successful", "OK")
                return True
            
            return False
        
        except Exception as e:
            log_msg(f"Cookie login failed: {e}")
            return False
    
    def _fresh_login(self):
        """Perform fresh login with credentials"""
        log_msg("Starting fresh login...", "LOGIN")
        
        try:
            self.driver.get(Config.LOGIN_URL)
            time.sleep(3)
            
            # Try primary account
            if self._try_account(
                Config.DAMADAM_USERNAME, 
                Config.DAMADAM_PASSWORD,
                "Primary"
            ):
                save_cookies(self.driver)
                log_msg("Fresh login successful", "OK")
                return True
            
            # Try secondary account if available
            if Config.DAMADAM_USERNAME_2 and Config.DAMADAM_PASSWORD_2:
                if self._try_account(
                    Config.DAMADAM_USERNAME_2,
                    Config.DAMADAM_PASSWORD_2,
                    "Secondary"
                ):
                    save_cookies(self.driver)
                    log_msg("Fresh login successful (secondary)", "OK")
                    return True
            
            return False
        
        except Exception as e:
            log_msg(f"Fresh login failed: {e}", "ERROR")
            return False
    
    def _try_account(self, username, password, label):
        """Try logging in with specific account"""
        log_msg(f"Attempting login with {label} account...", "LOGIN")
        
        try:
            # Find username field
            nick = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#nick, input[name='nick']")
                )
            )
            
            # Find password field
            try:
                pw = self.driver.find_element(By.CSS_SELECTOR, "#pass, input[name='pass']")
            except:
                pw = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[type='password']")
                    )
                )
            
            # Find submit button
            btn = self.driver.find_element(
                By.CSS_SELECTOR, 
                "button[type='submit'], form button"
            )
            
            # Fill and submit
            nick.clear()
            nick.send_keys(username)
            time.sleep(0.5)
            
            pw.clear()
            pw.send_keys(password)
            time.sleep(0.5)
            
            btn.click()
            time.sleep(4)
            
            # Check success
            if 'login' not in self.driver.current_url.lower():
                log_msg(f"{label} account login successful", "OK")
                return True
            
            log_msg(f"{label} account login failed", "LOGIN")
            return False
        
        except Exception as e:
            log_msg(f"{label} account error: {e}", "LOGIN")
            return False
