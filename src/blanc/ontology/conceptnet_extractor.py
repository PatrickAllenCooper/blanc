"""
ConceptNet5 extraction for biology domain.

Extracts behavioral defaults, taxonomic relations, and exceptions from
ConceptNet5 (21M edges) to create rich defeasible knowledge base.

Author: Patrick Cooper  
Date: 2026-02-11
"""

import gzip
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from blanc.core.theory import Theory, Rule, RuleType


class ConceptNetExtractor:
    """
    Extract biological knowledge from ConceptNet5.
    
    ConceptNet5 format (CSV, tab-separated):
        /a/[/r/Relation]/[start]/[end]/ <tab> relation <tab> start <tab> end <tab> metadata
    
    Example:
        /a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/... <tab> /r/CapableOf <tab> /c/en/bird <tab> /c/en/fly <tab> {"weight": 8.3}
    
    Strategy:
        1. Filter for English language (/c/en/)
        2. Filter for biological concepts (bird, animal, organism, etc.)
        3. Filter by confidence weight (> 2.0)
        4. Convert relations to Prolog rules:
           - IsA → isa(X, Y)
           - CapableOf → can_do(X, Y), then create behavioral rules
           - NotCapableOf → defeaters
           - HasProperty → property rules
    """
    
    def __init__(self, conceptnet_path: Path, weight_threshold: float = 2.0):
        """
        Initialize extractor.
        
        Args:
            conceptnet_path: Path to conceptnet-assertions-5.7.0.csv.gz
            weight_threshold: Minimum confidence weight (default: 2.0)
        """
        if not conceptnet_path.exists():
            raise FileNotFoundError(f"ConceptNet5 file not found: {conceptnet_path}")
        
        self.conceptnet_path = conceptnet_path
        self.weight_threshold = weight_threshold
        self.edges = []
        self.biological_edges = []
    
    def extract_biology(self, max_edges: int = None) -> None:
        """
        Extract biological edges from ConceptNet5.
        
        Filters for:
            - English language (/c/en/)
            - Biological keywords (bird, animal, organism, fly, swim, etc.)
            - Weight > threshold
        
        Args:
            max_edges: Maximum edges to process (None = all)
        """
        print(f"Extracting from {self.conceptnet_path}...")
        print(f"Weight threshold: {self.weight_threshold}")
        
        bio_keywords = {
            # Animals
            'bird', 'animal', 'mammal', 'fish', 'insect', 'reptile',
            'dog', 'cat', 'penguin', 'sparrow', 'eagle', 'dolphin',
            # Actions
            'fly', 'swim', 'walk', 'run', 'hunt', 'migrate', 'nest',
            # Properties
            'feather', 'wing', 'beak', 'tail', 'fur', 'scale',
            # General
            'organism', 'species', 'living', 'biological', 'creature',
        }
        
        edges_processed = 0
        bio_edges_found = 0
        
        with gzip.open(self.conceptnet_path, 'rt', encoding='utf-8') as f:
            for line in f:
                if max_edges and edges_processed >= max_edges:
                    break
                
                edges_processed += 1
                
                if edges_processed % 1000000 == 0:
                    print(f"  Processed {edges_processed/1000000:.1f}M edges, found {bio_edges_found} biological...")
                
                try:
                    parts = line.strip().split('\t')
                    if len(parts) < 5:
                        continue
                    
                    uri, relation, start, end, metadata_json = parts[:5]
                    
                    # Only English
                    if not ('/c/en/' in start and '/c/en/' in end):
                        continue
                    
                    # Parse metadata
                    metadata = json.loads(metadata_json)
                    weight = metadata.get('weight', 0.0)
                    
                    # Filter by weight
                    if weight < self.weight_threshold:
                        continue
                    
                    # Extract concepts
                    start_concept = self._extract_concept(start)
                    end_concept = self._extract_concept(end)
                    
                    # Check if biological
                    if any(kw in start_concept.lower() or kw in end_concept.lower() 
                           for kw in bio_keywords):
                        self.biological_edges.append({
                            'relation': self._extract_relation(relation),
                            'start': start_concept,
                            'end': end_concept,
                            'weight': weight,
                        })
                        bio_edges_found += 1
                
                except Exception as e:
                    # Skip malformed lines
                    continue
        
        print(f"  Processed {edges_processed} edges total")
        print(f"  Found {len(self.biological_edges)} biological edges")
    
    def to_theory(self) -> Theory:
        """
        Convert biological edges to defeasible theory.
        
        Conversion rules:
            - IsA → strict facts/rules
            - CapableOf → defeasible rules (behavioral defaults)
            - NotCapableOf → defeaters (exceptions)
            - HasProperty → defeasible property rules
        
        Returns:
            Theory with behavioral rules
        """
        theory = Theory()
        
        facts_added = set()
        rules_added = set()
        
        for edge in self.biological_edges:
            rel = edge['relation']
            start = self._normalize(edge['start'])
            end = self._normalize(edge['end'])
            weight = edge['weight']
            
            # IsA → taxonomic facts
            if rel == 'IsA':
                fact = f"isa({start}, {end})"
                if fact not in facts_added:
                    theory.add_fact(fact)
                    facts_added.add(fact)
            
            # CapableOf → behavioral defaults (defeasible)
            elif rel == 'CapableOf':
                # Create predicate from capability
                action = self._action_to_predicate(end)
                
                rule_key = (action, start)
                if rule_key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"{action}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_{action}_{start}",
                        metadata={"weight": weight, "source": "ConceptNet5"}
                    ))
                    rules_added.add(rule_key)
            
            # NotCapableOf → defeaters
            elif rel == 'NotCapableOf':
                action = self._action_to_predicate(end)
                
                rule_key = (f"~{action}", start)
                if rule_key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"~{action}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEATER,
                        label=f"d_{action}_{start}",
                        metadata={"weight": weight, "source": "ConceptNet5"}
                    ))
                    rules_added.add(rule_key)
            
            # HasProperty → property rules (defeasible)
            elif rel == 'HasProperty':
                prop = self._normalize(end)
                
                rule_key = (f"has_{prop}", start)
                if rule_key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"has_{prop}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_has_{prop}_{start}",
                        metadata={"weight": weight, "source": "ConceptNet5"}
                    ))
                    rules_added.add(rule_key)
        
        return theory
    
    def _extract_concept(self, uri: str) -> str:
        """Extract concept from ConceptNet URI."""
        # /c/en/bird/n → bird
        parts = uri.split('/')
        if len(parts) >= 4 and parts[1] == 'c' and parts[2] == 'en':
            return parts[3]
        return uri
    
    def _extract_relation(self, uri: str) -> str:
        """Extract relation from URI."""
        # /r/CapableOf → CapableOf
        parts = uri.split('/')
        if len(parts) >= 3 and parts[1] == 'r':
            return parts[2]
        return uri
    
    def _normalize(self, text: str) -> str:
        """Normalize concept for Prolog."""
        # Lowercase, replace spaces with underscores
        text = text.lower().replace(' ', '_').replace('-', '_')
        # Remove special characters
        text = ''.join(c for c in text if c.isalnum() or c == '_')
        return text
    
    def _action_to_predicate(self, action: str) -> str:
        """Convert action phrase to predicate."""
        # "fly" → "flies"
        # "swim" → "swims"  
        # For simplicity, just normalize
        return self._normalize(action)


def extract_biology_from_conceptnet(
    conceptnet_path: Path = None,
    weight_threshold: float = 2.0,
    max_edges: int = None
) -> Theory:
    """
    Extract biology KB from ConceptNet5.
    
    Args:
        conceptnet_path: Path to ConceptNet5 CSV
        weight_threshold: Minimum confidence
        max_edges: Max edges to process (None = all 21M)
    
    Returns:
        Theory with biological behavioral rules
    
    Example:
        >>> kb = extract_biology_from_conceptnet(
        ...     weight_threshold=3.0,
        ...     max_edges=1000000  # Process first 1M edges
        ... )
    """
    if conceptnet_path is None:
        conceptnet_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
    
    extractor = ConceptNetExtractor(conceptnet_path, weight_threshold)
    extractor.extract_biology(max_edges)
    theory = extractor.to_theory()
    
    return theory
