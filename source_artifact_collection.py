from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

SCHEMA_VERSION = "source_artifact_collection_v1"
DEFAULT_REQUIRED_ROLES = (
    "article_html_or_text",
    "metadata_json",
)
KNOWN_ARTIFACT_ROLES = {
    "article_html_or_text",
    "comments_json_or_text",
    "dom_snapshot",
    "screenshot",
    "metadata_json",
    "archive_receipt_json",
    "transcript_text",
    "media_metadata_json",
}
_TEXT_SUFFIXES = {".txt", ".md", ".html", ".htm", ".json", ".ndjson", ".csv", ".xml"}
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class SourceArtifactInput:
    role: str
    path: Path
    description: str = ""


def _safe_text(value: Any) -> str:
    return str(value or "").replace("\r", " ").strip()


def _safe_identifier(value: str, *, fallback: str) -> str:
    cleaned = _SAFE_ID_RE.sub("_", _safe_text(value)).strip("._-")
    return cleaned[:120] or fallback


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_id(parts: Iterable[Any], prefix: str) -> str:
    payload = json.dumps([_safe_text(part) for part in parts], sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"{prefix}.{hashlib.sha256(payload).hexdigest()[:12]}"


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON file is invalid: {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path.name}")
    return data


def parse_artifact_spec(spec: str) -> SourceArtifactInput:
    if "=" not in spec:
        raise ValueError("artifact spec must be role=path")
    role, raw_path = spec.split("=", 1)
    role = _safe_identifier(role, fallback="artifact")
    if not role:
        raise ValueError("artifact role is required")
    return SourceArtifactInput(role=role, path=Path(raw_path))


def _extract_job_context(capture_job: Mapping[str, Any] | None) -> dict[str, Any]:
    if not capture_job:
        return {}
    return {
        "capture_job_id": _safe_text(capture_job.get("capture_job_id") or capture_job.get("job_id")),
        "adapter_id": _safe_text(capture_job.get("adapter_id")),
        "source_url": _safe_text(capture_job.get("source_url") or capture_job.get("url")),
        "approval_required": bool(capture_job.get("approval_required", True)),
        "live_network_default": bool(capture_job.get("live_network_default", False)),
    }


def build_source_artifact_collection(
    *,
    adapter_id: str,
    source_url: str,
    artifacts: Sequence[SourceArtifactInput],
    capture_job: Mapping[str, Any] | None = None,
    required_roles: Sequence[str] = DEFAULT_REQUIRED_ROLES,
    operator_notes: str = "",
) -> dict[str, Any]:
    safe_adapter_id = _safe_identifier(adapter_id, fallback="adapter")
    clean_source_url = _safe_text(source_url)
    if not clean_source_url:
        raise ValueError("source_url is required")
    parsed = urlparse(clean_source_url)
    if parsed.scheme not in {"http", "https", "file"}:
        raise ValueError("source_url must use http, https, or file")
    if not artifacts:
        raise ValueError("at least one explicit artifact file is required")

    artifact_entries: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    seen_filenames: set[str] = set()
    for item in artifacts:
        role = _safe_identifier(item.role, fallback="artifact")
        if role not in KNOWN_ARTIFACT_ROLES:
            raise ValueError(f"unknown artifact role: {role}")
        path = Path(item.path)
        if not path.is_file():
            raise FileNotFoundError(f"artifact file not found: {path}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"artifact file is empty: {path.name}")
        filename = path.name
        safe_filename = _safe_identifier(filename, fallback=f"{role}.artifact")
        if safe_filename in seen_filenames:
            digest_short = _sha256_bytes(str(path).encode("utf-8"))[:8]
            safe_filename = f"{digest_short}.{safe_filename}"
        seen_roles.add(role)
        seen_filenames.add(safe_filename)
        suffix = path.suffix.lower()
        artifact_entries.append(
            {
                "role": role,
                "filename": safe_filename,
                "source_path_recorded": False,
                "byte_count": len(data),
                "sha256": _sha256_bytes(data),
                "content_kind": "text" if suffix in _TEXT_SUFFIXES else "binary",
                "suffix": suffix,
                "description": _safe_text(item.description),
            }
        )

    missing_roles = [role for role in required_roles if role not in seen_roles]
    collection_id = _stable_id(
        [safe_adapter_id, clean_source_url, [(entry["role"], entry["filename"], entry["sha256"]) for entry in artifact_entries]],
        "source_artifacts",
    )
    job_context = _extract_job_context(capture_job)
    return {
        "schema_version": SCHEMA_VERSION,
        "collection_id": collection_id,
        "adapter_id": safe_adapter_id,
        "source_url": clean_source_url,
        "source_domain": parsed.netloc or "local_file",
        "capture_job": job_context,
        "artifact_count": len(artifact_entries),
        "artifacts": artifact_entries,
        "required_roles": list(required_roles),
        "missing_required_roles": missing_roles,
        "collection_status": "READY_FOR_EXTRACTION" if not missing_roles else "NEEDS_REQUIRED_ARTIFACTS",
        "operator_notes": _safe_text(operator_notes),
        "safety": {
            "explicit_files_only": True,
            "folder_scan_performed": False,
            "network_fetch_performed": False,
            "browser_launch_performed": False,
            "full_local_paths_serialized": False,
            "credentials_read": False,
        },
    }


def build_source_artifact_collection_from_files(
    *,
    adapter_id: str,
    source_url: str,
    artifact_specs: Sequence[str],
    capture_job_path: Path | None = None,
    operator_notes: str = "",
) -> dict[str, Any]:
    capture_job = _load_json_file(capture_job_path) if capture_job_path else None
    artifacts = [parse_artifact_spec(spec) for spec in artifact_specs]
    return build_source_artifact_collection(
        adapter_id=adapter_id,
        source_url=source_url,
        artifacts=artifacts,
        capture_job=capture_job,
        operator_notes=operator_notes,
    )


__all__ = [
    "DEFAULT_REQUIRED_ROLES",
    "KNOWN_ARTIFACT_ROLES",
    "SCHEMA_VERSION",
    "SourceArtifactInput",
    "build_source_artifact_collection",
    "build_source_artifact_collection_from_files",
    "parse_artifact_spec",
]
