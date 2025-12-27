"""
Manages the login process for the DamaDam website.

Enhanced with:
- Cookie-based session persistence
- Automatic backup account failover
- GitHub Actions compatibility (no cookies)
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config_common import Config
from config.selectors import LoginSelectors
from .browser_manager import save_cookies, load_cookies
from utils.ui import log_msg


class LoginManager:
    """Handles the DamaDam authentication process with cookies and backup login."""

    def __init__(self, driver):
        """Initializes the LoginManager with the WebDriver instance."""
        self.driver = driver

    def login(self):
        """Orchestrates the login process with cookie persistence and backup failover.

        Login Strategy:
        1. Try cookie-based login (if not in CI/GitHub Actions)
        2. Try primary account fresh login
        3. Try backup account fresh login (if configured)

        Returns:
            bool: True if login is successful, False otherwise.
        """
        log_msg("🔐 Starting authentication...", "LOGIN")

        try:
            # Skip cookie login in GitHub Actions (no file persistence)
            if not Config.IS_GITHUB_ACTIONS:
                if self._try_cookie_login():
                    log_msg("✅ Cookie login successful", "OK")
                    return True
                else:
                    log_msg("⚠️ Cookie login failed, trying fresh login...", "WARNING")

            # Try fresh login with primary account
            if self._fresh_login(
                Config.DAMADAM_USERNAME,
                Config.DAMADAM_PASSWORD,
                "Primary"
            ):
                log_msg("✅ Primary account login successful", "OK")
                return True

            # Try backup account if configured
            if Config.DAMADAM_USERNAME_2 and Config.DAMADAM_PASSWORD_2:
                log_msg("⚠️ Primary login failed, trying backup account...", "WARNING")
                if self._fresh_login(
                    Config.DAMADAM_USERNAME_2,
                    Config.DAMADAM_PASSWORD_2,
                    "Backup"
                ):
                    log_msg("✅ Backup account login successful", "OK")
                    return True

            log_msg("❌ All login attempts failed", "ERROR")
            return False

        except Exception as e:
            log_msg(f"❌ Login failed: {e}", "ERROR")
            return False

    def _try_cookie_login(self):
        """Attempts to log in by loading saved cookies into the browser."""
        log_msg("🍪 Attempting cookie-based login...", "LOGIN")

        try:
            self.driver.get(Config.HOME_URL)
            time.sleep(2)

            if not load_cookies(self.driver):
                return False

            self.driver.refresh()
            time.sleep(3)

            if "login" not in self.driver.current_url.lower():
                return True

            return False

        except Exception as e:
            log_msg(f"⚠️ Cookie login failed: {e}", "LOGIN")
            return False

    def _fresh_login(self, username, password, label):
        """
        Performs a fresh login using username and password.

        Args:
            username (str): The account username.
            password (str): The account password.
            label (str): A label for logging (e.g., 'Primary', 'Backup').

        Returns:
            bool: True on successful login, False otherwise.
        """
        log_msg(f"🔑 Attempting fresh login with {label} account...", "LOGIN")

        try:
            self.driver.get(Config.LOGIN_URL)
            time.sleep(3)

            # Find username field
            nick = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, LoginSelectors.USERNAME_FIELD)
                )
            )

            # Find password field
            try:
                pw = self.driver.find_element(
                    By.CSS_SELECTOR,
                    LoginSelectors.PASSWORD_FIELD_1
                )
            except:
                pw = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, LoginSelectors.PASSWORD_FIELD_2)
                    )
                )

            # Find submit button
            btn = self.driver.find_element(
                By.CSS_SELECTOR,
                LoginSelectors.SUBMIT_BUTTON
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
            if "login" not in self.driver.current_url.lower():
                # Save cookies for future use (skip in CI)
                if not Config.IS_GITHUB_ACTIONS:
                    save_cookies(self.driver)
                    log_msg("💾 Session cookies saved", "OK")
                return True

            log_msg(f"⚠️ {label} account login failed", "LOGIN")
            return False

        except Exception as e:
            log_msg(f"❌ {label} account error: {e}", "LOGIN")
            return False
