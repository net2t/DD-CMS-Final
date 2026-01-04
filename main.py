#!/usr/bin/env python3
"""
DamaDam Scraper - Main Entry Point (Enhanced)

This is the main entry point of the DamaDam Scraper project.

What it does:
- Parses command-line arguments
- Initializes browser and authentication
- Runs Phase 1 (Profiles) scraping in selected mode
- Updates Google Sheets with results
- Provides comprehensive terminal output and metrics

Version: v2.100.0.18 (Enhanced)

Author: Nadeem (net2outlawzz@gmail.com)
AI Assistant: Claude (Anthropic)

Usage:
    python main.py <mode> [options]
    
    Modes:
        target  - Process profiles from RunList sheet
        online  - Scrape currently online users
        test    - Quick test with predefined profiles
    
    Options:
        --max-profiles N    Limit to N profiles (0 = unlimited)
        --batch-size N      Batch size for processing
        --metrics          Save detailed performance metrics
    
Examples:
    python main.py target --max-profiles 50
    python main.py online --max-profiles 20 --metrics
    python main.py test --max-profiles 3
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Core imports
from config.config_common import Config
from config.config_manager import ConfigManager
from core.run_context import RunContext
from core.browser_context import BrowserContext

# Utility imports
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
from utils.metrics import PerformanceMetrics

# Phase imports
from phases import phase_profile


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description=f"DamaDam Scraper {Config.SCRIPT_VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 Examples:
  python main.py target --max-profiles 50
  python main.py online --max-profiles 10
  python main.py target --batch-size 10
  python main.py online --max-profiles 20 --metrics

📚 Documentation:
  README.md          - Complete documentation
  LIMIT_HANDLING.md  - Handling API limits
  SECURITY.md        - Security best practices
  
📞 Support:
  Email: net2outlawzz@gmail.com
  Instagram: @net2nadeem
        """
    )
    
    # Mode selection (positional or optional)
    parser.add_argument(
        'mode_pos',
        nargs='?',
        choices=['target', 'online', 'test'],
        default=None,
        help='Scraping mode'
    )
    
    parser.add_argument(
        '--mode',
        dest='mode_opt',
        choices=['target', 'online', 'test'],
        help='Scraping mode (alternative to positional)'
    )
    
    # Scraping options
    parser.add_argument(
        '--max-profiles',
        type=int,
        default=0,
        help='Max profiles to scrape (0 = unlimited)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=Config.BATCH_SIZE,
        help=f'Batch size for processing (default: {Config.BATCH_SIZE})'
    )
    
    # Monitoring options
    parser.add_argument(
        '--metrics',
        action='store_true',
        help='Save detailed performance metrics to file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (more verbose output)'
    )
    
    # Parse
    args = parser.parse_args()
    
    # Determine mode
    args.mode = args.mode_opt or args.mode_pos
    if not args.mode:
        parser.error("❌ No mode specified. Choose: target, online, or test")
    
    return args


def setup_environment(args: argparse.Namespace) -> ConfigManager:
    """
    Setup environment and configuration for the run.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        ConfigManager instance
    """
    # Initialize logging
    init_run_logger(args.mode)
    
    # Print header
    print_header(
        f"DamaDam Scraper - {args.mode.upper()} MODE",
        Config.SCRIPT_VERSION
    )
    
    # Display configuration
    print_mode_config(args.mode, args.max_profiles, args.batch_size)
    
    # Load configuration with phase support
    config = ConfigManager(phase=args.mode)
    
    # Update runtime config
    Config.BATCH_SIZE = args.batch_size
    Config.MAX_PROFILES_PER_RUN = args.max_profiles
    
    return config


def initialize_browser_and_login(context: RunContext) -> bool:
    """
    Initialize browser and perform login.
    
    Args:
        context: RunContext instance
    
    Returns:
        True if successful, False otherwise
    """
    log_msg("🚀 Initializing browser...", "INFO")
    
    # Start browser
    driver = context.start_browser()
    if not driver:
        log_msg("❌ Failed to start browser", "ERROR")
        return False
    
    # Perform login
    if not context.login():
        log_msg("❌ Login failed - Cannot proceed", "ERROR")
        return False
    
    log_msg("✅ Browser and login successful", "OK")
    return True


def run_phase1_profiles(
    context: RunContext,
    args: argparse.Namespace,
    metrics: PerformanceMetrics
) -> tuple:
    """
    Run Phase 1 (Profiles) scraping.
    
    Args:
        context: RunContext instance
        args: Parsed arguments
        metrics: Performance metrics tracker
    
    Returns:
        Tuple of (stats, sheets_manager)
    """
    print_phase_start("PROFILE")
    
    # Measure phase execution time
    with metrics.measure('phase1_total'):
        stats, sheets = phase_profile.run(
            context,
            args.mode,
            args.max_profiles
        )
    
    # Record metrics
    metrics.increment('profiles_processed', stats.get('success', 0) + stats.get('failed', 0))
    metrics.increment('profiles_success', stats.get('success', 0))
    metrics.increment('profiles_failed', stats.get('failed', 0))
    metrics.set_metadata('mode', args.mode)
    metrics.set_metadata('max_profiles', args.max_profiles)
    
    # Display online users count if applicable
    if args.mode == 'online' and stats.get('logged', 0) > 0:
        print_online_users_found(stats.get('logged', 0))
    
    return stats, sheets


def finalize_and_report(
    stats: dict,
    sheets,
    args: argparse.Namespace,
    start_time,
    metrics: PerformanceMetrics
):
    """
    Finalize sheets and print comprehensive summary.
    
    Args:
        stats: Scraping statistics
        sheets: SheetsManager instance
        args: Parsed arguments
        start_time: Run start timestamp
        metrics: Performance metrics tracker
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    # Sort profiles by date
    if sheets:
        with metrics.measure('sort_profiles'):
            sheets.sort_profiles_by_date()
    
    # Calculate duration
    end_time = get_pkt_time()
    duration = (end_time - start_time).total_seconds()
    
    # Update dashboard
    if sheets:
        with metrics.measure('update_dashboard'):
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
        
        # Apply final formatting
        with metrics.measure('finalize_formatting'):
            sheets.finalize_formatting()
    
    # Print summary
    print_summary(stats, args.mode, duration)
    
    # Print important events
    print_important_events()
    
    # Print metrics if requested
    if args.metrics:
        log_msg("📊 Performance Metrics:", "INFO")
        metrics.print_summary()
        
        # Save to file
        metrics_file = Path("logs") / f"metrics_{args.mode}_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        metrics_file.parent.mkdir(exist_ok=True)
        metrics.save_to_file(str(metrics_file))
        log_msg(f"💾 Metrics saved to: {metrics_file}", "INFO")
    
    # Success message
    if stats.get('success', 0) > 0:
        log_msg("🎉 Run completed successfully!", "SUCCESS")
        return 0
    else:
        log_msg("⚠️ Run completed with no successful profiles", "WARNING")
        return 1


def main() -> int:
    """
    Main function - orchestrates the entire scraping session.
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    # Parse arguments
    args = parse_arguments()
    
    # Setup environment
    config = setup_environment(args)
    
    # Initialize metrics
    metrics = PerformanceMetrics()
    
    # Record start time
    start_time = get_pkt_time()
    
    # Initialize run context
    context = RunContext()
    
    try:
        # Browser and login
        if not initialize_browser_and_login(context):
            return 1
        
        # Run Phase 1 (Profiles)
        stats, sheets = run_phase1_profiles(context, args, metrics)
        
        # Future phases (stubs for now)
        # Uncomment when ready:
        # print_phase_start("MEHFIL")
        # phase_mehfil.run(context)
        
        # print_phase_start("POSTS")
        # phase_posts.run(context)
        
        # Finalize and report
        return finalize_and_report(stats, sheets, args, start_time, metrics)
    
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        print()
        log_msg("⚠️ Interrupted by user (Ctrl+C)", "WARNING")
        log_msg("📊 Partial results may have been saved", "INFO")
        return 1
    
    except Exception as e:
        # Catch unexpected errors
        log_msg(f"💥 Fatal error: {e}", "ERROR")
        
        if args.debug:
            import traceback
            traceback.print_exc()
        
        metrics.record_error('fatal_error')
        return 1
    
    finally:
        # Cleanup
        log_msg("🧹 Cleaning up...", "INFO")
        context.close()
        log_msg("👋 Goodbye!", "INFO")
        close_run_logger()


if __name__ == '__main__':
    sys.exit(main())
