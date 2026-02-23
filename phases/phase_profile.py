"""
Profile Phase Router — DD-CMS-V3

Routes the run to either Online or Target mode based on the `mode` argument.
"""

from phases.profile.online_mode import run_online_mode
from phases.profile.target_mode import run_target_mode
from config.config_online import OnlinePhaseConfig
from config.config_target import TargetPhaseConfig
from utils.ui import log_msg


def run(context, mode, max_profiles=0):
    """
    Entry point for the Profile phase.

    Args:
        context:      RunContext (holds driver + sheets factory)
        mode:         'online' or 'target'
        max_profiles: 0 = unlimited

    Returns:
        (stats dict, SheetsManager instance)
    """
    if mode == 'online':
        log_msg("=== PROFILE PHASE — ONLINE MODE ===")
        sheets = context.get_sheets_manager(
            credentials_json=OnlinePhaseConfig.CREDENTIALS_JSON,
            credentials_path=OnlinePhaseConfig.CREDENTIALS_PATH,
        )
        stats = run_online_mode(driver=context.driver, sheets=sheets, max_profiles=max_profiles)
        return stats, sheets

    elif mode == 'target':
        log_msg("=== PROFILE PHASE — TARGET MODE ===")
        sheets = context.get_sheets_manager(
            credentials_json=TargetPhaseConfig.CREDENTIALS_JSON,
            credentials_path=TargetPhaseConfig.CREDENTIALS_PATH,
        )
        stats = run_target_mode(driver=context.driver, sheets=sheets, max_profiles=max_profiles)
        return stats, sheets

    else:
        log_msg(f"Unknown mode: {mode}", "WARNING")
        return {}, None
