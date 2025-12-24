"""
Configuration for the Test Mode.
"""

from .config_common import Config

class TestPhaseConfig(Config):
    """Configuration specific to the test mode."""
    
    # A short, hardcoded list of nicknames to be used for testing.
    # These should include a mix of expected profile types (e.g., normal, unverified, banned).
    TEST_PROFILES = [
        {'nickname': 'testuser1', 'source': 'Test'},
        {'nickname': 'testuser2', 'source': 'Test'},
        {'nickname': 'banneduser', 'source': 'Test'},
        {'nickname': 'unverifieduser', 'source': 'Test'},
        {'nickname': 'nonexistentuser', 'source': 'Test'}
    ]
