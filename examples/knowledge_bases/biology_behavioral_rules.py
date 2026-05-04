"""
Biology Behavioral Rules -- Defeasible Defaults and Defeaters

Behavioral rules derived from biological knowledge in expert sources.
These represent defeasible defaults (typical behaviors with known
exceptions) and defeater rules that encode the exceptions.

Based on WordNet behavioral predicates, ConceptNet biology edges, and
domain knowledge from the DeFAb paper (paper.tex).

Author: Anonymous Authors
"""

from blanc.core.theory import Theory, Rule, RuleType


def _r(theory: Theory, rid: int, head: str, body: tuple,
       rtype: RuleType = RuleType.DEFEASIBLE) -> int:
    """Add a rule and return the next rule id."""
    theory.add_rule(Rule(
        head=head, body=body, rule_type=rtype,
        label=f"bio_r{rid}",
    ))
    return rid + 1


def add_behavioral_rules(theory: Theory) -> Theory:
    """Add defeasible behavioral rules and defeaters to a biology KB."""

    rid = 1000

    # ── Locomotion defaults ──────────────────────────────────────

    rid = _r(theory, rid, "flies(X)", ("bird(X)",))
    rid = _r(theory, rid, "flies(X)", ("insect(X)",))
    rid = _r(theory, rid, "flies(X)", ("bat(X)",))
    rid = _r(theory, rid, "swims(X)", ("fish(X)",))
    rid = _r(theory, rid, "swims(X)", ("amphibian(X)",))
    rid = _r(theory, rid, "swims(X)", ("dolphin(X)",))
    rid = _r(theory, rid, "swims(X)", ("whale(X)",))
    rid = _r(theory, rid, "swims(X)", ("turtle(X)",))
    rid = _r(theory, rid, "swims(X)", ("penguin(X)",))
    rid = _r(theory, rid, "walks(X)", ("mammal(X)",))
    rid = _r(theory, rid, "walks(X)", ("reptile(X)",))
    rid = _r(theory, rid, "walks(X)", ("bird(X)",))
    rid = _r(theory, rid, "runs(X)", ("mammal(X)",))
    rid = _r(theory, rid, "runs(X)", ("bird(X)",))
    rid = _r(theory, rid, "crawls(X)", ("insect(X)",))
    rid = _r(theory, rid, "crawls(X)", ("arachnid(X)",))
    rid = _r(theory, rid, "burrows(X)", ("rodent(X)",))
    rid = _r(theory, rid, "burrows(X)", ("worm(X)",))
    rid = _r(theory, rid, "climbs(X)", ("primate(X)",))
    rid = _r(theory, rid, "climbs(X)", ("squirrel(X)",))
    rid = _r(theory, rid, "glides(X)", ("flying_squirrel(X)",))
    rid = _r(theory, rid, "jumps(X)", ("frog(X)",))
    rid = _r(theory, rid, "jumps(X)", ("kangaroo(X)",))
    rid = _r(theory, rid, "slithers(X)", ("snake(X)",))

    # ── Locomotion defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~flies(X)", ("penguin(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("ostrich(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("kiwi(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("emu(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("cassowary(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("dodo(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("flea(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~flies(X)", ("ant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~walks(X)", ("whale(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~walks(X)", ("dolphin(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~walks(X)", ("snake(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~walks(X)", ("seal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~runs(X)", ("sloth(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~runs(X)", ("tortoise(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~swims(X)", ("land_tortoise(X)",), RuleType.DEFEATER)

    # ── Morphology defaults ──────────────────────────────────────

    rid = _r(theory, rid, "has_feathers(X)", ("bird(X)",))
    rid = _r(theory, rid, "has_fur(X)", ("mammal(X)",))
    rid = _r(theory, rid, "has_scales(X)", ("fish(X)",))
    rid = _r(theory, rid, "has_scales(X)", ("reptile(X)",))
    rid = _r(theory, rid, "has_wings(X)", ("bird(X)",))
    rid = _r(theory, rid, "has_wings(X)", ("insect(X)",))
    rid = _r(theory, rid, "has_wings(X)", ("bat(X)",))
    rid = _r(theory, rid, "has_beak(X)", ("bird(X)",))
    rid = _r(theory, rid, "has_tail(X)", ("mammal(X)",))
    rid = _r(theory, rid, "has_tail(X)", ("reptile(X)",))
    rid = _r(theory, rid, "has_tail(X)", ("fish(X)",))
    rid = _r(theory, rid, "has_exoskeleton(X)", ("insect(X)",))
    rid = _r(theory, rid, "has_exoskeleton(X)", ("crustacean(X)",))
    rid = _r(theory, rid, "has_exoskeleton(X)", ("arachnid(X)",))
    rid = _r(theory, rid, "has_backbone(X)", ("vertebrate(X)",))
    rid = _r(theory, rid, "has_shell(X)", ("turtle(X)",))
    rid = _r(theory, rid, "has_shell(X)", ("snail(X)",))
    rid = _r(theory, rid, "has_antlers(X)", ("deer(X)",))
    rid = _r(theory, rid, "has_horns(X)", ("bovine(X)",))
    rid = _r(theory, rid, "has_tusks(X)", ("elephant(X)",))
    rid = _r(theory, rid, "has_tusks(X)", ("walrus(X)",))

    # ── Morphology defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~has_fur(X)", ("dolphin(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_fur(X)", ("whale(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_fur(X)", ("naked_mole_rat(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_tail(X)", ("ape(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_tail(X)", ("frog(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_wings(X)", ("flea(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_wings(X)", ("silverfish(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_backbone(X)", ("hagfish(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_antlers(X)", ("female_deer(X)",), RuleType.DEFEATER)

    # ── Thermoregulation defaults ────────────────────────────────

    rid = _r(theory, rid, "is_warm_blooded(X)", ("mammal(X)",))
    rid = _r(theory, rid, "is_warm_blooded(X)", ("bird(X)",))
    rid = _r(theory, rid, "is_cold_blooded(X)", ("reptile(X)",))
    rid = _r(theory, rid, "is_cold_blooded(X)", ("amphibian(X)",))
    rid = _r(theory, rid, "is_cold_blooded(X)", ("fish(X)",))
    rid = _r(theory, rid, "is_cold_blooded(X)", ("insect(X)",))

    # ── Thermoregulation defeaters ───────────────────────────────

    rid = _r(theory, rid, "~is_cold_blooded(X)", ("tuna(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_cold_blooded(X)", ("great_white_shark(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_cold_blooded(X)", ("leatherback_turtle(X)",), RuleType.DEFEATER)

    # ── Reproduction defaults ────────────────────────────────────

    rid = _r(theory, rid, "lays_eggs(X)", ("bird(X)",))
    rid = _r(theory, rid, "lays_eggs(X)", ("reptile(X)",))
    rid = _r(theory, rid, "lays_eggs(X)", ("amphibian(X)",))
    rid = _r(theory, rid, "lays_eggs(X)", ("fish(X)",))
    rid = _r(theory, rid, "lays_eggs(X)", ("insect(X)",))
    rid = _r(theory, rid, "gives_live_birth(X)", ("mammal(X)",))
    rid = _r(theory, rid, "nurses_young(X)", ("mammal(X)",))

    # ── Reproduction defeaters ───────────────────────────────────

    rid = _r(theory, rid, "~gives_live_birth(X)", ("platypus(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~gives_live_birth(X)", ("echidna(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lays_eggs(X)", ("viviparous_lizard(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lays_eggs(X)", ("guppy(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lays_eggs(X)", ("aphid(X)",), RuleType.DEFEATER)

    # ── Diet defaults ────────────────────────────────────────────

    rid = _r(theory, rid, "eats_plants(X)", ("herbivore(X)",))
    rid = _r(theory, rid, "eats_meat(X)", ("carnivore(X)",))
    rid = _r(theory, rid, "eats_plants(X)", ("omnivore(X)",))
    rid = _r(theory, rid, "eats_meat(X)", ("omnivore(X)",))
    rid = _r(theory, rid, "eats_insects(X)", ("insectivore(X)",))
    rid = _r(theory, rid, "eats_fish(X)", ("piscivore(X)",))
    rid = _r(theory, rid, "filter_feeds(X)", ("whale(X)",))
    rid = _r(theory, rid, "photosynthesizes(X)", ("plant(X)",))
    rid = _r(theory, rid, "photosynthesizes(X)", ("algae(X)",))

    # ── Diet defeaters ───────────────────────────────────────────

    rid = _r(theory, rid, "~eats_plants(X)", ("venus_flytrap(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~photosynthesizes(X)", ("parasitic_plant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~filter_feeds(X)", ("sperm_whale(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~eats_meat(X)", ("panda(X)",), RuleType.DEFEATER)

    # ── Habitat defaults ─────────────────────────────────────────

    rid = _r(theory, rid, "lives_in_water(X)", ("fish(X)",))
    rid = _r(theory, rid, "lives_in_water(X)", ("coral(X)",))
    rid = _r(theory, rid, "lives_in_water(X)", ("jellyfish(X)",))
    rid = _r(theory, rid, "lives_on_land(X)", ("mammal(X)",))
    rid = _r(theory, rid, "lives_on_land(X)", ("reptile(X)",))
    rid = _r(theory, rid, "lives_on_land(X)", ("insect(X)",))
    rid = _r(theory, rid, "lives_underground(X)", ("worm(X)",))
    rid = _r(theory, rid, "lives_underground(X)", ("mole(X)",))
    rid = _r(theory, rid, "lives_in_trees(X)", ("primate(X)",))
    rid = _r(theory, rid, "lives_in_colonies(X)", ("ant(X)",))
    rid = _r(theory, rid, "lives_in_colonies(X)", ("bee(X)",))
    rid = _r(theory, rid, "lives_in_colonies(X)", ("termite(X)",))

    # ── Habitat defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~lives_on_land(X)", ("whale(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lives_on_land(X)", ("dolphin(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lives_on_land(X)", ("seal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lives_in_water(X)", ("lungfish(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lives_in_trees(X)", ("gorilla(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lives_in_colonies(X)", ("solitary_bee(X)",), RuleType.DEFEATER)

    # ── Behavioral defaults ──────────────────────────────────────

    rid = _r(theory, rid, "migrates(X)", ("bird(X)",))
    rid = _r(theory, rid, "migrates(X)", ("salmon(X)",))
    rid = _r(theory, rid, "migrates(X)", ("whale(X)",))
    rid = _r(theory, rid, "migrates(X)", ("wildebeest(X)",))
    rid = _r(theory, rid, "hibernates(X)", ("bear(X)",))
    rid = _r(theory, rid, "hibernates(X)", ("hedgehog(X)",))
    rid = _r(theory, rid, "hibernates(X)", ("bat(X)",))
    rid = _r(theory, rid, "is_nocturnal(X)", ("owl(X)",))
    rid = _r(theory, rid, "is_nocturnal(X)", ("bat(X)",))
    rid = _r(theory, rid, "is_nocturnal(X)", ("raccoon(X)",))
    rid = _r(theory, rid, "is_diurnal(X)", ("bird(X)",))
    rid = _r(theory, rid, "is_diurnal(X)", ("primate(X)",))
    rid = _r(theory, rid, "hunts(X)", ("carnivore(X)",))
    rid = _r(theory, rid, "hunts_in_packs(X)", ("wolf(X)",))
    rid = _r(theory, rid, "hunts_in_packs(X)", ("lion(X)",))
    rid = _r(theory, rid, "sings(X)", ("bird(X)",))
    rid = _r(theory, rid, "builds_nest(X)", ("bird(X)",))
    rid = _r(theory, rid, "builds_nest(X)", ("wasp(X)",))
    rid = _r(theory, rid, "produces_silk(X)", ("spider(X)",))
    rid = _r(theory, rid, "produces_silk(X)", ("silkworm(X)",))
    rid = _r(theory, rid, "echolocates(X)", ("bat(X)",))
    rid = _r(theory, rid, "echolocates(X)", ("dolphin(X)",))
    rid = _r(theory, rid, "uses_tools(X)", ("primate(X)",))
    rid = _r(theory, rid, "camouflages(X)", ("chameleon(X)",))
    rid = _r(theory, rid, "camouflages(X)", ("octopus(X)",))
    rid = _r(theory, rid, "regenerates(X)", ("starfish(X)",))
    rid = _r(theory, rid, "regenerates(X)", ("salamander(X)",))
    rid = _r(theory, rid, "produces_venom(X)", ("snake(X)",))
    rid = _r(theory, rid, "produces_venom(X)", ("spider(X)",))
    rid = _r(theory, rid, "produces_venom(X)", ("scorpion(X)",))
    rid = _r(theory, rid, "bioluminesces(X)", ("firefly(X)",))
    rid = _r(theory, rid, "bioluminesces(X)", ("anglerfish(X)",))
    rid = _r(theory, rid, "pollinates(X)", ("bee(X)",))
    rid = _r(theory, rid, "pollinates(X)", ("butterfly(X)",))

    # ── Behavioral defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~migrates(X)", ("chicken(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~migrates(X)", ("penguin(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~migrates(X)", ("pigeon(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~hibernates(X)", ("polar_bear(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_nocturnal(X)", ("fruit_bat(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~sings(X)", ("vulture(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~sings(X)", ("stork(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~builds_nest(X)", ("cuckoo(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~produces_venom(X)", ("python(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~produces_venom(X)", ("king_snake(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~uses_tools(X)", ("lemur(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_diurnal(X)", ("owl(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~hunts_in_packs(X)", ("solitary_lion(X)",), RuleType.DEFEATER)

    # ── Respiration defaults ─────────────────────────────────────

    rid = _r(theory, rid, "breathes_air(X)", ("mammal(X)",))
    rid = _r(theory, rid, "breathes_air(X)", ("bird(X)",))
    rid = _r(theory, rid, "breathes_air(X)", ("reptile(X)",))
    rid = _r(theory, rid, "breathes_water(X)", ("fish(X)",))
    rid = _r(theory, rid, "breathes_both(X)", ("amphibian(X)",))

    # ── Respiration defeaters ────────────────────────────────────

    rid = _r(theory, rid, "~breathes_water(X)", ("lungfish(X)",), RuleType.DEFEATER)

    # ── Sensory capabilities defaults ────────────────────────────

    rid = _r(theory, rid, "has_color_vision(X)", ("primate(X)",))
    rid = _r(theory, rid, "has_color_vision(X)", ("bird(X)",))
    rid = _r(theory, rid, "has_night_vision(X)", ("owl(X)",))
    rid = _r(theory, rid, "has_night_vision(X)", ("cat(X)",))
    rid = _r(theory, rid, "has_electroreception(X)", ("shark(X)",))
    rid = _r(theory, rid, "has_electroreception(X)", ("ray(X)",))
    rid = _r(theory, rid, "has_magnetoreception(X)", ("bird(X)",))
    rid = _r(theory, rid, "has_magnetoreception(X)", ("salmon(X)",))
    rid = _r(theory, rid, "has_lateral_line(X)", ("fish(X)",))
    rid = _r(theory, rid, "detects_infrared(X)", ("snake(X)",))
    rid = _r(theory, rid, "detects_ultraviolet(X)", ("insect(X)",))
    rid = _r(theory, rid, "detects_ultraviolet(X)", ("bird(X)",))

    # ── Sensory defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~has_color_vision(X)", ("nocturnal_primate(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_night_vision(X)", ("diurnal_bird(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_magnetoreception(X)", ("chicken(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_lateral_line(X)", ("lungfish(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~detects_infrared(X)", ("blind_snake(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~detects_ultraviolet(X)", ("ant(X)",), RuleType.DEFEATER)

    # ── Social structure defaults ────────────────────────────────

    rid = _r(theory, rid, "is_solitary(X)", ("cat(X)",))
    rid = _r(theory, rid, "is_solitary(X)", ("bear(X)",))
    rid = _r(theory, rid, "is_solitary(X)", ("tiger(X)",))
    rid = _r(theory, rid, "is_social(X)", ("wolf(X)",))
    rid = _r(theory, rid, "is_social(X)", ("dolphin(X)",))
    rid = _r(theory, rid, "is_social(X)", ("elephant(X)",))
    rid = _r(theory, rid, "is_social(X)", ("primate(X)",))
    rid = _r(theory, rid, "is_territorial(X)", ("bird(X)",))
    rid = _r(theory, rid, "mates_for_life(X)", ("swan(X)",))
    rid = _r(theory, rid, "mates_for_life(X)", ("eagle(X)",))
    rid = _r(theory, rid, "has_dominance_hierarchy(X)", ("wolf(X)",))
    rid = _r(theory, rid, "has_dominance_hierarchy(X)", ("primate(X)",))
    rid = _r(theory, rid, "is_eusocial(X)", ("ant(X)",))
    rid = _r(theory, rid, "is_eusocial(X)", ("bee(X)",))
    rid = _r(theory, rid, "is_eusocial(X)", ("termite(X)",))

    # ── Social defeaters ─────────────────────────────────────────

    rid = _r(theory, rid, "~is_solitary(X)", ("lion(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_social(X)", ("orangutan(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_territorial(X)", ("pigeon(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~mates_for_life(X)", ("duck(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_eusocial(X)", ("solitary_bee(X)",), RuleType.DEFEATER)

    # ── Development defaults ─────────────────────────────────────

    rid = _r(theory, rid, "undergoes_metamorphosis(X)", ("amphibian(X)",))
    rid = _r(theory, rid, "undergoes_metamorphosis(X)", ("insect(X)",))
    rid = _r(theory, rid, "undergoes_molting(X)", ("insect(X)",))
    rid = _r(theory, rid, "undergoes_molting(X)", ("crustacean(X)",))
    rid = _r(theory, rid, "undergoes_molting(X)", ("reptile(X)",))
    rid = _r(theory, rid, "has_larval_stage(X)", ("insect(X)",))
    rid = _r(theory, rid, "has_larval_stage(X)", ("amphibian(X)",))
    rid = _r(theory, rid, "develops_in_egg(X)", ("bird(X)",))
    rid = _r(theory, rid, "develops_in_egg(X)", ("reptile(X)",))
    rid = _r(theory, rid, "develops_in_utero(X)", ("mammal(X)",))

    # ── Development defeaters ────────────────────────────────────

    rid = _r(theory, rid, "~undergoes_metamorphosis(X)", ("silverfish(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~undergoes_metamorphosis(X)", ("direct_developing_frog(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~undergoes_molting(X)", ("mammal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~develops_in_egg(X)", ("viviparous_lizard(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~develops_in_utero(X)", ("platypus(X)",), RuleType.DEFEATER)

    # ── Communication defaults ───────────────────────────────────

    rid = _r(theory, rid, "communicates_acoustically(X)", ("bird(X)",))
    rid = _r(theory, rid, "communicates_acoustically(X)", ("whale(X)",))
    rid = _r(theory, rid, "communicates_acoustically(X)", ("frog(X)",))
    rid = _r(theory, rid, "communicates_chemically(X)", ("ant(X)",))
    rid = _r(theory, rid, "communicates_chemically(X)", ("moth(X)",))
    rid = _r(theory, rid, "uses_pheromones(X)", ("insect(X)",))
    rid = _r(theory, rid, "has_warning_coloration(X)", ("poison_dart_frog(X)",))
    rid = _r(theory, rid, "has_warning_coloration(X)", ("wasp(X)",))
    rid = _r(theory, rid, "has_warning_coloration(X)", ("coral_snake(X)",))
    rid = _r(theory, rid, "communicates_visually(X)", ("bird(X)",))
    rid = _r(theory, rid, "communicates_visually(X)", ("cuttlefish(X)",))

    # ── Communication defeaters ──────────────────────────────────

    rid = _r(theory, rid, "~communicates_acoustically(X)", ("snake(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~communicates_acoustically(X)", ("turtle(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~uses_pheromones(X)", ("vertebrate(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~communicates_visually(X)", ("mole(X)",), RuleType.DEFEATER)

    # ── Defense mechanism defaults ───────────────────────────────

    rid = _r(theory, rid, "has_armor(X)", ("turtle(X)",))
    rid = _r(theory, rid, "has_armor(X)", ("armadillo(X)",))
    rid = _r(theory, rid, "has_armor(X)", ("crustacean(X)",))
    rid = _r(theory, rid, "is_toxic_to_predators(X)", ("poison_dart_frog(X)",))
    rid = _r(theory, rid, "is_toxic_to_predators(X)", ("pufferfish(X)",))
    rid = _r(theory, rid, "uses_mimicry(X)", ("butterfly(X)",))
    rid = _r(theory, rid, "uses_mimicry(X)", ("octopus(X)",))
    rid = _r(theory, rid, "plays_dead(X)", ("opossum(X)",))
    rid = _r(theory, rid, "releases_ink(X)", ("octopus(X)",))
    rid = _r(theory, rid, "releases_ink(X)", ("squid(X)",))
    rid = _r(theory, rid, "has_quills(X)", ("porcupine(X)",))
    rid = _r(theory, rid, "has_quills(X)", ("hedgehog(X)",))

    # ── Defense defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~has_armor(X)", ("soft_shell_turtle(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_toxic_to_predators(X)", ("edible_frog(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~uses_mimicry(X)", ("monarch_butterfly(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_quills(X)", ("baby_hedgehog(X)",), RuleType.DEFEATER)

    # ── Ecological role defaults ─────────────────────────────────

    rid = _r(theory, rid, "is_producer(X)", ("plant(X)",))
    rid = _r(theory, rid, "is_producer(X)", ("algae(X)",))
    rid = _r(theory, rid, "is_primary_consumer(X)", ("herbivore(X)",))
    rid = _r(theory, rid, "is_secondary_consumer(X)", ("carnivore(X)",))
    rid = _r(theory, rid, "is_secondary_consumer(X)", ("insectivore(X)",))
    rid = _r(theory, rid, "is_decomposer(X)", ("fungus(X)",))
    rid = _r(theory, rid, "is_decomposer(X)", ("bacteria(X)",))
    rid = _r(theory, rid, "is_pollinator(X)", ("bee(X)",))
    rid = _r(theory, rid, "is_pollinator(X)", ("butterfly(X)",))
    rid = _r(theory, rid, "is_pollinator(X)", ("hummingbird(X)",))
    rid = _r(theory, rid, "is_seed_disperser(X)", ("bird(X)",))
    rid = _r(theory, rid, "is_seed_disperser(X)", ("bat(X)",))

    # ── Ecological defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~is_producer(X)", ("parasitic_plant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_primary_consumer(X)", ("omnivore(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_pollinator(X)", ("flightless_bee(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_seed_disperser(X)", ("penguin(X)",), RuleType.DEFEATER)

    # ── Multi-body compound rules (defeasible) ───────────────────

    rid = _r(theory, rid, "aquatic_mammal(X)", ("mammal(X)", "lives_in_water(X)"))
    rid = _r(theory, rid, "migratory_flier(X)", ("flies(X)", "migrates(X)"))
    rid = _r(theory, rid, "nocturnal_hunter(X)", ("hunts(X)", "is_nocturnal(X)"))
    rid = _r(theory, rid, "venomous_predator(X)", ("hunts(X)", "produces_venom(X)"))
    rid = _r(theory, rid, "social_insect(X)", ("insect(X)", "lives_in_colonies(X)"))
    rid = _r(theory, rid, "arboreal_primate(X)", ("primate(X)", "lives_in_trees(X)"))
    rid = _r(theory, rid, "burrowing_mammal(X)", ("mammal(X)", "burrows(X)"))
    rid = _r(theory, rid, "egg_laying_mammal(X)", ("mammal(X)", "lays_eggs(X)"))
    rid = _r(theory, rid, "flightless_bird(X)", ("bird(X)", "~flies(X)"))
    rid = _r(theory, rid, "warm_blooded_flier(X)", ("is_warm_blooded(X)", "flies(X)"))
    rid = _r(theory, rid, "cold_blooded_swimmer(X)", ("is_cold_blooded(X)", "swims(X)"))
    rid = _r(theory, rid, "pack_hunter(X)", ("hunts(X)", "is_social(X)"))
    rid = _r(theory, rid, "solitary_predator(X)", ("hunts(X)", "is_solitary(X)"))
    rid = _r(theory, rid, "nocturnal_flier(X)", ("flies(X)", "is_nocturnal(X)"))
    rid = _r(theory, rid, "diurnal_singer(X)", ("sings(X)", "is_diurnal(X)"))
    rid = _r(theory, rid, "aquatic_egg_layer(X)", ("lives_in_water(X)", "lays_eggs(X)"))
    rid = _r(theory, rid, "terrestrial_herbivore(X)", ("lives_on_land(X)", "eats_plants(X)"))
    rid = _r(theory, rid, "marine_predator(X)", ("lives_in_water(X)", "hunts(X)"))
    rid = _r(theory, rid, "aerial_hunter(X)", ("flies(X)", "hunts(X)"))
    rid = _r(theory, rid, "amphibious_animal(X)", ("breathes_air(X)", "swims(X)"))
    rid = _r(theory, rid, "venomous_reptile(X)", ("reptile(X)", "produces_venom(X)"))
    rid = _r(theory, rid, "singing_migratory(X)", ("sings(X)", "migrates(X)"))
    rid = _r(theory, rid, "colonial_pollinator(X)", ("lives_in_colonies(X)", "pollinates(X)"))
    rid = _r(theory, rid, "armored_herbivore(X)", ("has_armor(X)", "eats_plants(X)"))
    rid = _r(theory, rid, "camouflaged_predator(X)", ("camouflages(X)", "hunts(X)"))
    rid = _r(theory, rid, "deep_sea_hunter(X)", ("lives_in_water(X)", "bioluminesces(X)", "hunts(X)"))
    rid = _r(theory, rid, "tool_using_social(X)", ("uses_tools(X)", "is_social(X)"))
    rid = _r(theory, rid, "metamorphic_flier(X)", ("undergoes_metamorphosis(X)", "flies(X)"))
    rid = _r(theory, rid, "echolocating_hunter(X)", ("echolocates(X)", "hunts(X)"))
    rid = _r(theory, rid, "regenerating_marine(X)", ("regenerates(X)", "lives_in_water(X)"))

    # ── Multi-body compound defeaters ────────────────────────────

    rid = _r(theory, rid, "~aquatic_mammal(X)", ("otter(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~migratory_flier(X)", ("chicken(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~nocturnal_hunter(X)", ("fruit_bat(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~pack_hunter(X)", ("cheetah(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~solitary_predator(X)", ("wolf(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~diurnal_singer(X)", ("nightingale(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~terrestrial_herbivore(X)", ("hippopotamus(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~colonial_pollinator(X)", ("solitary_bee(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~tool_using_social(X)", ("lemur(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~echolocating_hunter(X)", ("fruit_bat(X)",), RuleType.DEFEATER)

    return theory


def add_bio_superiority_relations(theory: Theory) -> None:
    """Add superiority relations so defeaters override their defaults.

    Each relation declares that a more-specific defeater rule is superior
    to the general default it overrides, ensuring correct defeasible
    resolution.

    Label mapping (sequential from rid=1000):
        bio_r1000  flies(X) :- bird(X)
        bio_r1001  flies(X) :- insect(X)
        bio_r1009  walks(X) :- mammal(X)
        bio_r1010  walks(X) :- reptile(X)
        bio_r1012  runs(X) :- mammal(X)
        bio_r1040  has_fur(X) :- mammal(X)
        bio_r1071  is_cold_blooded(X) :- reptile(X)
        bio_r1073  is_cold_blooded(X) :- fish(X)
        bio_r1083  gives_live_birth(X) :- mammal(X)
        bio_r1103  lives_in_water(X) :- fish(X)
        bio_r1106  lives_on_land(X) :- mammal(X)
    """

    # Flightless birds defeat bird-flies default (bio_r1000)
    theory.add_superiority("bio_r1024", "bio_r1000")  # penguin
    theory.add_superiority("bio_r1025", "bio_r1000")  # ostrich
    theory.add_superiority("bio_r1026", "bio_r1000")  # kiwi
    theory.add_superiority("bio_r1027", "bio_r1000")  # emu
    theory.add_superiority("bio_r1028", "bio_r1000")  # cassowary
    theory.add_superiority("bio_r1029", "bio_r1000")  # dodo

    # Flightless insects defeat insect-flies default (bio_r1001)
    theory.add_superiority("bio_r1030", "bio_r1001")  # flea
    theory.add_superiority("bio_r1031", "bio_r1001")  # ant

    # Non-walking mammals defeat mammal-walks default (bio_r1009)
    theory.add_superiority("bio_r1032", "bio_r1009")  # whale
    theory.add_superiority("bio_r1033", "bio_r1009")  # dolphin
    theory.add_superiority("bio_r1035", "bio_r1009")  # seal

    # Snake defeats reptile-walks default (bio_r1010)
    theory.add_superiority("bio_r1034", "bio_r1010")  # snake

    # Sloth defeats mammal-runs default (bio_r1012)
    theory.add_superiority("bio_r1036", "bio_r1012")  # sloth

    # Hairless mammals defeat mammal-has_fur default (bio_r1040)
    theory.add_superiority("bio_r1060", "bio_r1040")  # dolphin
    theory.add_superiority("bio_r1061", "bio_r1040")  # whale
    theory.add_superiority("bio_r1062", "bio_r1040")  # naked mole rat

    # Warm fish defeat fish-is_cold_blooded default (bio_r1073)
    theory.add_superiority("bio_r1075", "bio_r1073")  # tuna
    theory.add_superiority("bio_r1076", "bio_r1073")  # great white shark

    # Warm reptile defeats reptile-is_cold_blooded default (bio_r1071)
    theory.add_superiority("bio_r1077", "bio_r1071")  # leatherback turtle

    # Egg-laying mammals defeat mammal-gives_live_birth (bio_r1083)
    theory.add_superiority("bio_r1085", "bio_r1083")  # platypus
    theory.add_superiority("bio_r1086", "bio_r1083")  # echidna

    # Marine mammals defeat mammal-lives_on_land default (bio_r1106)
    theory.add_superiority("bio_r1115", "bio_r1106")  # whale
    theory.add_superiority("bio_r1116", "bio_r1106")  # dolphin
    theory.add_superiority("bio_r1117", "bio_r1106")  # seal

    # Lungfish defeats fish-lives_in_water default (bio_r1103)
    theory.add_superiority("bio_r1118", "bio_r1103")  # lungfish


def count_behavioral_rules(theory: Theory) -> dict:
    """Return a breakdown of behavioral rule counts by type."""
    bio_rules = [r for r in theory.rules if r.label and r.label.startswith("bio_r")]
    defeasible = [r for r in bio_rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in bio_rules if r.rule_type == RuleType.DEFEATER]
    return {
        "total_behavioral": len(bio_rules),
        "defeasible": len(defeasible),
        "defeaters": len(defeaters),
    }
