"""
Profile Scraper + Target Mode Runner — DD-CMS-V3

Key changes from V2:
- Per-profile sheet write: RunList is updated IMMEDIATELY after each profile
  (no more batch queue — crash-safe)
- Col 9  (LIST)     ← RunList Col F value  (Target) or "" (Online)
- Col 11 (RUN MODE) ← "Online" or "Target"
- Public page URL uses ?page=1
"""

import time
import re
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config.config_common import Config
from config.selectors import ProfileSelectors
from utils.ui import get_pkt_time, log_msg, log_progress
from utils.url_builder import get_profile_url, get_public_profile_url


# ── Text helpers ───────────────────────────────────────────────────────────────

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().replace('\xa0', ' ').replace('\n', ' ')).strip()


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


def normalize_post_datetime(raw_date):
    """Parse any date/time string → 'dd-mmm-yy hh:mm am/pm' (PKT)."""
    if not raw_date or not str(raw_date).strip():
        return ""
    now  = get_pkt_time()
    text = str(raw_date).strip().lower()
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\t', ' '))

    # Relative times e.g. "3 hours ago"
    if "ago" in text:
        delta = timedelta()
        for amount, unit in re.findall(r'(\d+)\s*(year|yr|month|mon|week|wk|day|hour|hr|minute|min|second|sec)s?', text):
            amount = int(amount)
            u = unit
            if u in ('year', 'yr'):   delta += timedelta(days=amount * 365)
            elif u in ('month','mon'): delta += timedelta(days=amount * 30)
            elif u in ('week', 'wk'): delta += timedelta(weeks=amount)
            elif u == 'day':           delta += timedelta(days=amount)
            elif u in ('hour', 'hr'): delta += timedelta(hours=amount)
            elif u in ('minute','min'):delta += timedelta(minutes=amount)
            elif u in ('second','sec'):delta += timedelta(seconds=amount)
        return (now - delta).strftime("%d-%b-%y %I:%M %p").lower()

    # Absolute date formats
    for fmt in [
        "%d-%b-%y %I:%M %p", "%d-%b-%y %H:%M", "%d-%m-%y %H:%M",
        "%d-%m-%Y %H:%M",    "%d-%b-%y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d-%b-%y",          "%d-%m-%y", "%Y-%m-%d",
        "%I:%M %p",          "%H:%M",
    ]:
        try:
            dt = datetime.strptime(text, fmt)
            if '%d' not in fmt or '%m' not in fmt:
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            if ':' not in fmt:
                dt = dt.replace(hour=now.hour, minute=now.minute, second=0, microsecond=0)
            if dt.year > now.year + 1:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime("%d-%b-%y %I:%M %p").lower()
        except ValueError:
            continue

    return now.strftime("%d-%b-%y %I:%M %p").lower()


def normalize_date_only(raw_date):
    """Return date portion only: dd-mmm-yy"""
    dt_str = normalize_post_datetime(raw_date)
    if not dt_str:
        return ""
    try:
        return datetime.strptime(dt_str.split(' ')[0], "%d-%b-%y").strftime("%d-%b-%y")
    except Exception:
        return ""


def sanitize_nickname_for_url(nickname):
    """Return cleaned nickname safe for URL, or None if invalid."""
    if not nickname or not isinstance(nickname, str):
        return None
    nickname = nickname.strip()
    if not nickname or ' ' in nickname or len(nickname) > 50:
        return None
    if re.search(r'[<>"\'&|;`\\()\[\]{}\t\n\r]', nickname):
        return None
    return nickname


def validate_nickname(nickname):
    return sanitize_nickname_for_url(nickname)


# ── Detection helpers ──────────────────────────────────────────────────────────

def detect_suspension(page_source):
    if not page_source:
        return None
    lower = page_source.lower()
    for indicator in Config.SUSPENSION_INDICATORS:
        if indicator in lower:
            return indicator
    return None


def detect_unverified(driver, page_source):
    if not driver:
        return False
    try:
        elems = driver.find_elements(
            By.XPATH,
            "//div[contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz',"
            " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'UNVERIFIED USER') and "
            "contains(translate(@style,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'background:tomato')]"
        )
        return any(el.is_displayed() for el in elems)
    except Exception:
        return False


def detect_banned(page_source):
    if not page_source:
        return False
    lower = page_source.lower()
    return any(x in lower for x in ("account suspended", "banned!", "forever banned", "/website-rules/"))


# ── Profile Scraper ────────────────────────────────────────────────────────────

class ProfileScraper:
    """Scrapes a single DamaDam user profile page."""

    def __init__(self, driver):
        self.driver = driver

    def _extract_mehfil_details(self, page_source):
        result = {'MEH NAME': [], 'MEH LINK': [], 'MEH DATE': []}
        try:
            entries = self.driver.find_elements(By.CSS_SELECTOR, ProfileSelectors.MEHFIL_ENTRIES)
            for entry in entries:
                try:
                    name = entry.find_element(By.CSS_SELECTOR, ProfileSelectors.MEHFIL_NAME)
                    result['MEH NAME'].append(clean_text(name.text))
                    result['MEH LINK'].append(entry.get_attribute('href') or "")
                    date_elem = entry.find_element(By.CSS_SELECTOR, ProfileSelectors.MEHFIL_DATE)
                    date_text = clean_text(date_elem.text)
                    if 'since' in date_text.lower():
                        date_text = date_text.split('since')[-1].strip()
                    result['MEH DATE'].append(normalize_date_only(date_text))
                except Exception:
                    continue
        except Exception:
            pass
        return result

    def _extract_friend_status(self, page_source):
        try:
            btn = self.driver.find_element(By.XPATH, ProfileSelectors.FRIEND_STATUS_BUTTON)
            label = btn.text.strip().upper()
            if "UNFOLLOW" in label: return "Yes"
            if "FOLLOW"   in label: return "No"
        except Exception:
            pass
        if 'action="/follow/remove/' in page_source: return "Yes"
        if 'action="/follow/add/'    in page_source: return "No"
        return ""

    def _extract_rank(self, page_source):
        try:
            match = re.search(r'src=\"(/static/img/stars/[^\"]+)\"', page_source)
            if not match:
                return "", ""
            rel  = match.group(1)
            url  = rel if rel.startswith('http') else f"https://damadam.pk{rel}"
            lower = rel.lower()
            if   "red"    in lower: label = "Red Star"
            elif "gold"   in lower: label = "Gold Star"
            elif "silver" in lower: label = "Silver Star"
            else:                   label = Path(rel).stem.replace('-', ' ').title()
            return label, url
        except Exception:
            return "", ""

    def _extract_user_id(self, page_source):
        try:
            m = re.search(r'name=[\"\']tid[\"\']\s+value=[\"\'](\d+)[\"\']', page_source)
            if m:
                return m.group(1)
        except Exception:
            pass
        return ""

    def _extract_stats(self, page_source):
        stats = {'FOLLOWERS': '', 'POSTS': ''}
        try:
            stats['FOLLOWERS'] = clean_text(
                self.driver.find_element(By.XPATH, ProfileSelectors.FOLLOWERS_COUNT).text)
        except Exception:
            pass
        try:
            stats['POSTS'] = clean_text(
                self.driver.find_element(By.XPATH, ProfileSelectors.POSTS_COUNT).text)
        except Exception:
            pass
        # Fallback regex
        if not stats['FOLLOWERS']:
            for pat in [r'([\d,\.]+)\s+verified\s+followers', r'([\d,\.]+)\s+followers']:
                m = re.search(pat, page_source, re.IGNORECASE)
                if m: stats['FOLLOWERS'] = clean_text(m.group(1)); break
        if not stats['POSTS']:
            m = re.search(r'([\d,\.]+)\s+posts?', page_source, re.IGNORECASE)
            if m: stats['POSTS'] = clean_text(m.group(1))
        return stats

    def _extract_last_post(self, nickname, page_source, posts_count=None):
        result = {'LAST POST': '', 'LAST POST TIME': ''}

        # Try selectors on current page
        try:
            href = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TEXT).get_attribute('href')
            if href: result['LAST POST'] = normalize_post_url(href)
        except Exception:
            pass
        try:
            t = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TIME).text
            result['LAST POST TIME'] = normalize_post_datetime(t)
        except Exception:
            pass

        # If posts confirmed zero, skip public page
        if posts_count == 0:
            return result

        # Fetch public profile page 1 if enabled and data still missing
        if (not result['LAST POST'] or not result['LAST POST TIME']) \
                and nickname and Config.LAST_POST_FETCH_PUBLIC_PAGE:
            private_url = self.driver.current_url
            public_url  = get_public_profile_url(nickname)  # already has ?page=1
            try:
                self.driver.get(public_url)
                WebDriverWait(self.driver, Config.LAST_POST_PUBLIC_PAGE_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
                )
                try:
                    first = self.driver.find_element(By.CSS_SELECTOR, "article.mbl.bas-sh")
                except Exception:
                    try:
                        first = self.driver.find_element(By.CSS_SELECTOR, "article")
                    except Exception:
                        first = None

                if first:
                    for sel in ["a[href*='/content/']", "a[href*='/comments/text/']", "a[href*='/comments/image/']"]:
                        try:
                            href = first.find_element(By.CSS_SELECTOR, sel).get_attribute('href')
                            if href:
                                result['LAST POST'] = normalize_post_url(href)
                                break
                        except Exception:
                            continue
                    for sel in ["time.sp.cxs.cgy", "time", ".gry", ".sp"]:
                        try:
                            t = clean_text(first.find_element(By.CSS_SELECTOR, sel).text)
                            if t:
                                result['LAST POST TIME'] = normalize_post_datetime(t)
                                break
                        except Exception:
                            continue
            except Exception:
                log_msg(f"Public page fetch failed for {nickname}", "WARNING")
            finally:
                try:
                    self.driver.get(private_url)
                    WebDriverWait(self.driver, Config.LAST_POST_PUBLIC_PAGE_TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, ProfileSelectors.NICKNAME_HEADER))
                    )
                except Exception:
                    pass
        return result

    def _extract_profile_image(self, page_source):
        try:
            img = self.driver.find_element(By.CSS_SELECTOR, ProfileSelectors.PROFILE_IMAGE_CLOUDFRONT)
            src = img.get_attribute('src')
            if src and src.startswith('http'): return src
        except Exception:
            pass
        try:
            img = self.driver.find_element(By.XPATH, ProfileSelectors.PROFILE_IMAGE)
            src = img.get_attribute('src')
            if src:
                return src if src.startswith('http') else f"https://damadam.pk{src}"
        except Exception:
            pass
        if page_source:
            m = re.search(r"<img[^>]+src=['\"](https?://[^'\"]+avatar-imgs/[^'\"]+)['\"]", page_source, re.I)
            if m: return m.group(1)
        m = re.search(r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']", page_source or "", re.I)
        if m:
            url = m.group(1)
            if 'og_image.png' not in url:
                return url if url.startswith('http') else f"https://damadam.pk{url}"
        return ""

    def scrape_profile(self, nickname, source="Target"):
        """
        Scrape a single profile page. Returns profile dict or None on hard failure.
        """
        clean_nick = sanitize_nickname_for_url(nickname)
        if not clean_nick:
            log_msg(f"Invalid nickname: {nickname}", "ERROR")
            return None

        url = get_profile_url(clean_nick)
        try:
            log_msg(f"Scraping: {nickname}", "SCRAPING")
            self.driver.get(url)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, ProfileSelectors.NICKNAME_HEADER))
            )
            page_source = self.driver.page_source
            now         = get_pkt_time()

            data = {col: Config.DEFAULT_VALUES.get(col, "") for col in Config.COLUMN_ORDER}
            data["NICK NAME"]     = clean_nick
            data["DATETIME SCRAP"] = now.strftime("%d-%b-%y %I:%M %p")

            # Ban / suspension
            if detect_suspension(page_source) or detect_banned(page_source):
                data['STATUS'] = 'Banned'
                return data
            if detect_unverified(self.driver, page_source):
                data['STATUS'] = 'Unverified'
                return data

            data['STATUS'] = 'Verified'

            # Extract structured data
            mehfil      = self._extract_mehfil_details(page_source)
            stats       = self._extract_stats(page_source)
            _, rank_img = self._extract_rank(page_source)
            user_id     = self._extract_user_id(page_source)

            posts_digits = re.sub(r"\D+", "", str(stats.get('POSTS', '') or ''))
            try:
                posts_count = int(posts_digits) if posts_digits else None
            except Exception:
                posts_count = None
            if posts_digits == "0":
                posts_count = 0

            last_post = self._extract_last_post(clean_nick, page_source, posts_count)
            image_url  = self._extract_profile_image(page_source)

            data.update({
                "ID":           user_id,
                "PROFILE LINK": url.rstrip('/'),
                "POST URL":     get_public_profile_url(clean_nick),
                "RURL":         rank_img,
                "FOLLOWERS":    stats['FOLLOWERS'],
                "POSTS":        stats['POSTS'],
                "LAST POST":    last_post['LAST POST'],
                "LAST POST TIME": last_post['LAST POST TIME'],
                "IMAGE":        image_url,
                "MEH NAME":     "\n".join(mehfil['MEH NAME']),
                "MEH LINK":     "\n".join(mehfil['MEH LINK']),
                "MEH DATE":     "\n".join(mehfil['MEH DATE']),
            })

            # Profile detail fields
            field_map = [
                ('City',    'CITY',    lambda x: clean_text(x) if x else ''),
                ('Gender',  'GENDER',  lambda x: 'Female' if x and 'female' in x.lower()
                                               else 'Male' if x and 'male' in x.lower() else ''),
                ('Married', 'MARRIED', lambda x: 'Yes' if x and x.lower() in {'yes','married'}
                                               else 'No' if x and x.lower() in {'no','single','unmarried'} else ''),
                ('Age',     'AGE',     lambda x: clean_text(x) if x else ''),
                ('Joined',  'JOINED',  normalize_date_only),
            ]
            for label, key, process in field_map:
                for pattern in [ProfileSelectors.DETAIL_PATTERN_1,
                                ProfileSelectors.DETAIL_PATTERN_2,
                                ProfileSelectors.DETAIL_PATTERN_3]:
                    try:
                        elem = self.driver.find_element(By.XPATH, pattern.format(label))
                        raw  = elem.text.strip()
                        if ':' in raw and pattern == ProfileSelectors.DETAIL_PATTERN_2:
                            raw = raw.split(':', 1)[1].strip()
                        val = process(raw)
                        if val:
                            data[key] = val
                            break
                    except Exception:
                        continue

            return data

        except TimeoutException:
            log_msg(f"Timeout loading profile: {nickname}", "TIMEOUT")
            return None
        except Exception as e:
            log_msg(f"Error scraping {nickname}: {e}", "ERROR")
            return None


# ── Target Mode Runner ─────────────────────────────────────────────────────────

def run_target_mode(driver, sheets, max_profiles=0, targets=None, run_label="TARGET"):
    """
    Scrape profiles and write results IMMEDIATELY after each profile.

    This is crash-safe: RunList is updated right after each profile is scraped,
    so no data is lost if the run is interrupted.

    Args:
        driver:       Selenium WebDriver
        sheets:       SheetsManager instance
        max_profiles: 0 = unlimited
        targets:      list of target dicts (if None, reads from RunList)
        run_label:    "TARGET" or "ONLINE"

    Returns:
        dict of run statistics
    """
    label = (run_label or "TARGET").strip().upper()
    log_msg(f"=== {label} MODE STARTED ===")

    stats = {
        "success": 0, "failed": 0, "new": 0, "updated": 0,
        "unchanged": 0, "skipped": 0, "processed": 0, "total_found": 0,
    }

    # Fetch targets from RunList if not provided (Target mode path)
    if targets is None:
        try:
            targets = sheets.get_pending_targets()
        except Exception as e:
            log_msg(f"Failed to get pending targets: {e}", "ERROR")
            return stats

    if not targets:
        log_msg("No pending targets found")
        return stats

    if max_profiles > 0:
        targets = targets[:max_profiles]

    stats["total_found"] = len(targets)
    log_msg(f"Processing {len(targets)} profile(s)...")

    scraper              = ProfileScraper(driver)
    run_mode             = "Online" if label == "ONLINE" else "Target"
    consecutive_failures = 0
    MAX_CONSEC_FAIL      = 5
    STALL_PAUSE          = 120

    for i, target in enumerate(targets, 1):
        nickname = validate_nickname((target.get('nickname') or '').strip())
        if not nickname:
            log_msg(f"Skipping invalid nickname: {target.get('nickname', '')}", "WARNING")
            stats["skipped"] += 1
            continue

        # ── 1. Scrape ─────────────────────────────────────────────────────────
        log_progress(i, len(targets), nickname, "scraping")
        profile_data = scraper.scrape_profile(nickname, source=target.get('source', run_mode))

        if not profile_data:
            consecutive_failures += 1
            stats["failed"] += 1
            if target.get('row'):
                sheets.update_target_status(target['row'], 'error', 'Scraping failed')
            if consecutive_failures >= MAX_CONSEC_FAIL:
                log_msg(f"{consecutive_failures} consecutive failures — pausing {STALL_PAUSE}s", "WARNING")
                time.sleep(STALL_PAUSE)
                consecutive_failures = 0
            if i < len(targets):
                time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))
            continue

        consecutive_failures = 0

        # ── 2. Write to Profiles sheet immediately ────────────────────────────
        # list_value = RunList Col F (target mode only; empty for online mode)
        list_value = target.get('tag', '') if run_mode == "Target" else ""

        write_result = sheets.write_profile(
            profile_data,
            run_mode=run_mode,
            list_value=list_value,
        )
        w_status = write_result.get("status")

        ts = profile_data.get("DATETIME SCRAP") or get_pkt_time().strftime("%d-%b-%y %I:%M %p")

        # ── 3. Update RunList immediately (Target mode) ───────────────────────
        if w_status == "new":
            stats["success"] += 1; stats["new"] += 1
            remark = f"New Added: {ts}"
            log_progress(i, len(targets), nickname, "new")

        elif w_status == "updated":
            stats["success"] += 1; stats["updated"] += 1
            remark = f"Updated: {ts}"
            log_progress(i, len(targets), nickname, "updated")

        elif w_status == "unchanged":
            stats["success"] += 1; stats["unchanged"] += 1
            remark = f"Scraped ✅ {ts}"
            log_progress(i, len(targets), nickname, "unchanged")

        elif w_status == "skipped":
            stats["skipped"] += 1
            remark = f"Skipped (non-verified): {ts}"
            log_progress(i, len(targets), nickname, "skipped")

        else:
            stats["failed"] += 1
            remark = write_result.get("error") or "Sheet write failed"
            log_progress(i, len(targets), nickname, "error")

        # Update RunList row in Target mode
        if target.get('row'):
            final_status = 'done' if w_status in ('new', 'updated', 'unchanged', 'skipped') else 'error'
            sheets.update_target_status(target['row'], final_status, remark)

        stats["processed"] += 1

        if i < len(targets):
            time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

    log_msg(f"=== {label} MODE COMPLETED — "
            f"success={stats['success']} failed={stats['failed']} skipped={stats['skipped']} ===")
    return stats
