"""
Retry Decorator for Network Operations

Provides reusable retry logic with exponential backoff for handling
transient failures in network operations, API calls, and browser interactions.

Usage:
    @retry_on_failure(max_attempts=3, delay=2, backoff=2)
    def scrape_profile(nickname):
        # Network operation that may fail
        pass
"""

import time
import functools
from typing import Callable, Tuple, Type, Optional

from utils.ui import log_msg


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    on_final_failure: Optional[Callable] = None
):
    """
    Decorator to retry function on failure with exponential backoff.
    
    This decorator wraps a function and automatically retries it if it raises
    specified exceptions. The delay between retries increases exponentially
    based on the backoff multiplier.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 2.0)
        backoff: Multiplier for delay after each attempt (default: 2.0)
                Example: delay=2, backoff=2 → 2s, 4s, 8s
        exceptions: Tuple of exception types to catch and retry (default: Exception)
        on_retry: Optional callback called on each retry (func(attempt, exception))
        on_final_failure: Optional callback called if all retries fail (func(exception))
    
    Returns:
        Decorated function that retries on failure
    
    Example:
        >>> @retry_on_failure(max_attempts=3, delay=5, exceptions=(TimeoutException,))
        ... def scrape_profile(nickname):
        ...     driver.get(f"https://example.com/users/{nickname}")
        ...     return extract_data()
        
        >>> # Custom retry callback
        >>> def log_retry(attempt, error):
        ...     print(f"Attempt {attempt} failed: {error}")
        >>> 
        >>> @retry_on_failure(max_attempts=3, on_retry=log_retry)
        ... def api_call():
        ...     return requests.get(url)
    
    Note:
        - Function will be called max_attempts times maximum
        - Total wait time = delay * (backoff^0 + backoff^1 + ... + backoff^(n-2))
        - Example with 3 attempts, delay=2, backoff=2: waits 2s + 4s = 6s total
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Attempt to execute the function
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, don't retry
                    if attempt == max_attempts:
                        log_msg(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            "ERROR"
                        )
                        
                        # Call final failure callback if provided
                        if on_final_failure:
                            try:
                                on_final_failure(e)
                            except Exception as callback_error:
                                log_msg(
                                    f"Final failure callback error: {callback_error}",
                                    "WARNING"
                                )
                        
                        # Re-raise the exception
                        raise
                    
                    # Log retry attempt
                    log_msg(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {attempt_delay:.1f}s...",
                        "WARNING"
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            log_msg(
                                f"Retry callback error: {callback_error}",
                                "WARNING"
                            )
                    
                    # Wait before retrying
                    time.sleep(attempt_delay)
                    
                    # Increase delay for next attempt (exponential backoff)
                    attempt_delay *= backoff
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_with_custom_logic(
    max_attempts: int = 3,
    should_retry: Optional[Callable[[Exception], bool]] = None,
    get_delay: Optional[Callable[[int], float]] = None
):
    """
    Advanced retry decorator with custom retry logic and delay calculation.
    
    This decorator provides more flexibility than retry_on_failure by allowing
    custom logic to determine whether to retry and how long to wait.
    
    Args:
        max_attempts: Maximum number of retry attempts
        should_retry: Function that takes exception and returns bool (should retry?)
                     If None, retries on any exception
        get_delay: Function that takes attempt number and returns delay in seconds
                  If None, uses constant 2 second delay
    
    Returns:
        Decorated function with custom retry logic
    
    Example:
        >>> def custom_should_retry(error):
        ...     # Only retry on specific HTTP status codes
        ...     if isinstance(error, APIError):
        ...         return error.status_code in [429, 500, 502, 503]
        ...     return False
        >>> 
        >>> def custom_delay(attempt):
        ...     # Fibonacci backoff: 1, 1, 2, 3, 5, 8...
        ...     if attempt <= 2:
        ...         return 1
        ...     return custom_delay(attempt-1) + custom_delay(attempt-2)
        >>> 
        >>> @retry_with_custom_logic(
        ...     max_attempts=5,
        ...     should_retry=custom_should_retry,
        ...     get_delay=custom_delay
        ... )
        ... def api_call():
        ...     return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if should_retry and not should_retry(e):
                        log_msg(
                            f"{func.__name__} failed with non-retryable error: {e}",
                            "ERROR"
                        )
                        raise
                    
                    # If last attempt, don't retry
                    if attempt == max_attempts:
                        log_msg(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            "ERROR"
                        )
                        raise
                    
                    # Calculate delay
                    delay = get_delay(attempt) if get_delay else 2.0
                    
                    log_msg(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s...",
                        "WARNING"
                    )
                    
                    time.sleep(delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# Convenience decorators for common scenarios

def retry_on_timeout(max_attempts: int = 3, delay: float = 5.0):
    """
    Retry decorator specifically for timeout errors.
    
    Example:
        >>> from selenium.common.exceptions import TimeoutException
        >>> @retry_on_timeout(max_attempts=3, delay=5)
        ... def load_page(url):
        ...     driver.get(url)
        ...     wait_for_element()
    """
    from selenium.common.exceptions import TimeoutException
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        backoff=1.5,
        exceptions=(TimeoutException,)
    )


def retry_on_network_error(max_attempts: int = 3, delay: float = 3.0):
    """
    Retry decorator for network-related errors.
    
    Example:
        >>> @retry_on_network_error(max_attempts=3)
        ... def fetch_data(url):
        ...     response = requests.get(url)
        ...     return response.json()
    """
    from selenium.common.exceptions import WebDriverException
    import requests
    
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        backoff=2.0,
        exceptions=(
            WebDriverException,
            requests.exceptions.RequestException,
            ConnectionError,
            TimeoutError
        )
    )


def retry_on_api_limit(max_attempts: int = 3, delay: float = 60.0):
    """
    Retry decorator specifically for API rate limits.
    
    Uses longer delays suitable for API quotas (60s, 120s, 240s).
    
    Example:
        >>> from gspread.exceptions import APIError
        >>> @retry_on_api_limit(max_attempts=3)
        ... def update_sheet(worksheet, data):
        ...     worksheet.update('A1', data)
    """
    try:
        from gspread.exceptions import APIError
        exceptions = (APIError,)
    except ImportError:
        exceptions = (Exception,)
    
    return retry_on_failure(
        max_attempts=max_attempts,
        delay=delay,
        backoff=2.0,
        exceptions=exceptions
    )
