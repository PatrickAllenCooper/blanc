"""Upload new/updated instance files to HuggingFace dataset."""
import os
import json
from pathlib import Path
from huggingface_hub import HfApi, HfFileSystem

REPO = "PatrickAllenCooper/DeFAb"
LOCAL_BASE = Path("instances")

# Files to upload: (local_path, hf_path)
TARGETS = [
    # Multitier instances (new -- not on HF yet)
    ("instances/multitier/framenet/instances.json",    "instances/multitier/framenet/instances.json"),
    ("instances/multitier/gene_ontology/instances.json","instances/multitier/gene_ontology/instances.json"),
    ("instances/multitier/sumo/instances.json",         "instances/multitier/sumo/instances.json"),
    ("instances/multitier/wikidata/instances.json",     "instances/multitier/wikidata/instances.json"),
    ("instances/multitier/umls/instances.json",         "instances/multitier/umls/instances.json"),
    ("instances/multitier/yago_full/instances.json",    "instances/multitier/yago_full/instances.json"),
    ("instances/multitier/babelnet/instances.json",     "instances/multitier/babelnet/instances.json"),
    # Tier1 instances (updated versions)
    ("instances/tier1/biology/instances.json",   "instances/tier1/biology/instances.json"),
    ("instances/tier1/chemistry/instances.json", "instances/tier1/chemistry/instances.json"),
    ("instances/tier1/everyday/instances.json",  "instances/tier1/everyday/instances.json"),
    ("instances/tier1/legal/instances.json",     "instances/tier1/legal/instances.json"),
    ("instances/tier1/materials/instances.json", "instances/tier1/materials/instances.json"),
]

def main():
    api = HfApi()
    for local_rel, hf_path in TARGETS:
        local = Path(local_rel)
        if not local.exists():
            print(f"SKIP (missing): {local_rel}")
            continue
        size = local.stat().st_size
        if size < 10:
            print(f"SKIP (empty {size}b): {local_rel}")
            continue
        print(f"Uploading {local_rel} ({size/1e6:.1f} MB) -> {hf_path}")
        api.upload_file(
            path_or_fileobj=str(local),
            path_in_repo=hf_path,
            repo_id=REPO,
            repo_type="dataset",
            commit_message=f"upload {hf_path}",
        )
        print(f"  done")

if __name__ == "__main__":
    main()
