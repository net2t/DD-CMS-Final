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
from core.browser_manager import get_pkt_time, log_msg

# Import phase runners
from phases import phase_online
from phases import phase_target
from phases import phase_mehfil
from phases import phase_posts

# ==================== MAIN FUNCTION ====================

def main():
    """Main entry point"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="DamaDam Scraper v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode target --max-profiles 50
  python main.py --mode online --max-profiles 10
  python main.py --mode target --batch-size 10
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['target', 'online'],
        required=True,
        help='Scraping mode: target (from sheet) or online (from online list)'
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
    print("=" * 70)
    print(f"  DamaDam Scraper v4.0 - {args.mode.upper()} MODE")
    print("=" * 70)
    print(f"Mode: {args.mode}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Profiles: {'All' if args.max_profiles == 0 else args.max_profiles}")
    print("=" * 70)
    print()
    
    # Update config
    Config.BATCH_SIZE = args.batch_size
    Config.MAX_PROFILES_PER_RUN = args.max_profiles
    
    # Start time
    start_time = get_pkt_time()
    
    # Validate configuration before starting
    Config.validate()

    context = RunContext()
    try:
        # Start browser and login
        context.start_browser()
        if not context.login():
            log_msg("Login failed", "ERROR")
            return 1

        # Run phases
        stats = {}
        sheets = None

        if args.mode == 'online':
            log_msg("=== RUNNING ONLINE PHASE ===")
            stats, sheets = phase_online.run(context, args.max_profiles)
        
        if args.mode == 'target':
            log_msg("=== RUNNING TARGET PHASE ===")
            stats, sheets = phase_target.run(context, args.max_profiles)

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
        
        # Update dashboard
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
            # STEP-6: Include state counts (with BLANK fallback)
            "state_counts": {
                "ACTIVE": stats.get('active', 0),
                "UNVERIFIED": stats.get('unverified', 0),
                "BANNED": stats.get('banned', 0),
                "DEAD": stats.get('dead', 0)
            }
        }
        
        sheets.update_dashboard(dashboard_data)
        
        # Print summary
        print()
        print("=" * 70)
        print("  SCRAPING COMPLETED")
        print("=" * 70)
        print(f"Mode: {args.mode.upper()}")
        print(f"Success: {stats.get('success', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        print(f"New: {stats.get('new', 0)}")
        print(f"Updated: {stats.get('updated', 0)}")
        print(f"Unchanged: {stats.get('unchanged', 0)}")
        if args.mode == 'online':
            print(f"Logged: {stats.get('logged', 0)}")
        print(f"Duration: {(end_time - start_time).total_seconds():.0f}s")
        print("=" * 70)
        
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
