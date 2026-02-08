#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "wiki" / "raw"

SOURCE_DIRS = [
    ROOT / "oldnotes",
    ROOT / "runesite",
    ROOT / "stories",
    ROOT / "evernote",
]

TEXTUTIL_EXTS = {"doc", "docx", "rtf", "odt"}
PLAIN_TEXT_EXTS = {"txt", "md"}
HTML_EXTS = {"html", "htm"}
SKIP_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "rptok", "zip"}


@dataclass
class ExtractResult:
    rel_path: Path
    output_path: Path
    status: str
    message: str


class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0
        self._block_tags = {
            "p",
            "div",
            "section",
            "article",
            "header",
            "footer",
            "main",
            "br",
            "li",
            "ul",
            "ol",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "tr",
            "td",
            "th",
        }

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        t = tag.lower()
        if t in {"script", "style", "noscript", "head", "svg"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth == 0 and t in self._block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        t = tag.lower()
        if t in {"script", "style", "noscript", "head", "svg"} and self._ignored_depth > 0:
            self._ignored_depth -= 1
            return
        if self._ignored_depth == 0 and t in self._block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def as_text(self) -> str:
        joined = " ".join(self.parts)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n[ \t]+", "\n", joined)
        # Normalize excessive blank lines.
        return re.sub(r"\n{3,}", "\n\n", joined).strip()


def output_path_for(rel_path: Path) -> Path:
    # Keep original filename and append ".md" to avoid extension collisions.
    return RAW_DIR / Path(f"{rel_path}.md")


def read_with_textutil(path: Path) -> str:
    proc = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "textutil conversion failed")
    return proc.stdout.strip()


def read_as_plain_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def read_html_text(path: Path) -> str:
    parser = SimpleHTMLTextExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = parser.as_text()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""

    # Drop boilerplate-heavy leading nav content until first substantial prose line.
    start = 0
    found_prose = False
    for i, ln in enumerate(lines):
        word_count = len(ln.split())
        if word_count >= 10 and len(ln) >= 60 and re.search(r"[.!?]", ln):
            start = i
            found_prose = True
            break
    if not found_prose:
        for i, ln in enumerate(lines):
            if len(ln) >= 60:
                start = i
                break

    cleaned = lines[start:]
    if cleaned:
        title = re.sub(r"[-_]+", " ", path.stem).strip().lower()
        first = cleaned[0]
        first_lower = first.lower()
        doubled = f"{title} {title}"
        idx = first_lower.find(doubled)
        if idx >= 0:
            cleaned[0] = first[idx + len(title) + 1 :].lstrip()
    # Remove exact duplicate neighbors from repeated nav/layout blocks.
    deduped: list[str] = []
    for ln in cleaned:
        if deduped and deduped[-1] == ln:
            continue
        deduped.append(ln)

    return "\n\n".join(deduped).strip()


def extract_text(path: Path) -> tuple[str | None, str]:
    ext = path.suffix.lower().lstrip(".")

    if ext in SKIP_EXTS:
        return None, f"Skipped unsupported binary type: .{ext}"

    if ext in TEXTUTIL_EXTS:
        try:
            return read_with_textutil(path), "Converted with textutil"
        except Exception as exc:
            return None, f"textutil failed: {exc}"

    if ext in PLAIN_TEXT_EXTS:
        return read_as_plain_text(path), "Copied plaintext content"

    if ext in HTML_EXTS:
        return read_html_text(path), "Extracted visible HTML text"

    if ext == "pdf":
        return None, "PDF extraction unavailable (install pdftotext or pypdf for full support)"

    return None, f"No extractor configured for .{ext or '(none)'}"


def write_markdown(rel_path: Path, source_abs: Path, text: str | None, note: str) -> Path:
    out_path = output_path_for(rel_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title = rel_path.stem
    header = [
        f"# {title}",
        "",
        f"- Source: `{rel_path}`",
        f"- Extracted: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- Note: {note}",
        "",
    ]

    if text:
        body = text + "\n"
    else:
        body = "_No text content extracted from this file._\n"

    out_path.write_text("\n".join(header) + body, encoding="utf-8")
    return out_path


def collect_source_files() -> list[Path]:
    files: list[Path] = []
    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.name != ".DS_Store":
                files.append(file_path)
    files.sort(key=lambda p: str(p).lower())
    return files


def run() -> list[ExtractResult]:
    results: list[ExtractResult] = []
    files = collect_source_files()

    for abs_path in files:
        rel_path = abs_path.relative_to(ROOT)
        text, note = extract_text(abs_path)
        out_path = write_markdown(rel_path, abs_path, text, note)
        status = "ok" if text else "placeholder"
        results.append(
            ExtractResult(
                rel_path=rel_path,
                output_path=out_path,
                status=status,
                message=note,
            )
        )

    return results


def write_summary(results: list[ExtractResult]) -> None:
    summary_path = ROOT / "wiki" / "reference" / "extraction-report.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    ok_count = sum(1 for r in results if r.status == "ok")
    placeholder_count = len(results) - ok_count

    lines = [
        "# Extraction Report",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"Total files: **{len(results)}**",
        f"Text extracted: **{ok_count}**",
        f"Placeholders: **{placeholder_count}**",
        "",
        "| Source File | Output Markdown | Status | Note |",
        "|---|---|---|---|",
    ]

    for result in results:
        lines.append(
            f"| `{result.rel_path}` | `{result.output_path.relative_to(ROOT)}` | `{result.status}` | {result.message} |"
        )

    lines.append("")
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    results = run()
    write_summary(results)
    ok_count = sum(1 for r in results if r.status == "ok")
    print(f"Extracted markdown for {len(results)} files ({ok_count} with text).")


if __name__ == "__main__":
    main()
