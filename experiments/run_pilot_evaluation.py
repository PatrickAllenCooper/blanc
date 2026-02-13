"""
Pilot evaluation script - ready to run when API keys are available.

Runs evaluation on 20 instances with 2 models to validate pipeline.

Usage:
    python run_pilot_evaluation.py

Requires:
    - OpenAI API key in .env as OPENAI_API_KEY
    - Anthropic API key in .env as ANTHROPIC_API_KEY

Expected cost: $2-5
Expected time: 5-10 minutes

Author: Patrick Cooper
Date: 2026-02-13
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from model_interface import create_model_interface
from evaluation_pipeline import EvaluationPipeline
from blanc.author.generation import AbductiveInstance


def load_instances(domain: str, limit: int = 10) -> list:
    """Load instances from JSON file."""
    filepath = Path(f"instances/{domain}_dev_instances.json")
    
    if not filepath.exists():
        print(f"Warning: {filepath} not found, skipping {domain}")
        return []
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Convert to AbductiveInstance objects
    instances = []
    for i, item in enumerate(data[:limit]):
        # Create instance from JSON data
        # (This is simplified - real implementation would use proper deserialization)
        instance = AbductiveInstance(
            D_minus=item.get('D_minus'),
            target=item.get('target'),
            candidates=item.get('candidates', []),
            gold=item.get('gold', []),
            level=item.get('level', 2)
        )
        instance.id = item.get('id', f'{domain}-{i:03d}')
        instances.append(instance)
    
    return instances


def main():
    """Run pilot evaluation."""
    print("=" * 70)
    print("PILOT EVALUATION - Week 8")
    print("=" * 70)
    
    # Load environment variables
    load_dotenv()
    
    # Check for API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        print("   Please add your API key to .env and try again")
        return 1
    
    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not found in .env file")
        print("   Please add your API key to .env and try again")
        return 1
    
    print("✓ API keys loaded")
    
    # Load instances
    print("\nLoading instances...")
    biology_instances = load_instances('biology', limit=7)
    legal_instances = load_instances('legal', limit=7)
    materials_instances = load_instances('materials', limit=6)
    
    all_instances = biology_instances + legal_instances + materials_instances
    
    print(f"  Biology: {len(biology_instances)} instances")
    print(f"  Legal: {len(legal_instances)} instances")
    print(f"  Materials: {len(materials_instances)} instances")
    print(f"  Total: {len(all_instances)} instances")
    
    if len(all_instances) == 0:
        print("\n❌ No instances loaded. Please check instance files exist.")
        return 1
    
    # Create models
    print("\nInitializing models...")
    try:
        models = {
            'gpt-4o': create_model_interface('openai', api_key=openai_key, model='gpt-4o'),
            'claude-3.5-sonnet': create_model_interface('anthropic', api_key=anthropic_key)
        }
        print("  ✓ GPT-4o initialized")
        print("  ✓ Claude 3.5 Sonnet initialized")
    except Exception as e:
        print(f"\n❌ Error initializing models: {e}")
        return 1
    
    # Configure evaluation
    modalities = ['M4', 'M2']  # Pure formal and semi-formal
    strategies = ['direct']     # Just direct for pilot
    
    print("\nConfiguration:")
    print(f"  Models: {list(models.keys())}")
    print(f"  Modalities: {modalities}")
    print(f"  Strategies: {strategies}")
    print(f"  Total queries: {len(all_instances)} × {len(models)} × {len(modalities)} × {len(strategies)} = {len(all_instances) * len(models) * len(modalities) * len(strategies)}")
    
    # Create pipeline
    print("\nCreating evaluation pipeline...")
    pipeline = EvaluationPipeline(
        instances=all_instances,
        models=models,
        modalities=modalities,
        strategies=strategies,
        cache_dir="cache/responses",
        results_dir="results/evaluations"
    )
    
    # Run evaluation
    print("\n" + "=" * 70)
    print("Running evaluation...")
    print("=" * 70)
    
    try:
        results = pipeline.run(
            save_every=20,
            checkpoint_file="results/evaluations/pilot_checkpoint.json"
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted by user")
        print("   Progress has been saved to checkpoint")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display results
    print("\n" + "=" * 70)
    print("PILOT EVALUATION RESULTS")
    print("=" * 70)
    
    summary = results.summary
    
    print(f"\nOverall Performance:")
    print(f"  Total evaluations: {summary['total_evaluations']}")
    print(f"  Accuracy: {summary['accuracy']:.1%}")
    print(f"  Total cost: ${summary['total_cost']:.4f}")
    print(f"  Avg cost per eval: ${summary['avg_cost_per_eval']:.4f}")
    print(f"  Total time: {summary['total_latency']:.1f}s")
    print(f"  Avg latency: {summary['avg_latency']:.2f}s")
    
    print(f"\nDecoder Distribution:")
    for decoder, count in summary['decoder_distribution'].items():
        pct = (count / summary['total_evaluations']) * 100
        print(f"  {decoder}: {count} ({pct:.1f}%)")
    
    print(f"\nCache Performance:")
    print(f"  Hit rate: {summary['cache_hit_rate']:.1%}")
    cache_stats = summary['cache_statistics']
    print(f"  Cost saved: {cache_stats['cost_saved']}")
    print(f"  Time saved: {cache_stats['time_saved']}")
    
    # Save results
    output_file = "results/evaluations/pilot_evaluation_results.json"
    results.save(output_file)
    print(f"\nResults saved to: {output_file}")
    
    # Cost projection for full evaluation
    print("\n" + "=" * 70)
    print("COST PROJECTION FOR FULL EVALUATION")
    print("=" * 70)
    
    avg_cost = summary['avg_cost_per_eval']
    full_instances = 374
    full_models = 5  # GPT-4o, Claude, Gemini, Llama 70B, Llama 8B
    full_modalities = 4  # M1, M2, M3, M4
    full_strategies = 2  # direct, cot
    
    full_queries = full_instances * full_models * full_modalities * full_strategies
    projected_cost = full_queries * avg_cost
    
    print(f"\nFull evaluation projection:")
    print(f"  Total queries: {full_queries:,}")
    print(f"  Projected cost: ${projected_cost:.2f}")
    print(f"  (Based on avg ${avg_cost:.4f} per query from pilot)")
    
    print("\n" + "=" * 70)
    print("✅ PILOT EVALUATION COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
