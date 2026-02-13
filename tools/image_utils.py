#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

MANIFEST_REL_PATH = Path("reference") / "image-manifest.json"


def _normalize_rel_path(path: str | Path) -> str:
    if isinstance(path, Path):
        return path.as_posix()
    return Path(path).as_posix()


def _dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def load_image_maps(wiki_root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    manifest_path = wiki_root / MANIFEST_REL_PATH
    if not manifest_path.exists():
        return {}, {}

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}

    by_source: dict[str, list[str]] = {}
    for key, assets in (data.get("by_source") or {}).items():
        normalized_key = _normalize_rel_path(key)
        normalized_assets = _dedupe_keep_order(
            _normalize_rel_path(asset) for asset in (assets or []) if asset
        )
        if normalized_assets:
            by_source[normalized_key] = normalized_assets

    by_raw_doc: dict[str, list[str]] = {}
    for key, assets in (data.get("by_raw_doc") or {}).items():
        normalized_key = _normalize_rel_path(key)
        normalized_assets = _dedupe_keep_order(
            _normalize_rel_path(asset) for asset in (assets or []) if asset
        )
        if normalized_assets:
            by_raw_doc[normalized_key] = normalized_assets

    return by_source, by_raw_doc


def collect_assets_for_sources(
    source_rels: Iterable[str | Path],
    image_by_source: dict[str, list[str]],
) -> list[str]:
    assets: list[str] = []
    for source_rel in source_rels:
        key = _normalize_rel_path(source_rel)
        assets.extend(image_by_source.get(key, []))
    return _dedupe_keep_order(assets)


def collect_assets_for_raw_docs(
    raw_doc_rels: Iterable[str | Path],
    image_by_raw_doc: dict[str, list[str]],
) -> list[str]:
    assets: list[str] = []
    for raw_rel in raw_doc_rels:
        key = _normalize_rel_path(raw_rel)
        assets.extend(image_by_raw_doc.get(key, []))
    return _dedupe_keep_order(assets)


def merge_asset_lists(*asset_lists: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for asset_list in asset_lists:
        merged.extend(asset_list)
    return _dedupe_keep_order(merged)


def append_visual_references(
    lines: list[str],
    page_path: Path,
    wiki_root: Path,
    asset_rels: Iterable[str],
    subject_label: str,
) -> None:
    assets = _dedupe_keep_order(_normalize_rel_path(p) for p in asset_rels)
    lines += [
        "",
        "## Visual References",
        "",
    ]
    if not assets:
        lines.append("_No mapped images found yet._")
        return

    for idx, asset_rel in enumerate(assets, start=1):
        target = wiki_root / asset_rel
        href = Path(os.path.relpath(target, start=page_path.parent)).as_posix()
        alt = f"{subject_label} image {idx}"
        lines.append(f"![{alt}]({href})")
