"""Hash and index MSN adapter evidence/report outputs for handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


IMPORTANT_SUFFIXES = {".json", ".md", ".csv", ".html", ".warc", ".gz", ".wacz", ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m3u8", ".mpd"}
IMPORTANT_NAME_TOKENS = ["msn", "article", "comment", "profile", "media", "warc", "wacz", "acceptance", "validation", "reconciliation", "closeout", "viewer"]


@dataclass
class EvidencePackEntry:
    path: str
    size_bytes: int
    sha256: str
    category: str


@dataclass
class EvidencePackIndex:
    generated_at_utc: str
    root: str
    total_files_indexed: int
    entries: list[EvidencePackEntry]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _category(path: Path) -> str:
    lower = path.as_posix().lower()
    for token in ["acceptance", "validation", "reconciliation", "closeout"]:
        if token in lower:
            return "report"
    if "comment" in lower:
        return "comments"
    if "profile" in lower:
        return "profiles"
    if "media" in lower or path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".m3u8", ".mpd"}:
        return "media"
    if "warc" in lower or "wacz" in lower:
        return "archive"
    if "viewer" in lower or path.name.lower() == "rendered-page.html":
        return "offline_viewer"
    if "article" in lower:
        return "article"
    return "other"


def _include(path: Path) -> bool:
    lower = path.as_posix().lower()
    return path.suffix.lower() in IMPORTANT_SUFFIXES and any(token in lower for token in IMPORTANT_NAME_TOKENS)


def build_evidence_pack_index(root: Path, max_files: int = 2000) -> EvidencePackIndex:
    root = root.resolve()
    entries: list[EvidencePackEntry] = []
    if root.exists():
        for path in sorted(p for p in root.rglob("*") if p.is_file() and _include(p)):
            try:
                rel = path.relative_to(root).as_posix()
                entries.append(EvidencePackEntry(rel, path.stat().st_size, _sha256(path), _category(path)))
            except OSError:
                continue
            if len(entries) >= max_files:
                break
    return EvidencePackIndex(_now(), str(root), len(entries), entries)


def write_evidence_pack_index(index: EvidencePackIndex, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.md"
    json_path.write_text(json.dumps(asdict(index), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# MSN Source Adapter Evidence Pack Index",
        "",
        f"- Generated: `{index.generated_at_utc}`",
        f"- Root: `{index.root}`",
        f"- Files indexed: `{index.total_files_indexed}`",
        "",
        "| Category | Path | Bytes | SHA-256 |",
        "|---|---|---:|---|",
    ]
    for entry in index.entries:
        lines.append(f"| `{entry.category}` | `{entry.path}` | {entry.size_bytes} | `{entry.sha256}` |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index and hash MSN source adapter evidence outputs.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    root = Path(args.root)
    output = Path(args.output) if args.output else root / "reports"
    index = build_evidence_pack_index(root)
    json_path, md_path = write_evidence_pack_index(index, output)
    print(f"MSN evidence pack indexed files: {index.total_files_indexed}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
