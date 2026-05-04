# Instance samples (review version)

This directory contains 50-instance samples from each of the DeFAb tiers
described in the paper. The samples are sufficient to inspect format,
schema, and example content. The full dataset (372,648+ instances across
33.75M materialized rules from 18 knowledge sources) is available via
the anonymous review mirror; the camera-ready version will reveal the
HuggingFace path.

## Layout

- `synthetic/` — 409 contamination-control instances with invented
  predicate names (full release; central to the contamination-resistance
  claim in Section 3.5 and Appendix F)
- `tier1/{biology,chemistry,everyday,legal,materials}/instances.json`
  — 50-instance samples from the cross-ontology tier (full size: 324,511
  instances total across these five domains)
- `multitier/{babelnet,framenet,gene_ontology,mesh,sumo,umls,wikidata,yago_full}/instances.json`
  — 50-instance samples from the domain-specific Tier 2 sources
- Tier 0 (the 409-instance baseline used for the primary frontier-model
  evaluation in Section 5) is on the full mirror; instance counts and
  composition are reported in Table 1 and Figure 2 of the paper

## Schema

Each instance is a JSON object containing the challenge theory $\mathcal{D}^-$,
target literal $q$, candidate hypothesis set $\mathcal{H}_{\mathrm{cand}}$,
gold-standard answers $\mathcal{H}^*$, structural difficulty metrics
($|\mathrm{Supp}|$, $\mathrm{Nov}^*$, etc.), and renderings in all four
text modalities (M1 narrative, M2 semi-formal, M3 annotated formal,
M4 pure formal). M5 visual instances follow the same schema with image
references in place of selected entity-grounding facts.
