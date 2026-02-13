"""
Unit tests for response caching system.

Tests:
- Cache key generation
- Set/get operations
- Cache persistence
- Statistics tracking
- Hit/miss tracking

Author: Patrick Cooper
Date: 2026-02-13
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiments"))

from response_cache import ResponseCache, CacheEntry
from model_interface import ModelResponse


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def fresh_cache(temp_cache_dir):
    """Create a fresh cache for each test."""
    cache = ResponseCache(temp_cache_dir)
    cache.clear()  # Ensure clean state
    return cache


@pytest.fixture
def sample_response():
    """Create a sample model response."""
    return ModelResponse(
        text="Test response",
        model="gpt-4o",
        tokens_input=10,
        tokens_output=20,
        cost=0.001,
        latency=0.5
    )


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_make_key_deterministic(self, temp_cache_dir):
        """Test that key generation is deterministic."""
        cache = ResponseCache(temp_cache_dir)
        
        key1 = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        key2 = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        assert key1 == key2
    
    def test_make_key_different_for_different_params(self, temp_cache_dir):
        """Test that different parameters produce different keys."""
        cache = ResponseCache(temp_cache_dir)
        
        key1 = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        key2 = cache.make_key("inst-002", "gpt-4o", "M4", "direct")
        key3 = cache.make_key("inst-001", "claude", "M4", "direct")
        key4 = cache.make_key("inst-001", "gpt-4o", "M2", "direct")
        key5 = cache.make_key("inst-001", "gpt-4o", "M4", "cot")
        
        keys = [key1, key2, key3, key4, key5]
        assert len(set(keys)) == 5  # All unique
    
    def test_make_key_with_prompt(self, temp_cache_dir):
        """Test key generation with prompt hash."""
        cache = ResponseCache(temp_cache_dir)
        
        key1 = cache.make_key("inst-001", "gpt-4o", "M4", "direct", prompt="Test prompt")
        key2 = cache.make_key("inst-001", "gpt-4o", "M4", "direct", prompt="Different prompt")
        
        assert key1 != key2


class TestCacheOperations:
    """Test basic cache operations."""
    
    def test_set_and_get(self, temp_cache_dir, sample_response):
        """Test setting and getting from cache."""
        cache = ResponseCache(temp_cache_dir)
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        # Initially not in cache
        assert cache.get(key) is None
        
        # Set in cache
        cache.set(key, sample_response)
        
        # Now should be retrievable
        cached = cache.get(key)
        assert cached is not None
        assert cached.text == sample_response.text
        assert cached.model == sample_response.model
    
    def test_has_method(self, fresh_cache, sample_response):
        """Test has() method."""
        cache = fresh_cache
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        assert not cache.has(key)
        
        cache.set(key, sample_response)
        
        assert cache.has(key)
    
    def test_cache_size(self, fresh_cache, sample_response):
        """Test cache size tracking."""
        cache = fresh_cache
        
        assert cache.size == 0
        
        cache.set(cache.make_key("inst-001", "gpt-4o", "M4", "direct"), sample_response)
        assert cache.size == 1
        
        cache.set(cache.make_key("inst-002", "gpt-4o", "M4", "direct"), sample_response)
        assert cache.size == 2


class TestCachePersistence:
    """Test cache persistence."""
    
    def test_cache_persists_across_instances(self, temp_cache_dir, sample_response):
        """Test that cache persists when creating new cache instance."""
        key = "test-key"
        
        # Create cache and set value
        cache1 = ResponseCache(temp_cache_dir)
        cache1.set(key, sample_response)
        
        # Create new cache instance
        cache2 = ResponseCache(temp_cache_dir)
        
        # Should still have the cached value
        assert cache2.has(key)
        cached = cache2.get(key)
        assert cached.text == sample_response.text


class TestCacheStatistics:
    """Test cache statistics tracking."""
    
    def test_hit_miss_tracking(self, fresh_cache, sample_response):
        """Test that hits and misses are tracked."""
        cache = fresh_cache
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        # Miss
        cache.get(key)
        assert cache.stats['cache_misses'] == 1
        assert cache.stats['cache_hits'] == 0
        
        # Set
        cache.set(key, sample_response)
        
        # Hit
        cache.get(key)
        assert cache.stats['cache_hits'] == 1
        
        # Another hit
        cache.get(key)
        assert cache.stats['cache_hits'] == 2
    
    def test_cost_savings_tracking(self, fresh_cache):
        """Test that cost savings are tracked."""
        cache = fresh_cache
        
        response = ModelResponse(
            text="Test",
            model="gpt-4o",
            tokens_input=10,
            tokens_output=20,
            cost=0.05,  # $0.05 per query
            latency=1.0
        )
        
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        cache.set(key, response)
        
        # First hit
        cache.get(key)
        assert cache.stats['total_cost_saved'] == 0.05
        
        # Second hit
        cache.get(key)
        assert cache.stats['total_cost_saved'] == 0.10
    
    def test_time_savings_tracking(self, fresh_cache):
        """Test that time savings are tracked."""
        cache = fresh_cache
        
        response = ModelResponse(
            text="Test",
            model="gpt-4o",
            tokens_input=10,
            tokens_output=20,
            cost=0.01,
            latency=2.5  # 2.5 seconds
        )
        
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        cache.set(key, response)
        
        cache.get(key)
        assert cache.stats['total_time_saved'] == 2.5
    
    def test_hit_rate_calculation(self, fresh_cache, sample_response):
        """Test hit rate calculation."""
        cache = fresh_cache
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        # 1 miss
        cache.get(key)
        assert cache.hit_rate == 0.0
        
        # Set and hit
        cache.set(key, sample_response)
        cache.get(key)
        
        # 1 hit out of 2 total = 50%
        assert cache.hit_rate == 0.5
    
    def test_get_statistics(self, fresh_cache, sample_response):
        """Test get_statistics() method."""
        cache = fresh_cache
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        cache.set(key, sample_response)
        cache.get(key)
        
        stats = cache.get_statistics()
        
        assert 'cache_size' in stats
        assert 'total_queries' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_rate' in stats
        assert 'cost_saved' in stats
        assert 'time_saved' in stats


class TestCacheClear:
    """Test cache clearing."""
    
    def test_clear_removes_all_entries(self, fresh_cache, sample_response):
        """Test that clear removes all cache entries."""
        cache = fresh_cache
        
        # Add some entries
        cache.set(cache.make_key("inst-001", "gpt-4o", "M4", "direct"), sample_response)
        cache.set(cache.make_key("inst-002", "gpt-4o", "M4", "direct"), sample_response)
        
        assert cache.size == 2
        
        # Clear
        cache.clear()
        
        assert cache.size == 0
    
    def test_clear_resets_statistics(self, fresh_cache, sample_response):
        """Test that clear resets statistics."""
        cache = fresh_cache
        key = cache.make_key("inst-001", "gpt-4o", "M4", "direct")
        
        cache.set(key, sample_response)
        cache.get(key)
        
        assert cache.stats['cache_hits'] > 0
        
        cache.clear()
        
        assert cache.stats['cache_hits'] == 0
        assert cache.stats['cache_misses'] == 0
        assert cache.stats['total_cost_saved'] == 0.0


class TestCacheEntry:
    """Test CacheEntry dataclass."""
    
    def test_cache_entry_to_dict(self, sample_response):
        """Test converting cache entry to dict."""
        entry = CacheEntry(
            response=sample_response,
            cache_key="test-key",
            created_at="2026-02-13T12:00:00",
            hits=5
        )
        
        data = entry.to_dict()
        
        assert data['cache_key'] == "test-key"
        assert data['hits'] == 5
        assert 'response' in data
    
    def test_cache_entry_from_dict(self, sample_response):
        """Test creating cache entry from dict."""
        data = {
            'response': sample_response.to_dict(),
            'cache_key': 'test-key',
            'created_at': '2026-02-13T12:00:00',
            'hits': 5
        }
        
        entry = CacheEntry.from_dict(data)
        
        assert entry.cache_key == 'test-key'
        assert entry.hits == 5
        assert entry.response.text == sample_response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
