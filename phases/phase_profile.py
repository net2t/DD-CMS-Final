"""
Profile Phase Runner

Orchestrates the profile scraping process by running either online or target mode.
"""

from .profile.online_mode import run_online_mode
from .profile.target_mode import run_target_mode
from config.config_online import OnlinePhaseConfig
from config.config_target import TargetPhaseConfig
from utils.ui import log_msg

def run(context, mode, max_profiles=0):
    """
    Orchestrates the profile scraping phase.

    This function acts as a router, selecting the appropriate scraping mode
    (online or target) based on the 'mode' parameter. It initializes the
    SheetsManager with the correct credentials for the selected mode and then
    calls the corresponding run function to execute the scraping logic.

    Args:
        context (RunContext): The shared run context containing the browser driver.
        mode (str): The selected scraping mode ('online' or 'target').
        max_profiles (int): The maximum number of profiles to scrape.

    Returns:
        tuple: A tuple containing the scraping statistics (dict) and the
               SheetsManager instance used for the run.
    """
    if mode == 'online':
        log_msg("=== RUNNING PROFILE PHASE (ONLINE MODE) ===")
        sheets = context.get_sheets_manager(
            credentials_json=OnlinePhaseConfig.CREDENTIALS_JSON,
            credentials_path=OnlinePhaseConfig.CREDENTIALS_PATH
        )
        stats = run_online_mode(driver=context.driver, sheets=sheets, max_profiles=max_profiles)
        return stats, sheets
    
    elif mode == 'target':
        log_msg("=== RUNNING PROFILE PHASE (TARGET MODE) ===")
        sheets = context.get_sheets_manager(
            credentials_json=TargetPhaseConfig.CREDENTIALS_JSON,
            credentials_path=TargetPhaseConfig.CREDENTIALS_PATH
        )
        stats = run_target_mode(driver=context.driver, sheets=sheets, max_profiles=max_profiles)
        return stats, sheets
    
    else:
        log_msg(f"Unknown profile mode: {mode}", "WARNING")
        return {}, None
