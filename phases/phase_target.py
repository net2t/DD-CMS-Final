"""Target phase runner (delegates to existing scraper logic)"""

from scraper_target import run_target_mode


def run(context, max_profiles=0):
    """Run the existing target scraper using shared context"""
    driver = context.start_browser()
    if not driver:
        raise RuntimeError("Browser not initialized")

    sheets = context.get_sheets_manager()
    return run_target_mode(driver, sheets, max_profiles)
