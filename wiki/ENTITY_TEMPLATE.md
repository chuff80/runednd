# Entity Templates

This file defines the expected markdown structure for entity pages.

## Location Template

```md
# <Location Name>

## Overview
<2-3 sentence summary>

## Notable People
- <Name> (<count> mentions)

## Notable Places
- <Place> (<count> mentions)

## Important Historical Events
- <Event> (<count> references; sample sources: [[...]], [[...]])

## Canonical Sources
- Source file: `<source path>`
- Extracted text: [[raw/...|...]]

## Where This Location Appears
- [[raw/...|raw/...]] - <excerpt>
```

## Character Template (Auto)

```md
# <Character Name>

## Overview
<2-3 sentence summary>

## Notable Connections
- <Name> (<count> mentions)

## Associated Locations
- <Location> (<count> mentions)

## Important Historical Events
- <Event> (<count> references; sample sources: [[...]], [[...]])

## Canonical Sources
- Source file: `<source path>`
- Extracted text: [[raw/...|...]]

## Where This Character Appears
- [[raw/...|raw/...]] - <excerpt>
```

## Character Template (Curated Gold)

```md
# <Character Name>

`Canon status:` <statement about synthesis/confidence>

## Overview
<curated narrative summary>

## Appearance
<physical presentation, identifying traits, clothing/gear style, and notable changes over time>

## Identity Snapshot
| Field | Value |
|---|---|
| ... | ... |

## Key Relationships
| Person / Group | Relationship | Notes |
|---|---|---|
| ... | ... | ... |

## Source Trail
- [[raw/...|...]]
- [[raw/...|...]]
```

## History Event Template

```md
# <Event Name>

`Canon status:` <statement about synthesis/confidence>

## Overview
<concise summary of the event and why it matters>

## Belligerents and Key Figures
- <Faction/person> - <role in event>

## Timeline and Turning Points
1. <phase or milestone>
2. <phase or milestone>

## Outcomes and Lasting Impact
- <major outcome>

## Canonical Sources
- [[raw/...|...]]

## Where This Event Appears
- [[raw/...|...]] - <brief relevance note>
```

## Organization Template (Auto)

```md
# <Organization Name>

## Overview
<2-3 sentence summary>

## Beliefs
- <Source-backed belief/tenet statement>

## Practices and Structure
- <Source-backed structure, rites, institutions, or operations statement>

## Notable Members
- <Name> (<count> mentions)

## Associated Locations
- <Location> (<count> mentions)

## Important Historical Events
- <Event> (<count> references; sample sources: [[...]], [[...]])

## Canonical Sources
- [[raw/...|...]]

## Where This Organization Appears
- [[raw/...|raw/...]] - <excerpt>
```

## Notes

- Prefer concise sections and stable headings.
- Keep speculative content explicitly labeled.
- Always include a source trail on curated pages.
