"""Ontology extraction and conversion utilities."""

from blanc.ontology.opencyc_extractor import (
    OpenCycExtractor,
    extract_biology_from_opencyc,
    extract_from_opencyc,
)
from blanc.ontology.conceptnet_extractor import (
    ConceptNetExtractor,
    extract_biology_from_conceptnet,
    extract_from_conceptnet,
)
from blanc.ontology.cross_ontology import (
    combine_taxonomy_properties,
    build_cross_ontology_theory,
    CombinationStats,
)
from blanc.ontology.domain_profiles import (
    DomainProfile,
    RelationMapping,
    get_profile,
    combined_keywords,
    ALL_PROFILES,
    BIOLOGY,
    LEGAL,
    MATERIALS,
    CHEMISTRY,
    EVERYDAY,
)

__all__ = [
    "OpenCycExtractor",
    "extract_biology_from_opencyc",
    "extract_from_opencyc",
    "ConceptNetExtractor",
    "extract_biology_from_conceptnet",
    "extract_from_conceptnet",
    "combine_taxonomy_properties",
    "build_cross_ontology_theory",
    "CombinationStats",
    "DomainProfile",
    "RelationMapping",
    "get_profile",
    "combined_keywords",
    "ALL_PROFILES",
    "BIOLOGY",
    "LEGAL",
    "MATERIALS",
    "CHEMISTRY",
    "EVERYDAY",
]
