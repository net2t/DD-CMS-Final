"""
Centralized CSS and XPath selectors for DamaDam scraping.

FIX LOG (Phase 1 Stabilization):
- FOLLOWERS_COUNT: removed /b child — DamaDam no longer wraps count in <b>
  Old: //a[contains(@href, '/followers/')]/b
  New: //a[contains(@href, '/followers/')] — reads .text directly from anchor
- POSTS_COUNT: same fix — removed /b child requirement
  Old: //a[contains(@href, '/posts/')]/b
  New: //a[contains(@href, '/posts/')] — reads .text directly from anchor
- PROFILE_LOADED: removed broken /b selectors from ready-check list
  These were causing profile page load detection to rely on broken paths
- Added FOLLOWERS_COUNT_ALT and POSTS_COUNT_ALT as XPath fallbacks
  using different possible HTML structures on DamaDam
"""


class ProfileSelectors:

    NICKNAME_HEADER    = "//h1"

    # --- Page load detection ---
    # WHAT IT DOES: Waits until at least one of these elements appears in DOM
    # before scraping starts. If none found = page not loaded yet.
    # FIX: Removed the two broken /b child selectors. Only keep h1 which is reliable.
    PROFILE_LOADED     = [
        "//h1",
        "//a[contains(@href, '/followers/')]",   # anchor itself (no /b child required)
        "//a[contains(@href, '/posts/')]",        # anchor itself (no /b child required)
    ]

    UNVERIFIED_BADGE   = ".//span[contains(text(), 'Unverified User')]"
    INTRO_TEXT_B       = "//b[contains(normalize-space(.), 'Intro')]/following-sibling::span[1]"
    INTRO_TEXT_SPAN    = "//span[contains(@class,'nos')]"
    DETAIL_PATTERN_1   = "//b[contains(normalize-space(.), '{}:')]/following-sibling::span[1]"
    DETAIL_PATTERN_2   = "//div[contains(., '{}:') and not(contains(., '<img'))]"
    DETAIL_PATTERN_3   = "//span[contains(@class, 'label') and contains(., '{}:')]/following-sibling::span[1]"
    FRIEND_STATUS_BUTTON = "//form[contains(@action, '/follow/')]/button"

    # --- FOLLOWERS selector (PRIMARY) ---
    # WHAT IT DOES: Finds the anchor tag that links to /followers/ page
    # FIX: Removed /b child — new DamaDam HTML puts count as direct text in <a>,
    # not inside a <b> child. Old = broken. New = reads anchor text directly.
    # AFFECTS: _parse_count_from_anchor() will now read anchor.text instead of b.text
    FOLLOWERS_COUNT    = "//a[contains(@href, '/followers/')]"

    # --- FOLLOWERS selector (FALLBACK ALT 1) ---
    # WHAT IT DOES: Tries a broader parent div search if anchor approach fails
    # AFFECTS: _extract_stats() fallback chain
    FOLLOWERS_COUNT_ALT = "//div[contains(@class,'cl') and .//a[contains(@href,'/followers/')]]"

    # --- POSTS selector (PRIMARY) ---
    # WHAT IT DOES: Finds the anchor tag that links to /posts/ page
    # FIX: Same as FOLLOWERS — removed /b child requirement
    # AFFECTS: _parse_count_from_anchor() reads anchor text directly
    POSTS_COUNT        = "//a[contains(@href, '/posts/')]"

    # --- POSTS selector (FALLBACK ALT 1) ---
    # WHAT IT DOES: Looks for count in a div near the word POSTS
    # AFFECTS: _extract_stats() fallback chain
    POSTS_COUNT_ALT    = "//div[contains(translate(normalize-space(.),'posts','POSTS'),'POSTS') and string-length(normalize-space(.)) < 20]"

    LAST_POST_TEXT     = "//div[contains(@class, 'pst')]/a"
    LAST_POST_TIME     = "//div[contains(@class, 'pst')]/following-sibling::div/span[contains(@class, 'gry') and contains(@class, 'sp') and not(contains(@class, 'lk'))]"
    PROFILE_IMAGE      = "//img[contains(@class, 'dp') and contains(@class, 's') and contains(@class, 'cov')]"
    PROFILE_IMAGE_CLOUDFRONT = "img[src*='cloudfront.net/avatar-imgs']"
    MEHFIL_ENTRIES     = "div.mbl.mtl a[href*='/mehfil/public/']"
    MEHFIL_NAME        = "div.ow"
    MEHFIL_TYPE        = "div[style*='background:#f8f7f9']"
    MEHFIL_DATE        = "div.cs.sp"


class OnlineUserSelectors:
    PAGE_HEADER              = "h1"
    NICKNAME_STRATEGY_1      = "b.clb bdi"
    NICKNAME_STRATEGY_2      = "form[action*='/search/nickname/redirect/']"
    NICKNAME_STRATEGY_3      = "li.mbl.cl.sp"
    NICKNAME_STRATEGY_3_CHILD = ".//b[contains(@class, 'clb')]"


class LoginSelectors:
    USERNAME_FIELD   = "#nick, input[name='nick']"
    PASSWORD_FIELD_1 = "#pass, input[name='pass']"
    PASSWORD_FIELD_2 = "input[type='password']"
    SUBMIT_BUTTON    = "button[type='submit'], form button"


class PostSelectors:
    """Selectors for posts pages — reserved for Phase 2."""
    POST_CONTAINER      = "article.bas-sh"
    AUTHOR_PROFILE_LINK = "article.bas-sh a[href^='/users/']"
    AUTHOR_NAME         = "article.bas-sh h3[itemprop='name'] bdi"
    POST_TIME           = "article.bas-sh time[itemprop='datePublished']"
    TEXT_POST_CONTENT   = "article.bas-sh h2[itemprop='text']"
    IMAGE_POST_IMG      = "article.bas-sh img[itemprop='image']"
    REPLIES_BUTTON      = "a[href*='/comments/'] button[itemprop='discussionUrl']"
    REPLIES_COUNT       = "button [itemprop='commentCount']"
    FOLLOW_BUTTON       = "form[action='/follow/add/'] button.fbtn"
