"""
Knowledge base registry for managing available datasets.

Provides metadata and access to historical and modern knowledge bases
for research and benchmarking.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class KnowledgeBaseMetadata:
    """Metadata for a knowledge base."""
    
    name: str
    domain: str
    format: str  # 'prolog', 'asp', 'cycl', etc.
    path: Path
    description: str
    size_estimate: Optional[int] = None  # Number of facts/rules
    source_url: Optional[str] = None
    citation: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = field(default_factory=list)
    license: Optional[str] = None


class KnowledgeBaseRegistry:
    """
    Registry of available knowledge bases.
    
    Manages metadata for historical and modern knowledge bases,
    providing discovery and loading capabilities.
    """
    
    _instance = None
    _registry: Dict[str, KnowledgeBaseMetadata] = {}
    
    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, kb: KnowledgeBaseMetadata) -> None:
        """
        Register a knowledge base.
        
        Args:
            kb: Knowledge base metadata
        """
        cls._registry[kb.name] = kb
    
    @classmethod
    def get(cls, name: str) -> Optional[KnowledgeBaseMetadata]:
        """
        Get knowledge base metadata by name.
        
        Args:
            name: Knowledge base name
            
        Returns:
            Metadata or None if not found
        """
        return cls._registry.get(name)
    
    @classmethod
    def list_all(cls) -> List[KnowledgeBaseMetadata]:
        """
        List all registered knowledge bases.
        
        Returns:
            List of all knowledge base metadata
        """
        return list(cls._registry.values())
    
    @classmethod
    def list_by_domain(cls, domain: str) -> List[KnowledgeBaseMetadata]:
        """
        List knowledge bases by domain.
        
        Args:
            domain: Domain name (e.g., 'medical', 'legal')
            
        Returns:
            List of matching knowledge bases
        """
        return [kb for kb in cls._registry.values() if kb.domain == domain]
    
    @classmethod
    def list_by_format(cls, format: str) -> List[KnowledgeBaseMetadata]:
        """
        List knowledge bases by format.
        
        Args:
            format: Format name (e.g., 'prolog', 'asp')
            
        Returns:
            List of matching knowledge bases
        """
        return [kb for kb in cls._registry.values() if kb.format == format]
    
    @classmethod
    def search(cls, query: str) -> List[KnowledgeBaseMetadata]:
        """
        Search knowledge bases by keyword.
        
        Args:
            query: Search query
            
        Returns:
            List of matching knowledge bases
        """
        query_lower = query.lower()
        results = []
        
        for kb in cls._registry.values():
            if (query_lower in kb.name.lower() or 
                query_lower in kb.domain.lower() or
                query_lower in kb.description.lower() or
                any(query_lower in tag.lower() for tag in kb.tags)):
                results.append(kb)
                
        return results


def register_kb(
    name: str,
    domain: str,
    format: str,
    path: Path,
    description: str,
    **kwargs
) -> None:
    """
    Convenience function to register a knowledge base.
    
    Args:
        name: Knowledge base name
        domain: Domain (medical, legal, common-sense, etc.)
        format: Format (prolog, asp, cycl)
        path: Path to knowledge base file/directory
        description: Description of the knowledge base
        **kwargs: Additional metadata
    """
    kb = KnowledgeBaseMetadata(
        name=name,
        domain=domain,
        format=format,
        path=Path(path),
        description=description,
        **kwargs
    )
    KnowledgeBaseRegistry.register(kb)


# Register built-in knowledge bases
def register_builtin_kbs():
    """Register built-in/example knowledge bases."""
    
    # Example: Tweety knowledge base
    register_kb(
        name="tweety",
        domain="example",
        format="prolog",
        path=Path("examples/tweety.pl"),
        description="Classic Tweety the penguin example for defeasible reasoning",
        size_estimate=10,
        difficulty="easy",
        tags=["defeasible", "example", "tutorial"]
    )
    
    # Example: Medical diagnosis
    register_kb(
        name="medical_simple",
        domain="medical",
        format="prolog",
        path=Path("examples/medical.pl"),
        description="Simple medical diagnosis rules",
        size_estimate=20,
        difficulty="easy",
        tags=["medical", "diagnosis", "example"]
    )


# Auto-register built-ins on import
register_builtin_kbs()
