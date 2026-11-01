#!/usr/bin/env bash
# One-time setup per (fresh) machine: Python packages + German Piper voice (~115 MB, cached).
set -e
pip install -q --break-system-packages piper-tts soundfile numpy 2>/dev/null || pip install -q piper-tts soundfile numpy
M="${SN_MODELS:-$HOME/.cache/swiss-news/models}"
mkdir -p "$M"
V=vits-piper-de_DE-thorsten-high
if [ ! -s "$M/$V/de_DE-thorsten-high.onnx" ]; then
  curl -sSL -o "$M/$V.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$V.tar.bz2"
  tar xjf "$M/$V.tar.bz2" -C "$M" && rm "$M/$V.tar.bz2"
fi
python3 -c "import playwright, piper, soundfile" && which ffmpeg >/dev/null && echo "setup ok"
