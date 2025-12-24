"""
Manages the login process for the DamaDam website.

This module encapsulates the logic for authenticating the scraper's session,
using either saved cookies for a quick login or credentials for a fresh start.
It is designed to be resilient, with a fallback to a secondary account if the
primary one fails.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config_common import Config
from config.selectors import LoginSelectors
from .browser_manager import save_cookies, load_cookies, log_msg


class LoginManager:
    """Handles the DamaDam authentication process."""

    def __init__(self, driver):
        """Initializes the LoginManager with the WebDriver instance."""
        self.driver = driver

    def login(self):
        """Orchestrates the login process.

        It first attempts a quick login using saved session cookies. If that fails
        or no cookies are available, it proceeds with a full, fresh login using
        stored credentials.

        Returns:
            bool: True if login is successful, False otherwise.
        """
        log_msg("Starting authentication...", "LOGIN")

        try:
            if self._try_cookie_login():
                return True

            return self._fresh_login()

        except Exception as e:
            log_msg(f"Login failed: {e}", "ERROR")
            return False

    def _try_cookie_login(self):
        """Attempts to log in by loading saved cookies into the browser."""
        log_msg("Attempting cookie-based login...", "LOGIN")

        try:
            self.driver.get(Config.HOME_URL)
            time.sleep(2)

            if not load_cookies(self.driver):
                return False

            self.driver.refresh()
            time.sleep(3)

            if "login" not in self.driver.current_url.lower():
                log_msg("Cookie login successful", "OK")
                return True

            return False

        except Exception as e:
            log_msg(f"Cookie login failed: {e}", "LOGIN")
            return False

    def _fresh_login(self):
        """
        Performs a fresh login using username and password.

        It will try the primary account first. If that fails and a secondary
        account is configured, it will attempt to log in with the secondary
        credentials.
        """
        log_msg("Starting fresh login...", "LOGIN")

        try:
            self.driver.get(Config.LOGIN_URL)
            time.sleep(3)

            if self._try_account(
                Config.DAMADAM_USERNAME,
                Config.DAMADAM_PASSWORD,
                "Primary"
            ):
                save_cookies(self.driver)
                log_msg("Fresh login successful", "OK")
                return True

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
        """
        Attempts to log in with a specific set of credentials.

        Finds the username and password fields, fills them, and submits the form.

        Args:
            username (str): The account username.
            password (str): The account password.
            label (str): A label for logging (e.g., 'Primary', 'Secondary').

        Returns:
            bool: True on successful login, False otherwise.
        """
        log_msg(f"Attempting login with {label} account...", "LOGIN")

        try:
            nick = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, LoginSelectors.USERNAME_FIELD)
                )
            )

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

            btn = self.driver.find_element(
                By.CSS_SELECTOR,
                LoginSelectors.SUBMIT_BUTTON
            )

            nick.clear()
            nick.send_keys(username)
            time.sleep(0.5)

            pw.clear()
            pw.send_keys(password)
            time.sleep(0.5)

            btn.click()
            time.sleep(4)

            if "login" not in self.driver.current_url.lower():
                log_msg(f"{label} account login successful", "OK")
                return True

            log_msg(f"{label} account login failed", "LOGIN")
            return False

        except Exception as e:
            log_msg(f"{label} account error: {e}", "LOGIN")
            return False
