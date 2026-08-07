from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_artifact_collection import SourceArtifactInput, build_source_artifact_collection

SCHEMA_VERSION = "source_adapter_artifact_intake_v1"
VALIDATION_REPORT_SCHEMA_VERSION = "source_adapter_artifact_intake_validation_report_v1"
COLLECTION_INDEX_SCHEMA_VERSION = "source_adapter_artifact_collection_index_v1"
COLLECTION_HANDOFF_SCHEMA_VERSION = "source_adapter_artifact_collection_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_artifact_intake_operator_summary_v1"
ARTIFACT_INTAKE_STATUS = "ARTIFACT_FILES_VALIDATED"
COLLECTION_HANDOFF_STATUS = "READY_FOR_SHARED_EXTRACTION"

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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_id(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
    return text


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value if value is not None else default).replace("\r", " ").strip()
    return text


def _safe_basename(value: Any, *, label: str) -> str:
    text = _safe_text(value)
    if not text:
        raise ValueError(f"{label} is required")
    if "/" in text or "\\" in text:
        raise ValueError(f"{label} must be a safe basename, not a path")
    if text in {".", ".."} or not _SAFE_BASENAME_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
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


def _read_bytes(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"artifact file not found: {path}")
    data = path.read_bytes()
    if not data:
        raise ValueError(f"artifact file is empty: {path.name}")
    return data


def _extract_receipts(capture_session_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    direct = capture_session_package.get("artifact_receipts")
    if isinstance(direct, list) and direct:
        return [_as_mapping(receipt, "artifact receipt") for receipt in direct]
    index = capture_session_package.get("artifact_receipt_index")
    if isinstance(index, Mapping):
        indexed = index.get("receipts")
        if isinstance(indexed, list) and indexed:
            return [_as_mapping(receipt, "artifact receipt") for receipt in indexed]
    raise ValueError("capture session package must contain artifact receipts")


def _normalise_receipt(raw: Mapping[str, Any]) -> dict[str, Any]:
    adapter_id = _safe_id(raw.get("adapter_id"), label="receipt adapter_id")
    role = _safe_id(raw.get("artifact_role") or raw.get("role"), label="receipt artifact_role")
    basename = _safe_basename(raw.get("artifact_basename") or raw.get("filename"), label="artifact_basename")
    byte_count = _positive_or_zero_int(raw.get("byte_count"), label="byte_count")
    digest = _sha256(raw.get("sha256"), label="sha256")
    receipt_id = _safe_id(raw.get("receipt_id") or f"{adapter_id}.{role}.{basename}", label="receipt_id")
    return {
        "receipt_id": receipt_id,
        "adapter_id": adapter_id,
        "artifact_role": role,
        "artifact_basename": basename,
        "byte_count": byte_count,
        "sha256": digest,
        "source_url": _safe_text(raw.get("source_url"), ""),
    }


def _normalise_receipts(capture_session_package: Mapping[str, Any]) -> list[dict[str, Any]]:
    receipts = [_normalise_receipt(receipt) for receipt in _extract_receipts(capture_session_package)]
    seen_receipt_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for receipt in receipts:
        if receipt["receipt_id"] in seen_receipt_ids:
            raise ValueError(f"duplicate receipt_id: {receipt['receipt_id']}")
        pair = (receipt["adapter_id"], receipt["artifact_role"])
        if pair in seen_pairs:
            raise ValueError(f"duplicate adapter/role receipt: {pair[0]}/{pair[1]}")
        seen_receipt_ids.add(receipt["receipt_id"])
        seen_pairs.add(pair)
    return receipts


def _binding_entries(artifact_file_bindings: Any) -> list[Mapping[str, Any]]:
    if isinstance(artifact_file_bindings, Mapping):
        for key in ("artifact_file_bindings", "bindings", "artifact_files", "files"):
            value = artifact_file_bindings.get(key)
            if isinstance(value, list):
                return [_as_mapping(item, "artifact file binding") for item in value]
        if all(isinstance(key, str) for key in artifact_file_bindings.keys()):
            entries: list[Mapping[str, Any]] = []
            for receipt_id, path in artifact_file_bindings.items():
                if isinstance(path, Mapping):
                    entry = dict(path)
                    entry.setdefault("receipt_id", receipt_id)
                    entries.append(entry)
                else:
                    entries.append({"receipt_id": receipt_id, "path": path})
            return entries
    if isinstance(artifact_file_bindings, list):
        return [_as_mapping(item, "artifact file binding") for item in artifact_file_bindings]
    raise TypeError("artifact_file_bindings must be a list or a mapping containing bindings")


def _binding_key(binding: Mapping[str, Any]) -> tuple[str, str] | str:
    receipt_id = _safe_text(binding.get("receipt_id"), "")
    if receipt_id:
        return _safe_id(receipt_id, label="binding receipt_id")
    adapter_id = _safe_id(binding.get("adapter_id"), label="binding adapter_id")
    role = _safe_id(binding.get("artifact_role") or binding.get("role"), label="binding artifact_role")
    return (adapter_id, role)


def _normalise_bindings(artifact_file_bindings: Any) -> dict[tuple[str, str] | str, Path]:
    normalised: dict[tuple[str, str] | str, Path] = {}
    for binding in _binding_entries(artifact_file_bindings):
        key = _binding_key(binding)
        if key in normalised:
            raise ValueError(f"duplicate artifact file binding: {key}")
        path_text = _safe_text(binding.get("path") or binding.get("artifact_path"))
        if not path_text:
            raise ValueError("artifact file binding path is required")
        normalised[key] = Path(path_text)
    return normalised


def _binding_for_receipt(receipt: Mapping[str, Any], bindings: Mapping[tuple[str, str] | str, Path]) -> Path:
    receipt_id = str(receipt["receipt_id"])
    pair = (str(receipt["adapter_id"]), str(receipt["artifact_role"]))
    if receipt_id in bindings:
        return bindings[receipt_id]
    if pair in bindings:
        return bindings[pair]
    raise ValueError(f"missing artifact file binding for receipt: {receipt_id}")


def _validated_artifacts(receipts: Sequence[Mapping[str, Any]], artifact_file_bindings: Any) -> list[dict[str, Any]]:
    bindings = _normalise_bindings(artifact_file_bindings)
    validated: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for receipt in receipts:
        path = _binding_for_receipt(receipt, bindings)
        if path in seen_paths:
            raise ValueError(f"duplicate artifact path supplied: {path}")
        seen_paths.add(path)
        expected_basename = _safe_basename(receipt["artifact_basename"], label="artifact_basename")
        if path.name != expected_basename:
            raise ValueError(f"artifact path basename mismatch for {receipt['receipt_id']}: expected {expected_basename}")
        data = _read_bytes(path)
        byte_count = len(data)
        digest = hashlib.sha256(data).hexdigest()
        if byte_count != int(receipt["byte_count"]):
            raise ValueError(f"artifact byte_count mismatch for {receipt['receipt_id']}")
        if digest != str(receipt["sha256"]).lower():
            raise ValueError(f"artifact sha256 mismatch for {receipt['receipt_id']}")
        validated.append(
            {
                "receipt_id": receipt["receipt_id"],
                "adapter_id": receipt["adapter_id"],
                "artifact_role": receipt["artifact_role"],
                "artifact_basename": expected_basename,
                "byte_count": byte_count,
                "sha256": digest,
                "source_url": _safe_text(receipt.get("source_url"), ""),
                "explicit_path_supplied": True,
                "full_path_serialized": False,
                "bytes_read_for_hash_validation": True,
                "path": path,
            }
        )
    return validated


def _source_url_for(adapter_id: str, artifacts: Sequence[Mapping[str, Any]], fallback_source_url: str) -> str:
    for artifact in artifacts:
        url = _safe_text(artifact.get("source_url"), "")
        if url:
            return url
    if fallback_source_url:
        return fallback_source_url
    raise ValueError(f"source_url is required for adapter: {adapter_id}")


def _public_validation_entries(validated_artifacts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "receipt_id": artifact["receipt_id"],
            "adapter_id": artifact["adapter_id"],
            "artifact_role": artifact["artifact_role"],
            "artifact_basename": artifact["artifact_basename"],
            "byte_count": artifact["byte_count"],
            "sha256": artifact["sha256"],
            "explicit_path_supplied": True,
            "full_path_serialized": False,
            "bytes_read_for_hash_validation": True,
        }
        for artifact in validated_artifacts
    ]


def build_source_adapter_artifact_intake(
    capture_session_package: Mapping[str, Any],
    artifact_file_bindings: Any,
    *,
    source_url: str = "",
    operator_notes: str = "",
) -> dict[str, Any]:
    """Validate explicit artifact files from a capture session and build shared artifact collections."""

    session = _as_mapping(capture_session_package, "capture_session_package")
    receipts = _normalise_receipts(session)
    validated = _validated_artifacts(receipts, artifact_file_bindings)
    fallback_source_url = _safe_text(source_url, "")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in validated:
        grouped[str(artifact["adapter_id"])].append(dict(artifact))

    collections: list[dict[str, Any]] = []
    collection_index_entries: list[dict[str, Any]] = []
    for adapter_id in sorted(grouped):
        group = grouped[adapter_id]
        adapter_source_url = _source_url_for(adapter_id, group, fallback_source_url)
        required_roles = [str(artifact["artifact_role"]) for artifact in group]
        collection = build_source_artifact_collection(
            adapter_id=adapter_id,
            source_url=adapter_source_url,
            artifacts=[
                SourceArtifactInput(
                    role=str(artifact["artifact_role"]),
                    path=artifact["path"],
                    description=f"Validated from capture receipt {artifact['receipt_id']}",
                )
                for artifact in group
            ],
            required_roles=required_roles,
            operator_notes=operator_notes,
        )
        collections.append(collection)
        collection_index_entries.append(
            {
                "adapter_id": adapter_id,
                "source_url": adapter_source_url,
                "collection_id": collection.get("collection_id", ""),
                "artifact_count": collection.get("artifact_count", 0),
                "collection_status": collection.get("collection_status", ""),
            }
        )

    validation_report = {
        "schema_version": VALIDATION_REPORT_SCHEMA_VERSION,
        "validation_status": "PASSED",
        "source_adapter_capture_session_id": _safe_text(session.get("source_adapter_capture_session_id"), ""),
        "receipt_count": len(receipts),
        "artifact_file_count": len(validated),
        "validations": _public_validation_entries(validated),
        "issue_count": 0,
        "issues": [],
    }
    collection_index = {
        "schema_version": COLLECTION_INDEX_SCHEMA_VERSION,
        "collection_count": len(collection_index_entries),
        "collections": collection_index_entries,
    }
    collection_handoff = {
        "schema_version": COLLECTION_HANDOFF_SCHEMA_VERSION,
        "handoff_status": COLLECTION_HANDOFF_STATUS,
        "ready_for_content_extraction": True,
        "ready_for_comment_extraction": True,
        "collection_count": len(collection_index_entries),
        "collection_ids": [entry["collection_id"] for entry in collection_index_entries],
        "uses_shared_source_artifact_collection": True,
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": ARTIFACT_INTAKE_STATUS,
        "receipt_count": len(receipts),
        "artifact_file_count": len(validated),
        "collection_count": len(collection_index_entries),
        "live_network_default": False,
        "manual_or_live_actions_started_by_this_stage": False,
        "next_actions": [
            "Route the generated source artifact collections into shared content/comment extraction.",
            "Keep downstream extraction adapter-neutral unless a unique site surface requires code.",
            "Do not serialize full local artifact paths in review or release outputs.",
        ],
    }

    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "artifact_intake_status": ARTIFACT_INTAKE_STATUS,
        "source_adapter_capture_session_id": _safe_text(session.get("source_adapter_capture_session_id"), ""),
        "receipt_count": len(receipts),
        "artifact_file_count": len(validated),
        "collection_count": len(collection_index_entries),
        "validation_report": validation_report,
        "collection_index": collection_index,
        "source_artifact_collections": collections,
        "source_artifact_collection_handoff": collection_handoff,
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
            "full_local_paths_serialized": False,
            "forbidden_runtime_effects": list(FORBIDDEN_RUNTIME_EFFECTS),
        },
    }
    intake_id = f"source_adapter_artifact_intake.{_stable_hash(unsigned)}"
    package = dict(unsigned)
    package["source_adapter_artifact_intake_id"] = intake_id
    package["validation_report"] = dict(validation_report, source_adapter_artifact_intake_id=intake_id)
    package["collection_index"] = dict(collection_index, source_adapter_artifact_intake_id=intake_id)
    package["source_artifact_collection_handoff"] = dict(collection_handoff, source_adapter_artifact_intake_id=intake_id)
    package["operator_summary"] = dict(operator_summary, source_adapter_artifact_intake_id=intake_id)
    return package


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_artifact_intake_package": dict(pkg),
        "source_adapter_artifact_intake_validation_report": deepcopy(pkg.get("validation_report", {})),
        "source_adapter_artifact_collection_index": deepcopy(pkg.get("collection_index", {})),
        "source_adapter_artifact_collection_handoff": deepcopy(pkg.get("source_artifact_collection_handoff", {})),
        "source_adapter_artifact_intake_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "article.html"
        path.write_bytes(b"<html>example</html>")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        session = {
            "source_adapter_capture_session_id": "source_adapter_capture_session.example",
            "artifact_receipts": [
                {
                    "receipt_id": "article.article_html_or_text.article.html",
                    "adapter_id": "article",
                    "artifact_role": "article_html_or_text",
                    "artifact_basename": "article.html",
                    "byte_count": path.stat().st_size,
                    "sha256": digest,
                    "source_url": "https://article.example/story",
                }
            ],
        }
        built = build_source_adapter_artifact_intake(session, {"article.article_html_or_text.article.html": str(path)})
        assert built["artifact_intake_status"] == ARTIFACT_INTAKE_STATUS
        assert built["source_artifact_collection_handoff"]["ready_for_content_extraction"] is True
    print("Source Adapter Artifact Intake self-test passed.")
