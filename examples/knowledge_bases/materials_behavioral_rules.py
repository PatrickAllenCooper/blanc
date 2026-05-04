"""
Materials Science Behavioral Rules -- Defeasible Defaults and Defeaters

Defeasible rules encoding material property defaults and their known
exceptions, grounded in the MatOnto ontology concepts.  Material
properties are inherently defeasible: general class properties admit
exceptions for specific alloys, treatments, and compositions.

Author: Anonymous Authors
"""

from blanc.core.theory import Theory, Rule, RuleType


def _r(theory: Theory, rid: int, head: str, body: tuple,
       rtype: RuleType = RuleType.DEFEASIBLE) -> int:
    theory.add_rule(Rule(
        head=head, body=body, rule_type=rtype,
        label=f"mat_beh_r{rid}",
    ))
    return rid + 1


def add_materials_behavioral_rules(theory: Theory) -> Theory:
    """Add defeasible material-property rules and defeaters."""

    rid = 3000

    # ── Electrical conductivity defaults ─────────────────────────

    rid = _r(theory, rid, "conducts_electricity(X)", ("metal(X)",))
    rid = _r(theory, rid, "conducts_electricity(X)", ("alloy(X)",))
    rid = _r(theory, rid, "conducts_electricity(X)", ("semiconductor(X)",))
    rid = _r(theory, rid, "insulates_electricity(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "insulates_electricity(X)", ("polymer(X)",))
    rid = _r(theory, rid, "insulates_electricity(X)", ("glass(X)",))
    rid = _r(theory, rid, "insulates_electricity(X)", ("rubber(X)",))

    # ── Electrical defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~insulates_electricity(X)", ("ceramic_superconductor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~insulates_electricity(X)", ("conductive_polymer(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~insulates_electricity(X)", ("graphite(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~conducts_electricity(X)", ("oxidized_metal(X)",), RuleType.DEFEATER)

    # ── Thermal conductivity defaults ────────────────────────────

    rid = _r(theory, rid, "conducts_heat(X)", ("metal(X)",))
    rid = _r(theory, rid, "conducts_heat(X)", ("alloy(X)",))
    rid = _r(theory, rid, "insulates_heat(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "insulates_heat(X)", ("polymer(X)",))
    rid = _r(theory, rid, "insulates_heat(X)", ("aerogel(X)",))

    # ── Thermal defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~conducts_heat(X)", ("stainless_steel(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~conducts_heat(X)", ("titanium(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~insulates_heat(X)", ("diamond(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~insulates_heat(X)", ("aluminum_nitride(X)",), RuleType.DEFEATER)

    # ── Mechanical property defaults ─────────────────────────────

    rid = _r(theory, rid, "is_ductile(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_ductile(X)", ("alloy(X)",))
    rid = _r(theory, rid, "is_malleable(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_brittle(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "is_brittle(X)", ("glass(X)",))
    rid = _r(theory, rid, "is_elastic(X)", ("rubber(X)",))
    rid = _r(theory, rid, "is_elastic(X)", ("elastomer(X)",))
    rid = _r(theory, rid, "is_flexible(X)", ("polymer(X)",))
    rid = _r(theory, rid, "has_high_tensile_strength(X)", ("steel(X)",))
    rid = _r(theory, rid, "has_high_tensile_strength(X)", ("carbon_fiber(X)",))
    rid = _r(theory, rid, "has_high_tensile_strength(X)", ("titanium_alloy(X)",))
    rid = _r(theory, rid, "has_high_hardness(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "has_high_hardness(X)", ("diamond(X)",))
    rid = _r(theory, rid, "has_high_hardness(X)", ("carbide(X)",))
    rid = _r(theory, rid, "has_high_toughness(X)", ("steel(X)",))
    rid = _r(theory, rid, "has_high_toughness(X)", ("titanium_alloy(X)",))

    # ── Mechanical defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~is_ductile(X)", ("cast_iron(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_ductile(X)", ("tungsten(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_ductile(X)", ("bismuth(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_brittle(X)", ("metallic_glass(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_brittle(X)", ("toughened_ceramic(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_brittle(X)", ("tempered_glass(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_flexible(X)", ("thermoset(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_hardness(X)", ("soapstone(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_toughness(X)", ("high_carbon_steel(X)",), RuleType.DEFEATER)

    # ── Corrosion and degradation defaults ───────────────────────

    rid = _r(theory, rid, "resists_corrosion(X)", ("noble_metal(X)",))
    rid = _r(theory, rid, "resists_corrosion(X)", ("stainless_steel(X)",))
    rid = _r(theory, rid, "resists_corrosion(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "resists_corrosion(X)", ("polymer(X)",))
    rid = _r(theory, rid, "corrodes(X)", ("iron(X)",))
    rid = _r(theory, rid, "corrodes(X)", ("carbon_steel(X)",))
    rid = _r(theory, rid, "degrades_in_uv(X)", ("polymer(X)",))
    rid = _r(theory, rid, "oxidizes(X)", ("metal(X)",))

    # ── Corrosion defeaters ──────────────────────────────────────

    rid = _r(theory, rid, "~resists_corrosion(X)", ("stressed_stainless_steel(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~corrodes(X)", ("weathering_steel(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~oxidizes(X)", ("gold(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~oxidizes(X)", ("platinum(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~degrades_in_uv(X)", ("fluoropolymer(X)",), RuleType.DEFEATER)

    # ── Optical property defaults ────────────────────────────────

    rid = _r(theory, rid, "is_opaque(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_opaque(X)", ("alloy(X)",))
    rid = _r(theory, rid, "is_transparent(X)", ("glass(X)",))
    rid = _r(theory, rid, "is_transparent(X)", ("diamond(X)",))
    rid = _r(theory, rid, "is_translucent(X)", ("opal(X)",))

    # ── Optical defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~is_opaque(X)", ("transparent_ceramic(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_opaque(X)", ("thin_metal_film(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_transparent(X)", ("frosted_glass(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_transparent(X)", ("colored_diamond(X)",), RuleType.DEFEATER)

    # ── Magnetic property defaults ───────────────────────────────

    rid = _r(theory, rid, "is_magnetic(X)", ("iron(X)",))
    rid = _r(theory, rid, "is_magnetic(X)", ("nickel(X)",))
    rid = _r(theory, rid, "is_magnetic(X)", ("cobalt(X)",))
    rid = _r(theory, rid, "is_magnetic(X)", ("ferrite(X)",))
    rid = _r(theory, rid, "is_non_magnetic(X)", ("aluminum(X)",))
    rid = _r(theory, rid, "is_non_magnetic(X)", ("copper(X)",))
    rid = _r(theory, rid, "is_non_magnetic(X)", ("polymer(X)",))

    # ── Magnetic defeaters ───────────────────────────────────────

    rid = _r(theory, rid, "~is_magnetic(X)", ("austenitic_stainless_steel(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_magnetic(X)", ("paramagnetic_iron_compound(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_non_magnetic(X)", ("neodymium_alloy(X)",), RuleType.DEFEATER)

    # ── Structural property defaults ─────────────────────────────

    rid = _r(theory, rid, "is_crystalline(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_crystalline(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "is_amorphous(X)", ("glass(X)",))
    rid = _r(theory, rid, "is_amorphous(X)", ("polymer(X)",))
    rid = _r(theory, rid, "has_high_density(X)", ("metal(X)",))
    rid = _r(theory, rid, "has_low_density(X)", ("polymer(X)",))
    rid = _r(theory, rid, "has_low_density(X)", ("aerogel(X)",))
    rid = _r(theory, rid, "has_high_melting_point(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "has_high_melting_point(X)", ("refractory_metal(X)",))
    rid = _r(theory, rid, "has_low_melting_point(X)", ("solder(X)",))
    rid = _r(theory, rid, "has_low_melting_point(X)", ("wax(X)",))

    # ── Structural defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~is_crystalline(X)", ("metallic_glass(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_amorphous(X)", ("crystalline_polymer(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_density(X)", ("aluminum(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_density(X)", ("magnesium(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_density(X)", ("titanium(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_melting_point(X)", ("ice(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_low_melting_point(X)", ("tungsten_carbide(X)",), RuleType.DEFEATER)

    # ── Processing defaults ──────────────────────────────────────

    rid = _r(theory, rid, "can_be_welded(X)", ("metal(X)",))
    rid = _r(theory, rid, "can_be_forged(X)", ("metal(X)",))
    rid = _r(theory, rid, "can_be_cast(X)", ("metal(X)",))
    rid = _r(theory, rid, "can_be_machined(X)", ("metal(X)",))
    rid = _r(theory, rid, "can_be_sintered(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "can_be_injection_molded(X)", ("thermoplastic(X)",))
    rid = _r(theory, rid, "softens_on_annealing(X)", ("metal(X)",))
    rid = _r(theory, rid, "hardens_on_quenching(X)", ("steel(X)",))

    # ── Processing defeaters ─────────────────────────────────────

    rid = _r(theory, rid, "~can_be_welded(X)", ("cast_iron(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_be_welded(X)", ("tungsten(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_be_forged(X)", ("cast_iron(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_be_machined(X)", ("hardened_steel(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~softens_on_annealing(X)", ("precipitation_hardening_alloy(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~hardens_on_quenching(X)", ("austenitic_stainless_steel(X)",), RuleType.DEFEATER)

    # ── Biocompatibility defaults ────────────────────────────────

    rid = _r(theory, rid, "is_biocompatible(X)", ("titanium(X)",))
    rid = _r(theory, rid, "is_biocompatible(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "is_biocompatible(X)", ("gold(X)",))
    rid = _r(theory, rid, "is_toxic(X)", ("lead(X)",))
    rid = _r(theory, rid, "is_toxic(X)", ("cadmium(X)",))
    rid = _r(theory, rid, "is_toxic(X)", ("mercury(X)",))
    rid = _r(theory, rid, "is_toxic(X)", ("asbestos(X)",))

    # ── Biocompatibility defeaters ───────────────────────────────

    rid = _r(theory, rid, "~is_biocompatible(X)", ("nickel_alloy_implant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_toxic(X)", ("lead_glass(X)",), RuleType.DEFEATER)

    # ── Phase transition defaults ────────────────────────────────

    rid = _r(theory, rid, "is_solid_at_room_temp(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_solid_at_room_temp(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "is_liquid_at_room_temp(X)", ("oil(X)",))
    rid = _r(theory, rid, "is_gas_at_room_temp(X)", ("noble_gas(X)",))
    rid = _r(theory, rid, "sublimes(X)", ("dry_ice(X)",))
    rid = _r(theory, rid, "sublimes(X)", ("naphthalene(X)",))
    rid = _r(theory, rid, "undergoes_glass_transition(X)", ("polymer(X)",))
    rid = _r(theory, rid, "undergoes_glass_transition(X)", ("glass(X)",))
    rid = _r(theory, rid, "has_curie_temperature(X)", ("ferromagnetic_material(X)",))
    rid = _r(theory, rid, "has_superconducting_transition(X)", ("superconductor(X)",))

    # ── Phase transition defeaters ───────────────────────────────

    rid = _r(theory, rid, "~is_solid_at_room_temp(X)", ("mercury(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_solid_at_room_temp(X)", ("gallium(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_gas_at_room_temp(X)", ("radon(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~undergoes_glass_transition(X)", ("thermoset(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_curie_temperature(X)", ("diamagnetic_material(X)",), RuleType.DEFEATER)

    # ── Failure mode defaults ────────────────────────────────────

    rid = _r(theory, rid, "fails_by_fatigue(X)", ("metal(X)",))
    rid = _r(theory, rid, "fails_by_fatigue(X)", ("alloy(X)",))
    rid = _r(theory, rid, "fails_by_creep(X)", ("metal(X)",))
    rid = _r(theory, rid, "fails_by_creep(X)", ("polymer(X)",))
    rid = _r(theory, rid, "fails_by_brittle_fracture(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "fails_by_brittle_fracture(X)", ("glass(X)",))
    rid = _r(theory, rid, "fails_by_yielding(X)", ("metal(X)",))
    rid = _r(theory, rid, "stress_corrosion_cracks(X)", ("alloy(X)",))
    rid = _r(theory, rid, "fails_by_delamination(X)", ("composite(X)",))
    rid = _r(theory, rid, "fails_by_crazing(X)", ("polymer(X)",))

    # ── Failure mode defeaters ───────────────────────────────────

    rid = _r(theory, rid, "~fails_by_fatigue(X)", ("single_crystal_alloy(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~fails_by_creep(X)", ("refractory_metal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~fails_by_brittle_fracture(X)", ("toughened_ceramic(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~fails_by_yielding(X)", ("ceramic(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~stress_corrosion_cracks(X)", ("noble_metal(X)",), RuleType.DEFEATER)

    # ── Surface property defaults ────────────────────────────────

    rid = _r(theory, rid, "has_high_surface_energy(X)", ("metal(X)",))
    rid = _r(theory, rid, "has_high_surface_energy(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "is_hydrophobic(X)", ("polymer(X)",))
    rid = _r(theory, rid, "is_hydrophobic(X)", ("teflon(X)",))
    rid = _r(theory, rid, "is_hydrophilic(X)", ("glass(X)",))
    rid = _r(theory, rid, "is_hydrophilic(X)", ("ceramic(X)",))
    rid = _r(theory, rid, "has_low_friction(X)", ("teflon(X)",))
    rid = _r(theory, rid, "has_low_friction(X)", ("graphite(X)",))

    # ── Surface defeaters ────────────────────────────────────────

    rid = _r(theory, rid, "~has_high_surface_energy(X)", ("passivated_metal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_hydrophobic(X)", ("hydrophilic_polymer(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_hydrophilic(X)", ("hydrophobic_coating(X)",), RuleType.DEFEATER)

    # ── Composite behavior defaults ──────────────────────────────

    rid = _r(theory, rid, "is_anisotropic(X)", ("composite(X)",))
    rid = _r(theory, rid, "is_anisotropic(X)", ("wood(X)",))
    rid = _r(theory, rid, "has_fiber_reinforcement(X)", ("fiberglass(X)",))
    rid = _r(theory, rid, "has_fiber_reinforcement(X)", ("carbon_fiber_composite(X)",))
    rid = _r(theory, rid, "has_matrix_material(X)", ("composite(X)",))
    rid = _r(theory, rid, "has_high_specific_strength(X)", ("carbon_fiber(X)",))
    rid = _r(theory, rid, "has_high_specific_strength(X)", ("titanium_alloy(X)",))
    rid = _r(theory, rid, "has_layered_structure(X)", ("laminate(X)",))

    # ── Composite defeaters ──────────────────────────────────────

    rid = _r(theory, rid, "~is_anisotropic(X)", ("randomly_reinforced_composite(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_high_specific_strength(X)", ("heavy_metal_composite(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~has_layered_structure(X)", ("bulk_composite(X)",), RuleType.DEFEATER)

    # ── Semiconductor defaults ───────────────────────────────────

    rid = _r(theory, rid, "has_band_gap(X)", ("semiconductor(X)",))
    rid = _r(theory, rid, "can_be_doped(X)", ("semiconductor(X)",))
    rid = _r(theory, rid, "exhibits_photovoltaic_effect(X)", ("silicon(X)",))
    rid = _r(theory, rid, "exhibits_photovoltaic_effect(X)", ("gallium_arsenide(X)",))
    rid = _r(theory, rid, "has_pn_junction(X)", ("diode(X)",))
    rid = _r(theory, rid, "has_pn_junction(X)", ("transistor(X)",))
    rid = _r(theory, rid, "exhibits_piezoelectricity(X)", ("quartz(X)",))
    rid = _r(theory, rid, "exhibits_piezoelectricity(X)", ("pzt_ceramic(X)",))

    # ── Semiconductor defeaters ──────────────────────────────────

    rid = _r(theory, rid, "~has_band_gap(X)", ("metal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~can_be_doped(X)", ("insulator(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~exhibits_piezoelectricity(X)", ("centrosymmetric_crystal(X)",), RuleType.DEFEATER)

    # ── Recyclability defaults ───────────────────────────────────

    rid = _r(theory, rid, "is_recyclable(X)", ("metal(X)",))
    rid = _r(theory, rid, "is_recyclable(X)", ("glass(X)",))
    rid = _r(theory, rid, "is_recyclable(X)", ("thermoplastic(X)",))
    rid = _r(theory, rid, "is_biodegradable(X)", ("natural_polymer(X)",))
    rid = _r(theory, rid, "is_biodegradable(X)", ("wood(X)",))
    rid = _r(theory, rid, "is_compostable(X)", ("paper(X)",))

    # ── Recyclability defeaters ──────────────────────────────────

    rid = _r(theory, rid, "~is_recyclable(X)", ("contaminated_metal(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_recyclable(X)", ("thermoset(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~is_biodegradable(X)", ("synthetic_polymer(X)",), RuleType.DEFEATER)

    # ── Multi-body compound defaults ─────────────────────────────

    rid = _r(theory, rid, "structural_metal(X)", ("metal(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "refractory_material(X)", ("has_high_melting_point(X)", "resists_corrosion(X)"))
    rid = _r(theory, rid, "electronic_material(X)", ("conducts_electricity(X)", "is_crystalline(X)"))
    rid = _r(theory, rid, "thermal_barrier(X)", ("insulates_heat(X)", "has_high_melting_point(X)"))
    rid = _r(theory, rid, "spring_material(X)", ("is_elastic(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "bearing_material(X)", ("has_low_friction(X)", "has_high_hardness(X)"))
    rid = _r(theory, rid, "cutting_tool_material(X)", ("has_high_hardness(X)", "has_high_melting_point(X)"))
    rid = _r(theory, rid, "implant_material(X)", ("is_biocompatible(X)", "resists_corrosion(X)"))
    rid = _r(theory, rid, "electrical_insulator(X)", ("insulates_electricity(X)", "insulates_heat(X)"))
    rid = _r(theory, rid, "transparent_conductor(X)", ("is_transparent(X)", "conducts_electricity(X)"))
    rid = _r(theory, rid, "lightweight_structural(X)", ("has_low_density(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "magnetic_storage(X)", ("is_magnetic(X)", "has_high_hardness(X)"))
    rid = _r(theory, rid, "corrosion_resistant_structural(X)", ("resists_corrosion(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "high_temp_structural(X)", ("has_high_melting_point(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "flexible_conductor(X)", ("conducts_electricity(X)", "is_flexible(X)"))
    rid = _r(theory, rid, "recyclable_structural(X)", ("is_recyclable(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "biocompatible_ceramic(X)", ("is_biocompatible(X)", "ceramic(X)"))
    rid = _r(theory, rid, "machinable_alloy(X)", ("can_be_machined(X)", "alloy(X)"))
    rid = _r(theory, rid, "weldable_structural(X)", ("can_be_welded(X)", "has_high_tensile_strength(X)"))
    rid = _r(theory, rid, "castable_alloy(X)", ("can_be_cast(X)", "alloy(X)"))

    # ── Multi-body compound defeaters ────────────────────────────

    rid = _r(theory, rid, "~structural_metal(X)", ("lead(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~refractory_material(X)", ("calcium_oxide(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~spring_material(X)", ("cast_iron(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~implant_material(X)", ("nickel_alloy_implant(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~transparent_conductor(X)", ("opaque_conductor(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~lightweight_structural(X)", ("foam(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~weldable_structural(X)", ("cast_iron(X)",), RuleType.DEFEATER)
    rid = _r(theory, rid, "~machinable_alloy(X)", ("hardened_steel(X)",), RuleType.DEFEATER)

    return theory


def add_materials_superiority_relations(theory: Theory) -> None:
    """Establish superiority among competing materials behavioral rules."""

    # Electrical: specific defeaters beat general insulation defaults
    theory.add_superiority("mat_beh_r3007", "mat_beh_r3003")   # ceramic superconductor > ceramic insulates
    theory.add_superiority("mat_beh_r3008", "mat_beh_r3004")   # conductive polymer > polymer insulates
    theory.add_superiority("mat_beh_r3009", "mat_beh_r3003")   # graphite > ceramic insulates

    # Mechanical: specific defeaters beat general ductility/brittleness defaults
    theory.add_superiority("mat_beh_r3033", "mat_beh_r3022")   # cast iron ductile defeater > metal ductile
    theory.add_superiority("mat_beh_r3036", "mat_beh_r3025")   # metallic glass brittle defeater > ceramic brittle
    theory.add_superiority("mat_beh_r3038", "mat_beh_r3026")   # tempered glass brittle defeater > glass brittle

    # Corrosion: specific defeaters beat general corrosion defaults
    theory.add_superiority("mat_beh_r3050", "mat_beh_r3042")   # weathering steel corrodes defeater > iron corrodes
    theory.add_superiority("mat_beh_r3051", "mat_beh_r3045")   # gold oxidizes defeater > metal oxidizes

    # Optical: specific defeaters beat general opacity defaults
    theory.add_superiority("mat_beh_r3057", "mat_beh_r3046")   # transparent ceramic > metal opaque

    # Magnetic: specific defeaters beat general magnetic defaults
    theory.add_superiority("mat_beh_r3063", "mat_beh_r3053")   # austenitic SS magnetic defeater > iron magnetic

    # Structural: specific defeaters beat general crystalline/density defaults
    theory.add_superiority("mat_beh_r3066", "mat_beh_r3056")   # metallic glass crystalline defeater > metal crystalline
    theory.add_superiority("mat_beh_r3068", "mat_beh_r3060")   # aluminum density defeater > metal density

    # Processing: specific defeaters beat general processing defaults
    theory.add_superiority("mat_beh_r3079", "mat_beh_r3072")   # cast iron weld defeater > metal weldable
    theory.add_superiority("mat_beh_r3081", "mat_beh_r3073")   # cast iron forge defeater > metal forgeable

    # Phase transition: mercury solid defeater beats metal solid default
    theory.add_superiority("mat_beh_r3128", "mat_beh_r3118")   # mercury solid defeater > metal solid at room temp


def count_materials_behavioral_rules(theory: Theory) -> dict:
    """Return a breakdown of materials behavioral rule counts by type."""
    mat_rules = [r for r in theory.rules if r.label and r.label.startswith("mat_beh_r")]
    defeasible = [r for r in mat_rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in mat_rules if r.rule_type == RuleType.DEFEATER]
    return {
        "total_behavioral": len(mat_rules),
        "defeasible": len(defeasible),
        "defeaters": len(defeaters),
    }
