"""
Validation System - Input Validation and Sanitization

Provides comprehensive validation for nicknames, URLs, and other inputs
with detailed error messages and type hints.

Usage:
    from utils.validators import NicknameValidator
    
    valid, clean_nick, error = NicknameValidator.validate("user123")
    if not valid:
        print(f"Invalid: {error}")
"""

import re
import string
from typing import Tuple, Optional
from urllib.parse import urlparse


class NicknameValidator:
    """
    Comprehensive nickname validation with detailed feedback.
    
    This class provides validation for DamaDam usernames according to
    platform rules and security best practices.
    """
    
    # Configuration
    # Allowed: alphanumeric + a small safe set used by DamaDam profiles
    ALLOWED_SPECIAL = set('@.-_')
    ALLOWED_ALNUM = set(string.ascii_letters + string.digits)
    MAX_LENGTH = 50
    MIN_LENGTH = 1
    
    # Dangerous characters that could be used for injection
    DANGEROUS_CHARS = set('<>"\'&|;`\\()[]{}')
    
    # Whitespace characters
    WHITESPACE_CHARS = {' ', '\t', '\n', '\r', '\f', '\v'}
    
    @classmethod
    def validate(cls, nickname: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and sanitize a nickname.
        
        Args:
            nickname: Raw nickname string to validate
        
        Returns:
            Tuple of (is_valid, cleaned_nickname, error_message)
            - is_valid: True if valid, False otherwise
            - cleaned_nickname: Sanitized nickname (None if invalid)
            - error_message: Description of validation error (None if valid)
        
        Example:
            >>> valid, clean, error = NicknameValidator.validate("user123")
            >>> if valid:
            ...     print(f"Valid nickname: {clean}")
            ... else:
            ...     print(f"Invalid: {error}")
            Valid nickname: user123
            
            >>> valid, clean, error = NicknameValidator.validate("user name")
            >>> print(error)
            Contains whitespace
        """
        # Check type
        if not nickname or not isinstance(nickname, str):
            return False, None, "Empty or invalid type"
        
        # Strip leading/trailing whitespace
        nickname = nickname.strip()
        
        # Check if empty after strip
        if not nickname:
            return False, None, "Empty after strip"
        
        # Check length
        if len(nickname) < cls.MIN_LENGTH:
            return False, None, f"Too short (min {cls.MIN_LENGTH} character)"
        
        if len(nickname) > cls.MAX_LENGTH:
            return False, None, f"Too long (max {cls.MAX_LENGTH} characters)"
        
        # Check for whitespace
        if any(c in nickname for c in cls.WHITESPACE_CHARS):
            return False, None, "Contains whitespace"
        
        # Check for dangerous characters
        dangerous_found = [c for c in nickname if c in cls.DANGEROUS_CHARS]
        if dangerous_found:
            return False, None, f"Contains dangerous characters: {', '.join(dangerous_found)}"

        # Enforce supported character set
        invalid_chars = [
            c for c in nickname
            if not (c in cls.ALLOWED_ALNUM or c in cls.ALLOWED_SPECIAL)
        ]
        if invalid_chars:
            unique_chars = ', '.join(sorted(set(invalid_chars)))
            return (
                False,
                None,
                f"Contains unsupported characters: {unique_chars}. "
                "Allowed: A-Z, a-z, 0-9, @ . - _"
            )
        
        # Check if it's just special characters (must have at least one alphanumeric)
        if not any(c in cls.ALLOWED_ALNUM for c in nickname):
            return False, None, "Must contain at least one alphanumeric character"
        
        # Check for control characters
        if any(ord(c) < 32 or ord(c) == 127 for c in nickname):
            return False, None, "Contains control characters"
        
        # All checks passed
        return True, nickname, None
    
    @classmethod
    def validate_multiple(cls, nicknames: list) -> dict:
        """
        Validate multiple nicknames at once.
        
        Args:
            nicknames: List of nickname strings
        
        Returns:
            Dictionary with validation results:
            {
                'valid': [clean_nicknames],
                'invalid': [(raw_nickname, error_message), ...]
            }
        
        Example:
            >>> nicknames = ["user123", "user name", "valid@user", ""]
            >>> results = NicknameValidator.validate_multiple(nicknames)
            >>> print(f"Valid: {results['valid']}")
            >>> print(f"Invalid: {results['invalid']}")
            Valid: ['user123', 'valid@user']
            Invalid: [('user name', 'Contains whitespace'), ('', 'Empty or invalid type')]
        """
        results = {
            'valid': [],
            'invalid': []
        }
        
        for nickname in nicknames:
            valid, clean, error = cls.validate(nickname)
            if valid:
                results['valid'].append(clean)
            else:
                results['invalid'].append((nickname, error))
        
        return results
    
    @classmethod
    def is_valid(cls, nickname: str) -> bool:
        """
        Quick validation check (returns only True/False).
        
        Args:
            nickname: Nickname to validate
        
        Returns:
            True if valid, False otherwise
        
        Example:
            >>> NicknameValidator.is_valid("user123")
            True
            >>> NicknameValidator.is_valid("user name")
            False
        """
        valid, _, _ = cls.validate(nickname)
        return valid
    
    @classmethod
    def sanitize(cls, nickname: str) -> Optional[str]:
        """
        Attempt to sanitize a nickname (return cleaned version or None).
        
        Args:
            nickname: Nickname to sanitize
        
        Returns:
            Cleaned nickname if valid, None if invalid
        
        Example:
            >>> NicknameValidator.sanitize("  user123  ")
            'user123'
            >>> NicknameValidator.sanitize("user name")
            None
        """
        valid, clean, _ = cls.validate(nickname)
        return clean if valid else None


class URLValidator:
    """
    URL validation and normalization.
    
    Validates DamaDam URLs and provides normalization utilities.
    """
    
    VALID_SCHEMES = {'http', 'https'}
    VALID_DOMAINS = {'damadam.pk', 'www.damadam.pk'}
    
    @classmethod
    def validate(cls, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a URL.
        
        Args:
            url: URL string to validate
        
        Returns:
            Tuple of (is_valid, normalized_url, error_message)
        
        Example:
            >>> valid, clean, error = URLValidator.validate("https://damadam.pk/users/test")
            >>> if valid:
            ...     print(f"Valid URL: {clean}")
        """
        if not url or not isinstance(url, str):
            return False, None, "Empty or invalid type"
        
        url = url.strip()
        
        if not url:
            return False, None, "Empty after strip"
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme.lower() not in cls.VALID_SCHEMES:
                return False, None, f"Invalid scheme: {parsed.scheme}"
            
            # Check domain (optional - can be relaxed)
            # Uncomment if you want strict domain checking
            # if parsed.netloc.lower() not in cls.VALID_DOMAINS:
            #     return False, None, f"Invalid domain: {parsed.netloc}"
            
            # Normalize
            normalized = url.rstrip('/')
            
            return True, normalized, None
            
        except Exception as e:
            return False, None, f"Parse error: {e}"
    
    @classmethod
    def is_valid(cls, url: str) -> bool:
        """Quick URL validation check."""
        valid, _, _ = cls.validate(url)
        return valid


class ProfileStateValidator:
    """
    Validation for profile state values.
    
    Ensures profile states match allowed values from Config.
    """
    
    from config.config_common import Config
    
    VALID_STATES = {
        Config.PROFILE_STATE_ACTIVE,
        Config.PROFILE_STATE_UNVERIFIED,
        Config.PROFILE_STATE_BANNED,
        Config.PROFILE_STATE_DEAD
    }
    
    @classmethod
    def validate(cls, state: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a profile state.
        
        Args:
            state: Profile state string
        
        Returns:
            Tuple of (is_valid, normalized_state, error_message)
        """
        if not state or not isinstance(state, str):
            return False, None, "Empty or invalid type"
        
        state_upper = state.strip().upper()
        
        if state_upper in cls.VALID_STATES:
            return True, state_upper, None
        else:
            valid_list = ', '.join(cls.VALID_STATES)
            return False, None, f"Invalid state. Must be one of: {valid_list}"
    
    @classmethod
    def is_valid(cls, state: str) -> bool:
        """Quick state validation check."""
        valid, _, _ = cls.validate(state)
        return valid


class DateValidator:
    """
    Date format validation for scraped dates.
    
    Ensures dates match expected format: "dd-mmm-yy hh:mm a"
    """
    
    # Expected format: "04-jan-26 03:45 pm"
    DATE_PATTERN = re.compile(
        r'^\d{2}-[a-z]{3}-\d{2} \d{2}:\d{2} [ap]m$',
        re.IGNORECASE
    )
    
    @classmethod
    def validate(cls, date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a date string.
        
        Args:
            date_str: Date string to validate
        
        Returns:
            Tuple of (is_valid, normalized_date, error_message)
        
        Example:
            >>> valid, clean, error = DateValidator.validate("04-jan-26 03:45 pm")
            >>> print(valid)
            True
        """
        if not date_str or not isinstance(date_str, str):
            return False, None, "Empty or invalid type"
        
        date_str = date_str.strip().lower()
        
        if cls.DATE_PATTERN.match(date_str):
            return True, date_str, None
        else:
            return False, None, "Invalid format. Expected: dd-mmm-yy hh:mm am/pm"
    
    @classmethod
    def is_valid(cls, date_str: str) -> bool:
        """Quick date validation check."""
        valid, _, _ = cls.validate(date_str)
        return valid


# Convenience functions for backward compatibility

def validate_nickname(nickname: str) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    
    Args:
        nickname: Nickname to validate
    
    Returns:
        Cleaned nickname if valid, None otherwise
    """
    return NicknameValidator.sanitize(nickname)


def sanitize_nickname_for_url(nickname: str) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    
    Args:
        nickname: Nickname to sanitize
    
    Returns:
        Cleaned nickname if valid, None otherwise
    """
    return NicknameValidator.sanitize(nickname)
