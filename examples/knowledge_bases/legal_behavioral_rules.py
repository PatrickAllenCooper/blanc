"""
Legal Behavioral Rules -- Defeasible Defaults and Defeaters

Defeasible rules encoding legal defaults and their known exceptions,
grounded in the LKIF Core ontology concepts.  Legal reasoning is
inherently defeasible: general rules admit exceptions for jurisdiction,
capacity, immunity, and procedural requirements.

Author: Patrick Cooper
"""

from blanc.core.theory import Theory, Rule, RuleType


def _r(theory: Theory, rid: int, head: str, body: tuple,
       rtype: RuleType = RuleType.DEFEASIBLE) -> int:
    theory.add_rule(Rule(
        head=head, body=body, rule_type=rtype,
        label=f"legal_r{rid}",
    ))
    return rid + 1


def add_legal_behavioral_rules(theory: Theory) -> Theory:
    """Add defeasible legal rules and defeaters to a legal KB."""

    rid = 2000

    # ── Capacity defaults ────────────────────────────────────────

    rid = _r(theory, rid, "has_legal_capacity(X)", ("adult(X)",))
    rid = _r(theory, rid, "can_enter_contract(X)", ("has_legal_capacity(X)",))
    rid = _r(theory, rid, "can_vote(X)", ("adult_citizen(X)",))
    rid = _r(theory, rid, "can_testify(X)", ("person(X)",))
    rid = _r(theory, rid, "can_sue(X)", ("legal_person(X)",))
    rid = _r(theory, rid, "can_be_sued(X)", ("legal_person(X)",))
    rid = _r(theory, rid, "can_own_property(X)", ("legal_person(X)",))
    rid = _r(theory, rid, "can_hold_office(X)", ("adult_citizen(X)",))
    rid = _r(theory, rid, "can_marry(X)", ("adult(X)",))
    rid = _r(theory, rid, "can_consent(X)", ("adult(X)",))
    rid = _r(theory, rid, "can_serve_jury(X)", ("adult_citizen(X)",))
    rid = _r(theory, rid, "has_standing(X)", ("injured_party(X)",))

    # ── Capacity defeaters ───────────────────────────────────────

    rid = _r(theory, rid, "~has_legal_capacity(X)", ("minor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_legal_capacity(X)", ("mentally_incapacitated(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_enter_contract(X)", ("minor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_enter_contract(X)", ("intoxicated_person(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_vote(X)", ("disenfranchised_felon(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_vote(X)", ("non_citizen(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_testify(X)", ("incompetent_witness(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_testify(X)", ("privileged_spouse(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_hold_office(X)", ("convicted_felon(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_marry(X)", ("already_married(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_serve_jury(X)", ("lawyer(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_consent(X)", ("coerced_person(X)",), RuleType.DEFEATER)

    # ── Emancipated-minor override (defeater of a defeater) ──────

    rid = _r(theory, rid, "has_legal_capacity(X)", ("emancipated_minor(X)",))
    rid = _r(theory, rid, "can_enter_contract(X)", ("emancipated_minor(X)",))

    # ── Liability defaults ───────────────────────────────────────

    rid = _r(theory, rid, "is_liable(X)", ("tortfeasor(X)",))
    rid = _r(theory, rid, "is_liable(X)", ("breaching_party(X)",))
    rid = _r(theory, rid, "is_liable(X)", ("employer_of_tortfeasor(X)",))
    rid = _r(theory, rid, "is_criminally_liable(X)", ("perpetrator(X)",))
    rid = _r(theory, rid, "owes_duty_of_care(X)", ("professional(X)",))
    rid = _r(theory, rid, "owes_fiduciary_duty(X)", ("trustee(X)",))
    rid = _r(theory, rid, "owes_fiduciary_duty(X)", ("corporate_officer(X)",))
    rid = _r(theory, rid, "strictly_liable(X)", ("product_manufacturer(X)",))

    # ── Liability defeaters ──────────────────────────────────────

    rid = _r(theory, rid, "~is_liable(X)", ("diplomat(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_liable(X)", ("sovereign(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_liable(X)", ("acting_in_self_defense(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_liable(X)", ("force_majeure_event(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_criminally_liable(X)", ("insanity_defense(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_criminally_liable(X)", ("minor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~strictly_liable(X)", ("government_contractor(X)",), RuleType.DEFEATER)

    # ── Procedural defaults ──────────────────────────────────────

    rid = _r(theory, rid, "presumed_innocent(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "bears_burden_of_proof(X)", ("plaintiff(X)",))
    rid = _r(theory, rid, "bears_burden_of_proof(X)", ("prosecution(X)",))
    rid = _r(theory, rid, "has_right_to_counsel(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "has_right_to_appeal(X)", ("losing_party(X)",))
    rid = _r(theory, rid, "has_right_to_jury(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "entitled_to_due_process(X)", ("person(X)",))
    rid = _r(theory, rid, "bound_by_precedent(X)", ("lower_court(X)",))
    rid = _r(theory, rid, "bound_by_statute(X)", ("court(X)",))
    rid = _r(theory, rid, "admissible_as_evidence(X)", ("relevant_evidence(X)",))
    rid = _r(theory, rid, "statute_of_limitations_applies(X)", ("civil_claim(X)",))
    rid = _r(theory, rid, "statute_of_limitations_applies(X)", ("criminal_charge(X)",))

    # ── Procedural defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~presumed_innocent(X)", ("civil_defendant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~bears_burden_of_proof(X)", ("defendant_in_strict_liability(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~bound_by_precedent(X)", ("supreme_court(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_right_to_jury(X)", ("petty_offense_defendant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~admissible_as_evidence(X)", ("hearsay_evidence(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~admissible_as_evidence(X)", ("illegally_obtained_evidence(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~statute_of_limitations_applies(X)", ("murder_charge(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~statute_of_limitations_applies(X)", ("fraud_concealment(X)",), RuleType.DEFEATER)

    # ── Property defaults ────────────────────────────────────────

    rid = _r(theory, rid, "transferable(X)", ("property_right(X)",))
    rid = _r(theory, rid, "inheritable(X)", ("property_right(X)",))
    rid = _r(theory, rid, "enforceable(X)", ("valid_contract(X)",))
    rid = _r(theory, rid, "binding(X)", ("valid_contract(X)",))
    rid = _r(theory, rid, "revocable(X)", ("license(X)",))
    rid = _r(theory, rid, "renewable(X)", ("lease(X)",))
    rid = _r(theory, rid, "exclusive(X)", ("patent(X)",))
    rid = _r(theory, rid, "exclusive(X)", ("copyright(X)",))

    # ── Property defeaters ───────────────────────────────────────

    rid = _r(theory, rid, "~transferable(X)", ("personal_right(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~transferable(X)", ("government_license(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~enforceable(X)", ("unconscionable_contract(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~enforceable(X)", ("illegal_contract(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~binding(X)", ("contract_under_duress(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~revocable(X)", ("irrevocable_license(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~exclusive(X)", ("compulsory_license(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~exclusive(X)", ("fair_use(X)",), RuleType.DEFEATER)

    # ── Normative defaults ───────────────────────────────────────

    rid = _r(theory, rid, "obligated_to_pay_taxes(X)", ("citizen(X)",))
    rid = _r(theory, rid, "obligated_to_obey_law(X)", ("person(X)",))
    rid = _r(theory, rid, "permitted_to_travel(X)", ("citizen(X)",))
    rid = _r(theory, rid, "prohibited_from_discrimination(X)", ("employer(X)",))
    rid = _r(theory, rid, "obligated_to_disclose(X)", ("fiduciary(X)",))
    rid = _r(theory, rid, "obligated_to_mitigate(X)", ("injured_party(X)",))

    # ── Normative defeaters ──────────────────────────────────────

    rid = _r(theory, rid, "~obligated_to_pay_taxes(X)", ("tax_exempt_entity(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~permitted_to_travel(X)", ("parolee(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~permitted_to_travel(X)", ("person_under_travel_ban(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~prohibited_from_discrimination(X)", ("religious_organization(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~obligated_to_disclose(X)", ("attorney_client_privilege(X)",), RuleType.DEFEATER)

    # ── Constitutional law defaults ──────────────────────────────

    rid = _r(theory, rid, "has_free_speech(X)", ("citizen(X)",))
    rid = _r(theory, rid, "has_assembly_right(X)", ("citizen(X)",))
    rid = _r(theory, rid, "has_privacy_right(X)", ("person(X)",))
    rid = _r(theory, rid, "protected_from_search(X)", ("person(X)",))
    rid = _r(theory, rid, "has_religious_freedom(X)", ("person(X)",))
    rid = _r(theory, rid, "has_due_process_right(X)", ("person(X)",))
    rid = _r(theory, rid, "has_equal_protection(X)", ("person(X)",))
    rid = _r(theory, rid, "has_right_to_bear_arms(X)", ("citizen(X)",))
    rid = _r(theory, rid, "protected_from_self_incrimination(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "has_petition_right(X)", ("citizen(X)",))

    # ── Constitutional defeaters ─────────────────────────────────

    rid = _r(theory, rid, "~has_free_speech(X)", ("inciting_imminent_violence(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_free_speech(X)", ("making_true_threat(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_assembly_right(X)", ("unlawful_assembly(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~protected_from_search(X)", ("exigent_circumstances(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~protected_from_search(X)", ("plain_view_doctrine(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_right_to_bear_arms(X)", ("convicted_felon(X)",), RuleType.DEFEATER)

    # ── Criminal law defaults ────────────────────────────────────

    rid = _r(theory, rid, "requires_mens_rea(X)", ("criminal_offense(X)",))
    rid = _r(theory, rid, "requires_actus_reus(X)", ("criminal_offense(X)",))
    rid = _r(theory, rid, "requires_proof_beyond_reasonable_doubt(X)", ("criminal_charge(X)",))
    rid = _r(theory, rid, "allows_plea_bargain(X)", ("criminal_charge(X)",))
    rid = _r(theory, rid, "requires_unanimous_verdict(X)", ("felony_trial(X)",))
    rid = _r(theory, rid, "has_right_to_speedy_trial(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "eligible_for_parole(X)", ("convicted_prisoner(X)",))
    rid = _r(theory, rid, "eligible_for_bail(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "has_right_to_confront_witnesses(X)", ("criminal_defendant(X)",))
    rid = _r(theory, rid, "protected_from_double_jeopardy(X)", ("acquitted_defendant(X)",))

    # ── Criminal defeaters ───────────────────────────────────────

    rid = _r(theory, rid, "~requires_mens_rea(X)", ("strict_liability_offense(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~allows_plea_bargain(X)", ("capital_offense(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~requires_unanimous_verdict(X)", ("misdemeanor_trial(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~eligible_for_parole(X)", ("life_without_parole(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~eligible_for_bail(X)", ("capital_murder_charge(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~eligible_for_bail(X)", ("flight_risk(X)",), RuleType.DEFEATER)

    # ── Corporate law defaults ───────────────────────────────────

    rid = _r(theory, rid, "has_limited_liability(X)", ("corporation(X)",))
    rid = _r(theory, rid, "has_limited_liability(X)", ("llc(X)",))
    rid = _r(theory, rid, "must_file_annual_reports(X)", ("corporation(X)",))
    rid = _r(theory, rid, "has_board_of_directors(X)", ("corporation(X)",))
    rid = _r(theory, rid, "can_issue_shares(X)", ("corporation(X)",))
    rid = _r(theory, rid, "must_hold_annual_meeting(X)", ("corporation(X)",))
    rid = _r(theory, rid, "has_fiduciary_duty_to_shareholders(X)", ("corporate_officer(X)",))
    rid = _r(theory, rid, "subject_to_audit(X)", ("public_company(X)",))

    # ── Corporate defeaters ──────────────────────────────────────

    rid = _r(theory, rid, "~has_limited_liability(X)", ("pierced_corporate_veil(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_limited_liability(X)", ("general_partnership(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~must_file_annual_reports(X)", ("sole_proprietorship(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~subject_to_audit(X)", ("private_company(X)",), RuleType.DEFEATER)

    # ── Family law defaults ──────────────────────────────────────

    rid = _r(theory, rid, "has_custody_right(X)", ("biological_parent(X)",))
    rid = _r(theory, rid, "owes_child_support(X)", ("non_custodial_parent(X)",))
    rid = _r(theory, rid, "has_visitation_right(X)", ("non_custodial_parent(X)",))
    rid = _r(theory, rid, "can_adopt(X)", ("adult(X)",))
    rid = _r(theory, rid, "entitled_to_spousal_support(X)", ("dependent_spouse(X)",))
    rid = _r(theory, rid, "has_parental_authority(X)", ("legal_guardian(X)",))
    rid = _r(theory, rid, "has_inheritance_right(X)", ("surviving_spouse(X)",))
    rid = _r(theory, rid, "has_inheritance_right(X)", ("child_of_deceased(X)",))

    # ── Family defeaters ─────────────────────────────────────────

    rid = _r(theory, rid, "~has_custody_right(X)", ("abusive_parent(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_adopt(X)", ("person_with_abuse_record(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~entitled_to_spousal_support(X)", ("spouse_with_fault(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_inheritance_right(X)", ("disinherited_heir(X)",), RuleType.DEFEATER)

    # ── Employment law defaults ──────────────────────────────────

    rid = _r(theory, rid, "entitled_to_minimum_wage(X)", ("employee(X)",))
    rid = _r(theory, rid, "has_overtime_right(X)", ("non_exempt_employee(X)",))
    rid = _r(theory, rid, "protected_from_wrongful_termination(X)", ("employee(X)",))
    rid = _r(theory, rid, "can_form_union(X)", ("employee(X)",))
    rid = _r(theory, rid, "entitled_to_safe_workplace(X)", ("employee(X)",))
    rid = _r(theory, rid, "entitled_to_leave(X)", ("employee(X)",))
    rid = _r(theory, rid, "protected_from_retaliation(X)", ("whistleblower(X)",))
    rid = _r(theory, rid, "entitled_to_workers_comp(X)", ("injured_worker(X)",))

    # ── Employment defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~entitled_to_minimum_wage(X)", ("independent_contractor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_overtime_right(X)", ("exempt_employee(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_form_union(X)", ("supervisor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~protected_from_wrongful_termination(X)", ("at_will_employee(X)",), RuleType.DEFEATER)

    # ── Administrative law defaults ──────────────────────────────

    rid = _r(theory, rid, "subject_to_judicial_review(X)", ("agency_decision(X)",))
    rid = _r(theory, rid, "must_provide_notice_and_comment(X)", ("proposed_regulation(X)",))
    rid = _r(theory, rid, "must_follow_procedure(X)", ("administrative_action(X)",))
    rid = _r(theory, rid, "can_appeal_agency_decision(X)", ("aggrieved_party(X)",))
    rid = _r(theory, rid, "must_keep_records(X)", ("government_agency(X)",))
    rid = _r(theory, rid, "subject_to_foia(X)", ("government_agency(X)",))

    # ── Administrative defeaters ─────────────────────────────────

    rid = _r(theory, rid, "~subject_to_judicial_review(X)", ("prosecutorial_discretion(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~must_provide_notice_and_comment(X)", ("emergency_regulation(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_appeal_agency_decision(X)", ("unreviewable_discretion(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~subject_to_foia(X)", ("classified_information(X)",), RuleType.DEFEATER)

    # ── Multi-body compound rules (defeasible) ───────────────────

    rid = _r(theory, rid, "valid_contract(X)", ("can_enter_contract(X)", "has_consideration(X)"))
    rid = _r(theory, rid, "criminal_liability(X)", ("actus_reus(X)", "mens_rea(X)"))
    rid = _r(theory, rid, "qualified_voter(X)", ("can_vote(X)", "registered_voter(X)"))
    rid = _r(theory, rid, "enforceable_agreement(X)", ("valid_contract(X)", "not_unconscionable(X)"))
    rid = _r(theory, rid, "tortious_liability(X)", ("owes_duty_of_care(X)", "breached_duty(X)"))
    rid = _r(theory, rid, "complete_defense(X)", ("acting_in_self_defense(X)", "proportional_force(X)"))
    rid = _r(theory, rid, "valid_search(X)", ("has_warrant(X)", "probable_cause(X)"))
    rid = _r(theory, rid, "custodial_parent(X)", ("has_custody_right(X)", "primary_residence(X)"))
    rid = _r(theory, rid, "protected_employee(X)", ("employee(X)", "protected_class(X)"))
    rid = _r(theory, rid, "binding_precedent(X)", ("court_decision(X)", "same_jurisdiction(X)"))
    rid = _r(theory, rid, "admissible_expert_testimony(X)", ("expert_witness(X)", "relevant_expertise(X)"))
    rid = _r(theory, rid, "valid_will(X)", ("has_legal_capacity(X)", "has_witnesses(X)"))
    rid = _r(theory, rid, "corporate_officer_liable(X)", ("corporate_officer(X)", "breached_duty(X)"))
    rid = _r(theory, rid, "valid_plea_bargain(X)", ("allows_plea_bargain(X)", "voluntary_agreement(X)"))
    rid = _r(theory, rid, "qualified_immunity(X)", ("government_official(X)", "reasonable_belief(X)"))
    rid = _r(theory, rid, "effective_counsel(X)", ("has_right_to_counsel(X)", "competent_attorney(X)"))
    rid = _r(theory, rid, "valid_adoption(X)", ("can_adopt(X)", "best_interest_of_child(X)"))
    rid = _r(theory, rid, "enforceable_judgment(X)", ("valid_judgment(X)", "proper_jurisdiction(X)"))
    rid = _r(theory, rid, "lawful_arrest(X)", ("probable_cause(X)", "authorized_officer(X)"))
    rid = _r(theory, rid, "taxable_income(X)", ("obligated_to_pay_taxes(X)", "has_income(X)"))

    # ── Multi-body compound defeaters ────────────────────────────

    rid = _r(theory, rid, "~valid_contract(X)", ("contract_under_duress(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~criminal_liability(X)", ("insanity_defense(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~tortious_liability(X)", ("assumption_of_risk(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~valid_search(X)", ("fruit_of_poisonous_tree(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~binding_precedent(X)", ("overruled_decision(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~qualified_immunity(X)", ("clearly_established_right(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~enforceable_judgment(X)", ("void_judgment(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lawful_arrest(X)", ("unlawful_detention(X)",), RuleType.DEFEATER)

    return theory


def add_legal_superiority_relations(theory: Theory) -> None:
    """Register superiority relations among legal behavioral rules.

    Each call to theory.add_superiority(superior, inferior) declares that the
    superior rule prevails when both rules are applicable and yield conflicting
    conclusions.
    """

    # Capacity defeaters beat capacity defaults
    theory.add_superiority("legal_r2012", "legal_r2000")  # minor > adult capacity
    theory.add_superiority("legal_r2013", "legal_r2000")  # mentally incapacitated > adult capacity
    theory.add_superiority("legal_r2014", "legal_r2001")  # minor contract > can_enter_contract
    theory.add_superiority("legal_r2016", "legal_r2002")  # felon > can_vote
    theory.add_superiority("legal_r2017", "legal_r2002")  # non-citizen > can_vote

    # Liability defeaters beat liability defaults
    theory.add_superiority("legal_r2034", "legal_r2026")  # diplomat > tortfeasor liability
    theory.add_superiority("legal_r2035", "legal_r2026")  # sovereign > tortfeasor liability
    theory.add_superiority("legal_r2038", "legal_r2029")  # insanity > criminal liability

    # Procedural defeaters beat procedural defaults
    theory.add_superiority("legal_r2055", "legal_r2048")  # supreme court > bound_by_precedent
    theory.add_superiority("legal_r2057", "legal_r2050")  # hearsay > admissible evidence
    theory.add_superiority("legal_r2058", "legal_r2050")  # illegally obtained > admissible evidence

    # Normative defeaters beat normative defaults
    theory.add_superiority("legal_r2083", "legal_r2077")  # tax exempt > obligated_to_pay_taxes

    # Emancipated-minor overrides beat minor defeaters (defeater of a defeater)
    theory.add_superiority("legal_r2024", "legal_r2012")  # emancipated minor capacity > minor defeater
    theory.add_superiority("legal_r2025", "legal_r2014")  # emancipated minor contract > minor defeater

    # Normative exception specificity
    theory.add_superiority("legal_r2086", "legal_r2080")  # religious org > prohibited discrimination


def count_legal_behavioral_rules(theory: Theory) -> dict:
    """Return a breakdown of legal behavioral rule counts by type."""
    legal_rules = [r for r in theory.rules if r.label and r.label.startswith("legal_r")]
    defeasible = [r for r in legal_rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in legal_rules if r.rule_type == RuleType.DEFEATER]
    return {
        "total_behavioral": len(legal_rules),
        "defeasible": len(defeasible),
        "defeaters": len(defeaters),
    }
