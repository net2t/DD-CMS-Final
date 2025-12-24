"""
Posts phase-specific configuration
"""

import os

from .config_common import Config


class PostsPhaseConfig:
    CREDENTIALS_JSON = os.getenv("POSTS_GOOGLE_CREDENTIALS_JSON", None)
    CREDENTIALS_PATH = os.getenv("POSTS_GOOGLE_CREDENTIALS_PATH", None)
    SPREADSHEET_URL = os.getenv("POSTS_GOOGLE_SHEET_URL", Config.GOOGLE_SHEET_URL)
