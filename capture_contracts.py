from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from capture_status import (
    COMPLETENESS_NOT_APPLICABLE,
    FIDELITY_STRUCTURED_EXTRACTION,
    OPERATIONAL_STATUS_MODEL_ONLY,
    is_known_completeness_status,
    is_known_fidelity_status,
)


CAPTURE_CONTRACT_SCHEMA_VERSION = "rev4.0"

ARTIFACT_TYPE_ARTICLE_TEXT = "ARTICLE_TEXT"
ARTIFACT_TYPE_PAGE_OUTLINE = "PAGE_OUTLINE"
ARTIFACT_TYPE_RAW_HTML = "RAW_HTML"
ARTIFACT_TYPE_FINAL_DOM = "FINAL_DOM"
ARTIFACT_TYPE_MHTML = "MHTML"
ARTIFACT_TYPE_DOM_SNAPSHOT = "DOM_SNAPSHOT"
ARTIFACT_TYPE_ACCESSIBILITY_TREE = "ACCESSIBILITY_TREE"
ARTIFACT_TYPE_SCREENSHOT = "SCREENSHOT"
ARTIFACT_TYPE_COMMENTS_JSONL = "COMMENTS_JSONL"
ARTIFACT_TYPE_COMMENTS_TEXT = "COMMENTS_TEXT"
ARTIFACT_TYPE_LIVECHAT_JSONL = "LIVECHAT_JSONL"
ARTIFACT_TYPE_LIVECHAT_TEXT = "LIVECHAT_TEXT"
ARTIFACT_TYPE_MEDIA_INVENTORY = "MEDIA_INVENTORY"
ARTIFACT_TYPE_MEDIA_COMPONENT = "MEDIA_COMPONENT"
ARTIFACT_TYPE_MEDIA_FILE = "MEDIA_FILE"
ARTIFACT_TYPE_RENDERED_RECORDING = "RENDERED_RECORDING"
ARTIFACT_TYPE_WARC = "WARC"
ARTIFACT_TYPE_WACZ = "WACZ"
ARTIFACT_TYPE_ARCHIVE_RESULT = "ARCHIVE_RESULT"
ARTIFACT_TYPE_ACTION_LOG = "ACTION_LOG"
ARTIFACT_TYPE_MANIFEST = "MANIFEST"
ARTIFACT_TYPE_REPORT = "REPORT"

ARTIFACT_TYPES = (
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_SCREENSHOT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_COMMENTS_TEXT,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_LIVECHAT_TEXT,
    ARTIFACT_TYPE_MEDIA_INVENTORY,
    ARTIFACT_TYPE_MEDIA_COMPONENT,
    ARTIFACT_TYPE_MEDIA_FILE,
    ARTIFACT_TYPE_RENDERED_RECORDING,
    ARTIFACT_TYPE_WARC,
    ARTIFACT_TYPE_WACZ,
    ARTIFACT_TYPE_ARCHIVE_RESULT,
    ARTIFACT_TYPE_ACTION_LOG,
    ARTIFACT_TYPE_MANIFEST,
    ARTIFACT_TYPE_REPORT,
)

CAPTURE_SCOPE_LOCALHOST_FIXTURE = "localhost_fixture"
CAPTURE_SCOPE_SITE_ADAPTER = "site_adapter"
CAPTURE_SCOPE_MANUAL_LIVE_SITE = "manual_live_site"

CAPTURE_CONTRACT_SCOPE = (
    "operational site-capture contract model only; no fetch, browser, screenshot, "
    "download, archive, provider, credential, scraping, external process, or GUI behavior"
)

ZERO_SHA256 = "0" * 64


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_capture_id(prefix: str, *parts: object) -> str:
    payload = json.dumps([str(part or "") for part in parts], separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    safe_prefix = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in prefix or "id")
    return f"{safe_prefix}_{digest}"


def _dict_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_dict_value(item) for item in value]
    if isinstance(value, list):
        return [_dict_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dict_value(value[key]) for key in sorted(value)}
    return value


@dataclass(frozen=True)
class CaptureRequest:
    request_id: str
    source_url: str
    requested_scopes: tuple[str, ...] = ()
    adapter_id: str = ""
    operational_status: str = OPERATIONAL_STATUS_MODEL_ONLY
    source_id: str = ""
    canonical_url: str = ""
    user_label: str = ""
    options: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "canonical_url": self.canonical_url,
            "operational_status": self.operational_status,
            "options": _dict_value(dict(self.options or {})),
            "request_id": self.request_id,
            "requested_scopes": list(self.requested_scopes),
            "source_id": self.source_id,
            "source_url": self.source_url,
            "user_label": self.user_label,
        }


@dataclass(frozen=True)
class CaptureArtifact:
    artifact_id: str
    session_id: str
    source_url: str
    artifact_type: str
    capture_method: str
    created_at_utc: str
    sha256: str
    relative_path: str
    completeness: str
    fidelity: str
    source_id: str = ""
    canonical_url: str = ""
    final_url: str = ""
    scope: str = ""
    adapter_id: str = ""
    adapter_version: str = ""
    access_mode: str = ""
    capture_started_at_utc: str = ""
    capture_completed_at_utc: str = ""
    size_bytes: int = 0
    parent_artifact_ids: tuple[str, ...] = ()
    transformations: tuple[Mapping[str, Any], ...] = ()
    browser: Mapping[str, Any] | None = None
    viewport: Mapping[str, Any] | None = None
    tool_versions: Mapping[str, str] | None = None
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None
    schema_version: str = CAPTURE_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_mode": self.access_mode or None,
            "adapter_id": self.adapter_id or None,
            "adapter_version": self.adapter_version or None,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "browser": _dict_value(dict(self.browser or {})) if self.browser is not None else None,
            "canonical_url": self.canonical_url or None,
            "capture_completed_at_utc": self.capture_completed_at_utc or None,
            "capture_method": self.capture_method,
            "capture_started_at_utc": self.capture_started_at_utc or None,
            "completeness": self.completeness,
            "created_at_utc": self.created_at_utc,
            "fidelity": self.fidelity,
            "final_url": self.final_url or None,
            "metadata": _dict_value(dict(self.metadata or {})),
            "parent_artifact_ids": list(self.parent_artifact_ids),
            "relative_path": self.relative_path,
            "schema_version": self.schema_version,
            "scope": self.scope or None,
            "session_id": self.session_id,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
            "source_id": self.source_id or None,
            "source_url": self.source_url,
            "tool_versions": _dict_value(dict(self.tool_versions or {})),
            "transformations": [_dict_value(dict(item)) for item in self.transformations],
            "viewport": _dict_value(dict(self.viewport or {})) if self.viewport is not None else None,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CaptureSession:
    session_id: str
    request: CaptureRequest
    created_at_utc: str
    artifacts: tuple[CaptureArtifact, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = CAPTURE_CONTRACT_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "created_at_utc": self.created_at_utc,
            "request": self.request.to_dict(),
            "scope": self.scope,
            "session_id": self.session_id,
            "warnings": list(self.warnings),
        }


def build_capture_request(
    *,
    source_url: str,
    requested_scopes: tuple[str, ...] = (),
    adapter_id: str = "",
    source_id: str = "",
    canonical_url: str = "",
    user_label: str = "",
    operational_status: str = OPERATIONAL_STATUS_MODEL_ONLY,
    options: Mapping[str, Any] | None = None,
) -> CaptureRequest:
    return CaptureRequest(
        request_id=stable_capture_id("capture_request", source_url, requested_scopes, adapter_id),
        source_url=source_url,
        requested_scopes=tuple(requested_scopes),
        adapter_id=adapter_id,
        source_id=source_id,
        canonical_url=canonical_url,
        user_label=user_label,
        operational_status=operational_status,
        options=options,
    )


def build_capture_artifact(
    *,
    session_id: str,
    source_url: str,
    artifact_type: str,
    capture_method: str,
    relative_path: str,
    sha256: str = ZERO_SHA256,
    completeness: str = COMPLETENESS_NOT_APPLICABLE,
    fidelity: str = FIDELITY_STRUCTURED_EXTRACTION,
    created_at_utc: str = "",
    **kwargs: Any,
) -> CaptureArtifact:
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unknown capture artifact type: {artifact_type}")
    if not is_known_completeness_status(completeness):
        raise ValueError(f"Unknown completeness status: {completeness}")
    if not is_known_fidelity_status(fidelity):
        raise ValueError(f"Unknown fidelity status: {fidelity}")
    if len(sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in sha256):
        raise ValueError("Artifact sha256 must be a 64-character hexadecimal digest")

    return CaptureArtifact(
        artifact_id=stable_capture_id("artifact", session_id, artifact_type, relative_path),
        session_id=session_id,
        source_url=source_url,
        artifact_type=artifact_type,
        capture_method=capture_method,
        created_at_utc=created_at_utc or utc_now_iso(),
        sha256=sha256.lower(),
        relative_path=relative_path,
        completeness=completeness,
        fidelity=fidelity,
        **kwargs,
    )


def capture_session_to_json(session: CaptureSession) -> str:
    return json.dumps(session.to_dict(), indent=2, sort_keys=True)
