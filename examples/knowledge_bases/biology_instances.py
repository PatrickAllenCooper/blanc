"""
Biology Instance Facts

Common biological organisms as instance facts.
Based on organisms that exist in YAGO/WordNet taxonomies.

These are real organisms (not synthetic) that appear in expert KBs.
Used to populate the biology KB with ground facts for instance generation.

Author: Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory


def add_biology_instances(theory: Theory) -> Theory:
    """
    Add biological organism instances to theory.
    
    Organisms selected from YAGO/WordNet that match our taxonomy.
    All are real organisms documented in expert knowledge bases.
    """
    
    # Birds (from WordNet bird.n.01 hyponyms and YAGO)
    birds = [
        'robin', 'sparrow', 'eagle', 'hawk', 'owl', 'falcon',
        'duck', 'goose', 'swan', 'pelican', 'penguin', 'ostrich',
        'parrot', 'macaw', 'crow', 'raven', 'hummingbird', 'woodpecker',
        'cardinal', 'finch', 'canary', 'pigeon', 'seagull'
    ]
    
    for bird in birds:
        theory.add_fact(f"organism({bird})")
        theory.add_fact(f"animal({bird})")
        theory.add_fact(f"bird({bird})")
    
    # Mammals (from WordNet mammal.n.01 hyponyms and YAGO)
    mammals = [
        'dog', 'cat', 'lion', 'tiger', 'bear', 'wolf', 'fox',
        'deer', 'elk', 'moose', 'elephant', 'giraffe', 'zebra',
        'dolphin', 'whale', 'seal', 'otter', 'walrus',
        'bat', 'monkey', 'gorilla', 'chimpanzee',
        'rabbit', 'squirrel', 'mouse', 'rat', 'beaver'
    ]
    
    for mammal in mammals:
        theory.add_fact(f"organism({mammal})")
        theory.add_fact(f"animal({mammal})")
        theory.add_fact(f"mammal({mammal})")
    
    # Fish (from WordNet fish.n.02 hyponyms)
    fish_list = [
        'salmon', 'trout', 'bass', 'tuna', 'shark', 'ray',
        'goldfish', 'carp', 'pike', 'perch', 'cod', 'herring'
    ]
    
    for fish in fish_list:
        theory.add_fact(f"organism({fish})")
        theory.add_fact(f"animal({fish})")
        theory.add_fact(f"fish({fish})")
    
    # Insects (from WordNet insect.n.01 hyponyms)
    insects = [
        'bee', 'ant', 'butterfly', 'moth', 'beetle', 'fly',
        'mosquito', 'dragonfly', 'grasshopper', 'cricket', 'wasp'
    ]
    
    for insect in insects:
        theory.add_fact(f"organism({insect})")
        theory.add_fact(f"animal({insect})")
        theory.add_fact(f"insect({insect})")
    
    # Reptiles (from WordNet reptile.n.01 hyponyms)
    reptiles = [
        'snake', 'lizard', 'turtle', 'crocodile', 'alligator',
        'gecko', 'iguana', 'chameleon'
    ]
    
    for reptile in reptiles:
        theory.add_fact(f"organism({reptile})")
        theory.add_fact(f"animal({reptile})")
        theory.add_fact(f"reptile({reptile})")
    
    # Amphibians (from WordNet amphibian.n.01 hyponyms)
    amphibians = [
        'frog', 'toad', 'salamander', 'newt'
    ]
    
    for amphibian in amphibians:
        theory.add_fact(f"organism({amphibian})")
        theory.add_fact(f"animal({amphibian})")
        theory.add_fact(f"amphibian({amphibian})")
    
    return theory


def get_organism_counts():
    """Get counts of organisms by type."""
    return {
        'birds': 23,
        'mammals': 27,
        'fish': 12,
        'insects': 11,
        'reptiles': 8,
        'amphibians': 4,
        'total': 85
    }
