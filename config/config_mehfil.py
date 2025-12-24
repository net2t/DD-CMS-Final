"""
Mehfil phase-specific configuration
"""

import os

from .config_common import Config


class MehfilPhaseConfig:
    CREDENTIALS_JSON = os.getenv("MEHFIL_GOOGLE_CREDENTIALS_JSON", None)
    CREDENTIALS_PATH = os.getenv("MEHFIL_GOOGLE_CREDENTIALS_PATH", None)
    SPREADSHEET_URL = os.getenv("MEHFIL_GOOGLE_SHEET_URL", Config.GOOGLE_SHEET_URL)
