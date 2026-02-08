#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

echo "[1/5] Extract markdown"
"$PY" "$ROOT/tools/extract_markdown.py"

echo "[2/5] Build content indexes"
"$PY" "$ROOT/tools/build_wiki_index.py"

echo "[3/5] Build location entities"
"$PY" "$ROOT/tools/build_location_hubs.py"

echo "[4/5] Build character entities"
"$PY" "$ROOT/tools/build_character_hubs.py"

echo "[5/5] Validate wiki"
"$PY" "$ROOT/tools/validate_wiki.py"

echo "Rebuild complete."
