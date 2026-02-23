"""Target phase-specific credential overrides."""
import os
from .config_common import Config


class TargetPhaseConfig:
    CREDENTIALS_JSON = os.getenv("TARGET_GOOGLE_CREDENTIALS_JSON", Config.GOOGLE_CREDENTIALS_JSON)
    CREDENTIALS_PATH = os.getenv("TARGET_GOOGLE_CREDENTIALS_PATH", None) or Config.get_credentials_path()
    SPREADSHEET_URL  = os.getenv("TARGET_GOOGLE_SHEET_URL", Config.GOOGLE_SHEET_URL)
