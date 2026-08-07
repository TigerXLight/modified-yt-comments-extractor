from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from source_capture_bundle import build_source_capture_bundle

SCHEMA_VERSION = "source_adapter_capture_bundle_bridge_v1"
BUNDLE_INDEX_SCHEMA_VERSION = "source_adapter_capture_bundle_index_v1"
TOTAL_EXPORT_HANDOFF_SCHEMA_VERSION = "source_adapter_total_export_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_adapter_capture_bundle_bridge_operator_summary_v1"
CAPTURE_BUNDLE_BRIDGE_STATUS = "SHARED_CAPTURE_BUNDLES_BUILT"
TOTAL_EXPORT_HANDOFF_STATUS = "READY_FOR_SHARED_TOTAL_EXPORT_PACKAGE"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()[:length]


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _as_mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return [_as_mapping(item, f"{label} item") for item in value]


def _safe_text(value: Any, default: str = "") -> str:
    return str(value if value is not None else default).replace("\r", " ").strip()


def _safe_id(value: Any, *, label: str, fallback: str = "") -> str:
    text = _safe_text(value, fallback)
    if not text:
        raise ValueError(f"{label} is required")
    if not _SAFE_ID_RE.match(text):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore, or dash")
    return text


def _normalise_notes(operator_notes: Iterable[str] | None) -> list[str]:
    return [str(note).strip() for note in (operator_notes or []) if str(note).strip()]


def _content_items(extraction_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(extraction_bridge_package.get("content_extractions"), "content_extractions")


def _comment_items(extraction_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = extraction_bridge_package.get("comment_extractions")
    if value is None:
        return []
    return _as_mapping_list(value, "comment_extractions")


def _route_items(extraction_bridge_package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _as_mapping_list(extraction_bridge_package.get("extraction_routes"), "extraction_routes")


def _route_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return (_safe_id(value.get("adapter_id"), label="adapter_id"), _safe_text(value.get("source_url"), ""))


def _content_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return (_safe_id(value.get("adapter_id"), label="content adapter_id"), _safe_text(value.get("source_url"), ""))


def _comment_key(value: Mapping[str, Any]) -> tuple[str, str]:
    return (_safe_id(value.get("adapter_id"), label="comment adapter_id"), _safe_text(value.get("source_url"), ""))


def _collection_from_route(route: Mapping[str, Any]) -> dict[str, Any]:
    adapter_id = _safe_id(route.get("adapter_id"), label="route adapter_id")
    source_url = _safe_text(route.get("source_url"), "")
    artifacts = route.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
    collection_id = _safe_text(route.get("collection_id"), "") or f"{adapter_id}.source_artifacts"
    return {
        "schema_version": "source_artifact_collection_v1",
        "collection_id": collection_id,
        "artifact_collection_id": collection_id,
        "adapter_id": adapter_id,
        "source_url": source_url,
        "collection_status": "READY_FOR_CAPTURE_BUNDLE",
        "artifacts": [dict(item) for item in artifacts if isinstance(item, Mapping)],
    }


def _index_comments(comments: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in comments:
        key = _comment_key(item)
        if key in indexed:
            raise ValueError(f"duplicate comment extraction for adapter/source: {key[0]} {key[1]}")
        indexed[key] = item
    return indexed


def _index_routes(routes: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in routes:
        key = _route_key(item)
        if key in indexed:
            raise ValueError(f"duplicate extraction route for adapter/source: {key[0]} {key[1]}")
        indexed[key] = item
    return indexed


def build_source_adapter_capture_bundle_bridge(
    extraction_bridge_package: Mapping[str, Any],
    *,
    operator_notes: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build shared capture bundles from a source adapter extraction bridge package."""

    package = _as_mapping(extraction_bridge_package, "extraction_bridge_package")
    if package.get("extraction_bridge_status") != "SHARED_EXTRACTIONS_PREPARED":
        raise ValueError("extraction bridge package must be SHARED_EXTRACTIONS_PREPARED")
    handoff = package.get("source_adapter_capture_bundle_handoff")
    if not isinstance(handoff, Mapping) or handoff.get("handoff_status") != "READY_FOR_SHARED_CAPTURE_BUNDLE":
        raise ValueError("extraction bridge handoff must be READY_FOR_SHARED_CAPTURE_BUNDLE")

    contents = _content_items(package)
    comments_by_key = _index_comments(_comment_items(package))
    routes_by_key = _index_routes(_route_items(package))
    notes = _normalise_notes(operator_notes)

    if not contents:
        raise ValueError("at least one content extraction is required")

    capture_bundle_outputs: list[dict[str, Any]] = []
    bundle_rows: list[dict[str, Any]] = []
    issue_rows: list[str] = []

    for content in contents:
        key = _content_key(content)
        adapter_id, source_url = key
        route = routes_by_key.get(key)
        if route is None:
            issue_rows.append(f"missing extraction route for adapter/source: {adapter_id} {source_url}")
            continue
        collection = _collection_from_route(route)
        comment = comments_by_key.get(key)
        outputs = build_source_capture_bundle(
            content_extraction=content,
            comment_extraction=comment,
            artifact_collection=collection,
            adapter_id=adapter_id,
            source_url=source_url,
            operator_notes=notes,
        ).as_dict()
        bundle = _as_mapping(outputs.get("capture_bundle"), "capture_bundle")
        manifest = _as_mapping(outputs.get("capture_manifest"), "capture_manifest")
        total_handoff = _as_mapping(outputs.get("total_export_handoff"), "total_export_handoff")
        capture_bundle_outputs.append(dict(outputs))
        bundle_rows.append(
            {
                "adapter_id": adapter_id,
                "source_url": source_url,
                "capture_bundle_id": bundle.get("capture_bundle_id", ""),
                "content_extraction_id": content.get("content_id") or content.get("content_extraction_id") or "",
                "comment_extraction_id": comment.get("comment_extraction_id", "") if isinstance(comment, Mapping) else "",
                "artifact_count": manifest.get("artifact_count", 0),
                "comment_count": manifest.get("comment_count", 0),
                "handoff_status": total_handoff.get("handoff_status", ""),
            }
        )

    ready = bool(capture_bundle_outputs) and not issue_rows
    bundle_index = {
        "schema_version": BUNDLE_INDEX_SCHEMA_VERSION,
        "capture_bundle_count": len(capture_bundle_outputs),
        "bundle_rows": bundle_rows,
    }
    total_export_handoff = {
        "schema_version": TOTAL_EXPORT_HANDOFF_SCHEMA_VERSION,
        "handoff_status": TOTAL_EXPORT_HANDOFF_STATUS if ready else "CAPTURE_BUNDLE_BRIDGE_BLOCKED",
        "ready_for_total_export_package": ready,
        "required_next_stage": "source_total_export_package",
        "capture_bundle_ids": [row["capture_bundle_id"] for row in bundle_rows],
        "total_export_inputs": [
            {
                "role": "source_capture_bundle",
                "id": row["capture_bundle_id"],
                "filename_hint": f"{row['capture_bundle_id']}.source_capture_bundle.json",
            }
            for row in bundle_rows
        ],
    }
    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": CAPTURE_BUNDLE_BRIDGE_STATUS if ready else "CAPTURE_BUNDLE_BRIDGE_BLOCKED",
        "capture_bundle_count": len(capture_bundle_outputs),
        "issue_count": len(issue_rows),
        "operator_notes": notes,
        "implemented_stage": "source_capture_bundle",
        "next_actions": [
            "Pass each capture bundle and manifest to the shared Total Export package stage.",
            "Keep adapter work focused on source metadata and fixtures unless extraction behavior diverges.",
            "Use the bundle index to track multi-source capture package readiness.",
        ],
    }
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "capture_bundle_bridge_status": CAPTURE_BUNDLE_BRIDGE_STATUS if ready else "CAPTURE_BUNDLE_BRIDGE_BLOCKED",
        "source_adapter_extraction_bridge_id": _safe_text(package.get("source_adapter_extraction_bridge_id"), ""),
        "capture_bundle_count": len(capture_bundle_outputs),
        "issue_count": len(issue_rows),
        "issues": issue_rows,
        "capture_bundle_outputs": capture_bundle_outputs,
        "source_adapter_capture_bundle_index": bundle_index,
        "source_adapter_total_export_handoff": total_export_handoff,
        "operator_summary": operator_summary,
        "implementation_logic": {
            "shared_stage_executed": "source_capture_bundle",
            "input_source": "source_adapter_extraction_bridge",
            "per_adapter_path": "metadata_route_plus_shared_bundle_builder",
            "multi_adapter_batch_supported": True,
        },
    }
    bridge_id = f"source_adapter_capture_bundle_bridge.{_stable_hash(unsigned)}"
    result = dict(unsigned)
    result["source_adapter_capture_bundle_bridge_id"] = bridge_id
    result["source_adapter_capture_bundle_index"] = dict(bundle_index, source_adapter_capture_bundle_bridge_id=bridge_id)
    result["source_adapter_total_export_handoff"] = dict(total_export_handoff, source_adapter_capture_bundle_bridge_id=bridge_id)
    result["operator_summary"] = dict(operator_summary, source_adapter_capture_bundle_bridge_id=bridge_id)
    return result


def output_documents(package: Mapping[str, Any]) -> dict[str, Any]:
    pkg = _as_mapping(package, "package")
    return {
        "source_adapter_capture_bundle_bridge_package": dict(pkg),
        "source_adapter_capture_bundle_batch": deepcopy(pkg.get("capture_bundle_outputs", [])),
        "source_adapter_capture_bundle_index": deepcopy(pkg.get("source_adapter_capture_bundle_index", {})),
        "source_adapter_total_export_handoff": deepcopy(pkg.get("source_adapter_total_export_handoff", {})),
        "source_adapter_capture_bundle_bridge_operator_summary": deepcopy(pkg.get("operator_summary", {})),
    }


if __name__ == "__main__":
    content = {
        "adapter_id": "article",
        "source_url": "https://article.example/story",
        "content_id": "article.content.1234",
        "title": "Example title",
        "body_text": "Example body.",
    }
    extraction_bridge = {
        "extraction_bridge_status": "SHARED_EXTRACTIONS_PREPARED",
        "source_adapter_extraction_bridge_id": "source_adapter_extraction_bridge.example",
        "source_adapter_capture_bundle_handoff": {"handoff_status": "READY_FOR_SHARED_CAPTURE_BUNDLE"},
        "content_extractions": [content],
        "comment_extractions": [
            {
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "comment_extraction_id": "article.comments.1234",
                "comment_count": 1,
                "comments": [{"id": "c1", "text": "Example comment"}],
            }
        ],
        "extraction_routes": [
            {
                "adapter_id": "article",
                "source_url": "https://article.example/story",
                "collection_id": "article.collection.1234",
                "artifacts": [
                    {"role": "article_html_or_text", "filename": "article.html", "byte_count": 20, "sha256": "a" * 64},
                ],
            }
        ],
    }
    built = build_source_adapter_capture_bundle_bridge(extraction_bridge)
    assert built["capture_bundle_bridge_status"] == CAPTURE_BUNDLE_BRIDGE_STATUS
    assert built["source_adapter_total_export_handoff"]["ready_for_total_export_package"] is True
    print("Source Adapter Capture Bundle Bridge self-test passed.")
