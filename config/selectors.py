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
    
    # Mehfil section
    MEHFIL_ENTRIES = "div.mbl.mtl a[href*='/mehfil/public/']"
    MEHFIL_NAME = ".//div[contains(@class, 'ow')]"
    MEHFIL_TYPE = ".//div[contains(@style, 'background:#f8f7f9')]"
    MEHFIL_DATE = ".//div[contains(@class, 'cs') and contains(@class, 'sp')]"

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
