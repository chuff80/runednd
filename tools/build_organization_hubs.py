#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = WIKI / "raw"
HUB_ROOT = WIKI / "entities" / "organizations"
INDEX_PAGE = WIKI / "entities" / "organizations.md"

DEFAULT_MIN_DOC_REFS = 2
DEFAULT_MENTION_CHARS = 260
DEFAULT_EVENT_THRESHOLD = 2
DEFAULT_VISIBLE_MENTIONS = 8

ORG_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,5}\s+(?:Guild|Council|College|Court|Order|Choir|Church|Temple|Parliament|Consortium|Company|Brotherhood|Sisterhood|Engineers|Talkers|Reconcilers|Collective|Society|Legion|Clan|Tribe))\b"
    ),
    re.compile(
        r"\b((?:Order|Council|Guild|College|Court|Choir|Church|Temple)\s+of\s+(?:the\s+)?[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,4})\b"
    ),
]

SPECIAL_ORG_NAMES = {
    "The Sharks",
    "Meirlich",
    "Cumhnantach",
    "Dragon Talkers",
    "Reconcilers",
    "Celestial Choir",
    "Elder's Council",
    "Sidhe Court",
}

EVENT_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,5}\s+(?:War|Battle|Apocalypse|Destruction|Reconciliation|Collapse|Uprising|Protest|Flood|Curse|Cleansing|Occupation|Exodus|Siege|Revolt|Cataclysm|Vengeance|Massacre))\b"
    ),
    re.compile(
        r"\b((?:Battle|Fall|Closure|Founding|Rise|Siege|Return)\s+of\s+(?:the\s+)?[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,4})\b"
    ),
    re.compile(
        r"\b(elemental apocalypse|great destruction|hartland war|curse of badb|fey wars|raven queen(?:'s)? vengeance|closure of the shadowfell rift|reconciliation)\b",
        flags=re.IGNORECASE,
    ),
]

PERSON_RE = re.compile(r"\b([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,2})\b")

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
    "Other",
    "Others",
    "There",
    "Here",
    "Stories",
    "Story",
    "History",
    "Character",
    "Rune",
    "Campaign",
    "Ghealdar",
    "Atania",
    "Jariana",
    "Feywild",
    "States",
    "Kingdom",
    "Court",
    "Council",
    "Guild",
    "College",
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
}

NOISE_DOC_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp)\.md$", flags=re.IGNORECASE)

ORG_ALIAS_CANONICAL: dict[str, str] = {
    "church of the creator": "Church of the Creator",
    "church of the great creator": "Church of the Creator",
    "the church": "Church of the Creator",
    "elder s council": "Elders Council",
    "elders council": "Elders Council",
    "the reconcilers": "Reconcilers",
    "the goblin engineers": "The Goblin Engineers",
    "atania the goblin engineers": "The Goblin Engineers",
    "rune rune campaign atania the goblin engineers": "The Goblin Engineers",
    "more rune campaign atania the goblin engineers": "The Goblin Engineers",
}

NOISE_ORG_KEYS = {
    "rune campaign",
    "the council",
}

NAV_MENU_TOKENS = {
    "atania",
    "ghealdar",
    "gibard",
    "free states",
    "regions",
    "races",
    "destruction of the elves",
    "goblins",
    "religions",
    "the feywild",
    "niko the frost prince",
    "calendar",
}

BELIEF_KEYWORDS = {
    "believe",
    "belief",
    "faith",
    "doctrine",
    "tenet",
    "teaches",
    "teaching",
    "worship",
    "revere",
    "sacred",
    "holy",
    "divine",
    "god",
    "gods",
    "creator",
    "spirit",
    "spirits",
}

PRACTICE_KEYWORDS = {
    "order",
    "orders",
    "priest",
    "priesthood",
    "cleric",
    "church",
    "temple",
    "ritual",
    "rituals",
    "ceremony",
    "missionary",
    "disciples",
    "convert",
    "outpost",
    "ministry",
    "services",
    "founded",
    "follower",
    "followers",
}


@dataclass
class OrganizationCandidate:
    name: str
    docs: list[Path]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_lookup_name(name: str) -> str:
    cleaned = normalize_space(name)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned.lower())
    return normalize_space(cleaned)


def is_low_signal_text(text: str) -> bool:
    lower = normalize_space(text).lower()
    if "skip to main content" in lower and len(lower) < 2400:
        return True
    if lower.count("rune campaign") >= 4:
        return True
    return False


def is_noise_sentence(sentence: str) -> bool:
    lower = normalize_space(sentence).lower()
    if not lower:
        return True
    if "skip to main content" in lower or "skip to navigation" in lower:
        return True
    if lower.count("rune campaign") >= 2:
        return True
    nav_hits = sum(1 for token in NAV_MENU_TOKENS if token in lower)
    if nav_hits >= 5:
        return True
    return False


def split_sentences(text: str) -> list[str]:
    compressed = normalize_space(text.replace("\n", " "))
    if not compressed:
        return []
    parts = re.split(r"(?<=[.!?])\s+", compressed)
    return [p.strip() for p in parts if p.strip() and not is_noise_sentence(p)]


def summarize(text: str, max_chars: int) -> str:
    cleaned = normalize_space(text)
    if max_chars <= 0 or len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


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


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "organization"


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


def build_location_entity_lookup() -> dict[str, tuple[str, Path]]:
    lookup: dict[str, tuple[str, Path]] = {}
    loc_root = WIKI / "entities" / "locations"
    if not loc_root.exists():
        return lookup

    for page in loc_root.glob("*.md"):
        if not page.is_file():
            continue
        title = read_page_title(page)
        for key in {
            normalize_lookup_name(title),
            normalize_lookup_name(page.stem),
        }:
            if key and key not in lookup:
                lookup[key] = (title, page)
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


def read_doc(path: Path) -> str:
    return strip_markdown_metadata(path.read_text(encoding="utf-8", errors="replace"))


def all_raw_docs() -> list[Path]:
    docs = [p for p in RAW.rglob("*.md") if p.is_file()]
    docs.sort(key=lambda p: str(p).lower())
    return docs


def clean_org_name(name: str) -> str:
    cleaned = normalize_space(name.strip(" ,.;:!?()[]{}\""))
    cleaned = re.sub(r"(?:'s)$", "", cleaned, flags=re.IGNORECASE)
    if "goblin engineers" in cleaned.lower() and "rune campaign" in cleaned.lower():
        return "The Goblin Engineers"
    return cleaned


def org_lookup_key(name: str) -> str:
    return normalize_lookup_name(name)


def canonical_org_name(name: str) -> str:
    key = org_lookup_key(name)
    return ORG_ALIAS_CANONICAL.get(key, name)


def looks_like_org(name: str) -> bool:
    if not name:
        return False
    if any(ch.isdigit() for ch in name):
        return False
    lowered = normalize_lookup_name(name)
    if lowered in NOISE_ORG_KEYS:
        return False
    words = name.split()
    if len(words) == 1 and len(words[0]) <= 2:
        return False
    if len(words) > 6:
        return False
    if "skip to main content" in lowered or "skip to navigation" in lowered:
        return False
    if "rune campaign" in lowered and "goblin engineers" not in lowered:
        return False
    return True


def extract_candidates(min_doc_refs: int) -> list[OrganizationCandidate]:
    docs = all_raw_docs()
    by_org: dict[str, set[Path]] = defaultdict(set)
    display: dict[str, str] = {}

    for doc in docs:
        if NOISE_DOC_RE.search(doc.name):
            continue
        text = read_doc(doc)
        if not text:
            continue
        if is_low_signal_text(text):
            continue

        for pattern in ORG_PATTERNS:
            for m in pattern.finditer(text):
                name = canonical_org_name(clean_org_name(m.group(1)))
                if not looks_like_org(name):
                    continue
                key = org_lookup_key(name)
                by_org[key].add(doc)
                if key not in display:
                    display[key] = name

        lower_text = text.lower()
        for org in SPECIAL_ORG_NAMES:
            if re.search(rf"\b{re.escape(org.lower())}\b", lower_text):
                canonical = canonical_org_name(org)
                key = org_lookup_key(canonical)
                by_org[key].add(doc)
                if key not in display:
                    display[key] = canonical

    candidates: list[OrganizationCandidate] = []
    for key, matched_docs in by_org.items():
        if len(matched_docs) < min_doc_refs:
            continue
        candidates.append(
            OrganizationCandidate(
                name=display[key],
                docs=sorted(matched_docs, key=lambda p: str(p).lower()),
            )
        )

    candidates.sort(key=lambda c: (-len(c.docs), c.name.lower()))
    return candidates


def collect_mentions(org_name: str, docs: list[Path], mention_chars: int) -> list[tuple[Path, str]]:
    pattern = re.compile(rf"\b{re.escape(org_name)}\b", re.IGNORECASE)
    mentions: list[tuple[Path, str]] = []

    for doc in docs:
        text = read_doc(doc)
        m = pattern.search(text)
        if not m:
            continue
        start = max(0, m.start() - 140)
        end = min(len(text), m.end() + 260)
        excerpt = summarize(text[start:end], max_chars=mention_chars)
        mentions.append((doc, excerpt))

    mentions.sort(key=lambda x: str(x[0]).lower())
    return mentions


def build_overview(org_name: str, docs: list[Path]) -> str:
    pattern = re.compile(rf"\b{re.escape(org_name)}\b", re.IGNORECASE)
    candidates: list[str] = []
    for doc in docs:
        text = read_doc(doc)
        for sentence in split_sentences(text):
            if pattern.search(sentence):
                candidates.append(sentence)
                if len(candidates) >= 3:
                    break
        if len(candidates) >= 3:
            break

    if not candidates:
        return "_No summary available yet._"
    return " ".join(candidates[:3])


def extract_notable_members(
    org_name: str,
    docs: list[Path],
    character_lookup: dict[str, Path],
    limit: int = 12,
) -> list[tuple[str, int, Path | None]]:
    pattern = re.compile(rf"\b{re.escape(org_name)}\b", re.IGNORECASE)
    counts: dict[str, int] = defaultdict(int)

    for doc in docs:
        text = read_doc(doc)
        for sentence in split_sentences(text):
            if not pattern.search(sentence):
                continue
            for m in PERSON_RE.finditer(sentence):
                candidate = m.group(1).strip()
                words = candidate.split()
                if candidate in PERSON_STOPWORDS:
                    continue
                if candidate.lower() == org_name.lower():
                    continue
                if len(words) == 1 and len(words[0]) < 4:
                    continue
                if any(w.lower() in PLACE_HINT_WORDS for w in words):
                    continue
                counts[candidate] += 1

    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:limit]
    out: list[tuple[str, int, Path | None]] = []
    for name, count in items:
        linked = character_lookup.get(normalize_lookup_name(name))
        out.append((name, count, linked))
    return out


def extract_associated_locations(
    docs: list[Path],
    location_lookup: dict[str, tuple[str, Path]],
    limit: int = 10,
) -> list[tuple[str, int, Path | None]]:
    counts: dict[str, int] = defaultdict(int)
    for doc in docs:
        text = read_doc(doc)
        for loc_name in location_lookup.keys():
            c = len(re.findall(rf"\b{re.escape(loc_name)}\b", text, flags=re.IGNORECASE))
            if c > 0:
                counts[loc_name] += c

    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    out: list[tuple[str, int, Path | None]] = []
    for loc_name, count in items:
        display_name, path = location_lookup[loc_name]
        out.append((display_name, count, path))
    return out


def extract_events(docs: list[Path], threshold: int) -> list[tuple[str, int, list[Path]]]:
    event_docs: dict[str, set[Path]] = defaultdict(set)
    display: dict[str, str] = {}

    for doc in docs:
        text = read_doc(doc)
        for pattern in EVENT_PATTERNS:
            for m in pattern.finditer(text):
                ev = normalize_space(m.group(1).strip(" ,.;:"))
                key = ev.lower()
                event_docs[key].add(doc)
                if key not in display:
                    display[key] = ev

    items: list[tuple[str, int, list[Path]]] = []
    for key, seen_docs in event_docs.items():
        count = len(seen_docs)
        if count >= threshold:
            items.append((display[key], count, sorted(seen_docs, key=lambda p: str(p).lower())))

    items.sort(key=lambda x: (-x[1], x[0].lower()))
    return items[:10]


def extract_thematic_sentences(
    docs: list[Path],
    keywords: set[str],
    limit: int = 4,
) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()

    for doc in docs:
        text = read_doc(doc)
        for sentence in split_sentences(text):
            lower = sentence.lower()
            if not any(k in lower for k in keywords):
                continue
            key = normalize_space(lower)
            if key in seen:
                continue
            seen.add(key)
            out.append((normalize_space(sentence), doc))
            if len(out) >= limit:
                return out

    return out


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
        lines.append(f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())} - {excerpt}")

    if not hidden:
        return

    lines += [
        "",
        f"<details><summary>Show {len(hidden)} more references</summary>",
        "",
    ]
    for doc, excerpt in hidden:
        lines.append(f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())} - {excerpt}")
    lines += [
        "",
        "</details>",
    ]


def prune_stale_generated_pages(expected_paths: set[Path]) -> int:
    if not HUB_ROOT.exists():
        return 0

    removed = 0
    for page in HUB_ROOT.glob("*.md"):
        if not page.is_file():
            continue
        if page in expected_paths:
            continue
        existing = page.read_text(encoding="utf-8", errors="replace")
        if "`Canon status:`" in existing:
            continue
        page.unlink()
        removed += 1
    return removed


def write_page(
    candidate: OrganizationCandidate,
    mention_chars: int,
    event_threshold: int,
    visible_mentions: int,
    character_lookup: dict[str, Path],
    location_lookup: dict[str, tuple[str, Path]],
    history_lookup: dict[str, Path],
    allow_curated_overwrite: bool,
) -> tuple[Path, bool]:
    HUB_ROOT.mkdir(parents=True, exist_ok=True)
    slug = slugify(candidate.name)
    out_path = HUB_ROOT / f"{slug}.md"

    if out_path.exists() and not allow_curated_overwrite:
        existing = out_path.read_text(encoding="utf-8", errors="replace")
        if "`Canon status:`" in existing:
            return out_path, False

    overview = build_overview(candidate.name, candidate.docs)
    beliefs = extract_thematic_sentences(candidate.docs, BELIEF_KEYWORDS, limit=4)
    practices = extract_thematic_sentences(candidate.docs, PRACTICE_KEYWORDS, limit=5)
    members = extract_notable_members(candidate.name, candidate.docs, character_lookup)
    locations = extract_associated_locations(candidate.docs, location_lookup)
    events = extract_events(candidate.docs, threshold=event_threshold)
    mentions = collect_mentions(candidate.name, candidate.docs, mention_chars=mention_chars)

    lines = [
        f"# {candidate.name}",
        "",
        "## Overview",
        "",
        overview,
        "",
        "## Beliefs",
        "",
    ]

    if beliefs:
        for sentence, source_doc in beliefs:
            source = make_obsidian_link(source_doc, source_doc.relative_to(WIKI).as_posix())
            lines.append(f"- {sentence} _(source: {source})_")
    else:
        lines.append("_Insufficient canonical evidence for beliefs yet._")

    lines += [
        "",
        "## Practices and Structure",
        "",
    ]

    if practices:
        for sentence, source_doc in practices:
            source = make_obsidian_link(source_doc, source_doc.relative_to(WIKI).as_posix())
            lines.append(f"- {sentence} _(source: {source})_")
    else:
        lines.append("_Insufficient canonical evidence for practices/structure yet._")

    lines += [
        "",
        "## Notable Members",
        "",
    ]

    if members:
        for member, count, link_path in members:
            label = make_obsidian_link(link_path, member) if link_path else member
            lines.append(f"- {label} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No clear member names detected yet._")

    lines += [
        "",
        "## Associated Locations",
        "",
    ]

    if locations:
        for loc, count, link_path in locations:
            label = make_obsidian_link(link_path, loc) if link_path else loc
            lines.append(f"- {label} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("_No location links detected yet._")

    lines += [
        "",
        "## Important Historical Events",
        "",
    ]

    if events:
        for event, count, source_docs in events:
            sample_links = ", ".join(
                make_obsidian_link(d, d.relative_to(WIKI).as_posix()) for d in source_docs[:2]
            )
            event_path = history_lookup.get(normalize_lookup_name(event))
            event_label = make_obsidian_link(event_path, event) if event_path else event
            lines.append(
                f"- {event_label} ({count} references; sample sources: {sample_links})"
            )
    else:
        lines.append(
            "_No event phrases crossed the reference threshold yet (needs 2+ references)._"
        )

    lines += [
        "",
        "## Canonical Sources",
        "",
    ]

    for doc in candidate.docs[:8]:
        lines.append(f"- {make_obsidian_link(doc, doc.relative_to(WIKI).as_posix())}")

    lines += [
        "",
        "## Where This Organization Appears",
        "",
    ]

    append_mentions(lines, mentions, visible_count=visible_mentions)

    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path, True


def build_index() -> None:
    INDEX_PAGE.parent.mkdir(parents=True, exist_ok=True)
    HUB_ROOT.mkdir(parents=True, exist_ok=True)

    pages = sorted([p for p in HUB_ROOT.glob("*.md") if p.is_file()], key=lambda p: p.stem.lower())
    lines = [
        "# Organizations",
        "",
        "This is the organization index for your setting.",
        "",
        "## Organization Pages",
        "",
    ]

    for page in pages:
        label = read_page_title(page)
        lines.append(f"- {make_obsidian_link(page, label)}")

    lines.append("")
    INDEX_PAGE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build organization entity pages from extracted markdown.")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Build only organizations whose names contain this text (case-insensitive).",
    )
    parser.add_argument(
        "--only-exact",
        action="store_true",
        help="When --only is set, require an exact organization name match instead of substring matching.",
    )
    parser.add_argument(
        "--min-doc-refs",
        type=int,
        default=DEFAULT_MIN_DOC_REFS,
        help=f"Minimum number of unique docs mentioning an organization (default: {DEFAULT_MIN_DOC_REFS}).",
    )
    parser.add_argument(
        "--mention-chars",
        type=int,
        default=DEFAULT_MENTION_CHARS,
        help=f"Maximum characters for mention excerpts (default: {DEFAULT_MENTION_CHARS}).",
    )
    parser.add_argument(
        "--event-threshold",
        type=int,
        default=DEFAULT_EVENT_THRESHOLD,
        help=f"Minimum number of references for an event to be listed (default: {DEFAULT_EVENT_THRESHOLD}).",
    )
    parser.add_argument(
        "--visible-mentions",
        type=int,
        default=DEFAULT_VISIBLE_MENTIONS,
        help=f"Maximum number of mention entries to show before collapsing (default: {DEFAULT_VISIBLE_MENTIONS}).",
    )
    parser.add_argument(
        "--allow-curated-overwrite",
        action="store_true",
        help="Allow overwriting organization pages that include a canon status line.",
    )
    args = parser.parse_args()

    candidates = extract_candidates(min_doc_refs=args.min_doc_refs)
    if args.only:
        needle = args.only.lower().strip()
        if args.only_exact:
            candidates = [c for c in candidates if needle == c.name.lower()]
        else:
            candidates = [c for c in candidates if needle in c.name.lower()]

    character_lookup = build_character_entity_lookup()
    location_lookup = build_location_entity_lookup()
    history_lookup = build_history_entity_lookup()

    built = 0
    skipped_curated = 0
    removed_stale = 0
    if not args.only:
        expected_paths = {HUB_ROOT / f"{slugify(candidate.name)}.md" for candidate in candidates}
        removed_stale = prune_stale_generated_pages(expected_paths)

    for candidate in candidates:
        _path, written = write_page(
            candidate,
            mention_chars=args.mention_chars,
            event_threshold=args.event_threshold,
            visible_mentions=args.visible_mentions,
            character_lookup=character_lookup,
            location_lookup=location_lookup,
            history_lookup=history_lookup,
            allow_curated_overwrite=args.allow_curated_overwrite,
        )
        if written:
            built += 1
        else:
            skipped_curated += 1

    build_index()
    print(
        f"Built {built} organization hub pages"
        + (
            f" (skipped {skipped_curated} curated pages; pruned {removed_stale} stale generated pages)."
            if skipped_curated or removed_stale
            else "."
        )
    )


if __name__ == "__main__":
    main()
