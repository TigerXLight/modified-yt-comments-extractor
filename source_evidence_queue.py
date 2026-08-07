from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_evidence_queue_v1"
QUEUE_INDEX_SCHEMA_VERSION = "source_evidence_queue_index_v1"
REVIEW_HANDOFF_SCHEMA_VERSION = "source_evidence_review_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_evidence_queue_operator_summary_v1"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")

def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"


def _stable_hash(data: Mapping[str, Any], *, length: int = 12) -> str:
    return hashlib.sha256(_json_bytes(data)).hexdigest()[:length]


def _clean_identifier(value: object, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    text = _SAFE_ID_RE.sub(".", text).strip("._-")
    return text or fallback


def _coerce_mapping(value: Mapping[str, Any] | None, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _first_text(mapping: Mapping[str, Any], keys: Iterable[str], *, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _first_int(mapping: Mapping[str, Any], keys: Iterable[str], *, default: int = 0) -> int:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return default


def _safe_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text or "\\" in text or re.match(r"^[a-zA-Z]:", text):
        raise ValueError("artifact filenames must be safe basenames, not paths")
    return text


def _package_id(package: Mapping[str, Any]) -> str:
    return _clean_identifier(package.get("total_export_package_id"), fallback="source.total_export_package")


def _adapter_id(package: Mapping[str, Any], *, fallback: str = "source") -> str:
    return _clean_identifier(package.get("adapter_id"), fallback=fallback)


def _capture_bundle_id(package: Mapping[str, Any]) -> str:
    return _clean_identifier(package.get("capture_bundle_id"), fallback="source.capture_bundle")


def _source_url(package: Mapping[str, Any], handoff: Mapping[str, Any]) -> str:
    return _first_text(package, ("source_url", "url", "canonical_url"), default=_first_text(handoff, ("source_url", "url"), default=""))


def _content_summary(package: Mapping[str, Any]) -> dict[str, Any]:
    content = package.get("content")
    if not isinstance(content, Mapping):
        raise ValueError("total_export_package.content object is required")
    title = _first_text(content, ("title", "headline", "article_title"), default="")
    body_sha256 = _first_text(content, ("body_sha256", "sha256"), default="")
    body_char_count = _first_int(content, ("body_char_count", "char_count"), default=0)
    if not title and not body_sha256 and body_char_count <= 0:
        raise ValueError("total_export_package.content must include title, body_sha256, or body_char_count")
    return {
        "title": title,
        "body_sha256": body_sha256,
        "body_char_count": max(body_char_count, 0),
        "content_extraction_id": _first_text(content, ("content_extraction_id", "extraction_id"), default=""),
    }


def _comment_summary(package: Mapping[str, Any]) -> dict[str, Any]:
    comments = package.get("comments")
    if not isinstance(comments, Mapping):
        return {"available": False, "comment_count": 0, "comment_extraction_id": ""}
    count = max(_first_int(comments, ("comment_count", "total_comments", "comments_count"), default=0), 0)
    return {
        "available": bool(comments.get("available")) or count > 0,
        "comment_count": count,
        "comment_extraction_id": _first_text(comments, ("comment_extraction_id", "comments_extraction_id", "extraction_id"), default=""),
    }


def _artifact_index(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts = package.get("artifact_index")
    if not isinstance(artifacts, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        filename = _safe_basename(item.get("filename") or item.get("basename") or item.get("safe_basename"))
        if not filename:
            continue
        role = _clean_identifier(item.get("role") or item.get("artifact_role") or item.get("type"), fallback="artifact")
        key = (role, filename)
        if key in seen:
            continue
        seen.add(key)
        byte_count = item.get("byte_count")
        if not isinstance(byte_count, int) or byte_count < 0:
            byte_count = 0
        result.append(
            {
                "role": role,
                "filename": filename,
                "sha256": str(item.get("sha256") or "").strip(),
                "byte_count": byte_count,
                "source_stage": _clean_identifier(item.get("input_stage") or item.get("source_stage"), fallback="source_total_export_package"),
            }
        )
    result.sort(key=lambda entry: (entry["role"], entry["filename"]))
    return result


def _handoff_from_package(package: Mapping[str, Any], explicit_handoff: Mapping[str, Any]) -> dict[str, Any]:
    if explicit_handoff:
        return dict(explicit_handoff)
    embedded = package.get("evidence_queue_handoff")
    if isinstance(embedded, Mapping):
        return dict(embedded)
    return {}


def _review_actions(*, comments: Mapping[str, Any], artifact_count: int) -> list[dict[str, Any]]:
    actions = [
        {
            "action_id": "verify_source_identity",
            "label": "Confirm adapter, source URL, title, and capture identity before review.",
            "required": True,
        },
        {
            "action_id": "review_content_text",
            "label": "Review extracted content text against supplied artifacts.",
            "required": True,
        },
        {
            "action_id": "review_artifact_hashes",
            "label": "Confirm listed artifacts are present in the operator package and hashes match receipts.",
            "required": artifact_count > 0,
        },
        {
            "action_id": "decide_evidence_status",
            "label": "Record APPROVED, REJECTED, or REVISION_REQUESTED in the shared evidence review stage.",
            "required": True,
        },
    ]
    if comments.get("available"):
        actions.insert(
            2,
            {
                "action_id": "review_comments",
                "label": "Review extracted comments/replies against supplied comments artifacts.",
                "required": True,
            },
        )
    return actions


@dataclass(frozen=True)
class SourceEvidenceQueueOutputs:
    evidence_queue_item: dict[str, Any]
    evidence_queue_index: dict[str, Any]
    evidence_review_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_queue_item": self.evidence_queue_item,
            "evidence_queue_index": self.evidence_queue_index,
            "evidence_review_handoff": self.evidence_review_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_evidence_queue(
    *,
    total_export_package: Mapping[str, Any],
    evidence_queue_handoff: Mapping[str, Any] | None = None,
    queue_profile: str = "source_adapter_shared_v1",
    queue_notes: Iterable[str] | None = None,
) -> SourceEvidenceQueueOutputs:
    package = _coerce_mapping(total_export_package, name="total_export_package")
    handoff = _handoff_from_package(package, _coerce_mapping(evidence_queue_handoff, name="evidence_queue_handoff"))

    if package.get("schema_version") != "source_total_export_package_v1":
        raise ValueError("total_export_package schema_version must be source_total_export_package_v1")
    if package.get("export_status") != "READY_FOR_EVIDENCE_QUEUE":
        raise ValueError("total_export_package.export_status must be READY_FOR_EVIDENCE_QUEUE")

    package_id = _package_id(package)
    capture_bundle_id = _capture_bundle_id(package)
    adapter = _adapter_id(package)
    source_url = _source_url(package, handoff)
    profile = _clean_identifier(queue_profile, fallback="source_adapter_shared_v1")
    content = _content_summary(package)
    comments = _comment_summary(package)
    artifacts = _artifact_index(package)
    notes = [str(note).strip() for note in (queue_notes or []) if str(note).strip()]

    if handoff:
        if handoff.get("schema_version") != "source_total_export_evidence_queue_handoff_v1":
            raise ValueError("evidence_queue_handoff schema_version mismatch")
        if handoff.get("total_export_package_id") and str(handoff.get("total_export_package_id")) != package_id:
            raise ValueError("evidence_queue_handoff.total_export_package_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_EVIDENCE_QUEUE":
            raise ValueError("evidence_queue_handoff must be READY_FOR_EVIDENCE_QUEUE")

    identity_seed = {
        "adapter_id": adapter,
        "source_url": source_url,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "content": content,
        "comments": comments,
        "artifact_index": artifacts,
        "queue_profile": profile,
    }
    queue_item_id = f"{adapter}.evidence_queue.{_stable_hash(identity_seed)}"
    review_actions = _review_actions(comments=comments, artifact_count=len(artifacts))

    evidence_queue_item = {
        "schema_version": SCHEMA_VERSION,
        "queue_item_id": queue_item_id,
        "queue_status": "READY_FOR_EVIDENCE_REVIEW",
        "review_state": "PENDING_REVIEW",
        "adapter_id": adapter,
        "source_url": source_url,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "queue_profile": profile,
        "content_summary": content,
        "comment_summary": comments,
        "artifact_count": len(artifacts),
        "artifact_index": artifacts,
        "review_actions": review_actions,
        "queue_notes": notes,
    }

    evidence_queue_index = {
        "schema_version": QUEUE_INDEX_SCHEMA_VERSION,
        "queue_profile": profile,
        "queue_item_count": 1,
        "ready_for_review_count": 1,
        "items": [
            {
                "queue_item_id": queue_item_id,
                "queue_status": "READY_FOR_EVIDENCE_REVIEW",
                "adapter_id": adapter,
                "source_url": source_url,
                "total_export_package_id": package_id,
                "title": content["title"],
                "comment_count": comments["comment_count"],
                "artifact_count": len(artifacts),
            }
        ],
    }

    evidence_review_handoff = {
        "schema_version": REVIEW_HANDOFF_SCHEMA_VERSION,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": "READY_FOR_EVIDENCE_REVIEW",
        "required_next_stage": "source_evidence_review",
        "review_inputs": [
            {"role": "source_evidence_queue_item", "id": queue_item_id, "filename_hint": f"{queue_item_id}.source_evidence_queue_item.json"},
            {"role": "source_evidence_queue_index", "id": queue_item_id, "filename_hint": f"{queue_item_id}.source_evidence_queue_index.json"},
        ],
        "required_review_actions": [action["action_id"] for action in review_actions if action.get("required")],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_total_export_package_json_only",
        "queue_profile": profile,
        "review_action_count": len(review_actions),
        "queue_notes": notes,
        "next_actions": [
            "Pass the Evidence Review handoff to the shared source_evidence_review stage.",
            "Reviewer records APPROVED, REJECTED, or REVISION_REQUESTED without mutating the original package.",
            "Keep future adapters on this shared queue contract unless their evidence review identity genuinely differs.",
        ],
    }

    return SourceEvidenceQueueOutputs(
        evidence_queue_item=evidence_queue_item,
        evidence_queue_index=evidence_queue_index,
        evidence_review_handoff=evidence_review_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
