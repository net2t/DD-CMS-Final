"""Centralized CSS and XPath selectors for DamaDam scraping."""


class ProfileSelectors:
    NICKNAME_HEADER    = "//h1"
    UNVERIFIED_BADGE   = ".//span[contains(text(), 'Unverified User')]"
    INTRO_TEXT_B       = "//b[contains(normalize-space(.), 'Intro')]/following-sibling::span[1]"
    INTRO_TEXT_SPAN    = "//span[contains(@class,'nos')]"
    DETAIL_PATTERN_1   = "//b[contains(normalize-space(.), '{}:')]/following-sibling::span[1]"
    DETAIL_PATTERN_2   = "//div[contains(., '{}:') and not(contains(., '<img'))]"
    DETAIL_PATTERN_3   = "//span[contains(@class, 'label') and contains(., '{}:')]/following-sibling::span[1]"
    FRIEND_STATUS_BUTTON      = "//form[contains(@action, '/follow/')]/button"
    FOLLOWERS_COUNT           = "//a[contains(@href, '/followers/')]/b"
    POSTS_COUNT               = "//a[contains(@href, '/posts/')]/b"
    LAST_POST_TEXT            = "//div[contains(@class, 'pst')]/a"
    LAST_POST_TIME            = "//div[contains(@class, 'pst')]/following-sibling::div/span[contains(@class, 'gry') and contains(@class, 'sp') and not(contains(@class, 'lk'))]"
    PROFILE_IMAGE             = "//img[contains(@class, 'dp') and contains(@class, 's') and contains(@class, 'cov')]"
    PROFILE_IMAGE_CLOUDFRONT  = "img[src*='cloudfront.net/avatar-imgs']"
    MEHFIL_ENTRIES            = "div.mbl.mtl a[href*='/mehfil/public/']"
    MEHFIL_NAME               = "div.ow"
    MEHFIL_TYPE               = "div[style*='background:#f8f7f9']"
    MEHFIL_DATE               = "div.cs.sp"


class OnlineUserSelectors:
    PAGE_HEADER          = "h1.clb.cxl.lsp"
    NICKNAME_STRATEGY_1  = "b.clb bdi"
    NICKNAME_STRATEGY_2  = "form[action*='/search/nickname/redirect/']"
    NICKNAME_STRATEGY_3  = "li.mbl.cl.sp"
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
