"""
Profile Scraper + Target Mode Runner — DD-CMS-V3

Fixes (v3.0.4):
- CRITICAL: target_mode.py was missing (only .bak existed) — restored from backup
- has_meaningful_data: no longer drops profiles silently. Profiles with partial data
  are now saved with DATA_STATUS = 'PARTIAL' instead of being discarded.
- Only drops profile if NICK NAME itself is missing (truly unsalvageable).
- Emergency random-number fallback removed — was injecting wrong data into FOLLOWERS.
- DATA_STATUS field added to every scraped profile ('COMPLETE' or 'PARTIAL').
"""

import time
import re
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
    if not raw_date or not str(raw_date).strip():
        return ""
    now  = get_pkt_time()
    text = str(raw_date).strip().lower()
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ').replace('\t', ' '))

    if "ago" in text:
        delta = timedelta()
        for amount, unit in re.findall(r'(\d+)\s*(year|yr|month|mon|week|wk|day|hour|hr|minute|min|second|sec)s?', text):
            amount = int(amount)
            u = unit
            if u in ('year', 'yr'):     delta += timedelta(days=amount * 365)
            elif u in ('month', 'mon'): delta += timedelta(days=amount * 30)
            elif u in ('week', 'wk'):   delta += timedelta(weeks=amount)
            elif u == 'day':             delta += timedelta(days=amount)
            elif u in ('hour', 'hr'):   delta += timedelta(hours=amount)
            elif u in ('minute', 'min'):delta += timedelta(minutes=amount)
            elif u in ('second', 'sec'):delta += timedelta(seconds=amount)
        return (now - delta).strftime("%d-%b-%y %I:%M %p").lower()

    for fmt in [
        "%d-%b-%y %I:%M %p", "%d-%b-%y %H:%M", "%d-%m-%y %H:%M",
        "%d-%m-%Y %H:%M",    "%d-%b-%y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%d-%b-%y",          "%d-%m-%y", "%Y-%m-%d",
        "%I:%M %p",          "%H:%M",
    ]:
        try:
            dt = datetime.strptime(text, fmt)
            has_day   = '%d' in fmt
            has_month = '%m' in fmt or '%b' in fmt or '%B' in fmt
            if not has_day or not has_month:
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
                if dt > (now + timedelta(hours=1)):
                    dt = dt - timedelta(days=1)
            if ':' not in fmt:
                dt = dt.replace(hour=now.hour, minute=now.minute, second=0, microsecond=0)
            if dt.year > now.year + 1:
                dt = dt.replace(year=dt.year - 100)
            return dt.strftime("%d-%b-%y %I:%M %p").lower()
        except ValueError:
            continue

    return now.strftime("%d-%b-%y %I:%M %p").lower()


def normalize_date_only(raw_date):
    dt_str = normalize_post_datetime(raw_date)
    if not dt_str:
        return ""
    try:
        return datetime.strptime(dt_str.split(' ')[0], "%d-%b-%y").strftime("%d-%b-%y")
    except Exception:
        return ""


def sanitize_nickname_for_url(nickname):
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

    def __init__(self, driver):
        self.driver = driver

    def _extract_digits(self, text):
        if not text:
            return ""
        m = re.search(r"(\d[\d,\.]*)", str(text))
        return m.group(1) if m else ""

    def _parse_count_from_anchor(self, anchor_elem):
        """
        Try to extract a numeric count from an <a> element.
        First reads direct .text, then falls back to child node text.
        The /b child is NOT required — DamaDam removed it.
        """
        if not anchor_elem:
            return ""
        try:
            raw = anchor_elem.text or ""
        except Exception:
            raw = ""
        digits = self._extract_digits(raw)
        if digits:
            return clean_text(digits)

        # Fallback: count may be inside a child element (span, b, etc.)
        try:
            child_text = " ".join(
                [c.text for c in anchor_elem.find_elements(By.XPATH, ".//*") if c.text]
            )
        except Exception:
            child_text = ""
        digits = self._extract_digits(child_text)
        return clean_text(digits)

    def _wait_for_profile_page(self, timeout=5):
        """
        Wait until at least one profile element appears in DOM.
        Returns True if loaded. Raises TimeoutException if not.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            for selector in ProfileSelectors.PROFILE_LOADED:
                try:
                    elem = self.driver.find_element(By.XPATH, selector)
                    if elem.is_displayed():
                        return True
                except NoSuchElementException:
                    continue
            time.sleep(0.2)
        raise TimeoutException(f"Profile page did not load within {timeout}s")

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

    def _extract_rank(self, page_source):
        try:
            match = re.search(r'src=\"(/static/img/stars/[^\"]+)\"', page_source)
            if not match:
                return "", ""
            rel   = match.group(1)
            url   = rel if rel.startswith('http') else f"https://damadam.pk{rel}"
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

    def _extract_stats(self, page_source, nickname):
        """
        Extract follower count and post count using a 3-layer fallback strategy.

        Layer 1: XPath on live DOM elements (most reliable)
        Layer 2: Regex on raw page_source (medium reliability)
        Layer 3: Empty string returned — no random-number fallback (removed in v3.0.4)
                 because guessing wrong numbers is worse than leaving the field blank.

        FIX v3.0.4: Removed emergency random-number fallback from previous version.
        That block was picking any number from the page and injecting it as FOLLOWERS
        count — which caused incorrect data being written to the sheet.
        """
        stats = {'FOLLOWERS': '', 'POSTS': ''}

        # ────────────────────────────────────────────────────────────────────────
        # FOLLOWERS — Layer 1: XPath
        # WHAT IT DOES: Finds the /followers/ anchor and reads its text directly.
        # FIX: No /b child needed — DamaDam now puts count as plain anchor text.
        # ────────────────────────────────────────────────────────────────────────
        log_msg(f"[DEBUG] Starting follower extraction for {nickname}", "DEBUG")
        try:
            followers_element = self.driver.find_element(By.XPATH, ProfileSelectors.FOLLOWERS_COUNT)
            stats['FOLLOWERS'] = self._parse_count_from_anchor(followers_element)
            log_msg(f"[DEBUG] Followers found via XPath: '{stats['FOLLOWERS']}'", "DEBUG")
        except Exception as e:
            log_msg(f"[DEBUG] Followers XPath failed: {e}", "DEBUG")

        # FOLLOWERS — Layer 2: Regex fallback
        # WHAT IT DOES: Searches raw HTML for follower count patterns.
        # AFFECTS: Catches profiles where the anchor is present but Selenium can't read it.
        if not stats['FOLLOWERS']:
            log_msg(f"[DEBUG] Followers XPath empty, trying regex", "DEBUG")
            for i, pat in enumerate([
                r'([\d,\.]+)\s+verified\s+followers',
                r'([\d,\.]+)\s+followers',
                r'/followers/[^>]*>\s*(?:<[^>]+>\s*)*([\d,\.]+)',
            ], 1):
                m = re.search(pat, page_source, re.IGNORECASE)
                if m:
                    # Use last capture group that has digits
                    val = m.group(m.lastindex) if m.lastindex else m.group(1)
                    stats['FOLLOWERS'] = clean_text(val)
                    log_msg(f"[DEBUG] Followers via regex pattern {i}: '{stats['FOLLOWERS']}'", "DEBUG")
                    break
                else:
                    log_msg(f"[DEBUG] Followers regex pattern {i} no match", "DEBUG")

        if not stats['FOLLOWERS']:
            log_msg(f"[WARNING] FOLLOWERS empty for {nickname} — will save as blank", "WARNING")

        # ────────────────────────────────────────────────────────────────────────
        # POSTS — Layer 1: XPath
        # WHAT IT DOES: Finds /posts/ anchor, waits briefly, reads count.
        # FIX: No /b child — same fix as FOLLOWERS above.
        # ────────────────────────────────────────────────────────────────────────
        log_msg(f"[DEBUG] Starting post count extraction for {nickname}", "DEBUG")
        try:
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, ProfileSelectors.POSTS_COUNT))
                )
            except Exception:
                pass
            posts_element = self.driver.find_element(By.XPATH, ProfileSelectors.POSTS_COUNT)
            stats['POSTS'] = self._parse_count_from_anchor(posts_element)
            log_msg(f"[DEBUG] Posts found via XPath: '{stats['POSTS']}'", "DEBUG")
        except Exception as e:
            log_msg(f"[DEBUG] Posts XPath failed: {e}", "DEBUG")

        # POSTS — Layer 2: Regex fallback
        # WHAT IT DOES: Multiple regex patterns on raw HTML for post count.
        # AFFECTS: Catches posts count from different HTML structures DamaDam may use.
        if not stats['POSTS']:
            try:
                # Re-read page source in case DOM updated after XPath attempt
                page_source = self.driver.page_source
            except Exception:
                pass
            log_msg(f"[DEBUG] Posts XPath empty, trying regex. Source len={len(page_source)}", "DEBUG")
            for i, pat in enumerate([
                r'/posts/[^>]*>\s*(?:<[^>]+>\s*)*([\d,\.]+)',
                r'\b([\d,\.]+)\b\s*posts?\b',
                r'<div>\s*([\d,\.]+)\s*</div>\s*<div[^>]*>\s*POSTS\s*</div>',
                r'POSTS\s*</div>\s*</div>\s*<div>\s*([\d,\.]+)\s*</div>',
            ], 1):
                m = re.search(pat, page_source, re.IGNORECASE)
                if m:
                    val = m.group(m.lastindex) if m.lastindex else m.group(1)
                    if val and re.search(r'\d', val):
                        stats['POSTS'] = clean_text(val)
                        log_msg(f"[DEBUG] Posts via regex pattern {i}: '{stats['POSTS']}'", "DEBUG")
                        break
                    else:
                        log_msg(f"[DEBUG] Pattern {i} matched but no digits: '{val}'", "DEBUG")
                else:
                    log_msg(f"[DEBUG] Posts regex pattern {i} no match", "DEBUG")

        if not stats['POSTS']:
            # Diagnostic log — helps debug future selector failures
            posts_links = re.findall(r'href="[^"]*posts[^"]*"[^>]*>([^<]*)', page_source, re.IGNORECASE)
            posts_context = re.findall(r'[^<>]{0,30}posts[^<>]{0,30}', page_source, re.IGNORECASE)
            log_msg(f"[WARNING] POSTS empty for {nickname} — will save as blank", "WARNING")
            log_msg(f"[DEBUG] Posts links in HTML: {posts_links}", "DEBUG")
            log_msg(f"[DEBUG] Posts context snippets: {posts_context[:5]}", "DEBUG")

        return stats

    def _extract_last_post(self, nickname, page_source, posts_count=None):
        result = {'LAST POST': '', 'LAST POST TIME': ''}

        try:
            href = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TEXT).get_attribute('href')
            if href:
                result['LAST POST'] = normalize_post_url(href)
        except Exception:
            pass
        try:
            t = self.driver.find_element(By.XPATH, ProfileSelectors.LAST_POST_TIME).text
            result['LAST POST TIME'] = normalize_post_datetime(t)
        except Exception:
            pass

        # Skip public page fetch if user has 0 posts
        if posts_count == 0:
            return result

        if (not result['LAST POST'] or not result['LAST POST TIME']) \
                and nickname and Config.LAST_POST_FETCH_PUBLIC_PAGE:
            private_url = self.driver.current_url
            public_url  = get_public_profile_url(nickname)
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
                    self._wait_for_profile_page(timeout=Config.LAST_POST_PUBLIC_PAGE_TIMEOUT)
                    current_url = self.driver.current_url.rstrip('/')
                    if current_url != private_url.rstrip('/'):
                        log_msg(f"Navigation mismatch: expected {private_url}, got {current_url}", "WARNING")
                except Exception:
                    pass
        return result

    def _extract_profile_image(self, page_source):
        try:
            img = self.driver.find_element(By.CSS_SELECTOR, ProfileSelectors.PROFILE_IMAGE_CLOUDFRONT)
            src = img.get_attribute('src')
            if src and src.startswith('http'):
                return src
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
            if m:
                return m.group(1)
        m = re.search(
            r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']",
            page_source or "", re.I
        )
        if m:
            url = m.group(1)
            if 'og_image.png' not in url:
                return url if url.startswith('http') else f"https://damadam.pk{url}"
        return ""

    def scrape_profile(self, nickname, source="Target"):
        """
        Main profile scraping method.

        FIX v3.0.4 — has_meaningful_data logic overhauled:

        OLD BEHAVIOUR (BROKEN):
          If CITY, AGE, FOLLOWERS, POSTS, IMAGE, MEH NAME were all empty:
          → return None (profile silently dropped, OLD stale data stays in sheet)

        NEW BEHAVIOUR (FIXED):
          → Always save the profile if NICK NAME is present.
          → Set DATA_STATUS = 'PARTIAL' when meaningful fields are missing.
          → Set DATA_STATUS = 'COMPLETE' when at least one meaningful field found.
          → Stale data is always overwritten — never left behind.

        WHY: A profile with empty FOLLOWERS/POSTS is still a valid profile.
        Dropping it meant the sheet kept old wrong values forever.
        """
        clean_nick = sanitize_nickname_for_url(nickname)
        if not clean_nick:
            log_msg(f"Invalid nickname: {nickname}", "ERROR")
            return None

        url = get_profile_url(clean_nick)
        try:
            log_msg(f"Scraping: {nickname}", "SCRAPING")
            self.driver.get(url)
            self._wait_for_profile_page(timeout=Config.PAGE_LOAD_TIMEOUT)
            page_source = self.driver.page_source
            now         = get_pkt_time()

            data = {col: Config.DEFAULT_VALUES.get(col, "") for col in Config.COLUMN_ORDER}
            data["NICK NAME"]      = clean_nick
            data["DATETIME SCRAP"] = now.strftime("%Y-%m-%d %H:%M")

            # ── Banned / Suspended / Unverified detection ──────────────────────
            if detect_suspension(page_source) or detect_banned(page_source):
                data['_STATUS']     = 'Banned'
                data['STATUS']      = 'Banned'
                data['DATA_STATUS'] = 'COMPLETE'  # Status is definitively known
                return data
            if detect_unverified(self.driver, page_source):
                data['_STATUS']     = 'Unverified'
                data['STATUS']      = 'Unverified'
                data['DATA_STATUS'] = 'COMPLETE'  # Status is definitively known
                return data

            data['_STATUS'] = 'Verified'
            data['STATUS']  = 'Verified'

            # ── Extract all profile data ───────────────────────────────────────
            mehfil      = self._extract_mehfil_details(page_source)
            stats       = self._extract_stats(page_source, nickname)
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
                "ID":             user_id,
                "PROFILE LINK":   url.rstrip('/'),
                "POST URL":       get_public_profile_url(clean_nick),
                "RURL":           rank_img,
                "FOLLOWERS":      stats['FOLLOWERS'],
                "POSTS":          stats['POSTS'],
                "LAST POST":      last_post['LAST POST'],
                "LAST POST TIME": last_post['LAST POST TIME'],
                "IMAGE":          image_url,
                "MEH NAME":       "\n".join(mehfil['MEH NAME']),
                "MEH LINK":       "\n".join(mehfil['MEH LINK']),
                "MEH DATE":       "\n".join(mehfil['MEH DATE']),
            })

            # ── Structured detail fields (City, Gender, Age, Married, Joined) ──
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

            # ──────────────────────────────────────────────────────────────────
            # DATA_STATUS: COMPLETE vs PARTIAL
            #
            # FIX v3.0.4: This block NEVER drops a profile anymore.
            #
            # OLD CODE:
            #   if not has_meaningful_data:
            #       return None   ← THIS WAS THE BUG — stale data stayed in sheet
            #
            # NEW CODE:
            #   Always return data. Set DATA_STATUS to tell us how complete it is.
            #   The sheet will always overwrite — never leave old values behind.
            # ──────────────────────────────────────────────────────────────────
            has_meaningful_data = any([
                data.get("CITY"),
                data.get("AGE"),
                data.get("FOLLOWERS"),
                data.get("POSTS"),
                data.get("IMAGE"),
                data.get("MEH NAME"),
            ])

            if has_meaningful_data:
                data['DATA_STATUS'] = 'COMPLETE'
                log_msg(f"Profile {nickname} scraped — DATA_STATUS: COMPLETE", "OK")
            else:
                # ← KEY FIX: Was return None. Now we save as PARTIAL.
                data['DATA_STATUS'] = 'PARTIAL'
                log_msg(f"Profile {nickname} has no meaningful data — saving as PARTIAL (not dropping)", "WARNING")

            return data

        except TimeoutException:
            try:
                cur_url = self.driver.current_url
            except Exception:
                cur_url = ""
            try:
                title = self.driver.title
            except Exception:
                title = ""
            snippet = ""
            try:
                ps = self.driver.page_source or ""
                snippet = clean_text(ps[:500])
            except Exception:
                pass

            log_msg(f"Timeout loading profile: {nickname}", "TIMEOUT")
            if cur_url or title:
                log_msg(f"[TIMEOUT DEBUG] url={cur_url} | title={title}", "DEBUG")
            if snippet:
                log_msg(f"[TIMEOUT DEBUG] snippet={snippet}", "DEBUG")
            return None
        except Exception as e:
            log_msg(f"Error scraping {nickname}: {e}", "ERROR")
            return None


# ── Target Mode Runner ─────────────────────────────────────────────────────────

def run_target_mode(driver, sheets, max_profiles=0, targets=None, run_label="TARGET"):
    """
    Scrape profiles and write results via batch system.

    FIX v3.0.4:
    - Profiles with DATA_STATUS=PARTIAL are now written to sheet (not dropped)
    - Row movement to Row 2 is still done immediately inside write_profile
    - Data writes are batched and flushed every BATCH_SIZE profiles
    - Col D in RunList = ignore flag (handled in sheets.get_pending_targets)
    """
    label = (run_label or "TARGET").strip().upper()
    log_msg(f"=== {label} MODE STARTED ===")

    stats = {
        "success": 0, "failed": 0, "new": 0, "updated": 0,
        "unchanged": 0, "skipped": 0, "processed": 0, "total_found": 0,
    }

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

        # ── 1. Scrape ──────────────────────────────────────────────────────────
        log_progress(i, len(targets), nickname, "scraping")
        profile_data = scraper.scrape_profile(nickname, source=target.get('source', run_mode))

        if not profile_data:
            # scrape_profile only returns None for genuinely failed/invalid profiles
            consecutive_failures += 1
            stats["failed"] += 1
            if target.get('row'):
                sheets.update_target_status(target['row'], 'error', 'Scraping failed - no data returned')
            if consecutive_failures >= MAX_CONSEC_FAIL:
                log_msg(f"{consecutive_failures} consecutive failures — pausing {STALL_PAUSE}s", "WARNING")
                time.sleep(STALL_PAUSE)
                consecutive_failures = 0
            if i < len(targets):
                time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))
            continue

        consecutive_failures = 0

        # ── 2. Queue write (moveDimension is immediate inside write_profile) ───
        # NOTE: Profiles with DATA_STATUS=PARTIAL are written too.
        # This ensures stale data is always overwritten.
        list_value   = target.get('tag', '') if run_mode == "Target" else ""
        write_result = sheets.write_profile(
            profile_data,
            run_mode=run_mode,
            list_value=list_value,
        )
        w_status = write_result.get("status")

        ts = profile_data.get("DATETIME SCRAP") or get_pkt_time().strftime("%Y-%m-%d %H:%M")

        # ── 3. Update RunList status immediately ───────────────────────────────
        # Include DATA_STATUS in remark so RunList shows PARTIAL profiles clearly
        data_status_tag = f" [{profile_data.get('DATA_STATUS', '')}]" if profile_data.get('DATA_STATUS') else ""

        if w_status == "new":
            stats["success"] += 1; stats["new"] += 1
            remark = f"New Added: {ts}{data_status_tag}"
            log_progress(i, len(targets), nickname, "new")

        elif w_status == "updated":
            stats["success"] += 1; stats["updated"] += 1
            remark = f"Updated: {ts}{data_status_tag}"
            log_progress(i, len(targets), nickname, "updated")

        elif w_status == "unchanged":
            stats["success"] += 1; stats["unchanged"] += 1
            remark = f"Scraped OK: {ts}{data_status_tag}"
            log_progress(i, len(targets), nickname, "unchanged")

        elif w_status == "skipped":
            stats["skipped"] += 1
            remark = f"Skipped (non-verified): {ts}{data_status_tag}"
            log_progress(i, len(targets), nickname, "skipped")

        else:
            stats["failed"] += 1
            remark = write_result.get("error") or "Sheet write failed"
            log_progress(i, len(targets), nickname, "error")

        if target.get('row'):
            final_status = 'done' if w_status in ('new', 'updated', 'unchanged', 'skipped') else 'error'
            sheets.update_target_status(target['row'], final_status, remark)

        stats["processed"] += 1

        # ── 4. Flush batch every BATCH_SIZE profiles ───────────────────────────
        if sheets.should_flush_batch():
            if not sheets.flush_batch():
                log_msg("Batch flush failed — stopping run to avoid missing data", "ERROR")
                if target.get('row'):
                    sheets.update_target_status(target['row'], 'error', 'Batch flush failed')
                stats["failed"] += 1
                break

        if i < len(targets):
            time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

    # ── 5. Final flush for any remaining queued writes ─────────────────────────
    if not sheets.flush_batch():
        log_msg("Final batch flush failed — run may be missing writes", "ERROR")
        stats["failed"] += 1

    log_msg(f"=== {label} MODE COMPLETED — "
            f"success={stats['success']} failed={stats['failed']} "
            f"skipped={stats['skipped']} partial={stats.get('partial', 0)} ===")
    return stats
