# Creates the local Python environment for binoculars.py (Windows).
# CPU build of PyTorch by default; pass -Cuda for an NVIDIA GPU build.
param([switch]$Cuda)

$ErrorActionPreference = "Stop"
$venv = Join-Path $env:LOCALAPPDATA "ai-detector\venv"
$index = if ($Cuda) { "https://download.pytorch.org/whl/cu124" } else { "https://download.pytorch.org/whl/cpu" }

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv venv --python 3.12 $venv
    uv pip install --python "$venv\Scripts\python.exe" --index-url $index torch
    uv pip install --python "$venv\Scripts\python.exe" "transformers>=4.56" accelerate safetensors
} else {
    python -m venv $venv
    & "$venv\Scripts\python.exe" -m pip install --index-url $index torch
    & "$venv\Scripts\python.exe" -m pip install "transformers>=4.56" accelerate safetensors
}

# Download both models once (about 1 GB each).
& "$venv\Scripts\python.exe" -c "from huggingface_hub import snapshot_download as d; [d(m) for m in ['Qwen/Qwen2.5-0.5B','Qwen/Qwen2.5-0.5B-Instruct']]"
Write-Host "Ready: $venv\Scripts\python.exe"
