from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from capture_msn_manual_evidence_review_decision import (
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS,
    MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY,
)

MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERIFIER_SCHEMA_VERSION = "msn_manual_evidence_review_decision_verifier_v1"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_READY = "EVIDENCE_REVIEW_DECISION_READY"
MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_NEEDS_REVIEW = "EVIDENCE_REVIEW_DECISION_NEEDS_REVIEW"
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualEvidenceReviewDecisionVerificationReport:
    schema_version: str
    verdict: str
    issue_count: int
    issues: list[str]
    decision_id: str = ""
    queue_item_id: str = ""
    review_decision: str = ""
    approved_for_total_export: bool = False


def _contains_path_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_path_like(child) for child in value)
    return False


def verify_msn_manual_evidence_review_decision(decision: Mapping[str, Any]) -> MSNManualEvidenceReviewDecisionVerificationReport:
    issues: list[str] = []
    if decision.get("schema_version") != MSN_MANUAL_EVIDENCE_REVIEW_DECISION_SCHEMA_VERSION:
        issues.append("schema_version mismatch")
    for key in ("decision_id", "queue_item_id", "source_url", "named_site", "named_action", "reviewer_id", "review_decision", "decision_hash"):
        if not decision.get(key):
            issues.append(f"missing {key}")
    review_decision = str(decision.get("review_decision", ""))
    if review_decision not in MSN_MANUAL_EVIDENCE_REVIEW_DECISIONS:
        issues.append("unsupported review_decision")
    if decision.get("decision_status") != MSN_MANUAL_EVIDENCE_REVIEW_DECISION_STATUS_READY:
        issues.append("decision_status is not ready")
    if int(decision.get("issue_count", 0) or 0) != 0:
        issues.append("decision issue_count is non-zero")
    assets = decision.get("assets")
    if not isinstance(assets, list) or not assets:
        issues.append("missing assets")
    actions = decision.get("review_actions")
    if not isinstance(actions, list) or not actions:
        issues.append("missing review_actions")
    if review_decision == MSN_MANUAL_EVIDENCE_REVIEW_DECISION_APPROVED and decision.get("approved_for_total_export") is not True:
        issues.append("approved decision is not approved_for_total_export")
    flags = decision.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for flag in ("metadata_only_decision", "explicit_review_package_only", "no_live_http", "no_browser_automation", "no_full_local_paths", "no_credential_reads"):
            if flags.get(flag) is not True:
                issues.append(f"safety flag not true: {flag}")
    if _contains_path_like(decision):
        issues.append("decision contains full local path-like text")
    verdict = MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_READY if not issues else MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERDICT_NEEDS_REVIEW
    return MSNManualEvidenceReviewDecisionVerificationReport(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_DECISION_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issue_count=len(issues),
        issues=issues,
        decision_id=str(decision.get("decision_id", "")),
        queue_item_id=str(decision.get("queue_item_id", "")),
        review_decision=review_decision,
        approved_for_total_export=bool(decision.get("approved_for_total_export", False)),
    )


def msn_manual_evidence_review_decision_verification_report_to_json(report: MSNManualEvidenceReviewDecisionVerificationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
