"""Online phase runner (delegates to existing scraper logic)"""

from phases.profile.online_mode import run_online_mode
from config.config_online import OnlinePhaseConfig


def run(context, max_profiles=0):
    """Run the existing online scraper using shared context"""
    driver = context.start_browser()
    if not driver:
        raise RuntimeError("Browser not initialized")

    sheets = context.get_sheets_manager(
        credentials_json=OnlinePhaseConfig.CREDENTIALS_JSON,
        credentials_path=OnlinePhaseConfig.CREDENTIALS_PATH
    )

    stats = run_online_mode(driver, sheets, max_profiles)
    return stats, sheets
