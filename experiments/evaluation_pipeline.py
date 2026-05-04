"""
End-to-end evaluation pipeline for LLM evaluation.

Integrates:
- Model interfaces
- Prompting templates
- Response caching
- Decoder cascade (D1→D2→D3)
- Metrics computation

Author: Anonymous Authors
Date: 2026-02-13
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from model_interface import ModelInterface, ModelResponse
from prompting import render_prompt, RenderedPrompt
from response_cache import ResponseCache

from blanc.author.generation import AbductiveInstance
from blanc.codec.cascading_decoder import CascadingDecoder, decode_batch
from blanc.codec.d2_decoder import decode_d2
from blanc.codec.decoder import decode_response
from level3_evaluator import Level3Evaluator, Level3EvalResult


@dataclass
class EvaluationMetrics:
    """Metrics for a single evaluation."""
    
    # Binary accuracy
    correct: bool
    
    # Decoder used
    decoder_stage: str  # 'D1', 'D2', 'D3', 'FAILED'
    
    # Response quality
    latency: float
    tokens_used: int
    cost: float
    
    # Level 3 formal metrics
    novelty: Optional[float] = None           # Nov(predicted, D^-)
    conservativity: Optional[bool] = None     # is_conservative
    resolves_anomaly: Optional[bool] = None   # predicted rule resolves the anomaly
    revision_distance: Optional[int] = None   # d_rev
    graded_score: Optional[float] = None      # 0 / 0.25 / 0.5 / 0.75 / 1.0 (Section 4.6)
    resolution_strength: Optional[str] = None # weak / strong / restructuring
    is_minimal: Optional[bool] = None         # no proper sub-hypothesis also resolves
    error_class: Optional[str] = None         # E1-E5 taxonomy (Section 4.8)
    parse_success: Optional[bool] = None      # rule parse succeeded
    
    # Metadata
    predicted_hypothesis: Optional[str] = None
    gold_hypothesis: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SingleEvaluation:
    """Result of evaluating one instance-model-modality-strategy combination."""
    
    instance_id: str
    model: str
    modality: str
    strategy: str
    
    # Response
    raw_response: str
    decoded_hypothesis: Optional[str]
    
    # Metrics
    metrics: EvaluationMetrics
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cached: bool = False
    theory_size: Optional[int] = None     # |D^-| for theory size scaling analysis
    level: Optional[int] = None           # instance level (2 or 3)
    domain: Optional[str] = None          # biology / legal / materials

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON."""
        return {
            'instance_id': self.instance_id,
            'model': self.model,
            'modality': self.modality,
            'strategy': self.strategy,
            'raw_response': self.raw_response,
            'decoded_hypothesis': self.decoded_hypothesis,
            'metrics': self.metrics.to_dict(),
            'timestamp': self.timestamp,
            'cached': self.cached,
            'theory_size': self.theory_size,
            'level': self.level,
            'domain': self.domain,
        }


@dataclass
class EvaluationResults:
    """Complete evaluation results."""
    
    evaluations: List[SingleEvaluation]
    summary: Dict[str, Any]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON."""
        return {
            'evaluations': [e.to_dict() for e in self.evaluations],
            'summary': self.summary
        }
    
    def save(self, filepath: str):
        """Save results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'EvaluationResults':
        """Load results from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Note: Would need to reconstruct objects properly
        # For now, just return the raw data
        return data


class EvaluationPipeline:
    """End-to-end evaluation pipeline."""
    
    def __init__(
        self,
        instances: List[AbductiveInstance],
        models: Dict[str, ModelInterface],
        modalities: List[str] = ['M4', 'M2'],
        strategies: List[str] = ['direct'],
        cache_dir: str = "cache/responses",
        results_dir: str = "results/evaluations",
        manifest=None,
        m5_variant: str = 'replace',
    ):
        """
        Initialize evaluation pipeline.
        
        Args:
            instances: List of abductive instances to evaluate
            models: Dictionary mapping model names to ModelInterface objects
            modalities: List of modalities to test (default: M4, M2)
            strategies: List of prompting strategies (default: direct)
            cache_dir: Directory for response cache
            results_dir: Directory for evaluation results
            manifest: ImageManifest for M5 modality (optional)
            m5_variant: 'replace' or 'supplement' for M5 (default: replace)
        """
        self.instances = instances
        self.models = models
        self.modalities = modalities
        self.strategies = strategies
        self.manifest = manifest
        self.m5_variant = m5_variant
        
        self.cache = ResponseCache(cache_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._cascade_decoder = CascadingDecoder()
        self._level3_evaluator = Level3Evaluator()
        self.evaluations: List[SingleEvaluation] = []
    
    def run(
        self,
        save_every: int = 50,
        checkpoint_file: Optional[str] = None
    ) -> EvaluationResults:
        """
        Run complete evaluation.
        
        Args:
            save_every: Save checkpoint every N evaluations
            checkpoint_file: Path to checkpoint file (for resume)
            
        Returns:
            EvaluationResults object
        """
        print("Starting Evaluation Pipeline")
        print("=" * 70)
        print(f"Instances: {len(self.instances)}")
        print(f"Models: {list(self.models.keys())}")
        print(f"Modalities: {self.modalities}")
        print(f"Strategies: {self.strategies}")
        
        # Calculate total evaluations
        total = len(self.instances) * len(self.models) * len(self.modalities) * len(self.strategies)
        print(f"Total evaluations: {total}")
        print("=" * 70)
        
        # Progress bar
        pbar = tqdm(total=total, desc="Evaluating")
        
        evaluation_count = 0
        
        # Iterate through all combinations
        for instance in self.instances:
            for model_name, model in self.models.items():
                for modality in self.modalities:
                    for strategy in self.strategies:
                        try:
                            # Evaluate this combination
                            result = self.evaluate_single(
                                instance=instance,
                                model=model,
                                model_name=model_name,
                                modality=modality,
                                strategy=strategy
                            )
                            
                            self.evaluations.append(result)
                            evaluation_count += 1
                            
                            # Save checkpoint
                            if checkpoint_file and evaluation_count % save_every == 0:
                                self._save_checkpoint(checkpoint_file)
                            
                        except Exception as e:
                            print(f"\nError evaluating {instance.id if hasattr(instance, 'id') else 'unknown'} "
                                  f"with {model_name}/{modality}/{strategy}: {e}")
                            # Continue with next evaluation
                        
                        pbar.update(1)
        
        pbar.close()
        
        # Compute summary statistics
        summary = self._compute_summary()
        
        results = EvaluationResults(
            evaluations=self.evaluations,
            summary=summary
        )
        
        return results
    
    def evaluate_single(
        self,
        instance: AbductiveInstance,
        model: ModelInterface,
        model_name: str,
        modality: str,
        strategy: str
    ) -> SingleEvaluation:
        """
        Evaluate a single instance-model-modality-strategy combination.
        
        Args:
            instance: Abductive instance
            model: Model interface
            model_name: Model name
            modality: Modality (M1-M4)
            strategy: Prompting strategy
            
        Returns:
            SingleEvaluation result
        """
        # Get instance ID
        instance_id = getattr(instance, 'id', 'unknown')
        
        # Render prompt (M5 requires self.manifest)
        m5_kwargs = {}
        if modality.upper() == 'M5':
            m5_kwargs['manifest'] = getattr(self, 'manifest', None)
            m5_kwargs['m5_variant'] = getattr(self, 'm5_variant', 'replace')
        rendered = render_prompt(instance, modality, strategy, **m5_kwargs)

        # Compute token budget before cache key so it is part of the key.
        # Reasoning models need larger budgets for internal chain-of-thought.
        model_name_lower = model.model_name.lower()
        is_deepseek = "deepseek-r1" in model_name_lower or "r1-distill" in model_name_lower
        is_kimi     = "kimi" in model_name_lower
        if is_deepseek:
            max_tokens = 8192
        elif is_kimi:
            max_tokens = 4096
        else:
            max_tokens = 512

        # Build cache key -- include image hashes for M5 and generation params
        img_hashes = None
        if rendered.images:
            import hashlib as _hl
            img_hashes = [
                _hl.sha256(img.local_path.encode()).hexdigest()[:16]
                for img in rendered.images
                if img.local_path
            ]
        cache_key = self.cache.make_key(
            instance_id=instance_id,
            model=model_name,
            modality=modality,
            strategy=strategy,
            prompt=rendered.prompt,
            image_hashes=img_hashes,
            max_tokens=max_tokens,
        )
        
        cached_response = self.cache.get(cache_key)
        cached = False
        
        if cached_response and cached_response.text.strip():
            response = cached_response
            cached = True
        else:

            if rendered.images:
                response = model.query_multimodal(
                    prompt=rendered.prompt,
                    images=rendered.images,
                    temperature=0.0,
                    max_tokens=max_tokens,
                )
            else:
                response = model.query(
                    prompt=rendered.prompt,
                    temperature=0.0,
                    max_tokens=max_tokens,
                )
            
            # Cache response
            self.cache.set(cache_key, response)
        
        # Decode response using D1→D2→D3 cascade (single pass)
        decoded_hypothesis, decoder_stage = self._decode_response(response.text, instance)

        # Check correctness
        correct = self._check_correctness(decoded_hypothesis, instance)
        
        # Level 3 formal metrics
        l3_result: Optional[Level3EvalResult] = None
        if getattr(instance, 'level', 2) == 3:
            l3_result = self._level3_evaluator.evaluate(
                instance, response.text, decoded_hypothesis
            )
            # Reconcile correct: use exact match OR (resolves + conservative)
            if l3_result.resolves_anomaly and l3_result.is_conservative:
                correct = True

        metrics = EvaluationMetrics(
            correct=correct,
            decoder_stage=decoder_stage or "FAILED",
            latency=response.latency,
            tokens_used=response.tokens_input + response.tokens_output,
            cost=response.cost,
            predicted_hypothesis=decoded_hypothesis,
            gold_hypothesis=instance.gold[0] if instance.gold else None,
            novelty=l3_result.nov if l3_result else None,
            conservativity=l3_result.is_conservative if l3_result else None,
            resolves_anomaly=l3_result.resolves_anomaly if l3_result else None,
            revision_distance=l3_result.d_rev if l3_result else None,
            graded_score=l3_result.graded_score if l3_result else None,
            resolution_strength=l3_result.resolution_strength if l3_result else None,
            is_minimal=l3_result.is_minimal if l3_result else None,
            error_class=l3_result.error_class if l3_result else None,
            parse_success=l3_result.parse_success if l3_result else None,
        )
        
        return SingleEvaluation(
            instance_id=instance_id,
            model=model_name,
            modality=modality,
            strategy=strategy,
            raw_response=response.text,
            decoded_hypothesis=decoded_hypothesis,
            metrics=metrics,
            cached=cached,
            theory_size=(
                len(instance.D_minus.facts) + len(instance.D_minus.rules)
                if hasattr(instance, "D_minus") and instance.D_minus else None
            ),
            level=getattr(instance, "level", None),
            domain=instance.metadata.get("domain") if instance.metadata else None,
        )
    
    @staticmethod
    def _extract_cot_answer(text: str) -> str:
        """
        Extract the hypothesis from a CoT response.

        The CoT prompt instructs models to end their response with:
            FINAL ANSWER: <hypothesis text>

        Models may format this with markdown bold, numbered lists, or put the
        answer on the following line.  We handle all observed variants:
            FINAL ANSWER: hypothesis
            **FINAL ANSWER:** hypothesis
            **FINAL ANSWER:**\\n**1. hypothesis**
            FINAL ANSWER:\\nhypothesis

        When the pattern is absent, fall through to the original full text
        so D2/D3 still have a chance to find something.
        """
        import re

        # Strip markdown bold markers, backticks, and leading list numbers
        # from a candidate answer string.
        def _clean(s: str) -> str:
            s = re.sub(r"\*+", "", s)          # remove ** bold markers
            s = re.sub(r"`", "", s)             # remove backticks
            s = re.sub(r"^\s*\d+\.\s*", "", s) # remove leading "1. "
            return s.strip()

        # Primary pattern: "FINAL ANSWER" (with optional markdown) anywhere
        # in the text, followed by the answer on the same or the next line.
        pattern = re.compile(
            r"FINAL\s*ANSWER\s*[:\*]*\s*\n?\s*(.+)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            answer = _clean(match.group(1))
            if answer:
                return answer

        # Fallback: last non-empty, non-heading line — models sometimes omit
        # the prefix but still put the answer as the final line.
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if lines:
            # Skip lines that look like markdown headings or step labels.
            for line in reversed(lines):
                if not re.match(r"^#+\s|^Step\s\d|^---", line):
                    return _clean(line)

        return text

    def _decode_response(
        self,
        response_text: str,
        instance: AbductiveInstance,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Apply D1→D2→D3 cascade decoder and return (hypothesis, stage_name).

        For CoT responses the model is instructed to place its answer after
        'FINAL ANSWER:'.  We extract that fragment first so the exact-match
        decoder (D1) can succeed without seeing the full reasoning chain.

        Returns:
            (decoded_hypothesis, stage) where stage is 'D1', 'D2', 'D3', or
            None when all stages fail.
        """
        # Pre-process: pull the answer out of a CoT response if present.
        text_to_decode = self._extract_cot_answer(response_text)
        decoded, stage = self._cascade_decoder.decode(text_to_decode, instance.candidates)

        # If extraction narrowed the text too much and the cascade failed,
        # retry on the full response (D2/D3 may still find something).
        if decoded is None and text_to_decode != response_text:
            decoded, stage = self._cascade_decoder.decode(response_text, instance.candidates)

        return decoded, stage

    def _check_correctness(
        self,
        predicted: Optional[str],
        instance: AbductiveInstance
    ) -> bool:
        """Check if prediction matches gold hypothesis."""
        if not predicted or not instance.gold:
            return False
        
        # Simple string matching (could be more sophisticated)
        return predicted.strip() in [g.strip() for g in instance.gold]
    
    def _compute_summary(self) -> dict:
        """Compute summary statistics across all evaluations."""
        if not self.evaluations:
            return {}
        
        total = len(self.evaluations)
        correct = sum(1 for e in self.evaluations if e.metrics.correct)
        
        total_cost = sum(e.metrics.cost for e in self.evaluations)
        total_latency = sum(e.metrics.latency for e in self.evaluations)
        
        # Decoder distribution
        decoder_counts = {}
        for e in self.evaluations:
            stage = e.metrics.decoder_stage
            decoder_counts[stage] = decoder_counts.get(stage, 0) + 1
        
        # Cache hit rate
        cached_count = sum(1 for e in self.evaluations if e.cached)
        
        return {
            'total_evaluations': total,
            'accuracy': correct / total if total > 0 else 0.0,
            'total_cost': total_cost,
            'avg_cost_per_eval': total_cost / total if total > 0 else 0.0,
            'total_latency': total_latency,
            'avg_latency': total_latency / total if total > 0 else 0.0,
            'decoder_distribution': decoder_counts,
            'cache_hit_rate': cached_count / total if total > 0 else 0.0,
            'cache_statistics': self.cache.get_statistics()
        }
    
    def _save_checkpoint(self, filepath: str):
        """Save checkpoint for resume."""
        results = EvaluationResults(
            evaluations=self.evaluations,
            summary=self._compute_summary()
        )
        results.save(filepath)


if __name__ == "__main__":
    # Quick test with mock data
    from model_interface import MockModelInterface
    from blanc.core.theory import Theory, Rule, RuleType
    
    print("Evaluation Pipeline Test")
    print("=" * 70)
    
    # Create mock instance
    theory = Theory()
    theory.add_rule(Rule("bird(tweety)", (), RuleType.FACT, "f1"))
    
    instance = AbductiveInstance(
        D_minus=theory,
        target="flies(tweety)",
        candidates=["flies(tweety)", "bird(tweety)"],
        gold=["flies(tweety)"],
        level=1
    )
    instance.id = "test-001"
    
    # Create mock model
    mock_model = MockModelInterface("mock-gpt")
    mock_model.set_responses(["The answer is: flies(tweety)"])
    
    # Create pipeline
    pipeline = EvaluationPipeline(
        instances=[instance],
        models={'mock-gpt': mock_model},
        modalities=['M4'],
        strategies=['direct']
    )
    
    # Run evaluation
    results = pipeline.run()
    
    # Show results
    print("\nResults:")
    print(f"  Total: {results.summary['total_evaluations']}")
    print(f"  Accuracy: {results.summary['accuracy']:.1%}")
    print(f"  Cost: ${results.summary['total_cost']:.4f}")
    
    print("\n✅ Evaluation pipeline working!")
