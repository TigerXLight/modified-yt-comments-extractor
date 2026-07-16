from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from capture_contracts import CAPTURE_CONTRACT_SCHEMA_VERSION, stable_capture_id


WARC_WACZ_SCOPE = (
    "WARC/WACZ model and fixture metadata only; no live capture, browser automation, "
    "external download, archive provider call, ArchiveBox execution, credential use, "
    "cookie storage, external command, broad folder scan, or GUI behavior"
)

WARC_RECORD_REQUEST = "request"
WARC_RECORD_RESPONSE = "response"
WARC_RECORD_RESOURCE = "resource"

WACZ_PACKAGE_KIND_FIXTURE = "synthetic_fixture_manifest"

SECRET_HEADER_NAMES = (
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-api_key",
    "api-key",
    "apikey",
    "proxy-authorization",
)

REDACTED_HEADER_VALUE = "[redacted]"


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _sha256_text(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def _hash_basis_with_fixture_name(data: Mapping[str, Any], fixture_path_key: str) -> dict[str, Any]:
    basis = dict(data)
    fixture_path = str(basis.get(fixture_path_key) or "")
    if fixture_path:
        basis[fixture_path_key] = Path(fixture_path).name
    return basis


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_secret_header(header_name: str) -> bool:
    normalized = str(header_name or "").strip().lower()
    return normalized in SECRET_HEADER_NAMES


def sanitize_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key in sorted(dict(headers or {}), key=lambda item: str(item).lower()):
        name = str(key)
        sanitized[name] = REDACTED_HEADER_VALUE if _is_secret_header(name) else str(headers[key])
    return sanitized


@dataclass(frozen=True)
class WARCSyntheticRecord:
    source_url: str
    record_kind: str
    method: str = "GET"
    status_code: int = 0
    content_type: str = ""
    timestamp_utc: str = ""
    payload_sha256: str = ""
    headers: Mapping[str, Any] | None = None
    record_id: str = ""
    schema_version: str = CAPTURE_CONTRACT_SCHEMA_VERSION
    scope: str = WARC_WACZ_SCOPE

    def to_dict(self) -> dict[str, Any]:
        sanitized_headers = sanitize_headers(self.headers)
        data_without_hash = {
            "content_type": self.content_type,
            "headers": sanitized_headers,
            "method": self.method,
            "payload_sha256": self.payload_sha256,
            "record_id": self.record_id
            or stable_capture_id(
                "warc_record",
                self.source_url,
                self.record_kind,
                self.method,
                self.status_code,
                self.timestamp_utc,
                self.payload_sha256,
            ),
            "record_kind": self.record_kind,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "source_url": self.source_url,
            "status_code": int(self.status_code),
            "timestamp_utc": self.timestamp_utc,
        }
        return {
            **data_without_hash,
            "headers_sha256": _sha256_text(sanitized_headers),
        }


@dataclass(frozen=True)
class WARCManifest:
    source_url: str
    records: tuple[WARCSyntheticRecord, ...]
    fixture_warc_path: str = ""
    warc_sha256: str = ""
    capture_execution: str = "not executed"
    schema_version: str = CAPTURE_CONTRACT_SCHEMA_VERSION
    scope: str = WARC_WACZ_SCOPE

    def to_dict(self) -> dict[str, Any]:
        records = [record.to_dict() for record in self.records]
        data_without_hash = {
            "capture_execution": self.capture_execution,
            "fixture_warc_path": self.fixture_warc_path,
            "record_count": len(records),
            "records": records,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "source_url": self.source_url,
            "warc_sha256": self.warc_sha256,
        }
        return {
            **data_without_hash,
            "manifest_sha256": _sha256_text(
                _hash_basis_with_fixture_name(data_without_hash, "fixture_warc_path")
            ),
        }


@dataclass(frozen=True)
class WACZIndexEntry:
    url: str
    timestamp_utc: str
    warc_record_id: str
    status_code: int = 0
    content_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_type": self.content_type,
            "status_code": int(self.status_code),
            "timestamp_utc": self.timestamp_utc,
            "url": self.url,
            "warc_record_id": self.warc_record_id,
        }


@dataclass(frozen=True)
class WACZPageEntry:
    page_id: str
    url: str
    title: str = ""
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "timestamp_utc": self.timestamp_utc,
            "title": self.title,
            "url": self.url,
        }


@dataclass(frozen=True)
class WACZResourceRecord:
    resource_id: str
    url: str
    media_type: str = ""
    sha256: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "resource_id": self.resource_id,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
            "url": self.url,
        }


@dataclass(frozen=True)
class WACZWARCComponentReference:
    path: str
    sha256: str = ""
    record_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "record_count": int(self.record_count),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class WACZManifest:
    package_id: str
    source_url: str
    index_entries: tuple[WACZIndexEntry, ...] = ()
    pages: tuple[WACZPageEntry, ...] = ()
    resources: tuple[WACZResourceRecord, ...] = ()
    warc_components: tuple[WACZWARCComponentReference, ...] = ()
    fixture_wacz_path: str = ""
    wacz_sha256: str = ""
    package_kind: str = WACZ_PACKAGE_KIND_FIXTURE
    package_execution: str = "not executed"
    schema_version: str = CAPTURE_CONTRACT_SCHEMA_VERSION
    scope: str = WARC_WACZ_SCOPE

    def to_dict(self) -> dict[str, Any]:
        data_without_hash = {
            "fixture_wacz_path": self.fixture_wacz_path,
            "index_entries": [entry.to_dict() for entry in self.index_entries],
            "package_execution": self.package_execution,
            "package_id": self.package_id,
            "package_kind": self.package_kind,
            "pages": [page.to_dict() for page in self.pages],
            "resources": [resource.to_dict() for resource in self.resources],
            "schema_version": self.schema_version,
            "scope": self.scope,
            "source_url": self.source_url,
            "wacz_sha256": self.wacz_sha256,
            "warc_components": [component.to_dict() for component in self.warc_components],
        }
        return {
            **data_without_hash,
            "manifest_sha256": _sha256_text(
                _hash_basis_with_fixture_name(data_without_hash, "fixture_wacz_path")
            ),
        }


def build_warc_record(
    *,
    source_url: str,
    record_kind: str,
    method: str = "GET",
    status_code: int = 0,
    content_type: str = "",
    timestamp_utc: str = "",
    payload: bytes | None = None,
    payload_sha256: str = "",
    headers: Mapping[str, Any] | None = None,
) -> WARCSyntheticRecord:
    digest = payload_sha256 or (hashlib.sha256(payload or b"").hexdigest() if payload is not None else "")
    return WARCSyntheticRecord(
        source_url=source_url,
        record_kind=record_kind,
        method=method,
        status_code=status_code,
        content_type=content_type,
        timestamp_utc=timestamp_utc,
        payload_sha256=digest,
        headers=headers,
    )


def build_warc_manifest(
    *,
    source_url: str,
    records: tuple[WARCSyntheticRecord, ...],
    fixture_warc_path: str = "",
) -> WARCManifest:
    file_hash = sha256_file(fixture_warc_path) if fixture_warc_path and Path(fixture_warc_path).is_file() else ""
    return WARCManifest(
        source_url=source_url,
        records=records,
        fixture_warc_path=fixture_warc_path,
        warc_sha256=file_hash,
    )


def build_wacz_manifest(
    *,
    package_id: str,
    source_url: str,
    index_entries: tuple[WACZIndexEntry, ...] = (),
    pages: tuple[WACZPageEntry, ...] = (),
    resources: tuple[WACZResourceRecord, ...] = (),
    warc_components: tuple[WACZWARCComponentReference, ...] = (),
    fixture_wacz_path: str = "",
) -> WACZManifest:
    file_hash = sha256_file(fixture_wacz_path) if fixture_wacz_path and Path(fixture_wacz_path).is_file() else ""
    return WACZManifest(
        package_id=package_id,
        source_url=source_url,
        index_entries=index_entries,
        pages=pages,
        resources=resources,
        warc_components=warc_components,
        fixture_wacz_path=fixture_wacz_path,
        wacz_sha256=file_hash,
    )
