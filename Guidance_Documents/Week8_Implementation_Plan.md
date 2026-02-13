# Week 8 Implementation Plan: LLM Evaluation Infrastructure

**Date**: 2026-02-13  
**Status**: Week 7 Complete → Starting Week 8  
**Duration**: 5-7 days (20-30 hours)  
**Goal**: Build complete infrastructure for evaluating foundation models on DeFAb benchmark

---

## Executive Summary

Week 8 builds the evaluation infrastructure to test 5 foundation models (GPT-4o, Claude 3.5, Gemini 1.5 Pro, Llama 3 70B/8B) on our 374 development instances across 4 modalities with 2 prompting strategies.

**Key Deliverables**:
1. Model interface layer (5 models)
2. Prompting infrastructure (direct + CoT)
3. Batch evaluation pipeline
4. Response caching system
5. Decoder integration
6. Cost tracking

**Estimated API Cost**: $100-200 for development/testing, $450-700 for full evaluation (Week 9)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation Pipeline                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Prompting Layer (experiments/prompting.py)                 │
│  - Direct prompting                                          │
│  - Chain-of-Thought prompting                                │
│  - Modality-specific templates                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Model Interface Layer (experiments/model_interface.py)      │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ OpenAI   │  │Anthropic │  │  Google  │  │  Local   │   │
│  │ GPT-4o   │  │Claude 3.5│  │ Gemini   │  │  Llama   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                               │
│  - Unified interface                                          │
│  - Rate limiting                                              │
│  - Error handling                                             │
│  - Response caching                                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Decoder Pipeline (existing: src/blanc/codec/)              │
│  - D1: Exact match                                           │
│  - D2: Template extraction                                   │
│  - D3: Semantic parsing                                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Results & Analysis                                          │
│  - Accuracy metrics                                          │
│  - Error taxonomy                                            │
│  - Cost tracking                                             │
│  - Response cache                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Model Interface Layer (Days 1-2, 8-12 hours)

### 1.1 Base Interface Design

**File**: `experiments/model_interface.py`

**Core Classes**:
```python
class ModelInterface(ABC):
    """Abstract base class for all model interfaces."""
    
    @abstractmethod
    def query(self, prompt: str, temperature: float = 0.0, 
              max_tokens: int = 512) -> ModelResponse
    
    @abstractmethod
    def batch_query(self, prompts: List[str], **kwargs) -> List[ModelResponse]
    
    @property
    @abstractmethod
    def model_name(self) -> str
    
    @property
    @abstractmethod
    def cost_per_1k_input(self) -> float
    
    @property
    @abstractmethod
    def cost_per_1k_output(self) -> float

@dataclass
class ModelResponse:
    """Standardized response format."""
    text: str
    model: str
    tokens_input: int
    tokens_output: int
    cost: float
    latency: float
    metadata: Dict[str, Any]
```

**Tasks**:
- [ ] Create abstract base class
- [ ] Define ModelResponse dataclass
- [ ] Implement error handling framework
- [ ] Add rate limiting decorator
- [ ] Create response validation

**Acceptance**: Base class can be instantiated and tested

---

### 1.2 OpenAI Integration (GPT-4o)

**Implementation**:
```python
class OpenAIInterface(ModelInterface):
    """OpenAI API integration for GPT-4o."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._rate_limiter = RateLimiter(rpm=500, tpm=80000)
    
    @retry(exponential_backoff, max_attempts=3)
    def query(self, prompt: str, **kwargs) -> ModelResponse:
        # Implementation with rate limiting and retry logic
        pass
```

**Tasks**:
- [ ] Install openai SDK: `pip install openai`
- [ ] Implement OpenAIInterface class
- [ ] Add exponential backoff retry logic
- [ ] Test on 5 sample instances
- [ ] Verify cost tracking accuracy

**Rate Limits** (Tier 1):
- Requests: 500 RPM
- Tokens: 80,000 TPM
- Cost: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens

**Acceptance**: Can query GPT-4o and get valid responses

---

### 1.3 Anthropic Integration (Claude 3.5 Sonnet)

**Implementation**:
```python
class AnthropicInterface(ModelInterface):
    """Anthropic API integration for Claude 3.5 Sonnet."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._rate_limiter = RateLimiter(rpm=50, tpm=40000)
    
    def batch_query(self, prompts: List[str], **kwargs):
        # Use Message Batches API for 50% cost savings
        pass
```

**Tasks**:
- [ ] Install anthropic SDK: `pip install anthropic`
- [ ] Implement AnthropicInterface class
- [ ] Implement batch processing using Message Batches API
- [ ] Test on 5 sample instances
- [ ] Verify 50% batch discount applies

**Rate Limits** (Tier 1):
- Requests: 50 RPM
- Tokens: 40,000 TPM
- Cost: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- Batch: 50% discount, 24h completion window

**Acceptance**: Can query Claude 3.5 and use batch API

---

### 1.4 Google Integration (Gemini 1.5 Pro)

**Implementation**:
```python
class GoogleInterface(ModelInterface):
    """Google AI API integration for Gemini 1.5 Pro."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self._rate_limiter = RateLimiter(rpm=2, tpm=32000)
```

**Tasks**:
- [ ] Install google-generativeai SDK: `pip install google-generativeai`
- [ ] Implement GoogleInterface class
- [ ] Handle stricter rate limits (2 RPM)
- [ ] Test on 5 sample instances
- [ ] Verify pricing structure

**Rate Limits** (Free tier):
- Requests: 2 RPM (very low!)
- Tokens: 32,000 TPM
- Cost: Check current pricing for Gemini 1.5 Pro

**Note**: May need to upgrade to paid tier for reasonable throughput

**Acceptance**: Can query Gemini 1.5 Pro

---

### 1.5 Local Model Integration (Llama 3)

**Options**:
1. **Ollama** (recommended for local dev)
2. **HuggingFace Transformers** (direct)
3. **vLLM** (for production speed)

**Implementation**:
```python
class LlamaInterface(ModelInterface):
    """Local Llama 3 integration via Ollama."""
    
    def __init__(self, model: str = "llama3:70b"):
        import ollama
        self.client = ollama.Client()
        self.model = model
        # No rate limiting needed for local
    
    def query(self, prompt: str, **kwargs) -> ModelResponse:
        # No API costs, track inference time instead
        pass
```

**Tasks**:
- [ ] Install ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
- [ ] Pull models: `ollama pull llama3:70b` and `ollama pull llama3:8b`
- [ ] Implement LlamaInterface class
- [ ] Test on 5 sample instances
- [ ] Benchmark inference speed

**Acceptance**: Can query both Llama 3 70B and 8B locally

---

## Phase 2: Prompting Infrastructure (Days 2-3, 6-8 hours)

### 2.1 Prompt Templates

**File**: `experiments/prompting.py`

**Direct Prompting**:
```python
DIRECT_PROMPT_TEMPLATE = """You are a reasoning expert. You will be given:
1. A theory (knowledge base)
2. A target query
3. A set of candidate hypotheses

Your task: Select or generate the hypothesis that, when added to the theory, 
enables derivation of the target query.

Theory: {theory}
Target: {target}
Candidates: {candidates}

Output only the hypothesis, nothing else."""
```

**Chain-of-Thought Prompting**:
```python
COT_PROMPT_TEMPLATE = """You are a reasoning expert. Think step-by-step.

Theory: {theory}
Target: {target}
Candidates: {candidates}

Analyze:
1. What does the target query require?
2. What is currently missing from the theory?
3. Which candidate fills this gap?
4. Why does this candidate work?

Final Answer: [hypothesis]"""
```

**Modality-Specific Templates**:
- M1 (Narrative): Natural language description
- M2 (Semi-formal): Structured text with predicates
- M3 (Annotated): Formal with comments
- M4 (Pure formal): Raw Prolog-style

**Tasks**:
- [ ] Create base prompt templates
- [ ] Create modality-specific variants
- [ ] Create CoT variants
- [ ] Implement prompt rendering functions
- [ ] Test on sample instances (manual validation)

**Acceptance**: Can generate prompts for all modality × prompt-type combinations

---

### 2.2 Prompt Rendering Pipeline

**Functions**:
```python
def render_prompt(
    instance: AbductiveInstance,
    modality: str,  # M1, M2, M3, M4
    strategy: str,  # 'direct', 'cot'
    model_name: str  # For model-specific formatting
) -> str:
    """Render instance into model prompt."""
    pass

def format_candidates(
    candidates: List[str],
    modality: str
) -> str:
    """Format candidate hypotheses for display."""
    pass
```

**Tasks**:
- [ ] Implement render_prompt()
- [ ] Integrate with existing encoders (M1-M4)
- [ ] Add model-specific formatting (e.g., Claude's system message)
- [ ] Create test suite for prompt rendering
- [ ] Validate prompt quality manually (5-10 examples)

**Acceptance**: Prompts render correctly for all combinations

---

## Phase 3: Batch Evaluation Pipeline (Days 3-4, 8-10 hours)

### 3.1 Pipeline Architecture

**File**: `experiments/evaluation_pipeline.py`

**Core Class**:
```python
class EvaluationPipeline:
    """End-to-end evaluation pipeline."""
    
    def __init__(self, 
                 instances: List[AbductiveInstance],
                 models: List[ModelInterface],
                 modalities: List[str],
                 strategies: List[str],
                 cache_dir: str = "cache/responses"):
        self.instances = instances
        self.models = models
        self.modalities = modalities
        self.strategies = strategies
        self.cache = ResponseCache(cache_dir)
    
    def run(self, 
            batch_size: int = 10,
            save_every: int = 50) -> EvaluationResults:
        """Run full evaluation with progress tracking."""
        pass
    
    def evaluate_single(self, 
                       instance: AbductiveInstance,
                       model: ModelInterface,
                       modality: str,
                       strategy: str) -> SingleEvaluation:
        """Evaluate one instance-model-modality-strategy combination."""
        pass
```

**Tasks**:
- [ ] Implement EvaluationPipeline class
- [ ] Add progress tracking (tqdm)
- [ ] Implement checkpoint/resume functionality
- [ ] Add error recovery (log failures, continue)
- [ ] Integrate with decoders (D1→D2→D3)

**Acceptance**: Can run evaluation on 10 instances end-to-end

---

### 3.2 Response Caching

**Why**: Avoid re-querying models (saves money and time)

**Implementation**:
```python
class ResponseCache:
    """Persistent cache for model responses."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get(self, cache_key: str) -> Optional[ModelResponse]:
        """Retrieve cached response if exists."""
        pass
    
    def set(self, cache_key: str, response: ModelResponse):
        """Store response in cache."""
        pass
    
    def _make_key(self, 
                  instance_id: str,
                  model: str,
                  modality: str,
                  strategy: str) -> str:
        """Generate deterministic cache key."""
        return hashlib.sha256(
            f"{instance_id}:{model}:{modality}:{strategy}".encode()
        ).hexdigest()
```

**Cache Structure**:
```
cache/
  responses/
    {sha256_hash}.json  # One file per unique query
  metadata/
    cache_index.json    # Fast lookup index
```

**Tasks**:
- [ ] Implement ResponseCache class
- [ ] Add cache hit/miss tracking
- [ ] Implement cache statistics
- [ ] Test cache persistence across runs

**Acceptance**: Cached responses are reused correctly

---

### 3.3 Decoder Integration

**Integration**:
```python
def decode_response(
    response: ModelResponse,
    instance: AbductiveInstance,
    modality: str
) -> DecodedResult:
    """Apply D1→D2→D3 cascading decoder."""
    
    # Try D1 (exact match)
    result = decode_d1(response.text, instance)
    if result.success:
        return DecodedResult(hypothesis=result.value, 
                           decoder='D1', 
                           confidence=1.0)
    
    # Try D2 (template)
    result = decode_d2(response.text, instance)
    if result.success:
        return DecodedResult(hypothesis=result.value,
                           decoder='D2',
                           confidence=result.score)
    
    # Try D3 (semantic)
    result = decode_d3(response.text, instance)
    return DecodedResult(hypothesis=result.value if result.success else None,
                        decoder='D3' if result.success else 'FAILED',
                        confidence=result.score if result.success else 0.0)
```

**Tasks**:
- [ ] Create decoder integration wrapper
- [ ] Track which decoder succeeded
- [ ] Compute metrics (accuracy, decoder stage distribution)
- [ ] Handle decoder failures gracefully

**Acceptance**: Decoders work on real model responses

---

### 3.4 Metrics Computation

**Metrics**:
```python
@dataclass
class EvaluationMetrics:
    """Per-instance evaluation metrics."""
    
    # Binary accuracy
    correct: bool
    
    # Decoder used
    decoder_stage: str  # 'D1', 'D2', 'D3', 'FAILED'
    
    # For Level 2+
    novelty: Optional[float]  # Nov(h*)
    
    # For Level 3
    revision_distance: Optional[float]  # Diff(h*, h_prior)
    conservativity: Optional[bool]  # Does h* preserve all other expectations?
    
    # Response quality
    latency: float
    tokens_used: int
    cost: float
```

**Tasks**:
- [ ] Implement metric computation
- [ ] Add aggregation across instances
- [ ] Create result summary reports
- [ ] Export to JSON for analysis

**Acceptance**: Metrics computed correctly for sample instances

---

## Phase 4: Testing & Validation (Day 5, 4-6 hours)

### 4.1 Pilot Evaluation

**Goal**: Run mini-evaluation to validate entire pipeline

**Test Set**:
- 20 instances (biology: 7, legal: 7, materials: 6)
- 2 models (GPT-4o, Claude 3.5)
- 2 modalities (M4, M2)
- 1 strategy (direct)

**Total**: 20 × 2 × 2 × 1 = 80 queries

**Expected Cost**: ~$2-5

**Tasks**:
- [ ] Select diverse test instances
- [ ] Run pilot evaluation
- [ ] Verify all systems work
- [ ] Check decoder accuracy
- [ ] Validate cost tracking
- [ ] Estimate full evaluation cost

**Acceptance**: Pilot runs successfully, metrics look reasonable

---

### 4.2 Cost Estimation

**Full Evaluation** (Week 9):
- Instances: 374
- Models: 5 (GPT-4o, Claude 3.5, Gemini 1.5, Llama 70B, Llama 8B)
- Modalities: 4 (M1, M2, M3, M4)
- Strategies: 2 (direct, CoT)
- **Total queries**: 374 × 5 × 4 × 2 = 14,960 queries

**Cost Breakdown** (estimated):
```
GPT-4o:      374×4×2 = 2,992 queries × $0.02 =  $60
Claude 3.5:  374×4×2 = 2,992 queries × $0.015 = $45 (with batch discount)
Gemini 1.5:  374×4×2 = 2,992 queries × $0.01 =  $30
Llama 70B:   FREE (local)
Llama 8B:    FREE (local)

Total: ~$135-200 (conservative estimate with buffer)
```

**Note**: Initial estimate in handoff ($450-700) was likely for larger instance set or different pricing

**Tasks**:
- [ ] Calculate precise cost based on pilot
- [ ] Verify batch discounts apply
- [ ] Set up cost tracking dashboard

**Acceptance**: Cost estimates are accurate within 20%

---

### 4.3 Unit Tests

**Test Coverage**:
```
tests/
  experiments/
    test_model_interface.py
      - Test each model interface
      - Test rate limiting
      - Test error handling
      - Mock API responses
    
    test_prompting.py
      - Test prompt rendering
      - Test all modalities
      - Test CoT vs direct
    
    test_evaluation_pipeline.py
      - Test pipeline end-to-end (mocked models)
      - Test caching
      - Test checkpoint/resume
      - Test decoder integration
    
    test_metrics.py
      - Test metric computation
      - Test aggregation
```

**Tasks**:
- [ ] Write comprehensive unit tests
- [ ] Achieve >80% coverage on new code
- [ ] Add integration tests with mocked APIs
- [ ] Test error scenarios

**Acceptance**: All tests pass, >80% coverage

---

## Implementation Schedule

### Day 1 (6-8 hours): Foundation
**Morning**:
- [ ] Set up API keys (OpenAI, Anthropic, Google)
- [ ] Install SDKs: `pip install openai anthropic google-generativeai`
- [ ] Create base ModelInterface class
- [ ] Implement ModelResponse dataclass

**Afternoon**:
- [ ] Implement OpenAIInterface
- [ ] Test on 5 instances manually
- [ ] Add rate limiting
- [ ] Add exponential backoff

**Deliverable**: Working OpenAI integration

---

### Day 2 (6-8 hours): More Models
**Morning**:
- [ ] Implement AnthropicInterface
- [ ] Test batch API
- [ ] Implement GoogleInterface
- [ ] Handle rate limits

**Afternoon**:
- [ ] Install Ollama
- [ ] Pull Llama models
- [ ] Implement LlamaInterface
- [ ] Test all 5 models

**Deliverable**: All 5 model interfaces working

---

### Day 3 (6-8 hours): Prompting
**Morning**:
- [ ] Create prompt templates (direct + CoT)
- [ ] Implement render_prompt()
- [ ] Test on sample instances

**Afternoon**:
- [ ] Create modality-specific variants
- [ ] Manual quality check on 10 prompts
- [ ] Refine templates based on feedback

**Deliverable**: Prompting infrastructure complete

---

### Day 4 (6-8 hours): Pipeline
**Morning**:
- [ ] Implement ResponseCache
- [ ] Implement EvaluationPipeline skeleton
- [ ] Add progress tracking

**Afternoon**:
- [ ] Integrate decoders
- [ ] Implement metrics computation
- [ ] Add checkpoint/resume

**Deliverable**: Working evaluation pipeline

---

### Day 5 (4-6 hours): Testing & Validation
**Morning**:
- [ ] Write unit tests
- [ ] Run pilot evaluation (20 instances)
- [ ] Verify results

**Afternoon**:
- [ ] Calculate cost estimates
- [ ] Create evaluation plan for Week 9
- [ ] Document everything

**Deliverable**: Week 8 complete, ready for full evaluation

---

## File Structure

```
blanc/
├── experiments/
│   ├── model_interface.py       # NEW: Model API wrappers
│   ├── prompting.py              # NEW: Prompt templates and rendering
│   ├── evaluation_pipeline.py    # NEW: Batch evaluation system
│   ├── run_pilot_evaluation.py   # NEW: Pilot test script
│   └── run_full_evaluation.py    # NEW: Full evaluation script (Week 9)
│
├── cache/
│   ├── responses/                # NEW: Cached model responses
│   └── metadata/                 # NEW: Cache index
│
├── results/
│   └── evaluations/              # NEW: Evaluation results
│       ├── pilot_eval_YYYYMMDD.json
│       └── full_eval_YYYYMMDD.json
│
├── tests/
│   └── experiments/              # NEW: Tests for evaluation code
│       ├── test_model_interface.py
│       ├── test_prompting.py
│       └── test_evaluation_pipeline.py
│
└── requirements.txt              # UPDATE: Add new dependencies
```

---

## Dependencies to Add

```python
# API SDKs
openai>=1.50.0           # OpenAI GPT-4o
anthropic>=0.38.0        # Anthropic Claude 3.5
google-generativeai>=0.8.0  # Google Gemini 1.5
ollama>=0.3.0            # Local Llama models

# Utilities
tenacity>=8.0.0          # Retry logic with exponential backoff
tqdm>=4.66.0             # Progress bars
pydantic>=2.0.0          # Data validation
python-dotenv>=1.0.0     # Environment variable management

# Optional
httpx>=0.27.0            # Async HTTP (if needed)
aiofiles>=24.0.0         # Async file I/O (if needed)
```

---

## Configuration Management

**File**: `.env` (DO NOT COMMIT)
```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Model Settings
DEFAULT_TEMPERATURE=0.0
DEFAULT_MAX_TOKENS=512

# Evaluation Settings
BATCH_SIZE=10
SAVE_EVERY=50
CACHE_DIR=cache/responses
```

**File**: `config/evaluation_config.yaml`
```yaml
models:
  - name: gpt-4o
    provider: openai
    enabled: true
  - name: claude-3-5-sonnet-20241022
    provider: anthropic
    enabled: true
    use_batch: true
  - name: gemini-1.5-pro
    provider: google
    enabled: true
  - name: llama3:70b
    provider: ollama
    enabled: true
  - name: llama3:8b
    provider: ollama
    enabled: true

modalities:
  - M1  # Narrative
  - M2  # Semi-formal
  - M3  # Annotated
  - M4  # Pure formal

strategies:
  - direct
  - cot

instances:
  biology: instances/biology_dev_instances.json
  legal: instances/legal_dev_instances.json
  materials: instances/materials_dev_instances.json
```

---

## Testing Strategy

### Unit Tests (Per Component)
- Model interfaces: Mock API responses
- Prompting: Snapshot testing on templates
- Pipeline: Mock entire flow
- Caching: Test persistence and retrieval

### Integration Tests
- End-to-end on 5 instances with real APIs (gated by API keys)
- Verify decoder integration
- Check cost tracking accuracy

### Pilot Evaluation (20 instances)
- Smoke test for full pipeline
- Validate metrics
- Cost estimation

### Manual Validation
- Review 10 prompts for quality
- Check 10 model responses
- Verify decoder correctness

---

## Risk Mitigation

### Risk 1: API Rate Limits
**Mitigation**:
- Implement exponential backoff
- Use batch APIs where available (Claude)
- Set conservative rate limits
- Add sleep between batches

### Risk 2: High Costs
**Mitigation**:
- Run pilot first (20 instances, $2-5)
- Use caching aggressively
- Monitor spend in real-time
- Set hard limits in API dashboards

### Risk 3: Decoder Failures
**Mitigation**:
- Already validated D1/D2/D3 work (75% round-trip)
- Log all decoder failures for analysis
- Have fallback strategies

### Risk 4: Model Availability
**Mitigation**:
- Have local Llama as backup
- Make each model optional in config
- Can run partial evaluation if needed

---

## Success Criteria

### Week 8 Complete When:
- [ ] All 5 model interfaces working
- [ ] Can generate prompts for all modality × strategy combinations
- [ ] Evaluation pipeline runs end-to-end
- [ ] Response caching functional
- [ ] Decoders integrated and tested
- [ ] Pilot evaluation (20 instances) successful
- [ ] Cost estimates accurate
- [ ] Unit tests pass (>80% coverage)
- [ ] Documentation complete

### Ready for Week 9 When:
- [ ] Full evaluation plan documented
- [ ] API keys verified and funded
- [ ] All instances loaded (374 total)
- [ ] Cost budget approved (~$135-200)
- [ ] Pipeline tested and stable

---

## Week 9 Preview

**Goal**: Run full evaluation (14,960 queries)

**Strategy**:
1. Start with Llama models (free, fast feedback)
2. Run GPT-4o on M4 only first (cheapest, fastest)
3. Expand to all modalities
4. Add Claude and Gemini
5. Run CoT experiments
6. Analyze results

**Timeline**: 7-10 days (includes API wait times, analysis)

---

## Questions to Resolve Before Starting

1. **API Key Access**: Do we have all API keys?
2. **Budget Approval**: Is $135-200 approved for Week 9?
3. **Local Resources**: Can local machine run Llama 70B? (Need ~40GB RAM)
4. **Priorities**: Which models are most critical? (Can deprioritize if needed)

---

## Documentation Deliverables

### Technical Docs
- [ ] Model interface API reference
- [ ] Prompting guide
- [ ] Pipeline usage guide
- [ ] Configuration reference

### User Guides
- [ ] Quick start for running evaluation
- [ ] Cost optimization guide
- [ ] Troubleshooting guide

### Analysis Docs
- [ ] Pilot evaluation report
- [ ] Cost analysis
- [ ] Week 9 evaluation plan

---

## Next Steps After Week 8

**Week 9-10**: Full evaluation + analysis
**Week 11-12**: Advanced analyses (scaling, symbolic ceiling, etc.)
**Week 13-14**: HPC production + paper submission

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13  
**Status**: ✅ IMPLEMENTATION COMPLETE (Days 1-4)  
**Actual Completion**: 2026-02-13 (same day!)  
**Remaining**: Pilot evaluation (needs API keys)
