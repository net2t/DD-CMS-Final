"""
Phase 1 (Profiles) - Target Mode + Core Profile Scraper

This module contains:
- ProfileScraper: scrapes ONE profile page and returns a full profile dictionary
- run_target_mode: loops profiles (from RunList sheet or Online mode) and writes to Sheets

Important contract:
- scrape_profile() returns a full dict (even if banned/unverified) or None only on hard failure
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
from utils.ui import get_pkt_time, log_msg, log_progress
from utils.url_builder import get_profile_url, get_public_profile_url

# ==================== HELPER FUNCTIONS ====================

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    text = str(text).strip().replace('\xa0', ' ').replace('\n', ' ')
    return re.sub(r"\s+", " ", text).strip()

def normalize_post_url(url):
    if not url:
        return ""
    url = clean_text(url)
    if not url.startswith("http"):
        return url

    m = re.match(r"^(https?://[^/]+)(/.*)$", url)
    if not m:
        return url

    base, path = m.group(1), m.group(2)
    path = path.split('#', 1)[0].split('?', 1)[0]

    m2 = re.match(r"^(/comments/(?:text|image)/\d+)", path)
    if m2:
        return f"{base}{m2.group(1)}"

    m3 = re.match(r"^/content/(\d+)", path)
    if m3:
        return f"{base}/comments/image/{m3.group(1)}"

    return f"{base}{path.rstrip('/')}"

def normalize_date_only(raw_date):
    """Normalize any date string to standardized format: dd-mmm-yy"""
    if not raw_date:
        return ""
    dt_string = normalize_post_datetime(raw_date)
    if not dt_string:
        return ""
    try:
        # normalize_post_datetime returns 'dd-mon-yy hh:mm am/pm'
        # We just need the date part.
        date_part = dt_string.split(' ')[0]
        # Validate it's a date
        datetime.strptime(date_part, "%d-%b-%y")
        return date_part
    except (ValueError, IndexError):
        # Fallback if the format from normalize_post_datetime is unexpected
        log_msg(f"Could not extract date part from '{dt_string}'.", "WARNING")
        return ""

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
    if t.startswith('-'):
        t = t.lstrip('-').strip()
    t = re.sub(r'\s+', ' ', t)  # Normalize multiple spaces
    
    # Handle "X ago" format
    if "ago" in t:
        delta = timedelta()
        # Regex to find all number-unit pairs
        parts = re.findall(r'(\d+)\s*(year|yr|month|mon|week|wk|day|hour|hr|minute|min|second|sec)s?', t)
        
        if parts:
            for amount, unit in parts:
                amount = int(amount)
                if unit.startswith('year') or unit.startswith('yr'):
                    # Approximate days for year, better than fixed seconds
                    delta += timedelta(days=amount * 365)
                elif unit.startswith('month') or unit.startswith('mon'):
                    # Approximate days for month
                    delta += timedelta(days=amount * 30)
                elif unit.startswith('week') or unit.startswith('wk'):
                    delta += timedelta(weeks=amount)
                elif unit.startswith('day'):
                    delta += timedelta(days=amount)
                elif unit.startswith('hour') or unit.startswith('hr'):
                    delta += timedelta(hours=amount)
                elif unit.startswith('minute') or unit.startswith('min'):
                    delta += timedelta(minutes=amount)
                elif unit.startswith('second') or unit.startswith('sec'):
                    delta += timedelta(seconds=amount)
            
            dt = now - delta
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


def detect_unverified(driver, page_source):
    """Detect unverified profiles using a strict banner check.

    NOTE: We intentionally avoid checking only page_source text because the phrase
    "unverified user" can appear in unrelated places and cause false positives.
    """
    if not driver:
        return False

    try:
        # Known banner (tomato background) with visible text "UNVERIFIED USER".
        # Example (from user notes):
        # <div class="cs sp" style="...background:tomato...">UNVERIFIED USER</div>
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'UNVERIFIED USER') and contains(translate(@style, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'background:tomato')]"
        )
        for el in elems:
            try:
                if el.is_displayed():
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


def detect_banned(page_source):
    """Detect banned/suspended profiles using known page tattoos."""
    if not page_source:
        return False
    lower = page_source.lower()
    if "account suspended" in lower:
        return True
    if "banned!" in lower:
        return True
    if "forever banned" in lower:
        return True
    if "/website-rules/" in lower:
        return True
    return False

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
    
    # Strip whitespace only; nickname must remain unchanged
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
    
    # Allow most special characters but still prevent potential security issues
    # Disallowed: < > " ' & | ; ` \ ( ) [ ] { } \t \n \r
    if re.search(r'[<>"\'&|;`\\()\[\]{}[\t\n\r]]', nickname):
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
                    mehfil_data['MEH DATE'].append(normalize_date_only(date_text))
                    
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
    
    def _extract_stats(self, page_source):
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

        if not stats['POSTS']:
            try:
                posts_elem = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(., 'POSTS') or contains(., 'Posts')]//div[1]"
                )
                stats['POSTS'] = clean_text(posts_elem.text)
            except Exception:
                pass

        if not stats['POSTS']:
            try:
                posts_elem = self.driver.find_element(
                    By.XPATH,
                    "//a[contains(@href, '/profile/public/') and (contains(., 'POSTS') or contains(., 'Posts'))]//div[1]"
                )
                stats['POSTS'] = clean_text(posts_elem.text)
            except Exception:
                pass

        if not stats['FOLLOWERS']:
            follower_patterns = [
                r'([\d,\.]+)\s+verified\s+followers',
                r'([\d,\.]+)\s+unverified\s+followers',
                r'([\d,\.]+)\s+followers'
            ]
            stats['FOLLOWERS'] = self._match_stat(page_source, follower_patterns)
        if not stats['POSTS']:
            post_patterns = [
                r'([\d,\.]+)\s+posts?'
            ]
            stats['POSTS'] = self._match_stat(page_source, post_patterns)

        return stats

    def _extract_last_post(self, nickname, page_source, posts_count=None):
        """Extracts the last post text and time."""
        last_post = {'LAST POST': '', 'LAST POST TIME': ''}
        try:
            post_text_elem = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TEXT)
            href = post_text_elem.get_attribute('href')
            if href:
                last_post['LAST POST'] = normalize_post_url(href)
        except Exception:
            pass

        try:
            post_time_elem = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TIME)
            last_post['LAST POST TIME'] = normalize_post_datetime(post_time_elem.text)
        except Exception:
            pass

        if not last_post['LAST POST']:
            post_patterns = [
                r'<div[^>]+class="[^"]*pst[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>',
                r'Last\s+post[:\s]+([^<\n\r]+)'
            ]
            match = self._match_stat(page_source, post_patterns)
            if match:
                last_post['LAST POST'] = match

        if not last_post['LAST POST TIME']:
            time_patterns = [
                r'<div[^>]+class="[^"]*pst[^"]*"[^>]*>.*?<span[^>]*class="[^"]*(gry|sp)[^"]*"[^>]*>([^<]+)</span>',
                r'<span[^>]+class="[^"]*gry[^"]*"[^>]*>([^<]+ ago)</span>'
            ]
            match = self._match_stat(page_source, time_patterns)
            if match:
                last_post['LAST POST TIME'] = normalize_post_datetime(match)

        # If posts are confirmed zero, do not waste time opening public profile page.
        if posts_count == 0:
            return last_post

        # SPEED FLAG: Only open public page if enabled in config (default: off)
        if (not last_post['LAST POST'] or not last_post['LAST POST TIME']) and nickname and Config.LAST_POST_FETCH_PUBLIC_PAGE:
            private_url = self.driver.current_url
            public_url = get_public_profile_url(nickname)
            try:
                self.driver.get(public_url)
                WebDriverWait(self.driver, Config.LAST_POST_PUBLIC_PAGE_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
                )

                try:
                    first_post = self.driver.find_element(By.CSS_SELECTOR, "article.mbl.bas-sh")
                except Exception:
                    try:
                        first_post = self.driver.find_element(By.CSS_SELECTOR, "article")
                    except Exception:
                        first_post = None

                if not first_post:
                    return last_post

                try:
                    url_selectors = [
                        "a[href*='/content/']",
                        "a[href*='/comments/text/']",
                        "a[href*='/comments/image/']"
                    ]
                    for selector in url_selectors:
                        try:
                            link = first_post.find_element(By.CSS_SELECTOR, selector)
                            href = link.get_attribute('href')
                            if href:
                                last_post['LAST POST'] = normalize_post_url(href)
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

                raw_time = ""
                try:
                    time_elem = first_post.find_element(By.CSS_SELECTOR, "time.sp.cxs.cgy")
                    raw_time = clean_text(time_elem.text)
                except Exception:
                    pass

                if not raw_time:
                    try:
                        time_elem = first_post.find_element(By.CSS_SELECTOR, "time")
                        raw_time = clean_text(time_elem.text)
                    except Exception:
                        pass

                if not raw_time:
                    try:
                        time_elem = first_post.find_element(By.CSS_SELECTOR, ".gry, .sp")
                        raw_time = clean_text(time_elem.text)
                    except Exception:
                        pass

                if raw_time:
                    last_post['LAST POST TIME'] = normalize_post_datetime(raw_time)

            except Exception:
                log_msg(f"Public last post scrape failed for {nickname}", "WARNING")
                pass
            finally:
                try:
                    self.driver.get(private_url)
                    WebDriverWait(self.driver, Config.LAST_POST_PUBLIC_PAGE_TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, ProfileSelectors.NICKNAME_HEADER))
                    )
                except Exception:
                    pass

        return last_post

    def _extract_profile_image(self, page_source):
        """Extracts the profile image URL."""
        try:
            try:
                image_elem = self.driver.find_element(By.CSS_SELECTOR, ProfileSelectors.PROFILE_IMAGE_CLOUDFRONT)
                image_url = image_elem.get_attribute('src')
                if image_url and image_url.startswith('http'):
                    return image_url
            except Exception:
                pass

            image_elem = self.driver.find_element(By.XPATH, ProfileSelectors.PROFILE_IMAGE)
            image_url = image_elem.get_attribute('src')
            if image_url and image_url.startswith('http'):
                return image_url
            if image_url:
                return f"https://damadam.pk{image_url}"
        except Exception:
            pass

        # Prefer actual avatar images if present in HTML (cloudfront avatar-imgs)
        if page_source:
            m = re.search(
                r"<img[^>]+src=['\"](https?://[^'\"]+avatar-imgs/[^'\"]+)['\"]",
                page_source,
                re.IGNORECASE
            )
            if m:
                return m.group(1)

        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', page_source, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Ignore placeholder og image
            if 'og_image.png' in url:
                return ""
            return url if url.startswith('http') else f"https://damadam.pk{url}"

        # Last-resort: any non-placeholder image
        if page_source:
            m = re.search(r"<img[^>]+src=['\"]([^'\"]+)['\"]", page_source, re.IGNORECASE)
            if m:
                url = m.group(1)
                if url and 'og_image.png' not in url:
                    return url if url.startswith('http') else f"https://damadam.pk{url}"

        return ""

    def _match_stat(self, text, patterns):
        if not text:
            return ""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                if val:
                    return clean_text(val)
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
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, ProfileSelectors.NICKNAME_HEADER))
            )

            page_source = self.driver.page_source
            now = get_pkt_time()
            
            # Initialize profile data with default values
            data = {col: Config.DEFAULT_VALUES.get(col, "") for col in Config.COLUMN_ORDER}
            
            # Ensure nickname is set in the data
            data["NICK NAME"] = clean_nickname
            data["SKIP/DEL"] = source
            data["DATETIME SCRAP"] = now.strftime("%d-%b-%y %I:%M %p")

            suspend_reason = detect_suspension(page_source)
            if suspend_reason or detect_banned(page_source):
                data['STATUS'] = 'Banned'
                data['__skip_reason'] = 'Account Suspended'
                return data

            if detect_unverified(self.driver, page_source):
                data['STATUS'] = 'Unverified'
                data['__skip_reason'] = 'Unverified user'
                return data
            
            # Extract additional data
            mehfil_data = self._extract_mehfil_details(page_source)
            friend_status = self._extract_friend_status(page_source)
            _, rank_image = self._extract_rank(page_source)
            user_id = self._extract_user_id(page_source)
            stats_data = self._extract_stats(page_source)

            posts_count = None
            try:
                posts_raw = str(stats_data.get('POSTS', '') or '')
                posts_digits = re.sub(r"\D+", "", posts_raw)
                if posts_digits == "0":
                    posts_count = 0
                elif posts_digits:
                    posts_count = int(posts_digits)
            except Exception:
                posts_count = None

            last_post_data = self._extract_last_post(clean_nickname, page_source, posts_count=posts_count)
            image_url = self._extract_profile_image(page_source)

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
                "MEH LINK": "\n".join(mehfil_data['MEH LINK']) if mehfil_data['MEH LINK'] else "",
                "MEH DATE": "\n".join(mehfil_data['MEH DATE']) if mehfil_data['MEH DATE'] else ""
            })
            
            # Check suspension
            data['STATUS'] = 'Verified'

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
                ('Joined', 'JOINED', normalize_date_only)
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

def run_target_mode(driver, sheets, max_profiles=0, targets=None, run_label="TARGET"):
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
    # Shared runner used by both Target mode (RunList) and Online mode (online users).
    # `run_label` ensures logs clearly show which mode triggered the same scraping pipeline.
    label = (run_label or "TARGET").strip().upper()
    log_msg(f"=== {label} MODE STARTED ===")
    
    stats = {
        "success": 0,
        "failed": 0,
        "new": 0,
        "updated": 0,
        "unchanged": 0,
        "phase2_ready": 0,
        "phase2_not_eligible": 0,
        "skipped": 0,
        "processed": 0,
        "invalid_nicknames": 0,
        "total_found": 0
    }

    # Get pending targets if not provided
    if targets is None:
        # Target mode path: fetch pending nicknames from the RunList sheet.
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
    log_msg(f"Processing {len(targets)} profile(s)...")

    scraper = ProfileScraper(driver)

    # ── PHASE 1: Scrape ALL profiles first (browser only, zero sheet API calls) ──
    log_msg("Phase 1/2: Scraping all profiles...", "INFO")
    scraped_results = []   # list of (target, profile_data or None)
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5
    STALL_PAUSE_SECONDS = 120

    for i, target in enumerate(targets, 1):
        nickname = validate_nickname(target.get('nickname', '').strip())
        if not nickname:
            log_msg(f"Skipping invalid nickname: {target.get('nickname', '')}", "WARNING")
            stats["invalid_nicknames"] += 1
            stats["skipped"] += 1
            scraped_results.append((target, None))
            continue

        log_progress(i, len(targets), nickname, "scraping...")
        profile_data = scraper.scrape_profile(nickname, source=target.get('source', 'Target'))
        scraped_results.append((target, profile_data))

        if profile_data:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log_msg(
                    f"⚠️ {consecutive_failures} consecutive failures. "
                    f"Pausing {STALL_PAUSE_SECONDS}s to let site recover...",
                    "WARNING"
                )
                time.sleep(STALL_PAUSE_SECONDS)
                consecutive_failures = 0

        if i < len(targets):
            time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

    # ── PHASE 2: Push ALL results to sheet in bulk ──
    log_msg(f"Phase 2/2: Pushing {len(scraped_results)} results to sheet in bulk...", "INFO")

    # Separate successful scrapes from failures
    profiles_with_tags = []
    target_status_updates = []  # queued RunList updates
    ts = get_pkt_time().strftime("%d-%b-%y %I:%M %p")

    for target, profile_data in scraped_results:
        nickname = (target.get('nickname') or '').strip()
        row = target.get('row')

        if profile_data is None:
            stats['failed'] += 1
            if row:
                target_status_updates.append({
                    'row_num': row, 'status': 'error', 'remarks': 'Scraping failed'
                })
            continue

        # Phase 2 eligibility (pre-compute before bulk write)
        posts_raw = str(profile_data.get("POSTS", "") or "")
        posts_digits = re.sub(r"\D+", "", posts_raw)
        try:
            posts_count = int(posts_digits) if posts_digits else None
        except (ValueError, TypeError):
            posts_count = None

        if posts_count is not None and posts_count < 100:
            stats["phase2_ready"] += 1
            profile_data["PHASE 2"] = "Ready"
        else:
            stats["phase2_not_eligible"] += 1
            profile_data["PHASE 2"] = "Not Eligible"

        profiles_with_tags.append((profile_data, target.get('tag')))

    # Bulk write to Profiles sheet
    if profiles_with_tags:
        write_results = sheets.bulk_write_profiles(profiles_with_tags)
    else:
        write_results = {}

    # Build RunList status updates from write results
    for target, profile_data in scraped_results:
        if profile_data is None:
            continue  # already handled above

        nickname = (profile_data.get("NICK NAME") or target.get('nickname') or '').strip()
        row = target.get('row')
        write_result = write_results.get(nickname, {"status": "error", "error": "not found in results"})
        status = write_result.get("status")
        scrap_ts = profile_data.get("DATETIME SCRAP") or ts

        if status == "new":
            stats['success'] += 1
            stats['new'] += 1
            remark = f"New Added: on {scrap_ts}"
            log_progress(0, len(targets), nickname, "new")
        elif status == "updated":
            stats['success'] += 1
            stats['updated'] += 1
            remark = f"Updated: on {scrap_ts}"
            log_progress(0, len(targets), nickname, "updated")
        elif status == "unchanged":
            stats['success'] += 1
            stats['unchanged'] += 1
            remark = f"Scraped ✅ : on {scrap_ts}"
            log_progress(0, len(targets), nickname, "unchanged")
        elif status == "skipped" and write_result.get("reason") == "non_verified":
            stats['success'] += 1
            remark = f"Skipped (non-verified): on {scrap_ts}"
            log_progress(0, len(targets), nickname, "skipped")
        else:
            stats['failed'] += 1
            remark = write_result.get('error') or 'Sheet write failed'
            if row:
                target_status_updates.append({'row_num': row, 'status': 'error', 'remarks': remark})
            continue

        if row:
            target_status_updates.append({'row_num': row, 'status': 'done', 'remarks': remark})

    # Bulk update RunList statuses in ONE API call
    if target_status_updates:
        sheets.bulk_update_target_statuses(target_status_updates)
    
    log_msg(f"=== {label} MODE COMPLETED ===")
    log_msg(
        f"Results: {stats['success']} success, {stats['failed']} failed, "
        f"{stats['skipped']} skipped"
    )

    log_msg(
        f"PHASE 2 Eligibility: READY={stats.get('phase2_ready', 0)} | NOT ELIGIBLE={stats.get('phase2_not_eligible', 0)}",
        "SUCCESS"
    )
            
    return stats
