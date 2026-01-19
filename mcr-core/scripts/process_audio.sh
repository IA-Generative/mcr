#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <meeting_id>"
  exit 1
fi

MEETING_ID="$1"

./download_chunk.sh --prefix "audio/${MEETING_ID}" --dest "${MEETING_ID}/"

cd "${MEETING_ID}"

echo "→ Fusion des fichiers .weba..."
if ! cat *.weba | ffmpeg -i - -c copy output.webm; then
  echo "⚠️ Erreur ffmpeg : il est possible que l'ordre des fichiers *.weba soit incorrect."
  exit 1
fi

echo "→ Ouverture VLC..."
open -a VLC output.webm