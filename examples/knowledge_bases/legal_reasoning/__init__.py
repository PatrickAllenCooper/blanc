"""
Legal Reasoning Knowledge Base - Curated for DeFAb.

Covers contract law, tort law, and property law with natural defeaters
and hierarchical legal reasoning chains.

Author: Patrick Cooper
Date: 2026-02-12
"""

from .legal_base import (
    create_legal_base,
    create_legal_full,
    get_legal_stats,
)

__all__ = [
    'create_legal_base',
    'create_legal_full',
    'get_legal_stats',
]
