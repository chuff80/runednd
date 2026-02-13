#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"

LOCATION_DIR = WIKI / "entities" / "locations"
CHARACTER_DIR = WIKI / "entities" / "characters"
HISTORY_DIR = WIKI / "entities" / "history"
ORGANIZATION_DIR = WIKI / "entities" / "organizations"
LOCATION_INDEX = WIKI / "entities" / "locations.md"
CHARACTER_INDEX = WIKI / "entities" / "characters.md"
HISTORY_INDEX = WIKI / "entities" / "history.md"
ORGANIZATION_INDEX = WIKI / "entities" / "organizations.md"
TEMPLATE_FILE = WIKI / "ENTITY_TEMPLATE.md"
AGENTS_FILE = ROOT / "AGENTS.md"

LOCATION_REQUIRED = [
    "## Overview",
    "## Notable People",
    "## Notable Places",
    "## Important Historical Events",
    "## Visual References",
    "## Canonical Sources",
    "## Where This Location Appears",
]

CHAR_AUTO_REQUIRED = [
    "## Overview",
    "## Notable Connections",
    "## Associated Locations",
    "## Important Historical Events",
    "## Visual References",
    "## Canonical Sources",
    "## Where This Character Appears",
]

CHAR_CURATED_REQUIRED = [
    "## Overview",
    "## Appearance",
    "## Key Relationships",
    "## Source Trail",
]

HISTORY_REQUIRED = [
    "## Overview",
    "## Belligerents and Key Figures",
    "## Timeline and Turning Points",
    "## Outcomes and Lasting Impact",
    "## Canonical Sources",
    "## Where This Event Appears",
]

ORGANIZATION_REQUIRED = [
    "## Overview",
    "## Beliefs",
    "## Practices and Structure",
    "## Notable Members",
    "## Associated Locations",
    "## Important Historical Events",
    "## Visual References",
    "## Canonical Sources",
    "## Where This Organization Appears",
]

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def fail(errors: list[str]) -> int:
    if not errors:
        print("Validation passed.")
        return 0
    print("Validation failed:")
    for err in errors:
        print(f"- {err}")
    return 1


def check_exists(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"Missing required file: {path}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def has_headings(text: str, headings: list[str]) -> list[str]:
    missing = []
    for h in headings:
        if h not in text:
            missing.append(h)
    return missing


def resolve_wikilink_target(raw_target: str, source_file: Path) -> Path:
    target = raw_target.strip()
    rel = Path(target)
    if rel.suffix == "":
        rel = rel.with_suffix(".md")
    return WIKI / rel


def validate_wikilinks(file_path: Path, text: str, errors: list[str]) -> None:
    for m in WIKILINK_RE.finditer(text):
        raw_target = m.group(1).strip()
        # Ignore template placeholder links such as [[...]] or [[raw/...]].
        if "..." in raw_target or "<" in raw_target or ">" in raw_target:
            continue
        target_path = resolve_wikilink_target(raw_target, file_path)
        if not target_path.exists():
            errors.append(
                f"Broken wikilink in {file_path.relative_to(ROOT)}: [[{raw_target}]] -> {target_path.relative_to(ROOT)}"
            )


def links_from_index(path: Path) -> set[str]:
    text = read_text(path)
    out: set[str] = set()
    for m in WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        out.add(target if target.endswith(".md") else f"{target}.md")
    return out


def rel_from_wiki(path: Path) -> str:
    return path.relative_to(WIKI).as_posix()


def main() -> int:
    errors: list[str] = []

    # Required guardrail files
    for p in [
        AGENTS_FILE,
        TEMPLATE_FILE,
        LOCATION_INDEX,
        CHARACTER_INDEX,
        HISTORY_INDEX,
        ORGANIZATION_INDEX,
    ]:
        check_exists(p, errors)

    # Entity directories
    if not LOCATION_DIR.exists() or not LOCATION_DIR.is_dir():
        errors.append(f"Missing location entity directory: {LOCATION_DIR}")
    if not CHARACTER_DIR.exists() or not CHARACTER_DIR.is_dir():
        errors.append(f"Missing character entity directory: {CHARACTER_DIR}")
    if not HISTORY_DIR.exists() or not HISTORY_DIR.is_dir():
        errors.append(f"Missing history entity directory: {HISTORY_DIR}")
    if not ORGANIZATION_DIR.exists() or not ORGANIZATION_DIR.is_dir():
        errors.append(f"Missing organization entity directory: {ORGANIZATION_DIR}")

    location_pages = sorted([p for p in LOCATION_DIR.glob("*.md") if p.is_file()])
    character_pages = sorted([p for p in CHARACTER_DIR.rglob("*.md") if p.is_file()])
    history_pages = sorted([p for p in HISTORY_DIR.glob("*.md") if p.is_file()])
    organization_pages = sorted([p for p in ORGANIZATION_DIR.glob("*.md") if p.is_file()])

    if not location_pages:
        errors.append("No location entity pages found.")
    if not character_pages:
        errors.append("No character entity pages found.")
    if not history_pages:
        errors.append("No history entity pages found.")
    # Validate headings and links per page
    for page in location_pages:
        text = read_text(page)
        missing = has_headings(text, LOCATION_REQUIRED)
        if missing:
            errors.append(
                f"Location page missing headings ({', '.join(missing)}): {page.relative_to(ROOT)}"
            )
        validate_wikilinks(page, text, errors)

    for page in character_pages:
        text = read_text(page)
        if "`Canon status:`" in text:
            required = CHAR_CURATED_REQUIRED
        else:
            required = CHAR_AUTO_REQUIRED
        missing = has_headings(text, required)
        if missing:
            errors.append(
                f"Character page missing headings ({', '.join(missing)}): {page.relative_to(ROOT)}"
            )
        validate_wikilinks(page, text, errors)

    for page in history_pages:
        text = read_text(page)
        if "`Canon status:`" not in text:
            errors.append(
                f"History page missing canon status line: {page.relative_to(ROOT)}"
            )
        missing = has_headings(text, HISTORY_REQUIRED)
        if missing:
            errors.append(
                f"History page missing headings ({', '.join(missing)}): {page.relative_to(ROOT)}"
            )
        validate_wikilinks(page, text, errors)

    for page in organization_pages:
        text = read_text(page)
        missing = has_headings(text, ORGANIZATION_REQUIRED)
        if missing:
            errors.append(
                f"Organization page missing headings ({', '.join(missing)}): {page.relative_to(ROOT)}"
            )
        validate_wikilinks(page, text, errors)

    # Validate index coverage
    if LOCATION_INDEX.exists():
        linked = links_from_index(LOCATION_INDEX)
        expected = {rel_from_wiki(p) for p in location_pages}
        missing_links = expected - linked
        if missing_links:
            errors.append(
                f"Location index missing links: {', '.join(sorted(missing_links))}"
            )

    if CHARACTER_INDEX.exists():
        linked = links_from_index(CHARACTER_INDEX)
        expected = {rel_from_wiki(p) for p in character_pages}
        missing_links = expected - linked
        if missing_links:
            errors.append(
                f"Character index missing links: {', '.join(sorted(missing_links))}"
            )

    if HISTORY_INDEX.exists():
        linked = links_from_index(HISTORY_INDEX)
        expected = {rel_from_wiki(p) for p in history_pages}
        missing_links = expected - linked
        if missing_links:
            errors.append(
                f"History index missing links: {', '.join(sorted(missing_links))}"
            )

    if ORGANIZATION_INDEX.exists():
        linked = links_from_index(ORGANIZATION_INDEX)
        expected = {rel_from_wiki(p) for p in organization_pages}
        missing_links = expected - linked
        if missing_links:
            errors.append(
                f"Organization index missing links: {', '.join(sorted(missing_links))}"
            )

    # Validate wiki links for top-level key docs
    for p in [
        WIKI / "index.md",
        LOCATION_INDEX,
        CHARACTER_INDEX,
        HISTORY_INDEX,
        ORGANIZATION_INDEX,
        TEMPLATE_FILE,
    ]:
        if p.exists():
            validate_wikilinks(p, read_text(p), errors)

    return fail(errors)


if __name__ == "__main__":
    raise SystemExit(main())
