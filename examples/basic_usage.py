"""
Basic usage examples for BLANC knowledge base query API.

This file demonstrates the unified API for querying different knowledge
base systems.
"""

from blanc import KnowledgeBase, Query
from blanc.core.theory import Rule, RuleType, Theory


def example_theory_construction():
    """Example: Constructing a theory programmatically."""
    print("=" * 60)
    print("Example 1: Theory Construction")
    print("=" * 60)

    theory = Theory()

    # Add facts
    theory.add_fact("bird(tweety)")
    theory.add_fact("penguin(opus)")

    # Add defeasible rules
    r1 = Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    )

    r2 = Rule(
        head="not_flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r2",
    )

    theory.add_rule(r1)
    theory.add_rule(r2)

    # Penguin rule defeats bird rule
    theory.add_superiority("r2", "r1")

    print("\nTheory in defeasible logic format:")
    print(theory.to_defeasible())

    print("\nTheory in Prolog format:")
    print(theory.to_prolog())

    return theory


def example_medical_diagnosis():
    """Example: Medical diagnosis with defeasible rules."""
    print("\n" + "=" * 60)
    print("Example 2: Medical Diagnosis Theory")
    print("=" * 60)

    theory = Theory()

    # Patient symptoms
    theory.add_fact("symptom(patient1, fever)")
    theory.add_fact("symptom(patient1, cough)")
    theory.add_fact("symptom(patient1, fatigue)")

    # Diagnostic rules
    flu = Rule(
        head="diagnosis(P, flu)",
        body=("symptom(P, fever)", "symptom(P, cough)"),
        rule_type=RuleType.DEFEASIBLE,
        label="flu_rule",
    )

    covid = Rule(
        head="diagnosis(P, covid)",
        body=("symptom(P, fever)", "symptom(P, cough)", "symptom(P, fatigue)"),
        rule_type=RuleType.DEFEASIBLE,
        label="covid_rule",
    )

    theory.add_rule(flu)
    theory.add_rule(covid)

    # More specific diagnosis (COVID with more symptoms) takes precedence
    theory.add_superiority("covid_rule", "flu_rule")

    print("\nMedical knowledge base:")
    print(theory.to_defeasible())

    return theory


def example_query_construction():
    """Example: Constructing different types of queries."""
    print("\n" + "=" * 60)
    print("Example 3: Query Construction (Syntax Demo)")
    print("=" * 60)

    # Note: These queries won't execute without a backend implementation
    # This demonstrates the API syntax

    # Placeholder KB (would normally be initialized with backend)
    kb = None

    print("\n1. Deductive Query:")
    print("   Query(kb).select('diagnosis(Patient, Disease)')")
    print("            .where('symptom(Patient, fever)')")
    print("            .execute()")

    print("\n2. Abductive Query:")
    print("   Query(kb).abduce('infected(john, covid)')")
    print("            .given('symptom(john, fever)', 'symptom(john, cough)')")
    print("            .minimize('hypothesis_count')")
    print("            .execute()")

    print("\n3. Defeasible Query:")
    print("   Query(kb).defeasibly_infer('flies(tweety)')")
    print("            .with_defeaters('wounded(tweety)')")
    print("            .execute()")


def example_intrinsically_disordered_proteins():
    """
    Example: IDP discovery scenario from paper.

    Models the discovery of intrinsically disordered proteins,
    which contradicted the structure-function dogma.
    """
    print("\n" + "=" * 60)
    print("Example 4: IDP Discovery (From Paper)")
    print("=" * 60)

    theory = Theory()

    # Traditional structure-function dogma (defeasible rule)
    dogma = Rule(
        head="functional(P)",
        body=("protein(P)", "has_structure(P)"),
        rule_type=RuleType.DEFEASIBLE,
        label="structure_function_dogma",
    )

    # Facts about a specific protein
    theory.add_fact("protein(alpha_synuclein)")
    theory.add_fact("lacks_fixed_structure(alpha_synuclein)")
    theory.add_fact("functionally_active(alpha_synuclein)")

    theory.add_rule(dogma)

    # The discovery: a defeater showing structure isn't always required
    idp_exception = Rule(
        head="functional(P)",
        body=("protein(P)", "intrinsically_disordered(P)"),
        rule_type=RuleType.DEFEASIBLE,
        label="idp_functional",
    )

    # Classification rule
    idp_def = Rule(
        head="intrinsically_disordered(P)",
        body=("lacks_fixed_structure(P)", "functionally_active(P)"),
        rule_type=RuleType.STRICT,
    )

    theory.add_rule(idp_exception)
    theory.add_rule(idp_def)

    # IDP exception defeats the dogma
    theory.add_superiority("idp_functional", "structure_function_dogma")

    print("\nKnowledge base modeling IDP discovery:")
    print(theory.to_defeasible())

    print("\nThis demonstrates how defeasible logic can model")
    print("transformational scientific discoveries that contradict")
    print("previous defaults without discarding useful generalizations.")


def example_rule_types():
    """Example: Different rule types in defeasible logic."""
    print("\n" + "=" * 60)
    print("Example 5: Rule Types")
    print("=" * 60)

    theory = Theory()

    # FACT: Ground truth
    theory.add_fact("animal(tweety)")

    # STRICT rule: Always holds (->)
    strict = Rule(
        head="mortal(X)",
        body=("animal(X)",),
        rule_type=RuleType.STRICT,
    )

    # DEFEASIBLE rule: Usually holds but can be defeated (=>)
    defeasible = Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    )

    # DEFEATER: Blocks inference without proving opposite (~>)
    defeater = Rule(
        head="not_flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="r2",
    )

    theory.add_rule(strict)
    theory.add_rule(defeasible)
    theory.add_rule(defeater)

    print("\nRule type demonstrations:")
    print(f"\nFact:       {list(theory.facts)[0]}")
    print(f"Strict:     {strict.to_defeasible()}")
    print(f"Defeasible: {defeasible.to_defeasible()}")
    print(f"Defeater:   {defeater.to_defeasible()}")

    print("\nExplanation:")
    print("- Facts are ground truth")
    print("- Strict rules (->) are classical implications")
    print("- Defeasible rules (=>) can be defeated by exceptions")
    print("- Defeaters (~>) block inferences without asserting the opposite")


if __name__ == "__main__":
    example_theory_construction()
    example_medical_diagnosis()
    example_query_construction()
    example_intrinsically_disordered_proteins()
    example_rule_types()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nNote: Query execution requires backend implementation (Phase 2)")
    print("Current phase demonstrates API design and theory representation.")
