#!/usr/bin/env python3
"""
DamaDam Scraper v4.0 - Main Entry Point
Supports two modes: Target (from sheet) and Online (from online users list)
"""

import sys
import argparse
from datetime import datetime

from config import Config
from browser import BrowserManager, LoginManager, get_pkt_time, log_msg
from sheets_manager import SheetsManager
from scraper_target import run_target_mode
from scraper_online import run_online_mode

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
  python main.py --mode online
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
        help='Max profiles to scrape (0 = all, only for target mode)'
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
    if args.mode == 'target':
        print(f"Max Profiles: {'All' if args.max_profiles == 0 else args.max_profiles}")
    print("=" * 70)
    print()
    
    # Update config
    Config.BATCH_SIZE = args.batch_size
    if args.mode == 'target':
        Config.MAX_PROFILES_PER_RUN = args.max_profiles
    
    # Start time
    start_time = get_pkt_time()
    
    # Initialize browser
    browser = BrowserManager()
    driver = browser.setup()
    
    if not driver:
        log_msg("Failed to initialize browser", "ERROR")
        sys.exit(1)
    
    try:
        # Login
        login_mgr = LoginManager(driver)
        if not login_mgr.login():
            log_msg("Login failed", "ERROR")
            return 1
        
        # Connect to Google Sheets
        log_msg("Connecting to Google Sheets...")
        sheets = SheetsManager()
        
        # Run appropriate mode
        if args.mode == 'target':
            stats = run_target_mode(driver, sheets, args.max_profiles)
        else:  # online
            stats = run_online_mode(driver, sheets)
        
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
        browser.close()

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    sys.exit(main())
