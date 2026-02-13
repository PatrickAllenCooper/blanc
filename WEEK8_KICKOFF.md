# Week 8 Kickoff: LLM Evaluation Infrastructure

**Date**: 2026-02-13  
**Status**: Week 7 Complete → Starting Week 8  
**Goal**: Build infrastructure to evaluate foundation models

---

## Quick Overview

We're building the evaluation system to test 5 foundation models on our 374 abductive reasoning instances.

**What we're building**:
- Model API wrappers (OpenAI, Anthropic, Google, Ollama)
- Prompt templates (direct + Chain-of-Thought)
- Batch evaluation pipeline
- Response caching
- Metrics computation

**Timeline**: 5-7 days (20-30 hours)

---

## The Big Picture

```
Week 7 (DONE) ───> Week 8 (NOW) ───> Week 9 (NEXT)
Infrastructure     Evaluation        Run Full
Complete          Infrastructure     Evaluation
                  
374 instances      5 model APIs      14,960 queries
4 modalities       2 prompt types    Results & Analysis
3 decoders         Caching system    Error taxonomy
```

---

## What We Have (Week 7 Complete)

✅ **Expert Knowledge Bases**: 2,318 rules across 3 domains  
✅ **Development Instances**: 374 instances ready  
✅ **Complete Codec**: M1-M4 encoders, D1-D3 decoders  
✅ **Round-trip Validation**: 75% accuracy (3 of 4 modalities perfect)  
✅ **Test Suite**: 283 passing tests, 78% coverage  
✅ **Statistical Analysis**: Section 4.3 framework complete

---

## What We're Building (Week 8)

### Phase 1: Model Interfaces (Days 1-2)

**5 Model APIs**:
1. **GPT-4o** (OpenAI) - 500 RPM, $2.50/$10 per 1M tokens
2. **Claude 3.5 Sonnet** (Anthropic) - 50 RPM, batch API with 50% discount
3. **Gemini 1.5 Pro** (Google) - 2 RPM (may need upgrade)
4. **Llama 3 70B** (Local via Ollama) - Free, needs ~40GB RAM
5. **Llama 3 8B** (Local via Ollama) - Free, lightweight

**Key Features**:
- Unified interface for all models
- Rate limiting with exponential backoff
- Error handling and retry logic
- Cost tracking per query
- Response caching

---

### Phase 2: Prompting (Days 2-3)

**Two Strategies**:
1. **Direct**: "Given theory T and target q, select hypothesis h from candidates"
2. **Chain-of-Thought**: "Think step-by-step: What's missing? Why does h work?"

**Four Modalities** (already have encoders):
- M1: Natural language narrative
- M2: Semi-formal with predicates
- M3: Annotated formal logic
- M4: Pure Prolog-style

**Result**: 2 × 4 = 8 prompt variants per instance

---

### Phase 3: Evaluation Pipeline (Days 3-4)

**Pipeline Flow**:
```
Instance → Render Prompt → Query Model → Cache Response → 
Decode (D1→D2→D3) → Compute Metrics → Save Results
```

**Features**:
- Batch processing with progress bars
- Checkpoint/resume on failure
- Response caching (avoid re-querying)
- Decoder integration
- Metrics: accuracy, novelty, revision distance, cost

---

### Phase 4: Testing & Validation (Day 5)

**Pilot Evaluation**:
- 20 instances (representative sample)
- 2 models (GPT-4o, Claude 3.5)
- 2 modalities (M4, M2)
- 1 strategy (direct)
- **Total**: 80 queries
- **Cost**: ~$2-5

**Goals**:
- Validate entire pipeline works
- Get cost estimates for full run
- Check decoder accuracy on real responses
- Identify and fix issues

---

## Full Evaluation Preview (Week 9)

**Scale**:
- 374 instances × 5 models × 4 modalities × 2 strategies = **14,960 queries**

**Estimated Cost**:
```
GPT-4o:     2,992 queries × $0.02  = $60
Claude 3.5: 2,992 queries × $0.015 = $45  (batch discount)
Gemini 1.5: 2,992 queries × $0.01  = $30
Llama 70B:  FREE (local)
Llama 8B:   FREE (local)

Total: ~$135-200
```

**Timeline**: 7-10 days (includes API latency, batch processing time)

---

## Implementation Schedule

### Day 1: OpenAI + Foundation
- Set up API keys
- Install SDKs
- Create base ModelInterface class
- Implement OpenAIInterface
- Test on 5 instances

### Day 2: More Models
- Anthropic (Claude 3.5) + batch API
- Google (Gemini 1.5)
- Ollama (Llama 3 70B/8B)
- Test all 5 models

### Day 3: Prompting
- Direct prompt templates
- Chain-of-Thought templates
- Modality-specific rendering
- Manual quality validation

### Day 4: Pipeline
- Response caching system
- Batch evaluation pipeline
- Decoder integration
- Metrics computation

### Day 5: Testing
- Unit tests (>80% coverage)
- Pilot evaluation (20 instances)
- Cost analysis
- Documentation

---

## Prerequisites

### Required
- [ ] OpenAI API key (GPT-4o access)
- [ ] Anthropic API key (Claude 3.5 access)
- [ ] Google API key (Gemini 1.5 access)
- [ ] Budget approval: ~$135-200 for Week 9 full evaluation

### Optional
- [ ] Local GPU (helps with Llama 70B, not required for 8B)
- [ ] Upgraded Google tier (2 RPM is very slow on free tier)

### Installation
```bash
# API SDKs
pip install openai anthropic google-generativeai ollama

# Utilities
pip install tenacity tqdm pydantic python-dotenv

# Ollama (for local Llama)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3:70b
ollama pull llama3:8b
```

---

## Files We'll Create

```
experiments/
├── model_interface.py          # NEW: API wrappers for 5 models
├── prompting.py                # NEW: Prompt templates
├── evaluation_pipeline.py      # NEW: Batch evaluation system
├── run_pilot_evaluation.py     # NEW: Pilot test (20 instances)
└── run_full_evaluation.py      # NEW: Full eval (Week 9)

cache/
└── responses/                  # NEW: Cached model responses

tests/
└── experiments/                # NEW: Tests for evaluation code
    ├── test_model_interface.py
    ├── test_prompting.py
    └── test_evaluation_pipeline.py

config/
└── evaluation_config.yaml      # NEW: Model/experiment config

.env                            # NEW: API keys (DO NOT COMMIT)
```

---

## Success Criteria

### Week 8 Done When:
✅ All 5 model interfaces working  
✅ Prompts generate correctly for all modality × strategy combos  
✅ Evaluation pipeline runs end-to-end  
✅ Response caching functional  
✅ Decoders integrated  
✅ Pilot evaluation (20 instances) successful  
✅ Cost estimates accurate  
✅ Unit tests pass (>80% coverage)  
✅ Ready for full evaluation in Week 9

---

## Risk Mitigation

**Rate Limits**: Exponential backoff + batch APIs where available  
**Costs**: Pilot first ($2-5), aggressive caching, real-time monitoring  
**Decoder Failures**: Already validated (75% round-trip), log all failures  
**Model Availability**: Local Llama as backup, optional models in config

---

## Questions to Answer Today

1. **Do we have all API keys?** (OpenAI, Anthropic, Google)
2. **Is budget approved?** (~$135-200 for Week 9)
3. **Can we run Llama 70B locally?** (Need ~40GB RAM)
4. **Which models are priority?** (Can skip some if needed)

---

## Next Actions

**Immediately**:
1. Gather API keys
2. Install dependencies
3. Start Day 1 implementation

**This Week**:
1. Build all 5 model interfaces
2. Create prompting infrastructure
3. Build evaluation pipeline
4. Run pilot evaluation
5. Prepare for Week 9

---

## References

**Detailed Plan**: `Guidance_Documents/Week8_Implementation_Plan.md` (952 lines)  
**Handoff Doc**: `CONTINUE_DEVELOPMENT.md`  
**Paper Requirements**: `paper/paper.tex` (Section 4.5: Evaluation Protocol)

---

**Let's build this! 🚀**

**Author**: Patrick Cooper  
**Start Date**: 2026-02-13  
**Target Completion**: 2026-02-18 to 2026-02-20
