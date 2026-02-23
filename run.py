"""
DD-CMS-V3 — Main Entry Point
─────────────────────────────
Usage (command line):
    python run.py online              → run online mode once (manual)
    python run.py target              → run target mode once (manual)
    python run.py online --limit 20   → online mode, max 20 profiles
    python run.py target --limit 10   → target mode, max 10 profiles
    python run.py scheduler           → auto-scheduler (online every 15 min, no-overlap)

Features:
  - Per-run overlap lock (a second run won't start if one is already running)
  - Online mode auto-scheduler: runs every 15 minutes, skips if still running
  - Immediate per-profile sheet writes (no batch queue)
  - Profiles sorted by DATETIME SCRAP at end of each run
  - Dashboard updated with run summary
  - Logs written to logs/ folder

Lock System:
  A lock file (run.lock) is created at start and deleted at finish.
  If a run crashes, delete run.lock manually before the next run.
"""

import sys
import os
import time
import argparse
import signal
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── Add project root to sys.path ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from config.config_common import Config
from core.run_context import RunContext
from phases.phase_profile import run as run_phase
from utils.ui import (
    log_msg, print_header, print_summary, print_important_events,
    init_run_logger, close_run_logger, get_pkt_time,
)

# ── Lock file location ────────────────────────────────────────────────────────
LOCK_FILE   = SCRIPT_DIR / "run.lock"
_run_count  = 0         # tracks how many automated runs have happened this session


# ══════════════════════════════════════════════════════════════════════════════
#  Lock helpers
# ══════════════════════════════════════════════════════════════════════════════

def _is_locked() -> bool:
    """Return True if a run is already in progress."""
    return LOCK_FILE.exists()


def _acquire_lock(mode: str) -> bool:
    """Create the lock file with mode and PID. Return False if already locked."""
    if _is_locked():
        try:
            info = LOCK_FILE.read_text(encoding="utf-8").strip()
            log_msg(f"Another run is active: {info} — skipping", "WARNING")
        except Exception:
            log_msg("Lock file exists — another run is active. Skipping.", "WARNING")
        return False
    try:
        LOCK_FILE.write_text(
            f"mode={mode} pid={os.getpid()} started={get_pkt_time().strftime('%d-%b-%y %H:%M:%S')}",
            encoding="utf-8",
        )
        return True
    except Exception as e:
        log_msg(f"Could not create lock file: {e}", "WARNING")
        return True  # allow run even if lock file can't be written


def _release_lock():
    """Remove the lock file."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception as e:
        log_msg(f"Could not remove lock file: {e}", "WARNING")


# ══════════════════════════════════════════════════════════════════════════════
#  Single run
# ══════════════════════════════════════════════════════════════════════════════

def do_run(mode: str, max_profiles: int = 0) -> dict:
    """
    Execute one full scraping run (online or target mode).

    Returns stats dict.
    """
    global _run_count
    _run_count += 1

    mode = mode.lower().strip()
    assert mode in ("online", "target"), f"Unknown mode: {mode}"

    init_run_logger(mode)
    print_header("DD-CMS-V3", Config.SCRIPT_VERSION)
    log_msg(f"Run #{_run_count} | Mode: {mode.upper()} | MaxProfiles: {max_profiles or 'unlimited'}")

    # Validate config
    Config.validate()

    start_time = get_pkt_time()
    context    = RunContext()
    stats      = {}

    try:
        # ── Start browser & login ──────────────────────────────────────────────
        driver = context.start_browser()
        if not driver:
            log_msg("Browser failed to start — aborting", "ERROR")
            return {}

        if not context.login():
            log_msg("Login failed — aborting", "ERROR")
            context.close()
            return {}

        # ── Run the phase ──────────────────────────────────────────────────────
        stats, sheets = run_phase(context, mode=mode, max_profiles=max_profiles)

        # ── Sort profiles by date (once at end) ────────────────────────────────
        if sheets:
            try:
                sheets.sort_profiles_by_date()
            except Exception as e:
                log_msg(f"Sort failed: {e}", "WARNING")

        # ── Update dashboard ───────────────────────────────────────────────────
        if sheets:
            end_time = get_pkt_time()
            try:
                sheets.update_dashboard({
                    "Run Number":          _run_count,
                    "Last Run":            end_time.strftime("%d-%b-%y %I:%M %p"),
                    "Profiles Processed":  stats.get("processed", 0),
                    "Success":             stats.get("success", 0),
                    "Failed":              stats.get("failed", 0),
                    "New Profiles":        stats.get("new", 0),
                    "Updated Profiles":    stats.get("updated", 0),
                    "Unchanged Profiles":  stats.get("unchanged", 0),
                    "Trigger":             "manual" if _run_count == 1 and mode == "target" else "auto",
                    "Start":               start_time.strftime("%d-%b-%y %I:%M %p"),
                    "End":                 end_time.strftime("%d-%b-%y %I:%M %p"),
                })
            except Exception as e:
                log_msg(f"Dashboard update failed: {e}", "WARNING")

    except KeyboardInterrupt:
        log_msg("Run interrupted by user (Ctrl+C)", "WARNING")

    except Exception as e:
        log_msg(f"Unexpected error during run: {e}", "ERROR")

    finally:
        context.close()
        close_run_logger()

    end_time = get_pkt_time()
    duration = (end_time - start_time).total_seconds()
    print_summary(stats, mode, duration)
    print_important_events()

    return stats


# ══════════════════════════════════════════════════════════════════════════════
#  Manual single run (CLI)
# ══════════════════════════════════════════════════════════════════════════════

def run_once(mode: str, max_profiles: int = 0):
    """Run one time immediately. Used by CLI args 'online' / 'target'."""
    if not _acquire_lock(mode):
        sys.exit(0)
    try:
        do_run(mode, max_profiles)
    finally:
        _release_lock()


# ══════════════════════════════════════════════════════════════════════════════
#  Online mode scheduler (auto — every 15 minutes, no-overlap)
# ══════════════════════════════════════════════════════════════════════════════

ONLINE_INTERVAL_SECONDS = 15 * 60   # 15 minutes

_scheduler_stop = threading.Event()


def _signal_handler(sig, frame):
    log_msg("Shutdown signal received — stopping scheduler...", "WARNING")
    _scheduler_stop.set()


def run_scheduler(max_profiles: int = 0):
    """
    Continuously run Online Mode every 15 minutes.

    - If a run is still active when the next tick arrives, that tick is SKIPPED
      (no overlap, no cancellation of the running job).
    - Ctrl+C or SIGTERM stops the scheduler cleanly.
    """
    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    log_msg("=== SCHEDULER STARTED — Online mode every 15 minutes ===")
    log_msg("Press Ctrl+C to stop.")

    while not _scheduler_stop.is_set():
        now  = get_pkt_time()
        tick = now.strftime("%d-%b-%y %H:%M:%S")

        if _is_locked():
            log_msg(f"[{tick}] Run already active — skipping this tick", "WARNING")
        else:
            log_msg(f"[{tick}] Starting scheduled Online run...")
            if _acquire_lock("online"):
                try:
                    do_run("online", max_profiles)
                except Exception as e:
                    log_msg(f"Scheduled run error: {e}", "ERROR")
                finally:
                    _release_lock()

        # Wait for the next 15-minute tick, checking for stop signal every second
        for _ in range(ONLINE_INTERVAL_SECONDS):
            if _scheduler_stop.is_set():
                break
            time.sleep(1)

    log_msg("Scheduler stopped.")


# ══════════════════════════════════════════════════════════════════════════════
#  Interactive menu (no-arg run)
# ══════════════════════════════════════════════════════════════════════════════

def _prompt_int(label: str, default: int = 0, min_value: int = 0) -> int:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if val < min_value:
                print(f"Value must be >= {min_value}")
                continue
            return val
        except Exception:
            print("Enter a valid integer")


def _prompt_float(label: str, default: float = 0.0, min_value: float = 0.0) -> float:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = float(raw)
            if val < min_value:
                print(f"Value must be >= {min_value}")
                continue
            return val
        except Exception:
            print("Enter a valid number")


def _apply_runtime_overrides(*, batch_size=None, min_delay=None, max_delay=None,
                             page_load_timeout=None, sheet_write_delay=None):
    if batch_size is not None:
        Config.BATCH_SIZE = int(batch_size)
    if min_delay is not None:
        Config.MIN_DELAY = float(min_delay)
    if max_delay is not None:
        Config.MAX_DELAY = float(max_delay)
    if page_load_timeout is not None:
        Config.PAGE_LOAD_TIMEOUT = int(page_load_timeout)
    if sheet_write_delay is not None:
        Config.SHEET_WRITE_DELAY = float(sheet_write_delay)


def interactive_menu():
    print("\nSelect Mode:")
    print("  1) Online")
    print("  2) Target")
    print("  3) Scheduler (Online every 15 min)")
    print("  0) Exit")

    choice = input("Enter choice [1]: ").strip() or "1"
    if choice == "0":
        return
    if choice == "1":
        mode = "online"
    elif choice == "2":
        mode = "target"
    elif choice == "3":
        mode = "scheduler"
    else:
        print("Invalid choice")
        return

    print("\nOptions (press Enter to keep default):")
    limit = _prompt_int("How many profiles to run (0 = unlimited)", default=Config.MAX_PROFILES_PER_RUN, min_value=0)

    print("\nMore options:")
    batch_size = _prompt_int("Batch size", default=Config.BATCH_SIZE, min_value=1)
    min_delay = _prompt_float("Min delay (seconds)", default=Config.MIN_DELAY, min_value=0.0)
    max_delay = _prompt_float("Max delay (seconds)", default=Config.MAX_DELAY, min_value=0.0)
    page_load_timeout = _prompt_int("Page load timeout (seconds)", default=Config.PAGE_LOAD_TIMEOUT, min_value=1)
    sheet_write_delay = _prompt_float("Sheet write delay (seconds)", default=Config.SHEET_WRITE_DELAY, min_value=0.0)

    if max_delay < min_delay:
        print("Max delay cannot be less than min delay. Swapping values.")
        min_delay, max_delay = max_delay, min_delay

    _apply_runtime_overrides(
        batch_size=batch_size,
        min_delay=min_delay,
        max_delay=max_delay,
        page_load_timeout=page_load_timeout,
        sheet_write_delay=sheet_write_delay,
    )

    if mode == "scheduler":
        run_scheduler(max_profiles=limit)
    else:
        run_once(mode=mode, max_profiles=limit)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI parser
# ══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python run.py",
        description="DD-CMS-V3 — DamaDam Profile Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py online              Run online mode once (manual)
  python run.py target              Run target mode once (manual)
  python run.py online --limit 20   Online mode, max 20 profiles
  python run.py target --limit 10   Target mode, max 10 profiles
  python run.py scheduler           Auto-scheduler (online every 15 min)
  python run.py scheduler --limit 50  Scheduler with 50 profile cap per run
        """,
    )
    p.add_argument(
        "mode",
        choices=["online", "target", "scheduler"],
        help="online = online mode once | target = target mode once | scheduler = auto every 15 min",
    )
    p.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        metavar="N",
        help="Max profiles per run (0 = unlimited, default: 0)",
    )
    return p


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_menu()
    else:
        parser = _build_parser()
        args   = parser.parse_args()

        if args.mode == "scheduler":
            run_scheduler(max_profiles=args.limit)
        else:
            run_once(mode=args.mode, max_profiles=args.limit)
