# Installation Guide

## Quick Start

```bash
# Install BLANC
pip install -e ".[dev]"
```

## System Requirements

- Python 3.11 or later
- 64-bit system (recommended)
- 4GB RAM minimum, 8GB recommended

## Backend Dependencies

BLANC supports multiple reasoning backends. Install the backends you need:

### ASP Backend (Clingo) - Already Installed

The ASP backend using Clingo is already installed with the base package.

**Verify installation:**
```bash
python -c "import clingo; print(clingo.__version__)"
```

### Prolog Backend (SWI-Prolog + PySwip) - Recommended

#### Windows Installation

**Step 1: Install SWI-Prolog**

1. Download SWI-Prolog 8.4.2 or later (64-bit):
   - https://www.swi-prolog.org/download/stable
   - Choose "SWI-Prolog 9.x.x for Microsoft Windows (64 bit)"

2. Run the installer
   - Install to default location: `C:\Program Files\swipl\`
   - **Important**: Check "Add to PATH" during installation

3. Verify installation:
   ```powershell
   swipl --version
   ```
   Should output: `SWI-Prolog version 9.x.x`

**Step 2: Install PySwip**

PySwip is already installed. Verify it can find SWI-Prolog:

```python
from pyswip import Prolog
prolog = Prolog()
print("PySwip working!")
```

If you get an error about finding SWI-Prolog, set environment variables:

```powershell
# Find SWI-Prolog locations
swipl --dump-runtime-variables

# Set environment variables (adjust paths from dump output)
$env:SWI_HOME_DIR = "C:\Program Files\swipl"
$env:LIBSWIPL_PATH = "C:\Program Files\swipl\bin"
```

Add these permanently in System Environment Variables.

#### Linux Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install swi-prolog

# Fedora
sudo dnf install pl

# Arch
sudo pacman -S swi-prolog

# Verify
swipl --version
```

PySwip is already installed with the package.

#### macOS Installation

```bash
# Using Homebrew
brew install swi-prolog

# Verify
swipl --version
```

PySwip is already installed with the package.

## Optional Dependencies

### LLM Integration

For constrained generation and LLM integration:

```bash
pip install -e ".[llm]"
```

This installs:
- `guidance`: Constrained LLM generation
- `outlines`: Structured LLM outputs

### Development Tools

Already installed if you used `pip install -e ".[dev]"`:

- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `hypothesis`: Property-based testing
- `mypy`: Static type checking
- `ruff`: Linting and formatting

## Verifying Installation

### Test All Components

```bash
# Run full test suite
pytest tests -v

# Test specific backends
pytest tests/backends/test_asp_backend.py -v
pytest tests/backends/test_prolog_backend.py -v

# Run examples
python examples/basic_usage.py
```

### Quick Test Script

```python
from blanc import KnowledgeBase, Query
from blanc.core.theory import Rule, RuleType, Theory

# Test Theory creation
theory = Theory()
theory.add_fact("human(socrates)")
theory.add_rule(Rule(head="mortal(X)", body=("human(X)",)))
print("Theory created successfully!")

# Test ASP backend
try:
    kb_asp = KnowledgeBase(backend='asp')
    kb_asp.load(theory)
    print("ASP backend working!")
except Exception as e:
    print(f"ASP backend error: {e}")

# Test Prolog backend
try:
    kb_prolog = KnowledgeBase(backend='prolog')
    kb_prolog.load(theory)
    print("Prolog backend working!")
except Exception as e:
    print(f"Prolog backend error: {e}")
    print("Install SWI-Prolog to use Prolog backend")
```

## Troubleshooting

### PySwip can't find SWI-Prolog (Windows)

**Symptom**: ImportError or "SWI-Prolog not found"

**Solutions**:

1. Verify SWI-Prolog is installed:
   ```powershell
   swipl --version
   ```

2. Check architecture match:
   ```python
   import platform
   print(f"Python: {platform.architecture()[0]}")  # Should be 64bit
   ```
   
   SWI-Prolog must also be 64-bit.

3. Set environment variables:
   ```powershell
   # Get the paths
   swipl --dump-runtime-variables
   
   # Set them (adjust based on your output)
   [System.Environment]::SetEnvironmentVariable('SWI_HOME_DIR', 'C:\Program Files\swipl', 'User')
   [System.Environment]::SetEnvironmentVariable('LIBSWIPL_PATH', 'C:\Program Files\swipl\bin', 'User')
   ```

4. Restart your terminal/IDE after setting environment variables

### Clingo version issues

If you get Clingo version errors:

```bash
# Upgrade to latest
pip install --upgrade clingo clorm
```

### Import errors

If you get import errors:

```bash
# Reinstall in development mode
pip install -e ".[dev]"

# Or force reinstall
pip install --force-reinstall -e ".[dev]"
```

### Permission errors on Windows

Run PowerShell/Command Prompt as Administrator if you get permission errors during installation.

## Docker Alternative (Advanced)

If installation is problematic, use Docker:

```dockerfile
FROM python:3.11

# Install SWI-Prolog
RUN apt-get update && apt-get install -y swi-prolog

# Install BLANC
COPY . /blanc
WORKDIR /blanc
RUN pip install -e ".[dev]"

CMD ["python"]
```

Build and run:
```bash
docker build -t blanc .
docker run -it blanc
```

## Next Steps

After installation:

1. Read `README.md` for overview
2. Run `python examples/basic_usage.py` to see examples
3. Check `Guidance_Documents/` for detailed documentation
4. Explore `notebooks/BLANC_Tutorial.ipynb` (coming soon)
5. Download knowledge bases to `D:\datasets\` for research

## Support

If you encounter issues:

1. Check this INSTALL.md thoroughly
2. Review error messages carefully
3. Verify all prerequisites are installed
4. Check Python and SWI-Prolog architecture match (both 64-bit)
5. Consult backend documentation:
   - PySwip: https://pyswip.readthedocs.io/
   - Clingo: https://potassco.org/clingo/
   - SWI-Prolog: https://www.swi-prolog.org/

## Version Information

Tested with:
- Python 3.11, 3.12
- SWI-Prolog 9.0.x, 9.2.x
- Clingo 5.8.0
- PySwip 0.3.3
- Clorm 1.6.1

Last updated: February 5, 2026
