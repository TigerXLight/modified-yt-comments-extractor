from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Mapping

from capture_msn_manual_evidence_review_package import MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION

MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERIFIER_SCHEMA_VERSION = "msn_manual_evidence_review_package_verifier_v1"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_READY = "EVIDENCE_REVIEW_PACKAGE_READY"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_NEEDS_REVIEW = "EVIDENCE_REVIEW_PACKAGE_NEEDS_REVIEW"
_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")


@dataclass(frozen=True)
class MSNManualEvidenceReviewPackageVerificationReport:
    schema_version: str
    verdict: str
    issue_count: int
    issues: list[str]
    queue_item_id: str = ""
    asset_count: int = 0
    review_action_count: int = 0


def _contains_path_like(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_path_like(child) for child in value)
    return False


def verify_msn_manual_evidence_review_package(package: Mapping[str, Any]) -> MSNManualEvidenceReviewPackageVerificationReport:
    issues: list[str] = []
    if package.get("schema_version") != MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION:
        issues.append("schema_version mismatch")
    for key in ("queue_item_id", "source_url", "named_site", "named_action", "article_title", "review_status", "package_hash"):
        if not package.get(key):
            issues.append(f"missing {key}")
    assets = package.get("assets")
    if not isinstance(assets, list) or not assets:
        issues.append("missing assets")
        assets = []
    actions = package.get("review_actions")
    if not isinstance(actions, list) or len(actions) < 6:
        issues.append("missing required review actions")
        actions = []
    flags = package.get("safety_flags")
    if not isinstance(flags, Mapping):
        issues.append("missing safety_flags")
    else:
        for key in ("metadata_only_review_package", "explicit_operator_artifacts_only", "no_live_http", "no_browser_automation", "no_full_local_paths"):
            if flags.get(key) is not True:
                issues.append(f"safety flag not true: {key}")
    if _contains_path_like(package):
        issues.append("package contains full local path-like text")
    verdict = MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_READY if not issues else MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_NEEDS_REVIEW
    return MSNManualEvidenceReviewPackageVerificationReport(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issue_count=len(issues),
        issues=issues,
        queue_item_id=str(package.get("queue_item_id", "")),
        asset_count=len(assets),
        review_action_count=len(actions),
    )


def msn_manual_evidence_review_package_verification_report_to_json(report: MSNManualEvidenceReviewPackageVerificationReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
