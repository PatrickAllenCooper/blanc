"""
Download WordNet lexical database.

WordNet is an expert-curated lexical database created by Princeton linguists.
Provides taxonomic relationships (hypernyms, hyponyms) useful for biology.

Source: Princeton University
Citation: Miller, G. A. (1995). WordNet: A lexical database for English
License: Free for research and commercial use

Author: Patrick Cooper
Date: 2026-02-12
"""

import nltk
from pathlib import Path
import sys

def download_wordnet():
    """Download WordNet using NLTK."""
    
    print("=" * 70)
    print("Downloading WordNet Lexical Database")
    print("=" * 70)
    
    print("\nSource: Princeton University")
    print("Version: 3.0 (via NLTK)")
    print("License: Free for research and commercial use")
    
    # Create data directory for organization
    data_dir = Path("data/wordnet")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {data_dir}")
    print("\nDownloading via NLTK...")
    
    try:
        # Download WordNet corpus
        nltk.download('wordnet', quiet=False)
        nltk.download('omw-1.4', quiet=False)  # Open Multilingual WordNet
        
        print("\n[OK] WordNet downloaded successfully")
        
        # Test access
        from nltk.corpus import wordnet as wn
        
        # Get some stats
        synsets = list(wn.all_synsets())
        nouns = list(wn.all_synsets('n'))
        verbs = list(wn.all_synsets('v'))
        
        print(f"\nWordNet Statistics:")
        print(f"  Total synsets: {len(synsets):,}")
        print(f"  Noun synsets: {len(nouns):,}")
        print(f"  Verb synsets: {len(verbs):,}")
        
        # Test biology-related synsets
        print(f"\nBiology examples:")
        bird = wn.synset('bird.n.01')
        print(f"  bird.n.01: {bird.definition()}")
        print(f"  Hyponyms: {len(bird.hyponyms())} types of birds")
        
        # Create reference file
        ref_file = data_dir / "wordnet_info.txt"
        with open(ref_file, 'w') as f:
            f.write("WordNet 3.0\n")
            f.write("=" * 50 + "\n\n")
            f.write("Source: Princeton University\n")
            f.write("Access: NLTK corpus\n")
            f.write(f"Total synsets: {len(synsets):,}\n")
            f.write(f"Noun synsets: {len(nouns):,}\n")
            f.write(f"Verb synsets: {len(verbs):,}\n")
            f.write("\nUsage:\n")
            f.write("  from nltk.corpus import wordnet as wn\n")
            f.write("  bird = wn.synset('bird.n.01')\n")
        
        print(f"\nReference saved to: {ref_file}")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to download WordNet: {e}")
        return 1
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(download_wordnet())
