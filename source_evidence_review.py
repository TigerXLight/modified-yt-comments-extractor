from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "source_evidence_review_v1"
CHECKLIST_SCHEMA_VERSION = "source_evidence_review_checklist_v1"
DECISION_SCHEMA_VERSION = "source_evidence_review_decision_v1"
RELEASE_HANDOFF_SCHEMA_VERSION = "source_evidence_review_release_handoff_v1"
SUMMARY_SCHEMA_VERSION = "source_evidence_review_operator_summary_v1"

_ALLOWED_DECISIONS = {"PENDING_DECISION", "APPROVED", "REJECTED", "REVISION_REQUESTED"}
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


def _safe_basename(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "/" in text or "\\" in text or re.match(r"^[a-zA-Z]:", text):
        raise ValueError("artifact filenames must be safe basenames, not paths")
    return text


def _normalise_action(action: Mapping[str, Any]) -> dict[str, Any]:
    action_id = _clean_identifier(action.get("action_id"), fallback="review_action")
    return {
        "action_id": action_id,
        "label": str(action.get("label") or action_id).strip(),
        "required": bool(action.get("required")),
    }


def _review_actions(queue_item: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions = queue_item.get("review_actions")
    normalised: list[dict[str, Any]] = []
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, Mapping):
                normalised.append(_normalise_action(action))
    if not normalised:
        normalised = [
            {"action_id": "verify_source_identity", "label": "Confirm adapter, source URL, and source identity.", "required": True},
            {"action_id": "review_content_text", "label": "Review extracted content text against supplied artifacts.", "required": True},
            {"action_id": "decide_evidence_status", "label": "Record the evidence review decision.", "required": True},
        ]
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for action in normalised:
        if action["action_id"] in seen:
            continue
        seen.add(action["action_id"])
        unique.append(action)
    return unique


def _required_action_ids(actions: Iterable[Mapping[str, Any]]) -> list[str]:
    return [str(action.get("action_id")) for action in actions if action.get("required") and str(action.get("action_id") or "")]


def _normalise_completed_actions(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values: Iterable[object] = [piece for piece in value.split(",")]
    elif isinstance(value, Iterable):
        values = value
    else:
        values = []
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        action_id = str(item or "").strip()
        if not action_id or action_id in seen:
            continue
        seen.add(action_id)
        result.append(action_id)
    return result


def _artifact_index(queue_item: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts = queue_item.get("artifact_index")
    if not isinstance(artifacts, list):
        return []
    result: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        filename = _safe_basename(item.get("filename") or item.get("basename") or item.get("safe_basename"))
        if not filename:
            continue
        result.append(
            {
                "role": _clean_identifier(item.get("role") or item.get("artifact_role"), fallback="artifact"),
                "filename": filename,
                "sha256": str(item.get("sha256") or "").strip(),
                "byte_count": item.get("byte_count") if isinstance(item.get("byte_count"), int) and item.get("byte_count") >= 0 else 0,
                "source_stage": _clean_identifier(item.get("source_stage") or item.get("input_stage"), fallback="source_evidence_queue"),
            }
        )
    result.sort(key=lambda entry: (entry["role"], entry["filename"]))
    return result


def _normalise_decision(decision: Mapping[str, Any]) -> str:
    raw = str(decision.get("decision") or decision.get("review_decision") or decision.get("status") or "PENDING_DECISION").strip().upper()
    if raw not in _ALLOWED_DECISIONS:
        raise ValueError(f"review decision must be one of: {', '.join(sorted(_ALLOWED_DECISIONS))}")
    return raw


def _handoff_from_queue(queue_item: Mapping[str, Any], explicit_handoff: Mapping[str, Any]) -> dict[str, Any]:
    if explicit_handoff:
        return dict(explicit_handoff)
    embedded = queue_item.get("evidence_review_handoff")
    if isinstance(embedded, Mapping):
        return dict(embedded)
    return {}


@dataclass(frozen=True)
class SourceEvidenceReviewOutputs:
    evidence_review_package: dict[str, Any]
    evidence_review_checklist: dict[str, Any]
    evidence_review_decision: dict[str, Any]
    release_handoff: dict[str, Any]
    operator_summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_review_package": self.evidence_review_package,
            "evidence_review_checklist": self.evidence_review_checklist,
            "evidence_review_decision": self.evidence_review_decision,
            "release_handoff": self.release_handoff,
            "operator_summary": self.operator_summary,
        }


def build_source_evidence_review(
    *,
    evidence_queue_item: Mapping[str, Any],
    evidence_review_handoff: Mapping[str, Any] | None = None,
    reviewer_decision: Mapping[str, Any] | None = None,
    reviewer_id: str = "manual_reviewer",
    review_profile: str = "source_adapter_shared_review_v1",
    review_notes: Iterable[str] | None = None,
) -> SourceEvidenceReviewOutputs:
    queue_item = _coerce_mapping(evidence_queue_item, name="evidence_queue_item")
    handoff = _handoff_from_queue(queue_item, _coerce_mapping(evidence_review_handoff, name="evidence_review_handoff"))
    decision_input = _coerce_mapping(reviewer_decision, name="reviewer_decision")

    if queue_item.get("schema_version") != "source_evidence_queue_v1":
        raise ValueError("evidence_queue_item schema_version must be source_evidence_queue_v1")
    if queue_item.get("queue_status") != "READY_FOR_EVIDENCE_REVIEW":
        raise ValueError("evidence_queue_item.queue_status must be READY_FOR_EVIDENCE_REVIEW")
    if queue_item.get("review_state") != "PENDING_REVIEW":
        raise ValueError("evidence_queue_item.review_state must be PENDING_REVIEW")

    queue_item_id = _clean_identifier(queue_item.get("queue_item_id"), fallback="source.evidence_queue")
    package_id = _clean_identifier(queue_item.get("total_export_package_id"), fallback="source.total_export_package")
    capture_bundle_id = _clean_identifier(queue_item.get("capture_bundle_id"), fallback="source.capture_bundle")
    adapter = _clean_identifier(queue_item.get("adapter_id"), fallback="source")
    source_url = _first_text(queue_item, ("source_url", "url", "canonical_url"), default="")
    profile = _clean_identifier(review_profile, fallback="source_adapter_shared_review_v1")

    if handoff:
        if handoff.get("schema_version") != "source_evidence_review_handoff_v1":
            raise ValueError("evidence_review_handoff schema_version mismatch")
        if handoff.get("queue_item_id") and str(handoff.get("queue_item_id")) != queue_item_id:
            raise ValueError("evidence_review_handoff.queue_item_id mismatch")
        if handoff.get("handoff_status") != "READY_FOR_EVIDENCE_REVIEW":
            raise ValueError("evidence_review_handoff must be READY_FOR_EVIDENCE_REVIEW")

    actions = _review_actions(queue_item)
    required = _required_action_ids(actions)
    decision = _normalise_decision(decision_input)
    completed = _normalise_completed_actions(decision_input.get("completed_action_ids"))
    if decision != "PENDING_DECISION" and not completed:
        completed = required
    missing_required = [action_id for action_id in required if action_id not in completed]
    if decision != "PENDING_DECISION" and missing_required:
        raise ValueError("reviewer_decision.completed_action_ids is missing required review actions: " + ", ".join(missing_required))

    reviewer = _clean_identifier(decision_input.get("reviewer_id") or reviewer_id, fallback="manual_reviewer")
    notes = [str(note).strip() for note in (review_notes or []) if str(note).strip()]
    notes.extend(str(note).strip() for note in decision_input.get("notes", []) if isinstance(decision_input.get("notes"), list) for note in [note] if str(note).strip())

    review_seed = {
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "review_profile": profile,
    }
    review_package_id = f"{adapter}.evidence_review.{_stable_hash(review_seed)}"

    content_summary = queue_item.get("content_summary") if isinstance(queue_item.get("content_summary"), Mapping) else {}
    comment_summary = queue_item.get("comment_summary") if isinstance(queue_item.get("comment_summary"), Mapping) else {}
    artifacts = _artifact_index(queue_item)

    evidence_review_package = {
        "schema_version": SCHEMA_VERSION,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "review_profile": profile,
        "review_package_status": "READY_FOR_REVIEW_DECISION",
        "content_summary": dict(content_summary),
        "comment_summary": dict(comment_summary),
        "artifact_count": len(artifacts),
        "artifact_index": artifacts,
        "required_review_actions": required,
        "review_inputs": handoff.get("review_inputs") if isinstance(handoff.get("review_inputs"), list) else [],
    }

    checklist_items = [
        {
            "action_id": action["action_id"],
            "label": action["label"],
            "required": action["required"],
            "completed": action["action_id"] in completed,
        }
        for action in actions
    ]
    evidence_review_checklist = {
        "schema_version": CHECKLIST_SCHEMA_VERSION,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "checklist_status": "COMPLETE" if decision != "PENDING_DECISION" and not missing_required else "PENDING",
        "required_action_count": len(required),
        "completed_required_action_count": len([action_id for action_id in required if action_id in completed]),
        "items": checklist_items,
    }

    approved = decision == "APPROVED"
    if approved:
        review_status = "APPROVED_FOR_RELEASE"
        handoff_status = "READY_FOR_APPROVED_RELEASE"
    elif decision == "REJECTED":
        review_status = "REJECTED"
        handoff_status = "NOT_READY_REJECTED"
    elif decision == "REVISION_REQUESTED":
        review_status = "REVISION_REQUESTED"
        handoff_status = "NOT_READY_REVISION_REQUESTED"
    else:
        review_status = "PENDING_DECISION"
        handoff_status = "NOT_READY_PENDING_DECISION"

    evidence_review_decision = {
        "schema_version": DECISION_SCHEMA_VERSION,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "decision": decision,
        "review_status": review_status,
        "reviewer_id": reviewer,
        "approved_for_release": approved,
        "revision_required": decision == "REVISION_REQUESTED",
        "completed_action_ids": completed,
        "missing_required_action_ids": missing_required,
        "review_notes": notes,
    }

    release_handoff = {
        "schema_version": RELEASE_HANDOFF_SCHEMA_VERSION,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "capture_bundle_id": capture_bundle_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "handoff_status": handoff_status,
        "required_next_stage": "source_approved_release" if approved else "source_evidence_review",
        "decision": decision,
        "release_inputs": [
            {"role": "source_evidence_review_package", "id": review_package_id, "filename_hint": f"{review_package_id}.source_evidence_review_package.json"},
            {"role": "source_evidence_review_decision", "id": review_package_id, "filename_hint": f"{review_package_id}.source_evidence_review_decision.json"},
        ],
    }

    operator_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "evidence_review_package_id": review_package_id,
        "queue_item_id": queue_item_id,
        "total_export_package_id": package_id,
        "adapter_id": adapter,
        "source_url": source_url,
        "manual_or_live_actions_started": False,
        "input_mode": "explicit_evidence_queue_json_only",
        "decision": decision,
        "review_status": review_status,
        "handoff_status": handoff_status,
        "next_actions": [
            "If APPROVED, pass the release handoff to the shared source_approved_release stage.",
            "If REJECTED or REVISION_REQUESTED, keep the original evidence immutable and create a new corrected capture/review packet.",
            "Use this shared review contract for future adapters rather than cloning MSN-specific review modules.",
        ],
    }

    return SourceEvidenceReviewOutputs(
        evidence_review_package=evidence_review_package,
        evidence_review_checklist=evidence_review_checklist,
        evidence_review_decision=evidence_review_decision,
        release_handoff=release_handoff,
        operator_summary=operator_summary,
    )


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def dump_json(data: Mapping[str, Any]) -> str:
    return _json_bytes(data).decode("utf-8")
