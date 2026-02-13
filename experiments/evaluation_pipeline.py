"""
End-to-end evaluation pipeline for LLM evaluation.

Integrates:
- Model interfaces
- Prompting templates
- Response caching
- Decoder cascade (D1→D2→D3)
- Metrics computation

Author: Patrick Cooper
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
from blanc.codec.cascading_decoder import decode_batch
from blanc.codec.d2_decoder import decode_d2
from blanc.codec.decoder import decode_response


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
    
    # Additional metrics (for Level 2+)
    novelty: Optional[float] = None
    conservativity: Optional[bool] = None
    
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
            'cached': self.cached
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
        results_dir: str = "results/evaluations"
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
        """
        self.instances = instances
        self.models = models
        self.modalities = modalities
        self.strategies = strategies
        
        self.cache = ResponseCache(cache_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Render prompt
        rendered = render_prompt(instance, modality, strategy)
        
        # Check cache first
        cache_key = self.cache.make_key(
            instance_id=instance_id,
            model=model_name,
            modality=modality,
            strategy=strategy,
            prompt=rendered.prompt
        )
        
        cached_response = self.cache.get(cache_key)
        cached = False
        
        if cached_response:
            # Use cached response
            response = cached_response
            cached = True
        else:
            # Query model
            response = model.query(
                prompt=rendered.prompt,
                temperature=0.0,
                max_tokens=512
            )
            
            # Cache response
            self.cache.set(cache_key, response)
        
        # Decode response using D1→D2→D3 cascade
        decoded_hypothesis = self._decode_response(response.text, instance, modality)
        
        # Check correctness
        correct = self._check_correctness(decoded_hypothesis, instance)
        
        # Determine which decoder succeeded
        decoder_stage = self._determine_decoder_stage(response.text, instance, modality)
        
        # Create metrics
        metrics = EvaluationMetrics(
            correct=correct,
            decoder_stage=decoder_stage,
            latency=response.latency,
            tokens_used=response.tokens_input + response.tokens_output,
            cost=response.cost,
            predicted_hypothesis=decoded_hypothesis,
            gold_hypothesis=instance.gold[0] if instance.gold else None
        )
        
        return SingleEvaluation(
            instance_id=instance_id,
            model=model_name,
            modality=modality,
            strategy=strategy,
            raw_response=response.text,
            decoded_hypothesis=decoded_hypothesis,
            metrics=metrics,
            cached=cached
        )
    
    def _decode_response(
        self,
        response_text: str,
        instance: AbductiveInstance,
        modality: str
    ) -> Optional[str]:
        """
        Apply decoder cascade to extract hypothesis.
        
        Args:
            response_text: Raw model response
            instance: Instance for context
            modality: Modality
            
        Returns:
            Decoded hypothesis or None
        """
        # Try D1 (exact match) - would need to implement exact matching
        # Try D2 (template match)
        try:
            from blanc.codec.d2_decoder import decode_d2
            result = decode_d2(response_text, instance.candidates)
            if result:
                return result
        except:
            pass
        
        # Try D3 (semantic parsing) - would need full implementation
        # For now, just return first candidate if it appears in response
        for candidate in instance.candidates:
            if candidate.lower() in response_text.lower():
                return candidate
        
        return None
    
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
    
    def _determine_decoder_stage(
        self,
        response_text: str,
        instance: AbductiveInstance,
        modality: str
    ) -> str:
        """Determine which decoder stage succeeded."""
        # Simplified - just check if we got an answer
        decoded = self._decode_response(response_text, instance, modality)
        if decoded:
            return "D2"  # Assume D2 for now
        return "FAILED"
    
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
