# Runelore Wiki

This wiki is a local index of your homebrew content across:

- `/Users/coryhuff/Documents/Codex/runelore/oldnotes`
- `/Users/coryhuff/Documents/Codex/runelore/runesite`
- `/Users/coryhuff/Documents/Codex/runelore/stories`

Use the `Lists` section for category views and full-text search.

Start here for a Wikipedia-style browse experience:

- `[[entities/locations|Location Atlas]]`
- `[[entities/characters|Character Codex]]`
- `[[entities/history|History Chronicle]]`

## Workflow

1. Add files to your source folders.
2. Extract markdown from source files:
   - `python3 tools/extract_markdown.py`
3. Rebuild the index:
   - `python3 tools/build_wiki_index.py`
4. Rebuild entities:
   - `python3 tools/build_location_hubs.py`
   - `python3 tools/build_character_hubs.py`
5. Preview locally:
   - `mkdocs serve`
