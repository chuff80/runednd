#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
REFERENCE_DIR = WIKI / "reference"
ASSET_ROOT = WIKI / "assets" / "images"
MANIFEST_PATH = REFERENCE_DIR / "image-manifest.json"

SOURCE_DIRS = [
    ROOT / "oldnotes",
    ROOT / "runesite",
    ROOT / "stories",
    ROOT / "evernote",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
HTML_EXTENSIONS = {".html", ".htm"}


def rel_to_root(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def asset_rel_for_image(image_path: Path) -> str:
    rel_source = image_path.relative_to(ROOT)
    return (Path("assets") / "images" / rel_source).as_posix()


def collect_images() -> list[Path]:
    images: list[Path] = []
    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue
        for file_path in source_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            images.append(file_path)
    images.sort(key=lambda p: str(p).lower())
    return images


def collect_html_docs() -> list[Path]:
    docs: list[Path] = []
    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue
        for file_path in source_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in HTML_EXTENSIONS:
                continue
            docs.append(file_path)
    docs.sort(key=lambda p: str(p).lower())
    return docs


def load_html_texts(html_docs: list[Path]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for doc in html_docs:
        texts[doc] = doc.read_text(encoding="utf-8", errors="replace").lower()
    return texts


def infer_sources_from_parent(image_path: Path) -> set[str]:
    linked: set[str] = set()
    parent = image_path.parent
    candidate_root = parent.parent
    if candidate_root == parent:
        return linked
    parent_name = parent.name
    for ext in HTML_EXTENSIONS:
        candidate = candidate_root / f"{parent_name}{ext}"
        if candidate.exists():
            linked.add(rel_to_root(candidate))
    return linked


def infer_sources_from_html_text(
    image_name: str,
    html_texts: dict[Path, str],
) -> set[str]:
    linked: set[str] = set()
    needle = image_name.lower()
    for html_doc, text in html_texts.items():
        if needle in text:
            linked.add(rel_to_root(html_doc))
    return linked


def linked_raw_docs(linked_sources: list[str]) -> list[str]:
    out: list[str] = []
    for source_rel in linked_sources:
        raw_rel = (Path("raw") / f"{source_rel}.md").as_posix()
        if (WIKI / raw_rel).exists():
            out.append(raw_rel)
    out.sort()
    return out


def copy_to_assets(image_path: Path) -> str:
    asset_rel = asset_rel_for_image(image_path)
    asset_abs = WIKI / asset_rel
    asset_abs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image_path, asset_abs)
    return asset_rel


def main() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    images = collect_images()
    html_docs = collect_html_docs()
    html_texts = load_html_texts(html_docs)

    image_entries: list[dict[str, object]] = []
    by_source: dict[str, set[str]] = {}
    by_raw_doc: dict[str, set[str]] = {}
    unassigned: list[str] = []

    for image_path in images:
        source_image = rel_to_root(image_path)
        asset_image = copy_to_assets(image_path)

        linked_sources_set = set()
        linked_sources_set.update(infer_sources_from_parent(image_path))
        linked_sources_set.update(infer_sources_from_html_text(image_path.name, html_texts))
        linked_sources = sorted(linked_sources_set)
        linked_raw = linked_raw_docs(linked_sources)

        for source_rel in linked_sources:
            by_source.setdefault(source_rel, set()).add(asset_image)
        for raw_rel in linked_raw:
            by_raw_doc.setdefault(raw_rel, set()).add(asset_image)

        if not linked_sources:
            unassigned.append(asset_image)

        image_entries.append(
            {
                "source_image": source_image,
                "asset_image": asset_image,
                "linked_sources": linked_sources,
                "linked_raw_docs": linked_raw,
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "image_count": len(image_entries),
        "source_doc_count": len(by_source),
        "raw_doc_count": len(by_raw_doc),
        "images": sorted(image_entries, key=lambda x: str(x["source_image"]).lower()),
        "by_source": {
            key: sorted(values)
            for key, values in sorted(by_source.items(), key=lambda kv: kv[0].lower())
        },
        "by_raw_doc": {
            key: sorted(values)
            for key, values in sorted(by_raw_doc.items(), key=lambda kv: kv[0].lower())
        },
        "unassigned_assets": sorted(unassigned),
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Built image manifest for {len(image_entries)} images "
        f"({len(unassigned)} unassigned)."
    )


if __name__ == "__main__":
    main()
