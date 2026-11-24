#!/usr/bin/env bash
# Transcribe every sources/<id>/<id>.webm to work/transcripts/<id>.json (word timestamps).
# Skips files already transcribed. Shortest files first.
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-mlx-community/whisper-large-v3-turbo}"
OUT=work/transcripts
mkdir -p "$OUT"

for f in $(ls -Sr sources/*/*.webm); do
  id=$(basename "$f" .webm)
  if [[ -s "$OUT/$id.json" ]]; then echo "skip $id"; continue; fi
  echo "=== $id ($(date +%H:%M:%S))"
  mlx_whisper "$f" \
    --model "$MODEL" \
    --language en \
    --word-timestamps True \
    --condition-on-previous-text False \
    --hallucination-silence-threshold 2 \
    --output-format json \
    --output-dir "$OUT" \
    --output-name "$id" \
    --verbose False
done
echo "done ($(date +%H:%M:%S))"
