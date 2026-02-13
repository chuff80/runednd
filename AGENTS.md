# Runelore Wiki Guardrails

This file defines the canonical rules for this repository so future sessions produce consistent output.

## Canonical Workflow

Always run work from repository root:

- `/Users/coryhuff/Documents/Codex/runelore`

Preferred full rebuild command:

- `tools/rebuild_all.sh`

Manual equivalent sequence:

1. `python3 tools/extract_markdown.py`
2. `python3 tools/build_wiki_index.py`
3. `python3 tools/build_location_hubs.py`
4. `python3 tools/build_character_hubs.py`
5. `python3 tools/validate_wiki.py`

## Output Contract

All generated/curated entity pages must be stored under:

- `wiki/entities/locations/*.md`
- `wiki/entities/characters/*.md`
- `wiki/entities/history/*.md`
- `wiki/entities/organizations/*.md`

Indexes must be kept current:

- `wiki/entities/locations.md`
- `wiki/entities/characters.md`
- `wiki/entities/history.md`
- `wiki/entities/organizations.md`

Use Obsidian wiki-links (`[[path|label]]`) for internal linking.

## Formatting Rules

Use `/Users/coryhuff/Documents/Codex/runelore/wiki/ENTITY_TEMPLATE.md` as the source of truth for section layout.

Location pages must include at minimum:

- `## Overview`
- `## Notable People`
- `## Notable Places`
- `## Important Historical Events`
- `## Canonical Sources`
- `## Where This Location Appears`

Character pages have two supported schemas:

1. Auto/generated schema:
- `## Overview`
- `## Notable Connections`
- `## Associated Locations`
- `## Important Historical Events`
- `## Canonical Sources`
- `## Where This Character Appears`

2. Curated/gold schema (manual pages):
- include a `Canon status` line near the top
- include `## Overview`
- include `## Appearance`
- include `## Key Relationships`
- include `## Source Trail`

3. History event schema (manual pages):
- include a `Canon status` line near the top
- include `## Overview`
- include `## Belligerents and Key Figures`
- include `## Timeline and Turning Points`
- include `## Outcomes and Lasting Impact`
- include `## Canonical Sources`
- include `## Where This Event Appears`

4. Organization schema (auto pages):
- include `## Overview`
- include `## Beliefs`
- include `## Practices and Structure`
- include `## Notable Members`
- include `## Associated Locations`
- include `## Important Historical Events`
- include `## Canonical Sources`
- include `## Where This Organization Appears`

## Validation Requirements

Before considering work complete, run:

- `python3 tools/validate_wiki.py`

Validation must pass with exit code `0`.

## Dependency Pinning

Use pinned dependencies in:

- `requirements.txt`

For local setup:

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python3 -m pip install -r requirements.txt`

## Editing Policy

- Prefer script/config changes over ad-hoc manual rewrites.
- Preserve curated pages (do not overwrite manually curated gold pages).
- If a generator changes schema, update template + validator in the same change.
