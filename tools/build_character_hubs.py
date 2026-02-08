#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = WIKI / "raw"
CHAR_LIST = WIKI / "lists" / "characters.md"
LOC_LIST = WIKI / "lists" / "locations.md"
HUB_ROOT = WIKI / "entities" / "characters"
INDEX_PAGE = WIKI / "entities" / "characters.md"

DEFAULT_MENTION_CHARS = 260
DEFAULT_EVENT_THRESHOLD = 2

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

PERSON_RE = re.compile(r"\b([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){0,2})\b")

PERSON_STOPWORDS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "And",
    "But",
    "Then",
    "When",
    "Where",
    "Who",
    "What",
    "Why",
    "How",
    "After",
    "Before",
    "With",
    "Without",
    "Some",
    "Many",
    "Most",
    "Even",
    "Apparently",
    "Eventually",
    "Other",
    "Others",
    "There",
    "Here",
    "Stories",
    "Story",
    "Tribe",
    "Food",
    "Oral",
    "All",
    "Any",
    "Every",
    "Filled",
    "Atania",
    "Ghealdar",
    "Rune",
    "Campaign",
    "History",
    "Backstory",
    "Character",
}

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
    "village",
    "tower",
    "spine",
}


@dataclass
class Character:
    name: str
    source_rels: list[Path] = field(default_factory=list)
    extracted_rels: list[Path] = field(default_factory=list)


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "character"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    compressed = normalize_space(text.replace("\n", " "))
    if not compressed:
        return []
    parts = re.split(r"(?<=[.!?])\s+", compressed)
    return [p.strip() for p in parts if p.strip()]


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


def summarize(text: str, max_chars: int = 260) -> str:
    cleaned = normalize_space(text)
    if max_chars <= 0 or len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def clean_name(text: str) -> str:
    t = text.strip()
    t = re.sub(r"\bcharacter\s+history\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bbackstory\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bhistory\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bold\s+skool\s+d&d\s+party\s+run\s+down\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bparty\s+run\s+down\b", "", t, flags=re.IGNORECASE)
    t = t.replace("Rj'S", "RJ")
    t = re.sub(r"(?:'s|’s)$", "", t, flags=re.IGNORECASE)
    t = normalize_space(t.strip(" -_.,;:"))
    if not t:
        return ""
    if len(t) <= 2 and t.isalpha():
        return t.upper()
    return t


def normalize_candidate(text: str) -> str:
    t = normalize_space(text.strip(" ,.;:!?()[]{}\""))
    t = re.sub(r"(?:'s|’s)$", "", t, flags=re.IGNORECASE)
    return t


def parse_location_names() -> list[str]:
    if not LOC_LIST.exists():
        return []
    names: list[str] = []
    for line in LOC_LIST.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        title, file_type = cells[0], cells[1]
        if file_type != "`html`":
            continue
        compact = re.sub(r"[^a-zA-Z0-9]", "", title)
        if len(compact) >= 24 and re.fullmatch(r"[A-Fa-f0-9]+", compact):
            continue
        names.append(title)
    return names


def parse_characters() -> list[Character]:
    if not CHAR_LIST.exists():
        return []

    by_name: dict[str, Character] = {}

    for line in CHAR_LIST.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        title, file_type, _source, source_path, extracted = cells[:5]

        if title.lower() == "characters" and file_type == "`html`":
            # Site index page, not a single character.
            continue

        name = clean_name(title)
        if not name:
            continue

        m = re.search(r"\]\(\.\./(.+)\)", extracted)
        if not m:
            continue

        extracted_rel = Path(unquote(m.group(1)))
        source_rel = Path(source_path.strip("`"))

        key = name.lower()
        if key not in by_name:
            by_name[key] = Character(name=name)
        by_name[key].source_rels.append(source_rel)
        by_name[key].extracted_rels.append(extracted_rel)

    chars = list(by_name.values())
    chars.sort(key=lambda c: c.name.lower())
    return chars


def read_doc(path: Path) -> str:
    return strip_markdown_metadata(path.read_text(encoding="utf-8", errors="replace"))


def canonical_text(character: Character) -> str:
    parts: list[str] = []
    for rel in character.extracted_rels:
        p = WIKI / rel
        if p.exists():
            parts.append(read_doc(p))
    return "\n\n".join([p for p in parts if p.strip()]).strip()


def collect_mentions(character: Character, docs: list[Path]) -> list[tuple[Path, str]]:
    pattern = re.compile(rf"\b{re.escape(character.name)}\b", re.IGNORECASE)
    canonical_paths = {(WIKI / rel).resolve() for rel in character.extracted_rels}
    mentions: list[tuple[Path, str]] = []

    for doc in docs:
        if doc.resolve() in canonical_paths:
            continue
        if re.search(r"\.(jpg|jpeg|png|gif|webp)\.md$", doc.name, re.IGNORECASE):
            continue
        text = read_doc(doc)
        m = pattern.search(text)
        if not m:
            continue
        start = max(0, m.start() - 140)
        end = min(len(text), m.end() + 260)
        excerpt = summarize(text[start:end], max_chars=DEFAULT_MENTION_CHARS)
        mentions.append((doc, excerpt))

    mentions.sort(key=lambda x: str(x[0]).lower())
    return mentions


def extract_connections(
    canon_text: str, self_name: str, location_names: list[str], limit: int = 14
) -> list[tuple[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    self_lower = self_name.lower()
    self_first = self_name.split()[0].lower()
    location_lowers = {x.lower() for x in location_names}
    for m in PERSON_RE.finditer(canon_text):
        candidate = normalize_candidate(m.group(1))
        if not candidate:
            continue
        words = candidate.split()
        if len(words) > 3:
            continue
        if candidate in PERSON_STOPWORDS:
            continue
        if candidate.lower() == self_lower:
            continue
        if candidate.lower() == self_first:
            continue
        if candidate.lower() in location_lowers:
            continue
        if any(w.lower() in PLACE_HINT_WORDS for w in words):
            continue
        if len(words) == 1 and len(words[0]) < 4:
            continue
        counts[candidate] += 1

    filtered: list[tuple[str, int]] = []
    for name, count in counts.items():
        words = name.split()
        if len(words) == 1 and count < 2:
            continue
        filtered.append((name, count))

    items = sorted(filtered, key=lambda x: (-x[1], x[0].lower()))
    return items[:limit]


def extract_locations(text: str, location_names: list[str], limit: int = 10) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for loc in location_names:
        c = len(re.findall(rf"\b{re.escape(loc)}\b", text, flags=re.IGNORECASE))
        if c > 0:
            out.append((loc, c))
    out.sort(key=lambda x: (-x[1], x[0].lower()))
    return out[:limit]


def extract_events(mentions: list[tuple[Path, str]], threshold: int) -> list[tuple[str, int, list[Path]]]:
    event_docs: dict[str, set[Path]] = defaultdict(set)
    display: dict[str, str] = {}

    for doc, _excerpt in mentions:
        text = read_doc(doc)
        for pattern in EVENT_PATTERNS:
            for m in pattern.finditer(text):
                ev = normalize_space(m.group(1).strip(" ,.;:"))
                key = ev.lower()
                event_docs[key].add(doc)
                if key not in display:
                    display[key] = ev

    items: list[tuple[str, int, list[Path]]] = []
    for key, docs in event_docs.items():
        count = len(docs)
        if count >= threshold:
            items.append((display[key], count, sorted(docs, key=lambda p: str(p).lower())))

    items.sort(key=lambda x: (-x[1], x[0].lower()))
    return items[:10]


def make_obsidian_link(path: Path, label: str) -> str:
    rel = path.relative_to(WIKI).as_posix()
    return f"[[{rel}|{label}]]"


def link_list(paths: list[Path], limit: int = 2) -> str:
    links = [make_obsidian_link(path, path.stem) for path in paths[:limit]]
    return ", ".join(links)


def build_character_page(
    character: Character,
    docs: list[Path],
    location_names: list[str],
    event_threshold: int,
) -> Path:
    HUB_ROOT.mkdir(parents=True, exist_ok=True)
    hub_path = HUB_ROOT / f"{slugify(character.name)}.md"

    canon = canonical_text(character)
    overview_sentences = split_sentences(canon)
    overview = " ".join(overview_sentences[:3]) if overview_sentences else "_No summary available yet._"

    mentions = collect_mentions(character, docs)
    connections = extract_connections(canon, self_name=character.name, location_names=location_names)
    assoc_locations = extract_locations(canon + "\n\n" + "\n".join(x[1] for x in mentions), location_names)
    events = extract_events(mentions, threshold=event_threshold)

    lines = [
        f"# {character.name}",
        "",
        "## Overview",
        "",
        overview,
        "",
        "## Notable Connections",
        "",
    ]

    if connections:
        for name, count in connections:
            lines.append(f"- {name} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No strong character connections detected yet._")

    lines += [
        "",
        "## Associated Locations",
        "",
    ]

    if assoc_locations:
        for loc, count in assoc_locations:
            lines.append(f"- {loc} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No location links detected yet._")

    lines += [
        "",
        "## Important Historical Events",
        "",
    ]

    if events:
        for event, count, srcs in events:
            lines.append(
                f"- {event} ({count} references in other notes; sample sources: {link_list(srcs, limit=2)})"
            )
    else:
        lines.append(
            "_No event phrases crossed the reference threshold yet (needs 2+ references in other notes)._"
        )

    lines += [
        "",
        "## Canonical Sources",
        "",
    ]

    for src, ext in zip(character.source_rels, character.extracted_rels):
        lines.append(f"- Source file: `{src}`")
        lines.append(f"- Extracted text: {make_obsidian_link(WIKI / ext, ext.name)}")

    lines += [
        "",
        "## Where This Character Appears",
        "",
    ]

    if mentions:
        for doc, excerpt in mentions:
            lines.append(f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())} - {excerpt}")
    else:
        lines.append("_No cross-references found yet._")

    lines.append("")
    hub_path.write_text("\n".join(lines), encoding="utf-8")
    return hub_path


def build_index(chars: list[Character]) -> None:
    INDEX_PAGE.parent.mkdir(parents=True, exist_ok=True)
    HUB_ROOT.mkdir(parents=True, exist_ok=True)

    def page_title(path: Path) -> str:
        try:
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if first.startswith("# "):
                return first[2:].strip()
        except Exception:
            pass
        return path.stem.replace("-", " ").title()

    # Generated pages from structured sources.
    generated: dict[str, Path] = {
        c.name: HUB_ROOT / f"{slugify(c.name)}.md" for c in chars
    }

    # Curated/manual pages that already exist in the folder but are not generated.
    for existing in HUB_ROOT.glob("*.md"):
        if not existing.is_file():
            continue
        if existing.name.startswith("."):
            continue
        if existing in generated.values():
            continue
        generated[page_title(existing)] = existing

    lines = [
        "# Characters",
        "",
        "This is the character codex for your setting.",
        "",
        "## Character Pages",
        "",
    ]
    for label, path in sorted(generated.items(), key=lambda kv: kv[0].lower()):
        lines.append(f"- {make_obsidian_link(path, label)}")
    lines.append("")
    INDEX_PAGE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build character entity pages from extracted markdown.")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Build only characters whose names contain this text (case-insensitive).",
    )
    parser.add_argument(
        "--event-threshold",
        type=int,
        default=DEFAULT_EVENT_THRESHOLD,
        help=f"Minimum number of other-note references for an event to be listed (default: {DEFAULT_EVENT_THRESHOLD}).",
    )
    args = parser.parse_args()

    chars = parse_characters()
    selected = chars
    if args.only:
        needle = args.only.lower().strip()
        selected = [c for c in chars if needle in c.name.lower()]

    docs = [p for p in RAW.rglob("*.md") if p.is_file()]
    docs.sort(key=lambda p: str(p).lower())
    location_names = parse_location_names()

    for c in selected:
        build_character_page(c, docs, location_names=location_names, event_threshold=args.event_threshold)

    build_index(chars)
    print(f"Built {len(selected)} character hub pages.")


if __name__ == "__main__":
    main()
