"""
Google Sheets Manager (Phase 1)

This module is responsible for:
- Connecting to your Google Sheet
- Ensuring required sheets + headers exist
- Writing profile rows to the Profiles sheet
- Logging online users to OnlineLog
- Updating run stats to Dashboard

Important rule:
- Keep sheet output the same (schema + values). Refactors must not change output.
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime

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
    
    return re.sub(r"\s+", " ", v)

def clean_data_preserve_newlines(value):
    """Clean cell data but preserve newline characters for multiline cells."""
    if not value:
        return ""

    v = str(value).replace('\xa0', ' ').strip()
    bad_values = {
        "No city", "Not set", "[No Posts]", "N/A",
        "no city", "not set", "[no posts]", "n/a",
        "[No Post URL]", "[Error]", "no set", "none", "null", "no age"
    }
    if v in bad_values or not v:
        return ""

    lines = [re.sub(r"\s+", " ", line).strip() for line in v.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)

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
                if isinstance(cred_data, dict):
                    pk = cred_data.get("private_key")
                    if isinstance(pk, str) and "\\n" in pk:
                        cred_data["private_key"] = pk.replace("\\n", "\n")
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
    """Manages all interactions with the Google Sheets document."""
    
    def __init__(self, client=None, credentials_json=None, credentials_path=None):
        """Initializes the SheetsManager."""
        if client is None:
            client = create_gsheets_client(
                credentials_json=credentials_json,
                credentials_path=credentials_path
            )
        
        self.client = client
        self.spreadsheet = client.open_by_url(Config.GOOGLE_SHEET_URL)
        
        # Initialize worksheets
        self.profiles_ws = self._get_or_create(Config.SHEET_PROFILES, cols=len(Config.COLUMN_ORDER))
        self.target_ws = self._get_or_create(Config.SHEET_TARGET, cols=6)
        self.dashboard_ws = self._get_or_create(Config.SHEET_DASHBOARD, cols=12)
        self.online_log_ws = self._get_or_create(Config.SHEET_ONLINE_LOG, cols=4)

        # Ensure existing sheets have expected column counts
        self._ensure_min_cols(self.dashboard_ws, 12)
        self._ensure_min_cols(self.online_log_ws, 4)
        self._ensure_min_cols(self.target_ws, 6)
        
        # Optional sheets
        self.tags_ws = self._get_sheet_if_exists(Config.SHEET_TAGS)
        
        # Load data
        self.tags_mapping = {}
        self.existing_profiles = {}
        self._existing_profile_rows = {}
        self._sorted_profiles_this_run = False
        self._writes_since_profile_reload = 0
        self._profile_reload_interval = 50
        
        self._init_headers()
        self._load_tags()
        self._load_existing_profile_rows()
        
        log_msg("Google Sheets connected successfully", "OK")

    def _maybe_reload_existing_profiles(self, force: bool = False):
        """Reload existing profiles cache occasionally to reduce expensive full-sheet reads."""
        if force:
            self._writes_since_profile_reload = 0
            self._load_existing_profile_rows()
            self.existing_profiles = {}
            return

        self._writes_since_profile_reload += 1
        if self._writes_since_profile_reload >= self._profile_reload_interval:
            self._writes_since_profile_reload = 0
            self._load_existing_profile_rows()
            self.existing_profiles = {}

    def _update_existing_profiles_cache_after_insert(self, nickname: str, inserted_row_data: list, inserted_row_num: int = 2):
        """Best-effort update of in-memory cache without a full reload."""
        try:
            key = (nickname or "").strip().lower()
            if not key:
                return

            # Inserted at row 2 means all existing cached row numbers shift down by 1.
            if inserted_row_num == 2:
                for rec in self.existing_profiles.values():
                    try:
                        rec['row'] = int(rec.get('row') or 0) + 1
                    except Exception:
                        continue

                try:
                    for k in list(self._existing_profile_rows.keys()):
                        self._existing_profile_rows[k] = int(self._existing_profile_rows[k]) + 1
                except Exception:
                    pass

            self.existing_profiles[key] = {
                'row': inserted_row_num,
                'data': inserted_row_data
            }
            self._existing_profile_rows[key] = inserted_row_num
        except Exception:
            # Cache update is opportunistic; ignore failures.
            pass

    def _update_row_mapping_after_move_to_top(self, moved_key: str, from_row: int, to_row: int = 2):
        """Update nickname->row mapping after moving one row to the top (row 2)."""
        try:
            moved_key = (moved_key or "").strip().lower()
            if not moved_key:
                return
            if not from_row or from_row <= 1 or from_row == to_row:
                self._existing_profile_rows[moved_key] = to_row
                return

            # When moving from_row -> 2, the range [2, from_row-1] shifts down by 1.
            if to_row == 2 and from_row > 2:
                for k, r in list(self._existing_profile_rows.items()):
                    try:
                        r = int(r)
                    except Exception:
                        continue
                    if 2 <= r < from_row:
                        self._existing_profile_rows[k] = r + 1

            self._existing_profile_rows[moved_key] = to_row

            # Invalidate full-row cache for anything affected.
            self.existing_profiles.pop(moved_key, None)
        except Exception:
            pass
    
    def _get_or_create(self, name, cols=20, rows=1000):
        """Safely gets a worksheet by name, creating it if it doesn't exist."""
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"Creating worksheet: {name}")
            return self.spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)

    def _ensure_min_cols(self, ws, min_cols):
        if not ws:
            return
        try:
            if ws.col_count < min_cols:
                self._perform_write_operation(ws.add_cols, min_cols - ws.col_count)
        except Exception:
            pass

    def _format_header_cell(self, text):
        if not text:
            return ""
        t = str(text).strip().upper()
        # Split on '/' and whitespace into separate lines
        parts = []
        for chunk in t.split('/'):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts.extend([p for p in chunk.split() if p])
        return "\n".join(parts) if parts else t
    
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
            self.profiles_ws: [
                ("RUN MODE" if h == "SKIP/DEL" else h)
                for h in Config.COLUMN_ORDER
            ],
            self.target_ws: ["NICKNAME", "STATUS", "REMARKS"],
            self.dashboard_ws: [
                "RUN#", "TIMESTAMP", "PROFILES", "SUCCESS", "FAILED",
                "NEW", "UPDATED", "DIFF", "UNCHANGED", "TRIGGER", "START", "END"
            ],
            self.online_log_ws: Config.ONLINE_LOG_COLUMNS
        }

        for ws, headers in sheets_to_format.items():
            if not ws:
                continue
            try:
                current_headers = ws.row_values(1)

                if ws == self.profiles_ws and current_headers:
                    meh_type_header = self._format_header_cell("MEH TYPE")
                    if meh_type_header in current_headers:
                        col_index = current_headers.index(meh_type_header) + 1
                        log_msg(
                            f"Removing obsolete Profiles column: {meh_type_header} (col {col_index})...",
                            "WARNING"
                        )
                        self._perform_write_operation(ws.delete_columns, col_index)
                        current_headers = ws.row_values(1)

                formatted_headers = [self._format_header_cell(h) for h in headers]
                if not current_headers:
                    log_msg(f"Initializing headers for '{ws.title}' sheet...")
                    ws.append_row(formatted_headers)
                    self._apply_header_format(ws)

                # If headers differ, update only the header row (do NOT clear the sheet).
                elif (current_headers[:len(formatted_headers)] if ws == self.target_ws else current_headers) != formatted_headers:
                    log_msg(
                        f"Updating header row for '{ws.title}' sheet (preserving existing data)...",
                        "WARNING"
                    )
                    end_a1 = gspread.utils.rowcol_to_a1(1, len(headers))
                    header_range = f"A1:{end_a1}"
                    self._perform_write_operation(ws.update, header_range, [formatted_headers])
                    self._apply_header_format(ws)
            except Exception as e:
                log_msg(f"Header initialization for '{ws.title}' failed: {e}", "ERROR")

    def _apply_row_format(self, ws, row_index):
        """Apply 'Quantico' font to a specific data row (font-only)."""
        try:
            row_range = f'A{row_index}:{gspread.utils.rowcol_to_a1(row_index, ws.col_count)}'
            self._perform_write_operation(
                ws.format, 
                row_range, 
                {
                    "textFormat": {
                        "fontFamily": "Quantico"
                    }
                }
            )
        except Exception as e:
            log_msg(f"Failed to apply row format for '{ws.title}' at row {row_index}: {e}", "WARNING")

    def _apply_sheet_font(self, ws, max_rows=None):
        """Apply Quantico font to a whole sheet range (fast, one call)."""
        try:
            if max_rows is None:
                max_rows = ws.row_count
            end_a1 = gspread.utils.rowcol_to_a1(max_rows, ws.col_count)
            self._perform_write_operation(
                ws.format,
                f"A1:{end_a1}",
                {"textFormat": {"fontFamily": "Quantico"}}
            )
        except Exception as e:
            log_msg(f"Failed to apply sheet font for '{ws.title}': {e}", "WARNING")

    def _apply_sheet_wrap(self, ws, wrap_strategy, max_rows=None):
        try:
            if max_rows is None:
                max_rows = ws.row_count
            end_a1 = gspread.utils.rowcol_to_a1(max_rows, ws.col_count)
            self._perform_write_operation(
                ws.format,
                f"A1:{end_a1}",
                {"wrapStrategy": wrap_strategy}
            )
        except Exception as e:
            log_msg(f"Failed to apply wrap for '{ws.title}': {e}", "WARNING")

    def finalize_formatting(self):
        """Apply final formatting at end of run.

        Speed-first: this is optional and defaults to off (Config.FINALIZE_FORMATTING).
        """
        if not getattr(Config, 'FINALIZE_FORMATTING', False):
            return

        max_rows = getattr(Config, 'FORMAT_MAX_ROWS', 500)
        max_rows = None if (isinstance(max_rows, int) and max_rows <= 0) else max_rows

        for ws in [self.profiles_ws, self.target_ws, self.dashboard_ws, self.online_log_ws]:
            if ws:
                self._apply_sheet_font(ws, max_rows=max_rows)
                self._apply_sheet_wrap(ws, "CLIP", max_rows=max_rows)
                self._apply_header_format(ws)

    def _apply_header_format(self, ws):
        """Apply 'Quantico' font to the header row (font-only)."""
        try:
            header_range = f'A1:{gspread.utils.rowcol_to_a1(1, ws.col_count)}'
            self._perform_write_operation(
                ws.format,
                header_range,
                {
                    "textFormat": {
                        "fontFamily": "Quantico",
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1}
                    }
                }
            )
        except Exception as e:
            log_msg(f"Failed to apply header format for '{ws.title}': {e}", "WARNING")
    
    def _load_tags(self):
        """Loads the tag-to-nickname mappings from the 'Tags' sheet."""
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
    
    def _load_existing_profile_rows(self):
        """Loads only nickname->row index mapping from the 'Profiles' sheet (fast)."""
        try:
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME") + 1
            col_letter = gspread.utils.rowcol_to_a1(1, nick_idx).rstrip('1')
            values = self.profiles_ws.col_values(nick_idx)
            # values includes header at index 0
            rows = values[1:] if values else []
            mapping = {}
            for i, nickname in enumerate(rows, start=2):
                nickname = (nickname or "").strip()
                if nickname:
                    mapping[nickname.lower()] = i

            self._existing_profile_rows = mapping
            log_msg(f"Loaded {len(self._existing_profile_rows)} existing profile rows")
        
        except Exception as e:
            log_msg(f"Failed to load existing profile rows: {e}")

    def _get_existing_profile_record(self, nickname: str):
        """Get existing profile record, fetching row values on-demand."""
        key = (nickname or "").strip().lower()
        if not key:
            return None

        # In-memory full record cache
        if key in self.existing_profiles:
            return self.existing_profiles[key]

        row_num = self._existing_profile_rows.get(key)
        if not row_num:
            return None

        try:
            row = self.profiles_ws.row_values(row_num)
            rec = {'row': row_num, 'data': row}
            self.existing_profiles[key] = rec
            return rec
        except Exception:
            return None

    def _move_profile_row_to_top(self, from_row: int, to_row: int = 2) -> bool:
        """Move a row within Profiles sheet using Sheets API (faster and safer than delete+insert)."""
        try:
            if not from_row or from_row <= 1 or from_row == to_row:
                return True

            sheet_id = self.profiles_ws._properties.get('sheetId')
            if sheet_id is None:
                return False

            # Google Sheets uses 0-based, endIndex is exclusive
            body = {
                "requests": [
                    {
                        "moveDimension": {
                            "source": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": from_row - 1,
                                "endIndex": from_row
                            },
                            "destinationIndex": to_row - 1
                        }
                    }
                ]
            }
            self.spreadsheet.batch_update(body)
            time.sleep(Config.SHEET_WRITE_DELAY)
            return True
        except Exception as e:
            log_msg(f"Failed to move profile row {from_row} -> {to_row}: {e}", "WARNING")
            return False
    
    # ==================== PROFILE OPERATIONS ====================

    def _perform_write_operation(self, operation, *args, **kwargs):
        """Robust wrapper for all gspread write operations with retry logic."""
        for attempt in range(3):
            try:
                operation(*args, **kwargs)
                time.sleep(Config.SHEET_WRITE_DELAY)
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
        """Computes a normalized profile state."""
        skip_reason = (profile_data.get('__skip_reason') or '').lower()
        status = (profile_data.get('STATUS') or '').strip()

        if any(reason in skip_reason for reason in ['timeout', 'not found', 'page timeout']):
            return Config.PROFILE_STATE_DEAD
        if status == 'Banned' or 'suspend' in skip_reason or 'banned' in skip_reason:
            return Config.PROFILE_STATE_BANNED
        if status == 'Unverified':
            return Config.PROFILE_STATE_UNVERIFIED
        return Config.PROFILE_STATE_ACTIVE

    def write_profile(self, profile_data, target_tag: str | None = None):
        """
        Writes a profile to the 'Profiles' sheet with duplicate handling.
        FIXED: Applies Quantico font to the written row.
        """
        nickname = (profile_data.get("NICK NAME") or "").strip()
        if not nickname:
            log_msg("Profile has no nickname, skipping write.", "WARNING")
            return {"status": "error", "error": "Missing nickname"}

        # Only VERIFIED profiles should be written to Profiles (per project requirement).
        # Keep normalization consistent with existing uppercase behavior.
        incoming_status = clean_data(profile_data.get("STATUS", ""))
        if (incoming_status or "").strip().upper() != "VERIFIED":
            return {"status": "skipped", "reason": "non_verified"}

        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")

        # Target mode: tag batch/list name into Profiles column J (index 9 in COLUMN_ORDER).
        # This is optional and does not change schema; it only changes the value written.
        if target_tag is not None:
            try:
                col_j_idx = 9
                if 0 <= col_j_idx < len(Config.COLUMN_ORDER):
                    profile_data[Config.COLUMN_ORDER[col_j_idx]] = str(target_tag).strip()
            except Exception:
                pass
        # PROFILE_STATE column was removed from the sheet schema; keep internal state only.
        profile_data["_PROFILE_STATE"] = self._compute_profile_state(profile_data)
        
        if nickname.lower() in self.tags_mapping:
            profile_data["TAGS"] = self.tags_mapping[nickname.lower()]

        posts_raw = str(profile_data.get("POSTS", "") or "")
        posts_digits = re.sub(r"\D+", "", posts_raw)
        try:
            posts_count = int(posts_digits) if posts_digits else None
        except Exception:
            posts_count = None

        if posts_count is not None and posts_count < 100:
            profile_data["PHASE 2"] = "Ready"
        else:
            profile_data["PHASE 2"] = "Not Eligible"

        uppercase_cols = {
            "CITY",
            "GENDER",
            "MARRIED",
            "STATUS",
            "JOINED",
            "SKIP/DEL",
            "DATETIME SCRAP",
            "LAST POST TIME",
            "MEH NAME",
            "MEH DATE",
        }

        mehfil_multiline_cols = {"MEH NAME", "MEH LINK", "MEH DATE"}
        row_data = []
        for col in Config.COLUMN_ORDER:
            if col in mehfil_multiline_cols:
                val = clean_data_preserve_newlines(profile_data.get(col, ""))
            else:
                val = clean_data(profile_data.get(col, ""))
            if col == "POSTS" and val:
                val = re.sub(r"\D+", "", str(val))
            if col in mehfil_multiline_cols and val and ',' in val:
                val = re.sub(r",\s*", "\n", str(val))
            if col in uppercase_cols and val:
                val = val.upper()
            row_data.append(val)
        
        key = nickname.lower()
        existing = self._get_existing_profile_record(nickname)

        if existing:
            old_row_num = existing['row']
            old_data = existing['data']
            changed_fields = []
            updated_row = []
            preserve_if_blank = {"POSTS", "LAST POST", "LAST POST TIME"}
            ignore_for_diff_only = {
                "ID",              # Col A
                "NICK NAME",       # Col B
                "JOINED",          # Col H
                "DATETIME SCRAP",  # Col M
                "LAST POST",       # Col N
                "LAST POST TIME",  # Col O
                "PROFILE LINK",    # Col Q
                "POST URL",        # Col R
                "PHASE 2",          # Col V
            }

            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else ""
                new_val = row_data[i]
                if col in preserve_if_blank and (not new_val) and old_val:
                    new_val = old_val
                if col not in {"SKIP/DEL"} and col not in ignore_for_diff_only and old_val != new_val:
                    changed_fields.append(col)
                updated_row.append(new_val)

            # Always move scraped profile to row 2 (most recent), even if unchanged.
            # Speed+correctness: moveDimension avoids out-of-range deletes and keeps sheet size stable.
            if self._move_profile_row_to_top(old_row_num, to_row=2):
                self._update_row_mapping_after_move_to_top(key, from_row=old_row_num, to_row=2)
                end_a1 = gspread.utils.rowcol_to_a1(2, len(Config.COLUMN_ORDER))
                if self._perform_write_operation(self.profiles_ws.update, f"A2:{end_a1}", [updated_row]):
                    if changed_fields:
                        log_msg(f"Updated duplicate profile {nickname} and moved to Row 2.", "OK")
                    else:
                        log_msg(f"Refreshed duplicate profile {nickname} and moved to Row 2.", "OK")
                    try:
                        excluded_note_columns = {"A", "B", "H", "L", "M", "N", "O", "Q", "R", "U", "V"}
                        note_updates = []

                        for i, col in enumerate(Config.COLUMN_ORDER):
                            old_val = old_data[i] if i < len(old_data) else ""
                            new_val = updated_row[i]

                            if old_val == new_val:
                                continue

                            col_num = i + 1
                            col_a1 = gspread.utils.rowcol_to_a1(1, col_num)
                            col_letter = re.sub(r"\d+", "", col_a1)
                            if col_letter in excluded_note_columns:
                                continue

                            note_updates.append((col_num, old_val, new_val))

                        # Batch all notes into a single API call instead of one per field
                        if note_updates:
                            sheet_id = self.profiles_ws._properties.get('sheetId')
                            requests = []
                            for col_num, old_val, new_val in note_updates:
                                requests.append({
                                    "updateCells": {
                                        "rows": [{"values": [{"note": f"Before: {old_val}\nAfter: {new_val}"}]}],
                                        "fields": "note",
                                        "start": {
                                            "sheetId": sheet_id,
                                            "rowIndex": 1,  # row 2 = index 1
                                            "columnIndex": col_num - 1
                                        }
                                    }
                                })
                            try:
                                self.spreadsheet.batch_update({"requests": requests})
                                time.sleep(Config.SHEET_WRITE_DELAY)
                            except Exception as e:
                                log_msg(f"Batch note update failed: {e}", "WARNING")
                    except Exception:
                        pass
                    self._update_existing_profiles_cache_after_insert(nickname, updated_row, inserted_row_num=2)
                    self._maybe_reload_existing_profiles()
                    if changed_fields:
                        return {"status": "updated", "changed_fields": changed_fields}
                    return {"status": "unchanged"}
            return {"status": "error", "error": "Failed to update sheet"}
        else:
            if self._perform_write_operation(self.profiles_ws.insert_row, row_data, index=2):
                log_msg(f"New profile {nickname} added at Row 2.", "OK")
                self._update_existing_profiles_cache_after_insert(nickname, row_data, inserted_row_num=2)
                self._maybe_reload_existing_profiles()
                return {"status": "new"}
            return {"status": "error", "error": "Failed to write to sheet"}

    def get_profile(self, nickname):
        """Fetches a single profile's data from the in-memory cache."""
        record = self.existing_profiles.get((nickname or "").strip().lower())
        if not record:
            return None
        return {col: (record['data'][i] if i < len(record['data']) else "") for i, col in enumerate(Config.COLUMN_ORDER)}

    # ==================== TARGET OPERATIONS ====================

    def get_pending_targets(self):
        """Retrieves all pending rows from the 'RunList' sheet."""
        try:
            rows = self.target_ws.get_all_values()[1:]
            pending_targets = []
            for idx, row in enumerate(rows, start=2):
                if not row or not row[0].strip():
                    continue
                status_text = (row[1] if len(row) > 1 else "").strip().lower()
                if "pending" not in status_text:
                    continue
                tag_val = (row[5] if len(row) > 5 else "").strip()
                pending_targets.append({
                    'nickname': row[0].strip(),
                    'row': idx,
                    'source': 'Target',
                    'tag': tag_val
                })
            return pending_targets
        except Exception as e:
            log_msg(f"Failed to get pending targets: {e}", "ERROR")
            return []

    def get_skip_nicknames(self):
        """Returns a set of nicknames to skip based on RunList SKIP column values."""
        skips = set()
        try:
            rows = self.target_ws.get_all_values()[1:]
            for row in rows:
                if len(row) < 4:
                    continue
                cell = (row[3] or "").strip()
                if not cell:
                    continue
                parts = re.split(r"[\n,]+", cell)
                for p in parts:
                    nick = p.strip()
                    if nick:
                        skips.add(nick.lower())
        except Exception:
            pass
        return skips

    def update_target_status(self, row_num, status, remarks):
        """Updates the status and remarks for a specific target."""
        status_map = {
            'pending': Config.TARGET_STATUS_PENDING,
            'done': Config.TARGET_STATUS_DONE,
            'complete': Config.TARGET_STATUS_DONE,
            'error': Config.TARGET_STATUS_ERROR,
            'suspended': Config.TARGET_STATUS_ERROR,
            'unverified': Config.TARGET_STATUS_SKIP_DEL,
            'skip': Config.TARGET_STATUS_SKIP_DEL,
            'del': Config.TARGET_STATUS_SKIP_DEL,
            'skip/del': Config.TARGET_STATUS_SKIP_DEL
        }
        normalized_status = status_map.get((status or "").lower().strip(), status)
        self._perform_write_operation(self.target_ws.update, f"B{row_num}:C{row_num}", [[normalized_status, remarks]])

    # ==================== ONLINE LOG OPERATIONS ====================

    def log_online_user(self, nickname, timestamp=None):
        """Inserts a new row at Row 2 in the 'OnlineLog' sheet."""
        ts = timestamp or get_pkt_time().strftime("%d-%b-%y %I:%M %p")
        self._perform_write_operation(self.online_log_ws.insert_row, [ts, nickname, ts, ""], index=2)

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
        if batch_no is None:
            batch_no = get_pkt_time().strftime("%Y%m%d_%H%M")
        
        rows_to_add = [[ts, nickname, ts, batch_no] for nickname in nicknames]
        log_msg(f"Logging {len(rows_to_add)} online users to the sheet with batch {batch_no}...", "INFO")
        self._perform_write_operation(self.online_log_ws.insert_rows, rows_to_add, row=2)

    # ==================== DASHBOARD OPERATIONS ====================

    def update_dashboard(self, metrics):
        """
        Inserts a summary at Row 2 in the 'Dashboard' sheet.
        FIXED: Simplified columns (removed state counts L, M, N, O).
        """
        start_val = metrics.get("Start", "")
        end_val = metrics.get("End", "")
        diff_min = ""
        try:
            if start_val and end_val:
                start_dt = datetime.strptime(start_val, "%d-%b-%y %I:%M %p")
                end_dt = datetime.strptime(end_val, "%d-%b-%y %I:%M %p")
                diff_min = str(int(round((end_dt - start_dt).total_seconds() / 60.0)))
        except Exception:
            diff_min = ""

        row = [
            metrics.get("Run Number", 1),
            metrics.get("Last Run", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
            metrics.get("Profiles Processed", 0),
            metrics.get("Success", 0),
            metrics.get("Failed", 0),
            metrics.get("New Profiles", 0),
            metrics.get("Updated Profiles", 0),
            diff_min,
            metrics.get("Unchanged Profiles", 0),
            metrics.get("Trigger", "manual"),
            start_val,
            end_val,
        ]
        if self._perform_write_operation(self.dashboard_ws.insert_row, row, index=2):
            log_msg("Dashboard updated successfully.", "OK")

    # ==================== HELPERS ====================

    def sort_profiles_by_date(self):
        """Sorts the 'Profiles' sheet by 'DATETIME SCRAP' descending."""
        if not getattr(Config, 'SORT_PROFILES_BY_DATE', True):
            return
        if self._sorted_profiles_this_run:
            return
        log_msg("Sorting profiles by date...")
        try:
            date_idx = Config.COLUMN_ORDER.index("DATETIME SCRAP")

            sheet_id = self.profiles_ws._properties.get('sheetId')
            if sheet_id is None:
                return

            # sortRange is performed server-side; far faster than reading+rewriting all rows.
            body = {
                "requests": [
                    {
                        "sortRange": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": self.profiles_ws.col_count
                            },
                            "sortSpecs": [
                                {
                                    "dimensionIndex": date_idx,
                                    "sortOrder": "DESCENDING"
                                }
                            ]
                        }
                    }
                ]
            }
            self.spreadsheet.batch_update(body)
            time.sleep(Config.SHEET_WRITE_DELAY)
            self._apply_header_format(self.profiles_ws)
            self._maybe_reload_existing_profiles(force=True)
            log_msg("Profiles sorted by date.", "OK")
            self._sorted_profiles_this_run = True
        except (ValueError, APIError) as e:
            log_msg(f"Failed to sort profiles by date: {e}", "ERROR")
