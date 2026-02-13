#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from image_utils import (
    append_visual_references,
    collect_assets_for_raw_docs,
    collect_assets_for_sources,
    load_image_maps,
    merge_asset_lists,
)

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = WIKI / "raw"
HUB_ROOT = WIKI / "entities" / "locations"
INDEX_PAGE = WIKI / "entities" / "locations.md"
LOCATIONS_LIST = WIKI / "lists" / "locations.md"

DEFAULT_SUMMARY_CHARS = 0
DEFAULT_MENTION_CHARS = 260
DEFAULT_EVENT_THRESHOLD = 3
DEFAULT_VISIBLE_MENTIONS = 8

PLACE_HINT_WORDS = {
    "city",
    "kingdom",
    "river",
    "forest",
    "mountain",
    "mountains",
    "inn",
    "temple",
    "school",
    "church",
    "council",
    "bay",
    "port",
    "states",
    "rift",
    "quarter",
    "gate",
    "gates",
    "swamp",
    "plains",
    "lodge",
    "dump",
    "harbor",
    "harbour",
}

PERSON_CONTEXT_KEYWORDS = {
    "king",
    "queen",
    "prince",
    "princess",
    "lord",
    "lady",
    "general",
    "captain",
    "wizard",
    "druid",
    "leader",
    "member",
    "friend",
    "brother",
    "sister",
    "named",
    "called",
    "warlord",
    "archfey",
    "fence",
    "dragon",
    "barkeep",
}

PERSON_STOPWORDS = {
    "rune",
    "campaign",
    "calendar",
    "more",
    "navigation",
    "main",
    "content",
    "important",
    "current",
    "year",
    "history",
    "npcs",
    "organizations",
    "they",
    "there",
    "what",
    "this",
    "that",
    "these",
    "those",
    "who",
    "whom",
    "when",
    "where",
    "which",
    "also",
    "many",
    "most",
    "some",
    "none",
    "both",
    "another",
    "other",
    "after",
    "before",
    "creator",
    "sidhe",
    "ogham",
    "feywild",
    "dubhaine",
    "tuatha",
    "domhaine",
    "gibard",
    "ghealdar",
    "atania",
    "states",
    "gaeas",
    "hartland",
    "gaoth",
    "empire",
    "court",
    "parliament",
    "kingdom",
    "city",
    "council",
    "guild",
    "college",
}

EVENT_KEYWORDS = {
    "war",
    "battle",
    "apocalypse",
    "destruction",
    "reconciliation",
    "collapse",
    "uprising",
    "protest",
    "flood",
    "curse",
    "cleansing",
    "occupation",
    "exodus",
    "siege",
    "revolt",
    "cataclysm",
    "vengeance",
    "massacre",
    "founding",
    "fall",
}

TITLE_ONLY_WORDS = {
    "king",
    "queen",
    "prince",
    "princess",
    "lord",
    "lady",
    "general",
    "captain",
    "archmage",
    "wizard",
    "druid",
    "emperor",
    "empress",
    "commander",
    "warlord",
}

SPECIAL_PLACE_NAMES = {
    "the maw",
    "the dump",
    "the thir",
}

PERSON_TITLE_RE = re.compile(
    r"\b(?:King|Queen|Prince|Princess|Lord|Lady|General|Captain|Archmage|Wizard|Druid|Emperor|Empress)\s+([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2})\b"
)
PROPER_NOUN_RE = re.compile(
    r"\b([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2})\b"
)

PLACE_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,3}\s+(?:City|Kingdom|River|Forest|Mountains?|Inn|Temple|School|Church|Council|Bay|Port|States?|Rift|Quarter|Gates?|Swamp|Plains|Lodge|Dump|Harbor|Harbour))\b"
    ),
    re.compile(
        r"\b([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,3}\s+of\s+(?:the\s+)?[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2})\b"
    ),
    re.compile(r"\b(The\s+[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2})\b"),
]

EVENT_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,5}\s+(?:War|Battle|Apocalypse|Destruction|Reconciliation|Collapse|Uprising|Protest|Flood|Curse|Cleansing|Occupation|Exodus|Siege|Revolt|Cataclysm|Vengeance|Massacre))\b"
    ),
    re.compile(
        r"\b((?:Battle|Fall|Closure|Founding|Rise|Siege|Return)\s+of\s+(?:the\s+)?[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,4})\b"
    ),
    re.compile(
        r"\b(elemental apocalypse|great destruction|hartland war|curse of badb|fey wars|raven queen(?:'s)? vengeance|closure of the shadowfell rift|reconciliation)\b",
        flags=re.IGNORECASE,
    ),
]

EVENT_DATE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bgaeas\b", flags=re.IGNORECASE), "Recorded History begins (0 AG)"),
    (re.compile(r"\breconcil(?:er|iation)\b", flags=re.IGNORECASE), "695 AG"),
    (re.compile(r"\braven queen(?:'s)? war\b", flags=re.IGNORECASE), "1380 AG"),
    (re.compile(r"\bgreat destruction\b", flags=re.IGNORECASE), "1385 AG"),
    (re.compile(r"\bgibbard empire emerges\b", flags=re.IGNORECASE), "1435 AG"),
    (re.compile(r"\bgibbard empire collapses\b", flags=re.IGNORECASE), "1885 AG"),
    (re.compile(r"\bhartland war\b", flags=re.IGNORECASE), "c. 1000 years before 0 AG (pre-recorded)"),
]


@dataclass
class Location:
    name: str
    source_rel: Path
    extracted_rel: Path


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "location"


def is_noise_location_name(name: str) -> bool:
    # Exclude hashed image names from the location list.
    compact = re.sub(r"[^a-zA-Z0-9]", "", name)
    return len(compact) >= 24 and re.fullmatch(r"[A-Fa-f0-9]+", compact) is not None


def parse_locations() -> list[Location]:
    if not LOCATIONS_LIST.exists():
        return []

    lines = LOCATIONS_LIST.read_text(encoding="utf-8").splitlines()
    locations: list[Location] = []
    for line in lines:
        if not line.startswith("| ") or line.startswith("|---"):
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        title, file_type, _source, source_path, extracted = cells[:5]
        if file_type != "`html`":
            continue
        if is_noise_location_name(title):
            continue

        # extracted cell is markdown link: [md](../raw/...)
        m = re.search(r"\]\(\.\./(.+)\)", extracted)
        if not m:
            continue
        extracted_rel = Path(m.group(1))
        locations.append(
            Location(
                name=title,
                source_rel=Path(source_path.strip("`")),
                extracted_rel=extracted_rel,
            )
        )
    return locations


def all_raw_docs() -> list[Path]:
    if not RAW.exists():
        return []
    docs = [p for p in RAW.rglob("*.md") if p.is_file()]
    docs.sort(key=lambda p: str(p).lower())
    return docs


def strip_markdown_metadata(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for ln in lines:
        if ln.startswith("# "):
            continue
        if ln.startswith("- Source:"):
            continue
        if ln.startswith("- Extracted:"):
            continue
        if ln.startswith("- Note:"):
            continue
        out.append(ln)
    return "\n".join(out).strip()


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def summarize(text: str, max_chars: int = 900) -> str:
    cleaned = normalize_space(text)
    if max_chars <= 0:
        return cleaned
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def split_sentences(text: str) -> list[str]:
    compressed = normalize_space(text.replace("\n", " "))
    if not compressed:
        return []
    parts = re.split(r"(?<=[.!?])\s+", compressed)
    return [p.strip() for p in parts if p.strip()]


def format_title_case(phrase: str) -> str:
    small = {"of", "the", "and", "in", "to", "for"}
    words = phrase.split()
    if not words:
        return phrase
    out: list[str] = []
    for i, word in enumerate(words):
        if i > 0 and word.lower() in small:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


def clean_entity_name(name: str) -> str:
    cleaned = normalize_space(name.strip(" ,.;:!?()[]{}\""))
    cleaned = re.sub(r"(?:'s|’s)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+The$", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def normalize_lookup_name(name: str) -> str:
    cleaned = normalize_space(name)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned.lower())
    return normalize_space(cleaned)


def is_low_signal_text(text: str) -> bool:
    lower = text.lower()
    if "skip to main content" in lower and len(text) < 1800:
        return True
    if lower.count("rune campaign") >= 3 and len(text) < 2200:
        return True
    return False


def build_overview(text: str, max_chars: int = 0) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return "_No summary available yet._"
    count = 3 if len(sentences) >= 3 else len(sentences)
    overview = " ".join(sentences[:count])
    return summarize(overview, max_chars=max_chars)


def collect_location_docs(location: Location, docs: list[Path]) -> list[tuple[Path, str]]:
    pattern = re.compile(rf"\b{re.escape(location.name)}\b", re.IGNORECASE)
    matches: list[tuple[Path, str]] = []
    canonical = (WIKI / location.extracted_rel).resolve()

    for doc in docs:
        if doc.resolve() == canonical:
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp)\.md$", doc.name, re.IGNORECASE):
            continue
        text = strip_markdown_metadata(doc.read_text(encoding="utf-8", errors="replace"))
        if not text or is_low_signal_text(text):
            continue
        if not pattern.search(text):
            continue
        matches.append((doc, text))

    matches.sort(key=lambda x: str(x[0]).lower())
    return matches


def build_mentions(
    location: Location, doc_texts: list[tuple[Path, str]], mention_chars: int
) -> list[tuple[Path, str]]:
    pattern = re.compile(rf"\b{re.escape(location.name)}\b", re.IGNORECASE)
    mentions: list[tuple[Path, str]] = []
    for doc, text in doc_texts:
        m = pattern.search(text)
        if not m:
            continue
        start = max(0, m.start() - 140)
        end = min(len(text), m.end() + 260)
        excerpt = summarize(text[start:end], max_chars=mention_chars)
        excerpt = excerpt.replace("Skip to main content", "").replace("Skip to navigation", "")
        mentions.append((doc, excerpt.strip()))
    return mentions


def add_count(
    counts: dict[str, int], display: dict[str, str], name: str, amount: int = 1
) -> None:
    key = name.lower()
    counts[key] = counts.get(key, 0) + amount
    if key not in display:
        display[key] = name


def sorted_counts(counts: dict[str, int], display: dict[str, str]) -> list[tuple[str, int]]:
    items = [(display[key], count) for key, count in counts.items()]
    return sorted(items, key=lambda x: (-x[1], x[0].lower()))


def looks_like_person(name: str, location_names_lower: set[str]) -> bool:
    if not name or any(ch.isdigit() for ch in name):
        return False
    words = name.split()
    if not words or len(words) > 3:
        return False
    if words[0].lower() in {"the", "a", "an"}:
        return False
    if name.lower() in location_names_lower:
        return False
    if all(w.lower() in TITLE_ONLY_WORDS for w in words):
        return False
    if len(words) == 1 and words[0].lower() in TITLE_ONLY_WORDS:
        return False
    if all(w.lower() in PERSON_STOPWORDS for w in words):
        return False
    if len(words) == 1 and words[0].lower() in EVENT_KEYWORDS:
        return False
    if any(w.lower() in PLACE_HINT_WORDS for w in words):
        return False
    return True


def extract_notable_people(
    canonical_text: str,
    other_docs: list[tuple[Path, str]],
    location_names: Iterable[str],
) -> list[tuple[str, int]]:
    location_names_lower = {n.lower() for n in location_names}
    counts: dict[str, int] = {}
    display: dict[str, str] = {}

    for text in [canonical_text] + [t for _, t in other_docs]:
        for sentence in split_sentences(text):
            sentence_lower = sentence.lower()
            has_context = any(k in sentence_lower for k in PERSON_CONTEXT_KEYWORDS)

            for m in PERSON_TITLE_RE.finditer(sentence):
                candidate = clean_entity_name(m.group(1))
                if looks_like_person(candidate, location_names_lower):
                    add_count(counts, display, candidate, amount=2)

            if not has_context:
                continue

            for m in PROPER_NOUN_RE.finditer(sentence):
                candidate = clean_entity_name(m.group(1))
                words = candidate.split()
                if len(words) == 1 and words[0].lower() in PERSON_STOPWORDS:
                    continue
                if len(words) == 1 and len(words[0]) < 4:
                    continue
                if looks_like_person(candidate, location_names_lower):
                    add_count(counts, display, candidate, amount=1)

    return sorted_counts(counts, display)[:18]


def looks_like_place(
    name: str,
    location_names_lower: set[str],
    people_names_lower: set[str],
    current_location_lower: str,
) -> bool:
    if not name or any(ch.isdigit() for ch in name):
        return False
    lowered = name.lower()
    if lowered in people_names_lower:
        return False
    if lowered == current_location_lower:
        return False
    if lowered in {"rune campaign", "skip to main content", "skip to navigation"}:
        return False
    if any(re.search(rf"\b{re.escape(h)}\b", lowered) for h in PLACE_HINT_WORDS):
        return True
    if lowered in location_names_lower and lowered != current_location_lower:
        return True
    if lowered in SPECIAL_PLACE_NAMES:
        return True
    return False


def extract_notable_places(
    canonical_text: str,
    location_names: Iterable[str],
    people: list[tuple[str, int]],
    current_location: str,
) -> list[tuple[str, int]]:
    location_names_lower = {n.lower() for n in location_names}
    people_names_lower = {name.lower() for name, _ in people}
    current_location_lower = current_location.lower()
    counts: dict[str, int] = {}
    display: dict[str, str] = {}

    for pattern in PLACE_PATTERNS:
        for m in pattern.finditer(canonical_text):
            candidate = clean_entity_name(m.group(1))
            if looks_like_place(
                candidate,
                location_names_lower=location_names_lower,
                people_names_lower=people_names_lower,
                current_location_lower=current_location_lower,
            ):
                add_count(counts, display, candidate, amount=1)

    # Include known location names referenced in the article body.
    for loc_name in location_names:
        if loc_name.lower() == current_location_lower:
            continue
        if re.search(rf"\b{re.escape(loc_name)}\b", canonical_text, flags=re.IGNORECASE):
            add_count(counts, display, loc_name, amount=2)

    return sorted_counts(counts, display)[:14]


def clean_event_name(name: str) -> str:
    cleaned = clean_entity_name(name)
    cleaned = re.sub(r"^(the)\s+", "", cleaned, flags=re.IGNORECASE)
    if not cleaned:
        return ""
    if cleaned.islower():
        cleaned = format_title_case(cleaned)
    return cleaned


def looks_like_event(event_name: str) -> bool:
    lower = event_name.lower()
    if not lower:
        return False
    if len(lower) < 6:
        return False
    return any(k in lower for k in EVENT_KEYWORDS)


def extract_historical_events(
    other_docs: list[tuple[Path, str]], threshold: int
) -> list[tuple[str, int, list[Path]]]:
    event_docs: dict[str, set[Path]] = defaultdict(set)
    display: dict[str, str] = {}

    for doc, text in other_docs:
        for pattern in EVENT_PATTERNS:
            for m in pattern.finditer(text):
                event_name = clean_event_name(m.group(1))
                if not looks_like_event(event_name):
                    continue
                key = event_name.lower()
                event_docs[key].add(doc)
                if key not in display:
                    display[key] = event_name

    items: list[tuple[str, int, list[Path]]] = []
    for key, docs in event_docs.items():
        count = len(docs)
        if count >= threshold:
            items.append((display[key], count, sorted(docs, key=lambda p: str(p).lower())))
    items.sort(key=lambda x: (-x[1], x[0].lower()))
    return items


def make_obsidian_link(path: Path, label: str) -> str:
    rel = path.relative_to(WIKI).as_posix()
    return f"[[{rel}|{label}]]"


def read_page_title(path: Path) -> str:
    try:
        first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        if first.startswith("# "):
            return first[2:].strip()
    except Exception:
        pass
    return path.stem.replace("-", " ").title()


def build_character_entity_lookup() -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    chars_root = WIKI / "entities" / "characters"
    if not chars_root.exists():
        return lookup

    for page in chars_root.rglob("*.md"):
        if not page.is_file():
            continue
        title = read_page_title(page)
        for key in {
            normalize_lookup_name(title),
            normalize_lookup_name(page.stem),
        }:
            if key and key not in lookup:
                lookup[key] = page
    return lookup


def build_location_entity_lookup(locations: list[Location]) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for location in locations:
        page = HUB_ROOT / f"{slugify(location.name)}.md"
        title = location.name
        for key in {
            normalize_lookup_name(title),
            normalize_lookup_name(page.stem),
        }:
            if key and key not in lookup:
                lookup[key] = page
    return lookup


def build_history_entity_lookup() -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    history_root = WIKI / "entities" / "history"
    if not history_root.exists():
        return lookup

    for page in history_root.glob("*.md"):
        if not page.is_file():
            continue
        title = read_page_title(page)
        for key in {
            normalize_lookup_name(title),
            normalize_lookup_name(page.stem),
        }:
            if key and key not in lookup:
                lookup[key] = page
    return lookup


def link_list(paths: list[Path], limit: int = 2) -> str:
    links = [make_obsidian_link(path, path.stem) for path in paths[:limit]]
    return ", ".join(links) if links else ""


def calendar_date_for_event(event_name: str) -> str | None:
    for pattern, date_label in EVENT_DATE_HINTS:
        if pattern.search(event_name):
            return date_label
    return None


def append_mentions(
    lines: list[str],
    mentions: list[tuple[Path, str]],
    visible_count: int,
) -> None:
    if not mentions:
        lines.append("_No cross-references found yet._")
        return

    visible = mentions[:visible_count]
    hidden = mentions[visible_count:]

    for doc, excerpt in visible:
        lines.append(
            f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())} - {excerpt}"
        )

    if not hidden:
        return

    lines += [
        "",
        f"<details><summary>Show {len(hidden)} more references</summary>",
        "",
    ]
    for doc, excerpt in hidden:
        lines.append(
            f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())} - {excerpt}"
        )
    lines += [
        "",
        "</details>",
    ]


def build_hub(
    location: Location,
    docs: list[Path],
    location_names: list[str],
    character_lookup: dict[str, Path],
    location_lookup: dict[str, Path],
    history_lookup: dict[str, Path],
    image_by_source: dict[str, list[str]],
    image_by_raw_doc: dict[str, list[str]],
    summary_chars: int,
    mention_chars: int,
    event_threshold: int,
    visible_mentions: int,
) -> Path:
    HUB_ROOT.mkdir(parents=True, exist_ok=True)
    hub_path = HUB_ROOT / f"{slugify(location.name)}.md"
    canonical_md = WIKI / location.extracted_rel
    other_docs = collect_location_docs(location, docs)
    mentions = build_mentions(location, other_docs, mention_chars=mention_chars)

    body = ""
    if canonical_md.exists():
        raw = canonical_md.read_text(encoding="utf-8", errors="replace")
        body = strip_markdown_metadata(raw)

    overview = build_overview(body, max_chars=summary_chars) if body else "_No summary available yet._"
    people = extract_notable_people(body, other_docs, location_names=location_names) if body else []
    places = (
        extract_notable_places(
            body,
            location_names=location_names,
            people=people,
            current_location=location.name,
        )
        if body
        else []
    )
    events = extract_historical_events(other_docs, threshold=event_threshold)

    lines = [
        f"# {location.name}",
        "",
        "## Overview",
        "",
        overview,
        "",
        "## Notable People",
        "",
    ]

    if people:
        for name, count in people:
            entity_path = character_lookup.get(normalize_lookup_name(name))
            label = make_obsidian_link(entity_path, name) if entity_path else name
            lines.append(f"- {label} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No clear character names detected yet._")

    lines += [
        "",
        "## Notable Places",
        "",
    ]

    if places:
        for place, count in places:
            entity_path = location_lookup.get(normalize_lookup_name(place))
            label = make_obsidian_link(entity_path, place) if entity_path else place
            lines.append(f"- {label} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No place references detected yet._")

    lines += [
        "",
        "## Important Historical Events",
        "",
    ]

    if events:
        for event, count, source_docs in events:
            sources = link_list(source_docs, limit=2)
            date_label = calendar_date_for_event(event)
            date_text = f"; calendar anchor: {date_label}" if date_label else ""
            event_path = history_lookup.get(normalize_lookup_name(event))
            event_label = make_obsidian_link(event_path, event) if event_path else event
            if sources:
                lines.append(
                    f"- {event_label} ({count} references in other notes{date_text}; sample sources: {sources})"
                )
            else:
                lines.append(f"- {event_label} ({count} references in other notes{date_text})")
    else:
        lines.append(
            "_No event phrases crossed the reference threshold yet (needs 3+ references in other notes)._"
        )

    image_assets = merge_asset_lists(
        collect_assets_for_sources([location.source_rel], image_by_source),
        collect_assets_for_raw_docs([location.extracted_rel], image_by_raw_doc),
    )
    append_visual_references(
        lines,
        page_path=hub_path,
        wiki_root=WIKI,
        asset_rels=image_assets,
        subject_label=location.name,
    )

    lines += [
        "",
        "## Canonical Sources",
        "",
        f"- Source file: `{location.source_rel}`",
        f"- Extracted text: {make_obsidian_link(canonical_md, 'Primary Article')}",
        "",
        "## Where This Location Appears",
        "",
    ]

    append_mentions(lines, mentions, visible_count=visible_mentions)

    lines.append("")
    hub_path.write_text("\n".join(lines), encoding="utf-8")
    return hub_path


def build_index(locations: list[Location]) -> None:
    INDEX_PAGE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Locations",
        "",
        "This is the location atlas for your setting.",
        "",
        "## Location Pages",
        "",
    ]
    for location in sorted(locations, key=lambda x: x.name.lower()):
        hub = HUB_ROOT / f"{slugify(location.name)}.md"
        lines.append(f"- {make_obsidian_link(hub, location.name)}")
    lines.append("")
    INDEX_PAGE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build location hub pages from extracted markdown."
    )
    parser.add_argument(
        "--summary-chars",
        type=int,
        default=DEFAULT_SUMMARY_CHARS,
        help=f"Maximum characters in the 2-3 sentence overview section (default: {DEFAULT_SUMMARY_CHARS}). Use 0 for no limit.",
    )
    parser.add_argument(
        "--mention-chars",
        type=int,
        default=DEFAULT_MENTION_CHARS,
        help=f"Maximum characters for each mention excerpt (default: {DEFAULT_MENTION_CHARS}).",
    )
    parser.add_argument(
        "--event-threshold",
        type=int,
        default=DEFAULT_EVENT_THRESHOLD,
        help=f"Minimum number of other-note references for an event to be listed (default: {DEFAULT_EVENT_THRESHOLD}).",
    )
    parser.add_argument(
        "--visible-mentions",
        type=int,
        default=DEFAULT_VISIBLE_MENTIONS,
        help=f"Maximum number of mention entries to show before collapsing (default: {DEFAULT_VISIBLE_MENTIONS}).",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Build hubs only for location names containing this text (case-insensitive).",
    )
    args = parser.parse_args()

    locations = parse_locations()
    selected_locations = locations
    if args.only:
        needle = args.only.lower().strip()
        selected_locations = [loc for loc in locations if needle in loc.name.lower()]

    docs = all_raw_docs()
    location_names = [loc.name for loc in locations]
    character_lookup = build_character_entity_lookup()
    location_lookup = build_location_entity_lookup(locations)
    history_lookup = build_history_entity_lookup()
    image_by_source, image_by_raw_doc = load_image_maps(WIKI)

    for location in selected_locations:
        build_hub(
            location,
            docs,
            location_names=location_names,
            character_lookup=character_lookup,
            location_lookup=location_lookup,
            history_lookup=history_lookup,
            image_by_source=image_by_source,
            image_by_raw_doc=image_by_raw_doc,
            summary_chars=args.summary_chars,
            mention_chars=args.mention_chars,
            event_threshold=args.event_threshold,
            visible_mentions=args.visible_mentions,
        )

    build_index(locations)
    print(f"Built {len(selected_locations)} location hub pages.")


if __name__ == "__main__":
    main()
