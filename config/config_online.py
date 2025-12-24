"""
Online phase-specific configuration

Contains credential overrides and spreadsheet URLs for the online phase.
"""

import os

from .config_common import Config


class OnlinePhaseConfig:
    CREDENTIALS_JSON = os.getenv("ONLINE_GOOGLE_CREDENTIALS_JSON", Config.GOOGLE_CREDENTIALS_JSON)
    CREDENTIALS_PATH = os.getenv("ONLINE_GOOGLE_CREDENTIALS_PATH", None) or Config.get_credentials_path()
    SPREADSHEET_URL = os.getenv("ONLINE_GOOGLE_SHEET_URL", Config.GOOGLE_SHEET_URL)
