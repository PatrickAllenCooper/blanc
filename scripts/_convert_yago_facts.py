"""Convert yago_full_facts theory.pkl to theory.jsonl.gz for HuggingFace upload.

The pkl is 5.5 GB; this script streams it rule-by-rule to avoid peak memory doubling.
Run on a machine with >= 12 GB free RAM, or on CURC.
"""
import gzip
import json
import pickle
import sys
from pathlib import Path

PKL_PATH = Path(r"D:\datasets\DeFAb\rules\tier3\yago_full_facts\theory.pkl")
OUT_PATH = Path(r"D:\datasets\DeFAb\rules\tier3\yago_full_facts\theory.jsonl.gz")

def rule_to_dict(rule):
    """Convert a Rule object to a serialisable dict."""
    if hasattr(rule, "to_dict"):
        return rule.to_dict()
    # Fallback: use __dict__ or repr
    d = {}
    if hasattr(rule, "__dict__"):
        for k, v in rule.__dict__.items():
            try:
                json.dumps(v)
                d[k] = v
            except (TypeError, ValueError):
                d[k] = str(v)
    else:
        d["repr"] = repr(rule)
    return d

def main():
    print(f"Loading {PKL_PATH} ({PKL_PATH.stat().st_size / 1e9:.1f} GB)...")
    with open(PKL_PATH, "rb") as f:
        theory = pickle.load(f)

    # Theory may be a Theory object or a list/dict
    if hasattr(theory, "rules"):
        rules = theory.rules
    elif isinstance(theory, (list, tuple)):
        rules = theory
    elif isinstance(theory, dict):
        rules = theory.get("rules", list(theory.values()))
    else:
        print(f"Unknown theory type: {type(theory)}", file=sys.stderr)
        sys.exit(1)

    print(f"Writing {len(rules)} rules to {OUT_PATH}...")
    n = 0
    with gzip.open(OUT_PATH, "wt", encoding="utf-8") as gz:
        for rule in rules:
            gz.write(json.dumps(rule_to_dict(rule)) + "\n")
            n += 1
            if n % 100_000 == 0:
                print(f"  {n:,} rules written...")
    print(f"Done. {n:,} rules -> {OUT_PATH} ({OUT_PATH.stat().st_size / 1e9:.2f} GB)")

if __name__ == "__main__":
    main()
