#!/usr/bin/env python3
"""
DamaDam Scraper - Main Entry Point (Phase 1: Profiles)

This script is the main entry point of the project.

What it does (high level):
- Starts the browser and logs into DamaDam
- Runs Phase 1: scrapes profile data (Target/Online modes)
- Writes results to Google Sheets
- Prints a clean terminal summary at the end

Version:
- Displayed in terminal header from Config.SCRIPT_VERSION
"""

import sys
import argparse
from datetime import datetime

from config.config_common import Config
from core.run_context import RunContext
from utils.ui import (
    print_header, 
    print_summary, 
    log_msg, 
    get_pkt_time, 
    print_phase_start,
    print_mode_config,
    print_online_users_found,
    init_run_logger,
    close_run_logger,
    print_important_events
)

## Phase router imports
## Phase 1 (PROFILE) stabilization commits: acaa901, d6721fb, 4f05112
from phases import phase_profile

# ==================== MAIN FUNCTION ====================

def _parse_args():
    """Parse CLI arguments and return args."""
    parser = argparse.ArgumentParser(
        description=f"DamaDam Scraper {Config.SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 Examples:
  python main.py target --max-profiles 50
  python main.py online --max-profiles 10
  python main.py target --batch-size 10
        """
    )

    # Allow mode to be specified as positional or optional argument
    parser.add_argument(
        'mode_pos',
        nargs='?',
        choices=['target', 'online', 'test'],
        default=None,
        help='Scraping mode (e.g., `python main.py target`)'
    )
    parser.add_argument(
        '--mode',
        dest='mode_opt',
        choices=['target', 'online', 'test'],
        help='Scraping mode (e.g., `python main.py --mode target`)'
    )

    parser.add_argument(
        '--max-profiles',
        type=int,
        default=0,
        help='Max profiles to scrape (0 = all, applies to both modes)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=Config.BATCH_SIZE,
        help=f'Batch size (default: {Config.BATCH_SIZE})'
    )

    args = parser.parse_args()

    # Determine the final mode
    args.mode = args.mode_opt or args.mode_pos
    if not args.mode:
        parser.error("❌ No mode specified. Choose 'target', 'online', or 'test'.")

    return args


def _setup_run_environment(args):
    """Set up logger, header and config values for this run."""
    init_run_logger(args.mode)

    # --- Header ---
    print_header(f"DamaDam Scraper - {args.mode.upper()} MODE", Config.SCRIPT_VERSION)

    # --- Configuration Display ---
    print_mode_config(args.mode, args.max_profiles, args.batch_size)

    # --- Configuration Update ---
    Config.BATCH_SIZE = args.batch_size
    Config.MAX_PROFILES_PER_RUN = args.max_profiles


def _start_and_login(context):
    """Start browser and perform login. Returns True on success."""
    log_msg("🚀 Initializing browser...", "INFO")
    context.start_browser()
    if not context.login():
        log_msg("❌ Login failed - Cannot proceed", "ERROR")
        return False
    return True


def _run_phase1_profiles(context, args):
    """Run Phase 1 (Profiles) and return (stats, sheets)."""
    print_phase_start("PROFILE")
    stats, sheets = phase_profile.run(context, args.mode, args.max_profiles)

    # Display online users count if in online mode
    if args.mode == 'online' and stats.get('logged', 0) > 0:
        print_online_users_found(stats.get('logged', 0))

    return stats, sheets


def _finalize_and_report(stats, sheets, args, start_time):
    """Finalize sheets (sort/dashboard/format) and print summary."""
    if sheets:
        log_msg("📊 Sorting profiles by date...", "INFO")
        sheets.sort_profiles_by_date()

    end_time = get_pkt_time()
    duration = (end_time - start_time).total_seconds()

    if sheets:
        trigger = "scheduled" if Config.IS_CI else "manual"
        dashboard_data = {
            "Run Number": 1,
            "Last Run": end_time.strftime("%d-%b-%y %I:%M %p"),
            "Profiles Processed": stats.get('success', 0) + stats.get('failed', 0),
            "Success": stats.get('success', 0),
            "Failed": stats.get('failed', 0),
            "New Profiles": stats.get('new', 0),
            "Updated Profiles": stats.get('updated', 0),
            "Unchanged Profiles": stats.get('unchanged', 0),
            "Trigger": f"{trigger}-{args.mode}",
            "Start": start_time.strftime("%d-%b-%y %I:%M %p"),
            "End": end_time.strftime("%d-%b-%y %I:%M %p"),
        }
        sheets.update_dashboard(dashboard_data)

        # Apply font formatting once at the end (faster than per-row formatting)
        sheets.finalize_formatting()

    # Print beautiful summary
    print_summary(stats, args.mode, duration)
    print_important_events()

    # Success message
    if stats.get('success', 0) > 0:
        log_msg("🎉 Run completed successfully!", "SUCCESS")
    else:
        log_msg("⚠️ Run completed with no successful profiles", "WARNING")

    return 0

def main():
    """Runs one scraper session.

    Steps:
    - Read command line arguments (mode, max profiles, batch size)
    - Start Selenium browser and login
    - Run Phase 1 (Profiles) for the selected mode
    - Update Google Sheets (Profiles, OnlineLog, Dashboard)
    - Print summary and exit with a proper code
    """
    
    args = _parse_args()
    _setup_run_environment(args)
    
    # --- Initialization ---
    start_time = get_pkt_time()
    context = RunContext()
    
    try:
        # --- Main Execution Block ---
        
        if not _start_and_login(context):
            return 1

        stats, sheets = _run_phase1_profiles(context, args)

        # Mehfil and Posts phases (stubs for now)
        # Uncomment when ready:
        # print_phase_start("MEHFIL")
        # phase_mehfil.run(context)
        
        # print_phase_start("POSTS")
        # phase_posts.run(context)

        return _finalize_and_report(stats, sheets, args, start_time)
    
    except KeyboardInterrupt:
        # Handle graceful shutdown
        print()
        log_msg("⚠️ Interrupted by user (Ctrl+C)", "WARNING")
        log_msg("📊 Partial results may have been saved", "INFO")
        return 1
    
    except Exception as e:
        # Catch any unexpected errors
        log_msg(f"💥 Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # --- Cleanup ---
        log_msg("🧹 Cleaning up...", "INFO")
        context.close()
        log_msg("👋 Goodbye!", "INFO")
        close_run_logger()

# ==================== SCRIPT ENTRY POINT ====================

if __name__ == '__main__':
    sys.exit(main())
