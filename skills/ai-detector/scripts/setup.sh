#!/usr/bin/env sh
# Creates the local Python environment for binoculars.py (Linux/macOS).
# CPU build of PyTorch by default; run with CUDA=1 for an NVIDIA GPU build (Linux).
set -e
VENV="${HOME}/.local/share/ai-detector/venv"
if [ "${CUDA:-0}" = "1" ]; then INDEX="https://download.pytorch.org/whl/cu124"; else INDEX="https://download.pytorch.org/whl/cpu"; fi
# macOS wheels come from the default index.
[ "$(uname)" = "Darwin" ] && INDEX="https://pypi.org/simple"

if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 "$VENV"
  uv pip install --python "$VENV/bin/python" --index-url "$INDEX" torch
  uv pip install --python "$VENV/bin/python" "transformers>=4.56" accelerate safetensors
else
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --index-url "$INDEX" torch
  "$VENV/bin/python" -m pip install "transformers>=4.56" accelerate safetensors
fi

# Download both models once (about 1 GB each).
"$VENV/bin/python" -c "from huggingface_hub import snapshot_download as d; [d(m) for m in ['Qwen/Qwen2.5-0.5B','Qwen/Qwen2.5-0.5B-Instruct']]"
echo "Ready: $VENV/bin/python"
