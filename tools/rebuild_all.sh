#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

echo "[1/7] Extract markdown"
"$PY" "$ROOT/tools/extract_markdown.py"

echo "[2/7] Build image manifest"
"$PY" "$ROOT/tools/build_image_manifest.py"

echo "[3/7] Build content indexes"
"$PY" "$ROOT/tools/build_wiki_index.py"

echo "[4/7] Build location entities"
"$PY" "$ROOT/tools/build_location_hubs.py"

echo "[5/7] Build character entities"
"$PY" "$ROOT/tools/build_character_hubs.py"

echo "[6/7] Build organization entities"
"$PY" "$ROOT/tools/build_organization_hubs.py"

echo "[7/7] Validate wiki"
"$PY" "$ROOT/tools/validate_wiki.py"

echo "Rebuild complete."
