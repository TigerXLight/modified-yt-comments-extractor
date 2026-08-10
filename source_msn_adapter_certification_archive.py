from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_PATTERNS = (
    "MSN_SOURCE_ADAPTER_*.json",
    "MSN_SOURCE_ADAPTER_*.md",
    "MSN_SOURCE_ADAPTER_*.csv",
    "MSN_ADAPTER_*.json",
    "MSN_ADAPTER_*.md",
    "MSN_ADAPTER_*.csv",
    "MSN_*EVIDENCE*.json",
    "MSN_*EVIDENCE*.md",
    "media_inventory*.json",
    "media_download*.json",
    "media_download*.md",
    "source_*manifest*.json",
    "*provenance*.json",
)


@dataclass(frozen=True)
class ArchivedEvidenceFile:
    source_path: str
    archive_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class CertificationArchiveIndex:
    generated_at_utc: str
    root: str
    output_dir: str
    files: list[ArchivedEvidenceFile]
    zip_path: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_evidence_files(root: Path, patterns: Iterable[str] = DEFAULT_PATTERNS) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(p for p in root.rglob(pattern) if p.is_file())
    return sorted(set(found), key=lambda p: str(p).lower())


def build_certification_archive(root: Path, out_dir: Path, make_zip: bool = False) -> CertificationArchiveIndex:
    root = root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = out_dir / "evidence_files"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    archived: list[ArchivedEvidenceFile] = []
    for src in find_evidence_files(root):
        try:
            rel = src.relative_to(root)
        except ValueError:
            rel = Path(src.name)
        dest = evidence_dir / rel
        if src.resolve() == dest.resolve():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        archived.append(ArchivedEvidenceFile(
            source_path=str(src),
            archive_path=str(dest.relative_to(out_dir)),
            size_bytes=dest.stat().st_size,
            sha256=_sha256(dest),
        ))

    zip_path: str | None = None
    if make_zip:
        zip_file = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE.zip"
        with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in archived:
                zf.write(out_dir / item.archive_path, item.archive_path)
        zip_path = str(zip_file)

    index = CertificationArchiveIndex(
        generated_at_utc=_now(),
        root=str(root),
        output_dir=str(out_dir),
        files=archived,
        zip_path=zip_path,
    )
    write_archive_index(index, out_dir)
    return index


def write_archive_index(index: CertificationArchiveIndex, out_dir: Path) -> dict[str, Path]:
    json_path = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE_INDEX.json"
    md_path = out_dir / "MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE_INDEX.md"
    json_path.write_text(json.dumps(asdict(index), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# MSN Source Adapter Certification Archive Index",
        "",
        f"Generated: `{index.generated_at_utc}`",
        f"Root: `{index.root}`",
        f"Files: `{len(index.files)}`",
        "",
        "| Archive path | Size | SHA256 |",
        "|---|---:|---|",
    ]
    for item in index.files:
        lines.append(f"| `{item.archive_path}` | {item.size_bytes} | `{item.sha256}` |")
    if index.zip_path:
        lines.extend(["", f"ZIP: `{index.zip_path}`"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build hash-indexed MSN certification archive.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    args = parser.parse_args(argv)
    index = build_certification_archive(args.root, args.out, make_zip=args.make_zip)
    print(f"MSN certification archive files: {len(index.files)}")
    print(f"Index: {args.out / 'MSN_SOURCE_ADAPTER_CERTIFICATION_ARCHIVE_INDEX.json'}")
    if index.zip_path:
        print(f"ZIP: {index.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
