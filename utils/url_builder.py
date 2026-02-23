"""
Centralized URL construction for the DamaDam scraper.
"""
from config.config_common import Config


def get_profile_url(nickname):
    """Returns the private profile URL for a given nickname."""
    if not nickname or not isinstance(nickname, str):
        return None
    return f"{Config.BASE_URL}/users/{nickname.strip()}/"


def get_public_profile_url(nickname):
    """
    Returns the public posts page (page 1) for a given nickname.
    Page 1 gives us the most recent post without deep pagination.
    Previously was page=4 but reduced to page=1 to minimize API usage.
    """
    if not nickname or not isinstance(nickname, str):
        return None
    return f"{Config.BASE_URL}/profile/public/{nickname.strip()}?page=1"
