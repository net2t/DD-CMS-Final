"""
Login utilities extracted from browser.py
DO NOT CHANGE LOGIC
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config_common import Config
from .browser_manager import save_cookies, load_cookies, log_msg


class LoginManager:
    """Handles DamaDam login"""

    def __init__(self, driver):
        self.driver = driver

    def login(self):
        """Attempt login with saved cookies or credentials"""
        log_msg("Starting authentication...", "LOGIN")

        try:
            if self._try_cookie_login():
                return True

            return self._fresh_login()

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

            if "login" not in self.driver.current_url.lower():
                log_msg("Cookie login successful", "OK")
                return True

            return False

        except Exception as e:
            log_msg(f"Cookie login failed: {e}", "LOGIN")
            return False

    def _fresh_login(self):
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
        log_msg(f"Attempting login with {label} account...", "LOGIN")

        try:
            nick = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#nick, input[name='nick']")
                )
            )

            try:
                pw = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#pass, input[name='pass']"
                )
            except:
                pw = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[type='password']")
                    )
                )

            btn = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[type='submit'], form button"
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
