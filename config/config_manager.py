"""
Configuration Manager - Unified Config with Phase Support

This module provides a centralized configuration system that:
- Loads base configuration from config_common.py
- Applies phase-specific overrides (online, target, test)
- Validates all settings on startup
- Provides type-safe access to config values

Usage:
    config = ConfigManager(phase='online')
    max_profiles = config.get('MAX_PROFILES_PER_RUN', 0)
    username = config.get('DAMADAM_USERNAME')
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

from .config_common import Config
from utils.ui import log_msg


class ConfigManager:
    """
    Centralized configuration manager with phase-specific overrides.
    
    This class provides a single point of access for all configuration values,
    with support for phase-specific overrides while maintaining the base
    configuration as fallback.
    """
    
    def __init__(self, phase: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            phase: Phase name for loading phase-specific config.
                  Options: 'online', 'target', 'test', None (base only)
        """
        self.base = Config
        self.phase = phase
        self.phase_config = self._load_phase_config(phase)
        self._validated = False
    
    def _load_phase_config(self, phase: Optional[str]) -> Optional[Any]:
        """
        Load phase-specific configuration module if exists.
        
        Args:
            phase: Phase name to load
            
        Returns:
            Phase config class or None if phase is None or not found
        """
        if not phase:
            return None
        
        phase_lower = phase.lower()
        
        try:
            if phase_lower == 'online':
                from .config_online import OnlinePhaseConfig
                return OnlinePhaseConfig
            elif phase_lower == 'target':
                from .config_target import TargetPhaseConfig
                return TargetPhaseConfig
            else:
                log_msg(f"Unknown phase: {phase}, using base config only", "WARNING")
                return None
        except ImportError as e:
            log_msg(f"Failed to load phase config for {phase}: {e}", "WARNING")
            return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with phase override priority.
        
        Priority order:
        1. Phase-specific config (if loaded)
        2. Base config
        3. Provided default value
        
        Args:
            key: Configuration key name (e.g., 'MAX_PROFILES_PER_RUN')
            default: Default value if key not found
            
        Returns:
            Configuration value
            
        Example:
            >>> config = ConfigManager(phase='online')
            >>> max_profiles = config.get('MAX_PROFILES_PER_RUN', 0)
            >>> username = config.get('DAMADAM_USERNAME')
        """
        # Try phase-specific config first
        if self.phase_config and hasattr(self.phase_config, key):
            return getattr(self.phase_config, key)
        
        # Fall back to base config
        if hasattr(self.base, key):
            return getattr(self.base, key)
        
        # Return default if key not found
        return default
    
    def validate(self) -> bool:
        """
        Validate critical configuration values.
        
        This is called automatically on first access, but can also be
        called manually for explicit validation.
        
        Returns:
            True if validation passed
            
        Raises:
            SystemExit: If critical configuration missing
        """
        if self._validated:
            return True
        
        try:
            # Delegate to base Config validation
            self.base.validate()
            self._validated = True
            return True
        except Exception as e:
            log_msg(f"Configuration validation failed: {e}", "ERROR")
            sys.exit(1)
    
    def get_credentials_path(self) -> Path:
        """
        Get path to Google credentials file.
        
        Returns:
            Path object pointing to credentials.json
        """
        return self.base.get_credentials_path()
    
    def get_phase_info(self) -> dict:
        """
        Get information about current phase configuration.
        
        Returns:
            Dictionary with phase details
            
        Example:
            >>> config = ConfigManager(phase='online')
            >>> info = config.get_phase_info()
            >>> print(info)
            {
                'phase': 'online',
                'has_override': True,
                'config_module': 'config.config_online.OnlinePhaseConfig'
            }
        """
        return {
            'phase': self.phase,
            'has_override': self.phase_config is not None,
            'config_module': (
                f"{self.phase_config.__module__}.{self.phase_config.__name__}"
                if self.phase_config else None
            )
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        phase_info = self.get_phase_info()
        return (
            f"ConfigManager(phase='{phase_info['phase']}', "
            f"has_override={phase_info['has_override']})"
        )


# Convenience function for quick config access
def get_config(phase: Optional[str] = None) -> ConfigManager:
    """
    Factory function to create and validate ConfigManager.
    
    Args:
        phase: Phase name for loading phase-specific config
        
    Returns:
        Validated ConfigManager instance
        
    Example:
        >>> from config.config_manager import get_config
        >>> config = get_config('online')
        >>> max_profiles = config.get('MAX_PROFILES_PER_RUN', 0)
    """
    manager = ConfigManager(phase=phase)
    manager.validate()
    return manager
