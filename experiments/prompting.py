"""
Prompting infrastructure for LLM evaluation.

Provides:
- Direct prompting templates
- Chain-of-Thought (CoT) prompting templates  
- Modality-specific rendering (M1-M4)
- Integration with existing encoders

Author: Patrick Cooper
Date: 2026-02-13
"""

from typing import List, Optional, Dict
from dataclasses import dataclass

# Import our existing encoders
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blanc.author.generation import AbductiveInstance
from blanc.codec.m1_encoder import encode_m1_theory
from blanc.codec.m2_encoder import encode_m2_theory
from blanc.codec.m3_encoder import encode_m3_theory
from blanc.codec.encoder import PureFormalEncoder


# Prompt Templates

DIRECT_PROMPT_TEMPLATE = """You are an expert in logical reasoning and abductive inference.

You will be given:
1. A theory (knowledge base) with some elements removed
2. A target query that should be derivable
3. A set of candidate hypotheses

Your task: Select or generate the hypothesis that, when added to the theory, enables derivation of the target query.

{theory_section}

{target_section}

{candidates_section}

Output only the hypothesis that restores derivability. Do not include explanations or additional text."""


COT_PROMPT_TEMPLATE = """You are an expert in defeasible logical reasoning and abductive inference. Think step-by-step.

You will be given:
1. A theory (knowledge base) with some elements removed
2. A target query that should be derivable from the complete theory
3. A set of candidate hypotheses

{theory_section}

{target_section}

{candidates_section}

Reason through this in three steps:

Step 1 - Identify support and attackers: Which rules in the theory could derive the target query (or its negation)? Trace which rule(s) would support the target and which, if any, would block or attack it.

Step 2 - Identify the gap: What element is missing or what is blocking derivation of the target? Is a required rule absent, or is a defeater suppressing the conclusion without justification?

Step 3 - Select the hypothesis: Which candidate, when added to the theory, restores derivability of the target while leaving all other conclusions intact?

After your analysis, output only the selected hypothesis on the final line:
FINAL ANSWER: [the hypothesis that restores derivability]"""


# M1 (Narrative) specific
M1_THEORY_HEADER = "Background Knowledge (Natural Language):"
M1_TARGET_HEADER = "Observation to Explain:"
M1_CANDIDATES_HEADER = "Possible Explanations:"

# M2 (Semi-formal) specific
M2_THEORY_HEADER = "Theory (Semi-Formal Representation):"
M2_TARGET_HEADER = "Target Query:"
M2_CANDIDATES_HEADER = "Candidate Hypotheses:"

# M3 (Annotated) specific
M3_THEORY_HEADER = "Theory (Annotated Formal Logic):"
M3_TARGET_HEADER = "Target Query:"
M3_CANDIDATES_HEADER = "Candidate Hypotheses:"

# M4 (Pure formal) specific
M4_THEORY_HEADER = "Theory (Formal Logic Program):"
M4_TARGET_HEADER = "Target Query:"
M4_CANDIDATES_HEADER = "Candidate Hypotheses:"


@dataclass
class RenderedPrompt:
    """Rendered prompt ready for model querying."""
    
    prompt: str
    modality: str
    strategy: str
    instance_id: str
    metadata: Dict = None
    
    def __str__(self) -> str:
        return self.prompt


def render_prompt(
    instance: AbductiveInstance,
    modality: str,
    strategy: str = 'direct',
    domain: str = 'biology'
) -> RenderedPrompt:
    """
    Render an abductive instance into a model prompt.
    
    Args:
        instance: AbductiveInstance to render
        modality: One of 'M1', 'M2', 'M3', 'M4'
        strategy: One of 'direct', 'cot' (chain-of-thought)
        domain: Domain for NL mapping (for M1/M2)
        
    Returns:
        RenderedPrompt object
    """
    modality = modality.upper()
    strategy = strategy.lower()
    
    if modality not in ['M1', 'M2', 'M3', 'M4']:
        raise ValueError(f"Unknown modality: {modality}. Use M1, M2, M3, or M4")
    
    if strategy not in ['direct', 'cot']:
        raise ValueError(f"Unknown strategy: {strategy}. Use 'direct' or 'cot'")
    
    # Select template
    if strategy == 'direct':
        template = DIRECT_PROMPT_TEMPLATE
    else:
        template = COT_PROMPT_TEMPLATE
    
    # Encode theory in appropriate modality
    theory_text = _encode_theory(instance.D_minus, modality, domain)
    
    # Encode target
    target_text = _encode_element(instance.target, modality, domain)
    
    # Encode candidates
    candidates_text = _encode_candidates(instance.candidates, modality, domain)
    
    # Select headers based on modality
    if modality == 'M1':
        theory_header = M1_THEORY_HEADER
        target_header = M1_TARGET_HEADER
        candidates_header = M1_CANDIDATES_HEADER
    elif modality == 'M2':
        theory_header = M2_THEORY_HEADER
        target_header = M2_TARGET_HEADER
        candidates_header = M2_CANDIDATES_HEADER
    elif modality == 'M3':
        theory_header = M3_THEORY_HEADER
        target_header = M3_TARGET_HEADER
        candidates_header = M3_CANDIDATES_HEADER
    else:  # M4
        theory_header = M4_THEORY_HEADER
        target_header = M4_TARGET_HEADER
        candidates_header = M4_CANDIDATES_HEADER
    
    # Format sections
    theory_section = f"{theory_header}\n{theory_text}"
    target_section = f"{target_header}\n{target_text}"
    candidates_section = f"{candidates_header}\n{candidates_text}"
    
    # Fill template
    prompt = template.format(
        theory_section=theory_section,
        target_section=target_section,
        candidates_section=candidates_section
    )
    
    # Get instance ID if available
    instance_id = getattr(instance, 'id', 'unknown')
    
    return RenderedPrompt(
        prompt=prompt,
        modality=modality,
        strategy=strategy,
        instance_id=instance_id,
        metadata={
            'domain': domain,
            'level': instance.level,
            'num_candidates': len(instance.candidates)
        }
    )


def _encode_theory(theory, modality: str, domain: str) -> str:
    """Encode theory in specified modality."""
    if modality == 'M1':
        return encode_m1_theory(theory, domain=domain)
    elif modality == 'M2':
        return encode_m2_theory(theory, domain=domain)
    elif modality == 'M3':
        return encode_m3_theory(theory, domain=domain)
    else:  # M4
        encoder = PureFormalEncoder()
        rules_text = []
        for rule in theory.rules:
            rules_text.append(encoder.encode_rule(rule))
        return "\n".join(rules_text)


def _encode_element(element: str, modality: str, domain: str) -> str:
    """Encode a single element (fact or rule)."""
    if modality == 'M1':
        from blanc.codec.m1_encoder import encode_m1
        return encode_m1(element, domain=domain)
    elif modality == 'M2':
        from blanc.codec.m2_encoder import encode_m2
        return encode_m2(element, domain=domain)
    elif modality == 'M3':
        from blanc.codec.m3_encoder import encode_m3
        return encode_m3(element, domain=domain)
    else:  # M4
        # Candidates in M4 are already in pure formal notation; no re-encoding needed.
        return element


def _encode_candidates(candidates: List[str], modality: str, domain: str) -> str:
    """Encode candidate list."""
    encoded = []
    for i, candidate in enumerate(candidates, 1):
        encoded_candidate = _encode_element(candidate, modality, domain)
        encoded.append(f"{i}. {encoded_candidate}")
    return "\n".join(encoded)


def batch_render_prompts(
    instances: List[AbductiveInstance],
    modality: str,
    strategy: str = 'direct',
    domain: str = 'biology'
) -> List[RenderedPrompt]:
    """
    Render multiple instances at once.
    
    Args:
        instances: List of instances to render
        modality: Modality (M1-M4)
        strategy: Prompting strategy
        domain: Domain for NL mapping
        
    Returns:
        List of RenderedPrompt objects
    """
    return [
        render_prompt(instance, modality, strategy, domain)
        for instance in instances
    ]


if __name__ == "__main__":
    # Quick test with mock data
    from blanc.core.theory import Theory, Rule, RuleType
    from blanc.author.generation import AbductiveInstance
    
    print("Prompting Module Test")
    print("=" * 70)
    
    # Create simple test instance
    theory = Theory()
    theory.add_rule(Rule("bird(tweety)", (), RuleType.FACT, "f1"))
    theory.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, "r1"))
    
    instance = AbductiveInstance(
        D_minus=theory,
        target="flies(tweety)",
        candidates=[
            "bird(tweety)",  # Already in theory
            "penguin(tweety)",  # Wrong
            "injured(tweety)",  # Could work as defeater
        ],
        gold=["bird(tweety)"],
        level=1
    )
    instance.id = "test-001"
    
    # Test all modality x strategy combinations
    for modality in ['M4', 'M2']:  # Test subset
        for strategy in ['direct', 'cot']:
            print(f"\n{'='*70}")
            print(f"Modality: {modality}, Strategy: {strategy}")
            print(f"{'='*70}")
            
            rendered = render_prompt(instance, modality, strategy)
            
            # Show first 500 chars
            print(rendered.prompt[:500])
            print(f"\n... (Total length: {len(rendered.prompt)} chars)")
    
    print("\n" + "=" * 70)
    print("✅ Prompting module working!")
