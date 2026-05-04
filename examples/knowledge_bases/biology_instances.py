"""
Biology Instance Facts

Common biological organisms as instance facts.
Based on organisms that exist in YAGO/WordNet taxonomies.

These are real organisms (not synthetic) that appear in expert KBs.
Used to populate the biology KB with ground facts for instance generation.

Author: Anonymous Authors
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
    
    # Additional birds referenced in behavioral rules
    extra_birds = [
        'chicken', 'stork', 'vulture', 'cuckoo', 'cassowary',
        'kiwi', 'emu', 'nightingale',
    ]
    for bird in extra_birds:
        theory.add_fact(f"organism({bird})")
        theory.add_fact(f"animal({bird})")
        theory.add_fact(f"bird({bird})")

    # Additional mammals referenced in behavioral rules
    extra_mammals = [
        'hedgehog', 'raccoon', 'wildebeest', 'kangaroo',
        'platypus', 'echidna', 'sloth', 'mole', 'panda',
        'polar_bear', 'opossum', 'porcupine', 'armadillo',
        'orangutan', 'cheetah', 'hippopotamus', 'lemur',
    ]
    for mammal in extra_mammals:
        theory.add_fact(f"organism({mammal})")
        theory.add_fact(f"animal({mammal})")
        theory.add_fact(f"mammal({mammal})")

    # Arachnids
    arachnids = ['spider', 'scorpion']
    for a in arachnids:
        theory.add_fact(f"organism({a})")
        theory.add_fact(f"animal({a})")
        theory.add_fact(f"arachnid({a})")

    # Additional insects referenced in behavioral rules
    extra_insects = [
        'flea', 'silverfish', 'termite', 'silkworm',
        'firefly', 'aphid',
    ]
    for insect in extra_insects:
        theory.add_fact(f"organism({insect})")
        theory.add_fact(f"animal({insect})")
        theory.add_fact(f"insect({insect})")

    # Aquatic invertebrates
    aquatic_inverts = [
        'octopus', 'squid', 'starfish', 'jellyfish',
        'coral', 'cuttlefish',
    ]
    for ai in aquatic_inverts:
        theory.add_fact(f"organism({ai})")
        theory.add_fact(f"animal({ai})")

    # Additional fish
    extra_fish = ['anglerfish', 'lungfish', 'pufferfish']
    for fish in extra_fish:
        theory.add_fact(f"organism({fish})")
        theory.add_fact(f"animal({fish})")
        theory.add_fact(f"fish({fish})")

    # Plants and other producers
    plants = ['venus_flytrap', 'parasitic_plant', 'algae']
    for p in plants:
        theory.add_fact(f"organism({p})")
        theory.add_fact(f"plant({p})")

    # Microorganisms
    theory.add_fact("organism(fungus)")
    theory.add_fact("organism(bacteria)")

    # Worms
    theory.add_fact("organism(worm)")
    theory.add_fact("animal(worm)")

    # Crustaceans
    theory.add_fact("organism(crab)")
    theory.add_fact("animal(crab)")
    theory.add_fact("crustacean(crab)")

    # Snails
    theory.add_fact("organism(snail)")
    theory.add_fact("animal(snail)")

    return theory


def get_organism_counts():
    """Get counts of organisms by type."""
    return {
        'birds': 31,
        'mammals': 44,
        'fish': 15,
        'insects': 17,
        'reptiles': 8,
        'amphibians': 4,
        'arachnids': 2,
        'aquatic_invertebrates': 6,
        'plants': 3,
        'other': 5,
        'total': 135
    }
