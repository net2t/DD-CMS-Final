"""
Google Sheets Manager - All sheet operations

Refactored for v2.100.0.13:
- Nickname-based duplicate detection with inline diffs.
- New/updated profiles are moved to Row 2.
- 'Quantico' font applied to headers.
- API rate limit handling with retries.
- Sorting by DATETIME SCRAP on exit.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound, APIError

from config.config_common import Config
from utils.ui import get_pkt_time, log_msg

def clean_data(value):
    """Clean cell data, returning empty string for invalid values."""
    if not value:
        return ""
    
    v = str(value).strip().replace('\xa0', ' ')
    bad_values = {
        "No city", "Not set", "[No Posts]", "N/A", 
        "no city", "not set", "[no posts]", "n/a",
        "[No Post URL]", "[Error]", "no set", "none", "null", "no age"
    }
    
    if v in bad_values or not v:
        return ""
    
    import re
    return re.sub(r"\s+", " ", v)

# ==================== GOOGLE SHEETS CLIENT ====================

def create_gsheets_client(credentials_json=None, credentials_path=None):
    """Create authenticated Google Sheets client"""
    log_msg("Authenticating with Google Sheets API...")
    
    if not Config.GOOGLE_SHEET_URL:
        log_msg("GOOGLE_SHEET_URL is not set", "ERROR")
        raise ValueError("Missing GOOGLE_SHEET_URL")
    
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        json_source = credentials_json or Config.GOOGLE_CREDENTIALS_JSON
        path_source = credentials_path
        
        if not path_source:
            default_cred = Config.get_credentials_path()
            path_source = default_cred if default_cred else None

        if json_source:
            log_msg("Using credentials from provided JSON")
            try:
                cred_data = json.loads(json_source)
                creds = Credentials.from_service_account_info(cred_data, scopes=scope)
                return gspread.authorize(creds)
            except json.JSONDecodeError as e:
                log_msg(f"Invalid JSON in credentials: {e}", "ERROR")
                raise
        
        if path_source and Path(path_source).exists():
            log_msg(f"Using credentials file: {path_source}")
            creds = Credentials.from_service_account_file(str(path_source), scopes=scope)
            return gspread.authorize(creds)
        
        log_msg("No valid credentials found", "ERROR")
        raise ValueError("Missing Google credentials")
    
    except Exception as e:
        log_msg(f"Google Sheets authentication failed: {e}", "ERROR")
        raise

# ==================== SHEETS MANAGER ====================

class SheetsManager:
    # ... baqi __init__ aur dosray functions original jese

    def get_targets(self):
        """
        Retrieves only rows from the 'RunList' sheet that have pending status.
        Only specific pending variants are allowed.
        """
        try:
            all_values = self.target_ws.get_all_values()
            if len(all_values) <= 1:
                return []

            rows = all_values[1:]

            pending_variants = ['pending', 'Pending', '⚡pending', '⚡Pending', 'PENDING', '⚡PENDING']

            targets = []
            for idx, row in enumerate(rows, start=2):
                if len(row) < 1 or not row[0].strip():
                    continue

                nickname = row[0].strip()
                status = row[1].strip() if len(row) > 1 else ""

                if status in pending_variants:
                    source = row[3].strip() if len(row) > 3 else "Target"
                    targets.append({
                        'nickname': nickname,
                        'row': idx,  # row number starting from 2
                        'source': source or 'Target'
                    })
                else:
                    log_msg(f"Skipping row {idx+1}: Status '{status}' (only pending variants allowed)", "WARNING")

            return targets

        except Exception as e:
            log_msg(f"Failed to get targets: {e}", "ERROR")
            return []

    # Baqi functions (write_profile, update_target_status, flush_new_profiles, sort_profiles_by_date etc.) bilkul original jese hi rakhna

    def _compute_profile_state(self, profile_data):
        skip_reason = (profile_data.get('__skip_reason') or '').lower()
        
        if any(reason in skip_reason for reason in ['timeout', 'not found', 'page timeout']):
            return Config.PROFILE_STATE_DEAD
        
        status = profile_data.get("STATUS", "")
        if "banned" in status.lower():
            return Config.PROFILE_STATE_BANNED
        if "unverified" in status.lower():
            return Config.PROFILE_STATE_UNVERIFIED
        
        return Config.PROFILE_STATE_ACTIVE

# File end
