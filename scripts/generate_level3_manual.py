"""
Phase 2B: Manual Level 3 Defeater Abduction Instance Generation.

Generates 35+ validated defeater abduction instances across biology (15),
legal (10), and materials science (10) domains. Instances are verified
programmatically: anomaly provability, defeater effectiveness, and
conservativity. Novelty (Nov) and revision distance (d_rev) are computed
per Definition 14 and Definition 15 of paper.tex.

Author: Anonymous Authors
Date: 2026-02-18
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable
from blanc.author.metrics import (
    predicate_novelty as compute_novelty,
    check_conservativity,
)


# ─── Infrastructure ──────────────────────────────────────────────────────────

def _copy(t: Theory) -> Theory:
    """Deep-copy a theory."""
    t2 = Theory()
    for f in t.facts:
        t2.add_fact(f)
    for r in t.rules:
        t2.add_rule(Rule(
            head=r.head, body=r.body,
            rule_type=r.rule_type, label=r.label,
            metadata=dict(r.metadata) if r.metadata else {}
        ))
    t2.superiority = {k: v.copy() for k, v in t.superiority.items()}
    return t2


def _build_full(
    D_minus: Theory,
    defeater: Rule,
    beaten_labels: List[str],
    novel_facts: List[str] = None,
) -> Theory:
    """Add defeater (and optional novel_facts) to D^- and set superiority."""
    D_full = _copy(D_minus)
    if novel_facts:
        for f in novel_facts:
            D_full.add_fact(f)
    D_full.add_rule(defeater)
    for lbl in beaten_labels:
        D_full.add_superiority(defeater.label, lbl)
    return D_full


def verify_instance(
    name: str,
    D_minus: Theory,
    anomaly: str,
    gold: Rule,
    beaten_labels: List[str],
    distractors: List[Rule],
    preserved: List[str],
    novel_facts: List[str] = None,
) -> dict:
    """
    Full programmatic verification of a Level 3 instance.

    Checks:
      1. D^- ⊢∂ anomaly  (the challenge theory creates the anomaly)
      2. D^full ⊬∂ anomaly  (gold defeater resolves it)
      3. Conservativity: all preserved expectations hold in D^full
      4. Each distractor is not a hidden gold answer:
         a distractor is "bad" only if it BOTH resolves the anomaly AND
         is conservative (it would also be a valid gold answer).
         Distractors that resolve but are non-conservative are intentional:
         they test whether the model correctly prioritises conservativity.
    """
    errors = []

    # 1. Anomaly provability
    if not defeasible_provable(D_minus, anomaly):
        errors.append(f"anomaly '{anomaly}' not provable in D^-")

    # 2. Gold effectiveness (using novel_facts for D^full construction)
    D_full = _build_full(D_minus, gold, beaten_labels, novel_facts)
    if defeasible_provable(D_full, anomaly):
        errors.append(f"gold '{gold.label}' does not block anomaly")

    # 3. Conservativity
    conservative, lost = check_conservativity(D_minus, D_full, anomaly, preserved)

    # 4. Distractor check: bad = resolves anomaly AND is conservative
    #    (That would make it an undisclosed correct answer.)
    #    Distractors that resolve but violate conservativity are fine:
    #    they teach the model that conservativity matters.
    bad_distractors = []
    for d in distractors:
        # Distractors are tested WITHOUT novel_facts (model sees D^- only)
        D_test = _build_full(D_minus, d, beaten_labels)
        resolves = not defeasible_provable(D_test, anomaly)
        if resolves:
            d_conservative, _ = check_conservativity(
                D_minus, D_test, anomaly, preserved
            )
            if d_conservative:
                bad_distractors.append(d.label)

    if bad_distractors:
        errors.append(f"distractors that are also valid answers: {bad_distractors}")

    valid = len(errors) == 0 and conservative
    nov = compute_novelty(gold, D_minus)

    result = {
        "name": name,
        "valid": valid,
        "conservative": conservative,
        "nov": nov,
        "d_rev": 1 + len(lost),
        "lost_expectations": lost,
        "errors": errors,
    }

    status = "[OK]" if valid else "[FAIL]"
    nc = "" if conservative else " NON-CONSERVATIVE"
    print(f"  {status} {name} (Nov={nov:.2f}{nc})" + (f" | {errors}" if errors else ""))
    return result


def _make_instance(
    name: str,
    domain: str,
    D_minus: Theory,
    anomaly: str,
    gold: Rule,
    beaten_labels: List[str],
    distractors: List[Rule],
    preserved: List[str],
    defeater_type: str,
    description: str,
    novel_predicates: List[str] = None,
    novel_facts: List[str] = None,
) -> dict:
    """Build and verify a Level 3 instance, returning the full serialised dict."""
    vr = verify_instance(
        name, D_minus, anomaly, gold, beaten_labels,
        distractors, preserved, novel_facts,
    )
    return {
        "name": name,
        "domain": domain,
        "level": 3,
        "anomaly": anomaly,
        "gold": str(gold),
        "gold_label": gold.label,
        "beaten_rules": beaten_labels,
        "distractors": [str(d) for d in distractors],
        "candidates": [str(gold)] + [str(d) for d in distractors],
        "preserved_expectations": preserved,
        "defeater_type": defeater_type,
        "description": description,
        "novel_predicates": novel_predicates or [],
        "novel_facts_for_gold": novel_facts or [],
        "nov": vr["nov"],
        "d_rev": vr["d_rev"],
        "conservative": vr["conservative"],
        "lost_expectations": vr["lost_expectations"],
        "valid": vr["valid"],
        "errors": vr["errors"],
        "theory_size": len(D_minus),
        "theory_facts": sorted(D_minus.facts),
        "theory_rules": [str(r) for r in D_minus.rules],
    }


# ─── Biology Instances ───────────────────────────────────────────────────────

def bio_flightless_bird(
    name: str,
    entity: str,
    species_pred: str,
    description: str,
) -> dict:
    """
    Template: bird that doesn't fly.
    D^-: bird(entity), species(entity), bird(tweety), sparrow(tweety)
    Defeasible default: bird(X) => flies(X)
    Anomaly: flies(entity)
    Gold: ~flies(X) :- species(entity) with d > r_flies
    Preserved: flies(tweety)
    """
    D = Theory()
    D.add_fact(f"bird({entity})")
    D.add_fact(f"{species_pred}({entity})")
    D.add_fact("bird(tweety)")
    D.add_fact("sparrow(tweety)")
    D.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_flies"))
    D.add_rule(Rule(head="has_feathers(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_feathers"))
    D.add_rule(Rule(head="warm_blooded(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_warm"))

    gold = Rule(head=f"~flies(X)", body=(f"{species_pred}(X)",),
                rule_type=RuleType.DEFEATER, label=f"d_{name}")

    distractors = [
        Rule(head="~flies(X)", body=("bird(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_broad"),
        Rule(head="~has_feathers(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_wrong_head"),
        Rule(head="~warm_blooded(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_irrelevant"),
        Rule(head="walks(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEASIBLE, label=f"d_{name}_positive"),
        Rule(head="~flies(X)", body=("large(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_wrong_cond"),
    ]

    preserved = ["flies(tweety)", "has_feathers(tweety)", "warm_blooded(tweety)"]

    return _make_instance(
        name=name, domain="biology",
        D_minus=D, anomaly=f"flies({entity})",
        gold=gold, beaten_labels=["r_flies"],
        distractors=distractors, preserved=preserved,
        defeater_type="weak", description=description,
    )


def bio_non_walking_mammal(
    name: str,
    entity: str,
    species_pred: str,
    description: str,
    strong: bool = False,
) -> dict:
    """
    Template: mammal that doesn't walk.
    Optional strong=True adds a positive rule (mammal swims).
    """
    D = Theory()
    D.add_fact(f"mammal({entity})")
    D.add_fact(f"{species_pred}({entity})")
    D.add_fact("mammal(felix)")
    D.add_fact("cat(felix)")
    D.add_rule(Rule(head="walks(X)", body=("mammal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_walks"))
    D.add_rule(Rule(head="warm_blooded(X)", body=("mammal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_warm"))
    D.add_rule(Rule(head="has_fur(X)", body=("cat(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_fur"))

    gold = Rule(head="~walks(X)", body=(f"{species_pred}(X)",),
                rule_type=RuleType.DEFEATER, label=f"d_{name}")

    distractors = [
        Rule(head="~walks(X)", body=("mammal(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_broad"),
        Rule(head="~warm_blooded(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_wrong_head"),
        Rule(head="swims(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEASIBLE, label=f"d_{name}_positive"),
        Rule(head="~has_fur(X)", body=(f"{species_pred}(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_irrelevant"),
        Rule(head="~walks(X)", body=("aquatic(X)",),
             rule_type=RuleType.DEFEATER, label=f"d_{name}_wrong_cond"),
    ]

    preserved = ["walks(felix)", "warm_blooded(felix)", "has_fur(felix)"]

    return _make_instance(
        name=name, domain="biology",
        D_minus=D, anomaly=f"walks({entity})",
        gold=gold, beaten_labels=["r_walks"],
        distractors=distractors, preserved=preserved,
        defeater_type="strong" if strong else "weak",
        description=description,
    )


def _bio_instances() -> List[dict]:
    instances = []
    print("\n[Biology]")

    # ── Flightless birds ─────────────────────────────────────────────────
    instances.append(bio_flightless_bird(
        "penguin", "opus", "penguin",
        "Penguins are birds but cannot fly; their wings are adapted as flippers."
    ))
    instances.append(bio_flightless_bird(
        "ostrich", "obi", "ostrich",
        "Ostriches are the largest birds and are flightless; they run instead."
    ))
    instances.append(bio_flightless_bird(
        "emu", "emma", "emu",
        "Emus are large flightless birds native to Australia."
    ))
    instances.append(bio_flightless_bird(
        "cassowary", "cass", "cassowary",
        "Cassowaries are dangerous flightless birds found in New Guinea."
    ))
    instances.append(bio_flightless_bird(
        "kiwi", "kiri", "kiwi",
        "Kiwis are small flightless birds native to New Zealand with vestigial wings."
    ))

    # ── Non-walking mammals ───────────────────────────────────────────────
    instances.append(bio_non_walking_mammal(
        "bat", "brucie", "bat",
        "Bats are the only flying mammals; their forelimbs form wings."
    ))
    instances.append(bio_non_walking_mammal(
        "whale", "wally", "whale",
        "Whales are fully aquatic mammals with no functional hind limbs."
    ))
    instances.append(bio_non_walking_mammal(
        "dolphin", "flippy", "dolphin",
        "Dolphins are cetaceans whose limbs evolved into fins for aquatic locomotion.",
        strong=True,
    ))

    # ── Platypus: egg-laying mammal ───────────────────────────────────────
    D = Theory()
    D.add_fact("mammal(percy)")
    D.add_fact("platypus(percy)")
    D.add_fact("mammal(felix)")
    D.add_fact("cat(felix)")
    D.add_rule(Rule(head="gives_live_birth(X)", body=("mammal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_birth"))
    D.add_rule(Rule(head="warm_blooded(X)", body=("mammal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_warm_p"))
    D.add_rule(Rule(head="has_fur(X)", body=("mammal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_fur_p"))
    gold = Rule(head="~gives_live_birth(X)", body=("platypus(X)",),
                rule_type=RuleType.DEFEATER, label="d_platypus")
    distractors = [
        Rule(head="~gives_live_birth(X)", body=("mammal(X)",),
             rule_type=RuleType.DEFEATER, label="d_plat_broad"),
        Rule(head="~warm_blooded(X)", body=("platypus(X)",),
             rule_type=RuleType.DEFEATER, label="d_plat_wrong_head"),
        Rule(head="lays_eggs(X)", body=("platypus(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_plat_positive"),
        Rule(head="~has_fur(X)", body=("platypus(X)",),
             rule_type=RuleType.DEFEATER, label="d_plat_irrelevant"),
        Rule(head="~gives_live_birth(X)", body=("aquatic(X)",),
             rule_type=RuleType.DEFEATER, label="d_plat_wrong_cond"),
    ]
    instances.append(_make_instance(
        name="platypus", domain="biology",
        D_minus=D, anomaly="gives_live_birth(percy)",
        gold=gold, beaten_labels=["r_birth"],
        distractors=distractors,
        preserved=["gives_live_birth(felix)", "warm_blooded(felix)", "has_fur(felix)"],
        defeater_type="weak",
        description="Platypuses are monotremes: egg-laying mammals, "
                    "an exception to the mammalian default of live birth.",
    ))

    # ── Panda: herbivorous bear ───────────────────────────────────────────
    D = Theory()
    D.add_fact("bear(pandy)")
    D.add_fact("panda(pandy)")
    D.add_fact("bear(grizz)")
    D.add_fact("grizzly(grizz)")
    D.add_rule(Rule(head="carnivore(X)", body=("bear(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_carn"))
    D.add_rule(Rule(head="large_mammal(X)", body=("bear(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_large"))
    gold = Rule(head="~carnivore(X)", body=("panda(X)",),
                rule_type=RuleType.DEFEATER, label="d_panda")
    distractors = [
        Rule(head="~carnivore(X)", body=("bear(X)",),
             rule_type=RuleType.DEFEATER, label="d_panda_broad"),
        Rule(head="~large_mammal(X)", body=("panda(X)",),
             rule_type=RuleType.DEFEATER, label="d_panda_wrong_head"),
        Rule(head="herbivore(X)", body=("panda(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_panda_positive"),
        Rule(head="~carnivore(X)", body=("asian(X)",),
             rule_type=RuleType.DEFEATER, label="d_panda_wrong_cond"),
        Rule(head="bamboo_eater(X)", body=("panda(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_panda_irrelevant"),
    ]
    instances.append(_make_instance(
        name="panda", domain="biology",
        D_minus=D, anomaly="carnivore(pandy)",
        gold=gold, beaten_labels=["r_carn"],
        distractors=distractors,
        preserved=["carnivore(grizz)", "large_mammal(grizz)", "large_mammal(pandy)"],
        defeater_type="weak",
        description="Giant pandas are bears that subsist almost entirely on bamboo, "
                    "making them an exception to the default that bears are carnivores.",
    ))

    # ── Cuckoo: brood parasite ────────────────────────────────────────────
    D = Theory()
    D.add_fact("bird(coco)")
    D.add_fact("cuckoo(coco)")
    D.add_fact("bird(tweety)")
    D.add_fact("sparrow(tweety)")
    D.add_rule(Rule(head="builds_nest(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_nest"))
    D.add_rule(Rule(head="raises_own_young(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_young"))
    D.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_flies_c"))
    gold = Rule(head="~builds_nest(X)", body=("cuckoo(X)",),
                rule_type=RuleType.DEFEATER, label="d_cuckoo")
    distractors = [
        Rule(head="~builds_nest(X)", body=("bird(X)",),
             rule_type=RuleType.DEFEATER, label="d_cuck_broad"),
        Rule(head="~raises_own_young(X)", body=("cuckoo(X)",),
             rule_type=RuleType.DEFEATER, label="d_cuck_wrong_head"),
        Rule(head="~flies(X)", body=("cuckoo(X)",),
             rule_type=RuleType.DEFEATER, label="d_cuck_wrong_action"),
        Rule(head="parasite(X)", body=("cuckoo(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_cuck_positive"),
        Rule(head="~builds_nest(X)", body=("parasite(X)",),
             rule_type=RuleType.DEFEATER, label="d_cuck_indirect"),
    ]
    instances.append(_make_instance(
        name="cuckoo", domain="biology",
        D_minus=D, anomaly="builds_nest(coco)",
        gold=gold, beaten_labels=["r_nest"],
        distractors=distractors,
        preserved=["builds_nest(tweety)", "raises_own_young(tweety)", "flies(tweety)"],
        defeater_type="weak",
        description="Cuckoos are brood parasites: they lay eggs in other species' nests "
                    "rather than building their own.",
    ))

    # ── Lungfish: air-breathing fish (Nov > 0) ────────────────────────────
    # Two-entity pattern: lenny has accessory lung, gill_gill does not.
    # The non-novel distractor (~breathes_with_gills(X) :- lungfish(X))
    # blocks BOTH lenny and gill_gill -> non-conservative -> valid distractor.
    D = Theory()
    D.add_fact("fish(lenny)")
    D.add_fact("lungfish(lenny)")
    D.add_fact("fish(gill_gill)")
    D.add_fact("lungfish(gill_gill)")   # second lungfish: still breathes with gills
    D.add_fact("fish(nemo)")
    D.add_fact("salmon(nemo)")
    D.add_rule(Rule(head="breathes_with_gills(X)", body=("fish(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_gills"))
    D.add_rule(Rule(head="cold_blooded(X)", body=("fish(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_cold"))
    D.add_rule(Rule(head="spawns_upstream(X)", body=("salmon(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_spawn"))
    # Novel predicate 'has_accessory_lung' NOT added to D^- (kept in novel_facts).
    gold_lung = Rule(head="~breathes_with_gills(X)", body=("has_accessory_lung(X)",),
                     rule_type=RuleType.DEFEATER, label="d_lungfish")
    distractors_lung = [
        Rule(head="~breathes_with_gills(X)", body=("fish(X)",),
             rule_type=RuleType.DEFEATER, label="d_lung_broad"),
        Rule(head="~cold_blooded(X)", body=("lungfish(X)",),
             rule_type=RuleType.DEFEATER, label="d_lung_wrong_head"),
        Rule(head="~breathes_with_gills(X)", body=("lungfish(X)",),
             rule_type=RuleType.DEFEATER, label="d_lung_no_novel"),
        Rule(head="breathes_air(X)", body=("lungfish(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_lung_positive"),
        Rule(head="~spawns_upstream(X)", body=("lungfish(X)",),
             rule_type=RuleType.DEFEATER, label="d_lung_irrelevant"),
    ]
    instances.append(_make_instance(
        name="lungfish", domain="biology",
        D_minus=D, anomaly="breathes_with_gills(lenny)",
        gold=gold_lung, beaten_labels=["r_gills"],
        distractors=distractors_lung,
        preserved=["breathes_with_gills(gill_gill)", "breathes_with_gills(nemo)",
                   "cold_blooded(nemo)", "spawns_upstream(nemo)"],
        defeater_type="weak",
        description="Lungfish with accessory lungs can breathe air, an exception to the "
                    "fish default of gill respiration. Not all lungfish have this adaptation.",
        novel_predicates=["has_accessory_lung"],
        novel_facts=["has_accessory_lung(lenny)"],
    ))

    # ── Axolotl: neotenic amphibian (Nov > 0) ────────────────────────────
    # Two-entity pattern: axo is neotenic, normal_axo is not.
    D = Theory()
    D.add_fact("amphibian(axo)")
    D.add_fact("axolotl(axo)")
    D.add_fact("amphibian(normal_axo)")
    D.add_fact("axolotl(normal_axo)")
    D.add_fact("amphibian(frog_fred)")
    D.add_fact("frog(frog_fred)")
    D.add_rule(Rule(head="undergoes_metamorphosis(X)", body=("amphibian(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_meta"))
    D.add_rule(Rule(head="cold_blooded(X)", body=("amphibian(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_cold_a"))
    D.add_rule(Rule(head="moist_skin(X)", body=("frog(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_skin"))
    # Novel predicate 'neotenic' NOT in D^-.
    gold_axo = Rule(head="~undergoes_metamorphosis(X)", body=("neotenic(X)",),
                    rule_type=RuleType.DEFEATER, label="d_axolotl")
    distractors_axo = [
        Rule(head="~undergoes_metamorphosis(X)", body=("amphibian(X)",),
             rule_type=RuleType.DEFEATER, label="d_axo_broad"),
        Rule(head="~cold_blooded(X)", body=("axolotl(X)",),
             rule_type=RuleType.DEFEATER, label="d_axo_wrong_head"),
        Rule(head="~undergoes_metamorphosis(X)", body=("axolotl(X)",),
             rule_type=RuleType.DEFEATER, label="d_axo_no_novel"),
        Rule(head="retains_gills(X)", body=("axolotl(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_axo_positive"),
        Rule(head="~moist_skin(X)", body=("axolotl(X)",),
             rule_type=RuleType.DEFEATER, label="d_axo_irrelevant"),
    ]
    instances.append(_make_instance(
        name="axolotl", domain="biology",
        D_minus=D, anomaly="undergoes_metamorphosis(axo)",
        gold=gold_axo, beaten_labels=["r_meta"],
        distractors=distractors_axo,
        preserved=["undergoes_metamorphosis(normal_axo)", "undergoes_metamorphosis(frog_fred)",
                   "cold_blooded(frog_fred)", "moist_skin(frog_fred)"],
        defeater_type="weak",
        description="Neotenic axolotls retain larval features permanently and never "
                    "metamorphose. Not all axolotls are neotenic.",
        novel_predicates=["neotenic"],
        novel_facts=["neotenic(axo)"],
    ))

    # ── Vampire bat: hematophagous mammal (Nov > 0) ───────────────────────
    # Two-entity pattern: vlad is hematophagous, pip is not.
    D = Theory()
    D.add_fact("bat(vlad)")
    D.add_fact("vampire_bat(vlad)")
    D.add_fact("bat(pip)")
    D.add_fact("pipistrelle(pip)")
    D.add_fact("bat(reg)")
    D.add_fact("vampire_bat(reg)")   # second vampire bat: not hematophagous (hypothetically)
    D.add_rule(Rule(head="insectivore(X)", body=("bat(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_insect"))
    D.add_rule(Rule(head="nocturnal(X)", body=("bat(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_noc"))
    D.add_rule(Rule(head="echolocates(X)", body=("pipistrelle(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_echo"))
    # Novel predicate 'hematophagous' NOT in D^-.
    gold_vbat = Rule(head="~insectivore(X)", body=("hematophagous(X)",),
                     rule_type=RuleType.DEFEATER, label="d_vampire_bat")
    distractors_vbat = [
        Rule(head="~insectivore(X)", body=("bat(X)",),
             rule_type=RuleType.DEFEATER, label="d_vbat_broad"),
        Rule(head="~nocturnal(X)", body=("vampire_bat(X)",),
             rule_type=RuleType.DEFEATER, label="d_vbat_wrong_head"),
        Rule(head="~insectivore(X)", body=("vampire_bat(X)",),
             rule_type=RuleType.DEFEATER, label="d_vbat_no_novel"),
        Rule(head="blood_feeder(X)", body=("vampire_bat(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_vbat_positive"),
        Rule(head="~echolocates(X)", body=("vampire_bat(X)",),
             rule_type=RuleType.DEFEATER, label="d_vbat_irrelevant"),
    ]
    instances.append(_make_instance(
        name="vampire_bat", domain="biology",
        D_minus=D, anomaly="insectivore(vlad)",
        gold=gold_vbat, beaten_labels=["r_insect"],
        distractors=distractors_vbat,
        preserved=["insectivore(reg)", "insectivore(pip)",
                   "nocturnal(pip)", "echolocates(pip)"],
        defeater_type="weak",
        description="Vampire bats that have the hematophagous feeding adaptation feed "
                    "exclusively on blood, not insects. Not all vampire bats do.",
        novel_predicates=["hematophagous"],
        novel_facts=["hematophagous(vlad)"],
    ))

    # ── Seahorse: male-gestating fish (Nov > 0) ───────────────────────────
    # Two-entity pattern: floaty has paternal_gestation, sandy does not.
    D = Theory()
    D.add_fact("fish(floaty)")
    D.add_fact("seahorse(floaty)")
    D.add_fact("fish(sandy)")
    D.add_fact("seahorse(sandy)")    # second seahorse: female gestates normally
    D.add_fact("fish(nemo2)")
    D.add_fact("clownfish(nemo2)")
    D.add_rule(Rule(head="female_gestates(X)", body=("fish(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_gestate"))
    D.add_rule(Rule(head="cold_blooded(X)", body=("fish(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_cold_s"))
    D.add_rule(Rule(head="bright_colored(X)", body=("clownfish(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_bright"))
    # Novel predicate 'paternal_gestation' NOT in D^-.
    gold_sea = Rule(head="~female_gestates(X)", body=("paternal_gestation(X)",),
                    rule_type=RuleType.DEFEATER, label="d_seahorse")
    distractors_sea = [
        Rule(head="~female_gestates(X)", body=("fish(X)",),
             rule_type=RuleType.DEFEATER, label="d_sea_broad"),
        Rule(head="~cold_blooded(X)", body=("seahorse(X)",),
             rule_type=RuleType.DEFEATER, label="d_sea_wrong_head"),
        Rule(head="~female_gestates(X)", body=("seahorse(X)",),
             rule_type=RuleType.DEFEATER, label="d_sea_no_novel"),
        Rule(head="male_pregnancy(X)", body=("seahorse(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_sea_positive"),
        Rule(head="~bright_colored(X)", body=("seahorse(X)",),
             rule_type=RuleType.DEFEATER, label="d_sea_irrelevant"),
    ]
    instances.append(_make_instance(
        name="seahorse", domain="biology",
        D_minus=D, anomaly="female_gestates(floaty)",
        gold=gold_sea, beaten_labels=["r_gestate"],
        preserved=["female_gestates(sandy)", "female_gestates(nemo2)",
                   "cold_blooded(nemo2)", "bright_colored(nemo2)"],
        defeater_type="weak",
        description="Individual seahorses exhibiting paternal gestation have the male "
                    "carry and birth the young. Not all seahorses display this.",
        novel_predicates=["paternal_gestation"],
        novel_facts=["paternal_gestation(floaty)"],
        distractors=distractors_sea,
    ))

    # ── Tardigrade: survives desiccation (Nov = 0) ────────────────────────────
    # Tardigrades (water bears) can enter cryptobiosis -- a near-complete
    # suspension of metabolic activity -- surviving desiccation that is lethal
    # to all other animals. The predicate `tardigrade` is already in D^-.
    D = Theory()
    D.add_fact("animal(tardigrade_specimen)")
    D.add_fact("animal(rabbit_specimen)")
    D.add_fact("tardigrade(tardigrade_specimen)")
    D.add_rule(Rule(head="requires_water(X)", body=("animal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_water"))
    D.add_rule(Rule(head="requires_oxygen(X)", body=("animal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_oxygen"))
    D.add_rule(Rule(head="temperature_sensitive(X)", body=("animal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_temp"))
    gold_tard = Rule(head="~requires_water(X)", body=("tardigrade(X)",),
                     rule_type=RuleType.DEFEATER, label="d_tardigrade")
    distractors_tard = [
        Rule(head="~requires_water(X)", body=("animal(X)",),
             rule_type=RuleType.DEFEATER, label="d_tard_broad"),
        Rule(head="~requires_oxygen(X)", body=("tardigrade(X)",),
             rule_type=RuleType.DEFEATER, label="d_tard_wrong_head"),
        Rule(head="~temperature_sensitive(X)", body=("tardigrade(X)",),
             rule_type=RuleType.DEFEATER, label="d_tard_wrong_prop"),
        Rule(head="survives_desiccation(X)", body=("tardigrade(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_tard_positive"),
        Rule(head="~requires_water(X)", body=("microscopic(X)",),
             rule_type=RuleType.DEFEATER, label="d_tard_wrong_cond"),
    ]
    instances.append(_make_instance(
        name="tardigrade", domain="biology",
        D_minus=D, anomaly="requires_water(tardigrade_specimen)",
        gold=gold_tard, beaten_labels=["r_water"],
        distractors=distractors_tard,
        preserved=["requires_water(rabbit_specimen)", "requires_oxygen(rabbit_specimen)",
                   "temperature_sensitive(rabbit_specimen)"],
        defeater_type="weak",
        description="Tardigrades (water bears) can enter cryptobiosis, surviving complete "
                    "desiccation that is lethal to all other animals. They are the exception "
                    "to the rule that animals require continuous access to water.",
    ))

    return instances


# ─── Legal Instances ──────────────────────────────────────────────────────────

def _legal_instances() -> List[dict]:
    instances = []
    print("\n[Legal]")

    # ── Emancipated minor: can contract (Nov > 0) ─────────────────────────
    # Two-entity pattern: alex is court_emancipated, sam is not.
    # The non-novel distractor uses 'emancipated_minor' which would block BOTH
    # alex and sam (if sam were also emancipated_minor) - but here we use
    # 'court_emancipated' as the novel predicate so it's separate from status.
    D = Theory()
    D.add_fact("minor(alex)")
    D.add_fact("minor(sam)")
    D.add_fact("adult(taylor)")
    D.add_rule(Rule(head="lacks_contractual_capacity(X)", body=("minor(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_minor_cap"))
    D.add_rule(Rule(head="bound_by_contract(X)", body=("adult(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_adult_bound"))
    D.add_rule(Rule(head="subject_to_parental_authority(X)", body=("minor(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_parental"))
    # Novel predicate 'court_emancipated' NOT in D^-.
    gold_em = Rule(head="~lacks_contractual_capacity(X)", body=("court_emancipated(X)",),
                   rule_type=RuleType.DEFEATER, label="d_emancipated")
    distractors_em = [
        Rule(head="~lacks_contractual_capacity(X)", body=("minor(X)",),
             rule_type=RuleType.DEFEATER, label="d_em_broad"),
        Rule(head="~subject_to_parental_authority(X)", body=("court_emancipated(X)",),
             rule_type=RuleType.DEFEATER, label="d_em_wrong_head"),
        Rule(head="has_contractual_capacity(X)", body=("court_emancipated(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_em_positive"),
        Rule(head="~lacks_contractual_capacity(X)", body=("adult(X)",),
             rule_type=RuleType.DEFEATER, label="d_em_wrong_cond"),
        Rule(head="~bound_by_contract(X)", body=("court_emancipated(X)",),
             rule_type=RuleType.DEFEATER, label="d_em_irrelevant"),
    ]
    instances.append(_make_instance(
        name="emancipated_minor", domain="legal",
        D_minus=D, anomaly="lacks_contractual_capacity(alex)",
        gold=gold_em, beaten_labels=["r_minor_cap"],
        distractors=distractors_em,
        preserved=["lacks_contractual_capacity(sam)", "bound_by_contract(taylor)",
                   "subject_to_parental_authority(sam)"],
        defeater_type="weak",
        description="A court-emancipated minor has been legally freed from parental "
                    "control and gains contractual capacity. Non-emancipated minors retain "
                    "incapacity.",
        novel_predicates=["court_emancipated"],
        novel_facts=["court_emancipated(alex)"],
    ))

    # ── Statute of limitations: time-bars valid claim ─────────────────────
    D = Theory()
    D.add_fact("legal_claim(claim_a)")
    D.add_fact("time_barred(claim_a)")
    D.add_fact("legal_claim(claim_b)")
    D.add_fact("timely(claim_b)")
    D.add_rule(Rule(head="actionable(X)", body=("legal_claim(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_actionable"))
    D.add_rule(Rule(head="entitles_to_remedy(X)", body=("legal_claim(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_remedy"))
    gold_sol = Rule(head="~actionable(X)", body=("time_barred(X)",),
                    rule_type=RuleType.DEFEATER, label="d_statute_of_lim")
    distractors_sol = [
        Rule(head="~actionable(X)", body=("legal_claim(X)",),
             rule_type=RuleType.DEFEATER, label="d_sol_broad"),
        Rule(head="~entitles_to_remedy(X)", body=("time_barred(X)",),
             rule_type=RuleType.DEFEATER, label="d_sol_wrong_head"),
        Rule(head="dismissed(X)", body=("time_barred(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_sol_positive"),
        Rule(head="~actionable(X)", body=("dismissed(X)",),
             rule_type=RuleType.DEFEATER, label="d_sol_indirect"),
        Rule(head="~actionable(X)", body=("invalid(X)",),
             rule_type=RuleType.DEFEATER, label="d_sol_wrong_cond"),
    ]
    instances.append(_make_instance(
        name="statute_of_limitations", domain="legal",
        D_minus=D, anomaly="actionable(claim_a)",
        gold=gold_sol, beaten_labels=["r_actionable"],
        distractors=distractors_sol,
        preserved=["actionable(claim_b)", "entitles_to_remedy(claim_b)"],
        defeater_type="weak",
        description="A statute of limitations bars an otherwise valid legal claim "
                    "if filed outside the prescribed time window.",
    ))

    # ── Good faith purchaser: takes free of equitable interests ───────────
    D = Theory()
    D.add_fact("purchaser(gfp_alice)")
    D.add_fact("good_faith_purchaser(gfp_alice)")
    D.add_fact("purchaser(gfp_bob)")
    D.add_rule(Rule(head="takes_subject_to_prior_interests(X)", body=("purchaser(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_prior"))
    D.add_rule(Rule(head="bound_by_contract(X)", body=("purchaser(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_bound_p"))
    gold_gfp = Rule(head="~takes_subject_to_prior_interests(X)", body=("good_faith_purchaser(X)",),
                    rule_type=RuleType.DEFEATER, label="d_good_faith")
    distractors_gfp = [
        Rule(head="~takes_subject_to_prior_interests(X)", body=("purchaser(X)",),
             rule_type=RuleType.DEFEATER, label="d_gfp_broad"),
        Rule(head="~bound_by_contract(X)", body=("good_faith_purchaser(X)",),
             rule_type=RuleType.DEFEATER, label="d_gfp_wrong_head"),
        Rule(head="title_clear(X)", body=("good_faith_purchaser(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_gfp_positive"),
        Rule(head="~takes_subject_to_prior_interests(X)", body=("paid_value(X)",),
             rule_type=RuleType.DEFEATER, label="d_gfp_wrong_cond"),
        Rule(head="~takes_subject_to_prior_interests(X)", body=("registered(X)",),
             rule_type=RuleType.DEFEATER, label="d_gfp_irrelevant"),
    ]
    instances.append(_make_instance(
        name="good_faith_purchaser", domain="legal",
        D_minus=D, anomaly="takes_subject_to_prior_interests(gfp_alice)",
        gold=gold_gfp, beaten_labels=["r_prior"],
        distractors=distractors_gfp,
        preserved=["takes_subject_to_prior_interests(gfp_bob)", "bound_by_contract(gfp_alice)"],
        defeater_type="weak",
        description="A bona fide purchaser for value without notice takes title free "
                    "of prior equitable interests, defeating the default of subject-taking.",
    ))

    # ── Diplomatic immunity: diplomat not subject to local law ────────────
    D = Theory()
    D.add_fact("person(ambassador_jones)")
    D.add_fact("diplomat(ambassador_jones)")
    D.add_fact("person(citizen_smith)")
    D.add_rule(Rule(head="subject_to_local_law(X)", body=("person(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_local"))
    D.add_rule(Rule(head="taxable(X)", body=("person(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_tax"))
    gold_di = Rule(head="~subject_to_local_law(X)", body=("diplomat(X)",),
                   rule_type=RuleType.DEFEATER, label="d_diplomatic")
    distractors_di = [
        Rule(head="~subject_to_local_law(X)", body=("person(X)",),
             rule_type=RuleType.DEFEATER, label="d_di_broad"),
        Rule(head="~taxable(X)", body=("diplomat(X)",),
             rule_type=RuleType.DEFEATER, label="d_di_wrong_head"),
        Rule(head="immune(X)", body=("diplomat(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_di_positive"),
        Rule(head="~subject_to_local_law(X)", body=("foreign_national(X)",),
             rule_type=RuleType.DEFEATER, label="d_di_wrong_cond"),
        Rule(head="~subject_to_local_law(X)", body=("immune(X)",),
             rule_type=RuleType.DEFEATER, label="d_di_indirect"),
    ]
    instances.append(_make_instance(
        name="diplomatic_immunity", domain="legal",
        D_minus=D, anomaly="subject_to_local_law(ambassador_jones)",
        gold=gold_di, beaten_labels=["r_local"],
        distractors=distractors_di,
        preserved=["subject_to_local_law(citizen_smith)", "taxable(citizen_smith)"],
        defeater_type="weak",
        description="Accredited diplomats enjoy immunity from the jurisdiction of the "
                    "host state under the Vienna Convention, defeating the general default.",
    ))

    # ── Sovereign immunity: state not suable without consent ──────────────
    D = Theory()
    D.add_fact("entity(state_agency)")
    D.add_fact("sovereign(state_agency)")
    D.add_fact("entity(private_corp)")
    D.add_rule(Rule(head="suable(X)", body=("entity(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_suable"))
    D.add_rule(Rule(head="liable_for_damages(X)", body=("entity(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_liable"))
    gold_si = Rule(head="~suable(X)", body=("sovereign(X)",),
                   rule_type=RuleType.DEFEATER, label="d_sovereign")
    distractors_si = [
        Rule(head="~suable(X)", body=("entity(X)",),
             rule_type=RuleType.DEFEATER, label="d_si_broad"),
        Rule(head="~liable_for_damages(X)", body=("sovereign(X)",),
             rule_type=RuleType.DEFEATER, label="d_si_wrong_head"),
        Rule(head="immune_from_suit(X)", body=("sovereign(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_si_positive"),
        Rule(head="~suable(X)", body=("governmental(X)",),
             rule_type=RuleType.DEFEATER, label="d_si_wrong_cond"),
        Rule(head="~suable(X)", body=("non_profit(X)",),
             rule_type=RuleType.DEFEATER, label="d_si_irrelevant"),
    ]
    instances.append(_make_instance(
        name="sovereign_immunity", domain="legal",
        D_minus=D, anomaly="suable(state_agency)",
        gold=gold_si, beaten_labels=["r_suable"],
        distractors=distractors_si,
        preserved=["suable(private_corp)", "liable_for_damages(private_corp)"],
        defeater_type="weak",
        description="Sovereign immunity bars suits against a state without its consent, "
                    "overriding the default that all legal entities may be sued.",
    ))

    # ── Force majeure: excuses contractual non-performance ────────────────
    D = Theory()
    D.add_fact("contract(contract_x)")
    D.add_fact("force_majeure_event(contract_x)")
    D.add_fact("contract(contract_y)")
    D.add_rule(Rule(head="performance_required(X)", body=("contract(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_perform"))
    D.add_rule(Rule(head="breach_if_non_performance(X)", body=("contract(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_breach"))
    gold_fm = Rule(head="~performance_required(X)", body=("force_majeure_event(X)",),
                   rule_type=RuleType.DEFEATER, label="d_force_majeure")
    distractors_fm = [
        Rule(head="~performance_required(X)", body=("contract(X)",),
             rule_type=RuleType.DEFEATER, label="d_fm_broad"),
        Rule(head="~breach_if_non_performance(X)", body=("force_majeure_event(X)",),
             rule_type=RuleType.DEFEATER, label="d_fm_wrong_head"),
        Rule(head="excused(X)", body=("force_majeure_event(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_fm_positive"),
        Rule(head="~performance_required(X)", body=("frustrated(X)",),
             rule_type=RuleType.DEFEATER, label="d_fm_wrong_cond"),
        Rule(head="~performance_required(X)", body=("voided(X)",),
             rule_type=RuleType.DEFEATER, label="d_fm_irrelevant"),
    ]
    instances.append(_make_instance(
        name="force_majeure", domain="legal",
        D_minus=D, anomaly="performance_required(contract_x)",
        gold=gold_fm, beaten_labels=["r_perform"],
        distractors=distractors_fm,
        preserved=["performance_required(contract_y)", "breach_if_non_performance(contract_y)"],
        defeater_type="weak",
        description="A force majeure clause excuses non-performance when unforeseeable "
                    "events (war, natural disaster) make performance impossible.",
    ))

    # ── Qualified immunity: official shielded for good faith acts ─────────
    D = Theory()
    D.add_fact("official(officer_davis)")
    D.add_fact("qualified_immunity_claimant(officer_davis)")
    D.add_fact("official(officer_chen)")
    D.add_rule(Rule(head="civilly_liable(X)", body=("official(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_civil"))
    D.add_rule(Rule(head="subject_to_suit(X)", body=("official(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_suit"))
    gold_qi = Rule(head="~civilly_liable(X)", body=("qualified_immunity_claimant(X)",),
                   rule_type=RuleType.DEFEATER, label="d_qualified_immunity")
    distractors_qi = [
        Rule(head="~civilly_liable(X)", body=("official(X)",),
             rule_type=RuleType.DEFEATER, label="d_qi_broad"),
        Rule(head="~subject_to_suit(X)", body=("qualified_immunity_claimant(X)",),
             rule_type=RuleType.DEFEATER, label="d_qi_wrong_head"),
        Rule(head="immune_from_liability(X)", body=("qualified_immunity_claimant(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_qi_positive"),
        Rule(head="~civilly_liable(X)", body=("acting_in_good_faith(X)",),
             rule_type=RuleType.DEFEATER, label="d_qi_wrong_cond"),
        Rule(head="~civilly_liable(X)", body=("immune(X)",),
             rule_type=RuleType.DEFEATER, label="d_qi_indirect"),
    ]
    instances.append(_make_instance(
        name="qualified_immunity", domain="legal",
        D_minus=D, anomaly="civilly_liable(officer_davis)",
        gold=gold_qi, beaten_labels=["r_civil"],
        distractors=distractors_qi,
        preserved=["civilly_liable(officer_chen)", "subject_to_suit(officer_chen)"],
        defeater_type="weak",
        description="Qualified immunity shields government officials from civil liability "
                    "for actions taken in good faith within their official authority.",
    ))

    # ── Constitutional supremacy: state law void if conflicts ─────────────
    D = Theory()
    D.add_fact("law(state_law_x)")
    D.add_fact("conflicts_with_federal(state_law_x)")
    D.add_fact("law(state_law_y)")
    D.add_rule(Rule(head="enforceable(X)", body=("law(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_enforce"))
    D.add_rule(Rule(head="binding_on_citizens(X)", body=("law(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_binding"))
    gold_cs = Rule(head="~enforceable(X)", body=("conflicts_with_federal(X)",),
                   rule_type=RuleType.DEFEATER, label="d_supremacy")
    distractors_cs = [
        Rule(head="~enforceable(X)", body=("law(X)",),
             rule_type=RuleType.DEFEATER, label="d_cs_broad"),
        Rule(head="~binding_on_citizens(X)", body=("conflicts_with_federal(X)",),
             rule_type=RuleType.DEFEATER, label="d_cs_wrong_head"),
        Rule(head="preempted(X)", body=("conflicts_with_federal(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_cs_positive"),
        Rule(head="~enforceable(X)", body=("unconstitutional(X)",),
             rule_type=RuleType.DEFEATER, label="d_cs_wrong_cond"),
        Rule(head="~enforceable(X)", body=("preempted(X)",),
             rule_type=RuleType.DEFEATER, label="d_cs_indirect"),
    ]
    instances.append(_make_instance(
        name="constitutional_supremacy", domain="legal",
        D_minus=D, anomaly="enforceable(state_law_x)",
        gold=gold_cs, beaten_labels=["r_enforce"],
        distractors=distractors_cs,
        preserved=["enforceable(state_law_y)", "binding_on_citizens(state_law_y)"],
        defeater_type="weak",
        description="Under the Supremacy Clause, a state law that conflicts with federal "
                    "law is preempted and unenforceable, defeating the enforceability default.",
    ))

    # ── Ultra vires: act outside authority is void ────────────────────────
    D = Theory()
    D.add_fact("corporate_act(act_alpha)")
    D.add_fact("ultra_vires_act(act_alpha)")
    D.add_fact("corporate_act(act_beta)")
    D.add_rule(Rule(head="legally_valid(X)", body=("corporate_act(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_valid"))
    D.add_rule(Rule(head="binding_on_corporation(X)", body=("corporate_act(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_binding_c"))
    gold_uv = Rule(head="~legally_valid(X)", body=("ultra_vires_act(X)",),
                   rule_type=RuleType.DEFEATER, label="d_ultra_vires")
    distractors_uv = [
        Rule(head="~legally_valid(X)", body=("corporate_act(X)",),
             rule_type=RuleType.DEFEATER, label="d_uv_broad"),
        Rule(head="~binding_on_corporation(X)", body=("ultra_vires_act(X)",),
             rule_type=RuleType.DEFEATER, label="d_uv_wrong_head"),
        Rule(head="void_ab_initio(X)", body=("ultra_vires_act(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_uv_positive"),
        Rule(head="~legally_valid(X)", body=("unauthorized(X)",),
             rule_type=RuleType.DEFEATER, label="d_uv_wrong_cond"),
        Rule(head="~legally_valid(X)", body=("fraudulent(X)",),
             rule_type=RuleType.DEFEATER, label="d_uv_irrelevant"),
    ]
    instances.append(_make_instance(
        name="ultra_vires", domain="legal",
        D_minus=D, anomaly="legally_valid(act_alpha)",
        gold=gold_uv, beaten_labels=["r_valid"],
        distractors=distractors_uv,
        preserved=["legally_valid(act_beta)", "binding_on_corporation(act_beta)"],
        defeater_type="weak",
        description="An ultra vires act—one beyond a corporation's legal authority—is "
                    "void, defeating the default that corporate acts are legally valid.",
    ))

    # ── Laches: equitable defence for unreasonable delay (Nov > 0) ───────────
    # Laches bars an equity claim when the claimant has waited an unreasonably
    # long time and the delay prejudiced the defendant. The predicate
    # `laches_applies` is novel -- it does not appear in D^-.
    # Two-entity pattern: mansion_case has laches_applies (novel fact, D^full
    # only); park_case does not, so it retains valid_claim and remedy_available.
    D = Theory()
    D.add_fact("equity_claim(mansion_case)")
    D.add_fact("equity_claim(park_case)")
    D.add_rule(Rule(head="valid_claim(X)", body=("equity_claim(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_eq_valid"))
    D.add_rule(Rule(head="remedy_available(X)", body=("equity_claim(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_remedy"))
    gold_laches = Rule(head="~valid_claim(X)", body=("laches_applies(X)",),
                       rule_type=RuleType.DEFEATER, label="d_laches")
    distractors_laches = [
        Rule(head="~valid_claim(X)", body=("equity_claim(X)",),
             rule_type=RuleType.DEFEATER, label="d_laches_broad"),
        Rule(head="~remedy_available(X)", body=("laches_applies(X)",),
             rule_type=RuleType.DEFEATER, label="d_laches_wrong_head"),
        Rule(head="claim_dismissed(X)", body=("laches_applies(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_laches_positive"),
        Rule(head="~valid_claim(X)", body=("stale_claim(X)",),
             rule_type=RuleType.DEFEATER, label="d_laches_wrong_cond"),
        Rule(head="~valid_claim(X)", body=("unreasonable_delay(X)",),
             rule_type=RuleType.DEFEATER, label="d_laches_near_gold"),
    ]
    instances.append(_make_instance(
        name="laches", domain="legal",
        D_minus=D, anomaly="valid_claim(mansion_case)",
        gold=gold_laches, beaten_labels=["r_eq_valid"],
        distractors=distractors_laches,
        preserved=["valid_claim(park_case)", "remedy_available(park_case)"],
        defeater_type="weak",
        description="The equitable doctrine of laches bars a claim when the plaintiff "
                    "unreasonably delayed asserting it and the delay prejudiced the defendant, "
                    "defeating the equity court's default presumption that claims are valid.",
        novel_predicates=["laches_applies"],
        novel_facts=["laches_applies(mansion_case)"],
    ))

    return instances


# ─── Materials Science Instances ──────────────────────────────────────────────

def _materials_instances() -> List[dict]:
    instances = []
    print("\n[Materials]")

    # ── Metallic glass: not brittle despite being a metal (Nov > 0) ───────
    # Two-entity pattern: vitreloy is amorphous, steel_a is not.
    D = Theory()
    D.add_fact("material(vitreloy)")
    D.add_fact("metal(vitreloy)")
    D.add_fact("material(steel_a)")
    D.add_fact("metal(steel_a)")
    D.add_rule(Rule(head="brittle(X)", body=("metal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_brittle"))
    D.add_rule(Rule(head="conducts_electricity(X)", body=("metal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_conduct"))
    # Novel predicate 'amorphous_solid' NOT in D^-.
    gold_mg = Rule(head="~brittle(X)", body=("amorphous_solid(X)",),
                   rule_type=RuleType.DEFEATER, label="d_metallic_glass")
    distractors_mg = [
        Rule(head="~brittle(X)", body=("metal(X)",),
             rule_type=RuleType.DEFEATER, label="d_mg_broad"),
        Rule(head="~conducts_electricity(X)", body=("amorphous_solid(X)",),
             rule_type=RuleType.DEFEATER, label="d_mg_wrong_head"),
        Rule(head="~brittle(X)", body=("alloy(X)",),
             rule_type=RuleType.DEFEATER, label="d_mg_wrong_cond"),
        Rule(head="ductile(X)", body=("amorphous_solid(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_mg_positive"),
        Rule(head="~brittle(X)", body=("ceramic(X)",),
             rule_type=RuleType.DEFEATER, label="d_mg_irrelevant"),
    ]
    instances.append(_make_instance(
        name="metallic_glass", domain="materials",
        D_minus=D, anomaly="brittle(vitreloy)",
        gold=gold_mg, beaten_labels=["r_brittle"],
        distractors=distractors_mg,
        preserved=["brittle(steel_a)", "conducts_electricity(vitreloy)",
                   "conducts_electricity(steel_a)"],
        defeater_type="weak",
        description="Metallic glasses (e.g. Vitreloy) are amorphous solids that lack "
                    "crystalline structure, making them tough rather than brittle.",
        novel_predicates=["amorphous_solid"],
        novel_facts=["amorphous_solid(vitreloy)"],
    ))

    # ── Aerogel: extremely light solid ───────────────────────────────────
    D = Theory()
    D.add_fact("material(silica_aerogel)")
    D.add_fact("solid(silica_aerogel)")
    D.add_fact("material(concrete_block)")
    D.add_fact("solid(concrete_block)")
    D.add_rule(Rule(head="dense(X)", body=("solid(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_dense"))
    D.add_rule(Rule(head="rigid(X)", body=("solid(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_rigid"))
    gold_ag = Rule(head="~dense(X)", body=("aerogel(X)",),
                   rule_type=RuleType.DEFEATER, label="d_aerogel")
    D.add_fact("aerogel(silica_aerogel)")
    distractors_ag = [
        Rule(head="~dense(X)", body=("solid(X)",),
             rule_type=RuleType.DEFEATER, label="d_ag_broad"),
        Rule(head="~rigid(X)", body=("aerogel(X)",),
             rule_type=RuleType.DEFEATER, label="d_ag_wrong_head"),
        Rule(head="porous(X)", body=("aerogel(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_ag_positive"),
        Rule(head="~dense(X)", body=("foam(X)",),
             rule_type=RuleType.DEFEATER, label="d_ag_wrong_cond"),
        Rule(head="~dense(X)", body=("lightweight(X)",),
             rule_type=RuleType.DEFEATER, label="d_ag_irrelevant"),
    ]
    instances.append(_make_instance(
        name="aerogel", domain="materials",
        D_minus=D, anomaly="dense(silica_aerogel)",
        gold=gold_ag, beaten_labels=["r_dense"],
        distractors=distractors_ag,
        preserved=["dense(concrete_block)", "rigid(concrete_block)"],
        defeater_type="weak",
        description="Silica aerogels are among the least dense solid materials ever made, "
                    "composed mainly of air, defeating the solids-are-dense default.",
    ))

    # ── Superconductor: zero resistance below Tc (Nov > 0) ────────────────
    # Two-entity pattern: niobium is below Tc, warm_niobium is not.
    D = Theory()
    D.add_fact("material(niobium)")
    D.add_fact("metal(niobium)")
    D.add_fact("superconductor(niobium)")
    D.add_fact("material(warm_niobium)")
    D.add_fact("metal(warm_niobium)")
    D.add_fact("superconductor(warm_niobium)")
    D.add_fact("material(copper_wire)")
    D.add_fact("metal(copper_wire)")
    D.add_rule(Rule(head="has_electrical_resistance(X)", body=("metal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_resistance"))
    D.add_rule(Rule(head="conducts_electricity(X)", body=("metal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_conduct_s"))
    # Novel predicate 'below_critical_temperature' NOT in D^-.
    gold_sc = Rule(head="~has_electrical_resistance(X)", body=("below_critical_temperature(X)",),
                   rule_type=RuleType.DEFEATER, label="d_superconductor")
    distractors_sc = [
        Rule(head="~has_electrical_resistance(X)", body=("metal(X)",),
             rule_type=RuleType.DEFEATER, label="d_sc_broad"),
        Rule(head="~conducts_electricity(X)", body=("below_critical_temperature(X)",),
             rule_type=RuleType.DEFEATER, label="d_sc_wrong_head"),
        Rule(head="~has_electrical_resistance(X)", body=("superconductor(X)",),
             rule_type=RuleType.DEFEATER, label="d_sc_no_novel"),
        Rule(head="zero_resistance(X)", body=("below_critical_temperature(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_sc_positive"),
        Rule(head="~has_electrical_resistance(X)", body=("ceramic(X)",),
             rule_type=RuleType.DEFEATER, label="d_sc_wrong_cond"),
    ]
    instances.append(_make_instance(
        name="superconductor", domain="materials",
        D_minus=D, anomaly="has_electrical_resistance(niobium)",
        gold=gold_sc, beaten_labels=["r_resistance"],
        distractors=distractors_sc,
        preserved=["has_electrical_resistance(warm_niobium)",
                   "has_electrical_resistance(copper_wire)",
                   "conducts_electricity(copper_wire)", "conducts_electricity(niobium)"],
        defeater_type="weak",
        description="Below their critical temperature Tc, superconductors exhibit zero "
                    "electrical resistance. The same material above Tc still has resistance.",
        novel_predicates=["below_critical_temperature"],
        novel_facts=["below_critical_temperature(niobium)"],
    ))

    # ── Graphene: transparent single-layer carbon (Nov > 0) ───────────────
    # Two-entity pattern: graphene_sheet has monolayer_thickness, thick_graphene does not.
    D = Theory()
    D.add_fact("material(graphene_sheet)")
    D.add_fact("carbon_material(graphene_sheet)")
    D.add_fact("material(thick_graphene)")
    D.add_fact("carbon_material(thick_graphene)")
    D.add_fact("material(graphite_block)")
    D.add_fact("carbon_material(graphite_block)")
    D.add_rule(Rule(head="opaque(X)", body=("carbon_material(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_opaque"))
    D.add_rule(Rule(head="electrically_conductive(X)", body=("carbon_material(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_cond_g"))
    # Novel predicate 'monolayer_thickness' NOT in D^-.
    gold_gr = Rule(head="~opaque(X)", body=("monolayer_thickness(X)",),
                   rule_type=RuleType.DEFEATER, label="d_graphene")
    distractors_gr = [
        Rule(head="~opaque(X)", body=("carbon_material(X)",),
             rule_type=RuleType.DEFEATER, label="d_gr_broad"),
        Rule(head="~electrically_conductive(X)", body=("monolayer_thickness(X)",),
             rule_type=RuleType.DEFEATER, label="d_gr_wrong_head"),
        Rule(head="~opaque(X)", body=("graphene_sheet(X)",),
             rule_type=RuleType.DEFEATER, label="d_gr_wrong_cond"),
        Rule(head="transparent(X)", body=("monolayer_thickness(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_gr_positive"),
        Rule(head="~opaque(X)", body=("thin_film(X)",),
             rule_type=RuleType.DEFEATER, label="d_gr_irrelevant"),
    ]
    instances.append(_make_instance(
        name="graphene", domain="materials",
        D_minus=D, anomaly="opaque(graphene_sheet)",
        gold=gold_gr, beaten_labels=["r_opaque"],
        distractors=distractors_gr,
        preserved=["opaque(thick_graphene)", "opaque(graphite_block)",
                   "electrically_conductive(graphite_block)",
                   "electrically_conductive(graphene_sheet)"],
        defeater_type="weak",
        description="Single-layer graphene transmits ~97.7% of light because of its "
                    "monolayer thickness; multilayer graphene remains opaque.",
        novel_predicates=["monolayer_thickness"],
        novel_facts=["monolayer_thickness(graphene_sheet)"],
    ))

    # ── Shape memory alloy: recovers deformed shape (Nov > 0) ─────────────
    # Two-entity pattern: nitinol has thermoelastic_martensite, nitinol_annealed does not.
    D = Theory()
    D.add_fact("material(nitinol)")
    D.add_fact("alloy(nitinol)")
    D.add_fact("material(nitinol_annealed)")
    D.add_fact("alloy(nitinol_annealed)")
    D.add_fact("material(aluminum_alloy)")
    D.add_fact("alloy(aluminum_alloy)")
    D.add_rule(Rule(head="permanently_deformed_when_bent(X)", body=("alloy(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_deform"))
    D.add_rule(Rule(head="conducts_electricity(X)", body=("alloy(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_cond_a"))
    # Novel predicate 'thermoelastic_martensite' NOT in D^-.
    gold_sma = Rule(head="~permanently_deformed_when_bent(X)", body=("thermoelastic_martensite(X)",),
                    rule_type=RuleType.DEFEATER, label="d_nitinol")
    distractors_sma = [
        Rule(head="~permanently_deformed_when_bent(X)", body=("alloy(X)",),
             rule_type=RuleType.DEFEATER, label="d_sma_broad"),
        Rule(head="~conducts_electricity(X)", body=("thermoelastic_martensite(X)",),
             rule_type=RuleType.DEFEATER, label="d_sma_wrong_head"),
        Rule(head="~permanently_deformed_when_bent(X)", body=("nitinol(X)",),
             rule_type=RuleType.DEFEATER, label="d_sma_no_novel"),
        Rule(head="recovers_shape(X)", body=("thermoelastic_martensite(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_sma_positive"),
        Rule(head="~permanently_deformed_when_bent(X)", body=("elastic(X)",),
             rule_type=RuleType.DEFEATER, label="d_sma_wrong_cond"),
    ]
    instances.append(_make_instance(
        name="nitinol_sma", domain="materials",
        D_minus=D, anomaly="permanently_deformed_when_bent(nitinol)",
        gold=gold_sma, beaten_labels=["r_deform"],
        distractors=distractors_sma,
        preserved=["permanently_deformed_when_bent(nitinol_annealed)",
                   "permanently_deformed_when_bent(aluminum_alloy)",
                   "conducts_electricity(aluminum_alloy)", "conducts_electricity(nitinol)"],
        defeater_type="weak",
        description="NiTi alloy in its thermoelastic martensite phase recovers its "
                    "original shape when heated; annealed NiTi deforms permanently.",
        novel_predicates=["thermoelastic_martensite"],
        novel_facts=["thermoelastic_martensite(nitinol)"],
    ))

    # ── Piezoelectric: generates current under pressure ───────────────────
    D = Theory()
    D.add_fact("material(quartz_crystal)")
    D.add_fact("crystal(quartz_crystal)")
    D.add_fact("piezoelectric(quartz_crystal)")
    D.add_fact("material(table_salt)")
    D.add_fact("crystal(table_salt)")
    D.add_rule(Rule(head="electrically_passive(X)", body=("crystal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_passive"))
    D.add_rule(Rule(head="rigid(X)", body=("crystal(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_rigid_p"))
    gold_pz = Rule(head="~electrically_passive(X)", body=("piezoelectric(X)",),
                   rule_type=RuleType.DEFEATER, label="d_piezoelectric")
    distractors_pz = [
        Rule(head="~electrically_passive(X)", body=("crystal(X)",),
             rule_type=RuleType.DEFEATER, label="d_pz_broad"),
        Rule(head="~rigid(X)", body=("piezoelectric(X)",),
             rule_type=RuleType.DEFEATER, label="d_pz_wrong_head"),
        Rule(head="voltage_generating(X)", body=("piezoelectric(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_pz_positive"),
        Rule(head="~electrically_passive(X)", body=("semiconductor(X)",),
             rule_type=RuleType.DEFEATER, label="d_pz_wrong_cond"),
        Rule(head="~electrically_passive(X)", body=("charged(X)",),
             rule_type=RuleType.DEFEATER, label="d_pz_irrelevant"),
    ]
    instances.append(_make_instance(
        name="piezoelectric", domain="materials",
        D_minus=D, anomaly="electrically_passive(quartz_crystal)",
        gold=gold_pz, beaten_labels=["r_passive"],
        distractors=distractors_pz,
        preserved=["electrically_passive(table_salt)", "rigid(table_salt)",
                   "rigid(quartz_crystal)"],
        defeater_type="weak",
        description="Piezoelectric crystals like quartz generate electrical charge under "
                    "mechanical stress, defeating the default passivity of crystals.",
    ))

    # ── Thermoelectric: converts heat to electricity ───────────────────────
    D = Theory()
    D.add_fact("material(bismuth_telluride)")
    D.add_fact("semiconductor(bismuth_telluride)")
    D.add_fact("thermoelectric(bismuth_telluride)")
    D.add_fact("material(silicon_chip)")
    D.add_fact("semiconductor(silicon_chip)")
    D.add_rule(Rule(head="thermally_passive(X)", body=("semiconductor(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_therm_pass"))
    D.add_rule(Rule(head="band_gap(X)", body=("semiconductor(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_bandgap"))
    gold_te = Rule(head="~thermally_passive(X)", body=("thermoelectric(X)",),
                   rule_type=RuleType.DEFEATER, label="d_thermoelectric")
    distractors_te = [
        Rule(head="~thermally_passive(X)", body=("semiconductor(X)",),
             rule_type=RuleType.DEFEATER, label="d_te_broad"),
        Rule(head="~band_gap(X)", body=("thermoelectric(X)",),
             rule_type=RuleType.DEFEATER, label="d_te_wrong_head"),
        Rule(head="seebeck_effect(X)", body=("thermoelectric(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_te_positive"),
        Rule(head="~thermally_passive(X)", body=("conductor(X)",),
             rule_type=RuleType.DEFEATER, label="d_te_wrong_cond"),
        Rule(head="~thermally_passive(X)", body=("doped(X)",),
             rule_type=RuleType.DEFEATER, label="d_te_irrelevant"),
    ]
    instances.append(_make_instance(
        name="thermoelectric", domain="materials",
        D_minus=D, anomaly="thermally_passive(bismuth_telluride)",
        gold=gold_te, beaten_labels=["r_therm_pass"],
        distractors=distractors_te,
        preserved=["thermally_passive(silicon_chip)", "band_gap(silicon_chip)",
                   "band_gap(bismuth_telluride)"],
        defeater_type="weak",
        description="Thermoelectric materials convert a temperature gradient directly "
                    "into electrical voltage via the Seebeck effect.",
    ))

    # ── Superhydrophobic: extreme water repellency ─────────────────────────
    D = Theory()
    D.add_fact("material(lotus_coating)")
    D.add_fact("polymer(lotus_coating)")
    D.add_fact("superhydrophobic(lotus_coating)")
    D.add_fact("material(polyethylene_film)")
    D.add_fact("polymer(polyethylene_film)")
    D.add_rule(Rule(head="wetted_by_water(X)", body=("polymer(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_wet"))
    D.add_rule(Rule(head="flexible(X)", body=("polymer(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_flex"))
    gold_sh = Rule(head="~wetted_by_water(X)", body=("superhydrophobic(X)",),
                   rule_type=RuleType.DEFEATER, label="d_superhydrophobic")
    distractors_sh = [
        Rule(head="~wetted_by_water(X)", body=("polymer(X)",),
             rule_type=RuleType.DEFEATER, label="d_sh_broad"),
        Rule(head="~flexible(X)", body=("superhydrophobic(X)",),
             rule_type=RuleType.DEFEATER, label="d_sh_wrong_head"),
        Rule(head="water_repellent(X)", body=("superhydrophobic(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_sh_positive"),
        Rule(head="~wetted_by_water(X)", body=("waxed(X)",),
             rule_type=RuleType.DEFEATER, label="d_sh_wrong_cond"),
        Rule(head="~wetted_by_water(X)", body=("coated(X)",),
             rule_type=RuleType.DEFEATER, label="d_sh_irrelevant"),
    ]
    instances.append(_make_instance(
        name="superhydrophobic", domain="materials",
        D_minus=D, anomaly="wetted_by_water(lotus_coating)",
        gold=gold_sh, beaten_labels=["r_wet"],
        distractors=distractors_sh,
        preserved=["wetted_by_water(polyethylene_film)", "flexible(polyethylene_film)",
                   "flexible(lotus_coating)"],
        defeater_type="weak",
        description="Superhydrophobic surfaces (contact angle > 150°) repel water "
                    "completely, defeating the default wettability of polymers.",
    ))

    # ── Metamaterial: negative refractive index ───────────────────────────
    D = Theory()
    D.add_fact("material(split_ring_resonator)")
    D.add_fact("composite(split_ring_resonator)")
    D.add_fact("metamaterial(split_ring_resonator)")
    D.add_fact("material(carbon_fiber_plate)")
    D.add_fact("composite(carbon_fiber_plate)")
    D.add_rule(Rule(head="positive_refractive_index(X)", body=("composite(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_pos_ref"))
    D.add_rule(Rule(head="absorbs_electromagnetic(X)", body=("composite(X)",),
                    rule_type=RuleType.DEFEASIBLE, label="r_absorb"))
    gold_mm = Rule(head="~positive_refractive_index(X)", body=("metamaterial(X)",),
                   rule_type=RuleType.DEFEATER, label="d_metamaterial")
    distractors_mm = [
        Rule(head="~positive_refractive_index(X)", body=("composite(X)",),
             rule_type=RuleType.DEFEATER, label="d_mm_broad"),
        Rule(head="~absorbs_electromagnetic(X)", body=("metamaterial(X)",),
             rule_type=RuleType.DEFEATER, label="d_mm_wrong_head"),
        Rule(head="negative_refraction(X)", body=("metamaterial(X)",),
             rule_type=RuleType.DEFEASIBLE, label="d_mm_positive"),
        Rule(head="~positive_refractive_index(X)", body=("engineered_structure(X)",),
             rule_type=RuleType.DEFEATER, label="d_mm_wrong_cond"),
        Rule(head="~positive_refractive_index(X)", body=("periodic_structure(X)",),
             rule_type=RuleType.DEFEATER, label="d_mm_irrelevant"),
    ]
    instances.append(_make_instance(
        name="metamaterial", domain="materials",
        D_minus=D, anomaly="positive_refractive_index(split_ring_resonator)",
        gold=gold_mm, beaten_labels=["r_pos_ref"],
        distractors=distractors_mm,
        preserved=["positive_refractive_index(carbon_fiber_plate)",
                   "absorbs_electromagnetic(carbon_fiber_plate)"],
        defeater_type="weak",
        description="Electromagnetic metamaterials can exhibit negative refractive indices "
                    "through engineered subwavelength structures, defeating the natural default.",
    ))

    return instances


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Phase 2B: Manual Level 3 Instance Generation")
    print("=" * 70)

    all_instances = []
    all_instances.extend(_bio_instances())
    all_instances.extend(_legal_instances())
    all_instances.extend(_materials_instances())

    # Summary
    total = len(all_instances)
    valid = sum(1 for i in all_instances if i["valid"])
    nov_pos = sum(1 for i in all_instances if i["nov"] > 0)
    by_domain = {}
    for inst in all_instances:
        d = inst["domain"]
        by_domain[d] = by_domain.get(d, {"total": 0, "valid": 0})
        by_domain[d]["total"] += 1
        by_domain[d]["valid"] += int(inst["valid"])

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total instances:    {total}")
    print(f"Valid:              {valid}/{total}")
    print(f"Nov > 0:            {nov_pos}")
    for domain, stats in by_domain.items():
        print(f"  {domain:<12}: {stats['valid']}/{stats['total']}")

    # Save
    output = Path(__file__).parent.parent / "instances" / "level3_instances.json"
    output.parent.mkdir(exist_ok=True)

    dataset = {
        "metadata": {
            "name": "DeFAb Level 3 Instances v1.0",
            "generated": "2026-02-18",
            "total": total,
            "valid": valid,
            "nov_positive": nov_pos,
            "domains": {d: s["total"] for d, s in by_domain.items()},
        },
        "instances": all_instances,
    }

    with open(output, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\nSaved to: {output}")
    return dataset


if __name__ == "__main__":
    main()
