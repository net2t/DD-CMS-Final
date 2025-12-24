"""
Target phase-specific configuration
"""

import os

from .config_common import Config


class TargetPhaseConfig:
    CREDENTIALS_JSON = os.getenv("TARGET_GOOGLE_CREDENTIALS_JSON", None)
    CREDENTIALS_PATH = os.getenv("TARGET_GOOGLE_CREDENTIALS_PATH", None)
    SPREADSHEET_URL = os.getenv("TARGET_GOOGLE_SHEET_URL", Config.GOOGLE_SHEET_URL)
