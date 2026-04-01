"""
Phase 2 (Posts) Orchestrator
"""

from config.config_common import Config
from utils.ui import log_msg
from phases.posts.scraper import scrape_posts_for_profile

def run(context, limit=None):
    """
    Run Phase 2: Scrape posts for profiles marked as 'Ready'.
    """
    log_msg("=" * 60, "INFO")
    log_msg("🚀 STARTING PHASE 2: POST SCRAPING", "OK")
    log_msg(f"Target limit: {limit if limit else 'ALL'}", "INFO")
    log_msg("=" * 60, "INFO")

    sheets = context.get_sheets_manager()
    browser = context.driver

    # Ensure Posts sheet headers exist
    sheets._init_headers()

    eligible = sheets.get_eligible_profiles_for_phase2(limit)
    total_eligible = len(eligible)
    
    if not total_eligible:
        log_msg("No eligible profiles found for Phase 2.", "WARNING")
        return

    log_msg(f"Found {total_eligible} profiles ready for Phase 2", "OK")

    processed = 0
    total_new_posts = 0

    for item in eligible:
        row_num = item["row"]
        nick = item["NICK NAME"]
        profile_id = item["PROFILE ID"]
        
        if not nick:
            sheets.mark_phase2_done(row_num, "Error: No Nickname")
            continue

        log_msg(f"Processing posts for @{nick} (Row {row_num})...")

        try:
            posts_data = scrape_posts_for_profile(browser, nick, profile_id)
            if posts_data is not None:
                # Write to Posts sheet
                if len(posts_data) > 0:
                    sheets.write_posts_batch(posts_data)
                    total_new_posts += len(posts_data)
                
                # Mark as Done
                sheets.mark_phase2_done(row_num, "Scraped")
                processed += 1
            else:
                # Failed/Errors
                sheets.mark_phase2_done(row_num, "Error")
                
        except Exception as e:
            log_msg(f"Phase 2 error for {nick}: {e}", "ERROR")
            sheets.mark_phase2_done(row_num, "Error")

    log_msg("=" * 60, "INFO")
    log_msg(f"🏁 PHASE 2 COMPLETE", "OK")
    log_msg(f"Profiles processed: {processed}/{total_eligible}", "INFO")
    log_msg(f"Total posts saved: {total_new_posts}", "OK")
    log_msg("=" * 60, "INFO")
