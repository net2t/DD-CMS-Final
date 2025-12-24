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
        
        # fallback to global path if none provided
        if not path_source:
            default_cred = Config.get_credentials_path()
            path_source = default_cred if default_cred else None

        # Try using raw JSON first (GitHub Actions or override)
        if json_source:
            log_msg("Using credentials from provided JSON")
            try:
                cred_data = json.loads(json_source)
                creds = Credentials.from_service_account_info(cred_data, scopes=scope)
                return gspread.authorize(creds)
            except json.JSONDecodeError as e:
                log_msg(f"Invalid JSON in credentials: {e}", "ERROR")
                raise
        
        # Try file path (local development or override)
        if path_source and Path(path_source).exists():
            log_msg(f"Using credentials file: {path_source}")
            creds = Credentials.from_service_account_file(str(path_source), scopes=scope)
            return gspread.authorize(creds)
        
        # No credentials found
        log_msg("No valid credentials found", "ERROR")
        raise ValueError("Missing Google credentials")
    
    except Exception as e:
        log_msg(f"Google Sheets authentication failed: {e}", "ERROR")
        raise

# ==================== SHEETS MANAGER ====================

class SheetsManager:
    """Manages all Google Sheets operations
    
    STEP-6 Updates:
    - Nickname-based duplicate detection
    - Row 2 insertion for new/updated data
    - Dashboard blank value handling
    - Sorting by DATETIME SCRAP descending
    """
    
    def __init__(self, client=None, credentials_json=None, credentials_path=None):
        if client is None:
            client = create_gsheets_client(
                credentials_json=credentials_json,
                credentials_path=credentials_path
            )
        
        self.client = client
        self.spreadsheet = client.open_by_url(Config.GOOGLE_SHEET_URL)
        
        # Initialize worksheets
        self.profiles_ws = self._get_or_create(Config.SHEET_PROFILES, cols=len(Config.COLUMN_ORDER))
        self.target_ws = self._get_or_create(Config.SHEET_TARGET, cols=4)
        self.dashboard_ws = self._get_or_create(Config.SHEET_DASHBOARD, cols=15)
        self.online_log_ws = self._get_or_create(Config.SHEET_ONLINE_LOG, cols=3)
        
        # Optional sheets
        self.tags_ws = self._get_sheet_if_exists(Config.SHEET_TAGS)
        
        # Load data
        self.tags_mapping = {}
        self.existing_profiles = {}  # {nickname_lower: {row, data}}
        
        self._init_headers()
        self._load_tags()
        self._load_existing_profiles()
        
        log_msg("Google Sheets connected successfully", "OK")
    
    def _get_or_create(self, name, cols=20, rows=1000):
        """Get or create worksheet"""
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"Creating worksheet: {name}")
            return self.spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)
    
    def _get_sheet_if_exists(self, name):
        """Get sheet if it exists, return None otherwise"""
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"Optional sheet '{name}' not found, skipping")
            return None
    
    def _init_headers(self):
        """Initialize headers and apply formatting for all sheets."""
        sheets_to_format = {
            self.profiles_ws: Config.COLUMN_ORDER,
            self.target_ws: ["Nickname", "Status", "Remarks", "Source"],
            self.dashboard_ws: ["Run#", "Timestamp", "Profiles", "Success", "Failed", 
                               "New", "Updated", "Unchanged", "Trigger", "Start", "End",
                               "Active", "Unverified", "Banned", "Dead"],
            self.online_log_ws: Config.ONLINE_LOG_COLUMNS
        }

        for ws, headers in sheets_to_format.items():
            if not ws:
                continue
            try:
                current_headers = ws.row_values(1)
                if not current_headers or current_headers != headers:
                    log_msg(f"Initializing headers for '{ws.title}' sheet...")
                    ws.clear()
                    ws.append_row(headers)
                    self._apply_header_format(ws)
            except Exception as e:
                log_msg(f"Header initialization for '{ws.title}' failed: {e}", "ERROR")

    def _apply_header_format(self, ws):
        """Apply 'Quantico' font and bold style to the header row."""
        try:
            log_msg(f"Applying 'Quantico' font to '{ws.title}' headers...")
            header_range = f'A1:{gspread.utils.rowcol_to_a1(1, ws.col_count)}'
            ws.format(header_range, {
                "textFormat": {
                    "fontFamily": "Quantico",
                    "bold": True
                }
            })
        except Exception as e:
            log_msg(f"Failed to apply header format for '{ws.title}': {e}", "WARNING")
    
    def _load_tags(self):
        """Load tags mapping from Tags sheet"""
        if not self.tags_ws:
            return
        
        try:
            all_values = self.tags_ws.get_all_values()
            if not all_values or len(all_values) < 2:
                return
            
            headers = all_values[0]
            for col_idx, header in enumerate(headers):
                tag_name = clean_data(header)
                if not tag_name:
                    continue
                
                for row in all_values[1:]:
                    if col_idx < len(row):
                        nickname = row[col_idx].strip()
                        if nickname:
                            key = nickname.lower()
                            if key in self.tags_mapping:
                                if tag_name not in self.tags_mapping[key]:
                                    self.tags_mapping[key] += f", {tag_name}"
                            else:
                                self.tags_mapping[key] = tag_name
            
            log_msg(f"Loaded {len(self.tags_mapping)} tag mappings")
        
        except Exception as e:
            log_msg(f"Tags load failed: {e}")
    
    def _load_existing_profiles(self):
        """Load existing profiles indexed by NICKNAME (lowercase)."""
        try:
            rows = self.profiles_ws.get_all_values()[1:]  # Skip header
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME")
            
            for i, row in enumerate(rows, start=2):
                if len(row) > nick_idx:
                    nickname = row[nick_idx].strip()
                    if nickname:
                        key = nickname.lower()
                        self.existing_profiles[key] = {
                            'row': i,
                            'data': row
                        }
            
            log_msg(f"Loaded {len(self.existing_profiles)} existing profiles (indexed by nickname)")
        
        except Exception as e:
            log_msg(f"Failed to load existing profiles: {e}")
    
    # ==================== PROFILE OPERATIONS ====================

    def _perform_write_operation(self, operation, *args, **kwargs):
        """Perform a sheet write operation with retry logic for API rate limits."""
        for attempt in range(3):
            try:
                operation(*args, **kwargs)
                time.sleep(Config.SHEET_WRITE_DELAY)  # Prevent hitting per-minute limits
                return True
            except APIError as e:
                if '429' in str(e):
                    wait_time = (attempt + 1) * 60
                    log_msg(f"API rate limit hit. Waiting {wait_time}s before retry...", "WARNING")
                    time.sleep(wait_time)
                else:
                    log_msg(f"API Error during write: {e}", "ERROR")
                    return False
            except Exception as e:
                log_msg(f"An unexpected error occurred during write: {e}", "ERROR")
                return False
        log_msg("Failed to perform write operation after multiple retries.", "ERROR")
        return False

    def _compute_profile_state(self, profile_data):
        """Compute normalized PROFILE_STATE from scraper signals."""
        skip_reason = (profile_data.get('__skip_reason') or '').lower()
        status = (profile_data.get('STATUS') or '').strip()
        intro = (profile_data.get('INTRO') or '').lower()

        if any(reason in skip_reason for reason in ['timeout', 'not found', 'page timeout']):
            return Config.PROFILE_STATE_DEAD
        if status == 'Banned' or any(word in intro for word in ['suspend', 'banned', 'blocked']):
            return Config.PROFILE_STATE_BANNED
        if status == 'Unverified':
            return Config.PROFILE_STATE_UNVERIFIED
        return Config.PROFILE_STATE_ACTIVE

    def write_profile(self, profile_data):
        """Write profile to Profiles sheet with nickname-based duplicate handling."""
        nickname = (profile_data.get("NICK NAME") or "").strip()
        if not nickname:
            log_msg("Profile has no nickname, skipping write.", "WARNING")
            return {"status": "error", "error": "Missing nickname"}

        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        profile_data["PROFILE_STATE"] = self._compute_profile_state(profile_data)
        if nickname.lower() in self.tags_mapping:
            profile_data["TAGS"] = self.tags_mapping[nickname.lower()]

        row_data = [clean_data(profile_data.get(col, "")) for col in Config.COLUMN_ORDER]
        
        key = nickname.lower()
        existing = self.existing_profiles.get(key)

        if existing:
            old_row_num = existing['row']
            old_data = existing['data']
            changed_fields = []
            updated_row = []

            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else ""
                new_val = row_data[i]
                if col in {"DATETIME SCRAP", "SOURCE"}:
                    updated_row.append(new_val)
                    continue
                if old_val != new_val:
                    changed_fields.append(col)
                    updated_row.append(f"Before: {old_val}\nNow: {new_val}")
                else:
                    updated_row.append(new_val)

            if not changed_fields:
                return {"status": "unchanged"}

            if self._perform_write_operation(self.profiles_ws.delete_rows, old_row_num):
                if self._perform_write_operation(self.profiles_ws.insert_row, updated_row, index=2):
                    log_msg(f"Updated duplicate profile {nickname} and moved to Row 2.", "OK")
                    self._load_existing_profiles() # Refresh cache after structural change
                    return {"status": "updated", "changed_fields": changed_fields}
            return {"status": "error", "error": "Failed to update sheet"}
        else:
            if self._perform_write_operation(self.profiles_ws.insert_row, row_data, index=2):
                log_msg(f"New profile {nickname} added at Row 2.", "OK")
                self._load_existing_profiles() # Refresh cache after structural change
                return {"status": "new"}
            return {"status": "error", "error": "Failed to write to sheet"}

    def get_profile(self, nickname):
        """Fetch existing profile data by nickname."""
        record = self.existing_profiles.get((nickname or "").strip().lower())
        if not record:
            return None
        return {col: (record['data'][i] if i < len(record['data']) else "") for i, col in enumerate(Config.COLUMN_ORDER)}


    # ==================== TARGET OPERATIONS ====================

    def get_pending_targets(self):
        """Get pending targets from the RunList sheet."""
        try:
            rows = self.target_ws.get_all_values()[1:]
            return [
                {'nickname': row[0].strip(), 'row': idx, 'source': (row[3] if len(row) > 3 else 'Target').strip() or 'Target'}
                for idx, row in enumerate(rows, start=2)
                if row and row[0].strip() and ("pending" in (row[1] if len(row) > 1 else '').lower() or not (row[1] if len(row) > 1 else ''))
            ]
        except Exception as e:
            log_msg(f"Failed to get pending targets: {e}", "ERROR")
            return []

    def update_target_status(self, row_num, status, remarks):
        """Update the status and remarks for a target in the RunList sheet."""
        status_map = {
            'pending': Config.TARGET_STATUS_PENDING,
            'done': Config.TARGET_STATUS_DONE,
            'complete': Config.TARGET_STATUS_DONE,
            'error': Config.TARGET_STATUS_ERROR,
            'suspended': Config.TARGET_STATUS_ERROR,
            'unverified': Config.TARGET_STATUS_ERROR
        }
        normalized_status = status_map.get((status or "").lower().strip(), status)
        self._perform_write_operation(self.target_ws.update, f"B{row_num}:C{row_num}", [[normalized_status, remarks]])

    # ==================== ONLINE LOG OPERATIONS ====================

    def log_online_user(self, nickname, timestamp=None):
        """Log an online user to the OnlineLog sheet."""
        ts = timestamp or get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        self._perform_write_operation(self.online_log_ws.append_row, [ts, nickname, ts])

    # ==================== DASHBOARD OPERATIONS ====================

    def update_dashboard(self, metrics):
        """Update the dashboard with run metrics, using empty strings for missing values."""
        state_counts = metrics.get("state_counts", {})
        row = [
            metrics.get("Run Number", 1),
            metrics.get("Last Run", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
            metrics.get("Profiles Processed", 0),
            metrics.get("Success", 0),
            metrics.get("Failed", 0),
            metrics.get("New Profiles", 0),
            metrics.get("Updated Profiles", 0),
            metrics.get("Unchanged Profiles", 0),
            metrics.get("Trigger", "manual"),
            metrics.get("Start", ""),
            metrics.get("End", ""),
            state_counts.get("ACTIVE", 0),
            state_counts.get("UNVERIFIED", 0),
            state_counts.get("BANNED", 0),
            state_counts.get("DEAD", 0)
        ]
        if self._perform_write_operation(self.dashboard_ws.append_row, row):
            log_msg("Dashboard updated successfully.", "OK")

    # ==================== HELPERS ====================

    def sort_profiles_by_date(self):
        """Sort the Profiles sheet by DATETIME SCRAP descending."""
        log_msg("Sorting profiles by date...")
        try:
            all_rows = self.profiles_ws.get_all_values()
            if len(all_rows) <= 1:
                return

            header, rows = all_rows[0], all_rows[1:]
            date_idx = header.index("DATETIME SCRAP")

            def parse_date(row):
                try:
                    return datetime.strptime(row[date_idx], "%d-%b-%y %I:%M %p")
                except (ValueError, IndexError):
                    return datetime.min

            rows.sort(key=parse_date, reverse=True)
            
            if self._perform_write_operation(self.profiles_ws.clear) and self._perform_write_operation(self.profiles_ws.update, [header] + rows):
                self._load_existing_profiles() # Refresh cache after sort
                log_msg("Profiles sorted by date.", "OK")
        except (ValueError, APIError) as e:
            log_msg(f"Failed to sort profiles by date: {e}", "ERROR")
