"""
Natural Language Mapping for Semi-Formal Encoding (M2).

Maps predicate symbols to natural language phrases while maintaining injectivity.
Definition 28 from paper.tex.

Author: Anonymous Authors
Date: 2026-02-12
"""

from typing import Dict, Set


# Biology KB NL Mapping (from YAGO + WordNet expert predicates)
NL_MAPPING_BIOLOGY = {
    # Taxonomic predicates
    'organism': 'is an organism',
    'animal': 'is an animal',
    'bird': 'is a bird',
    'mammal': 'is a mammal',
    'fish': 'is a fish',
    'insect': 'is an insect',
    'reptile': 'is a reptile',
    'amphibian': 'is an amphibian',
    'vertebrate': 'is a vertebrate',
    
    # Behavioral predicates (from WordNet)
    'flies': 'can fly',
    'swims': 'can swim',
    'walks': 'can walk',
    'runs': 'can run',
    'hunts': 'hunts prey',
    'eats': 'eats food',
    'migrates': 'migrates seasonally',
    'sings': 'produces vocalizations',
    
    # Additional biological terms
    'carnivore': 'is carnivorous',
    'herbivore': 'is herbivorous',
    'predator': 'is a predator',
    'prey': 'is prey',
}

# Legal KB NL Mapping (from LKIF Core expert ontology)
NL_MAPPING_LEGAL = {
    # Legal documents
    'legal_document': 'is a legal document',
    'statute': 'is a statute',
    'regulation': 'is a regulation',
    'contract': 'is a contract',
    'treaty': 'is a treaty',
    
    # Legal actions
    'legal_action': 'is a legal action',
    'filing': 'involves filing',
    'motion': 'is a motion',
    'appeal': 'is an appeal',
    'judgment': 'is a judgment',
    'ruling': 'is a ruling',
    
    # Legal roles
    'legal_role': 'has legal role',
    'plaintiff': 'is plaintiff',
    'defendant': 'is defendant',
    'judge': 'is judge',
    'prosecutor': 'is prosecutor',
    'attorney': 'is attorney',
    
    # Legal norms
    'obligation': 'has obligation',
    'permission': 'has permission',
    'prohibition': 'is prohibited',
}

# Materials KB NL Mapping (from MatOnto expert ontology)
NL_MAPPING_MATERIALS = {
    # Material types
    'material': 'is a material',
    'metal': 'is a metal',
    'alloy': 'is an alloy',
    'crystal': 'is a crystal',
    'polymer': 'is a polymer',
    'composite': 'is a composite',
    
    # Chemical classes
    'chemical': 'is a chemical',
    'acid': 'is an acid',
    'solution': 'is a solution',
    
    # Material properties (defeasible)
    'conductive': 'is electrically conductive',
    'brittle': 'is brittle',
    'ductile': 'is ductile',
    'strong': 'has high strength',
    'flexible': 'is flexible',
    'hard': 'is hard',
    'corrosion_resistant': 'is corrosion resistant',
}


class NLMapping:
    """Natural language mapping with injectivity verification."""
    
    def __init__(self, mapping: Dict[str, str]):
        """
        Initialize with predicate → NL mapping.
        
        Args:
            mapping: Dictionary mapping predicates to NL phrases
        
        Raises:
            ValueError: If mapping is not injective
        """
        self.mapping = mapping
        self._verify_injectivity()
    
    def _verify_injectivity(self):
        """Verify mapping is injective (one-to-one)."""
        nl_phrases = list(self.mapping.values())
        if len(nl_phrases) != len(set(nl_phrases)):
            # Find duplicates
            from collections import Counter
            counts = Counter(nl_phrases)
            duplicates = [phrase for phrase, count in counts.items() if count > 1]
            raise ValueError(f"NL mapping not injective. Duplicate phrases: {duplicates}")
    
    def to_nl(self, predicate: str) -> str:
        """
        Map predicate to natural language.
        
        Args:
            predicate: Predicate symbol
        
        Returns:
            Natural language phrase
        """
        return self.mapping.get(predicate, predicate)
    
    def from_nl(self, nl_phrase: str) -> str:
        """
        Reverse map from natural language to predicate.
        
        Args:
            nl_phrase: Natural language phrase
        
        Returns:
            Predicate symbol or None if not found
        """
        # Invert mapping
        inverse = {v: k for k, v in self.mapping.items()}
        return inverse.get(nl_phrase)
    
    def has_mapping(self, predicate: str) -> bool:
        """Check if predicate has NL mapping."""
        return predicate in self.mapping
    
    def add_mapping(self, predicate: str, nl_phrase: str):
        """
        Add new mapping.
        
        Args:
            predicate: Predicate symbol
            nl_phrase: Natural language phrase
        
        Raises:
            ValueError: If would violate injectivity
        """
        if nl_phrase in self.mapping.values():
            raise ValueError(f"NL phrase '{nl_phrase}' already mapped")
        self.mapping[predicate] = nl_phrase


# Create mapping instances for each KB
biology_nl = NLMapping(NL_MAPPING_BIOLOGY)
legal_nl = NLMapping(NL_MAPPING_LEGAL)
materials_nl = NLMapping(NL_MAPPING_MATERIALS)


def get_nl_mapping(domain: str) -> NLMapping:
    """
    Get NL mapping for domain.
    
    Args:
        domain: 'biology', 'legal', or 'materials'
    
    Returns:
        NLMapping instance for domain
    """
    if domain == 'biology':
        return biology_nl
    elif domain == 'legal':
        return legal_nl
    elif domain == 'materials':
        return materials_nl
    else:
        raise ValueError(f"Unknown domain: {domain}")
