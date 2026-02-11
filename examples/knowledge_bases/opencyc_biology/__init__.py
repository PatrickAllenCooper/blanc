"""OpenCyc Biology KB - Extracted from OpenCyc 4.0."""

import pickle
from pathlib import Path
from blanc.core.theory import Theory


def load_opencyc_biology() -> Theory:
    """
    Load OpenCyc biology KB.
    
    Returns:
        Theory with 12K+ biological concepts and 21K+ taxonomic relations
    
    Stats:
        - 12,363 biological concepts (facts)
        - 21,220 taxonomic relations (rules)
        - 33,583 total elements
        - Extracted from OpenCyc 4.0 (2012-05-10)
    """
    pkl_path = Path(__file__).parent / "opencyc_biology.pkl"
    
    if not pkl_path.exists():
        raise FileNotFoundError(
            f"OpenCyc biology KB not found at {pkl_path}. "
            "Run scripts/extract_opencyc_biology.py to generate."
        )
    
    with open(pkl_path, 'rb') as f:
        theory = pickle.load(f)
    
    return theory


__all__ = ["load_opencyc_biology"]
