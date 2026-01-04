"""
Performance Metrics Tracker

Tracks detailed performance metrics for optimization and monitoring.
Provides timing measurements, counters, and summary statistics.

Usage:
    from utils.metrics import PerformanceMetrics, measure_time
    
    metrics = PerformanceMetrics()
    
    with metrics.measure('scrape_profile'):
        scrape_profile()
    
    metrics.increment('profiles_scraped')
    print(metrics.get_summary())
"""

import time
import json
from collections import defaultdict
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime


class PerformanceMetrics:
    """
    Track performance metrics for scraping operations.
    
    This class provides utilities for measuring operation timings,
    counting events, and generating summary statistics.
    """
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.errors: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()
        self.metadata: Dict[str, Any] = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager to measure operation time.
        
        Args:
            operation_name: Name of the operation being measured
        
        Yields:
            None
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> with metrics.measure('scrape_profile'):
            ...     scrape_profile(nickname)
            >>> 
            >>> with metrics.measure('write_to_sheet'):
            ...     sheet.update(data)
        """
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.timings[operation_name].append(duration)
    
    def record_timing(self, operation_name: str, duration: float):
        """
        Manually record a timing measurement.
        
        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> start = time.time()
            >>> # ... do work ...
            >>> duration = time.time() - start
            >>> metrics.record_timing('custom_operation', duration)
        """
        self.timings[operation_name].append(duration)
    
    def increment(self, counter_name: str, amount: int = 1):
        """
        Increment a counter.
        
        Args:
            counter_name: Name of the counter
            amount: Amount to increment by (default: 1)
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> metrics.increment('profiles_scraped')
            >>> metrics.increment('api_calls', 5)
        """
        self.counters[counter_name] += amount
    
    def record_error(self, error_type: str):
        """
        Record an error occurrence.
        
        Args:
            error_type: Type/category of error
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> try:
            ...     scrape_profile()
            ... except TimeoutError:
            ...     metrics.record_error('timeout')
        """
        self.errors[error_type] += 1
    
    def set_metadata(self, key: str, value: Any):
        """
        Set metadata for this metrics session.
        
        Args:
            key: Metadata key
            value: Metadata value
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> metrics.set_metadata('mode', 'target')
            >>> metrics.set_metadata('max_profiles', 50)
        """
        self.metadata[key] = value
    
    def get_timing_stats(self, operation_name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a specific operation.
        
        Args:
            operation_name: Name of the operation
        
        Returns:
            Dictionary with timing statistics, or None if no data
        
        Example:
            >>> stats = metrics.get_timing_stats('scrape_profile')
            >>> print(f"Average: {stats['avg_seconds']:.2f}s")
            >>> print(f"Total: {stats['total_seconds']:.2f}s")
        """
        times = self.timings.get(operation_name)
        if not times:
            return None
        
        return {
            'count': len(times),
            'total_seconds': sum(times),
            'avg_seconds': sum(times) / len(times),
            'min_seconds': min(times),
            'max_seconds': max(times),
            'median_seconds': sorted(times)[len(times) // 2]
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of all metrics.
        
        Returns:
            Dictionary with all metrics data
        
        Example:
            >>> summary = metrics.get_summary()
            >>> print(json.dumps(summary, indent=2))
        """
        total_runtime = time.time() - self.start_time
        
        summary = {
            'metadata': self.metadata,
            'runtime': {
                'total_seconds': total_runtime,
                'total_minutes': total_runtime / 60,
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.now().isoformat()
            },
            'operations': {},
            'counters': dict(self.counters),
            'errors': dict(self.errors)
        }
        
        # Add timing statistics for each operation
        for operation_name in self.timings.keys():
            stats = self.get_timing_stats(operation_name)
            if stats:
                summary['operations'][operation_name] = stats
        
        return summary
    
    def print_summary(self):
        """
        Print formatted summary to console.
        
        Example:
            >>> metrics.print_summary()
            
            === Performance Metrics Summary ===
            
            Total Runtime: 5m 23s
            
            Operations:
              scrape_profile:
                Count: 50
                Total: 245.3s
                Average: 4.9s
                Min: 2.1s
                Max: 12.3s
            ...
        """
        from utils.ui import console
        from rich.table import Table
        from rich import box
        
        summary = self.get_summary()
        
        console.print("\n" + "=" * 70)
        console.print("📊 [bold cyan]Performance Metrics Summary[/bold cyan]")
        console.print("=" * 70 + "\n")
        
        # Runtime
        runtime = summary['runtime']
        console.print(
            f"⏱️  [yellow]Total Runtime:[/yellow] "
            f"{int(runtime['total_minutes'])}m {int(runtime['total_seconds'] % 60)}s"
        )
        console.print()
        
        # Operations
        if summary['operations']:
            table = Table(
                title="Operation Timings",
                show_header=True,
                header_style="bold magenta",
                box=box.SIMPLE
            )
            
            table.add_column("Operation", style="cyan")
            table.add_column("Count", justify="right", style="yellow")
            table.add_column("Total", justify="right", style="green")
            table.add_column("Average", justify="right", style="blue")
            table.add_column("Min/Max", justify="right", style="dim")
            
            for op_name, stats in summary['operations'].items():
                table.add_row(
                    op_name,
                    str(stats['count']),
                    f"{stats['total_seconds']:.1f}s",
                    f"{stats['avg_seconds']:.2f}s",
                    f"{stats['min_seconds']:.1f}s / {stats['max_seconds']:.1f}s"
                )
            
            console.print(table)
            console.print()
        
        # Counters
        if summary['counters']:
            console.print("[bold cyan]Counters:[/bold cyan]")
            for name, value in summary['counters'].items():
                console.print(f"  • {name}: [yellow]{value}[/yellow]")
            console.print()
        
        # Errors
        if summary['errors']:
            console.print("[bold red]Errors:[/bold red]")
            for error_type, count in summary['errors'].items():
                console.print(f"  • {error_type}: [red]{count}[/red]")
            console.print()
        
        console.print("=" * 70 + "\n")
    
    def save_to_file(self, filepath: str):
        """
        Save metrics to JSON file.
        
        Args:
            filepath: Path to save JSON file
        
        Example:
            >>> metrics.save_to_file('logs/metrics_20260104.json')
        """
        summary = self.get_summary()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
    
    def reset(self):
        """
        Reset all metrics (useful for multi-phase runs).
        
        Example:
            >>> # Phase 1
            >>> metrics.measure(...)
            >>> metrics.print_summary()
            >>> 
            >>> # Reset for Phase 2
            >>> metrics.reset()
            >>> metrics.measure(...)
        """
        self.timings.clear()
        self.counters.clear()
        self.errors.clear()
        self.metadata.clear()
        self.start_time = time.time()


# Global metrics instance (optional convenience)
_global_metrics: Optional[PerformanceMetrics] = None


def get_global_metrics() -> PerformanceMetrics:
    """
    Get or create global metrics instance.
    
    Returns:
        Global PerformanceMetrics instance
    
    Example:
        >>> from utils.metrics import get_global_metrics
        >>> metrics = get_global_metrics()
        >>> metrics.increment('profiles')
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PerformanceMetrics()
    return _global_metrics


def reset_global_metrics():
    """Reset global metrics instance."""
    global _global_metrics
    if _global_metrics:
        _global_metrics.reset()


# Decorator for automatic timing measurement
def measure_time(operation_name: Optional[str] = None, metrics: Optional[PerformanceMetrics] = None):
    """
    Decorator to automatically measure function execution time.
    
    Args:
        operation_name: Name for the operation (default: function name)
        metrics: Metrics instance to use (default: global instance)
    
    Returns:
        Decorated function
    
    Example:
        >>> @measure_time('scrape_profile')
        ... def scrape_profile(nickname):
        ...     # ... scraping logic ...
        ...     pass
        
        >>> @measure_time()  # Uses function name
        ... def extract_data():
        ...     pass
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            m = metrics or get_global_metrics()
            op_name = operation_name or func.__name__
            
            with m.measure(op_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
