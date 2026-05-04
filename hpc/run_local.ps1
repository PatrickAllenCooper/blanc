# Local evaluation runner for DeFAb (PowerShell / Windows).
#
# Equivalent to the SLURM scripts but with no cluster dependencies.
# Reads credentials from .env at the project root.
#
# Supported providers:
#   openai         - GPT-4o via OpenAI API          (requires OPENAI_API_KEY)
#   anthropic      - Claude via Anthropic API        (requires ANTHROPIC_API_KEY)
#   google         - Gemini via Google API           (requires GOOGLE_API_KEY)
#   azure          - GPT-4o via Azure OpenAI         (requires AZURE_OPENAI_* vars)
#   ollama         - Local model via Ollama          (requires Ollama running locally)
#   curc           - CURC vLLM via SSH tunnel        (requires CURC_VLLM_BASE_URL)
#   foundry-gpt    - gpt-5.2-chat via Foundry       (requires FOUNDRY_API_KEY)
#   foundry-kimi   - Kimi-K2.5 via Foundry          (requires FOUNDRY_API_KEY)
#   foundry-claude - claude-sonnet-4-6 via Foundry  (requires FOUNDRY_API_KEY)
#   foundry        - Run all three Foundry models    (requires FOUNDRY_API_KEY)
#   mock           - Deterministic fake model        (no credentials needed)
#
# Usage:
#   .\hpc\run_local.ps1 [[-Provider] <string>] [options]
#
# Examples:
#   .\hpc\run_local.ps1 openai
#   .\hpc\run_local.ps1 anthropic -InstanceLimit 20 -Modalities "M4"
#   .\hpc\run_local.ps1 ollama -OllamaModel llama3:8b
#   .\hpc\run_local.ps1 mock -InstanceLimit 5
#   .\hpc\run_local.ps1  # auto-detects from .env
#
# Author: Anonymous Authors
# Date: 2026-02-19

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("openai", "anthropic", "google", "azure", "ollama", "curc",
                 "foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek", "foundry",
                 "mock", "")]
    [string]$Provider = "",

    [int]$InstanceLimit  = 20,
    [string]$Modalities  = "M4 M2",
    [string]$Strategies  = "direct cot",
    [bool]$IncludeLevel3 = $true,
    [int]$Level3Limit    = 20,
    [string]$OllamaModel = "",
    [string]$OllamaHost  = "http://localhost:11434",

    # Pass any extra args directly to run_evaluation.py
    [string[]]$ExtraArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Locate project root
# ---------------------------------------------------------------------------
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjDir    = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjDir

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
$EnvFile = Join-Path $ProjDir ".env"
$EnvVars = @{}

if (Test-Path $EnvFile) {
    Write-Host "Loaded credentials from .env"
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*([A-Z_][A-Z0-9_]*)=(.+)$') {
            $key   = $Matches[1]
            $value = $Matches[2].Trim()
            $EnvVars[$key] = $value
            # Also set in current process environment for subprocess access
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Host "Note: no .env file found at $EnvFile"
    Write-Host "      Create one from .env.template and fill in your credentials."
}

function Get-EnvVal([string]$Key, [string]$Default = "") {
    if ($EnvVars.ContainsKey($Key)) { return $EnvVars[$Key] }
    $fromEnv = [System.Environment]::GetEnvironmentVariable($Key)
    if ($fromEnv) { return $fromEnv }
    return $Default
}

# ---------------------------------------------------------------------------
# Provider auto-detection
# ---------------------------------------------------------------------------
if ($Provider -eq "") {
    # Prefer Foundry when key is available
    if (Get-EnvVal "FOUNDRY_API_KEY")      { $Provider = "foundry" }
    elseif (Get-EnvVal "OPENAI_API_KEY")   { $Provider = "openai" }
    elseif (Get-EnvVal "ANTHROPIC_API_KEY") { $Provider = "anthropic" }
    elseif (Get-EnvVal "GOOGLE_API_KEY")    { $Provider = "google" }
    elseif (Get-EnvVal "AZURE_OPENAI_API_KEY") { $Provider = "azure" }
    else {
        Write-Error ("No provider specified and no API key found in .env or environment.`n" +
                     "Pass a provider name as the first argument, or set one in .env.`n" +
                     "Use 'mock' for a credential-free dry run.")
        exit 1
    }
    Write-Host "Auto-detected provider: $Provider"
}

# ---------------------------------------------------------------------------
# 'foundry' meta-provider: run all three models sequentially
# ---------------------------------------------------------------------------
if ($Provider -eq "foundry") {
    $FoundryKey = Get-EnvVal "FOUNDRY_API_KEY"
    if (-not $FoundryKey) { Write-Error "FOUNDRY_API_KEY not set."; exit 1 }
    Write-Host "Running all three Foundry models sequentially..."
    $OverallExit = 0
    foreach ($Sub in @("foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek")) {
        & $MyInvocation.MyCommand.Path $Sub `
            -InstanceLimit $InstanceLimit -Modalities $Modalities `
            -Strategies $Strategies -IncludeLevel3 $IncludeLevel3 `
            -Level3Limit $Level3Limit
        if ($LASTEXITCODE -ne 0) { $OverallExit = $LASTEXITCODE }
    }
    exit $OverallExit
}

# ---------------------------------------------------------------------------
# Timestamp and directories
# ---------------------------------------------------------------------------
$Timestamp  = (Get-Date -Format "yyyyMMdd_HHmmss")
$ResultsDir = "experiments\results\local_${Provider}_${Timestamp}"
$CacheDir   = "experiments\cache\local_${Provider}"
$Checkpoint = "$ResultsDir\checkpoint.json"

New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir   | Out-Null
New-Item -ItemType Directory -Force -Path "logs"      | Out-Null

Write-Host "======================================================================="
Write-Host "DeFAb Local Evaluation"
Write-Host "======================================================================="
Write-Host "Provider      : $Provider"
Write-Host "Instance limit: $InstanceLimit per domain"
Write-Host "Modalities    : $Modalities"
Write-Host "Strategies    : $Strategies"
Write-Host "Level 3       : $IncludeLevel3 (limit: $Level3Limit)"
Write-Host "Results dir   : $ResultsDir"
Write-Host "Started       : $(Get-Date)"
Write-Host "======================================================================="
Write-Host ""

# ---------------------------------------------------------------------------
# Build provider-specific arguments
# ---------------------------------------------------------------------------
$ProviderArgs = @()

switch ($Provider) {
    "openai" {
        $key = Get-EnvVal "OPENAI_API_KEY"
        if (-not $key) { Write-Error "OPENAI_API_KEY not set."; exit 1 }
        $model = Get-EnvVal "OPENAI_MODEL" "gpt-4o"
        $ProviderArgs += "--api-key", $key, "--model", $model
    }

    "anthropic" {
        $key = Get-EnvVal "ANTHROPIC_API_KEY"
        if (-not $key) { Write-Error "ANTHROPIC_API_KEY not set."; exit 1 }
        $model = Get-EnvVal "ANTHROPIC_MODEL" "claude-3-5-sonnet-20241022"
        $ProviderArgs += "--api-key", $key, "--model", $model
    }

    "google" {
        $key = Get-EnvVal "GOOGLE_API_KEY"
        if (-not $key) { Write-Error "GOOGLE_API_KEY not set."; exit 1 }
        $model = Get-EnvVal "GOOGLE_MODEL" "gemini-1.5-pro"
        $ProviderArgs += "--api-key", $key, "--model", $model
    }

    "azure" {
        $key        = Get-EnvVal "AZURE_OPENAI_API_KEY"
        $endpoint   = Get-EnvVal "AZURE_OPENAI_ENDPOINT"
        $deployment = Get-EnvVal "AZURE_OPENAI_DEPLOYMENT"
        $apiVersion = Get-EnvVal "AZURE_OPENAI_API_VERSION" "2024-08-01-preview"
        if (-not $key)        { Write-Error "AZURE_OPENAI_API_KEY not set.";    exit 1 }
        if (-not $endpoint)   { Write-Error "AZURE_OPENAI_ENDPOINT not set.";   exit 1 }
        if (-not $deployment) { Write-Error "AZURE_OPENAI_DEPLOYMENT not set."; exit 1 }
        $ProviderArgs += "--api-key", $key, "--endpoint", $endpoint,
                         "--deployment", $deployment, "--api-version", $apiVersion
    }

    "ollama" {
        if (-not $OllamaModel) { $OllamaModel = Get-EnvVal "OLLAMA_MODEL" "llama3:8b" }
        # Check server reachable
        try {
            $null = Invoke-WebRequest -Uri "$OllamaHost/api/tags" -UseBasicParsing -TimeoutSec 5
        } catch {
            Write-Error ("Ollama server not reachable at $OllamaHost`n" +
                         "Start it with: ollama serve`n" +
                         "Then pull a model: ollama pull $OllamaModel")
            exit 1
        }
        $ProviderArgs += "--model", $OllamaModel, "--ollama-host", $OllamaHost
    }

    "curc" {
        $baseUrl = Get-EnvVal "CURC_VLLM_BASE_URL" "http://localhost:8000"
        $model   = Get-EnvVal "CURC_VLLM_MODEL" "Qwen/Qwen2.5-72B-Instruct-AWQ"
        try {
            $null = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -TimeoutSec 5
        } catch {
            Write-Error ("CURC vLLM server not reachable at $baseUrl`n" +
                         "Create an SSH tunnel first. See .env.template for instructions.")
            exit 1
        }
        $ProviderArgs += "--curc-base-url", $baseUrl, "--model", $model
    }

    { $_ -in "foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek" } {
        $key = Get-EnvVal "FOUNDRY_API_KEY"
        if (-not $key) { Write-Error "FOUNDRY_API_KEY not set."; exit 1 }
        $ProviderArgs += "--api-key", $key
    }

    "mock" {
        # No credentials required
    }
}

# ---------------------------------------------------------------------------
# Level 3 arguments
# ---------------------------------------------------------------------------
$Level3Args = @()
if ($IncludeLevel3) {
    $Level3Args = @("--include-level3", "--level3-limit", "$Level3Limit")
}

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
$PythonArgs = @(
    "experiments/run_evaluation.py",
    "--provider",       $Provider,
    "--modalities"
) + ($Modalities -split '\s+') + @(
    "--strategies"
) + ($Strategies -split '\s+') + @(
    "--instance-limit", "$InstanceLimit",
    "--results-dir",    $ResultsDir,
    "--cache-dir",      $CacheDir,
    "--checkpoint",     $Checkpoint
) + $ProviderArgs + $Level3Args + $ExtraArgs

Write-Host "Starting evaluation..."
python @PythonArgs
$EvalExit = $LASTEXITCODE

# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
if ($EvalExit -eq 0 -and (Test-Path $ResultsDir)) {
    Write-Host ""
    Write-Host "Running analysis..."
    python experiments/analyze_results.py `
        --results-dir $ResultsDir `
        --save "$ResultsDir\summary.json" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  (analyze_results.py: non-fatal error, skipping)"
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "======================================================================="
Write-Host "Evaluation Complete"
Write-Host "======================================================================="
Write-Host "End      : $(Get-Date)"
Write-Host "Exit code: $EvalExit"
Write-Host "Results  : $ResultsDir"
Write-Host ""

$SummaryFile = "$ResultsDir\summary.json"
if (Test-Path $SummaryFile) {
    python -c @"
import json
with open(r'$SummaryFile') as f:
    s = json.load(f)
overall = s.get('overall', {})
acc    = overall.get('accuracy', 'n/a')
robust = s.get('rendering_robust_accuracy', 'n/a')
n      = overall.get('total', 'n/a')
print(f'  Overall accuracy          : {acc}')
print(f'  Rendering-robust accuracy : {robust}')
print(f'  Total evaluations         : {n}')
"@ 2>$null
}

exit $EvalExit
