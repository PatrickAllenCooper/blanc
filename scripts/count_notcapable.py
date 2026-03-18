"""Quick scan of ConceptNet NotCapableOf edges."""
import gzip
import json
from pathlib import Path

path = Path("data/conceptnet/conceptnet-assertions-5.7.0.csv.gz")
bio_kw = {
    "bird", "animal", "mammal", "fish", "insect", "reptile", "amphibian",
    "organism", "species", "plant", "fly", "swim", "walk", "hunt",
    "feather", "wing", "biological", "predator", "prey", "penguin",
    "dog", "cat", "horse", "snake", "frog", "bear", "lion", "tiger",
}

notcapable_total = 0
notcapable_en = 0
notcapable_bio = 0
weight_below_2 = 0
samples = []

with gzip.open(path, "rt", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) < 5:
            continue
        rel = parts[1].split("/")[-1] if "/" in parts[1] else parts[1]
        if rel != "NotCapableOf":
            continue
        notcapable_total += 1
        if "/c/en/" not in parts[2] or "/c/en/" not in parts[3]:
            continue
        notcapable_en += 1
        start = parts[2].split("/c/en/")[1].split("/")[0]
        end = parts[3].split("/c/en/")[1].split("/")[0]
        meta = json.loads(parts[4])
        weight = meta.get("weight", 0)
        if weight < 2.0:
            weight_below_2 += 1
        if any(kw in start.lower() or kw in end.lower() for kw in bio_kw):
            notcapable_bio += 1
            if len(samples) < 20:
                samples.append(f"  {start} NotCapableOf {end} (w={weight:.1f})")

print(f"Total NotCapableOf edges: {notcapable_total}")
print(f"English only: {notcapable_en}")
print(f"Weight < 2.0: {weight_below_2}")
print(f"Biology-keyword matching: {notcapable_bio}")
print(f"\nSamples:")
for s in samples:
    print(s)
