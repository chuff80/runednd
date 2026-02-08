from __future__ import annotations

from pathlib import Path
import posixpath
import re
from urllib.parse import quote

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+(?:#[^\]|]+)?)(?:\|([^\]]+))?\]\]")


def _split_target(target: str) -> tuple[str, str]:
    if "#" in target:
        path_part, anchor = target.split("#", 1)
        return path_part.strip(), anchor.strip()
    return target.strip(), ""


def _default_label(path_part: str) -> str:
    stem = Path(path_part).stem
    return stem.replace("-", " ").replace("_", " ").strip() or path_part


def _as_relative_href(src_uri: str, target_path: str, anchor: str) -> str:
    src_dir = posixpath.dirname(src_uri) or "."
    rel = posixpath.relpath(target_path, start=src_dir)
    encoded = quote(rel, safe="/")
    if anchor:
        return f"{encoded}#{quote(anchor, safe='')}"
    return encoded


def _replace_wikilink(match: re.Match[str], src_uri: str) -> str:
    raw_target = match.group(1).strip()
    label = (match.group(2) or "").strip()

    if "..." in raw_target or "<" in raw_target or ">" in raw_target:
        return match.group(0)

    path_part, anchor = _split_target(raw_target)
    if not path_part:
        return match.group(0)

    target_path = Path(path_part)
    if target_path.suffix == "":
        target_path = target_path.with_suffix(".md")

    target_posix = target_path.as_posix()
    href = _as_relative_href(src_uri, target_posix, anchor)
    link_text = label or _default_label(path_part)
    return f"[{link_text}]({href})"


def on_page_markdown(markdown: str, page, config, files):  # noqa: ANN001
    src_uri = page.file.src_uri
    return WIKILINK_RE.sub(lambda m: _replace_wikilink(m, src_uri), markdown)
