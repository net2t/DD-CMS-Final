#!/usr/bin/env python3
"""
DamaDam Scraper v2.100.0.15 - Main Entry Point

Enhanced with:
- Beautiful terminal UI with emojis and colors
- Comprehensive summary reports
- Cookie-based login with backup account
- GitHub Actions ready
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
    print_online_users_found
)

# Import phase runners
from phases import phase_profile, phase_mehfil, phase_posts

# ==================== MAIN FUNCTION ====================

def main():
    """Main entry point for the DamaDam Scraper."""
    
    # --- Argument Parsing ---
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
    
    # --- Header --- 
    print_header(f"DamaDam Scraper - {args.mode.upper()} MODE", Config.SCRIPT_VERSION)
    
    # --- Configuration Display ---
    print_mode_config(args.mode, args.max_profiles, args.batch_size)
    
    # --- Configuration Update ---
    Config.BATCH_SIZE = args.batch_size
    Config.MAX_PROFILES_PER_RUN = args.max_profiles
    
    # --- Initialization ---
    start_time = get_pkt_time()
    context = RunContext()
    
    try:
        # --- Main Execution Block ---
        
        # Start browser and login
        log_msg("🚀 Initializing browser...", "INFO")
        context.start_browser()
        
        if not context.login():
            log_msg("❌ Login failed - Cannot proceed", "ERROR")
            return 1

        # --- Phase Execution ---
        print_phase_start("PROFILE")
        
        stats, sheets = phase_profile.run(context, args.mode, args.max_profiles)
        
        # Display online users count if in online mode
        if args.mode == 'online' and stats.get('logged', 0) > 0:
            print_online_users_found(stats.get('logged', 0))

        # Mehfil and Posts phases (stubs for now)
        # Uncomment when ready:
        # print_phase_start("MEHFIL")
        # phase_mehfil.run(context)
        
        # print_phase_start("POSTS")
        # phase_posts.run(context)

        # --- Finalization ---
        if sheets:
            log_msg("📊 Sorting profiles by date...", "INFO")
            sheets.sort_profiles_by_date()
        
        # End time
        end_time = get_pkt_time()
        duration = (end_time - start_time).total_seconds()
        
        # --- Reporting ---
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
        
        # Success message
        if stats.get('success', 0) > 0:
            log_msg("🎉 Run completed successfully!", "SUCCESS")
        else:
            log_msg("⚠️ Run completed with no successful profiles", "WARNING")
        
        return 0
    
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

# ==================== SCRIPT ENTRY POINT ====================

if __name__ == '__main__':
    sys.exit(main())
