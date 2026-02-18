"""
OpenCyc ontology extraction for biology domain.

Extracts biological concepts, taxonomic relations, and properties from
OpenCyc 4.0 (300K concepts) and converts to definite logic program.

Author: Patrick Cooper
Date: 2026-02-11
"""

import gzip
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict

try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF, RDFS, OWL
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False
    Graph = None
    Namespace = None
    RDF = RDFS = OWL = None

from blanc.core.theory import Theory, Rule, RuleType


class OpenCycExtractor:
    """
    Extract biological knowledge from OpenCyc ontology.
    
    Strategy:
        1. Load OWL file with rdflib
        2. Identify biological concepts (subclasses of BiologicalLivingObject)
        3. Extract taxonomic relations (rdfs:subClassOf)
        4. Extract properties and relations
        5. Convert to definite logic program
    
    Complexity: O(n) where n is number of triples (millions)
    """
    
    def __init__(self, opencyc_path: Path):
        """
        Initialize extractor.
        
        Args:
            opencyc_path: Path to OpenCyc OWL file (.owl or .owl.gz)
        
        Raises:
            ImportError: If rdflib not installed
            FileNotFoundError: If OpenCyc file not found
        """
        if not RDFLIB_AVAILABLE:
            raise ImportError(
                "rdflib is required for OpenCyc extraction. "
                "Install with: pip install rdflib>=7.0.0"
            )
        
        if not opencyc_path.exists():
            raise FileNotFoundError(f"OpenCyc file not found: {opencyc_path}")
        
        self.opencyc_path = opencyc_path
        self.graph = None
        self.biological_concepts = set()
        self.taxonomic_relations = []
        self.properties = []
    
    def load(self) -> None:
        """
        Load OpenCyc OWL file into RDF graph.
        
        Handles .gz compression automatically.
        """
        print(f"Loading OpenCyc from {self.opencyc_path}...")
        
        self.graph = Graph()
        
        # Handle gzipped files
        if self.opencyc_path.suffix == '.gz':
            with gzip.open(self.opencyc_path, 'rb') as f:
                self.graph.parse(f, format='xml')
        else:
            self.graph.parse(self.opencyc_path, format='xml')
        
        print(f"  Loaded {len(self.graph)} triples")
    
    def extract_biology(self) -> None:
        """
        Extract biological concepts and relations.
        
        Strategy:
            1. Find all concepts related to biology
            2. Extract their taxonomic hierarchy
            3. Extract properties
        """
        if self.graph is None:
            raise ValueError("Must call load() first")
        
        print("Extracting biological concepts...")
        
        # Biology-related root concepts to search from
        bio_roots = [
            "BiologicalLivingObject",
            "Organism_Whole",
            "Animal",
            "Plant",
            "Cell",
            "BiologicalProcess",
            "AnatomicalStructure",
        ]
        
        # Find concepts containing biological keywords
        bio_keywords = [
            'bird', 'animal', 'organism', 'cell', 'plant',
            'species', 'biological', 'anatomy', 'organ',
            'tissue', 'protein', 'enzyme', 'dna', 'gene'
        ]
        
        concept_count = 0
        
        # Iterate through all classes
        for subject in self.graph.subjects(RDF.type, OWL.Class):
            # Get label
            labels = list(self.graph.objects(subject, RDFS.label))
            
            if labels:
                label = str(labels[0]).lower()
                
                # Check if biological
                if any(keyword in label for keyword in bio_keywords):
                    concept_name = self._extract_concept_name(subject)
                    if concept_name:
                        self.biological_concepts.add(concept_name)
                        concept_count += 1
                        
                        # Extract subclass relations
                        for superclass in self.graph.objects(subject, RDFS.subClassOf):
                            super_name = self._extract_concept_name(superclass)
                            if super_name:
                                self.taxonomic_relations.append((concept_name, super_name))
        
        print(f"  Found {len(self.biological_concepts)} biological concepts")
        print(f"  Found {len(self.taxonomic_relations)} taxonomic relations")
    
    def to_definite_lp(self) -> Theory:
        """
        Convert extracted concepts to definite logic program.
        
        Returns:
            Theory object with biology KB
        
        Conversion strategy:
            - Concepts → ground facts: concept(name)
            - Taxonomic relations → rules: isa(X, Super) :- isa(X, Sub)
            - Simplify for tractability (function-free)
        """
        theory = Theory()
        
        # Add biological concepts as facts
        for concept in sorted(self.biological_concepts):
            # Normalize concept name for Prolog
            concept_normalized = self._normalize_for_prolog(concept)
            theory.add_fact(f"biological_concept({concept_normalized})")
        
        # Add taxonomic relations as rules
        added_rules = set()
        for sub, super_cls in self.taxonomic_relations:
            sub_norm = self._normalize_for_prolog(sub)
            super_norm = self._normalize_for_prolog(super_cls)
            
            rule_key = (sub_norm, super_norm)
            if rule_key not in added_rules:
                theory.add_rule(Rule(
                    head=f"isa({sub_norm}, {super_norm})",
                    body=(),
                    rule_type=RuleType.STRICT,
                    label=f"tax_{sub_norm}_{super_norm}"
                ))
                added_rules.add(rule_key)
        
        return theory
    
    def _extract_concept_name(self, uri) -> str:
        """Extract concept name from URI."""
        uri_str = str(uri)
        # Get last component after / or #
        if '/' in uri_str:
            name = uri_str.split('/')[-1]
        elif '#' in uri_str:
            name = uri_str.split('#')[-1]
        else:
            name = uri_str
        
        # Remove query parameters
        if '?' in name:
            name = name.split('?')[0]
        
        return name if name and name != uri_str else None
    
    def _normalize_for_prolog(self, name: str) -> str:
        """
        Normalize concept name for Prolog.
        
        Rules:
            - Lowercase
            - Replace spaces/hyphens with underscores
            - Remove special characters
            - Must start with letter
        """
        # Lowercase
        name = name.lower()
        
        # Replace spaces and hyphens
        name = name.replace(' ', '_').replace('-', '_')
        
        # Remove parentheses and other special chars
        name = ''.join(c if c.isalnum() or c == '_' else '' for c in name)
        
        # Ensure starts with letter
        if name and not name[0].isalpha():
            name = 'c_' + name
        
        return name


def extract_biology_from_opencyc(
    opencyc_path: Path = None,
    max_concepts: int = None
) -> Theory:
    """
    Extract biology KB from OpenCyc.
    
    Convenience function for complete extraction pipeline.
    
    Args:
        opencyc_path: Path to OpenCyc OWL file
        max_concepts: Maximum concepts to extract (None = all)
    
    Returns:
        Theory with biological knowledge
    
    Example:
        >>> from pathlib import Path
        >>> kb = extract_biology_from_opencyc(
        ...     Path(r"D:\\datasets\\opencyc-kb\\opencyc-2012-05-10-readable.owl.gz")
        ... )
        >>> print(f"Extracted {len(kb)} rules")
    """
    if opencyc_path is None:
        opencyc_path = Path(__file__).parent.parent.parent.parent / "data" / "opencyc" / "opencyc-2012-05-10-readable.owl.gz"
    
    extractor = OpenCycExtractor(opencyc_path)
    extractor.load()
    extractor.extract_biology()
    
    # Limit if specified
    if max_concepts:
        extractor.biological_concepts = set(list(extractor.biological_concepts)[:max_concepts])
        extractor.taxonomic_relations = extractor.taxonomic_relations[:max_concepts * 2]
    
    theory = extractor.to_definite_lp()
    
    return theory
