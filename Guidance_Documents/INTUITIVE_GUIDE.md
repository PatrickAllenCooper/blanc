# BLANC: An Intuitive Guide to the Benchmark

**Understanding What We're Testing and Why It Matters**

Patrick Cooper  
February 13, 2026

---

## The Big Picture

Imagine you're a scientist, lawyer, or engineer with years of expertise. You know thousands of rules about your domain - some absolute, some with exceptions. When faced with a new problem, you can reason about what's missing and fill in the gaps.

**Can AI models do this?**

That's what BLANC tests: Can foundation models perform **defeasible abductive reasoning** - the ability to figure out what missing knowledge would explain an observation, while handling exceptions and conflicting information.

---

## What is Defeasible Reasoning?

**Defeasible** means "can be defeated" or "has exceptions."

### Example: Birds and Flying

**Rule**: Birds typically fly.

**But**: Penguins are birds that don't fly.

Traditional logic can't handle this elegantly. Defeasible logic can say:
- "Birds fly" is a **defeasible rule** (usually true, but has exceptions)
- "Penguins don't fly" can **defeat** the general rule for penguins

This is how real-world expertise works - full of useful generalizations that have exceptions.

---

## What is Abductive Reasoning?

**Abduction** is reasoning backwards from observations to explanations.

### Example: Materials Science

**Given**:
- You know: "Alloys are typically strong"
- You observe: "Steel is strong"
- You ask: **Why is steel strong?**

**Answer**: "Because steel is an alloy"

You're working backwards from the observation (steel is strong) to find the explanation (steel is an alloy, and alloys are strong).

---

## The Three Domains

We test this reasoning across three expert domains:

### 1. Biology (YAGO + WordNet)

**Source**: 927 rules from peer-reviewed taxonomies  
**Focus**: Animal taxonomy, behavior, and traits

**Example Rules**:
```
STRICT RULES (always true):
- "If X is a bird, then X is an animal"
- "If X is a mammal, then X is a vertebrate"
- "If X is a lion, then X is a carnivore"

DEFEASIBLE RULES (usually true):
- "Birds typically fly"
- "Mammals typically walk"
- "Fish typically swim"
- "Carnivores typically hunt"
```

**Example Facts**:
```
- robin is a bird
- penguin is a bird (but penguins don't fly!)
- dolphin is a mammal
- shark is a fish
```

---

### 2. Legal Reasoning (LKIF Core)

**Source**: 201 rules from Amsterdam Legal Knowledge Base  
**Focus**: Legal documents, entities, and relationships

**Example Rules**:
```
STRICT RULES:
- "If X is a statute, then X is a legal document"
- "If X is a contract, then X is a legal document"
- "If X is a regulation, then X is a legal norm"

DEFEASIBLE RULES:
- "Legal documents typically have enforceable provisions"
- "Contracts typically create obligations"
- "Statutes typically apply to citizens"
```

**Example Facts**:
```
- ferpa is a statute (Family Educational Rights and Privacy Act)
- ada is a statute (Americans with Disabilities Act)
- service_agreement is a contract
- subpoena is a legal action
```

---

### 3. Materials Science (MatOnto)

**Source**: 1,190 rules from Materials Science Ontology  
**Focus**: Materials, properties, and structure-property relationships

**Example Rules**:
```
STRICT RULES:
- "If X is a metal, then X is a material"
- "If X is an alloy, then X is a solution"
- "If X is diamond, then X is hard"

DEFEASIBLE RULES:
- "Metals are typically conductive"
- "Crystals are typically brittle"
- "Metals are typically ductile"
- "Alloys are typically strong"
- "Polymers are typically flexible"
```

**Example Facts**:
```
- iron is a metal
- steel is an alloy
- diamond is a crystal
- polyethylene is a polymer
- stainless_steel is corrosion resistant
```

---

## What Does a Test Look Like?

### Scenario: Biology Example

**The Setup**:
```
You have these facts:
- owl is an organism
- owl is an animal

You have these rules:
- Birds are animals (strict)
- Birds are vertebrates (strict)
- Birds typically fly (defeasible)
- Birds typically sing (defeasible)
```

**The Challenge**:
```
Question: "Is owl a bird?"

Problem: You CAN'T derive "owl is a bird" from what you know!
  - You know owl is an animal
  - But MANY things are animals (mammals, fish, reptiles...)
  - The rules go forward (bird → animal), not backward

Task: What HYPOTHESIS would let you derive "owl is a bird"?
```

**The Answer**:
```
Hypothesis: "owl is a bird"

Why it works:
  - IF we add "owl is a bird" to our knowledge
  - THEN we can derive everything we observe:
    - "owl is a bird" + rule "birds are animals" → "owl is an animal" ✓
    - "owl is a bird" + rule "birds are vertebrates" → "owl is a vertebrate" ✓

This is the ABDUCTIVE step: finding what's missing.
```

**The AI's Job**:

We give the model 6 candidates:
```
1. "owl is a bird" ← CORRECT!
2. "dog is an organism" ← Wrong (doesn't help with owl)
3. "duck is an animal" ← Wrong (doesn't help with owl)
4. "whale is an organism" ← Wrong (doesn't help with owl)
5. "duck is an organism" ← Wrong (doesn't help with owl)
6. "cat is an organism" ← Wrong (doesn't help with owl)
```

**Can the AI pick #1?**

---

### Scenario: Materials Science Example

**The Setup**:
```
You have these facts:
- polyethylene is a material

You have these rules:
- Polymers are materials (strict)
- Polymers are typically flexible (defeasible)
```

**The Challenge**:
```
Question: "Is polyethylene a polymer?"

Problem: Can't derive it from what we know!
  - We know polyethylene is a material
  - But metals, alloys, crystals are ALSO materials
  - Need to figure out WHICH type

Task: What hypothesis explains why polyethylene is a material?
```

**The Answer**:
```
Hypothesis: "polyethylene is a polymer"

Why it works:
  - "polyethylene is a polymer" + "polymers are materials" 
    → "polyethylene is a material" ✓
  - This is the simplest explanation

AI must choose from:
1. "polyethylene is a polymer" ← CORRECT!
2. "diamond is a crystal" ← Wrong material
3. "titanium is a material" ← Too general
4. "gold is a material" ← Wrong material
5. "brass is an alloy" ← Wrong type
6. "brass is a material" ← Wrong material
```

---

### Scenario: Legal Reasoning Example

**The Setup**:
```
You have these facts:
- ferpa is recognized in court

You have these rules:
- Statutes are legal documents (strict)
- Legal documents are typically recognized in court (defeasible)
```

**The Challenge**:
```
Question: "Is FERPA a legal document?"

Problem: We know it's recognized in court, but WHY?
  - Many things can be recognized in court
  - Need to trace back to what TYPE of document it is

Task: Find the hypothesis that explains this
```

**The Answer**:
```
Hypothesis: "ferpa is a legal_document"

Why it works:
  - Directly states what we need
  - Explains court recognition via the defeasible rule

AI must distinguish from:
- "service_agreement is a legal_document" (different document)
- "ada is a statute" (different statute)
- "subpoena is a legal_action" (wrong category)
- etc.
```

---

## The Three Levels in One Example

The examples above are all Level 2. DeFAb has three levels, each testing a different capability. One scenario illustrates all three.

### The Theory: Bear Hibernation

A biologist knows the following:

```
Facts:   bear(grizzly). bear(polar_bear). bear(black_bear).
         arctic(polar_bear). seal_hunter(polar_bear). winter_active(polar_bear).
Strict:  r_s1: bear(X) -> mammal(X).
Default: r_d1: bear(X) => hibernates_in_winter(X).       "Bears typically hibernate."
Defeater:  r*: bear(X), arctic(X), seal_hunter(X) ~> ~hibernates_in_winter(X).
Superiority: r* > r_d1.
```

This derives: grizzly hibernates, black bear hibernates, polar bear does NOT (the defeater overrides the default). Now we ablate different pieces to create each level.

### Level 1: Find the Missing Fact

**Remove** `bear(grizzly)`. **Target:** `hibernates_in_winter(grizzly)`.

The rule "bears typically hibernate" is present, but the theory no longer says grizzly is a bear. The derivation chain is broken at its root. The model picks from candidates:

```
  bear(grizzly)    <- GOLD: completes the chain
  mammal(grizzly)  <- Tempting, but r_d1 requires bear(X), not mammal(X)
  bear(salmon)     <- Wrong entity
```

**The point:** trace a derivation backward and find the missing link.

### Level 2: Find the Missing Rule

**Remove** `r_d1` (the default "bears hibernate"). **Target:** `hibernates_in_winter(grizzly)`.

All facts are present, including `bear(grizzly)`. But no rule connects bears to hibernation. The model picks from candidates:

```
  bear(X) => hibernates_in_winter(X)    <- GOLD: the correct generalization
  mammal(X) => hibernates_in_winter(X)  <- Too broad: makes all mammals hibernate
  arctic(X) => hibernates_in_winter(X)  <- Wrong: arctic animals are less likely to hibernate
```

**The point:** reconstruct a missing generalization. The too-broad distractor technically works for this query but is the wrong rule.

### Level 3: Construct the Missing Exception

**Remove** `r*` and its superiority. **Target anomaly:** polar bear is active in winter, but the theory now predicts it hibernates.

All facts and rules are present. The default `r_d1` fires for polar bear and concludes `hibernates_in_winter(polar_bear)`. This contradicts the observed `winter_active(polar_bear)`. The model must *construct* a new rule (not select from candidates) that fixes this without breaking anything else:

```
Score 0:   "bears hibernate in winter"
           Restates the default. Anomaly unresolved.

Score 0.5: "no bears hibernate" (~hibernates(X) :- bear(X))
           Fixes the polar bear but DESTROYS grizzly and black bear
           conclusions. Sledgehammer, not scalpel. Not conservative.

Score 0.75: "arctic bears don't hibernate" (bear(X), arctic(X) ~> ~hibernates(X))
            Fixes polar bear, preserves others, but only makes the
            theory agnostic rather than positively asserting the exception.

Score 1.0: "arctic seal-hunting bears don't hibernate"
           (bear(X), arctic(X), seal_hunter(X) ~> ~hibernates(X), with r* > r_d1)
           Overrides the default precisely where it fails, preserves
           every other conclusion, captures the causal mechanism.
```

**The point:** Level 3 is qualitatively different. The model must invent a rule the theory has never seen, override a default it "believes," and do so with surgical precision. Too broad wrecks other conclusions. Too narrow misses the cause. Current models score near zero.

### Summary

| | Level 1 | Level 2 | Level 3 |
|---|---------|---------|---------|
| **What is missing** | A fact | A rule | An exception |
| **Task** | Select from candidates | Select from candidates | Construct from scratch |
| **Analogy** | Missing puzzle piece | Missing picture on box | Puzzle printed wrong; design the fix |
| **Conservativity** | Not required | Not required | Required (too-broad fixes break things) |
| **Deficit tested** | Grounding | Grounding + novelty | Grounding + novelty + belief revision |
| **Model performance** | High | High (direct), drops with CoT | Near zero |

---

## Why This is Hard for AI

### Challenge 1: Backward Reasoning

Most AI training is **forward**: "Given A, conclude B"

Abduction requires **backward**: "Given B, find A that would explain it"

### Challenge 2: Defeasibility

The AI must understand:
- General rules ("birds fly")
- Exceptions ("penguins don't fly")
- When rules can be defeated

### Challenge 3: Multiple Candidates

We don't just ask "what's missing?" - we give 6 options:
- **1 correct answer** (the gold hypothesis)
- **5 distractors** (plausible but wrong)

The AI must:
1. Understand the query
2. Reason about what's needed
3. Evaluate each candidate
4. Pick the one that restores derivability

### Challenge 4: Domain Expertise

These aren't toy problems - they use **real expert knowledge**:
- YAGO 4.5 (Télécom Paris, SIGIR 2024)
- WordNet 3.0 (Princeton cognitive science)
- LKIF Core (University of Amsterdam legal ontology)
- MatOnto (Materials science community)

The AI must reason about real-world concepts, not artificial examples.

---

## The Four Modalities

We present the same problem in different formats to test representation robustness:

### M1: Narrative (Natural Language)

**Most human-readable, hardest for formal reasoning**

```
"We know that owl is an organism and owl is an animal. 
We also know that if something is a bird, it is an animal.
Which of the following would let us conclude that owl is a bird?"
```

### M2: Semi-Formal (Structured Text)

**Hybrid of natural language and logic**

```
THEORY:
  organism(owl)
  animal(owl)
  bird(X) → animal(X)

TARGET: bird(owl)

CANDIDATES:
  1. bird(owl)
  2. organism(dog)
  ...
```

### M3: Annotated Formal (Prolog with Comments)

**Formal syntax with natural language guidance**

```
% Facts
organism(owl).  % Owl is an organism
animal(owl).    % Owl is an animal

% Rules
animal(X) :- bird(X).  % Birds are animals

% Query: Can we derive bird(owl)?
```

### M4: Pure Formal (Raw Prolog)

**No natural language, just logic**

```
organism(owl).
animal(owl).
animal(X) :- bird(X).
?- bird(owl).
```

**Why test all 4?**
- See if models prefer natural vs formal representations
- Test if they can handle symbolic reasoning
- Measure representation bias

---

## The Evaluation Pipeline

### Step 1: Load Knowledge Base

Start with expert knowledge (e.g., biology KB with 16 rules, 45 facts)

### Step 2: Generate Test Instance

1. Pick a **target query** (e.g., "owl is a bird")
2. **Ablate** (remove) the critical knowledge that would let us derive it
3. Generate **5 distractor hypotheses** (plausible but wrong)
4. Create the test with 1 gold + 5 distractors

### Step 3: Encode in All Modalities

Convert the same test to M1, M2, M3, M4

### Step 4: Query Models

Ask each model (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3):
- **Direct prompt**: "Select the hypothesis that restores derivability"
- **Chain-of-Thought**: "Think step-by-step about what's missing"

### Step 5: Decode Response

The model responds in natural language. We use 3 decoders:
- **D1 (Exact Match)**: Does response contain exact hypothesis string?
- **D2 (Template Extraction)**: Can we parse structured answer?
- **D3 (Semantic Parse)**: Can we extract meaning from free text?

### Step 6: Verify & Score

Check if extracted hypothesis is correct:
- **Correct**: Model selected the gold hypothesis
- **Incorrect**: Model selected a distractor
- **Failed**: Couldn't decode response

---

## Real Examples from Our Dataset

### Biology Instance #1

```
TARGET: bird(owl)

THEORY (after ablation):
  Facts: organism(owl), animal(owl)
  Rules: bird(X) → animal(X)

CANDIDATES:
  ✓ bird(owl)                    [GOLD - restores derivability]
  ✗ organism(dog)                [Wrong entity]
  ✗ animal(duck)                 [Wrong entity]
  ✗ organism(whale)              [Wrong entity]
  ✗ organism(duck)               [Wrong entity]
  ✗ organism(cat)                [Wrong entity]
```

### Materials Instance #1

```
TARGET: polymer(polyethylene)

THEORY (after ablation):
  Facts: material(polyethylene)
  Rules: polymer(X) → material(X)

CANDIDATES:
  ✓ polymer(polyethylene)        [GOLD - explains observation]
  ✗ crystal(diamond)             [Different material]
  ✗ material(titanium)           [Too general]
  ✗ material(gold)               [Too general]
  ✗ alloy(brass)                 [Wrong type]
  ✗ material(brass)              [Wrong entity]
```

### Legal Instance #1

```
TARGET: legal_document(ferpa)

THEORY (after ablation):
  Facts: statute(ferpa), recognized_in_court(ferpa)
  Rules: legal_document(X) → recognized_in_court(X)

CANDIDATES:
  ✓ legal_document(ferpa)           [GOLD - direct classification]
  ✗ legal_document(service_agreement) [Different document]
  ✗ statute(ada)                      [Different statute]
  ✗ legal_action(subpoena)            [Wrong category]
  ✗ legal_document(partnership_agreement) [Different document]
  ✗ statute(ferpa)                    [Already known]
```

---

## What Makes Our Benchmark Unique

### 1. Expert-Grounded Knowledge

**Not hand-crafted** - all rules from peer-reviewed sources:
- YAGO 4.5 (Télécom Paris, published SIGIR 2024)
- WordNet 3.0 (Princeton, 50k+ citations)
- LKIF Core (University of Amsterdam, EU legal ontology project)
- MatOnto (Materials Genome Initiative, community-driven)

This ensures **ecological validity** - we're testing real-world reasoning.

### 2. Defeasible Logic

Most benchmarks use classical logic. We test **non-monotonic reasoning**:
- Rules with exceptions
- Preference between conflicting rules
- Realistic expert knowledge

### 3. Abductive Task

Most benchmarks test:
- **Deduction**: A → B, we have A, conclude B
- **Induction**: Many (A → B), generalize to all

We test:
- **Abduction**: We observe B, find A that explains it

This is how scientific hypotheses, medical diagnoses, and legal arguments work.

### 4. Multi-Modal Representation

Testing 4 modalities reveals:
- Do models prefer natural language or formal logic?
- Can they handle symbolic reasoning?
- Are they robust to representation changes?

### 5. Multiple Prompting Strategies

- **Direct**: Forces crisp reasoning
- **Chain-of-Thought**: Allows stepwise thinking

Reveals whether models benefit from explicit reasoning steps.

---

## Dataset Statistics

### Size
- **2,318 expert rules** (927 biology, 201 legal, 1,190 materials)
- **374 development instances** (114 biology, 168 legal, 92 materials)
- **Production**: Scaling to 1M+ instances with HPC

### Difficulty
- **All Level 2**: Moderate difficulty with distractors
- **Average 6 candidates** per instance (1 gold + 5 distractors)
- **Balanced distractors**: Syntactically similar but semantically wrong

### Coverage
- **3 expert domains** (biology, legal, materials)
- **4 modalities** (M1-M4)
- **2 prompting strategies** (direct, CoT)
- **5 models** (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3 70B/8B)

**Total evaluation**: 374 instances × 5 models × 4 modalities × 2 strategies = **14,960 queries**

---

## Example Prompt to a Model

### M2 (Semi-Formal) with Chain-of-Thought

```
You are a reasoning expert. Think step-by-step.

THEORY:
  organism(owl)
  animal(owl)
  bird(X) → animal(X)

TARGET: bird(owl)

CANDIDATES:
  1. bird(owl)
  2. organism(dog)
  3. animal(duck)
  4. organism(whale)
  5. organism(duck)
  6. organism(cat)

Analyze:
1. What does the target query require?
2. What is currently missing from the theory?
3. Which candidate fills this gap?
4. Why does this candidate work?

Final Answer: [hypothesis]
```

**What we hope to see**:

```
1. The target requires knowing that owl is a bird.

2. Currently missing: We know owl is an animal, but we don't 
   know what TYPE of animal. The rule says birds → animals, 
   but we need the reverse connection.

3. Candidate #1 "bird(owl)" fills this gap.

4. This works because:
   - Adding "bird(owl)" to our theory
   - Applying rule "bird(X) → animal(X)" with X=owl
   - Derives "animal(owl)" which we already observe
   - This EXPLAINS our observation

Final Answer: bird(owl)
```

---

## What We Learn From This

### Model Capabilities
- Can foundation models perform abductive reasoning?
- Do they understand defeasible logic?
- Are they robust to representation changes?

### Model Limitations
- Where do they fail? (Error taxonomy E1-E5)
- Do they prefer certain modalities?
- Does Chain-of-Thought help?

### Scaling Laws
- Does Llama 8B vs 70B show size effects?
- How does theory size affect accuracy?
- Are there phase transitions in difficulty?

### Symbolic Ceiling
- How do models compare to symbolic reasoners (ASP solvers)?
- What's the gap between neural and symbolic approaches?

---

## Why This Matters

### For AI Research
- **New benchmark** for reasoning under uncertainty
- **Grounded in real expertise** (not toy problems)
- **Tests neglected capabilities** (abduction, defeasibility)

### For Applications
- **Scientific discovery**: Generating hypotheses from observations
- **Medical diagnosis**: Explaining symptoms with diseases
- **Legal reasoning**: Finding precedents and statutes
- **Engineering**: Diagnosing system failures

### For Understanding AI
- **Where are models strong?** (pattern matching vs reasoning)
- **Where do they struggle?** (backward reasoning, exceptions)
- **How can we improve them?** (better representations, training)

---

## Summary: What We're Actually Testing

**The Core Question**: Given expert knowledge with rules and exceptions, can AI figure out what's missing to explain an observation?

**Three Domains**: Biology, Legal, Materials Science

**Real Expert Knowledge**: 2,318 rules from peer-reviewed sources

**The Task**: Pick the hypothesis that restores derivability (1 correct, 5 distractors)

**The Test**: 
- 4 representations (natural → formal)
- 2 strategies (direct, CoT)
- 5 models (GPT-4o, Claude, Gemini, Llama)

**What We Measure**:
- Accuracy (did they get it right?)
- Decoder stage (exact, template, semantic)
- Error patterns (where/why did they fail?)
- Modality effects (which representation works best?)
- Scaling effects (does size matter?)

**Why It's Hard**:
- Backward reasoning (observation → explanation)
- Defeasible rules (with exceptions)
- Real-world complexity (expert domains)
- Symbolic manipulation (not just pattern matching)

---

## Next Steps

With API keys, we can run the full evaluation:
1. **Pilot**: 20 instances, $1.40, validate pipeline
2. **Full**: 374 instances × 5 models × 4 modalities × 2 strategies = 14,960 queries
3. **Analysis**: Error taxonomy, model comparison, scaling laws
4. **Publication**: NeurIPS 2026 submission

**Status**: Infrastructure complete, ready to evaluate.

---

---

## Quick Reference: Levels, Objectives, and Dataset Counts

| Level | Task | Grounding | Novelty | Belief Revision | Dataset (Feb 2026) |
|-------|------|:---------:|:-------:|:---------------:|-------------------|
| 1 | Fact completion | Yes | No | No | 0 instances (future) |
| 2 | Rule abduction | Yes | No | No | 374 instances |
| 3 | Defeater abduction | Yes | Yes | Yes | 35 instances |

**Critical point**: Only Level 3 tests all three objectives simultaneously. The paper's title — "Grounding, Novelty, and Belief Revision" — requires Level 3 instances to be substantiated.

### Domain examples at a glance

| Domain | Default | Exception | Defeater rule | Nov > 0? |
|--------|---------|-----------|---------------|----------|
| Biology | Birds fly | Penguins don't | `~flies(X) :- penguin(X)` | No |
| Legal | Minors cannot sign contracts | Emancipated minors can | `can_sign(X) :- emancipated_minor(X)` | Yes |
| Materials | Crystals are brittle | Amorphous metals aren't | `~brittle(X) :- amorphous_metal(X)` | Yes |

---

**Author**: Patrick Cooper  
**Date**: February 13, 2026  
**Project**: BLANC - Defeasible Abduction Benchmark  
**Purpose**: Make the benchmark accessible to non-experts
