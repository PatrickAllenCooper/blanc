"""
Domain profiles for parameterized ontology extraction.

Each DomainProfile encapsulates the keywords, relation mappings,
behavioral predicates, and known exceptions for a specific knowledge
domain, replacing hardcoded lists in the extractors.

Author: Patrick Cooper
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple


@dataclass(frozen=True)
class RelationMapping:
    """Maps a ConceptNet relation to a defeasible logic rule pattern.

    Attributes:
        relation: ConceptNet relation name (e.g. "CapableOf")
        head_template: Template for the rule head ("{prop}" and "{concept}"
            are interpolated at extraction time)
        rule_type: One of "strict", "defeasible", "defeater"
    """

    relation: str
    head_template: str
    rule_type: str


@dataclass(frozen=True)
class DomainProfile:
    """Configuration for domain-specific ontology extraction.

    Attributes:
        name: Short identifier (e.g. "biology", "legal")
        description: Human-readable description
        keywords: Set of lowercase keywords used to filter concepts
        opencyc_roots: OWL class names to seed OpenCyc traversal
        relation_mappings: How each ConceptNet relation converts to rules
        behavioral_predicates: Predicates that represent domain defaults
        known_exceptions: (predicate, concept) pairs that are known defeaters
    """

    name: str
    description: str
    keywords: FrozenSet[str]
    opencyc_roots: Tuple[str, ...] = ()
    relation_mappings: Tuple[RelationMapping, ...] = ()
    behavioral_predicates: Tuple[str, ...] = ()
    known_exceptions: Tuple[Tuple[str, str], ...] = ()

    def matches(self, text: str) -> bool:
        """Return True if *text* contains any domain keyword."""
        lower = text.lower()
        return any(kw in lower for kw in self.keywords)


# ── Shared relation mappings ─────────────────────────────────────────

_COMMON_RELATIONS: Tuple[RelationMapping, ...] = (
    RelationMapping("IsA", "{concept}(X)", "strict"),
    RelationMapping("CapableOf", "{prop}(X)", "defeasible"),
    RelationMapping("NotCapableOf", "~{prop}(X)", "defeater"),
    RelationMapping("HasProperty", "has_{prop}(X)", "defeasible"),
    RelationMapping("Causes", "causes_{prop}(X)", "defeasible"),
    RelationMapping("UsedFor", "used_for_{prop}(X)", "defeasible"),
)


# ── Biology ──────────────────────────────────────────────────────────

BIOLOGY = DomainProfile(
    name="biology",
    description="Biological organisms, taxonomy, behavior, and ecology",
    keywords=frozenset({
        "bird", "animal", "mammal", "fish", "insect", "reptile",
        "amphibian", "organism", "species", "plant", "tree", "flower",
        "cell", "bacteria", "virus", "fungus", "algae", "parasite",
        "predator", "prey", "herbivore", "carnivore", "omnivore",
        "vertebrate", "invertebrate", "arthropod", "mollusk",
        "crustacean", "arachnid", "primate", "rodent", "feline",
        "canine", "equine", "bovine", "avian", "aquatic",
        "fly", "swim", "walk", "run", "hunt", "migrate", "nest",
        "feather", "wing", "beak", "tail", "fur", "scale", "shell",
        "egg", "larva", "pupa", "metamorphosis",
        "photosynthesis", "respiration", "reproduction",
        "biological", "ecology", "habitat", "ecosystem",
        "dolphin", "whale", "shark", "penguin", "sparrow", "eagle",
        "hawk", "owl", "parrot", "ostrich", "bat", "snake", "lizard",
        "frog", "toad", "salamander", "turtle", "crocodile",
        "spider", "ant", "bee", "butterfly", "moth", "beetle",
        "worm", "coral", "sponge", "jellyfish", "octopus", "squid",
    }),
    opencyc_roots=(
        "BiologicalLivingObject",
        "Organism_Whole",
        "Animal",
        "Plant",
        "Cell",
        "BiologicalProcess",
        "AnatomicalStructure",
    ),
    relation_mappings=_COMMON_RELATIONS,
    behavioral_predicates=(
        "flies", "swims", "walks", "runs", "hunts", "migrates",
        "sings", "lays_eggs", "has_feathers", "has_fur", "has_scales",
        "breathes_air", "breathes_water", "is_warm_blooded",
        "is_cold_blooded", "is_nocturnal", "is_diurnal",
        "hibernates", "photosynthesizes",
    ),
    known_exceptions=(
        ("flies", "penguin"),
        ("flies", "ostrich"),
        ("flies", "kiwi"),
        ("flies", "emu"),
        ("walks", "whale"),
        ("walks", "dolphin"),
        ("walks", "snake"),
        ("has_fur", "dolphin"),
        ("has_fur", "whale"),
        ("is_cold_blooded", "tuna"),
        ("lays_eggs", "platypus"),
        ("has_feathers", "bat"),
    ),
)


# ── Legal ────────────────────────────────────────────────────────────

LEGAL = DomainProfile(
    name="legal",
    description="Legal concepts, norms, rights, obligations, and jurisdictions",
    keywords=frozenset({
        "law", "legal", "right", "obligation", "duty", "liability",
        "contract", "tort", "crime", "statute", "regulation",
        "court", "judge", "jurisdiction", "precedent", "appeal",
        "plaintiff", "defendant", "witness", "evidence", "verdict",
        "sentence", "penalty", "fine", "imprisonment", "probation",
        "parole", "bail", "arrest", "prosecution", "defense",
        "constitution", "amendment", "bill", "act", "ordinance",
        "property", "ownership", "lease", "mortgage", "trust",
        "patent", "copyright", "trademark", "license",
        "citizen", "resident", "alien", "minor", "adult",
        "capacity", "consent", "competence", "immunity",
        "negligence", "fraud", "breach", "damages",
        "legislative", "executive", "judicial",
        "civil", "criminal", "administrative",
        "plaintiff", "respondent", "petitioner",
        "norm", "rule", "power", "permission", "prohibition",
        "hohfeld", "claim", "privilege", "liberty",
    }),
    opencyc_roots=(
        "LegalAction",
        "LegalAgent",
        "Law",
        "LegalConcept",
        "GovernmentOrganization",
        "JudicialProcess",
    ),
    relation_mappings=_COMMON_RELATIONS,
    behavioral_predicates=(
        "can_contract", "can_vote", "can_testify", "can_sue",
        "has_capacity", "has_liability", "has_immunity",
        "is_liable", "is_competent", "is_culpable",
        "owes_duty", "holds_right", "bears_burden",
        "presumed_innocent", "bound_by_precedent",
    ),
    known_exceptions=(
        ("can_contract", "minor"),
        ("can_vote", "felon"),
        ("can_vote", "non_citizen"),
        ("can_testify", "incompetent_witness"),
        ("is_liable", "diplomat"),
        ("is_liable", "sovereign"),
        ("bound_by_precedent", "supreme_court"),
        ("has_capacity", "minor"),
        ("has_capacity", "mentally_incapacitated"),
        ("bears_burden", "defendant_in_strict_liability"),
        ("presumed_innocent", "civil_defendant"),
    ),
)


# ── Materials Science ────────────────────────────────────────────────

MATERIALS = DomainProfile(
    name="materials",
    description="Materials science: metals, ceramics, polymers, composites",
    keywords=frozenset({
        "metal", "alloy", "steel", "iron", "aluminum", "copper",
        "titanium", "nickel", "zinc", "tin", "gold", "silver",
        "ceramic", "glass", "porcelain", "oxide", "carbide", "nitride",
        "polymer", "plastic", "rubber", "resin", "nylon", "polyester",
        "composite", "fiber", "matrix", "laminate",
        "semiconductor", "silicon", "germanium", "gallium",
        "crystal", "amorphous", "polycrystalline",
        "conductor", "insulator", "superconductor",
        "brittle", "ductile", "malleable", "elastic", "plastic",
        "hardness", "tensile", "strength", "toughness", "fatigue",
        "corrosion", "oxidation", "wear", "creep",
        "annealing", "quenching", "tempering", "sintering",
        "casting", "forging", "welding", "machining",
        "material", "substance", "compound", "element",
        "biomaterial", "nanomaterial", "metamaterial",
        "thermal", "electrical", "magnetic", "optical",
    }),
    opencyc_roots=(
        "Material",
        "Substance",
        "ChemicalCompound",
        "Metal",
        "Alloy",
    ),
    relation_mappings=_COMMON_RELATIONS,
    behavioral_predicates=(
        "conducts_electricity", "conducts_heat",
        "is_brittle", "is_ductile", "is_malleable",
        "is_magnetic", "is_transparent", "is_opaque",
        "resists_corrosion", "is_biocompatible",
        "is_crystalline", "is_amorphous",
    ),
    known_exceptions=(
        ("conducts_electricity", "ceramic_superconductor"),
        ("is_brittle", "metallic_glass"),
        ("is_brittle", "toughened_ceramic"),
        ("is_ductile", "cast_iron"),
        ("is_opaque", "optical_fiber"),
        ("is_opaque", "transparent_ceramic"),
        ("resists_corrosion", "iron"),
        ("is_magnetic", "austenitic_stainless_steel"),
        ("conducts_heat", "aerogel"),
        ("is_crystalline", "metallic_glass"),
    ),
)


# ── Chemistry ────────────────────────────────────────────────────────

CHEMISTRY = DomainProfile(
    name="chemistry",
    description="Chemical elements, reactions, compounds, and properties",
    keywords=frozenset({
        "element", "compound", "molecule", "atom", "ion",
        "acid", "base", "salt", "solvent", "solute", "solution",
        "reaction", "catalyst", "enzyme", "oxidation", "reduction",
        "bond", "covalent", "ionic", "metallic", "hydrogen",
        "organic", "inorganic", "aromatic", "aliphatic",
        "carbon", "oxygen", "nitrogen", "hydrogen",
        "chemical", "reagent", "product", "reactant",
        "gas", "liquid", "solid", "plasma",
        "boiling", "melting", "freezing", "evaporation",
        "concentration", "ph", "equilibrium", "kinetics",
        "thermodynamic", "enthalpy", "entropy",
        "polymer", "monomer", "isomer", "isotope",
    }),
    opencyc_roots=(
        "ChemicalSubstance",
        "ChemicalReaction",
        "ChemicalElement",
        "ChemicalCompound",
    ),
    relation_mappings=_COMMON_RELATIONS,
    behavioral_predicates=(
        "dissolves_in_water", "reacts_with_acid",
        "is_flammable", "is_volatile", "is_stable",
        "is_soluble", "is_gaseous_at_room_temp",
        "conducts_in_solution", "is_polar",
    ),
    known_exceptions=(
        ("dissolves_in_water", "oil"),
        ("dissolves_in_water", "sand"),
        ("is_flammable", "water"),
        ("is_flammable", "carbon_dioxide"),
        ("is_gaseous_at_room_temp", "mercury"),
        ("is_gaseous_at_room_temp", "bromine"),
        ("is_stable", "alkali_metal"),
        ("is_polar", "carbon_tetrachloride"),
    ),
)


# ── Everyday / Commonsense ───────────────────────────────────────────

EVERYDAY = DomainProfile(
    name="everyday",
    description="Commonsense knowledge about everyday objects and activities",
    keywords=frozenset({
        "person", "human", "child", "adult", "baby",
        "food", "drink", "water", "bread", "fruit", "vegetable",
        "house", "building", "room", "door", "window", "wall",
        "car", "vehicle", "bicycle", "bus", "train", "airplane",
        "tool", "hammer", "knife", "scissors", "pen", "pencil",
        "book", "paper", "computer", "phone", "television",
        "chair", "table", "bed", "desk", "lamp", "clock",
        "clothes", "shoe", "hat", "shirt", "pants",
        "weather", "rain", "snow", "sun", "wind", "cloud",
        "day", "night", "morning", "evening",
        "hot", "cold", "warm", "cool",
        "big", "small", "heavy", "light",
        "fast", "slow", "loud", "quiet",
        "wood", "stone", "brick", "concrete",
        "float", "sink", "burn", "melt", "freeze",
    }),
    opencyc_roots=(
        "PhysicalDevice",
        "FoodOrDrink",
        "Building",
        "Vehicle",
        "Artifact",
    ),
    relation_mappings=_COMMON_RELATIONS,
    behavioral_predicates=(
        "floats", "sinks", "burns", "melts",
        "is_edible", "is_portable", "is_fragile",
        "requires_electricity", "is_waterproof",
    ),
    known_exceptions=(
        ("floats", "waterlogged_wood"),
        ("floats", "iron_wood"),
        ("sinks", "pumice"),
        ("sinks", "ice"),
        ("burns", "asbestos"),
        ("is_edible", "poisonous_mushroom"),
        ("is_fragile", "tempered_glass"),
        ("requires_electricity", "mechanical_clock"),
    ),
)


# ── Registry ─────────────────────────────────────────────────────────

ALL_PROFILES: Dict[str, DomainProfile] = {
    p.name: p for p in (BIOLOGY, LEGAL, MATERIALS, CHEMISTRY, EVERYDAY)
}


def get_profile(name: str) -> DomainProfile:
    """Look up a domain profile by name.

    Raises:
        KeyError: If *name* is not a registered profile.
    """
    if name not in ALL_PROFILES:
        raise KeyError(
            f"Unknown domain profile {name!r}. "
            f"Available: {sorted(ALL_PROFILES)}"
        )
    return ALL_PROFILES[name]


def combined_keywords(*names: str) -> FrozenSet[str]:
    """Return the union of keywords across the named profiles."""
    result: Set[str] = set()
    for n in names:
        result |= get_profile(n).keywords
    return frozenset(result)
