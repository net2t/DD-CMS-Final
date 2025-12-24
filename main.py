#!/usr/bin/env python3
"""
DamaDam Scraper v4.0 - Main Entry Point
Supports two modes: Target (from sheet) and Online (from online users list)
STEP-6: Online mode max_profiles limit, profile sorting
"""

import sys
import argparse
from datetime import datetime

from config.config_common import Config
from core.run_context import RunContext
from utils.ui import print_header, print_summary, log_msg, get_pkt_time

# Import phase runners
from phases import phase_profile, phase_mehfil, phase_posts

# ==================== MAIN FUNCTION ====================

def main():
    """Main entry point"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description=f"DamaDam Scraper {Config.SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py target --max-profiles 50
  python main.py online --max-profiles 10
  python main.py target --batch-size 10
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['target', 'online'],
        help='Scraping mode: `target` (from RunList sheet) or `online` (from online users list)'
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
    
    # Print header
    print_header(f"DamaDam Scraper - {args.mode.upper()} MODE", Config.SCRIPT_VERSION)
    
    # Update config
    Config.BATCH_SIZE = args.batch_size
    Config.MAX_PROFILES_PER_RUN = args.max_profiles
    
    # Start time
    start_time = get_pkt_time()
    

    context = RunContext()
    try:
        # Start browser and login
        context.start_browser()
        if not context.login():
            log_msg("Login failed", "ERROR")
            return 1

        # Run profile phase
        stats, sheets = phase_profile.run(context, args.mode, args.max_profiles)

        # Mehfil and Posts phases are stubs for now
        log_msg("=== RUNNING MEHFIL PHASE (STUB) ===")
        phase_mehfil.run(context)

        log_msg("=== RUNNING POSTS PHASE (STUB) ===")
        phase_posts.run(context)

        # Sort profiles by date after scraping if a sheet was used
        if sheets:
            log_msg("Sorting profiles by date...")
            sheets.sort_profiles_by_date()
        
        # End time
        end_time = get_pkt_time()
        
        # Update dashboard and print summary
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

        print_summary(stats, args.mode, (end_time - start_time).total_seconds())
        
        return 0
    
    except KeyboardInterrupt:
        print()
        log_msg("Interrupted by user", "WARNING")
        return 1
    
    except Exception as e:
        log_msg(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        context.close()

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    sys.exit(main())
