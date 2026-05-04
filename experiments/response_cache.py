"""
Response caching system for LLM evaluation.

Provides persistent caching of model responses to:
- Avoid re-querying models (saves money and time)
- Enable reproducibility
- Support checkpoint/resume
- Track cache statistics

Author: Anonymous Authors
Date: 2026-02-13
"""

import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from model_interface import ModelResponse


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    
    response: ModelResponse
    cache_key: str
    created_at: str
    hits: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON."""
        return {
            'response': self.response.to_dict(),
            'cache_key': self.cache_key,
            'created_at': self.created_at,
            'hits': self.hits
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CacheEntry':
        """Load from dictionary."""
        return cls(
            response=ModelResponse.from_dict(data['response']),
            cache_key=data['cache_key'],
            created_at=data['created_at'],
            hits=data.get('hits', 0)
        )


class ResponseCache:
    """Persistent cache for model responses."""
    
    def __init__(self, cache_dir: str = "cache/responses"):
        """
        Initialize response cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_dir = Path("cache/metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.metadata_dir / "cache_index.json"
        self.stats_file = self.metadata_dir / "cache_stats.json"
        
        # Load index
        self.index = self._load_index()
        self.stats = self._load_stats()
    
    def _load_index(self) -> Dict[str, str]:
        """Load cache index (maps keys to file paths)."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """Save cache index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load cache statistics."""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_cost_saved': 0.0,
            'total_time_saved': 0.0
        }
    
    def _save_stats(self):
        """Save cache statistics."""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def make_key(
        self,
        instance_id: str,
        model: str,
        modality: str,
        strategy: str,
        prompt: Optional[str] = None,
        image_hashes: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate deterministic cache key.
        
        Args:
            instance_id: Instance identifier
            model: Model name
            modality: Modality (M1-M5)
            strategy: Prompting strategy
            prompt: Optional prompt text for extra uniqueness
            image_hashes: Optional list of image identity hashes for M5
            max_tokens: Generation budget (included when provided to prevent stale hits)
            temperature: Sampling temperature (included when provided)
            
        Returns:
            SHA256 hash as cache key
        """
        key_components = f"{instance_id}:{model}:{modality}:{strategy}"
        
        if prompt:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
            key_components += f":{prompt_hash}"

        if max_tokens is not None:
            key_components += f":mt{max_tokens}"
        if temperature is not None:
            key_components += f":t{temperature}"

        if image_hashes:
            img_hash = hashlib.sha256(
                "|".join(sorted(image_hashes)).encode()
            ).hexdigest()[:16]
            key_components += f":{img_hash}"

        # Generate SHA256 hash
        cache_key = hashlib.sha256(key_components.encode()).hexdigest()
        return cache_key
    
    def get(self, cache_key: str) -> Optional[ModelResponse]:
        """
        Retrieve cached response if exists.
        
        Args:
            cache_key: Cache key
            
        Returns:
            ModelResponse if cached, None otherwise
        """
        self.stats['total_queries'] += 1
        
        if cache_key in self.index:
            # Load from file
            filepath = Path(self.index[cache_key])
            
            if filepath.exists():
                with open(filepath, 'r') as f:
                    entry_data = json.load(f)
                
                entry = CacheEntry.from_dict(entry_data)
                
                # Update hit count
                entry.hits += 1
                
                # Save updated entry
                with open(filepath, 'w') as f:
                    json.dump(entry.to_dict(), f, indent=2)
                
                # Update stats
                self.stats['cache_hits'] += 1
                self.stats['total_cost_saved'] += entry.response.cost
                self.stats['total_time_saved'] += entry.response.latency
                self._save_stats()
                
                return entry.response
        
        # Cache miss
        self.stats['cache_misses'] += 1
        self._save_stats()
        return None
    
    def set(
        self,
        cache_key: str,
        response: ModelResponse
    ):
        """
        Store response in cache.
        
        Args:
            cache_key: Cache key
            response: Model response to cache
        """
        # Create cache entry
        entry = CacheEntry(
            response=response,
            cache_key=cache_key,
            created_at=datetime.now().isoformat(),
            hits=0
        )
        
        # Save to file
        filepath = self.cache_dir / f"{cache_key}.json"
        with open(filepath, 'w') as f:
            json.dump(entry.to_dict(), f, indent=2)
        
        # Update index
        self.index[cache_key] = str(filepath)
        self._save_index()
    
    def has(self, cache_key: str) -> bool:
        """Check if key is in cache."""
        return cache_key in self.index
    
    def clear(self):
        """Clear all cache entries."""
        # Remove all cache files
        for filepath in self.cache_dir.glob("*.json"):
            filepath.unlink()
        
        # Clear index
        self.index = {}
        self._save_index()
        
        # Reset stats
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_cost_saved': 0.0,
            'total_time_saved': 0.0
        }
        self._save_stats()
    
    @property
    def size(self) -> int:
        """Get number of cached entries."""
        return len(self.index)
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.stats['total_queries'] == 0:
            return 0.0
        return self.stats['cache_hits'] / self.stats['total_queries']
    
    def get_statistics(self) -> dict:
        """Get cache statistics."""
        return {
            'cache_size': self.size,
            'total_queries': self.stats['total_queries'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'hit_rate': f"{self.hit_rate:.1%}",
            'cost_saved': f"${self.stats['total_cost_saved']:.2f}",
            'time_saved': f"{self.stats['total_time_saved']:.1f}s"
        }


if __name__ == "__main__":
    # Test cache
    print("Response Cache Test")
    print("=" * 70)
    
    # Create cache
    cache = ResponseCache("cache/responses")
    
    # Create mock response
    response = ModelResponse(
        text="Test response",
        model="gpt-4o",
        tokens_input=10,
        tokens_output=20,
        cost=0.001,
        latency=0.5
    )
    
    # Test set/get
    key1 = cache.make_key("instance-001", "gpt-4o", "M4", "direct")
    
    print(f"Cache key: {key1[:16]}...")
    print(f"Initial size: {cache.size}")
    
    # Store
    cache.set(key1, response)
    print(f"After set: {cache.size}")
    
    # Retrieve
    cached = cache.get(key1)
    print(f"Retrieved: {cached.text if cached else 'None'}")
    
    # Test hit/miss
    cache.get(key1)  # Hit
    cache.get("nonexistent-key")  # Miss
    
    # Show stats
    print(f"\nCache Statistics:")
    for key, value in cache.get_statistics().items():
        print(f"  {key}: {value}")
    
    print("\n✅ Cache module working!")
