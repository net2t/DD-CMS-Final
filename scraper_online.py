"""
Online Mode Scraper - Scrapes users from online list
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import Config
from browser import get_pkt_time, log_msg
from scraper_target import ProfileScraper

# ==================== ONLINE USERS PARSER ====================

class OnlineUsersParser:
    """Parses the online users page"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def get_online_nicknames(self):
        """Extract all online user nicknames"""
        try:
            log_msg("Fetching online users list...")
            
            self.driver.get(Config.ONLINE_USERS_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.clb.cxl.lsp"))
            )
            
            # Find all nickname elements
            nicknames = set()
            
            # Strategy 1: Find <b><bdi> elements with nicknames
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, "b.clb bdi")
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
                    "form[action*='/search/nickname/redirect/']"
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
                items = self.driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp")
                for item in items:
                    # Find <b> tag inside
                    try:
                        b_tag = item.find_element(By.CSS_SELECTOR, "b.clb")
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

def run_online_mode(driver, sheets):
    """Run scraper in Online mode"""
    log_msg("=== ONLINE MODE STARTED ===")
    
    # Get online users
    parser = OnlineUsersParser(driver)
    nicknames = parser.get_online_nicknames()
    
    if not nicknames:
        log_msg("No online users found")
        return {
            "success": 0,
            "failed": 0,
            "new": 0,
            "updated": 0,
            "unchanged": 0,
            "logged": 0
        }
    
    log_msg(f"Processing {len(nicknames)} online users...")
    
    scraper = ProfileScraper(driver)
    stats = {
        "success": 0,
        "failed": 0,
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "logged": 0
    }
    
    timestamp = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
    
    for i, nickname in enumerate(nicknames, 1):
        log_msg(f"[{i}/{len(nicknames)}] Processing: {nickname}")
        
        try:
            # Log to OnlineLog sheet
            sheets.log_online_user(nickname, timestamp)
            stats['logged'] += 1
            
            # Scrape profile
            profile = scraper.scrape_profile(nickname, source="Online")
            
            if not profile:
                log_msg(f"Failed to scrape {nickname}")
                stats['failed'] += 1
                time.sleep(Config.MIN_DELAY)
                continue
            
            # Check skip reason
            skip_reason = profile.get('__skip_reason')
            if skip_reason:
                log_msg(f"Skipping {nickname}: {skip_reason}")
                sheets.write_profile(profile)
                stats['failed'] += 1
            else:
                # Write profile
                result = sheets.write_profile(profile)
                status = result.get("status", "error")
                
                if status in {"new", "updated", "unchanged"}:
                    stats['success'] += 1
                    stats[status] += 1
                    log_msg(f"{nickname}: {status}", "OK")
                else:
                    log_msg(f"{nickname}: write failed")
                    stats['failed'] += 1
        
        except Exception as e:
            log_msg(f"Error processing {nickname}: {e}", "ERROR")
            stats['failed'] += 1
        
        # Delay between profiles
        time.sleep(Config.MIN_DELAY)
    
    log_msg("=== ONLINE MODE COMPLETED ===")
    log_msg(
        f"Results: {stats['success']} success, {stats['failed']} failed, "
        f"{stats['logged']} logged"
    )
    
    return stats
