"""
Online Mode Runner — DD-CMS-V3

What this module does:
- Opens the DamaDam online users page
- Collects all visible nicknames using multiple fallback strategies
- Passes them to run_target_mode() (shared scraping pipeline)
- Does NOT update RunList (Online mode has no RunList rows)
- Col 9  (LIST)     → empty string for Online mode
- Col 11 (RUN MODE) → "Online"
"""

import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config.config_common import Config
from config.selectors import OnlineUserSelectors
from utils.ui import log_msg
from phases.profile.target_mode import run_target_mode, validate_nickname


class OnlineUsersParser:
    """Parses the DamaDam online users page and returns a list of nicknames."""

    def __init__(self, driver):
        self.driver = driver

    def get_online_nicknames(self):
        """
        Fetch the online users page and extract unique nicknames.

        Uses three fallback strategies so it stays resilient to site HTML changes.

        Returns:
            list[str]: Sorted list of unique valid nicknames.
        """
        try:
            log_msg("Fetching online users list...")
            self.driver.get(Config.ONLINE_USERS_URL)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, OnlineUserSelectors.PAGE_HEADER))
            )

            nicknames = set()

            # Strategy 1 — <b><bdi> text inside user cards
            try:
                for elem in self.driver.find_elements(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_1):
                    nick = elem.text.strip()
                    if nick:
                        nicknames.add(nick)
            except Exception as e:
                log_msg(f"Online parser strategy 1 failed: {e}", "WARNING")

            # Strategy 2 — form action URLs like /search/nickname/redirect/SomeNick/
            try:
                for form in self.driver.find_elements(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_2):
                    action = form.get_attribute('action') or ""
                    m = re.search(r'/redirect/([^/]+)/?$', action)
                    if m and m.group(1):
                        nicknames.add(m.group(1))
            except Exception as e:
                log_msg(f"Online parser strategy 2 failed: {e}", "WARNING")

            # Strategy 3 — list items containing <b class="clb">
            try:
                for item in self.driver.find_elements(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_3):
                    try:
                        b = item.find_element(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_3_CHILD)
                        nick = b.text.strip()
                        if nick:
                            nicknames.add(nick)
                    except Exception:
                        continue
            except Exception as e:
                log_msg(f"Online parser strategy 3 failed: {e}", "WARNING")

            # Validate all nicknames before returning
            valid = sorted(n for n in nicknames if validate_nickname(n))
            log_msg(f"Found {len(valid)} valid online users", "OK")
            return valid

        except TimeoutException:
            log_msg("Timeout loading online users page", "TIMEOUT")
            return []
        except Exception as e:
            log_msg(f"Error fetching online users: {e}", "ERROR")
            return []


def run_online_mode(driver, sheets, max_profiles=0):
    """
    Orchestrate Online Mode scraping.

    Steps:
      1. Parse online users page → collect nicknames
      2. Build target list with source="Online" (no RunList rows)
      3. Delegate to run_target_mode() with run_label="ONLINE"
         - COL 9  LIST     = "" (empty — no RunList Col F for online)
         - COL 11 RUN MODE = "Online"

    Args:
        driver:       Selenium WebDriver
        sheets:       SheetsManager instance
        max_profiles: 0 = unlimited

    Returns:
        dict of run statistics
    """
    log_msg("=== ONLINE MODE STARTED ===")

    parser    = OnlineUsersParser(driver)
    nicknames = parser.get_online_nicknames()

    if not nicknames:
        log_msg("No online users found — nothing to scrape")
        return {"success": 0, "failed": 0, "new": 0, "updated": 0, "unchanged": 0}

    # Build target list — no 'row' key means RunList will NOT be updated
    targets = [
        {
            'nickname': nick,
            'source':   'Online',
            'tag':      '',       # No RunList Col F value for online mode
            'row':      None,     # No RunList row to update
        }
        for nick in nicknames
    ]

    stats = run_target_mode(
        driver=driver,
        sheets=sheets,
        max_profiles=max_profiles,
        targets=targets,
        run_label="ONLINE",
    )

    log_msg(f"=== ONLINE MODE COMPLETED — "
            f"success={stats.get('success',0)} failed={stats.get('failed',0)} ===")
    return stats
