"""
fix_datetime_format.py — ONE-TIME migration script
===================================================
Run this ONCE after deploying the DATETIME SCRAP format fix.

What it does:
  - Reads every row in the Profiles sheet
  - Finds the DATETIME SCRAP column (Col M, index 12)
  - Converts old format  "08-Mar-26 05:00 PM"  →  new format  "2026-03-08 17:00"
  - Writes all converted values back in one batch call
  - Does NOT touch any other column

After running this, Google Sheets sort will work correctly and most-recent
profiles will always appear at the top.

Usage:
    python fix_datetime_format.py

Requirements:
    - .env file must be present with GOOGLE_SHEET_URL and GOOGLE_CREDENTIALS_JSON
      (same credentials used by run.py)
"""

import sys
from pathlib import Path
from datetime import datetime

# ── Load project config (same as run.py does) ─────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv
load_dotenv(SCRIPT_DIR / ".env")

from config.config_common import Config
from utils.sheets_manager import create_gsheets_client
from utils.ui import log_msg


# ── Date format definitions ───────────────────────────────────────────────────

# All the old formats that may exist in the sheet from previous runs
OLD_FORMATS = [
    "%d-%b-%y %I:%M %p",   # "08-Mar-26 05:00 PM"  ← most common old format
    "%d-%b-%y %I:%M%p",    # "08-Mar-26 05:00PM"   ← variant without space
    "%d-%b-%y %H:%M",      # "08-Mar-26 17:00"     ← 24h old variant
    "%d-%b-%y",             # "08-Mar-26"            ← date only old variant
]

# The new sortable format
NEW_FORMAT = "%Y-%m-%d %H:%M"   # "2026-03-08 17:00"


def convert_date(raw):
    """
    Try to parse raw date string from old formats and return new format string.
    Returns None if already in new format or cannot be parsed.
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    # Already in new format — skip
    try:
        datetime.strptime(raw, NEW_FORMAT)
        return None   # No change needed
    except ValueError:
        pass

    # Try each old format
    for fmt in OLD_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime(NEW_FORMAT)
        except ValueError:
            continue

    # Could not parse — leave as-is
    log_msg(f"  ⚠️  Could not parse date: '{raw}' — skipping", "WARNING")
    return None


def main():
    print("=" * 60)
    print("  DATETIME SCRAP format migration")
    print("  Old: '08-Mar-26 05:00 PM'")
    print("  New: '2026-03-08 17:00'")
    print("=" * 60)

    # ── Connect to Google Sheets ───────────────────────────────────────────────
    log_msg("Connecting to Google Sheets...")
    client      = create_gsheets_client()
    spreadsheet = client.open_by_url(Config.GOOGLE_SHEET_URL)
    ws          = spreadsheet.worksheet(Config.SHEET_PROFILES)
    log_msg("Connected ✅")

    # ── Read all data ──────────────────────────────────────────────────────────
    log_msg("Reading all rows from Profiles sheet...")
    all_values = ws.get_all_values()   # list of lists, row 0 = headers

    if not all_values or len(all_values) < 2:
        log_msg("No data rows found — nothing to migrate.", "WARNING")
        return

    headers    = all_values[0]
    data_rows  = all_values[1:]        # skip header row

    # Find DATETIME SCRAP column index (0-based)
    try:
        dt_col_idx = Config.COLUMN_ORDER.index("DATETIME SCRAP")
    except ValueError:
        log_msg("DATETIME SCRAP not found in COLUMN_ORDER — aborting.", "ERROR")
        return

    log_msg(f"DATETIME SCRAP is column index {dt_col_idx} (Col {dt_col_idx + 1})")
    log_msg(f"Total data rows to check: {len(data_rows)}")

    # ── Build list of cells to update ─────────────────────────────────────────
    # We collect (row_number, new_value) pairs — only rows that need changing
    updates   = []
    converted = 0
    skipped   = 0

    for row_idx, row in enumerate(data_rows, start=2):   # start=2 because row 1 = header
        # Get current value in DATETIME SCRAP column
        old_val = row[dt_col_idx] if dt_col_idx < len(row) else ""

        new_val = convert_date(old_val)

        if new_val is not None:
            # This row needs updating
            updates.append({
                "range":  f"M{row_idx}",   # Column M = index 12 = DATETIME SCRAP
                "values": [[new_val]]
            })
            converted += 1
        else:
            skipped += 1

    log_msg(f"Rows to convert: {converted}")
    log_msg(f"Rows already correct / skipped: {skipped}")

    if not updates:
        log_msg("Nothing to update — all dates already in new format! ✅")
        return

    # ── Write all updates in one batch call ───────────────────────────────────
    log_msg(f"Writing {converted} updates to sheet (batch)...")

    # gspread batch_update sends all changes in a single API call
    ws.batch_update(updates, value_input_option="RAW")

    log_msg(f"Done! {converted} rows converted ✅")
    print()
    print("Next step: The scraper will now write dates in YYYY-MM-DD HH:MM format.")
    print("The sort at end of each run will correctly show newest profiles at top.")


if __name__ == "__main__":
    main()
