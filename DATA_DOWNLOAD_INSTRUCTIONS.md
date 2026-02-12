# Data Download Instructions

**Important**: Expert KB data files (2.7 GB) are NOT in the git repository due to GitHub's 100 MB file size limit.

---

## Download All Expert KBs

Run the download scripts to obtain all expert-curated knowledge bases:

```bash
# Download all 6 expert KBs
python scripts/download_yago.py           # YAGO 4.5 (336 MB)
python scripts/download_wordnet.py        # WordNet 3.0 (via NLTK)
python scripts/download_opencyc.py        # OpenCyc 2012 (27 MB)
python scripts/download_lkif.py           # LKIF Core (194 KB)
python scripts/download_dapreco.py        # DAPRECO GDPR (5.6 MB)
python scripts/download_matonto.py        # MatOnto (1.3 MB)
```

**Total download**: ~370 MB compressed, ~2.7 GB uncompressed

---

## What Will Be Downloaded

### Biology Sources
- `data/yago/` - YAGO 4.5 (Télécom Paris)
- `data/wordnet/` - WordNet 3.0 (Princeton)
- `data/opencyc/` - OpenCyc 2012 (Cycorp)

### Legal Sources
- `data/lkif-core/` - LKIF Core (U Amsterdam)
- `data/dapreco/` - DAPRECO GDPR (U Luxembourg)

### Materials Sources
- `data/matonto/` - MatOnto (MatPortal)

---

## Why Data is Not in Git

GitHub has a 100 MB file size limit. The expert KB files exceed this:
- yago-tiny.ttl: 1.6 GB
- yago-entities.jsonl: 647 MB
- yago zips: 191 MB + 145 MB

**Solution**: Download locally using provided scripts.

---

## Quick Setup

```bash
# Clone repository
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc

# Install dependencies
pip install -r requirements.txt

# Download expert KBs (one command downloads all)
python scripts/download_all_kbs.py

# Verify installation
python -m pytest tests/
python scripts/test_all_expert_kbs.py
```

---

## Alternative: Use Extracted KBs Only

If you don't want to download 2.7 GB, the extracted KBs work without raw data:

```python
# These work immediately after cloning
from examples.knowledge_bases.biology_kb import create_biology_kb
from examples.knowledge_bases.legal_kb import create_legal_kb
from examples.knowledge_bases.materials_kb import create_materials_kb

bio = create_biology_kb()      # 927 rules, 255 facts
legal = create_legal_kb()      # 201 rules, 63 facts
materials = create_materials_kb()  # 1,190 rules, 86 facts
```

**These files ARE in git and don't require downloads.**

---

## Data Directory Structure (After Download)

```
data/
├── yago/                    2.4 GB
├── wordnet/                 10 MB (via NLTK)
├── opencyc/                 27 MB
├── lkif-core/               194 KB
├── dapreco/                 5.6 MB
└── matonto/                 1.3 MB
```

**Total**: ~2.7 GB (not in git, download with scripts)

---

**Note**: All download scripts include progress bars and verification.
