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
    """
    Manages all interactions with the Google Sheets document.

    This class acts as a high-level API for all sheet-related operations. It handles
    authentication, worksheet creation, header initialization, and provides methods
    for reading and writing data in a structured way. It also contains the core logic
    for caching existing profiles to avoid redundant reads and for handling duplicate
    entries based on nicknames.
    """
    
    def __init__(self, client=None, credentials_json=None, credentials_path=None):
        """
        Initializes the SheetsManager.

        Sets up the connection to Google Sheets, gets or creates all required
        worksheets, and pre-loads caches for existing profiles and tags to
        optimize performance during the run.
        """
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
        self.online_log_ws = self._get_or_create(Config.SHEET_ONLINE_LOG, cols=4)
        
        # Optional sheets
        self.tags_ws = self._get_sheet_if_exists(Config.SHEET_TAGS)
        
        # Load data
        self.tags_mapping = {}
        self.existing_profiles = {}  # {nickname_lower: {row, data}}
        self.new_profiles_buffer = []
        
        self._init_headers()
        self._load_tags()
        self._load_existing_profiles()
        
        log_msg("Google Sheets connected successfully", "OK")
    
    def _get_or_create(self, name, cols=20, rows=1000):
        """Safely gets a worksheet by name, creating it if it doesn't exist."""
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"Creating worksheet: {name}")
            return self.spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)
    
    def _get_sheet_if_exists(self, name):
        """Safely gets a worksheet by name, returning None if it doesn't exist."""
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
        """
        Loads the tag-to-nickname mappings from the 'Tags' sheet.

        This creates an in-memory dictionary that maps a lowercase nickname to a
        comma-separated string of tags, allowing for quick enrichment of profile data.
        """
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
        """
        Loads all existing profiles from the 'Profiles' sheet into an in-memory cache.

        The cache is a dictionary where the key is the lowercase nickname and the
        value contains the row number and the full row data. This is the core
        mechanism for the nickname-based duplicate detection.
        """
        try:
            rows = self.profiles_ws.get_all_values()[1:]  # Skip header
            id_idx = Config.COLUMN_ORDER.index("ID")
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME")
            
            for i, row in enumerate(rows, start=2):
                if len(row) > max(id_idx, nick_idx):
                    # Create keys for both ID and nickname matching
                    id_val = row[id_idx].strip() if len(row) > id_idx else ""
                    nickname = row[nick_idx].strip() if len(row) > nick_idx else ""
                    
                    # Use nickname as primary key, but also store ID for matching
                    if nickname:
                        key = nickname.lower()
                        self.existing_profiles[key] = {
                            'row': i,
                            'data': row,
                            'id': id_val
                        }
                    elif id_val:  # If no nickname but ID exists, use ID as key
                        key = f"id_{id_val}"
                        self.existing_profiles[key] = {
                            'row': i,
                            'data': row,
                            'id': id_val
                        }
            
            log_msg(f"Loaded {len(self.existing_profiles)} existing profiles (indexed by nickname/ID)")
        
        except Exception as e:
            log_msg(f"Failed to load existing profiles: {e}")
    
    # ==================== PROFILE OPERATIONS ====================

    def _perform_write_operation(self, operation, *args, **kwargs):
        """
        A robust wrapper for all gspread write operations.

        This method automatically handles the Google Sheets API's rate limits (429 errors)
        by implementing a retry mechanism with an exponential backoff. This makes all
        write actions more resilient to temporary API issues.

        Args:
            operation: The gspread worksheet method to call (e.g., `ws.update`).
            *args: Positional arguments for the operation.
            **kwargs: Keyword arguments for the operation.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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

    def _strip_status_symbols(self, value):
        """Remove any existing status symbols from a string."""
        if not value:
            return ""
        for symbol in ["🔴", "🆕", "🟢"]:
            value = value.replace(symbol, "")
        return value.strip()

    def _format_status_with_symbol(self, value, symbol):
        """Attach the specified symbol to the status text."""
        text = self._strip_status_symbols(value)
        if not text:
            return symbol
        return f"{symbol} {text}"

    def _strip_status_symbols(self, value):
        """Remove status symbols from a string."""
        if not value:
            return ""
        for symbol in ["🔴", "🆕", "🟢"]:
            value = value.replace(symbol, "")
        return value.strip()

    def _format_status_with_symbol(self, value, symbol):
        """Attach a status symbol to the text."""
        text = self._strip_status_symbols(value)
        if not text:
            return symbol
        return f"{symbol} {text}"

    def _compute_profile_state(self, profile_data):
        """
        Computes a normalized profile state based on various scraped data points.

        This centralizes the logic for determining if a profile is ACTIVE, BANNED,
        UNVERIFIED, or DEAD, making the state logic consistent across the application.

        Args:
            profile_data (dict): The raw scraped profile data.

        Returns:
            str: The normalized profile state (e.g., 'ACTIVE').
        """
        skip_reason = (profile_data.get('__skip_reason') or '').lower()
        status = (profile_data.get('STATUS') or '').strip()

        if any(reason in skip_reason for reason in ['timeout', 'not found', 'page timeout']):
            return Config.PROFILE_STATE_DEAD
        if status == 'Banned':
            return Config.PROFILE_STATE_BANNED
        if status == 'Unverified':
            return Config.PROFILE_STATE_UNVERIFIED
        return Config.PROFILE_STATE_ACTIVE

    def write_profile(self, profile_data):
        """
        Writes a profile to the 'Profiles' sheet with advanced duplicate handling.
        
        - Matches by ID (Col A) or nickname (Col B)
        - New profiles are inserted at Row 2.
        - Updated profiles have their old values moved to cell notes with highlighting.
        - All write operations are batched to avoid API rate limits.
        """
        nickname = (profile_data.get("NICK NAME") or "").strip()
        profile_id = (profile_data.get("ID") or "").strip()
        
        if not nickname and not profile_id:
            log_msg("Profile has no nickname or ID, skipping write.", "WARNING")
            return {"status": "error", "error": "Missing nickname and ID"}

        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        profile_data["PROFILE_STATE"] = self._compute_profile_state(profile_data)
        if nickname.lower() in self.tags_mapping:
            profile_data["TAGS"] = self.tags_mapping[nickname.lower()]

        row_data = [clean_data(profile_data.get(col, "")) for col in Config.COLUMN_ORDER]

        status_idx = Config.COLUMN_ORDER.index("STATUS")
        icons_idx = Config.COLUMN_ORDER.index("ICONS / SYMBOLS (QUICK SCAN)")
        
        # Try to find existing profile by nickname or ID
        existing = None
        if nickname:
            key = nickname.lower()
            existing = self.existing_profiles.get(key)
        
        if not existing and profile_id:
            key = f"id_{profile_id}"
            existing = self.existing_profiles.get(key)

        if existing:
            old_row_num = existing['row']
            old_data = existing['data']
            changed_fields = []
            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else ""
                new_val = row_data[i]
                if col in {"DATETIME SCRAP", "SOURCE", "ICONS / SYMBOLS (QUICK SCAN)"}:
                    continue

                compare_old = self._strip_status_symbols(old_val) if col == "STATUS" else old_val
                compare_new = self._strip_status_symbols(new_val) if col == "STATUS" else new_val

                if compare_old != compare_new:
                    changed_fields.append(col)

            if not changed_fields:
                icons_symbol = "🟢"
                row_data[status_idx] = self._format_status_with_symbol(row_data[status_idx], icons_symbol)
                row_data[icons_idx] = icons_symbol
                if self._perform_batch_update(self.profiles_ws, old_row_num, row_data, []):
                    log_msg(f"Profile {nickname or profile_id} unchanged, timestamp refreshed at Row {old_row_num}.", "OK")
                    self.existing_profiles[key]['data'] = row_data
                    self._move_row_to_top(old_row_num)
                    return {"status": "unchanged"}
                return {"status": "error", "error": "Failed to update sheet"}

            icons_symbol = "🔴"
            row_data[status_idx] = self._format_status_with_symbol(row_data[status_idx], icons_symbol)
            row_data[icons_idx] = icons_symbol
            if self._perform_batch_update(self.profiles_ws, old_row_num, row_data, []):
                log_msg(f"Updated profile {nickname or profile_id} at Row {old_row_num}.", "OK")
                self.existing_profiles[key]['data'] = row_data  # Update cache
                self._move_row_to_top(old_row_num)
                return {"status": "updated", "changed_fields": changed_fields}
            return {"status": "error", "error": "Failed to update sheet"}
        else:
            icons_symbol = "🆕"
            row_data[status_idx] = self._format_status_with_symbol(row_data[status_idx], icons_symbol)
            row_data[icons_idx] = icons_symbol
            self.new_profiles_buffer.append(row_data)
            log_msg(f"New profile {nickname or profile_id} added to buffer.", "OK")
            return {"status": "new"}

    def get_profile(self, nickname):
        """
        Fetches a single profile's data from the in-memory cache.

        Args:
            nickname (str): The nickname of the profile to retrieve.

        Returns:
            dict or None: A dictionary of the profile data, or None if not found.
        """
        record = self.existing_profiles.get((nickname or "").strip().lower())
        if not record:
            return None
        return {col: (record['data'][i] if i < len(record['data']) else "") for i, col in enumerate(Config.COLUMN_ORDER)}


    # ==================== TARGET OPERATIONS ====================

    def get_pending_targets(self):
        """
        Retrieves all rows from the 'RunList' sheet that are marked as pending.

        This is used in 'target' mode to build the queue of profiles to be scraped.

        Returns:
            list[dict]: A list of target dictionaries, each containing the nickname,
                        row number, and source.
        """
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
        """
        Updates the status and remarks for a specific target in the 'RunList' sheet.

        Args:
            row_num (int): The row number of the target to update.
            status (str): The new status (e.g., 'Done', 'Error').
            remarks (str): Any relevant remarks about the scraping attempt.
        """
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

    def batch_log_online_users(self, nicknames, timestamp=None, batch_no=None):
        """
        Appends multiple rows to the 'OnlineLog' sheet in a single batch operation.

        Args:
            nicknames (list[str]): A list of nicknames to log.
            timestamp (str, optional): The timestamp for all entries. Defaults to now.
            batch_no (str, optional): The batch number for all entries. Defaults to generated.
        """
        if not nicknames:
            return
        
        ts = timestamp or get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        # Generate batch number if not provided (format: YYYYMMDD_HHMM)
        if batch_no is None:
            batch_no = get_pkt_time().strftime("%Y%m%d_%H%M")
        
        rows_to_add = [[ts, nickname, ts, batch_no] for nickname in nicknames]
        
        log_msg(f"Logging {len(rows_to_add)} online users to the sheet with batch {batch_no}...", "INFO")
        self._perform_write_operation(self.online_log_ws.append_rows, rows_to_add)

    # ==================== DASHBOARD OPERATIONS ====================

    def update_dashboard(self, metrics):
        """
        Appends a summary of a scraper run to the 'Dashboard' sheet.

        Args:
            metrics (dict): A dictionary containing the statistics of the completed run.
        """
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
        if self._perform_write_operation(self.dashboard_ws.insert_row, row, 2):
            log_msg("Dashboard updated successfully.", "OK")

    # ==================== HELPERS ====================

    def flush_new_profiles(self):
        """Writes all new profiles from the buffer to the sheet in a single batch."""
        if not self.new_profiles_buffer:
            return
        
        log_msg(f"Writing {len(self.new_profiles_buffer)} new profiles to the sheet...", "INFO")
        if self._perform_write_operation(self.profiles_ws.insert_rows, self.new_profiles_buffer, row=2):
            self.new_profiles_buffer.clear()
            self._load_existing_profiles() # Refresh cache after structural change
            log_msg("New profiles flushed successfully.", "OK")
        else:
            log_msg("Failed to flush new profiles.", "ERROR")

    def _perform_batch_update(self, ws, row_num, row_data, notes):
        """Performs a batch update for a row's values and notes in a single API call."""
        try:
            # Update the row values directly
            update_range = f'A{row_num}:{gspread.utils.rowcol_to_a1(row_num, len(row_data))}'
            self._perform_write_operation(ws.update, update_range, [row_data])

            # Update notes for changed cells
            if notes:
                note_payload = []
                for note in notes:
                    note_payload.append({
                        'range': note['range'],
                        'values': [[note['note']]]
                    })
                self._perform_write_operation(ws.batch_update, note_payload, value_input_option='USER_ENTERED')

            return True
        except Exception as e:
            log_msg(f"Batch update for row {row_num} failed: {e}", "ERROR")
            return False

    def _highlight_changed_cells(self, row_num, changed_fields):
        """Highlight changed cells with background color."""
        try:
            for field in changed_fields:
                if field in Config.COLUMN_ORDER:
                    col_idx = Config.COLUMN_ORDER.index(field) + 1
                    cell_range = gspread.utils.rowcol_to_a1(row_num, col_idx)
                    
                    # Apply yellow background highlight
                    self.profiles_ws.format(cell_range, {
                        "backgroundColor": {
                            "red": 1.0,
                            "green": 1.0,
                            "blue": 0.8
                        }
                    })
        except Exception as e:
            log_msg(f"Failed to highlight changed cells: {e}", "WARNING")

    def _move_row_to_top(self, row_num):
        """Move a row to the top (Row 2) of the sheet."""
        try:
            # Get the row data
            row_data = self.profiles_ws.row_values(row_num)
            
            # Delete the original row
            self.profiles_ws.delete_rows(row_num)
            
            # Insert at Row 2 (below header)
            self.profiles_ws.insert_row(row_data, 2)
            
            # Update cache
            self._load_existing_profiles()
            
        except Exception as e:
            log_msg(f"Failed to move row to top: {e}", "WARNING")

    def format_all_sheets(self):
        """Applies 'Quantico' font to all sheets in the spreadsheet."""
        log_msg("Applying 'Quantico' font to all sheets...", "INFO")
        
        all_worksheets = [
            self.profiles_ws, self.target_ws, self.dashboard_ws, 
            self.online_log_ws
        ]
        
        # Add tags sheet if it exists
        if self.tags_ws:
            all_worksheets.append(self.tags_ws)
        
        for ws in all_worksheets:
            if not ws:
                continue
                
            try:
                # Get the current number of rows and columns
                row_count = ws.row_count
                col_count = ws.col_count
                if row_count <= 1:
                    continue

                # Define the range for all data rows (excluding the header)
                data_range = f'A2:{gspread.utils.rowcol_to_a1(row_count, col_count)}'

                # Create the format request
                request = {
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 1,  # Starts after the header
                            "endRowIndex": row_count
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "fontFamily": "Quantico",
                                    "bold": False
                                }
                            }
                        },
                        "fields": "userEnteredFormat.textFormat"
                    }
                }
                self.spreadsheet.batch_update({'requests': [request]})
                log_msg(f"Font formatting applied to '{ws.title}' sheet.", "OK")
                
            except Exception as e:
                log_msg(f"Failed to apply sheet-wide format for '{ws.title}': {e}", "WARNING")

    def format_profile_sheet(self):
        """Applies 'Quantico' font to the entire data range of the profiles sheet."""
        log_msg("Applying 'Quantico' font to the entire sheet...", "INFO")
        try:
            # Get the current number of rows and columns
            row_count = self.profiles_ws.row_count
            col_count = self.profiles_ws.col_count
            if row_count <= 1:
                return

            # Define the range for all data rows (excluding the header)
            data_range = f'A2:{gspread.utils.rowcol_to_a1(row_count, col_count)}'

            # Create the format request
            request = {
                "repeatCell": {
                    "range": {
                        "sheetId": self.profiles_ws.id,
                        "startRowIndex": 1,  # Starts after the header
                        "endRowIndex": row_count
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "fontFamily": "Quantico",
                                "bold": False
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat"
                }
            }
            self.spreadsheet.batch_update({'requests': [request]})
            log_msg("Font formatting applied successfully.", "OK")
        except Exception as e:
            log_msg(f"Failed to apply sheet-wide format: {e}", "WARNING")

    def sort_profiles_by_date(self):
        """
        Sorts the entire 'Profiles' sheet by the 'DATETIME SCRAP' column in descending order.

        This is typically called at the end of a run to ensure the most recently
        scraped or updated profiles are always at the top of the sheet.
        After sorting, it refreshes the local profile cache to ensure row numbers are correct.
        """
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
