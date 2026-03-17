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
from blanc.ontology.nell_extractor import (
    NellExtractor,
    extract_from_nell,
)
from blanc.ontology.sumo_extractor import (
    SumoExtractor,
    extract_from_sumo,
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
from blanc.ontology.gene_ontology_extractor import (
    GeneOntologyExtractor,
    extract_from_gene_ontology,
)
from blanc.ontology.framenet_extractor import (
    FrameNetExtractor,
    extract_from_framenet,
)
from blanc.ontology.mesh_extractor import (
    MeshExtractor,
    extract_from_mesh,
)
from blanc.ontology.wikidata_extractor import (
    WikidataExtractor,
    extract_from_wikidata,
    DOMAIN_CLASSES as WIKIDATA_DOMAIN_CLASSES,
)
from blanc.ontology.yago_full_extractor import (
    YagoFullExtractor,
    extract_from_yago_full,
)
from blanc.ontology.rule_validator import (
    ValidationReport,
    validate_theory,
    deduplicate_theory,
    save_report,
)

__all__ = [
    "OpenCycExtractor",
    "extract_biology_from_opencyc",
    "extract_from_opencyc",
    "ConceptNetExtractor",
    "extract_biology_from_conceptnet",
    "extract_from_conceptnet",
    "NellExtractor",
    "extract_from_nell",
    "SumoExtractor",
    "extract_from_sumo",
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
    "GeneOntologyExtractor",
    "extract_from_gene_ontology",
    "FrameNetExtractor",
    "extract_from_framenet",
    "MeshExtractor",
    "extract_from_mesh",
    "WikidataExtractor",
    "extract_from_wikidata",
    "WIKIDATA_DOMAIN_CLASSES",
    "YagoFullExtractor",
    "extract_from_yago_full",
    "ValidationReport",
    "validate_theory",
    "deduplicate_theory",
    "save_report",
]
