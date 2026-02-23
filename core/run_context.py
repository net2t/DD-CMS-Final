"""
RunContext — Shared state for a single scraper run.

⚠️  CORE LOCK — DO NOT MODIFY ⚠️
See core/CORE_LOCK.md for details.
"""

from typing import Optional
from .browser_manager import BrowserManager, log_msg
from .login_manager import LoginManager
from utils.sheets_manager import SheetsManager


class RunContext:
    """Manages the shared state for a single scraper run."""

    def __init__(self):
        self.browser_manager = BrowserManager()
        self.driver = None
        self.login_manager: Optional[LoginManager] = None

    def start_browser(self):
        if not self.driver:
            self.driver = self.browser_manager.start()
        return self.driver

    def login(self):
        driver = self.start_browser()
        if not driver:
            log_msg("Cannot login without a running browser driver", "ERROR")
            return False
        if not self.login_manager:
            self.login_manager = LoginManager(driver)
        return self.login_manager.login()

    def get_sheets_manager(self, credentials_json=None, credentials_path=None):
        return SheetsManager(
            credentials_json=credentials_json,
            credentials_path=credentials_path
        )

    def close(self):
        self.browser_manager.close()
