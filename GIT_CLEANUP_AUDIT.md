# Git Repository Cleanup Audit

**Date**: 2026-02-12  
**Purpose**: Ensure clean, tight, reproducible git repository  
**Current**: 89 markdown files - TOO MANY

---

## Current State

### Markdown Files: 89 total

**Root**: 18 files  
**Guidance_Documents**: 6 files  
**docs/**: 54 files (way too many!)  
**archive/**: 12 files  
**hpc/**: 1 file  
**examples/**: 1 file

**Problem**: Too much documentation clutter

---

## What MUST Be In Git

### Essential Root Files (6-8 max)

**Required**:
1. README.md - Project overview
2. QUICK_START.md - Getting started
3. KNOWLEDGE_BASE_POLICY.md - Expert-only policy (CRITICAL)
4. IMPLEMENTATION_PLAN.md - Technical specification

**Current Status**:
5. CONTINUE_WEEK3.md - Current development status
6. WEEK3_COMPLETION.md - Latest milestone

**Optional** (consider removing):
7. COVERAGE_ANALYSIS.md - Could move to docs/
8. BLOCKERS_CHECK.md - Session-specific, archive
9. DATA_DOWNLOAD_INSTRUCTIONS.md - Could move to docs/
10. DOCUMENTATION_INDEX.md - Needed for navigation
11. INSTALL.md - Needed
12. NEURIPS_FULL_ROADMAP.md - Needed
13. PROJECT_STATUS.md - Duplicate of CONTINUE_WEEK3?
14. SESSION_COMPLETE.md - Session-specific, archive
15. WEEK2_COMPLETE.md - Archive
16. WEEK2_HANDOFF.md - Archive

**Recommendation**: Keep 6-8, move/delete rest

---

### Source Code (MUST HAVE)

**Current in git**: ✅
- src/blanc/ (production code)
- tests/ (test suite)
- examples/knowledge_bases/ (expert KBs)
- scripts/ (download and generation scripts)

**Status**: ✅ GOOD

---

### Scripts for Reproducibility (MUST HAVE)

**Download scripts** (6 needed):
- download_yago.py
- download_wordnet.py
- download_opencyc.py
- download_lkif.py
- download_dapreco.py
- download_matonto.py

**Extraction scripts** (6 needed):
- extract_yago_biology.py
- extract_wordnet_biology.py
- extract_lkif_legal.py
- extract_matonto_materials.py
- (others)

**Generation scripts**:
- generate_dev_instances.py
- compute_yield_curves_dev.py
- analyze_instances.py

**Status**: ✅ All present

---

### Data Files (MUST NOT BE IN GIT)

**Check**: data/ folder

**Current**: ✅ NOT in git (correctly excluded)

**Download scripts present**: ✅ Users can recreate

**Status**: ✅ CORRECT

---

## What Should Be REMOVED

### Archive Folder - DELETE

**Why**: Historical snapshots, not needed in git
- 12 files in archive/mvp_docs/
- 12 files in archive/week2_docs/
- 6 files in archive/week_reports/

**Action**: Delete entire archive/ folder (30 files)

**Justification**: Git history already preserves this

---

### docs/ Folder - REDUCE

**Current**: 54 files (way too many)

**Keep** (essential):
- docs/audits/KB_INVENTORY.md
- docs/audits/KB_REQUIREMENTS_AUDIT.md
- docs/audits/COVERAGE_AUDIT.md

**Delete** (redundant):
- All session reports (git history has this)
- Duplicate planning docs
- Old status files

**Target**: Reduce from 54 to ~10 essential files

---

### Root Files - REDUCE

**Current**: 18 files

**Keep** (6-8 essential):
1. README.md
2. QUICK_START.md
3. KNOWLEDGE_BASE_POLICY.md (CRITICAL)
4. IMPLEMENTATION_PLAN.md
5. NEURIPS_FULL_ROADMAP.md
6. CONTINUE_WEEK3.md
7. INSTALL.md
8. DOCUMENTATION_INDEX.md (optional)

**Move to docs/**:
- COVERAGE_ANALYSIS.md
- DATA_DOWNLOAD_INSTRUCTIONS.md
- WEEK2_COMPLETE.md
- WEEK2_HANDOFF.md
- WEEK3_COMPLETION.md

**Delete**:
- BLOCKERS_CHECK.md (session-specific)
- SESSION_COMPLETE.md (session-specific)
- PROJECT_STATUS.md (duplicate of CONTINUE_WEEK3)

---

## Proposed Clean Structure

```
blanc/ (git repository)
├── README.md
├── QUICK_START.md
├── INSTALL.md
├── KNOWLEDGE_BASE_POLICY.md (CRITICAL)
├── IMPLEMENTATION_PLAN.md
├── NEURIPS_FULL_ROADMAP.md
├── CONTINUE_WEEK3.md (or STATUS.md)
│
├── src/blanc/                  Source code
├── tests/                      Test suite
├── examples/knowledge_bases/   Expert KBs (extracted, no raw data)
├── scripts/                    All reproducibility scripts
├── hpc/                        HPC infrastructure
├── paper/                      LaTeX paper
│
├── docs/                       Essential documentation only (~10 files)
│   ├── audits/                 Key technical audits (3-5 files)
│   └── DATA_DOWNLOAD_INSTRUCTIONS.md
│
└── Guidance_Documents/         Phase guides (6 files)
```

**Total markdown**: ~20-25 (vs current 89)

---

## Reproducibility Check

### Can someone clone and recreate everything?

**YES** ✅ if we have:

1. ✅ Source code (src/blanc/)
2. ✅ Tests (tests/)
3. ✅ Download scripts (scripts/download_*.py)
4. ✅ Extraction scripts (scripts/extract_*.py)
5. ✅ Generation scripts (scripts/generate_*.py)
6. ✅ Extracted KBs (examples/knowledge_bases/*.py)
7. ✅ Instructions (README, QUICK_START, DATA_DOWNLOAD_INSTRUCTIONS)
8. ✅ Requirements (requirements.txt, setup.py if exists)

**Current status**: ✅ ALL PRESENT

---

## Action Plan

### Phase 1: Delete Archive (30 files)

```bash
git rm -r archive/
git commit -m "Remove archive - git history preserves this"
```

### Phase 2: Clean docs/ (54 → 10 files)

Keep only:
- docs/audits/KB_INVENTORY.md
- docs/audits/KB_REQUIREMENTS_AUDIT.md
- docs/audits/COVERAGE_AUDIT.md
- docs/DATA_DOWNLOAD_INSTRUCTIONS.md
- docs/README.md (brief index)

Delete rest

### Phase 3: Clean Root (18 → 7 files)

Keep only:
- README.md
- QUICK_START.md
- INSTALL.md
- KNOWLEDGE_BASE_POLICY.md
- IMPLEMENTATION_PLAN.md
- NEURIPS_FULL_ROADMAP.md
- CONTINUE_WEEK3.md

Move to docs/:
- WEEK2_COMPLETE.md → docs/week2_complete.md
- WEEK3_COMPLETION.md → docs/week3_complete.md
- COVERAGE_ANALYSIS.md → docs/coverage_analysis.md

Delete:
- BLOCKERS_CHECK.md
- SESSION_COMPLETE.md
- PROJECT_STATUS.md (duplicate)
- WEEK2_HANDOFF.md (superseded)
- DOCUMENTATION_INDEX.md (if not needed)

### Result

**Markdown files**: 89 → ~25 (70% reduction)  
**Structure**: Clean and professional  
**Reproducibility**: Fully maintained

---

## Verification Checklist

After cleanup, verify:

- [ ] README.md explains project
- [ ] QUICK_START.md works for new users
- [ ] All download scripts present (6)
- [ ] All extraction scripts present (6+)
- [ ] All generation scripts present (3+)
- [ ] Extracted KBs in examples/ (no raw data)
- [ ] Tests run: `python -m pytest tests/`
- [ ] Can download data: `python scripts/download_*.py`
- [ ] Can generate instances: `python scripts/generate_dev_instances.py`

---

**Execute this cleanup?**

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12
