"""
Centralized CSS and XPath Selectors.

This module contains all the selectors used for scraping the DamaDam website.
By centralizing them here, we can easily update them if the site's HTML
structure changes, without having to search through the entire codebase.
"""

class ProfileSelectors:
    """Selectors for the user profile page."""
    
    # Main page elements
    NICKNAME_HEADER = "//h1"
    UNVERIFIED_BADGE = ".//span[contains(text(), 'Unverified User')]"
    
    # Intro / Bio
    INTRO_TEXT_B = "//b[contains(normalize-space(.), 'Intro')]/following-sibling::span[1]"
    INTRO_TEXT_SPAN = "//span[contains(@class,'nos')]"
    
    # User details (multiple patterns for resilience)
    DETAIL_PATTERN_1 = "//b[contains(normalize-space(.), '{}:')]/following-sibling::span[1]"
    DETAIL_PATTERN_2 = "//div[contains(., '{}:') and not(contains(., '<img'))]"
    DETAIL_PATTERN_3 = "//span[contains(@class, 'label') and contains(., '{}:')]/following-sibling::span[1]"
    
    # Friend/Follow status
    FRIEND_STATUS_BUTTON = "//form[contains(@action, '/follow/')]/button"
    
    # Stats
    FOLLOWERS_COUNT = "//a[contains(@href, '/followers/')]/b"
    POSTS_COUNT = "//a[contains(@href, '/posts/')]/b"

    # Last Post
    LAST_POST_TEXT = "//div[contains(@class, 'pst')]/a"
    LAST_POST_TIME = "//div[contains(@class, 'pst')]/following-sibling::div/span[contains(@class, 'gry') and contains(@class, 'sp') and not(contains(@class, 'lk'))]"

    # Profile Image
    PROFILE_IMAGE = "//img[contains(@class, 'dp') and contains(@class, 's') and contains(@class, 'cov')]"
    PROFILE_IMAGE_CLOUDFRONT = "img[src*='cloudfront.net/avatar-imgs']"

    # Mehfil section
    MEHFIL_ENTRIES = "div.mbl.mtl a[href*='/mehfil/public/']"
    MEHFIL_NAME = "div.ow"
    MEHFIL_TYPE = "div[style*='background:#f8f7f9']"
    MEHFIL_DATE = "div.cs.sp"

class OnlineUserSelectors:
    """Selectors for the 'Online Users' page."""
    
    PAGE_HEADER = "h1.clb.cxl.lsp"
    
    # Multiple strategies for finding nicknames
    NICKNAME_STRATEGY_1 = "b.clb bdi"
    NICKNAME_STRATEGY_2 = "form[action*='/search/nickname/redirect/']"
    NICKNAME_STRATEGY_3 = "li.mbl.cl.sp"
    NICKNAME_STRATEGY_3_CHILD = ".//b[contains(@class, 'clb')]"

class LoginSelectors:
    """Selectors for the login page."""
    
    USERNAME_FIELD = "#nick, input[name='nick']"
    PASSWORD_FIELD_1 = "#pass, input[name='pass']"
    PASSWORD_FIELD_2 = "input[type='password']"
    SUBMIT_BUTTON = "button[type='submit'], form button"


class PostSelectors:
    """Selectors for posts pages (stored for Phase 2 use; not used in Phase 1)."""

    POST_CONTAINER = "article.bas-sh"
    AUTHOR_PROFILE_LINK = "article.bas-sh a[href^='/users/']"
    AUTHOR_NAME = "article.bas-sh h3[itemprop='name'] bdi"
    POST_TIME = "article.bas-sh time[itemprop='datePublished']"
    TEXT_POST_CONTENT = "article.bas-sh h2[itemprop='text']"
    IMAGE_POST_IMG = "article.bas-sh img[itemprop='image']"
    REPLIES_BUTTON = "a[href*='/comments/'] button[itemprop='discussionUrl'], a[href*='/comments/'] button.vt"
    REPLIES_COUNT = "button [itemprop='commentCount']"
    FOLLOW_BUTTON = "form[action='/follow/add/'] button.fbtn"
    ONE_ON_ONE_BUTTON = "form[action^='/1-on-1/'] button"
    SHARE_BUTTON_IMAGE = "form[action='/1-on-1/share/photo/'] button"
    LINK_BUTTON = "a[href^='/content/'] button.link"
    REPORT_BUTTON = "form[action='/report-or-block/'] button.report"
    CATEGORY_SUGGEST_BUTTON = "form[action='/category/suggest/'] button.categbtns"


class CommentSelectors:
    """Selectors for comments pages (stored for Phase 2 use; not used in Phase 1)."""

    COMMENTS_PAGE_ROOT = "div.bas-sh"
    BACK_TO_POSTS_BUTTON = "form[action='/redirect-to-content/'] button"
    MAIN_POST_WRAPPER = "section[itemtype*='SocialMediaPosting']"
    POST_AUTHOR_LINK = "section a[href^='/users/'] h3 bdi"
    POST_PUBLISHED_TIME = "section time[itemprop='datePublished']"
    POST_TEXT_CONTENT = "h2[itemprop='text']"
    MAIN_IMAGE = "img[itemprop='image']"
    REPLY_ANCHOR = "a[name='reply']"

    REPLY_FORM = "form[action='/direct-response/send/']"
    REPLY_CSRF_TOKEN = "form[action='/direct-response/send/'] input[name='csrfmiddlewaretoken']"
    REPLY_TEXTAREA = "textarea#id_direct_response, textarea[name='direct_response']"
    SEND_REPLY_BUTTON = "form[action='/direct-response/send/'] button[type='submit']"
    REFRESH_BUTTON = "form[action^='/comments/'] button.rf"

    FOLLOW_TO_REPLY_MARKER = "mark"

    COMMENT_ROW = "div[style*='overflow:hidden']"
    COMMENT_AUTHOR = "a[href^='/users/'] bdi b"
    COMMENT_TEXT = "span.nos.lsp.bw bdi"
    COMMENT_TIME = "span.cxs.cgy bdi"
    BLOCK_BUTTON = "form[action='/block/user/'] button"
    INLINE_REPLY_BUTTON = "form[action='/direct-response/create/'] button.dir_rep"
