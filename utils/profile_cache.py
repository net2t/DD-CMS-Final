"""
Profile Cache System - Avoid Re-scraping Recent Profiles

Implements file-based caching for scraped profiles to avoid
re-scraping profiles that were recently updated.

Usage:
    from utils.profile_cache import ProfileCache
    
    cache = ProfileCache(ttl_hours=24)
    
    # Check cache before scraping
    cached = cache.get('user123')
    if cached:
        use_cached_profile(cached)
    else:
        profile = scrape_profile('user123')
        cache.set('user123', profile)
"""

import pickle
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from utils.ui import log_msg


class ProfileCache:
    """
    File-based cache for scraped profiles.
    
    This class provides persistent caching of profile data to avoid
    re-scraping profiles that haven't changed. Uses pickle for fast
    serialization and includes TTL (time-to-live) support.
    
    Example:
        >>> cache = ProfileCache(cache_dir='cache', ttl_hours=24)
        >>> 
        >>> # Get cached profile (if fresh)
        >>> profile = cache.get('user123')
        >>> if profile:
        ...     print("Using cached profile")
        >>> else:
        ...     profile = scrape_profile('user123')
        ...     cache.set('user123', profile)
        >>> 
        >>> # Clear old cache entries
        >>> cache.cleanup()
    """
    
    def __init__(
        self,
        cache_dir: str = "cache",
        ttl_hours: float = 24.0,
        format: str = "pickle"  # "pickle" or "json"
    ):
        """
        Initialize profile cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours (0 = never expire)
            format: Storage format ("pickle" or "json")
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(hours=ttl_hours) if ttl_hours > 0 else None
        self.format = format.lower()
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'expired': 0,
            'errors': 0
        }
    
    def _get_cache_path(self, nickname: str) -> Path:
        """
        Get cache file path for a nickname.
        
        Uses hash to avoid filesystem issues with special characters.
        
        Args:
            nickname: Profile nickname
        
        Returns:
            Path to cache file
        """
        # Normalize nickname
        nick_lower = nickname.lower().strip()
        
        # Create hash for filename (avoid special char issues)
        nick_hash = hashlib.md5(nick_lower.encode()).hexdigest()[:16]
        
        # Filename: hash_nickname.ext
        ext = 'pkl' if self.format == 'pickle' else 'json'
        filename = f"{nick_hash}_{nick_lower}.{ext}"
        
        return self.cache_dir / filename
    
    def get(self, nickname: str) -> Optional[Dict[str, Any]]:
        """
        Get cached profile if it exists and is fresh.
        
        Args:
            nickname: Profile nickname to retrieve
        
        Returns:
            Profile dictionary if cached and fresh, None otherwise
        
        Example:
            >>> profile = cache.get('user123')
            >>> if profile:
            ...     print(f"Cached: {profile['CITY']}")
            ... else:
            ...     print("Not in cache or expired")
        """
        cache_file = self._get_cache_path(nickname)
        
        # Check if file exists
        if not cache_file.exists():
            self.stats['misses'] += 1
            return None
        
        try:
            # Load cache entry
            if self.format == 'pickle':
                with open(cache_file, 'rb') as f:
                    cache_entry = pickle.load(f)
            else:  # json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
            
            # Check TTL
            if self.ttl:
                cached_time = cache_entry.get('_cached_at')
                if not cached_time:
                    self.stats['errors'] += 1
                    return None
                
                # Convert string to datetime if needed
                if isinstance(cached_time, str):
                    cached_time = datetime.fromisoformat(cached_time)
                
                age = datetime.now() - cached_time
                if age > self.ttl:
                    self.stats['expired'] += 1
                    # Delete expired cache
                    cache_file.unlink()
                    return None
            
            # Cache hit
            self.stats['hits'] += 1
            return cache_entry.get('profile')
        
        except Exception as e:
            log_msg(f"Cache read error for {nickname}: {e}", "WARNING")
            self.stats['errors'] += 1
            return None
    
    def set(self, nickname: str, profile_data: Dict[str, Any]):
        """
        Cache a profile.
        
        Args:
            nickname: Profile nickname
            profile_data: Profile dictionary to cache
        
        Example:
            >>> profile = scrape_profile('user123')
            >>> cache.set('user123', profile)
        """
        cache_file = self._get_cache_path(nickname)
        
        try:
            cache_entry = {
                'profile': profile_data,
                '_cached_at': datetime.now(),
                '_nickname': nickname
            }
            
            # Save to file
            if self.format == 'pickle':
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_entry, f)
            else:  # json
                # Convert datetime to string for JSON
                cache_entry['_cached_at'] = cache_entry['_cached_at'].isoformat()
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_entry, f, indent=2)
            
            self.stats['sets'] += 1
        
        except Exception as e:
            log_msg(f"Cache write error for {nickname}: {e}", "WARNING")
            self.stats['errors'] += 1
    
    def delete(self, nickname: str) -> bool:
        """
        Delete a cached profile.
        
        Args:
            nickname: Profile nickname to delete
        
        Returns:
            True if deleted, False if not found
        
        Example:
            >>> cache.delete('user123')
        """
        cache_file = self._get_cache_path(nickname)
        
        if cache_file.exists():
            try:
                cache_file.unlink()
                return True
            except Exception as e:
                log_msg(f"Cache delete error for {nickname}: {e}", "WARNING")
                return False
        
        return False
    
    def exists(self, nickname: str) -> bool:
        """
        Check if a profile is cached (regardless of freshness).
        
        Args:
            nickname: Profile nickname to check
        
        Returns:
            True if cached, False otherwise
        """
        cache_file = self._get_cache_path(nickname)
        return cache_file.exists()
    
    def is_fresh(self, nickname: str) -> bool:
        """
        Check if a cached profile is fresh (within TTL).
        
        Args:
            nickname: Profile nickname to check
        
        Returns:
            True if fresh, False if expired or not cached
        """
        profile = self.get(nickname)
        return profile is not None
    
    def cleanup(self, force_all: bool = False) -> int:
        """
        Clean up expired cache entries.
        
        Args:
            force_all: If True, delete ALL cache entries
        
        Returns:
            Number of entries deleted
        
        Example:
            >>> # Delete expired entries
            >>> deleted = cache.cleanup()
            >>> print(f"Deleted {deleted} expired entries")
            >>> 
            >>> # Delete all cache
            >>> cache.cleanup(force_all=True)
        """
        deleted = 0
        
        try:
            ext = 'pkl' if self.format == 'pickle' else 'json'
            cache_files = list(self.cache_dir.glob(f'*.{ext}'))
            
            for cache_file in cache_files:
                should_delete = force_all
                
                if not should_delete and self.ttl:
                    try:
                        # Load and check age
                        if self.format == 'pickle':
                            with open(cache_file, 'rb') as f:
                                entry = pickle.load(f)
                        else:
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                entry = json.load(f)
                        
                        cached_time = entry.get('_cached_at')
                        if isinstance(cached_time, str):
                            cached_time = datetime.fromisoformat(cached_time)
                        
                        if cached_time:
                            age = datetime.now() - cached_time
                            should_delete = age > self.ttl
                    
                    except Exception:
                        # If we can't read it, delete it
                        should_delete = True
                
                if should_delete:
                    cache_file.unlink()
                    deleted += 1
            
            log_msg(f"Cache cleanup: {deleted} entries deleted", "INFO")
            return deleted
        
        except Exception as e:
            log_msg(f"Cache cleanup error: {e}", "ERROR")
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        
        Example:
            >>> stats = cache.get_stats()
            >>> print(f"Hit rate: {stats['hit_rate']:.1%}")
            >>> print(f"Size: {stats['size']} entries")
        """
        # Count cache files
        ext = 'pkl' if self.format == 'pickle' else 'json'
        cache_files = list(self.cache_dir.glob(f'*.{ext}'))
        cache_size = len(cache_files)
        
        # Calculate hit rate
        total_reads = self.stats['hits'] + self.stats['misses']
        hit_rate = (
            self.stats['hits'] / total_reads
            if total_reads > 0 else 0.0
        )
        
        return {
            'size': cache_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'expired': self.stats['expired'],
            'errors': self.stats['errors'],
            'hit_rate': hit_rate
        }
    
    def print_stats(self):
        """
        Print formatted cache statistics.
        
        Example:
            >>> cache.print_stats()
            
            Cache Statistics:
              Size: 150 entries
              Hits: 120 (80.0%)
              Misses: 30 (20.0%)
              ...
        """
        stats = self.get_stats()
        
        print("\n" + "=" * 50)
        print("📊 Cache Statistics")
        print("=" * 50)
        print(f"  Size: {stats['size']} entries")
        print(f"  Hits: {stats['hits']} ({stats['hit_rate']:.1%})")
        print(f"  Misses: {stats['misses']}")
        print(f"  Sets: {stats['sets']}")
        print(f"  Expired: {stats['expired']}")
        print(f"  Errors: {stats['errors']}")
        print("=" * 50 + "\n")


class SmartCache(ProfileCache):
    """
    Enhanced cache with automatic cleanup and statistics tracking.
    
    Automatically cleans up expired entries during get operations
    and provides detailed statistics.
    
    Example:
        >>> cache = SmartCache(ttl_hours=24, auto_cleanup_threshold=100)
        >>> profile = cache.get('user123')  # Auto-cleanup if needed
    """
    
    def __init__(
        self,
        cache_dir: str = "cache",
        ttl_hours: float = 24.0,
        format: str = "pickle",
        auto_cleanup_threshold: int = 100
    ):
        """
        Initialize smart cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours
            format: Storage format ("pickle" or "json")
            auto_cleanup_threshold: Auto-cleanup after N operations
        """
        super().__init__(cache_dir, ttl_hours, format)
        
        self.auto_cleanup_threshold = auto_cleanup_threshold
        self.operations_since_cleanup = 0
    
    def get(self, nickname: str) -> Optional[Dict[str, Any]]:
        """Get with auto-cleanup."""
        result = super().get(nickname)
        
        self.operations_since_cleanup += 1
        
        # Auto-cleanup if threshold reached
        if self.operations_since_cleanup >= self.auto_cleanup_threshold:
            log_msg("Auto-cleanup threshold reached, cleaning cache...", "INFO")
            self.cleanup()
            self.operations_since_cleanup = 0
        
        return result


# Convenience function for quick caching
def with_cache(
    cache: ProfileCache,
    nickname: str,
    scrape_func,
    force_refresh: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Get profile from cache or scrape if not cached/expired.
    
    Convenience function that handles cache check, scraping, and caching.
    
    Args:
        cache: ProfileCache instance
        nickname: Profile nickname
        scrape_func: Function to call if not cached (takes nickname)
        force_refresh: Skip cache and force scrape
    
    Returns:
        Profile dictionary
    
    Example:
        >>> from utils.profile_cache import ProfileCache, with_cache
        >>> 
        >>> cache = ProfileCache(ttl_hours=24)
        >>> 
        >>> def scrape_profile(nickname):
        ...     # Actual scraping logic
        ...     return profile_data
        >>> 
        >>> # Use cache
        >>> profile = with_cache(cache, 'user123', scrape_profile)
    """
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = cache.get(nickname)
        if cached:
            log_msg(f"Cache HIT for {nickname}", "INFO")
            return cached
    
    # Cache miss or force refresh - scrape
    log_msg(f"Cache MISS for {nickname}, scraping...", "INFO")
    profile = scrape_func(nickname)
    
    # Cache the result
    if profile:
        cache.set(nickname, profile)
    
    return profile
