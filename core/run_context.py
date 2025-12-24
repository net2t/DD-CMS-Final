"""
RunContext holds the shared state for a single scraper run, including the browser
instance, login status, and access to the SheetsManager.
"""

from typing import Optional

from .browser_manager import BrowserManager, log_msg
from .login_manager import LoginManager
from utils.sheets_manager import SheetsManager


class RunContext:
    """
    Manages the shared state for a single scraper run.

    This class is responsible for initializing and holding the browser driver,
    handling the login process, and providing access to the SheetsManager.
    It ensures that different phases of the scraping process can share the same
    browser session and resources without having to pass them around manually.
    """

    def __init__(self):
        """Initializes the context, setting up managers but not starting the browser."""
        self.browser_manager = BrowserManager()
        self.driver = None
        self.login_manager: Optional[LoginManager] = None

    def start_browser(self):
        """
        Starts the browser instance if it's not already running.

        Returns:
            The Selenium WebDriver instance, or None if startup fails.
        """
        if not self.driver:
            self.driver = self.browser_manager.start()
        return self.driver

    def login(self):
        """
        Ensures the browser is started and performs the login sequence.

        Returns:
            bool: True if login is successful, False otherwise.
        """
        driver = self.start_browser()
        if not driver:
            log_msg("Cannot login without a running browser driver", "ERROR")
            return False

        if not self.login_manager:
            self.login_manager = LoginManager(driver)

        return self.login_manager.login()

    def get_sheets_manager(self, credentials_json=None, credentials_path=None):
        """
        Creates and returns a new SheetsManager instance.

        This allows different phases to use separate credentials if needed,
        while still being managed by the central run context.

        Args:
            credentials_json (str, optional): Raw JSON string for service account.
            credentials_path (str, optional): Path to the service account JSON file.

        Returns:
            SheetsManager: An initialized SheetsManager instance.
        """
        return SheetsManager(
            credentials_json=credentials_json,
            credentials_path=credentials_path
        )

    def close(self):
        """Closes the browser and cleans up resources."""
        self.browser_manager.close()
