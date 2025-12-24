"""
Core browser utilities (extracted from browser.py)
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

from config.config_common import Config
from utils.ui import log_msg


class BrowserManager:
    """Manages Chrome browser instance"""

    def __init__(self):
        self.driver = None

    def start(self):
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
