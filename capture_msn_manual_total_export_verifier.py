from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


MSN_MANUAL_TOTAL_EXPORT_VERIFIER_SCHEMA_VERSION = "msn_manual_total_export_verifier_v1"
_READY_VERDICT = "MSN_MANUAL_TOTAL_EXPORT_READY_FOR_REVIEW"
_NEEDS_REVIEW_VERDICT = "MSN_MANUAL_TOTAL_EXPORT_NEEDS_REVIEW"
_FULL_PATH_RE = re.compile(r"(?:^|[\s'\"])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SECRET_RE = re.compile(r"(?:api[_-]?key|secret|token|password|credential|bearer|authorization)", re.I)


@dataclass(frozen=True)
class MSNManualTotalExportVerificationIssue:
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MSNManualTotalExportVerificationReport:
    schema_version: str
    verdict: str
    issues: tuple[MSNManualTotalExportVerificationIssue, ...]
    package_id: str
    file_count: int
    comment_count: int
    total_export_manifest_present: bool
    article_text_present: bool
    bundle_json_present: bool
    full_local_path_serialized: bool = False
    secret_like_value_serialized: bool = False
    ready_for_total_export_review: bool = True
    review_required: bool = True
    completed_capture_claimed: bool = False
    verified_capture_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _contains_path_or_secret(value: Any) -> tuple[bool, bool]:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return bool(_FULL_PATH_RE.search(text)), bool(_SECRET_RE.search(text))


def verify_msn_manual_total_export_cli_result(payload: Mapping[str, Any]) -> MSNManualTotalExportVerificationReport:
    issues: list[MSNManualTotalExportVerificationIssue] = []
    packet = payload.get("packet") if isinstance(payload.get("packet"), Mapping) else {}
    store_result = payload.get("store_result") if isinstance(payload.get("store_result"), Mapping) else {}
    files = store_result.get("files") if isinstance(store_result.get("files"), list) else []
    file_names = {str(file.get("file_name", "")) for file in files if isinstance(file, Mapping)}

    manifest_present = any(name.endswith("_manifest.json") and name.startswith("metadata/") for name in file_names)
    article_present = any(name.endswith("_article_text.txt") and name.startswith("page_capture/") for name in file_names)
    bundle_present = any(name.endswith("_msn_manual_capture_bundle.json") and name.startswith("metadata/") for name in file_names)
    if not manifest_present:
        issues.append(MSNManualTotalExportVerificationIssue("missing_manifest", "Total Export manifest file is missing."))
    if not article_present:
        issues.append(MSNManualTotalExportVerificationIssue("missing_article_text", "Extracted article text file is missing."))
    if not bundle_present:
        issues.append(MSNManualTotalExportVerificationIssue("missing_bundle", "MSN manual capture bundle JSON file is missing."))
    if packet.get("total_export_manifest_implemented") is not True:
        issues.append(MSNManualTotalExportVerificationIssue("manifest_not_implemented", "Packet does not mark Total Export manifest implementation as present."))
    if packet.get("ready_for_total_export_review") is not True:
        issues.append(MSNManualTotalExportVerificationIssue("not_review_ready", "Packet is not ready for Total Export review."))
    if packet.get("completed_capture_claimed") is True or packet.get("verified_capture_claimed") is True:
        issues.append(MSNManualTotalExportVerificationIssue("unsafe_capture_claim", "Packet must not claim completed or verified capture."))

    has_path, has_secret = _contains_path_or_secret(payload)
    if has_path:
        issues.append(MSNManualTotalExportVerificationIssue("full_path_serialized", "CLI result serialized a full local path."))
    if has_secret:
        issues.append(MSNManualTotalExportVerificationIssue("secret_like_value", "CLI result serialized a secret-like value."))

    verdict = _READY_VERDICT if not issues else _NEEDS_REVIEW_VERDICT
    return MSNManualTotalExportVerificationReport(
        schema_version=MSN_MANUAL_TOTAL_EXPORT_VERIFIER_SCHEMA_VERSION,
        verdict=verdict,
        issues=tuple(issues),
        package_id=str(packet.get("package_id", "")),
        file_count=len(files),
        comment_count=int(packet.get("comment_count") or 0),
        total_export_manifest_present=manifest_present,
        article_text_present=article_present,
        bundle_json_present=bundle_present,
        full_local_path_serialized=has_path,
        secret_like_value_serialized=has_secret,
        ready_for_total_export_review=not issues,
    )


def msn_manual_total_export_verification_report_to_json(report: MSNManualTotalExportVerificationReport) -> str:
    return json.dumps(report.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
