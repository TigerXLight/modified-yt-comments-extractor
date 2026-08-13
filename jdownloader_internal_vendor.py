from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jdownloader_internal_paths import (
    JD_MANIFESTS_DIR,
    JD_REQUIRED_CONTROL_SOURCE_PATHS,
    JD_REQUIRED_YOUTUBE_SOURCE_PATHS,
    JD_RUNTIME_DIR,
    JD_RUNTIME_SOURCE_FILES,
    JD_SOURCE_ARCHIVE_SOURCES,
    JD_SOURCE_ARCHIVES_DIR,
    JD_SOURCE_TREE_DIR,
    JD_VENDOR_ROOT,
    LOCAL_BUNDLE_INPUT_PREFIX,
    LOCAL_BUNDLE_ZIP,
    LOCAL_JD_INSTALLED_ROOT,
    LOCAL_JD_MIRROR_ROOT,
)


@dataclass(frozen=True)
class VendorFileRecord:
    name: str
    source_path: str
    target_path: str
    copied: bool
    exists: bool
    size: int = 0
    sha256: str = ""
    provenance: str = ""
    warning: str = ""


@dataclass(frozen=True)
class JDownloaderVendorReport:
    vendor_root: str
    mode: str
    source_archives: tuple[VendorFileRecord, ...] = ()
    runtime_files: tuple[VendorFileRecord, ...] = ()
    extracted_archives: tuple[str, ...] = ()
    required_youtube_source_paths: tuple[str, ...] = JD_REQUIRED_YOUTUBE_SOURCE_PATHS
    required_control_source_paths: tuple[str, ...] = JD_REQUIRED_CONTROL_SOURCE_PATHS
    local_mirror_root: str = str(LOCAL_JD_MIRROR_ROOT)
    installed_runtime_root: str = str(LOCAL_JD_INSTALLED_ROOT)
    bundle_zip: str = str(LOCAL_BUNDLE_ZIP)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(source: Path, target: Path, *, provenance: str) -> VendorFileRecord:
    if not source.is_file():
        return VendorFileRecord(
            name=target.name,
            source_path=str(source),
            target_path=str(target),
            copied=False,
            exists=False,
            provenance=provenance,
            warning="source file missing",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or sha256_file(source) != sha256_file(target):
        shutil.copy2(source, target)
        copied = True
    else:
        copied = False
    return VendorFileRecord(
        name=target.name,
        source_path=str(source),
        target_path=str(target),
        copied=copied,
        exists=True,
        size=target.stat().st_size,
        sha256=sha256_file(target),
        provenance=provenance,
    )


def _extract_bundle_input(name: str, target: Path) -> VendorFileRecord | None:
    if not LOCAL_BUNDLE_ZIP.is_file():
        return None
    zip_name = LOCAL_BUNDLE_INPUT_PREFIX + name
    try:
        with zipfile.ZipFile(LOCAL_BUNDLE_ZIP) as archive:
            if zip_name not in archive.namelist():
                return None
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = archive.read(zip_name)
            existing = target.read_bytes() if target.is_file() else None
            copied = existing != payload
            if copied:
                target.write_bytes(payload)
    except (OSError, zipfile.BadZipFile):
        return None
    return VendorFileRecord(
        name=target.name,
        source_path=f"{LOCAL_BUNDLE_ZIP}!/{zip_name}",
        target_path=str(target),
        copied=copied,
        exists=True,
        size=target.stat().st_size,
        sha256=sha256_file(target),
        provenance="uploaded Codex V27 bundle input",
    )


def _copy_source_archives() -> tuple[VendorFileRecord, ...]:
    records: list[VendorFileRecord] = []
    for name, source in JD_SOURCE_ARCHIVE_SOURCES.items():
        target = JD_SOURCE_ARCHIVES_DIR / name
        record = _copy_file(source, target, provenance="local JDownloader mirror/source path")
        if not record.exists:
            bundled = _extract_bundle_input(name, target)
            if bundled is not None:
                record = bundled
        records.append(record)
    return tuple(records)


def _copy_runtime_files() -> tuple[VendorFileRecord, ...]:
    records: list[VendorFileRecord] = []
    for relative, source in JD_RUNTIME_SOURCE_FILES.items():
        records.append(_copy_file(source, JD_RUNTIME_DIR / relative, provenance="local installed JDownloader runtime"))
    return tuple(records)


def _extract_sources(records: Sequence[VendorFileRecord]) -> tuple[str, ...]:
    extracted: list[str] = []
    for record in records:
        path = Path(record.target_path)
        if not record.exists or path.suffix.lower() != ".zip":
            continue
        target = JD_SOURCE_TREE_DIR / path.stem
        target.mkdir(parents=True, exist_ok=True)
        marker = target / ".ytce_extracted_from"
        try:
            with zipfile.ZipFile(path) as archive:
                archive.extractall(target)
            marker.write_text(str(path), encoding="utf-8")
            extracted.append(str(target))
        except (OSError, zipfile.BadZipFile) as exc:
            extracted.append(f"{target} ERROR {type(exc).__name__}: {exc}")
    return tuple(extracted)


def write_vendor_manifests(report: JDownloaderVendorReport) -> None:
    JD_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    (JD_MANIFESTS_DIR / "jdownloader_vendor_manifest.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (JD_MANIFESTS_DIR / "jdownloader_required_files.json").write_text(
        json.dumps(
            {
                "required_source_archives": list(JD_SOURCE_ARCHIVE_SOURCES.keys()),
                "required_runtime_files": list(JD_RUNTIME_SOURCE_FILES.keys()),
                "youtube_plugin_source_paths": list(JD_REQUIRED_YOUTUBE_SOURCE_PATHS),
                "control_account_captcha_linkgrabber_paths": list(JD_REQUIRED_CONTROL_SOURCE_PATHS),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime = {
        "runtime_dir": str(JD_RUNTIME_DIR),
        "installed_runtime_bootstrap_source": str(LOCAL_JD_INSTALLED_ROOT),
        "runtime_files": [record.__dict__ for record in report.runtime_files],
        "external_installed_jdownloader_is_bootstrap_source_only": True,
    }
    (JD_MANIFESTS_DIR / "jdownloader_runtime_manifest.json").write_text(
        json.dumps(runtime, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def bootstrap_jdownloader_vendor(
    *,
    source_only: bool = False,
    source_and_runtime: bool = False,
    extract_source: bool = False,
) -> JDownloaderVendorReport:
    JD_VENDOR_ROOT.mkdir(parents=True, exist_ok=True)
    JD_SOURCE_ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    JD_SOURCE_TREE_DIR.mkdir(parents=True, exist_ok=True)
    JD_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    source_records = _copy_source_archives()
    runtime_records: tuple[VendorFileRecord, ...] = ()
    if source_and_runtime and not source_only:
        runtime_records = _copy_runtime_files()
    extracted = _extract_sources(source_records) if extract_source else ()
    warnings = tuple(record.warning for record in (*source_records, *runtime_records) if record.warning)
    mode = "source-and-runtime" if source_and_runtime and not source_only else "source-only"
    if extract_source:
        mode += "+extract-source"
    report = JDownloaderVendorReport(
        vendor_root=str(JD_VENDOR_ROOT),
        mode=mode,
        source_archives=source_records,
        runtime_files=runtime_records,
        extracted_archives=extracted,
        warnings=warnings,
    )
    write_vendor_manifests(report)
    return report


def verify_jdownloader_vendor() -> JDownloaderVendorReport:
    source_records = tuple(
        VendorFileRecord(
            name=name,
            source_path=str(source),
            target_path=str(JD_SOURCE_ARCHIVES_DIR / name),
            copied=False,
            exists=(JD_SOURCE_ARCHIVES_DIR / name).is_file(),
            size=(JD_SOURCE_ARCHIVES_DIR / name).stat().st_size if (JD_SOURCE_ARCHIVES_DIR / name).is_file() else 0,
            sha256=sha256_file(JD_SOURCE_ARCHIVES_DIR / name) if (JD_SOURCE_ARCHIVES_DIR / name).is_file() else "",
            provenance="project-internal vendored source archive",
            warning="" if (JD_SOURCE_ARCHIVES_DIR / name).is_file() else "vendored source missing",
        )
        for name, source in JD_SOURCE_ARCHIVE_SOURCES.items()
    )
    runtime_records = tuple(
        VendorFileRecord(
            name=relative,
            source_path=str(source),
            target_path=str(JD_RUNTIME_DIR / relative),
            copied=False,
            exists=(JD_RUNTIME_DIR / relative).is_file(),
            size=(JD_RUNTIME_DIR / relative).stat().st_size if (JD_RUNTIME_DIR / relative).is_file() else 0,
            sha256=sha256_file(JD_RUNTIME_DIR / relative) if (JD_RUNTIME_DIR / relative).is_file() else "",
            provenance="project-internal vendored runtime",
            warning="" if (JD_RUNTIME_DIR / relative).is_file() else "vendored runtime file missing",
        )
        for relative, source in JD_RUNTIME_SOURCE_FILES.items()
    )
    report = JDownloaderVendorReport(
        vendor_root=str(JD_VENDOR_ROOT),
        mode="verify",
        source_archives=source_records,
        runtime_files=runtime_records,
        warnings=tuple(record.warning for record in (*source_records, *runtime_records) if record.warning),
    )
    write_vendor_manifests(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap or verify project-internal JDownloader vendor inputs.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--source-only", action="store_true")
    mode.add_argument("--source-and-runtime", action="store_true")
    parser.add_argument("--extract-source", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    if args.verify_only:
        report = verify_jdownloader_vendor()
    else:
        report = bootstrap_jdownloader_vendor(
            source_only=args.source_only or not args.source_and_runtime,
            source_and_runtime=args.source_and_runtime,
            extract_source=args.extract_source,
        )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
