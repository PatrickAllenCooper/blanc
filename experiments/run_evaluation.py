"""
CLI entry point for the DeFAb evaluation pipeline.

Supports all providers (openai, azure, anthropic, google, ollama, mock) and
all instance levels (Level 2 dev set + Level 3 defeater set).

Usage examples:

    # Azure OpenAI (CURC)
    python experiments/run_evaluation.py \\
        --provider azure \\
        --endpoint https://<resource>.openai.azure.com \\
        --api-key $AZURE_OPENAI_API_KEY \\
        --deployment gpt-4o \\
        --modalities M4 M2 \\
        --strategies direct cot \\
        --include-level3

    # CURC vLLM (Qwen 2.5 72B or Llama 3.3 70B via CURC LLM Hoster)
    # Assumes vLLM server running; access via SSH tunnel on port 8000
    python experiments/run_evaluation.py \\
        --provider curc \\
        --model Qwen/Qwen2.5-72B-Instruct-AWQ \\
        --curc-base-url http://localhost:8000 \\
        --modalities M4 M2 \\
        --strategies direct cot \\
        --include-level3

    # Ollama (local Llama 3, legacy)
    python experiments/run_evaluation.py \\
        --provider ollama \\
        --model llama3:70b \\
        --modalities M4 \\
        --strategies direct

    # Dry run with mock model
    python experiments/run_evaluation.py --provider mock --instance-limit 5

Author: Patrick Cooper
Date: 2026-02-18
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

# Load .env from the project root so FOUNDRY_API_KEY and other credentials
# are available when the script is invoked directly (not via the local runners).
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from model_interface import create_model_interface
from evaluation_pipeline import EvaluationPipeline


# ---------------------------------------------------------------------------
# Instance loading
# ---------------------------------------------------------------------------

def _load_level2_instances(domain: str, limit: int, instances_dir: Path) -> list[AbductiveInstance]:
    """Load Level 2 (rule abduction) instances from a JSON file."""
    path = instances_dir / f"{domain}_dev_instances.json"
    if not path.exists():
        print(f"  Warning: {path} not found, skipping {domain} Level 2.")
        return []

    with open(path) as f:
        data = json.load(f)

    instances = []
    for i, item in enumerate(data["instances"][:limit]):
        # Reconstruct a placeholder Theory (the pipeline uses it for prompt
        # rendering via the encoder; the stored 'target' and 'candidates' are
        # what drive the evaluation).
        D_minus = _build_placeholder_theory(item)

        inst = AbductiveInstance(
            D_minus=D_minus,
            target=item.get("target", ""),
            candidates=item.get("candidates", []),
            gold=item.get("gold", []),
            level=item.get("level", 2),
            metadata=item.get("metadata", {}),
        )
        inst.id = item.get("metadata", {}).get("instance_id", f"{domain}-l2-{i+1:04d}")
        instances.append(inst)

    return instances


def _load_level3_instances(limit: int, instances_dir: Path) -> list[AbductiveInstance]:
    """Load Level 3 (defeater abduction) instances from level3_instances.json."""
    path = instances_dir / "level3_instances.json"
    if not path.exists():
        print(f"  Warning: {path} not found, skipping Level 3.")
        return []

    with open(path) as f:
        data = json.load(f)

    instances = []
    for item in data["instances"][:limit]:
        D_minus = _reconstruct_theory_from_level3(item)

        inst = AbductiveInstance(
            D_minus=D_minus,
            target=item["anomaly"],
            candidates=item["candidates"],
            gold=[item["gold"]],
            level=3,
            metadata={
                "domain":        item.get("domain", ""),
                "nov":           item.get("nov", 0.0),
                "d_rev":         item.get("d_rev", 1),
                "conservative":  item.get("conservative", True),
            },
        )
        inst.id = f"l3-{item['name']}"
        instances.append(inst)

    return instances


def _build_placeholder_theory(item: dict) -> Theory:
    """
    Create a minimal Theory from the metadata stored in a Level 2 JSON record.
    The pipeline encodes this theory for the prompt; any structure is sufficient.
    """
    meta = item.get("metadata", {})
    facts = meta.get("facts", [])
    rules_raw = meta.get("rules", [])
    rules = []
    for r in rules_raw:
        if isinstance(r, dict):
            rules.append(Rule(
                head=r.get("head", ""),
                body=tuple(r.get("body", [])),
                rule_type=RuleType(r.get("rule_type", "defeasible")),
                label=r.get("label"),
            ))
    return Theory(facts=facts, rules=rules, superiority=[])


def _reconstruct_theory_from_level3(item: dict) -> Theory:
    """Reconstruct Theory from the theory_facts / theory_rules fields in a Level 3 record."""
    facts = list(item.get("theory_facts", []))
    rules: list[Rule] = []

    for rule_str in item.get("theory_rules", []):
        if ":" in rule_str:
            label, rest = rule_str.split(":", 1)
            label, rest = label.strip(), rest.strip()
        else:
            label, rest = None, rule_str.strip()

        if "~>" in rest:
            body_part, head_part = rest.split("~>", 1)
            rule_type = RuleType.DEFEATER
        elif "=>" in rest:
            body_part, head_part = rest.split("=>", 1)
            rule_type = RuleType.DEFEASIBLE
        elif ":-" in rest:
            body_part, head_part = rest.split(":-", 1)
            rule_type = RuleType.STRICT
        else:
            rules.append(Rule(head=rest.strip(), body=(), rule_type=RuleType.STRICT, label=label))
            continue

        body_atoms = tuple(b.strip() for b in body_part.split(",") if b.strip())
        rules.append(Rule(head=head_part.strip(), body=body_atoms, rule_type=rule_type, label=label))

    return Theory(facts=facts, rules=rules, superiority=[])


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DeFAb evaluation pipeline CLI")

    # Provider / credentials
    p.add_argument("--provider", required=True,
                   choices=[
                       "openai", "azure", "curc", "anthropic", "google", "ollama",
                       "foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek",
                       "mock",
                   ],
                   help="Model provider.")
    p.add_argument("--api-key", default=None,
                   help="API key. For Foundry providers, falls back to FOUNDRY_API_KEY env var.")
    p.add_argument("--model", default=None, help="Model or deployment name.")
    p.add_argument("--endpoint", default=None,
                   help="Azure / Foundry: resource endpoint URL.")
    p.add_argument("--deployment", default=None, help="Azure: deployment name in AI Studio.")
    p.add_argument("--api-version", default="2024-08-01-preview",
                   help="Azure: REST API version.")
    p.add_argument("--ollama-host", default="http://localhost:11434",
                   help="Ollama: server URL.")
    p.add_argument("--curc-base-url", default="http://localhost:8000",
                   help="CURC vLLM server base URL (default via SSH tunnel: http://localhost:8000).")
    p.add_argument("--foundry-base-url", default=None,
                   help="Foundry-Kimi: override base_url (default: Foundry endpoint).")

    # Evaluation config
    p.add_argument("--modalities", nargs="+", default=["M4"],
                   help="Encoding modalities to evaluate (M1-M4).")
    p.add_argument("--strategies", nargs="+", default=["direct"],
                   help="Prompting strategies (direct, cot).")
    p.add_argument("--instance-limit", type=int, default=50,
                   help="Max instances per domain.")
    p.add_argument("--include-level3", action="store_true",
                   help="Include Level 3 (defeater abduction) instances.")
    p.add_argument("--level3-limit", type=int, default=33,
                   help="Max Level 3 instances.")

    # Paths
    p.add_argument("--instances-dir", default=str(ROOT / "instances"),
                   help="Directory containing instance JSON files.")
    p.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"),
                   help="Directory for output files.")
    p.add_argument("--cache-dir", default=str(ROOT / "experiments" / "cache"),
                   help="Directory for response cache.")
    p.add_argument("--checkpoint", default=None,
                   help="Path to save/resume checkpoint.")

    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb Evaluation Pipeline")
    print("=" * 70)
    print(f"Provider  : {args.provider}")
    print(f"Model     : {args.model or '(default)'}")
    print(f"Modalities: {args.modalities}")
    print(f"Strategies: {args.strategies}")
    print()

    # ---------------------------------------------------------------------------
    # Build model interface
    # ---------------------------------------------------------------------------
    kwargs: dict = {}
    api_key = args.api_key

    if args.provider == "azure":
        kwargs["endpoint"] = args.endpoint
        kwargs["deployment_name"] = args.deployment
        kwargs["api_version"] = args.api_version
        if not all([api_key, args.endpoint, args.deployment]):
            print("ERROR: Azure requires --api-key, --endpoint, and --deployment.")
            return 1

    elif args.provider == "curc":
        kwargs["base_url"] = args.curc_base_url
        print(f"CURC vLLM URL : {args.curc_base_url}")

    elif args.provider == "ollama":
        kwargs["host"] = args.ollama_host

    elif args.provider in ("foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek"):
        # Fall back to FOUNDRY_API_KEY env var when --api-key is not given
        if not api_key:
            api_key = os.environ.get("FOUNDRY_API_KEY", "")
        if not api_key:
            print("ERROR: Foundry providers require --api-key or FOUNDRY_API_KEY env var.")
            return 1

        if args.provider == "foundry-gpt":
            if args.endpoint:
                kwargs["endpoint"] = args.endpoint
            if args.api_version != "2024-08-01-preview":
                kwargs["api_version"] = args.api_version
        elif args.provider == "foundry-kimi":
            if args.foundry_base_url:
                kwargs["base_url"] = args.foundry_base_url
        elif args.provider == "foundry-claude":
            if args.endpoint:
                kwargs["endpoint"] = args.endpoint

        print(f"Foundry provider : {args.provider}")

    try:
        interface = create_model_interface(
            provider=args.provider,
            api_key=api_key,
            model=args.model,
            **kwargs,
        )
        print(f"Model interface initialised: {interface.model_name}")
    except Exception as e:
        print(f"ERROR: Could not initialise model interface: {e}")
        return 1

    # ---------------------------------------------------------------------------
    # Load instances
    # ---------------------------------------------------------------------------
    instances_dir = Path(args.instances_dir)
    all_instances: list[AbductiveInstance] = []

    print("\nLoading instances...")
    for domain in ["biology", "legal", "materials"]:
        domain_inst = _load_level2_instances(domain, args.instance_limit, instances_dir)
        print(f"  {domain:10s} Level 2: {len(domain_inst)} instances")
        all_instances.extend(domain_inst)

    if args.include_level3:
        l3 = _load_level3_instances(args.level3_limit, instances_dir)
        print(f"  {'level3':10s} Level 3: {len(l3)} instances")
        all_instances.extend(l3)

    print(f"  Total: {len(all_instances)} instances")

    if not all_instances:
        print("\nERROR: No instances loaded. Check --instances-dir path.")
        return 1

    # ---------------------------------------------------------------------------
    # Run pipeline
    # ---------------------------------------------------------------------------
    pipeline = EvaluationPipeline(
        instances=all_instances,
        models={interface.model_name: interface},
        modalities=args.modalities,
        strategies=args.strategies,
        cache_dir=args.cache_dir,
        results_dir=args.results_dir,
    )

    results = pipeline.run(checkpoint_file=args.checkpoint)

    # ---------------------------------------------------------------------------
    # Save and report
    # ---------------------------------------------------------------------------
    out_path = Path(args.results_dir) / f"results_{args.provider}.json"
    results.save(str(out_path))
    print(f"\nResults saved to: {out_path}")

    summary = results.summary
    print("\nSummary:")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k:<40} {v:.4f}")
        else:
            print(f"  {k:<40} {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
