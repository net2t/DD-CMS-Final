"""
Google Sheets Manager — DD-CMS-V3

Fixes applied (v3.0.2):
- Batch writes now actually work: all data writes are queued and flushed in bulk
- moveDimension is still per-profile (must be immediate) but data write is batched
- Duplicate fix: after every batch flush, reload nickname→row cache from sheet
- Cell notes: changed fields written as a Google Sheets note (Insert > Note) on Col B
  Format: "BEFORE:\n  FIELD: old_value\nAFTER:\n  FIELD: new_value"
- Post count preserved if new scrape returns blank (_PRESERVE_IF_BLANK includes POSTS)
- Col D in RunList = ignore/skip flag (if Col D has any value, skip that target)
- Row movement: every scraped profile moves to Row 2 regardless of data change
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

    def __init__(self, client=None, credentials_json=None, credentials_path=None, spreadsheet_url=None):
        if client is None:
            client = create_gsheets_client(credentials_json, credentials_path)

        self.client      = client
        sheet_url = (spreadsheet_url or Config.GOOGLE_SHEET_URL).strip()
        log_msg(f"Opening spreadsheet: {sheet_url[:60]}...")
        self.spreadsheet = client.open_by_url(sheet_url)

        self.profiles_ws  = self._get_or_create(Config.SHEET_PROFILES,  cols=len(Config.COLUMN_ORDER))
        self.target_ws    = self._get_or_create(Config.SHEET_TARGET,     cols=6)
        self.dashboard_ws = self._get_or_create(Config.SHEET_DASHBOARD,  cols=12)
        self.tags_ws      = self._get_sheet_if_exists(Config.SHEET_TAGS)

        self.tags_mapping                = {}
        self.existing_profiles           = {}
        self._existing_profile_rows      = {}
        self._sorted_profiles_this_run   = False

        # Batch write buffer
        self._batch_data_requests  = []   # updateCells requests (data only)
        self._batch_note_requests  = []   # updateCells requests (notes only)
        self._batch_count          = 0

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
        if not text:
            return ""
        parts = []
        for chunk in str(text).strip().upper().split('/'):
            parts.extend(w for w in chunk.split() if w)
        return "\n".join(parts) if parts else text.strip().upper()

    def _init_headers(self):
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
        """
        Reload the full nickname→row mapping from the sheet.
        Called at startup AND after every batch flush (because inserts shift rows).
        """
        try:
            nick_idx = Config.COLUMN_ORDER.index("NICK NAME") + 1
            values   = self.profiles_ws.col_values(nick_idx)
            mapping  = {}
            for i, nick in enumerate(values[1:], start=2):
                nick = (nick or "").strip()
                if nick:
                    # Keep only the first occurrence (lowest row = most recent after sort)
                    if nick.lower() not in mapping:
                        mapping[nick.lower()] = i
            self._existing_profile_rows = mapping
            # Invalidate detail cache since row numbers may have changed
            self.existing_profiles = {}
            log_msg(f"Loaded {len(mapping)} existing profile rows")
        except Exception as e:
            log_msg(f"Failed to load profile rows: {e}", "WARNING")

    def _get_existing_record(self, nickname):
        """Fetch a single profile record on-demand (cached per run)."""
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

    def _cache_update_after_move(self, moved_nick, old_row, to_row=2):
        """
        After moving `moved_nick` from old_row → to_row=2,
        shift all rows that were between to_row and old_row upward by 1.
        """
        key = (moved_nick or "").strip().lower()
        if old_row <= to_row:
            return
        # Rows 2..(old_row-1) all move down by 1 because the moved row
        # was extracted from below them and inserted above them.
        for k in list(self._existing_profile_rows):
            r = self._existing_profile_rows[k]
            if to_row <= r < old_row:
                self._existing_profile_rows[k] = r + 1
        # The moved row is now at to_row
        self._existing_profile_rows[key] = to_row
        # Invalidate cached detail for any affected rows
        self.existing_profiles.pop(key, None)

    def _cache_insert_at_top(self, nickname, row_data):
        """
        After inserting a new row at row 2, shift all existing rows down by 1.
        """
        key = (nickname or "").strip().lower()
        for k in list(self._existing_profile_rows):
            self._existing_profile_rows[k] += 1
        self._existing_profile_rows[key] = 2
        self.existing_profiles[key] = {'row': 2, 'data': row_data}

    # ── Row movement ───────────────────────────────────────────────────────────

    def _move_row_to_top(self, from_row, to_row=2):
        """Move a Profiles row to row 2 using Sheets API moveDimension."""
        if not from_row or from_row <= 1 or from_row == to_row:
            return True
        try:
            sheet_id = self.profiles_ws._properties.get('sheetId')
            if sheet_id is None:
                return False
            body = {"requests": [{"moveDimension": {
                "source": {
                    "sheetId":    sheet_id,
                    "dimension":  "ROWS",
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

    _UPPERCASE_COLS   = {"CITY", "GENDER", "MARRIED", "JOINED",
                         "LIST", "RUN MODE", "DATETIME SCRAP",
                         "LAST POST TIME", "MEH NAME", "MEH DATE"}
    _MEHFIL_MULTILINE = {"MEH NAME", "MEH LINK", "MEH DATE"}

    # These columns are preserved from the old row if the new scrape returns blank.
    # POSTS added here — if scraper misses the count, keep the last known value.
    _PRESERVE_IF_BLANK = {"POSTS", "LAST POST", "LAST POST TIME"}

    # These columns are excluded from change detection (always changing or irrelevant).
    _IGNORE_DIFF = {"ID", "NICK NAME", "JOINED", "DATETIME SCRAP",
                    "LAST POST", "LAST POST TIME", "PROFILE LINK",
                    "POST URL", "PHASE 2", "RUN MODE", "LIST"}

    def _build_row(self, profile_data):
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
        profile_data["DATETIME SCRAP"] = get_pkt_time().strftime("%Y-%m-%d %H:%M")

        if list_value:
            profile_data["LIST"] = str(list_value).strip()
        else:
            profile_data.setdefault("LIST", "")

        profile_data["RUN MODE"] = run_mode

        nick_key = (profile_data.get("NICK NAME") or "").strip().lower()
        if nick_key in self.tags_mapping:
            profile_data["TAGS"] = self.tags_mapping[nick_key]

        posts_digits = re.sub(r"\D+", "", str(profile_data.get("POSTS", "") or ""))
        try:
            posts_count = int(posts_digits) if posts_digits else None
        except Exception:
            posts_count = None
        profile_data["PHASE 2"] = "Ready" if (posts_count is not None and posts_count < 100) else "Not Eligible"

    # ── Cell Note builder ──────────────────────────────────────────────────────

    def _build_change_note(self, changed_fields, old_data, new_row):
        """
        Build a Google Sheets note string showing before/after values
        for all changed fields.

        Format (same as Insert > Note / Shift+F2):
            BEFORE:
              CITY: LAHORE
              FOLLOWERS: 120
            AFTER:
              CITY: KARACHI
              FOLLOWERS: 145
        """
        if not changed_fields:
            return ""
        lines = ["BEFORE:"]
        for col in changed_fields:
            idx = Config.COLUMN_ORDER.index(col)
            old_val = old_data[idx] if idx < len(old_data) else ""
            lines.append(f"  {col}: {old_val or '—'}")
        lines.append("AFTER:")
        for col in changed_fields:
            idx = Config.COLUMN_ORDER.index(col)
            new_val = new_row[idx]
            lines.append(f"  {col}: {new_val or '—'}")
        ts = get_pkt_time().strftime("%Y-%m-%d %H:%M")
        lines.append(f"\nUpdated: {ts}")
        return "\n".join(lines)

    # ── Batch write buffer ─────────────────────────────────────────────────────

    def _queue_row_data(self, row_num, row_data):
        """Queue a full row data write into the batch buffer."""
        sheet_id = self.profiles_ws._properties.get('sheetId')
        end_col  = len(Config.COLUMN_ORDER)
        self._batch_data_requests.append({
            'updateCells': {
                'range': {
                    'sheetId':          sheet_id,
                    'startRowIndex':    row_num - 1,
                    'endRowIndex':      row_num,
                    'startColumnIndex': 0,
                    'endColumnIndex':   end_col,
                },
                'rows': [{'values': [
                    {'userEnteredValue': {'stringValue': str(v) if v else ''}}
                    for v in row_data
                ]}],
                'fields': 'userEnteredValue',
            }
        })
        self._batch_count += 1

    def _queue_cell_note(self, row_num, col_num, note_text):
        """
        Queue a cell note write (Insert > Note) on a specific cell.
        col_num is 0-based column index.
        """
        if not note_text:
            return
        sheet_id = self.profiles_ws._properties.get('sheetId')
        self._batch_note_requests.append({
            'updateCells': {
                'range': {
                    'sheetId':          sheet_id,
                    'startRowIndex':    row_num - 1,
                    'endRowIndex':      row_num,
                    'startColumnIndex': col_num,
                    'endColumnIndex':   col_num + 1,
                },
                'rows': [{'values': [{'note': note_text}]}],
                'fields': 'note',
            }
        })

    def flush_batch(self):
        """
        Send all queued data + note writes to Sheets API in one batch call.
        After flushing, reload the nickname→row cache so row numbers stay accurate.
        """
        all_requests = self._batch_data_requests + self._batch_note_requests
        if not all_requests:
            return

        count = self._batch_count
        log_msg(f"Flushing batch ({count} profiles, {len(all_requests)} requests)...")
        try:
            self.spreadsheet.batch_update({'requests': all_requests})
            time.sleep(Config.SHEET_WRITE_DELAY)
            log_msg(f"Batch flushed OK ({count} profiles)", "OK")
        except APIError as e:
            if '429' in str(e):
                log_msg("Rate limit on batch flush — waiting 60s...", "WARNING")
                time.sleep(60)
                try:
                    self.spreadsheet.batch_update({'requests': all_requests})
                    time.sleep(Config.SHEET_WRITE_DELAY)
                    log_msg(f"Batch flushed OK after retry ({count} profiles)", "OK")
                except Exception as e2:
                    log_msg(f"Batch flush failed after retry: {e2}", "ERROR")
            else:
                log_msg(f"Batch flush API error: {e}", "ERROR")
        except Exception as e:
            log_msg(f"Batch flush failed: {e}", "ERROR")
        finally:
            self._batch_data_requests = []
            self._batch_note_requests = []
            self._batch_count         = 0
            # CRITICAL: reload cache after flush because batch inserts/moves
            # can shift row numbers that the in-memory cache no longer reflects.
            self._load_existing_profile_rows()

    def should_flush_batch(self):
        return self._batch_count > 0 and self._batch_count % Config.BATCH_SIZE == 0

    # ── Public write API ───────────────────────────────────────────────────────

    def write_profile(self, profile_data, run_mode="Target", list_value=None):
        """
        Write or update a single profile.

        Flow:
          1. Enrich (timestamp, tags, PHASE 2, LIST, RUN MODE)
          2. Build row
          3. moveDimension immediately (must be real-time to keep row order correct)
          4. Queue data write into batch buffer
          5. If fields changed → queue cell note on Col B (NICK NAME column)
          6. Return status

        The actual Sheets write happens when flush_batch() is called
        (every BATCH_SIZE profiles or at end of run).
        """
        nickname = (profile_data.get("NICK NAME") or "").strip()
        if not nickname:
            return {"status": "error", "error": "missing nickname"}

        status_raw = clean_data(profile_data.get("STATUS", ""))
        if status_raw.upper() != "VERIFIED":
            return {"status": "skipped", "reason": "non_verified"}

        self._enrich_profile(profile_data, run_mode, list_value)
        row_data = self._build_row(profile_data)
        key      = nickname.lower()

        existing = self._get_existing_record(nickname)

        # Col index for NICK NAME (Col B, 0-based = 1)
        nick_col_idx = Config.COLUMN_ORDER.index("NICK NAME")

        if existing:
            old_row  = existing['row']
            old_data = existing['data']

            # ── Detect changed fields ──────────────────────────────────────────
            changed   = []
            final_row = []
            for i, col in enumerate(Config.COLUMN_ORDER):
                old_val = old_data[i] if i < len(old_data) else ""
                new_val = row_data[i]
                # Preserve old value if scraper returned blank for important cols
                if col in self._PRESERVE_IF_BLANK and not new_val and old_val:
                    new_val = old_val
                if col not in self._IGNORE_DIFF and old_val != new_val:
                    changed.append(col)
                final_row.append(new_val)

            # ── Move row to top IMMEDIATELY (must be real-time) ────────────────
            # Every scraped profile moves to Row 2 regardless of data change.
            if old_row != 2:
                if not self._move_row_to_top(old_row, to_row=2):
                    log_msg(f"Move failed for {nickname} — skipping write", "WARNING")
                    return {"status": "error", "error": "move failed"}
                self._cache_update_after_move(key, old_row, to_row=2)

            # ── Queue data write (Row 2 after move) ────────────────────────────
            self._queue_row_data(2, final_row)

            # ── Queue cell note if fields changed ──────────────────────────────
            if changed:
                note_text = self._build_change_note(changed, old_data, final_row)
                self._queue_cell_note(2, nick_col_idx, note_text)

            # Update detail cache
            self.existing_profiles[key] = {'row': 2, 'data': final_row}

            status = "updated" if changed else "unchanged"
            log_msg(f"{'Updated' if changed else 'Refreshed'} {nickname} → queued for Row 2", "OK")
            return {"status": status, "changed_fields": changed}

        else:
            # ── New profile: INSERT immediately at Row 2 ───────────────────────
            # Insert must be immediate so row numbering stays correct for
            # subsequent moveDimension calls in this same run.
            if not self._write(self.profiles_ws.insert_row, row_data, index=2):
                return {"status": "error", "error": "insert failed"}
            self._cache_insert_at_top(nickname, row_data)
            # Note: No batch queue for new rows — insert_row already wrote the data.
            # _batch_count is NOT incremented because there's nothing to flush.
            log_msg(f"New profile {nickname} → Row 2 (inserted immediately)", "OK")
            return {"status": "new"}

    # ── Target / RunList helpers ───────────────────────────────────────────────

    def get_pending_targets(self):
        """
        Return list of pending target dicts from RunList sheet.

        Col A = NICKNAME
        Col B = STATUS  (must contain "pending")
        Col C = REMARKS
        Col D = IGNORE flag — if this cell has ANY value, skip this row entirely
        Col F = TAG / LIST value
        """
        try:
            rows = self.target_ws.get_all_values()[1:]
            result = []
            for idx, row in enumerate(rows, start=2):
                if not row or not row[0].strip():
                    continue

                # ── Col D ignore check ─────────────────────────────────────────
                col_d = (row[3] if len(row) > 3 else "").strip()
                if col_d:
                    log_msg(f"Skipping {row[0].strip()} — Col D ignore flag: {col_d}", "SKIP")
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
        _STATUS_MAP = {
            'pending':    Config.TARGET_STATUS_PENDING,
            'done':       Config.TARGET_STATUS_DONE,
            'complete':   Config.TARGET_STATUS_DONE,
            'error':      Config.TARGET_STATUS_ERROR,
            'suspended':  Config.TARGET_STATUS_ERROR,
            'unverified': Config.TARGET_STATUS_SKIP_DEL,
            'skip':       Config.TARGET_STATUS_SKIP_DEL,
            'del':        Config.TARGET_STATUS_SKIP_DEL,
        }
        norm = _STATUS_MAP.get((status or "").lower().strip(), status)
        self._write(self.target_ws.update, f"B{row_num}:C{row_num}", [[norm, remarks]])

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def update_dashboard(self, metrics):
        start_val = metrics.get("Start", "")
        end_val   = metrics.get("End",   "")
        diff_min  = ""
        try:
            if start_val and end_val:
                s = datetime.strptime(start_val, "%Y-%m-%d %H:%M")
                e = datetime.strptime(end_val,   "%Y-%m-%d %H:%M")
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
                    "sheetId":          sheet_id,
                    "startRowIndex":    1,
                    "startColumnIndex": 0,
                    "endColumnIndex":   self.profiles_ws.col_count,
                },
                "sortSpecs": [{"dimensionIndex": date_idx, "sortOrder": "DESCENDING"}],
            }}]}
            self.spreadsheet.batch_update(body)
            time.sleep(Config.SHEET_WRITE_DELAY)
            self._apply_header_format(self.profiles_ws)
            self._load_existing_profile_rows()
            self._sorted_profiles_this_run = True
            log_msg("Profiles sorted by date", "OK")
        except Exception as e:
            log_msg(f"Sort failed: {e}", "ERROR")
