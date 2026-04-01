"""
Phase 2: Post Scraper Logic

Extracts paginated posts from DamaDam user profiles.
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.config_common import Config
from config.selectors import PostSelectors
from utils.ui import log_msg, get_pkt_time
from phases.profile.target_mode import normalize_post_datetime


def _get_element_text_safe(container, selector, by=By.CSS_SELECTOR, default=""):
    try:
        el = container.find_element(by, selector)
        text = el.text.strip()
        # If text is empty (sometimes happens with display:none elements or odd structures),
        # checkout InnerText or TextContent as fallback.
        if not text:
            text = el.get_attribute("textContent").strip()
        return text
    except NoSuchElementException:
        return default

def _get_element_attr_safe(container, selector, attr, by=By.CSS_SELECTOR, default=""):
    try:
        el = container.find_element(by, selector)
        return el.get_attribute(attr) or default
    except NoSuchElementException:
        return default


def extract_comment_info(container, browser_driver=None):
    """
    Extracts reply count, direct post URL, and the 'open/off/follow' comment status.
    Returns (count_str, post_url, has_replies_button, comment_status)
    """
    # 1. Try to find the Replies button
    try:
        btn_parent_a = container.find_element(By.CSS_SELECTOR, "a[href*='/comments/']")
        post_url = btn_parent_a.get_attribute('href')
        
        try:
            btn_text = btn_parent_a.text.strip()
            match = re.search(r'(\d+)', btn_text)
            count = match.group(1) if match else "0"
            return str(count), post_url, True, "Open"
        except Exception:
            return "0", post_url, True, "Open"
            
    except NoSuchElementException:
        pass
        
    # 2. No replies button. Determine if "Off" or "Follow to Reply"
    # Search for specific yellow banner / text that states "follow to reply". Sometimes it's inside the container or adjacent.
    container_text = container.text.lower()
    if "follow" in container_text and "reply" in container_text:
        return "0", "", False, "Follow to Reply"
    
    # 3. Otherwise, comments are totally off/disabled
    return "0", "", False, "Off"


def is_post_temporary(container, has_replies_button):
    """
    Determines if a post is temporary.
    Criteria (from user): "clock icon at the top right" OR "no reply icon button (didn't allow to comment)"
    """
    # 1. No replies button means disabled/temporary
    if not has_replies_button:
        return "Yes"
    
    # 2. Check for clock icon. Usually something like: img[src*='clock'], or an SVG path, or class containing 'clock'/'time'
    try:
        clock_svg = container.find_elements(By.XPATH, ".//*[local-name()='svg' and (contains(@class, 'clk') or contains(@class, 'tim') or contains(@class, 'clock'))]")
        if clock_svg:
            return "Yes"
    except Exception:
        pass
        
    return "No"


def scrape_posts_for_profile(browser, nickname, profile_id, needed_posts=0):
    """
    Navigates to user profile and scrapes posts across pagination.
    Stops when it hits `needed_posts` if needed_posts > 0.
    Returns a list of dictionaries mapping to Config.POSTS_COLUMN_ORDER.
    """
    base_url = f"{Config.BASE_URL}/profile/public/{nickname}/"
    posts_data = []
    page = 1
    total_parsed_overall = 0
    
    while True:
        url = f"{base_url}?page={page}"
        log_msg(f"Loading page {page}: {url}")
        
        try:
            browser.get(url)
            # Wait for either articles to load, or a clear "no more posts" indicator / empty page
            WebDriverWait(browser, Config.PAGE_LOAD_TIMEOUT).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, PostSelectors.POST_CONTAINER) or \
                          d.find_elements(By.XPATH, "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no posts')]") or \
                          d.find_elements(By.XPATH, "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no more posts')]")
            )
        except TimeoutException:
            log_msg(f"Timeout loading page {page}. Either strict rate limit or empty page.", "WARNING")
            break
            
        containers = browser.find_elements(By.CSS_SELECTOR, PostSelectors.POST_CONTAINER)
        if not containers:
            log_msg(f"No more post containers found on page {page}. End of data.")
            break
            
        log_msg(f"Found {len(containers)} posts on page {page}.")
        
        parsed_on_page = 0
        
        for container in containers:
            if needed_posts > 0 and total_parsed_overall >= needed_posts:
                break
                
            post_time_raw = _get_element_text_safe(container, PostSelectors.POST_TIME)
            post_time = normalize_post_datetime(post_time_raw) if post_time_raw else ""
            
            content_text = _get_element_text_safe(container, PostSelectors.TEXT_POST_CONTENT)
            
            # Since sometimes content is in a different tag if it's a caption, let's grab all text safely
            image_url = _get_element_attr_safe(container, PostSelectors.IMAGE_POST_IMG, "src")
            post_type = "Image" if image_url else "Text"
            
            if not content_text:
                all_text = container.text
                if post_type == "Image":
                    # Attempt to clean: `ZAim.KhAn : Assalam u... - 3 weeks ago FOLLOW 19`
                    # Remove the `Nickname : ` prefix if exists
                    cleaned = re.sub(r"^.*? :\s*", "", all_text, count=1, flags=re.MULTILINE|re.IGNORECASE)
                    # Remove trailing suffix like ` - 3 weeks ago FOLLOW 19`
                    cleaned = re.sub(r"\s*-\s*\d+\s*(?:weeks?|months?|days?|hours?|mins?|secs?).*$", "", cleaned, flags=re.DOTALL|re.IGNORECASE)
                    content_text = cleaned.strip()
                else:
                    lines = [l for l in all_text.splitlines() if l.strip() and not l.strip() in ['UNFOLLOW', '1 ON 1', 'SHARE', 'LINK', 'REPORT', 'HIDE', 'UNLIKE']]
                    if len(lines) > 1:
                        content_text = "\n".join(lines[1:-1])

            replies_count, post_url, has_replies, cmt_status = extract_comment_info(container, browser)
            is_temp = is_post_temporary(container, has_replies)
            
            hyperlinked_nick = f'=HYPERLINK("{base_url}", "{nickname}")'
            
            post_dict = {
                "PROFILE ID": profile_id,
                "NICK NAME": hyperlinked_nick,
                "POST URL": post_url,
                "POST TYPE": post_type,
                "POST TIME": post_time,
                "CONTENT": content_text[:5000],  # safety crop 
                "IMAGE URL": image_url,
                "REPLIES": replies_count,
                "COMMENT STATUS": cmt_status,
                "IS TEMPORARY": is_temp,
                "DATETIME SCRAP": get_pkt_time().strftime("%Y-%m-%d %H:%M")
            }
            
            posts_data.append(post_dict)
            parsed_on_page += 1
            total_parsed_overall += 1
            
            time.sleep(0.1) 
            
        if needed_posts > 0 and total_parsed_overall >= needed_posts:
            log_msg(f"Reached delta limit ({needed_posts}). Stopping pagination loop.")
            break
        
        # If we didn't parse any valid containers on this page, or we reached a page with 0 posts
        if parsed_on_page == 0:
            break
            
        page += 1
        time.sleep(Config.MIN_DELAY)
        
    return posts_data
