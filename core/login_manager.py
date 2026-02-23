"""
Login Manager — DamaDam Authentication

⚠️  CORE LOCK — DO NOT MODIFY ⚠️
See core/CORE_LOCK.md for details.
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
    """Handles the DamaDam authentication process with cookies and backup failover."""

    def __init__(self, driver):
        self.driver = driver

    def login(self):
        log_msg("Starting authentication...", "LOGIN")
        try:
            if not Config.IS_GITHUB_ACTIONS:
                if self._try_cookie_login():
                    log_msg("Cookie login successful", "OK")
                    return True
                log_msg("Cookie login failed, trying fresh login...", "WARNING")

            if self._fresh_login(Config.DAMADAM_USERNAME, Config.DAMADAM_PASSWORD, "Primary"):
                log_msg("Primary account login successful", "OK")
                return True

            if Config.DAMADAM_USERNAME_2 and Config.DAMADAM_PASSWORD_2:
                log_msg("Primary login failed, trying backup account...", "WARNING")
                if self._fresh_login(Config.DAMADAM_USERNAME_2, Config.DAMADAM_PASSWORD_2, "Backup"):
                    log_msg("Backup account login successful", "OK")
                    return True

            log_msg("All login attempts failed", "ERROR")
            return False

        except Exception as e:
            log_msg(f"Login failed: {e}", "ERROR")
            return False

    def _try_cookie_login(self):
        log_msg("Attempting cookie-based login...", "LOGIN")
        try:
            self.driver.get(Config.HOME_URL)
            time.sleep(2)
            if not load_cookies(self.driver):
                return False
            self.driver.refresh()
            time.sleep(3)
            return "login" not in self.driver.current_url.lower()
        except Exception as e:
            log_msg(f"Cookie login error: {e}", "LOGIN")
            return False

    def _fresh_login(self, username, password, label):
        log_msg(f"Attempting fresh login with {label} account...", "LOGIN")
        try:
            self.driver.get(Config.LOGIN_URL)
            time.sleep(3)

            nick = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, LoginSelectors.USERNAME_FIELD))
            )
            try:
                pw = self.driver.find_element(By.CSS_SELECTOR, LoginSelectors.PASSWORD_FIELD_1)
            except Exception:
                pw = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, LoginSelectors.PASSWORD_FIELD_2))
                )

            btn = self.driver.find_element(By.CSS_SELECTOR, LoginSelectors.SUBMIT_BUTTON)

            nick.clear()
            nick.send_keys(username)
            time.sleep(0.5)
            pw.clear()
            pw.send_keys(password)
            time.sleep(0.5)
            btn.click()
            time.sleep(4)

            if "login" not in self.driver.current_url.lower():
                if not Config.IS_GITHUB_ACTIONS:
                    save_cookies(self.driver)
                    log_msg("Session cookies saved", "OK")
                return True

            log_msg(f"{label} account login failed", "LOGIN")
            return False

        except Exception as e:
            log_msg(f"{label} account error: {e}", "LOGIN")
            return False
