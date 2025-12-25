"""
Target Mode scraping logic.

This module contains the core components for the 'target' scraping mode. It defines
the ProfileScraper class, which is responsible for extracting detailed information
from an individual user's profile page. It also includes the `run_target_mode`
function, which orchestrates the process of fetching a list of target users from
the 'RunList' sheet and scraping each one.
"""

import time
import re
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config.config_common import Config
from config.selectors import ProfileSelectors
from utils.ui import get_pkt_time, log_msg
from utils.url_builder import get_profile_url, get_public_profile_url

# ==================== HELPER FUNCTIONS ====================

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = str(text).strip().replace('\xa0', ' ').replace('\n', ' ')
    return re.sub(r"\s+", " ", text).strip()

def normalize_post_datetime(raw_date):
    """Normalize any date string to standardized format: dd-mmm-yy hh:mm a
    
    Centralized date normalization layer for all scrapers (profiles, posts, boards).
    
    Handles multiple input formats:
    - Relative times: "5 mins ago", "2 hours ago", "1 day ago", "Yesterday"
    - Absolute dates: "22-Dec-25 04:53 PM", "22-Dec-25 16:53", "22-12-2025 16:53"
    - Date only: "22-Dec-25" (time defaults to current time)
    - Time only: "04:53 PM" (date defaults to today)
    - None/empty: Returns current time
    
    Args:
        raw_date (str | None): Raw date string from page source
        
    Returns:
        str: Standardized datetime string in format "dd-mmm-yy hh:mm a" (lowercase)
             Example: "22-dec-25 04:53 pm"
    
    Note: Output format matches existing project standard for consistency.
    """
    text = raw_date  # Keep original variable name for existing logic
    
    if not text or not str(text).strip():
        return ""
    
    text = str(text).strip().lower()
    now = get_pkt_time()
    
    # Handle empty or invalid input
    if not text or text in ['-', 'n/a', 'none', 'null']:
        return now.strftime("%d-%b-%y %I:%M %p").lower()
    
    # Clean and standardize the input text
    t = text.replace('\n', ' ').replace('\t', ' ').replace('\r', '').strip()
    t = re.sub(r'\s+', ' ', t)  # Normalize multiple spaces
    
    # Handle "X ago" format
    ago_match = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", t)
    if ago_match:
        amount = int(ago_match.group(1))
        unit = ago_match.group(2)
        
        # Map units to seconds
        seconds_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31536000
        }
        
        if unit in seconds_map:
            dt = now - timedelta(seconds=amount * seconds_map[unit])
            return dt.strftime("%d-%b-%y %I:%M %p").lower()
    
    # Try parsing as absolute date
    date_formats = [
        # Full date and time formats
        "%d-%b-%y %I:%M %p",  # 22-Dec-25 04:53 PM
        "%d-%b-%y %H:%M",     # 22-Dec-25 16:53
        "%d-%m-%y %H:%M",     # 22-12-25 16:53
        "%d-%m-%Y %H:%M",     # 22-12-2025 16:53
        "%d-%b-%y %I:%M%p",   # 22-Dec-25 04:53PM
        "%d-%b-%y %H:%M:%S",  # 22-Dec-25 16:53:00
        "%Y-%m-%d %H:%M:%S",  # 2025-12-22 16:53:00
        # Date only formats
        "%d-%b-%y",           # 22-Dec-25
        "%d-%m-%y",           # 22-12-25
        "%Y-%m-%d",           # 2025-12-22
        # Time only formats (assume today)
        "%I:%M %p",           # 04:53 PM
        "%H:%M"               # 16:53
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(t, fmt)
            
            # If time not in format, use current time
            if ':' not in fmt:
                dt = dt.replace(
                    hour=now.hour,
                    minute=now.minute,
                    second=0,
                    microsecond=0
                )
            # If date not in format, use today's date
            elif '%d' not in fmt or '%m' not in fmt or ('%y' not in fmt and '%Y' not in fmt):
                dt = dt.replace(
                    year=now.year,
                    month=now.month,
                    day=now.day
                )
                
            # Handle 2-digit years
            if dt.year > now.year + 1:  # If year is in the future, assume it's 1900s
                dt = dt.replace(year=dt.year - 100)
                
            return dt.strftime("%d-%b-%y %I:%M %p").lower()
            
        except ValueError:
            continue
    
    # If no format matches, log warning and return current time
    log_msg(f"Could not parse date: '{text}'. Using current time.", "WARNING")
    return now.strftime("%d-%b-%y %I:%M %p").lower()

def detect_suspension(page_source):
    """Detect account suspension"""
    if not page_source:
        return None
    
    lower = page_source.lower()
    for indicator in Config.SUSPENSION_INDICATORS:
        if indicator in lower:
            return indicator
    return None

def sanitize_nickname_for_url(nickname):
    """Sanitize and validate nickname for URL usage
    
    Rejects:
    - Empty/None values
    - Whitespace characters
    - Length > 50 chars
    - Invalid characters (non-word chars except .-_)
    
    Returns:
        str: Cleaned nickname safe for URL usage
        None: Invalid nickname
    """
    if not nickname or not isinstance(nickname, str):
        return None
    
    # Strip leading/trailing whitespace
    nickname = nickname.strip()
    
    # Reject if empty after strip
    if not nickname:
        return None
    
    # Reject if contains any whitespace
    if ' ' in nickname or '\t' in nickname or '\n' in nickname or '\r' in nickname:
        return None
    
    # Reject if too long
    if len(nickname) > 50:
        return None
    
    # Validate format: alphanumeric, dots, hyphens, underscores only
    if not re.match(r'^[\w\.\-_]+$', nickname):
        return None
    
    return nickname

def validate_nickname(nickname):
    """Validate nickname format and return cleaned version
    
    Wrapper around sanitize_nickname_for_url for backwards compatibility
    """
    return sanitize_nickname_for_url(nickname)

# ==================== PROFILE SCRAPER ====================

class ProfileScraper:
    """
    A dedicated scraper for extracting data from a single user profile page.

    This class encapsulates all the logic for navigating to a user's profile,
    parsing the HTML, and extracting various data points like user info, mehfil
    details, friend status, and post information. It is designed to be resilient
    to minor page layout changes by using multiple selectors for key data points.
    """
    
    def __init__(self, driver):
        """Initializes the scraper with the WebDriver instance."""
        self.driver = driver
    
    def _extract_mehfil_details(self, page_source):
        """Extract mehfil details from profile page"""
        mehfil_data = {
            'MEH NAME': [],
            'MEH TYPE': [],
            'MEH LINK': [],
            'MEH DATE': []
        }
        
        try:
            # Find all mehfil entries
            mehfil_entries = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ProfileSelectors.MEHFIL_ENTRIES
            )
            
            for entry in mehfil_entries:
                try:
                    # Extract mehfil name
                    name_elem = entry.find_element(By.CSS_SELECTOR, ProfileSelectors.MEHFIL_NAME)
                    mehfil_data['MEH NAME'].append(clean_text(name_elem.text))
                    
                    # Extract mehfil types
                    type_elems = entry.find_elements(
                        By.CSS_SELECTOR, 
                        ProfileSelectors.MEHFIL_TYPE
                    )
                    types = [clean_text(t.text) for t in type_elems]
                    mehfil_data['MEH TYPE'].append(", ".join(types))
                    
                    # Extract mehfil link
                    link = entry.get_attribute('href')
                    mehfil_data['MEH LINK'].append(link)
                    
                    # Extract join date
                    date_elem = entry.find_element(
                        By.CSS_SELECTOR, 
                        ProfileSelectors.MEHFIL_DATE
                    )
                    date_text = clean_text(date_elem.text)
                    if 'since' in date_text.lower():
                        date_text = date_text.split('since')[-1].strip()
                    mehfil_data['MEH DATE'].append(normalize_post_datetime(date_text))
                    
                except Exception as e:
                    log_msg(f"Error extracting mehfil entry: {e}", "WARNING")
                    continue
                    
        except Exception as e:
            log_msg(f"Error finding mehfil section: {e}", "WARNING")
            
        return mehfil_data
        
    def _extract_friend_status(self, page_source):
        """Extract friend status from follow button"""
        try:
            button = self.driver.find_element(By.XPATH, ProfileSelectors.FRIEND_STATUS_BUTTON)
            label = button.text.strip().upper()
            if "UNFOLLOW" in label:
                return "Yes"
            if "FOLLOW" in label:
                return "No"
        except Exception:
            pass

        if 'action="/follow/remove/' in page_source:
            return "Yes"
        if 'action="/follow/add/' in page_source:
            return "No"
        return ""
    
    def _extract_rank(self, page_source):
        """Extract rank label and star image URL"""
        try:
            match = re.search(r'src=\"(/static/img/stars/[^\"]+)\"', page_source)
            if not match:
                return "", ""

            rel_path = match.group(1)
            image_url = rel_path if rel_path.startswith('http') else f"https://damadam.pk{rel_path}"

            lower = rel_path.lower()
            if "red" in lower:
                label = "Red Star"
            elif "gold" in lower:
                label = "Gold Star"
            elif "silver" in lower:
                label = "Silver Star"
            else:
                label = Path(rel_path).stem.replace('-', ' ').title()

            return label, image_url

        except Exception as e:
            log_msg(f"Rank extraction failed: {e}", "WARNING")
            return "", ""
    
    def _extract_user_id(self, page_source):
        """Extract user ID from hidden input field"""
        try:
            # Look for <input type="hidden" name="tid" value="3405367">
            match = re.search(r'name=[\"\']tid[\"\']\s+value=[\"\'](\d+)[\"\']', page_source)
            if match:
                return match.group(1)
                
            # Alternative: Look for it in follow form
            match = re.search(r'name=[\"\']pl[\"\']\s+value=[\"\']\*\*\*\d+\*(\d+)\*', page_source)
            if match:
                return match.group(1)
                
        except Exception as e:
            log_msg(f"Error extracting user ID: {e}", "WARNING")
            
        return ""
    
    def _extract_stats(self):
        """Extracts follower and post counts."""
        stats = {'FOLLOWERS': '', 'POSTS': ''}
        try:
            followers_elem = self.driver.find_element(By.XPATH, ProfileSelectors.FOLLOWERS_COUNT)
            stats['FOLLOWERS'] = clean_text(followers_elem.text)
        except Exception:
            pass  # Keep default value if not found

        try:
            posts_elem = self.driver.find_element(By.XPATH, ProfileSelectors.POSTS_COUNT)
            stats['POSTS'] = clean_text(posts_elem.text)
        except Exception:
            pass  # Keep default value if not found

        return stats

    def _extract_last_post(self):
        """Extracts the last post text and time."""
        last_post = {'LAST POST': '', 'LAST POST TIME': ''}
        try:
            post_text_elem = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TEXT)
            last_post['LAST POST'] = clean_text(post_text_elem.text)
        except Exception:
            pass

        try:
            post_time_elem = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TIME)
            last_post['LAST POST TIME'] = normalize_post_datetime(post_time_elem.text)
        except Exception:
            pass

        return last_post

    def _extract_profile_image(self):
        """Extracts the profile image URL."""
        try:
            image_elem = self.driver.find_element(By.XPATH, ProfileSelectors.PROFILE_IMAGE)
            image_url = image_elem.get_attribute('src')
            return image_url if image_url and image_url.startswith('http') else f"https://damadam.pk{image_url}"
        except Exception:
            return ""

    def scrape_profile(self, nickname, source="Target"):
        """
        Scrapes a complete user profile.

        Navigates to the user's profile URL and systematically extracts all
        available information, handling various states like suspended or
        unverified accounts. It returns a structured dictionary of the data.

        Args:
            nickname (str): The nickname of the user to scrape.
            source (str): The source from which this scrape was initiated (e.g., 'Target').

        Returns:
            dict or None: A dictionary containing the scraped profile data, or None
                          if a critical error occurs (e.g., page timeout).
        """
        # Sanitize nickname for URL usage
        clean_nickname = sanitize_nickname_for_url(nickname)
        if not clean_nickname:
            log_msg(f"Invalid nickname: {nickname}", "ERROR")
            return None
        
        url = get_profile_url(clean_nickname)
        
        try:
            log_msg(f"Scraping: {nickname}", "SCRAPING")
            
            self.driver.get(url)
            WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((By.XPATH, ProfileSelectors.NICKNAME_HEADER))
            )

            page_source = self.driver.page_source
            now = get_pkt_time()
            
            # Initialize profile data with default values
            data = {col: Config.DEFAULT_VALUES.get(col, "") for col in Config.COLUMN_ORDER}
            
            # Ensure nickname is set in the data
            data["NICK NAME"] = clean_nickname
            data["SOURCE"] = source
            data["DATETIME SCRAP"] = now.strftime("%d-%b-%y %I:%M %p")
            
            # Extract additional data
            mehfil_data = self._extract_mehfil_details(page_source)
            friend_status = self._extract_friend_status(page_source)
            _, rank_image = self._extract_rank(page_source)
            user_id = self._extract_user_id(page_source)
            stats_data = self._extract_stats()
            last_post_data = self._extract_last_post()
            image_url = self._extract_profile_image()

            # Update data with all fields
            data.update({
                "ID": user_id,
                "PROFILE LINK": url.rstrip('/'),
                "POST URL": get_public_profile_url(clean_nickname),
                "FRIEND": friend_status,
                "FRD": friend_status,
                "RURL": rank_image,
                "FOLLOWERS": stats_data['FOLLOWERS'],
                "POSTS": stats_data['POSTS'],
                "LAST POST": last_post_data['LAST POST'],
                "LAST POST TIME": last_post_data['LAST POST TIME'],
                "IMAGE": image_url,
                "MEH NAME": "\n".join(mehfil_data['MEH NAME']) if mehfil_data['MEH NAME'] else "",
                "MEH TYPE": "\n".join(mehfil_data['MEH TYPE']) if mehfil_data['MEH TYPE'] else "",
                "MEH LINK": "\n".join(mehfil_data['MEH LINK']) if mehfil_data['MEH LINK'] else "",
                "MEH DATE": "\n".join(mehfil_data['MEH DATE']) if mehfil_data['MEH DATE'] else ""
            })
            
            # Check suspension
            suspend_reason = detect_suspension(page_source)
            if suspend_reason:
                data['STATUS'] = 'Banned'
                data['INTRO'] = "Account Suspended"[:250]
                data['__skip_reason'] = 'Account Suspended'
                return data
            
            if 'account suspended' in page_source.lower():
                data['STATUS'] = 'Banned'
                data['__skip_reason'] = 'Account Suspended'
                return data
            
            # Check unverified
            if (
                re.search(r">\s*unverified\s*user\s*<", page_source, re.IGNORECASE) or
                'background:tomato' in page_source or
                'style="background:tomato"' in page_source.lower()
            ):
                data['STATUS'] = 'Unverified'
                data['__skip_reason'] = 'Unverified user'
            else:
                data['STATUS'] = 'Verified'
            
            # Extract intro / bio text
            intro_xpaths = [
                ProfileSelectors.INTRO_TEXT_B,
                ProfileSelectors.INTRO_TEXT_SPAN
            ]
            intro_text = ""
            for xp in intro_xpaths:
                try:
                    intro_elem = self.driver.find_element(By.XPATH, xp)
                    intro_text = clean_text(intro_elem.text.strip())
                    if intro_text:
                        break
                except:
                    continue
            
            data['INTRO'] = intro_text

            # Extract profile fields using multiple selector patterns
            field_selectors = [
                # Pattern 1: <b>Label:</b> <span>Value</span>
                (ProfileSelectors.DETAIL_PATTERN_1, 
                 lambda e: e.text.strip() if e else None),
                
                # Pattern 2: <div><b>Label:</b> Value</div>
                (ProfileSelectors.DETAIL_PATTERN_2,
                 lambda e: e.text.split(':', 1)[1].strip() if e and ':' in e.text else None),
                
                # Pattern 3: <span class="label">Label:</span> <span>Value</span>
                (ProfileSelectors.DETAIL_PATTERN_3,
                 lambda e: e.text.strip() if e else None)
            ]
            
            # Define fields to extract with their processing logic
            fields = [
                ('City', 'CITY', lambda x: clean_text(x) if x else ''),
                ('Gender', 'GENDER', lambda x: 'Female' if x and 'female' in x.lower() 
                                             else 'Male' if x and 'male' in x.lower() 
                                             else ''),
                ('Married', 'MARRIED', 
                 lambda x: 'Yes' if x and x.lower() in {'yes', 'married'} 
                              else 'No' if x and x.lower() in {'no', 'single', 'unmarried'}
                              else ''),
                ('Age', 'AGE', lambda x: clean_text(x) if x else ''),
                ('Joined', 'JOINED', lambda x: normalize_post_datetime(x) if x else '')
            ]
            
            # Try each field with all selector patterns
            for label, key, process_func in fields:
                value = None
                for selector_pattern, extract_func in field_selectors:
                    try:
                        xpath = selector_pattern.format(label)
                        elem = self.driver.find_element(By.XPATH, xpath)
                        raw_value = extract_func(elem)
                        if raw_value:
                            value = process_func(raw_value)
                            break
                    except:
                        continue
                
                if value:
                    data[key] = value
            
            return data
        
        except TimeoutException:
            log_msg(f"Timeout loading profile: {nickname}", "TIMEOUT")
            return None
        
        except Exception as e:
            log_msg(f"Error scraping {nickname}: {e}", "ERROR")
            return None

# ==================== TARGET MODE RUNNER ====================

def run_target_mode(driver, sheets, max_profiles=0, targets=None):
    """
    Orchestrates the scraping process for the 'target' mode.

    This function retrieves a list of pending targets from the 'RunList' sheet,
    iterates through them, and uses the ProfileScraper to scrape each one. It
    updates the sheet with the status of each target ('Done' or 'Error') and
    compiles statistics on the overall run.

    Args:
        driver: The Selenium WebDriver instance.
        sheets: An initialized SheetsManager instance.
        max_profiles (int): The maximum number of profiles to process (0 for all).

    Returns:
        dict: A dictionary of statistics from the scraping run.
    """
    log_msg("=== TARGET MODE STARTED ===")
    
    stats = {
        "success": 0,
        "failed": 0,
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "processed": 0,
        "invalid_nicknames": 0,
        "total_found": 0
    }

    # Get pending targets if not provided
    if targets is None:
        try:
            targets = sheets.get_pending_targets()
        except Exception as e:
            log_msg(f"Error getting pending targets: {e}", "ERROR")
            return stats
    
    if not targets:
        log_msg("No pending targets found")
        return stats
    
    # Limit targets if specified
    if max_profiles > 0:
        targets = targets[:max_profiles]

    stats["total_found"] = len(targets)
    log_msg(f"Processing {len(targets)} target(s)...")

    scraper = ProfileScraper(driver)

    for i, target in enumerate(targets, 1):
        try:
            # Validate and clean nickname
            nickname = validate_nickname(target.get('nickname', '').strip())
            if not nickname:
                log_msg(f"Skipping invalid nickname: {target.get('nickname', '')}", "WARNING")
                stats["invalid_nicknames"] += 1
                stats["skipped"] += 1
                continue
                
            row = target.get('row')
                
            log_msg(f"Processing {i}/{len(targets)}: {nickname}")
            
            # Scrape profile
            profile_data = scraper.scrape_profile(nickname, source="Target")
            stats["processed"] += 1
            
            if not profile_data:
                log_msg(f"Failed to scrape {nickname}")
                stats["failed"] += 1
                if row:
                    sheets.update_target_status(row, "Error", "Failed to scrape profile")
                time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))
                continue
            
            # Check for skip reason
            skip_reason = profile_data.get('__skip_reason')
            if skip_reason:
                log_msg(f"Skipping {nickname}: {skip_reason}")
                stats["skipped"] += 1
                
                # Still write to sheet for record keeping
                sheets.write_profile(profile_data)
                if row:
                    sheets.update_target_status(row, "Error", skip_reason)
                time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))
                continue
            
            # Write successful profile
            result = sheets.write_profile(profile_data)
            write_status = result.get("status", "error")
            
            if write_status in {"new", "updated", "unchanged"}:
                stats["success"] += 1
                stats[write_status] += 1
                
                remarks = f"New profile" if write_status == "new" else f"Profile {write_status}"
                if row:
                    sheets.update_target_status(row, "Done", remarks)
                log_msg(f"{nickname}: {write_status}", "OK")
            else:
                log_msg(f"{nickname}: write failed")
                stats["failed"] += 1
                if row:
                    sheets.update_target_status(row, "Error", "Failed to write profile")
            
        except Exception as e:
            log_msg(f"Error processing {nickname}: {str(e)}", "ERROR")
            stats["failed"] += 1
            stats["processed"] += 1
            if row:
                try:
                    sheets.update_target_status(row, "Error", f"Processing error: {str(e)[:100]}")
                except:
                    log_msg("Failed to update target status", "ERROR")
        
        # Add delay between requests
        if i < len(targets):
            time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))
    
    log_msg("=== TARGET MODE COMPLETED ===")
    log_msg(
        f"Results: {stats['success']} success, {stats['failed']} failed, "
        f"{stats['skipped']} skipped"
    )
            
    return stats
