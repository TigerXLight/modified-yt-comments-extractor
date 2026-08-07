from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_comment_extraction import COMMENT_ROLE_CANDIDATES, SourceCommentArtifact, build_source_comment_extraction
from source_content_extraction import TEXT_ROLE_CANDIDATES, SourceContentArtifact, build_source_content_extraction

SCHEMA_VERSION = "source_adapter_extraction_bridge_v1"
CONTENT_INDEX_SCHEMA_VERSION = "source_adapter_content_extraction_index_v1"
COMMENT_INDEX_SCHEMA_VERSION = "source_adapter_comment_extraction_index_v1"
CAPTURE_BUNDLE_HANDOFF_SCHEMA_VERSION = "source_adapter_capture_bundle_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_extraction_bridge_operator_summary_v1"
EXTRACTION_BRIDGE_STATUS = "SHARED_EXTRACTIONS_PREPARED"
CAPTURE_BUNDLE_HANDOFF_STATUS = "READY_FOR_SHARED_CAPTURE_BUNDLE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SAFE_BASENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")

FORBIDDEN_RUNTIME_EFFECTS = [
    "fetch_url",
    "launch_browser",
    "scan_folder",
    "read_credentials",
    "submit_archive",
    "upload_release",
    "mutate_app_files",
    "mutate_registry_files",
    "start_live_action",
]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _safe_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).replace("\r", " ").strip()


def _safe_id(value: Any, *, label: str) -> str:
    text = _safe_text(value)
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
    return text


def _safe_basename(value: Any, *, label: str) -> str:
    text = _safe_text(value)
    if not text:
        raise ValueError(f"{label} is required")
    if "/" in text or "\\" in text or text in {".", ".."} or not _SAFE_BASENAME_RE.match(text):
        raise ValueError(f"{label} must be a safe basename")
    return text


def _sha256(value: Any, *, label: str) -> str:
    text = _safe_text(value).lower()
    if not _SHA256_RE.match(text):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return text


def _positive_or_zero_int(value: Any, *, label: str) -> int:
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if integer < 0:
        raise ValueError(f"{label} must be zero or greater")
    return integer


def _artifact_collections(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    collections = package.get("source_artifact_collections")
    if not isinstance(collections, list) or not collections:
        raise ValueError("artifact intake package must contain source_artifact_collections")
    return [_as_mapping(collection, "source artifact collection") for collection in collections]


def _binding_entries(artifact_file_bindings: Any) -> list[Mapping[str, Any]]:
    if isinstance(artifact_file_bindings, Mapping):
        for key in ("artifact_file_bindings", "bindings", "artifact_files", "files"):
            value = artifact_file_bindings.get(key)
            if isinstance(value, list):
                return [_as_mapping(item, "artifact file binding") for item in value]
        entries: list[Mapping[str, Any]] = []
        for name, path in artifact_file_bindings.items():
            if isinstance(path, Mapping):
                entry = dict(path)
                entry.setdefault("artifact_basename", name)
                entries.append(entry)
            else:
                entries.append({"artifact_basename": name, "path": path})
        return entries
    if isinstance(artifact_file_bindings, list):
        return [_as_mapping(item, "artifact file binding") for item in artifact_file_bindings]
    raise TypeError("artifact_file_bindings must be a list or mapping")


def _binding_keys(binding: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    basename = _safe_basename(binding.get("artifact_basename") or binding.get("filename"), label="artifact_basename")
    keys: list[tuple[Any, ...]] = [("basename", basename)]
    adapter_id = _safe_text(binding.get("adapter_id"))
    role = _safe_text(binding.get("artifact_role") or binding.get("role"))
    if adapter_id and role:
        keys.append(("adapter_role_basename", _safe_id(adapter_id, label="adapter_id"), _safe_id(role, label="artifact_role"), basename))
    return keys


def _normalise_bindings(artifact_file_bindings: Any) -> dict[tuple[Any, ...], Path]:
    normalised: dict[tuple[Any, ...], Path] = {}
    for binding in _binding_entries(artifact_file_bindings):
        path_text = _safe_text(binding.get("path") or binding.get("artifact_path"))
        if not path_text:
            raise ValueError("artifact file binding path is required")
        path = Path(path_text)
        for key in _binding_keys(binding):
            if key in normalised:
                raise ValueError(f"duplicate artifact file binding: {key}")
            normalised[key] = path
    return normalised


def _artifact_path_for(adapter_id: str, artifact: Mapping[str, Any], bindings: Mapping[tuple[Any, ...], Path]) -> Path:
    role = _safe_id(artifact.get("role"), label="artifact role")
    filename = _safe_basename(artifact.get("filename"), label="artifact filename")
    specific = ("adapter_role_basename", adapter_id, role, filename)
    basename = ("basename", filename)
    if specific in bindings:
        return bindings[specific]
    if basename in bindings:
        return bindings[basename]
    raise ValueError(f"missing explicit artifact file binding for {adapter_id}/{role}/{filename}")


def _validated_extraction_artifacts(
    collection: Mapping[str, Any], bindings: Mapping[tuple[Any, ...], Path]
) -> list[dict[str, Any]]:
    adapter_id = _safe_id(collection.get("adapter_id"), label="collection adapter_id")
    artifacts = collection.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(f"collection has no artifacts: {collection.get('collection_id', '')}")
    validated: list[dict[str, Any]] = []
    for artifact in artifacts:
        item = _as_mapping(artifact, "collection artifact")
        role = _safe_id(item.get("role"), label="artifact role")
        filename = _safe_basename(item.get("filename"), label="artifact filename")
        expected_size = _positive_or_zero_int(item.get("byte_count"), label="byte_count")
        expected_hash = _sha256(item.get("sha256"), label="sha256")
        path = _artifact_path_for(adapter_id, item, bindings)
        if not path.is_file():
            raise FileNotFoundError(f"artifact file not found: {path}")
        if path.name != filename:
            raise ValueError(f"artifact basename mismatch for {adapter_id}/{role}: expected {filename}")
        data = path.read_bytes()
        if len(data) != expected_size:
            raise ValueError(f"artifact byte_count mismatch for {adapter_id}/{role}/{filename}")
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_hash:
            raise ValueError(f"artifact sha256 mismatch for {adapter_id}/{role}/{filename}")
        validated.append(
            {
                "adapter_id": adapter_id,
                "role": role,
                "filename": filename,
                "path": path,
                "byte_count": len(data),
                "sha256": digest,
                "content_kind": _safe_text(item.get("content_kind"), ""),
            }
        )
    return validated


def _content_candidates(artifacts: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    candidates = [artifact for artifact in artifacts if str(artifact.get("role")) in TEXT_ROLE_CANDIDATES]
    if candidates:
        return candidates
    return [artifact for artifact in artifacts if any(token in str(artifact.get("role")) for token in ("article", "content", "dom", "text"))]


def _comment_candidates(artifacts: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    candidates = [artifact for artifact in artifacts if str(artifact.get("role")) in COMMENT_ROLE_CANDIDATES]
    if candidates:
        return candidates
    return [artifact for artifact in artifacts if any(token in str(artifact.get("role")) for token in ("comment", "reply", "livechat"))]


def _source_url(collection: Mapping[str, Any], fallback: str) -> str:
    url = _safe_text(collection.get("source_url"), "") or fallback
    if not url:
        raise ValueError("source_url is required for extraction bridge")
    return url


def _public_artifact_entry(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "adapter_id": artifact["adapter_id"],
        "role": artifact["role"],
        "filename": artifact["filename"],
        "byte_count": artifact["byte_count"],
        "sha256": artifact["sha256"],
        "explicit_path_supplied": True,
        "full_path_serialized": False,
    }


def build_source_adapter_extraction_bridge(
    artifact_intake_package: Mapping[str, Any],
    artifact_file_bindings: Any,
    *,
    source_url: str = "",
) -> dict[str, Any]:
    """Run shared content/comment extraction from validated adapter artifact intake outputs."""

    intake = _as_mapping(artifact_intake_package, "artifact_intake_package")
    if intake.get("artifact_intake_status") != "ARTIFACT_FILES_VALIDATED":
        raise ValueError("artifact intake package must be ARTIFACT_FILES_VALIDATED")
    handoff = intake.get("source_artifact_collection_handoff") if isinstance(intake.get("source_artifact_collection_handoff"), Mapping) else {}
    if handoff.get("handoff_status") != "READY_FOR_SHARED_EXTRACTION":
        raise ValueError("artifact intake handoff must be READY_FOR_SHARED_EXTRACTION")

    bindings = _normalise_bindings(artifact_file_bindings)
    fallback_source_url = _safe_text(source_url, "")
    content_extractions: list[dict[str, Any]] = []
    comment_extractions: list[dict[str, Any]] = []
    extraction_routes: list[dict[str, Any]] = []
    issues: list[str] = []

    for collection in _artifact_collections(intake):
        if collection.get("collection_status") != "READY_FOR_EXTRACTION":
            raise ValueError(f"collection is not READY_FOR_EXTRACTION: {collection.get('collection_id', '')}")
        adapter_id = _safe_id(collection.get("adapter_id"), label="collection adapter_id")
        url = _source_url(collection, fallback_source_url)
        artifacts = _validated_extraction_artifacts(collection, bindings)
        public_artifacts = [_public_artifact_entry(artifact) for artifact in artifacts]

        content_items = _content_candidates(artifacts)
        if content_items:
            content_extraction = build_source_content_extraction(
                adapter_id=adapter_id,
                source_url=url,
                artifacts=[
                    SourceContentArtifact(
                        role=str(artifact["role"]),
                        path=str(artifact["path"]),
                        filename=str(artifact["filename"]),
                    )
                    for artifact in content_items
                ],
            )
            content_extractions.append(content_extraction)
        else:
            content_extraction = {}
            issues.append(f"no content artifact candidate for adapter: {adapter_id}")

        comment_items = _comment_candidates(artifacts)
        if comment_items:
            comment_extraction = build_source_comment_extraction(
                adapter_id=adapter_id,
                source_url=url,
                artifacts=[
                    SourceCommentArtifact(
                        role=str(artifact["role"]),
                        path=str(artifact["path"]),
                        filename=str(artifact["filename"]),
                    )
                    for artifact in comment_items
                ],
            )
            comment_extractions.append(comment_extraction)
            comment_status = "COMMENTS_EXTRACTED"
        else:
            comment_extraction = {}
            comment_status = "NO_COMMENT_ARTIFACT_SUPPLIED"

        extraction_routes.append(
            {
                "adapter_id": adapter_id,
                "source_url": url,
                "collection_id": collection.get("collection_id", ""),
                "artifact_count": len(artifacts),
                "artifacts": public_artifacts,
                "content_status": "CONTENT_EXTRACTED" if content_extraction else "CONTENT_NOT_EXTRACTED",
                "content_id": content_extraction.get("content_id", ""),
                "comment_status": comment_status,
                "comment_extraction_id": comment_extraction.get("comment_extraction_id", ""),
            }
        )

    content_index = {
        "schema_version": CONTENT_INDEX_SCHEMA_VERSION,
        "content_extraction_count": len(content_extractions),
        "content_extractions": [
            {
                "adapter_id": item.get("adapter_id", ""),
                "source_url": item.get("source_url", ""),
                "content_id": item.get("content_id", ""),
                "title": item.get("title", ""),
                "body_sha256": item.get("body_sha256", ""),
                "body_paragraph_count": item.get("body_paragraph_count", 0),
            }
            for item in content_extractions
        ],
    }
    comment_index = {
        "schema_version": COMMENT_INDEX_SCHEMA_VERSION,
        "comment_extraction_count": len(comment_extractions),
        "comment_extractions": [
            {
                "adapter_id": item.get("adapter_id", ""),
                "source_url": item.get("source_url", ""),
                "comment_extraction_id": item.get("comment_extraction_id", ""),
                "comment_sha256": item.get("comment_sha256", ""),
                "comment_count": item.get("comment_count", 0),
            }
            for item in comment_extractions
        ],
    }
    ready = not issues and bool(content_extractions)
    capture_bundle_handoff = {
        "schema_version": CAPTURE_BUNDLE_HANDOFF_SCHEMA_VERSION,
        "handoff_status": CAPTURE_BUNDLE_HANDOFF_STATUS if ready else "EXTRACTION_BRIDGE_BLOCKED",
        "ready_for_shared_capture_bundle": ready,
        "content_extraction_count": len(content_extractions),
        "comment_extraction_count": len(comment_extractions),
        "content_extraction_ids": [item.get("content_id", "") for item in content_extractions],
        "comment_extraction_ids": [item.get("comment_extraction_id", "") for item in comment_extractions],
        "required_next_inputs": [
            "source_content_extraction_json",
            "source_comment_extraction_json when comments are available",
            "source_artifact_collection_json",
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": EXTRACTION_BRIDGE_STATUS if ready else "EXTRACTION_BRIDGE_BLOCKED",
        "collection_count": len(extraction_routes),
        "content_extraction_count": len(content_extractions),
        "comment_extraction_count": len(comment_extractions),
        "issue_count": len(issues),
        "live_network_default": False,
        "manual_or_live_actions_started_by_this_stage": False,
        "next_actions": [
            "Route the prepared content/comment extraction outputs into shared capture bundle creation.",
            "Keep extraction adapter-neutral unless a unique site surface requires an adapter module.",
            "Preserve explicit artifact provenance without serializing full local paths.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "extraction_bridge_status": EXTRACTION_BRIDGE_STATUS if ready else "EXTRACTION_BRIDGE_BLOCKED",
        "source_adapter_artifact_intake_id": _safe_text(intake.get("source_adapter_artifact_intake_id"), ""),
        "collection_count": len(extraction_routes),
        "content_extraction_count": len(content_extractions),
        "comment_extraction_count": len(comment_extractions),
        "issue_count": len(issues),
        "issues": issues,
        "extraction_routes": extraction_routes,
        "content_extractions": content_extractions,
        "comment_extractions": comment_extractions,
        "content_extraction_index": content_index,
        "comment_extraction_index": comment_index,
        "source_adapter_capture_bundle_handoff": capture_bundle_handoff,
        "operator_summary": operator_summary,
        "safety_contract": {
            "explicit_files_only": True,
            "folder_scan_performed": False,
            "network_fetch_performed": False,
            "browser_launch_performed": False,
            "credentials_read": False,
            "archive_submitted": False,
            "app_files_mutated": False,
            "registry_files_mutated": False,
            "artifact_bytes_read_for_hash_validation": True,
            "artifact_bytes_read_for_extraction": True,
            "full_local_paths_serialized": False,
            "forbidden_runtime_effects": list(FORBIDDEN_RUNTIME_EFFECTS),
        },
    }
    bridge_id = f"source_adapter_extraction_bridge.{_stable_hash(unsigned)}"
    package = dict(unsigned)
    package["source_adapter_extraction_bridge_id"] = bridge_id
    package["content_extraction_index"] = dict(content_index, source_adapter_extraction_bridge_id=bridge_id)
    package["comment_extraction_index"] = dict(comment_index, source_adapter_extraction_bridge_id=bridge_id)
    package["source_adapter_capture_bundle_handoff"] = dict(capture_bundle_handoff, source_adapter_extraction_bridge_id=bridge_id)
    package["operator_summary"] = dict(operator_summary, source_adapter_extraction_bridge_id=bridge_id)
    return package


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_extraction_bridge_package": dict(pkg),
        "source_adapter_content_extraction_index": deepcopy(pkg.get("content_extraction_index", {})),
        "source_adapter_comment_extraction_index": deepcopy(pkg.get("comment_extraction_index", {})),
        "source_adapter_capture_bundle_handoff": deepcopy(pkg.get("source_adapter_capture_bundle_handoff", {})),
        "source_adapter_extraction_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        article = tmp_path / "article.html"
        comments = tmp_path / "comments.json"
        article.write_bytes(b"<html><h1>Example title</h1><article><p>Example body.</p></article></html>")
        comments.write_bytes(b'[{"id":"c1","author":"Reader","text":"Example comment"}]')
        intake = {
            "artifact_intake_status": "ARTIFACT_FILES_VALIDATED",
            "source_adapter_artifact_intake_id": "source_adapter_artifact_intake.example",
            "source_artifact_collection_handoff": {"handoff_status": "READY_FOR_SHARED_EXTRACTION"},
            "source_artifact_collections": [
                {
                    "collection_id": "source_artifacts.example",
                    "adapter_id": "article",
                    "source_url": "https://article.example/story",
                    "collection_status": "READY_FOR_EXTRACTION",
                    "artifacts": [
                        {"role": "article_html_or_text", "filename": article.name, "byte_count": article.stat().st_size, "sha256": hashlib.sha256(article.read_bytes()).hexdigest(), "content_kind": "text"},
                        {"role": "comments_json_or_text", "filename": comments.name, "byte_count": comments.stat().st_size, "sha256": hashlib.sha256(comments.read_bytes()).hexdigest(), "content_kind": "text"},
                    ],
                }
            ],
        }
        built = build_source_adapter_extraction_bridge(
            intake,
            [
                {"adapter_id": "article", "artifact_role": "article_html_or_text", "artifact_basename": article.name, "path": str(article)},
                {"adapter_id": "article", "artifact_role": "comments_json_or_text", "artifact_basename": comments.name, "path": str(comments)},
            ],
        )
        assert built["extraction_bridge_status"] == EXTRACTION_BRIDGE_STATUS
        assert built["source_adapter_capture_bundle_handoff"]["ready_for_shared_capture_bundle"] is True
    print("Source Adapter Extraction Bridge self-test passed.")
