"""
Google Sheets Manager - All sheet operations
STEP-6: Nickname-based duplication, Row 2 insertion, Dashboard fixes
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound, APIError

from config import Config

def get_pkt_time():
    """Get current Pakistan time"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log_msg(msg, level="INFO"):
    """Logger"""
    ts = get_pkt_time().strftime('%H:%M:%S')
    print(f"[{ts}] [{level}] {msg}")
    import sys
    sys.stdout.flush()

def clean_data(value):
    """Clean cell data - STEP-6: Return 'BLANK' for empty values"""
    if not value:
        return "BLANK"
    
    v = str(value).strip().replace('\xa0', ' ')
    bad = {
        "No city", "Not set", "[No Posts]", "N/A", 
        "no city", "not set", "[no posts]", "n/a",
        "[No Post URL]", "[Error]", "no set", "none", "null", "no age"
    }
    
    if v in bad or not v:
        return "BLANK"
    
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
        
        # Load data - STEP-6: Index by nickname (lowercase)
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
        """Initialize headers for all sheets"""
        # ProfilesTarget
        try:
            vals = self.profiles_ws.get_all_values()
            if not vals or not vals[0] or all(not c for c in vals[0]):
                log_msg("Initializing ProfilesTarget headers...")
                self.profiles_ws.append_row(Config.COLUMN_ORDER)
        except Exception as e:
            log_msg(f"ProfilesTarget header init failed: {e}")
        
        # Target
        try:
            vals = self.target_ws.get_all_values()
            if not vals or not vals[0] or all(not c for c in vals[0]):
                log_msg("Initializing Target headers...")
                self.target_ws.append_row(["Nickname", "Status", "Remarks", "Source"])
        except Exception as e:
            log_msg(f"Target header init failed: {e}")
        
        # Dashboard
        try:
            vals = self.dashboard_ws.get_all_values()
            expected = ["Run#", "Timestamp", "Profiles", "Success", "Failed", 
                       "New", "Updated", "Unchanged", "Trigger", "Start", "End",
                       "Active", "Unverified", "Banned", "Dead"]
            if not vals or vals[0] != expected:
                self.dashboard_ws.clear()
                self.dashboard_ws.append_row(expected)
        except Exception as e:
            log_msg(f"Dashboard header init failed: {e}")
        
        # OnlineLog
        try:
            vals = self.online_log_ws.get_all_values()
            if not vals or not vals[0] or all(not c for c in vals[0]):
                log_msg("Initializing OnlineLog headers...")
                self.online_log_ws.append_row(Config.ONLINE_LOG_COLUMNS)
        except Exception as e:
            log_msg(f"OnlineLog header init failed: {e}")
    
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
                if not tag_name or tag_name == "BLANK":
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
        """Load existing profiles indexed by NICKNAME (lowercase)
        
        STEP-6: Primary match key is NICK NAME, not ID
        """
        try:
            rows = self.profiles_ws.get_all_values()[1:]  # Skip header
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME")
            
            for i, row in enumerate(rows, start=2):
                if len(row) > nick_idx:
                    nickname = row[nick_idx].strip()
                    if nickname and nickname != "BLANK":
                        key = nickname.lower()
                        self.existing_profiles[key] = {
                            'row': i,
                            'data': row
                        }
            
            log_msg(f"Loaded {len(self.existing_profiles)} existing profiles (indexed by nickname)")
        
        except Exception as e:
            log_msg(f"Failed to load existing profiles: {e}")
    
    # ==================== PROFILE OPERATIONS ====================
    
    def _compute_profile_state(self, profile_data):
        """Compute normalized PROFILE_STATE from scraper signals"""
        skip_reason = (profile_data.get('__skip_reason') or '').lower()
        status = (profile_data.get('STATUS') or '').strip()
        intro = (profile_data.get('INTRO') or '').lower()
        
        # DEAD: Profile not found, deleted, or inaccessible
        if skip_reason:
            if 'timeout' in skip_reason or 'not found' in skip_reason:
                return Config.PROFILE_STATE_DEAD
            if 'page timeout' in skip_reason:
                return Config.PROFILE_STATE_DEAD
        
        # BANNED: Account suspended by platform
        if status == 'Banned':
            return Config.PROFILE_STATE_BANNED
        if 'suspend' in intro or 'banned' in intro or 'blocked' in intro:
            return Config.PROFILE_STATE_BANNED
        
        # UNVERIFIED: Account exists but not verified
        if status == 'Unverified':
            return Config.PROFILE_STATE_UNVERIFIED
        
        # ACTIVE: Default for verified, functioning profiles
        return Config.PROFILE_STATE_ACTIVE
    
    def write_profile(self, profile_data):
        """Write profile to ProfilesTarget sheet
        
        STEP-6 Logic:
        - Duplicate check by NICKNAME (lowercase)
        - If duplicate: Update existing row + move to Row 2
        - If new: Insert at Row 2
        - Inline update format: "old_value → new_value"
        
        Args:
            profile_data (dict): Profile data with all fields
            
        Returns:
            dict: {"status": "new|updated|unchanged", "changed_fields": [...]}
        """
        nickname = (profile_data.get("NICK NAME") or "").strip()
        
        if not nickname or nickname == "BLANK":
            log_msg("Warning: Profile has no nickname, skipping", "WARNING")
            return {"status": "error", "error": "Missing nickname"}
        
        # Add scrape timestamp
        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        
        # Compute normalized PROFILE_STATE
        profile_data["PROFILE_STATE"] = self._compute_profile_state(profile_data)
        
        # Add tags if available
        tags = self.tags_mapping.get(nickname.lower())
        if tags:
            profile_data["TAGS"] = tags
        
        # Build row data with BLANK handling
        row_data = []
        for col in Config.COLUMN_ORDER:
            value = profile_data.get(col, "BLANK")
            # Clean and apply BLANK logic
            if not value or str(value).strip() == "":
                value = "BLANK"
            else:
                value = clean_data(value)
            row_data.append(value)
        
        # Lookup by nickname (primary match key)
        key = nickname.lower()
        existing = self.existing_profiles.get(key)
        
        if existing:
            # DUPLICATE FOUND: Update existing row
            old_row_num = existing['row']
            old_data = existing['data']
            
            # Detect changes with inline update format
            changed_fields = []
            updated_row = []
            
            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else "BLANK"
                new_val = row_data[i]
                
                # Skip timestamp columns from change detection
                if col in {"DATETIME SCRAP", "LAST POST", "LAST POST TIME"}:
                    updated_row.append(new_val)
                    continue
                
                if old_val != new_val:
                    changed_fields.append(col)
                    # STEP-6: Inline update format
                    updated_row.append(f"{old_val} → {new_val}")
                else:
                    updated_row.append(new_val)
            
            # Delete old row
            self.profiles_ws.delete_rows(old_row_num)
            time.sleep(Config.SHEET_WRITE_DELAY)
            
            # Insert updated row at Row 2 (after header)
            self.profiles_ws.insert_row(updated_row, index=2)
            time.sleep(Config.SHEET_WRITE_DELAY)
            
            # Update cache
            self.existing_profiles[key] = {'row': 2, 'data': updated_row}
            
            status = "updated" if changed_fields else "unchanged"
            log_msg(f"Updated {nickname} (moved to Row 2)", "OK")
            return {"status": status, "changed_fields": changed_fields}
        
        else:
            # NEW PROFILE: Insert at Row 2
            self.profiles_ws.insert_row(row_data, index=2)
            time.sleep(Config.SHEET_WRITE_DELAY)
            
            # Add to cache
            self.existing_profiles[key] = {'row': 2, 'data': row_data}
            
            log_msg(f"New profile {nickname} added at Row 2", "OK")
            return {"status": "new", "changed_fields": list(Config.COLUMN_ORDER)}
    
    def get_profile(self, nickname):
        """Fetch existing profile data by nickname
        
        Args:
            nickname (str): Profile nickname
            
        Returns:
            dict: Profile data dictionary, or None if not found
        """
        if not nickname:
            return None
            
        key = nickname.strip().lower()
        record = self.existing_profiles.get(key)
        if not record:
            return None
            
        data = record['data']
        profile_dict = {}
        for idx, col in enumerate(Config.COLUMN_ORDER):
            value = data[idx] if idx < len(data) else "BLANK"
            profile_dict[col] = value
        return profile_dict

    def create_profile(self, profile_data):
        """Create a new profile row"""
        return self.write_profile(profile_data)

    def update_profile(self, nickname, profile_data):
        """Update an existing profile row"""
        if nickname:
            profile_data = dict(profile_data)
            profile_data["NICK NAME"] = nickname
        return self.write_profile(profile_data)

    # ==================== TARGET OPERATIONS ====================
    
    def get_pending_targets(self):
        """Get pending targets from Target sheet"""
        try:
            rows = self.target_ws.get_all_values()[1:]  # Skip header
            targets = []
            
            for idx, row in enumerate(rows, start=2):
                nickname = (row[0] if len(row) > 0 else '').strip()
                status = (row[1] if len(row) > 1 else '').strip()
                source = (row[3] if len(row) > 3 else 'Target').strip() or 'Target'
                
                # Check if pending
                is_pending = (
                    not status or 
                    status == Config.TARGET_STATUS_PENDING or
                    "pending" in status.lower()
                )
                
                if nickname and is_pending:
                    targets.append({
                        'nickname': nickname,
                        'row': idx,
                        'source': source
                    })
            
            return targets
        
        except Exception as e:
            log_msg(f"Failed to get pending targets: {e}", "ERROR")
            return []
    
    def update_target_status(self, row, status, remarks):
        """Update target status"""
        try:
            # Normalize status
            lower = (status or "").lower().strip()
            if 'pending' in lower:
                status = Config.TARGET_STATUS_PENDING
            elif 'done' in lower or 'complete' in lower:
                status = Config.TARGET_STATUS_DONE
            elif 'error' in lower or 'suspended' in lower or 'unverified' in lower:
                status = Config.TARGET_STATUS_ERROR
            
            # Update with retry
            for attempt in range(3):
                try:
                    self.target_ws.update(values=[[status]], range_name=f"B{row}")
                    self.target_ws.update(values=[[remarks]], range_name=f"C{row}")
                    time.sleep(Config.SHEET_WRITE_DELAY)
                    break
                except APIError as e:
                    if '429' in str(e):
                        log_msg("API quota exceeded, waiting 60s...")
                        time.sleep(60)
                    else:
                        raise
        
        except Exception as e:
            log_msg(f"Failed to update target status: {e}", "ERROR")

    def update_runlist_status(self, row, status, remarks):
        """Backward compatible alias"""
        return self.update_target_status(row, status, remarks)

    # ==================== ONLINE LOG OPERATIONS ====================
    
    def log_online_user(self, nickname, timestamp=None):
        """Log an online user to OnlineLog sheet"""
        if timestamp is None:
            timestamp = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        
        try:
            row = [timestamp, nickname, timestamp]
            self.online_log_ws.append_row(row)
            time.sleep(Config.SHEET_WRITE_DELAY)
        except Exception as e:
            log_msg(f"Failed to log online user: {e}", "ERROR")
    
    # ==================== DASHBOARD OPERATIONS ====================
    
    def update_dashboard(self, metrics):
        """Update dashboard with run metrics
        
        STEP-6: Populate all columns with "BLANK" if missing
        """
        try:
            # Basic metrics with BLANK fallback
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
                metrics.get("Start", "BLANK"),
                metrics.get("End", "BLANK"),
            ]
            
            # STEP-6: Always populate state columns (use BLANK if missing)
            state_counts = metrics.get("state_counts", {})
            row.extend([
                state_counts.get("ACTIVE", "BLANK"),
                state_counts.get("UNVERIFIED", "BLANK"),
                state_counts.get("BANNED", "BLANK"),
                state_counts.get("DEAD", "BLANK")
            ])
            
            self.dashboard_ws.append_row(row)
            time.sleep(Config.SHEET_WRITE_DELAY)
            log_msg("Dashboard updated", "OK")
        
        except Exception as e:
            log_msg(f"Dashboard update failed: {e}", "ERROR")
    
    # ==================== HELPERS ====================
    
    def _column_letter(self, index):
        """Convert 0-based index to Excel column letter"""
        result = ""
        index += 1
        while index > 0:
            index -= 1
            result = chr(index % 26 + 65) + result
            index //= 26
        return result

    def sort_profiles_by_date(self):
        """Sort profiles sheet by DATETIME SCRAP descending
        
        STEP-6: Always sort after bulk updates
        """
        try:
            all_rows = self.profiles_ws.get_all_values()
            if len(all_rows) <= 1:
                return

            header, rows = all_rows[0], all_rows[1:]
            try:
                date_idx = header.index("DATETIME SCRAP")
            except ValueError:
                log_msg("DATETIME SCRAP column not found, skipping sort", "WARNING")
                return

            def parse_date(row):
                try:
                    value = row[date_idx] if date_idx < len(row) else ""
                    if not value or value == "BLANK":
                        return datetime.min
                    return datetime.strptime(value, "%d-%b-%y %I:%M %p")
                except Exception:
                    return datetime.min

            rows.sort(key=parse_date, reverse=True)
            self.profiles_ws.clear()
            self.profiles_ws.update([header] + rows)
            time.sleep(Config.SHEET_WRITE_DELAY)
            
            # Refresh cache after sort
            self._load_existing_profiles()
            log_msg("Profiles sorted by date", "OK")
        except Exception as e:
            log_msg(f"Failed to sort profiles by date: {e}", "ERROR")
