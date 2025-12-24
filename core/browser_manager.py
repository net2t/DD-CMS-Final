"""
Core browser management utilities.

This module contains the BrowserManager class, which is a wrapper around the
Selenium WebDriver for starting, configuring, and stopping the browser.
It also includes helper functions for saving and loading cookies to persist
login sessions across multiple runs.
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
    """Manages the lifecycle of the Chrome WebDriver instance."""

    def __init__(self):
        """Initializes the BrowserManager, but does not start the browser."""
        self.driver = None

    def start(self):
        """
        Initializes and configures the Chrome WebDriver.

        Sets up headless mode, window size, and various options to avoid
        detection. It can use a custom ChromeDriver if the path is specified
        in the config.

        Returns:
            The configured WebDriver instance, or None on failure.
        """
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
        """Safely closes the WebDriver instance, ignoring any errors."""
        if self.driver:
            try:
                self.driver.quit()
                log_msg("Browser closed")
            except:
                pass


def save_cookies(driver):
    """
    Saves the current browser session cookies to a file using pickle.

    This allows the scraper to persist logins between sessions, avoiding the need
    to re-authenticate with a username and password every time.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        bool: True if cookies were saved successfully, False otherwise.
    """
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
    """
    Loads cookies from a file and adds them to the current browser session.

    This is used at the start of a run to attempt to restore a previous login
    session, which is faster and less likely to trigger security measures.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        bool: True if cookies were loaded successfully, False otherwise.
    """
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
