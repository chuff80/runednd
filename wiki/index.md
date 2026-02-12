# Runelore Wiki

This wiki is the canonical lore portal for the Rune setting.

## Start Here

Use these routes depending on what you are trying to do:

<div class="home-grid">
  <a class="home-card" href="entities/locations/">
    <h3>Location Atlas</h3>
    <p>Browse nations, cities, and regions first, then branch into people and events.</p>
  </a>
  <a class="home-card" href="entities/characters/">
    <h3>Character Codex</h3>
    <p>Track key figures by era, with links to sources and related locations.</p>
  </a>
  <a class="home-card" href="entities/organizations/">
    <h3>Organization Ledger</h3>
    <p>View factions, faiths, courts, and orders with supporting references.</p>
  </a>
  <a class="home-card" href="entities/history/">
    <h3>History Chronicle</h3>
    <p>Follow major conflicts and timeline anchors across source notes.</p>
  </a>
</div>

## Suggested Routes

1. New reader: [[entities/history|History Chronicle]] -> [[entities/locations|Location Atlas]] -> [[entities/characters|Character Codex]]
2. Session prep: [[lists/session-notes|Session Notes]] -> [[entities/locations|Location Atlas]] -> [[entities/organizations|Organization Ledger]]
3. Canon audit: [[reference/sources|Sources]] -> [[reference/extraction-report|Extraction Report]] -> [[lists/all-content|All Content]]

## Source Coverage

Primary source folders:

- `/Users/coryhuff/Documents/Codex/runelore/oldnotes`
- `/Users/coryhuff/Documents/Codex/runelore/runesite`
- `/Users/coryhuff/Documents/Codex/runelore/stories`
- `/Users/coryhuff/Documents/Codex/runelore/evernote`

## Workflow

1. Add source files.
2. Rebuild and validate from repository root:
   - `tools/rebuild_all.sh`
3. Preview locally:
   - `mkdocs serve`
