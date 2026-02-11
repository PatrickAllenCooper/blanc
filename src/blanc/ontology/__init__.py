"""Ontology extraction and conversion utilities."""

from blanc.ontology.opencyc_extractor import (
    OpenCycExtractor,
    extract_biology_from_opencyc,
)

__all__ = [
    "OpenCycExtractor",
    "extract_biology_from_opencyc",
]
