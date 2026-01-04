"""
Browser Context Manager - Safe Browser Lifecycle Management

Provides context manager pattern for Selenium WebDriver to ensure
proper cleanup even when errors occur.

Usage:
    from core.browser_context import BrowserContext
    
    with BrowserContext() as driver:
        driver.get("https://example.com")
        # Browser automatically closed on exit
"""

import time
from contextlib import contextmanager
from typing import Optional, Generator

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

from config.config_common import Config
from utils.ui import log_msg


class BrowserContext:
    """
    Context manager for safe browser lifecycle management.
    
    This class ensures that the browser is properly cleaned up even if
    errors occur during execution. It implements the context manager
    protocol (__enter__ and __exit__).
    
    Example:
        >>> with BrowserContext() as driver:
        ...     driver.get("https://example.com")
        ...     # Do scraping
        ...     pass
        ... # Browser automatically closed here
        
        >>> # Can also be used without context manager
        >>> browser = BrowserContext()
        >>> driver = browser.start()
        >>> try:
        ...     driver.get("https://example.com")
        ... finally:
        ...     browser.close()
    """
    
    def __init__(
        self,
        headless: bool = True,
        window_size: str = "1920,1080",
        timeout: int = None
    ):
        """
        Initialize browser context.
        
        Args:
            headless: Run browser in headless mode (default: True)
            window_size: Browser window size as "width,height" (default: "1920,1080")
            timeout: Page load timeout in seconds (default: from Config)
        """
        self.headless = headless
        self.window_size = window_size
        self.timeout = timeout or Config.PAGE_LOAD_TIMEOUT
        self.driver: Optional[webdriver.Chrome] = None
        self._started = False
    
    def _create_chrome_options(self) -> Options:
        """
        Create Chrome options with anti-detection measures.
        
        Returns:
            Configured Chrome Options object
        """
        opts = Options()
        
        # Headless mode
        if self.headless:
            opts.add_argument("--headless=new")
        
        # Window size
        opts.add_argument(f"--window-size={self.window_size}")
        
        # Anti-detection
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        
        # Stability
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        
        # Reduce noise
        opts.add_argument("--log-level=3")
        
        return opts
    
    def start(self) -> webdriver.Chrome:
        """
        Start the browser instance.
        
        Returns:
            Configured Chrome WebDriver instance
            
        Raises:
            WebDriverException: If browser fails to start
        """
        if self._started:
            log_msg("Browser already started", "WARNING")
            return self.driver
        
        log_msg("🌐 Initializing Chrome browser...")
        
        try:
            opts = self._create_chrome_options()
            
            # Use custom ChromeDriver if specified
            if Config.CHROMEDRIVER_PATH and Config.CHROMEDRIVER_PATH.strip():
                from pathlib import Path
                chromedriver_path = Path(Config.CHROMEDRIVER_PATH)
                
                if chromedriver_path.exists():
                    log_msg(f"Using custom ChromeDriver: {chromedriver_path}")
                    service = Service(executable_path=str(chromedriver_path))
                    self.driver = webdriver.Chrome(service=service, options=opts)
                else:
                    log_msg(
                        f"ChromeDriver path not found: {chromedriver_path}. Using system default.",
                        "WARNING"
                    )
                    self.driver = webdriver.Chrome(options=opts)
            else:
                log_msg("Using system ChromeDriver")
                self.driver = webdriver.Chrome(options=opts)
            
            # Configure timeouts
            self.driver.set_page_load_timeout(self.timeout)
            
            # Hide webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self._started = True
            log_msg("✅ Browser initialized successfully", "OK")
            
            return self.driver
            
        except WebDriverException as e:
            log_msg(f"❌ Browser setup failed: {e}", "ERROR")
            raise
        except Exception as e:
            log_msg(f"❌ Unexpected error during browser setup: {e}", "ERROR")
            raise
    
    def close(self):
        """
        Close the browser instance safely.
        
        This method ensures the browser is closed even if errors occur.
        It's safe to call multiple times (won't error if already closed).
        """
        if not self._started or not self.driver:
            return
        
        try:
            self.driver.quit()
            log_msg("🔒 Browser closed successfully")
        except Exception as e:
            log_msg(f"⚠️ Error closing browser (non-critical): {e}", "WARNING")
        finally:
            self.driver = None
            self._started = False
    
    def restart(self) -> webdriver.Chrome:
        """
        Restart the browser (close and start again).
        
        Useful for recovering from browser crashes or memory leaks.
        
        Returns:
            New Chrome WebDriver instance
        """
        log_msg("♻️ Restarting browser...")
        self.close()
        time.sleep(2)  # Give OS time to release resources
        return self.start()
    
    def __enter__(self) -> webdriver.Chrome:
        """
        Context manager entry point.
        
        Returns:
            Started Chrome WebDriver instance
        """
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point.
        
        Ensures browser is closed even if exception occurred.
        
        Args:
            exc_type: Exception type (if raised)
            exc_val: Exception value (if raised)
            exc_tb: Exception traceback (if raised)
        
        Returns:
            False (don't suppress exceptions)
        """
        self.close()
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """Destructor - ensure browser is closed when object is garbage collected."""
        if self._started:
            self.close()


@contextmanager
def browser_session(
    headless: bool = True,
    window_size: str = "1920,1080",
    timeout: int = None
) -> Generator[webdriver.Chrome, None, None]:
    """
    Convenience context manager for browser sessions.
    
    This is a simpler alternative to BrowserContext class when you just need
    a quick browser session without managing the BrowserContext object.
    
    Args:
        headless: Run browser in headless mode (default: True)
        window_size: Browser window size (default: "1920,1080")
        timeout: Page load timeout in seconds (default: from Config)
    
    Yields:
        Chrome WebDriver instance
    
    Example:
        >>> from core.browser_context import browser_session
        >>> 
        >>> with browser_session() as driver:
        ...     driver.get("https://example.com")
        ...     print(driver.title)
    """
    context = BrowserContext(
        headless=headless,
        window_size=window_size,
        timeout=timeout
    )
    
    driver = None
    try:
        driver = context.start()
        yield driver
    finally:
        context.close()


# Convenience function for quick browser access
def get_browser(
    headless: bool = True,
    timeout: int = None
) -> webdriver.Chrome:
    """
    Quick way to get a browser instance without context manager.
    
    ⚠️ Warning: Remember to call driver.quit() when done!
    Better to use BrowserContext or browser_session context managers.
    
    Args:
        headless: Run in headless mode (default: True)
        timeout: Page load timeout (default: from Config)
    
    Returns:
        Chrome WebDriver instance
    
    Example:
        >>> driver = get_browser()
        >>> try:
        ...     driver.get("https://example.com")
        ...     print(driver.title)
        ... finally:
        ...     driver.quit()  # Don't forget!
    """
    context = BrowserContext(headless=headless, timeout=timeout)
    return context.start()
