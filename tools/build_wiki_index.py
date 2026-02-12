#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "wiki"
LISTS = DOCS / "lists"
REFERENCE = DOCS / "reference"
RAW = DOCS / "raw"

SOURCE_DIRS = [
    ROOT / "oldnotes",
    ROOT / "runesite",
    ROOT / "stories",
    ROOT / "evernote",
]

SKIP_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
}

CATEGORIES = [
    "characters",
    "locations",
    "session-notes",
    "lore",
    "stories",
    "other",
]


@dataclass
class Entry:
    title: str
    rel_path: Path
    abs_path: Path
    ext: str
    source: str
    category: str
    extracted_rel: Path


def clean_title(path: Path) -> str:
    name = path.stem
    name = re.sub(r"[-_]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else path.name


def is_dated_title(text: str) -> bool:
    # Match common date-like file names: 9-17-2016, 10-16, 2024-01-01, etc.
    return bool(re.search(r"\b\d{1,4}[-.]\d{1,2}([-.]\d{1,4})?\b", text))


def classify(path: Path) -> str:
    lower = str(path).lower()
    name = path.name.lower()

    if "stories/" in lower:
        return "stories"

    if any(k in lower for k in ["character", "backstory", "party run down"]):
        return "characters"

    if any(k in lower for k in ["region", "ghealdar", "atania", "jariana", "feywild", "free-states"]):
        return "locations"

    if any(k in lower for k in ["session", "old skool", "calendar", "notes"]) or is_dated_title(name):
        return "session-notes"

    if any(k in lower for k in ["religion", "races", "goblin", "elves", "lore", "niko", "engineers"]):
        return "lore"

    return "other"


def extracted_path_for(rel_path: Path) -> Path:
    return Path("raw") / Path(f"{rel_path}.md")


def collect_entries() -> list[Entry]:
    entries: list[Entry] = []

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue

        for abs_path in source_dir.rglob("*"):
            if not abs_path.is_file():
                continue
            if abs_path.name == ".DS_Store":
                continue
            if abs_path.suffix.lower() in SKIP_EXTENSIONS:
                continue

            rel_path = abs_path.relative_to(ROOT)
            ext = abs_path.suffix.lower().lstrip(".") or "(none)"
            category = classify(rel_path)
            entries.append(
                Entry(
                    title=clean_title(abs_path),
                    rel_path=rel_path,
                    abs_path=abs_path,
                    ext=ext,
                    source=source_dir.name,
                    category=category,
                    extracted_rel=extracted_path_for(rel_path),
                )
            )

    entries.sort(key=lambda e: (e.category, e.source, str(e.rel_path).lower()))
    return entries


def write_list_page(path: Path, title: str, entries: list[Entry]) -> None:
    lines = [f"# {title}", "", f"Total items: **{len(entries)}**", ""]

    if not entries:
        lines += ["No entries found.", ""]
    else:
        lines += [
            "| Title | Type | Source | Path | Extracted |",
            "|---|---|---|---|---|",
        ]
        for e in entries:
            extracted_abs = DOCS / e.extracted_rel
            encoded_rel = quote(str(e.extracted_rel).replace("\\", "/"), safe="/")
            extracted_cell = (
                f"[md](../{encoded_rel})" if extracted_abs.exists() else "_missing_"
            )
            lines.append(
                f"| {e.title} | `{e.ext}` | `{e.source}` | `{e.rel_path}` | {extracted_cell} |"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_sources_page(entries: list[Entry]) -> None:
    by_source: dict[str, int] = {}
    by_ext: dict[str, int] = {}

    for e in entries:
        by_source[e.source] = by_source.get(e.source, 0) + 1
        by_ext[e.ext] = by_ext.get(e.ext, 0) + 1

    lines = [
        "# Sources",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Source Folders",
        "",
    ]

    for source_dir in SOURCE_DIRS:
        lines.append(f"- `{source_dir}`")

    lines += ["", "## Counts by Source", "", "| Source | Count |", "|---|---|"]
    for source, count in sorted(by_source.items()):
        lines.append(f"| `{source}` | {count} |")

    lines += ["", "## Counts by File Type", "", "| Extension | Count |", "|---|---|"]
    for ext, count in sorted(by_ext.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{ext}` | {count} |")

    lines.append("")
    (REFERENCE / "sources.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    LISTS.mkdir(parents=True, exist_ok=True)
    REFERENCE.mkdir(parents=True, exist_ok=True)

    entries = collect_entries()

    write_list_page(LISTS / "all-content.md", "All Content", entries)
    for category in CATEGORIES:
        cat_entries = [e for e in entries if e.category == category]
        title = category.replace("-", " ").title()
        write_list_page(LISTS / f"{category}.md", title, cat_entries)

    write_sources_page(entries)
    print(f"Generated wiki index with {len(entries)} items.")


if __name__ == "__main__":
    main()
