"""
Online Mode scraping logic.

This module handles the 'online' scraping mode. It first fetches a list of
currently online users and then scrapes the profile of each user, similar to
the target mode. It reuses the `ProfileScraper` for the individual profile
scraping logic.
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config.config_common import Config
from config.selectors import OnlineUserSelectors
from utils.ui import get_pkt_time, log_msg
from phases.profile.target_mode import run_target_mode, validate_nickname

# ==================== ONLINE USERS PARSER ====================

class OnlineUsersParser:
    """
    Parses the 'Online Users' page to extract a list of nicknames.

    It uses multiple strategies to find nicknames on the page to make the scraper
    more resilient to changes in the website's HTML structure.
    """
    
    def __init__(self, driver):
        """Initializes the parser with the WebDriver instance."""
        self.driver = driver
    
    def get_online_nicknames(self):
        """
        Fetches and extracts all unique nicknames from the online users page.

        Returns:
            list[str]: A sorted list of unique nicknames.
        """
        try:
            log_msg("Fetching online users list...")
            
            self.driver.get(Config.ONLINE_USERS_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, OnlineUserSelectors.PAGE_HEADER))
            )
            
            # Find all nickname elements
            nicknames = set()
            
            # Strategy 1: Find <b><bdi> elements with nicknames
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_1)
                for elem in elements:
                    nick = elem.text.strip()
                    if nick:
                        nicknames.add(nick)
            except Exception as e:
                log_msg(f"Strategy 1 failed: {e}")
            
            # Strategy 2: Find form action URLs containing nicknames
            try:
                forms = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    OnlineUserSelectors.NICKNAME_STRATEGY_2
                )
                
                for form in forms:
                    action = form.get_attribute('action')
                    if action:
                        # Extract nickname from URL
                        # Example: /search/nickname/redirect/Alz/
                        match = re.search(r'/redirect/([^/]+)/?$', action)
                        if match:
                            nick = match.group(1)
                            if nick:
                                nicknames.add(nick)
            except Exception as e:
                log_msg(f"Strategy 2 failed: {e}")
            
            # Strategy 3: Parse from list items
            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_3)
                for item in items:
                    # Find <b> tag inside
                    try:
                        b_tag = item.find_element(By.CSS_SELECTOR, OnlineUserSelectors.NICKNAME_STRATEGY_3_CHILD)
                        nick = b_tag.text.strip()
                        if nick:
                            nicknames.add(nick)
                    except:
                        pass
            except Exception as e:
                log_msg(f"Strategy 3 failed: {e}")
            
            # Convert to sorted list
            result = sorted(list(nicknames))
            log_msg(f"Found {len(result)} online users", "OK")
            
            return result
        
        except TimeoutException:
            log_msg("Timeout loading online users page", "TIMEOUT")
            return []
        
        except Exception as e:
            log_msg(f"Error fetching online users: {e}", "ERROR")
            return []

# ==================== ONLINE MODE RUNNER ====================

def run_online_mode(driver, sheets, max_profiles=0):
    """
    Orchestrates the scraping process for the 'online' mode.

    This function fetches the list of online users and then delegates the scraping
    to the `run_target_mode` function. This ensures that the same, consistent
    scraping and data handling logic is used across all modes.

    Args:
        driver: The Selenium WebDriver instance.
        sheets: An initialized SheetsManager instance.
        max_profiles (int): The maximum number of profiles to process (0 for all).

    Returns:
        dict: A dictionary of statistics from the scraping run.
    """
    log_msg("=== ONLINE MODE STARTED ===")
    
    # Get online users
    parser = OnlineUsersParser(driver)
    nicknames = parser.get_online_nicknames()
    
    if not nicknames:
        log_msg("No online users found")
        return {
            "success": 0, "failed": 0, "new": 0,
            "updated": 0, "unchanged": 0, "logged": 0
        }

    # Log all users to the OnlineLog sheet in a single batch operation
    timestamp = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
    batch_no = get_pkt_time().strftime("%Y%m%d_%H%M")
    sheets.batch_log_online_users(nicknames, timestamp, batch_no)

    # Format nicknames into the target structure for run_target_mode
    targets = [
        {'nickname': nick, 'source': 'Online'}
        for nick in nicknames if validate_nickname(nick)
    ]

    # Delegate the scraping to the centralized target mode runner
    stats = run_target_mode(driver, sheets, max_profiles, targets, run_label="ONLINE")
    
    # Add online-specific stats
    stats['logged'] = len(nicknames)
    
    log_msg("=== ONLINE MODE COMPLETED ===")
    log_msg(
        f"Results: {stats.get('success', 0)} success, {stats.get('failed', 0)} failed, "
        f"{stats.get('logged', 0)} logged"
    )
    
    return stats
