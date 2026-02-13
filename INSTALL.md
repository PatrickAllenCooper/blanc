# Installation Guide

Quick setup for BLANC: Defeasible Abduction Benchmark

---

## Requirements

- Python 3.11+
- pip

---

## Installation

```bash
# Clone repository
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest tests/ --tb=no -q
```

Expected: 343 tests passing, 10 skipped

---

## For LLM Evaluation (Week 8+)

```bash
# 1. Create .env file
cp .env.template .env

# 2. Add your API keys to .env:
#    OPENAI_API_KEY=sk-...
#    ANTHROPIC_API_KEY=sk-ant-...
#    GOOGLE_API_KEY=... (optional)

# 3. Validate keys
python experiments/validate_api_keys.py

# 4. Run pilot evaluation
python experiments/run_pilot_evaluation.py
```

---

## Optional: Local Models

```bash
# Install Ollama for free local Llama models
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3:8b   # Lightweight
ollama pull llama3:70b  # Requires ~40GB RAM
```

---

## Troubleshooting

**Import errors**: Make sure you installed requirements
```bash
pip install -r requirements.txt
```

**Tests fail**: Check Python version
```bash
python --version  # Should be 3.11+
```

**API errors**: Validate your keys
```bash
python experiments/validate_api_keys.py
```

---

**For full documentation**: See `Guidance_Documents/`
