"""
Google Sheets Manager — DD-CMS-V3

Key changes from V2:
- No OnlineLog sheet (removed completely)
- Dashboard kept for run summaries only
- write_profile() updates RunList IMMEDIATELY after each profile (no batch queue)
- Col 9  = LIST     → RunList Col F value
- Col 11 = RUN MODE → "Online" / "Target"
- sort_profiles_by_date() called once at end of run
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


# ── Data Cleaning ─────────────────────────────────────────────────────────────

def clean_data(value):
    """Strip and normalize a cell value; returns empty string for junk values."""
    if not value:
        return ""
    v = str(value).strip().replace('\xa0', ' ')
    junk = {
        "No city", "Not set", "[No Posts]", "N/A", "no city", "not set",
        "[no posts]", "n/a", "[No Post URL]", "[Error]", "no set", "none",
        "null", "no age",
    }
    if v in junk:
        return ""
    return re.sub(r"\s+", " ", v)


def clean_data_preserve_newlines(value):
    """Like clean_data but keeps newlines (used for mehfil multi-line cells)."""
    if not value:
        return ""
    v = str(value).replace('\xa0', ' ').strip()
    junk = {
        "No city", "Not set", "[No Posts]", "N/A", "no city", "not set",
        "[no posts]", "n/a", "[No Post URL]", "[Error]", "no set", "none",
        "null", "no age",
    }
    if v in junk:
        return ""
    lines = [re.sub(r"\s+", " ", line).strip() for line in v.splitlines()]
    return "\n".join(l for l in lines if l)


# ── Auth ──────────────────────────────────────────────────────────────────────

def create_gsheets_client(credentials_json=None, credentials_path=None):
    """Create an authenticated gspread client."""
    log_msg("Authenticating with Google Sheets API...")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        json_src = credentials_json or Config.GOOGLE_CREDENTIALS_JSON
        path_src = credentials_path or Config.get_credentials_path()

        if json_src:
            log_msg("Using credentials from JSON env var")
            try:
                data = json.loads(json_src)
            except Exception as e:
                log_msg(f"Invalid GOOGLE_CREDENTIALS_JSON (will try credentials file instead): {e}", "WARNING")
                data = None

            if isinstance(data, dict) and data:
                pk = data.get("private_key")
                if isinstance(pk, str) and "\\n" in pk:
                    data["private_key"] = pk.replace("\\n", "\n")
                creds = Credentials.from_service_account_info(data, scopes=scope)
                return gspread.authorize(creds)

        if path_src and Path(path_src).exists():
            log_msg(f"Using credentials file: {path_src}")
            creds = Credentials.from_service_account_file(str(path_src), scopes=scope)
            return gspread.authorize(creds)

        raise ValueError("No valid Google credentials found.")

    except Exception as e:
        log_msg(f"Google Sheets auth failed: {e}", "ERROR")
        raise


# ── SheetsManager ─────────────────────────────────────────────────────────────

class SheetsManager:
    """All Google Sheets interactions for DD-CMS-V3."""

    def __init__(self, client=None, credentials_json=None, credentials_path=None):
        if client is None:
            client = create_gsheets_client(credentials_json, credentials_path)

        self.client      = client
        self.spreadsheet = client.open_by_url(Config.GOOGLE_SHEET_URL)

        # Required sheets
        self.profiles_ws  = self._get_or_create(Config.SHEET_PROFILES,  cols=len(Config.COLUMN_ORDER))
        self.target_ws    = self._get_or_create(Config.SHEET_TARGET,     cols=6)
        self.dashboard_ws = self._get_or_create(Config.SHEET_DASHBOARD,  cols=12)

        # Optional
        self.tags_ws = self._get_sheet_if_exists(Config.SHEET_TAGS)

        # In-memory caches
        self.tags_mapping       = {}          # nick_lower → tag string
        self.existing_profiles  = {}          # nick_lower → {'row': int, 'data': list}
        self._existing_profile_rows = {}      # nick_lower → row int (fast lookup)
        self._sorted_profiles_this_run = False

        self._ensure_min_cols(self.dashboard_ws, 12)
        self._ensure_min_cols(self.target_ws, 6)
        self._init_headers()
        self._load_tags()
        self._load_existing_profile_rows()

        log_msg("Google Sheets connected", "OK")

    # ── Sheet helpers ──────────────────────────────────────────────────────────

    def _get_or_create(self, name, cols=20, rows=1000):
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            log_msg(f"Creating worksheet: {name}")
            return self.spreadsheet.add_worksheet(title=name, rows=rows, cols=cols)

    def _get_sheet_if_exists(self, name):
        try:
            return self.spreadsheet.worksheet(name)
        except WorksheetNotFound:
            return None

    def _ensure_min_cols(self, ws, min_cols):
        if ws and ws.col_count < min_cols:
            try:
                self._write(ws.add_cols, min_cols - ws.col_count)
            except Exception:
                pass

    def _format_header_cell(self, text):
        """Convert header text to multi-line uppercase (words on separate lines)."""
        if not text:
            return ""
        parts = []
        for chunk in str(text).strip().upper().split('/'):
            parts.extend(w for w in chunk.split() if w)
        return "\n".join(parts) if parts else text.strip().upper()

    def _init_headers(self):
        """Ensure all sheets have correct headers."""
        sheet_headers = {
            self.profiles_ws:  [self._format_header_cell(h) for h in Config.COLUMN_ORDER],
            self.target_ws:    ["NICKNAME", "STATUS", "REMARKS"],
            self.dashboard_ws: [
                "RUN#", "TIMESTAMP", "PROFILES", "SUCCESS", "FAILED",
                "NEW", "UPDATED", "DIFF", "UNCHANGED", "TRIGGER", "START", "END",
            ],
        }
        for ws, headers in sheet_headers.items():
            if not ws:
                continue
            try:
                current = ws.row_values(1)
                if not current:
                    ws.append_row(headers)
                    self._apply_header_format(ws)
                elif current != headers:
                    end_a1 = gspread.utils.rowcol_to_a1(1, len(headers))
                    self._write(ws.update, f"A1:{end_a1}", [headers])
                    self._apply_header_format(ws)
            except Exception as e:
                log_msg(f"Header init failed for {ws.title}: {e}", "WARNING")

    def _apply_header_format(self, ws):
        """Apply white Quantico font to header row."""
        try:
            header_range = f"A1:{gspread.utils.rowcol_to_a1(1, ws.col_count)}"
            self._write(ws.format, header_range, {
                "textFormat": {
                    "fontFamily": "Quantico",
                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                }
            })
        except Exception:
            pass

    # ── Write wrapper ──────────────────────────────────────────────────────────

    def _write(self, operation, *args, **kwargs):
        """Retry wrapper for all gspread write operations."""
        for attempt in range(3):
            try:
                operation(*args, **kwargs)
                time.sleep(Config.SHEET_WRITE_DELAY)
                return True
            except APIError as e:
                if '429' in str(e):
                    wait = (attempt + 1) * 60
                    log_msg(f"Rate limit hit — waiting {wait}s...", "WARNING")
                    time.sleep(wait)
                else:
                    log_msg(f"API error: {e}", "ERROR")
                    return False
            except Exception as e:
                log_msg(f"Write error: {e}", "ERROR")
                return False
        log_msg("Write failed after 3 retries", "ERROR")
        return False

    # ── Tag loading ────────────────────────────────────────────────────────────

    def _load_tags(self):
        if not self.tags_ws:
            return
        try:
            rows = self.tags_ws.get_all_values()
            if not rows or len(rows) < 2:
                return
            headers = rows[0]
            for col_idx, tag_name in enumerate(headers):
                tag_name = clean_data(tag_name)
                if not tag_name:
                    continue
                for row in rows[1:]:
                    if col_idx < len(row):
                        nick = row[col_idx].strip()
                        if nick:
                            key = nick.lower()
                            self.tags_mapping[key] = (
                                f"{self.tags_mapping[key]}, {tag_name}"
                                if key in self.tags_mapping else tag_name
                            )
            log_msg(f"Loaded {len(self.tags_mapping)} tag mappings")
        except Exception as e:
            log_msg(f"Tags load failed: {e}", "WARNING")

    # ── Existing profile cache ─────────────────────────────────────────────────

    def _load_existing_profile_rows(self):
        """Load nickname→row mapping from Profiles sheet (nickname column only)."""
        try:
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME") + 1
            values   = self.profiles_ws.col_values(nick_idx)
            mapping  = {}
            for i, nick in enumerate(values[1:], start=2):  # skip header
                nick = (nick or "").strip()
                if nick:
                    mapping[nick.lower()] = i
            self._existing_profile_rows = mapping
            log_msg(f"Loaded {len(mapping)} existing profile rows")
        except Exception as e:
            log_msg(f"Failed to load profile rows: {e}", "WARNING")

    def _get_existing_record(self, nickname):
        """Fetch a single profile record (on-demand, cached)."""
        key = (nickname or "").strip().lower()
        if not key:
            return None
        if key in self.existing_profiles:
            return self.existing_profiles[key]
        row_num = self._existing_profile_rows.get(key)
        if not row_num:
            return None
        try:
            data = self.profiles_ws.row_values(row_num)
            rec  = {'row': row_num, 'data': data}
            self.existing_profiles[key] = rec
            return rec
        except Exception:
            return None

    def _cache_insert(self, nickname, row_data, row_num=2):
        """Update in-memory cache after inserting a new row at row_num."""
        key = (nickname or "").strip().lower()
        if not key:
            return
        # Shift existing rows down
        for k in list(self._existing_profile_rows):
            if self._existing_profile_rows[k] >= row_num:
                self._existing_profile_rows[k] += 1
        for rec in self.existing_profiles.values():
            try:
                if int(rec.get('row', 0)) >= row_num:
                    rec['row'] += 1
            except Exception:
                pass
        self._existing_profile_rows[key] = row_num
        self.existing_profiles[key] = {'row': row_num, 'data': row_data}

    def _cache_move_to_top(self, nickname, from_row, to_row=2):
        """Update cache after moving a row to the top."""
        key = (nickname or "").strip().lower()
        if not key or from_row == to_row:
            return
        if to_row == 2 and from_row > 2:
            for k, r in list(self._existing_profile_rows.items()):
                try:
                    if 2 <= int(r) < from_row:
                        self._existing_profile_rows[k] = int(r) + 1
                except Exception:
                    pass
        self._existing_profile_rows[key] = to_row
        self.existing_profiles.pop(key, None)

    # ── Row movement ───────────────────────────────────────────────────────────

    def _move_row_to_top(self, from_row, to_row=2):
        """Move a Profiles row using Sheets API moveDimension (no delete/insert)."""
        if not from_row or from_row <= 1 or from_row == to_row:
            return True
        try:
            sheet_id = self.profiles_ws._properties.get('sheetId')
            if sheet_id is None:
                return False
            body = {"requests": [{"moveDimension": {
                "source": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": from_row - 1,
                    "endIndex":   from_row,
                },
                "destinationIndex": to_row - 1,
            }}]}
            self.spreadsheet.batch_update(body)
            time.sleep(Config.SHEET_WRITE_DELAY)
            return True
        except Exception as e:
            log_msg(f"Failed to move row {from_row}→{to_row}: {e}", "WARNING")
            return False

    # ── Row data builder ───────────────────────────────────────────────────────

    _UPPERCASE_COLS       = {"CITY", "GENDER", "MARRIED", "JOINED",
                             "LIST", "RUN MODE", "DATETIME SCRAP",
                             "LAST POST TIME", "MEH NAME", "MEH DATE"}
    _MEHFIL_MULTILINE     = {"MEH NAME", "MEH LINK", "MEH DATE"}
    _PRESERVE_IF_BLANK    = {"POSTS", "LAST POST", "LAST POST TIME"}
    _IGNORE_DIFF          = {"ID", "NICK NAME", "JOINED", "DATETIME SCRAP",
                             "LAST POST", "LAST POST TIME", "PROFILE LINK",
                             "POST URL", "PHASE 2"}

    def _build_row(self, profile_data):
        """Build a list of cell values aligned to Config.COLUMN_ORDER."""
        row = []
        for col in Config.COLUMN_ORDER:
            if col in self._MEHFIL_MULTILINE:
                val = clean_data_preserve_newlines(profile_data.get(col, ""))
            else:
                val = clean_data(profile_data.get(col, ""))
            if col == "POSTS" and val:
                val = re.sub(r"\D+", "", str(val))
            if col in self._MEHFIL_MULTILINE and val and ',' in val:
                val = re.sub(r",\s*", "\n", str(val))
            if col in self._UPPERCASE_COLS and val:
                val = val.upper()
            row.append(val)
        return row

    def _enrich_profile(self, profile_data, run_mode, list_value=None):
        """
        Stamp timestamp, tags, PHASE 2, LIST, and RUN MODE onto profile_data in-place.

        Args:
            profile_data: dict of scraped values
            run_mode:     "Online" or "Target"
            list_value:   RunList Col F value (Target mode) or None (Online mode)
        """
        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%d-%b-%y %I:%M %p")

        # Col 9 — LIST
        if list_value:
            profile_data["LIST"] = str(list_value).strip()
        else:
            profile_data.setdefault("LIST", "")

        # Col 11 — RUN MODE
        profile_data["RUN MODE"] = run_mode

        # Tags
        nick_key = (profile_data.get("NICK NAME") or "").strip().lower()
        if nick_key in self.tags_mapping:
            profile_data["TAGS"] = self.tags_mapping[nick_key]

        # PHASE 2 eligibility
        posts_digits = re.sub(r"\D+", "", str(profile_data.get("POSTS", "") or ""))
        try:
            posts_count = int(posts_digits) if posts_digits else None
        except Exception:
            posts_count = None
        profile_data["PHASE 2"] = "Ready" if (posts_count is not None and posts_count < 100) else "Not Eligible"

    # ── Public write API ───────────────────────────────────────────────────────

    def write_profile(self, profile_data, run_mode="Target", list_value=None):
        """
        Write or update a single profile immediately.

        Flow:
          1. Enrich (timestamp, tags, PHASE 2, LIST, RUN MODE)
          2. Build row
          3. If duplicate → move to row 2, update data
          4. If new       → insert at row 2
          5. Return status dict

        Args:
            profile_data: scraped profile dict
            run_mode:     "Online" or "Target"
            list_value:   RunList Col F value (Target mode only)

        Returns:
            dict with key 'status': 'new' | 'updated' | 'unchanged' | 'skipped' | 'error'
        """
        nickname = (profile_data.get("NICK NAME") or "").strip()
        if not nickname:
            return {"status": "error", "error": "missing nickname"}

        # Only VERIFIED profiles go to the Profiles sheet
        status_raw = clean_data(profile_data.get("STATUS", ""))
        if status_raw.upper() != "VERIFIED":
            return {"status": "skipped", "reason": "non_verified"}

        self._enrich_profile(profile_data, run_mode, list_value)
        row_data = self._build_row(profile_data)
        key      = nickname.lower()

        existing = self._get_existing_record(nickname)

        if existing:
            old_row   = existing['row']
            old_data  = existing['data']
            changed   = []
            new_row   = []

            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else ""
                new_val = row_data[i]
                # Keep old non-blank value if new scrape returned blank for these cols
                if col in self._PRESERVE_IF_BLANK and not new_val and old_val:
                    new_val = old_val
                if col not in self._IGNORE_DIFF and old_val != new_val:
                    changed.append(col)
                new_row.append(new_val)

            # Always move to row 2 (most recently scraped at top)
            if not self._move_row_to_top(old_row, to_row=2):
                return {"status": "error", "error": "move failed"}

            self._cache_move_to_top(key, from_row=old_row, to_row=2)
            end_a1 = gspread.utils.rowcol_to_a1(2, len(Config.COLUMN_ORDER))

            if not self._write(self.profiles_ws.update, f"A2:{end_a1}", [new_row]):
                return {"status": "error", "error": "update failed"}

            self.existing_profiles[key] = {'row': 2, 'data': new_row}
            self._existing_profile_rows[key] = 2
            log_msg(f"{'Updated' if changed else 'Refreshed'} {nickname} → Row 2", "OK")
            return {"status": "updated" if changed else "unchanged", "changed_fields": changed}

        else:
            if not self._write(self.profiles_ws.insert_row, row_data, index=2):
                return {"status": "error", "error": "insert failed"}
            self._cache_insert(nickname, row_data, row_num=2)
            log_msg(f"New profile {nickname} → Row 2", "OK")
            return {"status": "new"}

    # ── Target / RunList helpers ───────────────────────────────────────────────

    def get_pending_targets(self):
        """Return list of pending target dicts from RunList sheet."""
        try:
            rows = self.target_ws.get_all_values()[1:]
            result = []
            for idx, row in enumerate(rows, start=2):
                if not row or not row[0].strip():
                    continue
                status = (row[1] if len(row) > 1 else "").strip().lower()
                if "pending" not in status:
                    continue
                tag_val = (row[5] if len(row) > 5 else "").strip()
                result.append({
                    'nickname': row[0].strip(),
                    'row':      idx,
                    'source':   'Target',
                    'tag':      tag_val,
                })
            return result
        except Exception as e:
            log_msg(f"Failed to get pending targets: {e}", "ERROR")
            return []

    def update_target_status(self, row_num, status, remarks):
        """Update a single RunList row's status + remarks immediately."""
        _STATUS_MAP = {
            'pending':   Config.TARGET_STATUS_PENDING,
            'done':      Config.TARGET_STATUS_DONE,
            'complete':  Config.TARGET_STATUS_DONE,
            'error':     Config.TARGET_STATUS_ERROR,
            'suspended': Config.TARGET_STATUS_ERROR,
            'unverified':Config.TARGET_STATUS_SKIP_DEL,
            'skip':      Config.TARGET_STATUS_SKIP_DEL,
            'del':       Config.TARGET_STATUS_SKIP_DEL,
        }
        norm = _STATUS_MAP.get((status or "").lower().strip(), status)
        self._write(self.target_ws.update, f"B{row_num}:C{row_num}", [[norm, remarks]])

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def update_dashboard(self, metrics):
        """Insert one summary row at Row 2 of Dashboard sheet."""
        start_val = metrics.get("Start", "")
        end_val   = metrics.get("End",   "")
        diff_min  = ""
        try:
            if start_val and end_val:
                s = datetime.strptime(start_val, "%d-%b-%y %I:%M %p")
                e = datetime.strptime(end_val,   "%d-%b-%y %I:%M %p")
                diff_min = str(int(round((e - s).total_seconds() / 60)))
        except Exception:
            pass

        row = [
            metrics.get("Run Number",          1),
            metrics.get("Last Run", get_pkt_time().strftime("%d-%b-%y %I:%M %p")),
            metrics.get("Profiles Processed",   0),
            metrics.get("Success",              0),
            metrics.get("Failed",               0),
            metrics.get("New Profiles",         0),
            metrics.get("Updated Profiles",     0),
            diff_min,
            metrics.get("Unchanged Profiles",   0),
            metrics.get("Trigger",        "manual"),
            start_val,
            end_val,
        ]
        if self._write(self.dashboard_ws.insert_row, row, index=2):
            log_msg("Dashboard updated", "OK")

    # ── Sort ──────────────────────────────────────────────────────────────────

    def sort_profiles_by_date(self):
        """Sort Profiles sheet by DATETIME SCRAP (col 12) descending — one API call."""
        if not Config.SORT_PROFILES_BY_DATE or self._sorted_profiles_this_run:
            return
        log_msg("Sorting profiles by date...")
        try:
            date_idx = Config.COLUMN_ORDER.index("DATETIME SCRAP")
            sheet_id = self.profiles_ws._properties.get('sheetId')
            if sheet_id is None:
                return
            body = {"requests": [{"sortRange": {
                "range": {
                    "sheetId":         sheet_id,
                    "startRowIndex":   1,
                    "startColumnIndex":0,
                    "endColumnIndex":  self.profiles_ws.col_count,
                },
                "sortSpecs": [{"dimensionIndex": date_idx, "sortOrder": "DESCENDING"}],
            }}]}
            self.spreadsheet.batch_update(body)
            time.sleep(Config.SHEET_WRITE_DELAY)
            self._apply_header_format(self.profiles_ws)
            # Reload cache since row numbers changed
            self._load_existing_profile_rows()
            self.existing_profiles = {}
            self._sorted_profiles_this_run = True
            log_msg("Profiles sorted by date", "OK")
        except Exception as e:
            log_msg(f"Sort failed: {e}", "ERROR")
