"""
Sheets Batch Writer - Prevent API Rate Limits

Queues profile writes and flushes in batches to avoid hitting
Google Sheets API rate limits (60 requests/minute).

Usage:
    from utils.sheets_batch_writer import SheetsBatchWriter
    
    with SheetsBatchWriter(sheets, batch_size=10) as writer:
        for profile in profiles:
            writer.add_profile(profile)
    # Auto-flushes on exit
"""

import time
from typing import List, Dict, Any, Optional
from collections import deque

from utils.ui import log_msg
from utils.metrics import PerformanceMetrics


class SheetsBatchWriter:
    """
    Queue profile writes and flush in batches to prevent rate limits.
    
    This class implements the context manager protocol to ensure
    all queued writes are flushed even if errors occur.
    
    Example:
        >>> from utils.sheets_manager import SheetsManager
        >>> from utils.sheets_batch_writer import SheetsBatchWriter
        >>> 
        >>> sheets = SheetsManager()
        >>> 
        >>> with SheetsBatchWriter(sheets, batch_size=10) as writer:
        ...     for nickname in nicknames:
        ...         profile = scrape_profile(nickname)
        ...         writer.add_profile(profile)
        ... # Automatically flushes remaining profiles
        
        >>> # Manual usage
        >>> writer = SheetsBatchWriter(sheets, batch_size=10)
        >>> writer.add_profile(profile1)
        >>> writer.add_profile(profile2)
        >>> writer.flush()  # Manual flush
    """
    
    def __init__(
        self,
        sheets_manager,
        batch_size: int = 10,
        auto_flush_interval: float = 30.0,
        metrics: Optional[PerformanceMetrics] = None
    ):
        """
        Initialize batch writer.
        
        Args:
            sheets_manager: SheetsManager instance to use for writing
            batch_size: Number of profiles to queue before auto-flush
            auto_flush_interval: Seconds before auto-flush (0 = disabled)
            metrics: Optional PerformanceMetrics for tracking
        """
        self.sheets = sheets_manager
        self.batch_size = batch_size
        self.auto_flush_interval = auto_flush_interval
        self.metrics = metrics
        
        # Queue for pending writes
        self.queue: deque = deque()
        
        # Statistics
        self.stats = {
            'queued': 0,
            'flushed': 0,
            'failed': 0,
            'batches': 0
        }
        
        # Timing
        self.last_flush_time = time.time()
    
    def add_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        Add a profile to the write queue.
        
        Args:
            profile_data: Profile dictionary with all fields
        
        Returns:
            True if added successfully
        
        Example:
            >>> writer.add_profile({
            ...     'NICK NAME': 'user123',
            ...     'CITY': 'KARACHI',
            ...     # ... other fields
            ... })
        """
        if not profile_data:
            log_msg("Empty profile data, skipping", "WARNING")
            return False
        
        # Add to queue
        self.queue.append(profile_data)
        self.stats['queued'] += 1
        
        # Auto-flush if batch size reached
        if len(self.queue) >= self.batch_size:
            self.flush()
            return True
        
        # Auto-flush if interval elapsed
        if self.auto_flush_interval > 0:
            elapsed = time.time() - self.last_flush_time
            if elapsed >= self.auto_flush_interval:
                self.flush()
        
        return True
    
    def flush(self) -> Dict[str, int]:
        """
        Flush all queued profiles to sheet.
        
        Returns:
            Dictionary with flush statistics:
            {
                'success': int,  # Successfully written
                'failed': int,   # Failed writes
                'total': int     # Total attempted
            }
        
        Example:
            >>> result = writer.flush()
            >>> print(f"Written: {result['success']}/{result['total']}")
        """
        if not self.queue:
            return {'success': 0, 'failed': 0, 'total': 0}
        
        queue_size = len(self.queue)
        # Intentionally keep flush quiet; batch writer can be noisy during scraping.
        
        success_count = 0
        failed_count = 0
        
        # Measure flush time if metrics available
        measure_ctx = (
            self.metrics.measure('batch_flush')
            if self.metrics else None
        )
        
        if measure_ctx:
            measure_ctx.__enter__()
        
        try:
            # Process queue
            while self.queue:
                profile = self.queue.popleft()
                
                try:
                    result = self.sheets.write_profile(profile)
                    status = result.get('status', 'error')
                    
                    if status in {'new', 'updated', 'unchanged'}:
                        success_count += 1
                    else:
                        failed_count += 1
                        # Re-queue failed write (optional)
                        # self.queue.append(profile)
                
                except Exception as e:
                    log_msg(
                        f"Failed to write profile: {e}",
                        "ERROR"
                    )
                    failed_count += 1
                
                # Small delay between writes to avoid burst
                time.sleep(0.5)
            
            # Update statistics
            self.stats['flushed'] += success_count
            self.stats['failed'] += failed_count
            self.stats['batches'] += 1
            self.last_flush_time = time.time()
            
            log_msg(
                f"Batch flushed: {success_count} success, {failed_count} failed",
                "OK" if failed_count == 0 else "WARNING"
            )
            
            return {
                'success': success_count,
                'failed': failed_count,
                'total': queue_size
            }
        
        finally:
            if measure_ctx:
                measure_ctx.__exit__(None, None, None)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get batch writer statistics.
        
        Returns:
            Dictionary with statistics
        
        Example:
            >>> stats = writer.get_stats()
            >>> print(f"Queued: {stats['queued']}")
            >>> print(f"Flushed: {stats['flushed']}")
        """
        return {
            **self.stats,
            'queue_size': len(self.queue)
        }
    
    def clear_queue(self):
        """
        Clear all queued profiles without writing.
        
        ⚠️ Warning: This discards all pending writes!
        
        Example:
            >>> writer.clear_queue()  # Discard all pending
        """
        queue_size = len(self.queue)
        self.queue.clear()
        log_msg(
            f"Cleared {queue_size} queued profile(s) (not written)",
            "WARNING"
        )
    
    def __enter__(self):
        """Context manager entry point."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point - auto-flush.
        
        Ensures all queued profiles are written even if exception occurred.
        """
        if self.queue:
            self.flush()
        
        # Print final statistics
        stats = self.get_stats()
        # Keep context-exit summary quiet; flush() already reports success/failure.
        
        return False  # Don't suppress exceptions
    
    def __del__(self):
        """Destructor - warn if queue not empty."""
        if self.queue:
            log_msg(
                f"Warning: {len(self.queue)} profile(s) in queue were not flushed!",
                "WARNING"
            )


class SmartBatchWriter(SheetsBatchWriter):
    """
    Enhanced batch writer with adaptive batch sizing.
    
    Automatically adjusts batch size based on API response times
    to optimize throughput while avoiding rate limits.
    
    Example:
        >>> writer = SmartBatchWriter(sheets, initial_batch_size=10)
        >>> for profile in profiles:
        ...     writer.add_profile(profile)
    """
    
    def __init__(
        self,
        sheets_manager,
        initial_batch_size: int = 10,
        min_batch_size: int = 5,
        max_batch_size: int = 20,
        **kwargs
    ):
        """
        Initialize smart batch writer.
        
        Args:
            sheets_manager: SheetsManager instance
            initial_batch_size: Starting batch size
            min_batch_size: Minimum batch size (during throttling)
            max_batch_size: Maximum batch size (during optimal conditions)
            **kwargs: Additional args for SheetsBatchWriter
        """
        super().__init__(sheets_manager, initial_batch_size, **kwargs)
        
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.initial_batch_size = initial_batch_size
        
        # Performance tracking
        self.flush_times: List[float] = []
        self.api_errors = 0
    
    def flush(self) -> Dict[str, int]:
        """Flush with adaptive batch size adjustment."""
        start_time = time.time()
        
        result = super().flush()
        
        flush_time = time.time() - start_time
        self.flush_times.append(flush_time)
        
        # Keep last 5 flush times for averaging
        if len(self.flush_times) > 5:
            self.flush_times.pop(0)
        
        # Adjust batch size based on performance
        self._adjust_batch_size(result, flush_time)
        
        return result
    
    def _adjust_batch_size(self, result: Dict[str, int], flush_time: float):
        """
        Adjust batch size based on performance.
        
        Logic:
        - If errors: decrease batch size (reduce load)
        - If fast: increase batch size (optimize throughput)
        - If slow: decrease batch size (avoid timeout)
        """
        if result['failed'] > 0:
            # Errors occurred - reduce batch size
            self.api_errors += result['failed']
            new_size = max(
                self.min_batch_size,
                int(self.batch_size * 0.8)
            )
            if new_size != self.batch_size:
                log_msg(
                    f"Reducing batch size: {self.batch_size} → {new_size} "
                    f"(errors: {result['failed']})",
                    "WARNING"
                )
                self.batch_size = new_size
        
        elif flush_time < 3.0 and self.batch_size < self.max_batch_size:
            # Fast flush - can increase batch size
            new_size = min(
                self.max_batch_size,
                self.batch_size + 2
            )
            log_msg(
                f"Increasing batch size: {self.batch_size} → {new_size} "
                f"(fast flush: {flush_time:.1f}s)",
                "INFO"
            )
            self.batch_size = new_size
        
        elif flush_time > 10.0 and self.batch_size > self.min_batch_size:
            # Slow flush - decrease batch size
            new_size = max(
                self.min_batch_size,
                int(self.batch_size * 0.9)
            )
            log_msg(
                f"Reducing batch size: {self.batch_size} → {new_size} "
                f"(slow flush: {flush_time:.1f}s)",
                "WARNING"
            )
            self.batch_size = new_size


# Convenience function for quick usage
def batch_write_profiles(
    sheets_manager,
    profiles: List[Dict[str, Any]],
    batch_size: int = 10,
    smart: bool = False
) -> Dict[str, int]:
    """
    Write multiple profiles in batches.
    
    Convenience function for one-shot batch writing without
    managing the writer object.
    
    Args:
        sheets_manager: SheetsManager instance
        profiles: List of profile dictionaries
        batch_size: Batch size for writing
        smart: Use SmartBatchWriter (adaptive sizing)
    
    Returns:
        Dictionary with write statistics
    
    Example:
        >>> profiles = [profile1, profile2, profile3, ...]
        >>> result = batch_write_profiles(sheets, profiles, batch_size=10)
        >>> print(f"Success: {result['success']}/{result['total']}")
    """
    WriterClass = SmartBatchWriter if smart else SheetsBatchWriter
    
    total_success = 0
    total_failed = 0
    
    with WriterClass(sheets_manager, batch_size) as writer:
        for profile in profiles:
            writer.add_profile(profile)
    
    # Get final stats
    stats = writer.get_stats()
    
    return {
        'success': stats['flushed'],
        'failed': stats['failed'],
        'total': len(profiles)
    }
