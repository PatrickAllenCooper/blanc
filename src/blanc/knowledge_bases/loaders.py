"""
Knowledge base loaders for different formats and sources.

Provides utilities to load knowledge bases from files, URLs, and repositories.
"""

import subprocess
from pathlib import Path
from typing import Optional, Union

from blanc.core.knowledge_base import KnowledgeBase
from blanc.knowledge_bases.registry import KnowledgeBaseRegistry


def load_knowledge_base(
    name_or_path: Union[str, Path],
    backend: str = "prolog",
    **backend_kwargs
) -> KnowledgeBase:
    """
    Load a knowledge base by name or path.
    
    If a registered name is provided, uses registry metadata.
    If a path is provided, loads directly.
    
    Args:
        name_or_path: Knowledge base name (from registry) or file path
        backend: Backend to use ('prolog', 'asp', etc.)
        **backend_kwargs: Additional backend configuration
        
    Returns:
        Loaded knowledge base
        
    Raises:
        FileNotFoundError: If knowledge base not found
        ValueError: If knowledge base not registered
    """
    # Try registry first
    if isinstance(name_or_path, str) and not Path(name_or_path).exists():
        kb_meta = KnowledgeBaseRegistry.get(name_or_path)
        if kb_meta:
            # Load from registry
            kb = KnowledgeBase(backend=backend, **backend_kwargs)
            kb.load(kb_meta.path)
            return kb
        else:
            raise ValueError(
                f"Knowledge base '{name_or_path}' not found in registry. "
                f"Available: {[kb.name for kb in KnowledgeBaseRegistry.list_all()]}"
            )
    
    # Load from path
    path = Path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {path}")
        
    kb = KnowledgeBase(backend=backend, **backend_kwargs)
    kb.load(path)
    return kb


def download_from_github(
    repo_url: str,
    destination: Path,
    branch: str = "main"
) -> Path:
    """
    Download a knowledge base from GitHub repository.
    
    Args:
        repo_url: GitHub repository URL
        destination: Local destination directory
        branch: Branch to clone (default: main)
        
    Returns:
        Path to downloaded repository
        
    Raises:
        RuntimeError: If git clone fails
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    
    # Extract repo name from URL
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    target_dir = destination / repo_name
    
    if target_dir.exists():
        print(f"Repository already exists at {target_dir}")
        return target_dir
    
    # Clone repository
    try:
        subprocess.run(
            ["git", "clone", "-b", branch, repo_url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Successfully downloaded to {target_dir}")
        return target_dir
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone repository: {e.stderr}") from e


def download_taxkb(destination: Path = Path("D:/datasets/taxkb")) -> Path:
    """
    Download TaxKB knowledge base from GitHub.
    
    Args:
        destination: Where to save (default: D:/datasets/taxkb)
        
    Returns:
        Path to downloaded knowledge base
    """
    return download_from_github(
        "https://github.com/mcalejo/TaxKB",
        destination.parent,
        branch="main"
    )


def download_nephrodoc(destination: Path = Path("D:/datasets/nephrodoc")) -> Path:
    """
    Download NephroDoctor knowledge base from GitHub.
    
    Args:
        destination: Where to save (default: D:/datasets/nephrodoc)
        
    Returns:
        Path to downloaded knowledge base
    """
    return download_from_github(
        "https://github.com/nicoladileo/NephroDoctor",
        destination.parent,
        branch="master"
    )


class CycLConverter:
    """
    Converter for CycL (Cyc Language) to Prolog.
    
    Note: This is a simplified converter. Full CycL conversion
    requires handling complex modal operators, contexts, etc.
    """
    
    @staticmethod
    def convert_to_prolog(cycl_code: str) -> str:
        """
        Convert CycL code to Prolog (basic implementation).
        
        Args:
            cycl_code: CycL source code
            
        Returns:
            Prolog code
        """
        # TODO: Implement CycL to Prolog conversion
        # This is a placeholder for Phase 3
        raise NotImplementedError(
            "CycL conversion not yet implemented. "
            "This requires handling Cyc's modal operators and contexts."
        )
