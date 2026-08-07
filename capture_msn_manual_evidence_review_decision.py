from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION = "msn_manual_evidence_review_decision_v1"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION = "msn_manual_evidence_review_package_v1"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED = "APPROVED"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REJECTED = "REJECTED"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REVISION_REQUESTED = "REVISION_REQUESTED"
MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS = {
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REJECTED,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REVISION_REQUESTED,
}
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY = "DECISION_READY"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_NEEDS_REVIEW = "DECISION_NEEDS_REVIEW"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualEvidenceReviewDecisionAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0


@dataclass(frozen=True)
class MSNManualEvidenceReviewActionDecision:
    action_id: str
    label: str
    required: bool
    completed: bool


@dataclass(frozen=True)
class MSNManualEvidenceReviewDecisionReport:
    schema_version: str
    decision_id: str
    queue_item_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    reviewer_id: str
    review_decision: str
    decision_status: str
    approved_for_total_export: bool
    issue_count: int
    issues: list[str] = field(default_factory=list)
    assets: list[MSNManualEvidenceReviewDecisionAsset] = field(default_factory=list)
    review_actions: list[MSNManualEvidenceReviewActionDecision] = field(default_factory=list)
    evidence_queue_update: dict[str, str] = field(default_factory=dict)
    total_export_handoff: dict[str, str] = field(default_factory=dict)
    comments: list[str] = field(default_factory=list)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    decision_hash: str = ""


class MSNManualEvidenceReviewDecisionError(ValueError):
    pass


def _safe_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_id(value: Any, *, default: str) -> str:
    raw = _safe_text(value, default=default)
    safe = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return safe or default


def _safe_filename(value: Any, *, fallback: str) -> str:
    raw = _safe_text(value, default=fallback).replace("\\", "/").split("/")[-1]
    safe = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return safe or fallback


def _contains_path_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_path_like(child) for child in value)
    return False


def _ensure_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MSNManualEvidenceReviewDecisionError(f"{label} must be a JSON object")
    return value


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _normalise_assets(raw_assets: Any) -> list[MSNManualEvidenceReviewDecisionAsset]:
    assets: list[MSNManualEvidenceReviewDecisionAsset] = []
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes, bytearray)):
        return assets
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_assets, start=1):
        if not isinstance(raw, Mapping):
            continue
        role = _safe_id(raw.get("role", raw.get("asset_role", f"asset_{index}")), default=f"asset_{index}")
        filename = _safe_filename(
            raw.get("filename", raw.get("safe_filename", raw.get("name", raw.get("relative_path", f"asset_{index}.json")))),
            fallback=f"asset_{index}.json",
        )
        sha256 = _safe_text(raw.get("sha256", raw.get("hash", raw.get("content_sha256", ""))))
        byte_count = _read_int(raw.get("byte_count", raw.get("bytes", raw.get("size", 0))))
        key = (role, filename, sha256)
        if key in seen:
            continue
        seen.add(key)
        assets.append(MSNManualEvidenceReviewDecisionAsset(role=role, filename=filename, sha256=sha256, byte_count=byte_count))
    return assets


def _normalise_actions(raw_actions: Any, completed_action_ids: set[str]) -> list[MSNManualEvidenceReviewActionDecision]:
    actions: list[MSNManualEvidenceReviewActionDecision] = []
    if not isinstance(raw_actions, Sequence) or isinstance(raw_actions, (str, bytes, bytearray)):
        return actions
    for index, raw in enumerate(raw_actions, start=1):
        if not isinstance(raw, Mapping):
            continue
        action_id = _safe_id(raw.get("action_id", raw.get("id", f"review_action_{index}")), default=f"review_action_{index}")
        label = _safe_text(raw.get("label", raw.get("name", action_id)), default=action_id)
        required = bool(raw.get("required", True))
        completed = bool(raw.get("completed", False)) or action_id in completed_action_ids
        actions.append(MSNManualEvidenceReviewActionDecision(action_id=action_id, label=label, required=required, completed=completed))
    return actions


def _safe_comments(comments: Sequence[str] | None) -> list[str]:
    result: list[str] = []
    for comment in comments or []:
        text = _safe_text(comment)
        if not text:
            continue
        if _contains_path_like(text):
            raise MSNManualEvidenceReviewDecisionError("reviewer comments must not include full local paths")
        result.append(text)
    return result


def build_msn_manual_evidence_review_decision(
    review_package: Mapping[str, Any],
    *,
    review_decision: str,
    reviewer_id: str = "operator",
    completed_action_ids: Sequence[str] | None = None,
    comments: Sequence[str] | None = None,
) -> MSNManualEvidenceReviewDecisionReport:
    package = _ensure_mapping(review_package, label="review_package")
    decision = _safe_text(review_decision).upper()
    if decision not in MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS:
        raise MSNManualEvidenceReviewDecisionError(f"unsupported review_decision: {review_decision}")

    issues: list[str] = []
    if package.get("schema_version") != MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION:
        issues.append("review package schema_version mismatch")

    queue_item_id = _safe_id(package.get("queue_item_id", "msn_manual_queue_item"), default="msn_manual_queue_item")
    source_url = _safe_text(package.get("source_url"))
    named_site = _safe_text(package.get("named_site"), default="msn")
    named_action = _safe_text(package.get("named_action"), default="msn_manual_capture")
    article_title = _safe_text(package.get("article_title"), default="MSN manual capture review item")
    reviewer = _safe_id(reviewer_id, default="operator")

    for key, value in {
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
    }.items():
        if not value:
            issues.append(f"missing {key}")

    package_status = _safe_text(package.get("review_status"), default="")
    if package_status not in {"REVIEW_PENDING", "REVIEW_READY", "NEEDS_OPERATOR_REVIEW"}:
        issues.append("review package status is not recognised")

    assets = _normalise_assets(package.get("assets", []))
    if not assets:
        issues.append("review package has no assets")
    for asset in assets:
        if not asset.filename:
            issues.append(f"asset missing safe filename for role {asset.role}")
        if not asset.sha256:
            issues.append(f"asset missing sha256 for role {asset.role}")

    completed_ids = {_safe_id(action_id, default="review_action") for action_id in (completed_action_ids or []) if _safe_text(action_id)}
    actions = _normalise_actions(package.get("review_actions", []), completed_ids)
    if not actions:
        issues.append("review package has no review actions")
    missing_required = [action.action_id for action in actions if action.required and not action.completed]
    if decision == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED and missing_required:
        issues.append("approved decision is missing completed required review actions: " + ",".join(missing_required))

    package_issue_count = _read_int(package.get("source_issue_count", package.get("issue_count", 0)))
    if decision == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED and package_issue_count:
        issues.append("approved decision still has source issues")

    safe_flags = package.get("safety_flags")
    if not isinstance(safe_flags, Mapping):
        issues.append("review package missing safety_flags")
    else:
        for flag in ("metadata_only_review_package", "explicit_operator_artifacts_only", "no_live_http", "no_browser_automation", "no_full_local_paths"):
            if safe_flags.get(flag) is not True:
                issues.append(f"review package safety flag not true: {flag}")

    reviewer_comments = _safe_comments(comments)
    if _contains_path_like(package):
        issues.append("review package contains full local path-like text")

    approved_for_total_export = decision == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED and not issues
    queue_status = {
        MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED: "REVIEW_APPROVED",
        MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REJECTED: "REVIEW_REJECTED",
        MSN_MANUAL_EVIDENCE_REVIEW_DECISION_REVISION_REQUESTED: "REVISION_REQUESTED",
    }[decision]
    handoff_status = "READY_FOR_TOTAL_EXPORT" if approved_for_total_export else "BLOCKED_PENDING_REVIEW"
    decision_status = MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY if not issues else MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_NEEDS_REVIEW

    seed = {
        "queue_item_id": queue_item_id,
        "reviewer_id": reviewer,
        "review_decision": decision,
        "completed_action_ids": sorted(action.action_id for action in actions if action.completed),
        "asset_hashes": sorted(asset.sha256 for asset in assets if asset.sha256),
    }
    decision_hash = _sha256_json(seed)
    decision_id = f"{queue_item_id}.{decision.lower()}.{decision_hash[:12]}"

    report_without_hash = {
        "schema_version": MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION,
        "decision_id": decision_id,
        "queue_item_id": queue_item_id,
        "source_url": source_url,
        "named_site": named_site,
        "named_action": named_action,
        "article_title": article_title,
        "reviewer_id": reviewer,
        "review_decision": decision,
        "decision_status": decision_status,
        "approved_for_total_export": approved_for_total_export,
        "issue_count": len(issues),
        "issues": issues,
        "assets": [asdict(asset) for asset in assets],
        "review_actions": [asdict(action) for action in actions],
        "evidence_queue_update": {"queue_item_id": queue_item_id, "queue_status": queue_status},
        "total_export_handoff": {
            "queue_item_id": queue_item_id,
            "handoff_status": handoff_status,
            "next_cli": "capture_msn_manual_total_export_cli.py",
        },
        "comments": reviewer_comments,
        "safety_flags": {
            "metadata_only_decision": True,
            "explicit_review_package_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
        },
    }
    final_hash = _sha256_json(report_without_hash)
    return MSNManualEvidenceReviewDecisionReport(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION,
        decision_id=decision_id,
        queue_item_id=queue_item_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        reviewer_id=reviewer,
        review_decision=decision,
        decision_status=decision_status,
        approved_for_total_export=approved_for_total_export,
        issue_count=len(issues),
        issues=issues,
        assets=assets,
        review_actions=actions,
        evidence_queue_update={"queue_item_id": queue_item_id, "queue_status": queue_status},
        total_export_handoff={
            "queue_item_id": queue_item_id,
            "handoff_status": handoff_status,
            "next_cli": "capture_msn_manual_total_export_cli.py",
        },
        comments=reviewer_comments,
        safety_flags={
            "metadata_only_decision": True,
            "explicit_review_package_only": True,
            "no_live_http": True,
            "no_browser_automation": True,
            "no_full_local_paths": True,
            "no_credential_reads": True,
        },
        decision_hash=final_hash,
    )


def msn_manual_evidence_review_decision_to_json(report: MSNManualEvidenceReviewDecisionReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
