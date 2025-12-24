"""
Centralized URL construction for the DamaDam scraper.

This module provides a single source of truth for all URLs used in the application,
making it easy to update them if the website's structure changes.
"""

from config.config_common import Config

def get_profile_url(nickname):
    """Constructs the URL for a user's profile page."""
    if not nickname or not isinstance(nickname, str):
        return None
    return f"{Config.BASE_URL}/users/{nickname.strip()}/"

def get_public_profile_url(nickname):
    """Constructs the URL for a user's public profile/post page."""
    if not nickname or not isinstance(nickname, str):
        return None
    return f"{Config.BASE_URL}/profile/public/{nickname.strip()}"
