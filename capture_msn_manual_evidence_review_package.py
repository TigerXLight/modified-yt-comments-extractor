from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION = "msn_manual_evidence_review_package_v1"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING = "REVIEW_PENDING"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_READY = "REVIEW_READY"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_NEEDS_OPERATOR_REVIEW = "NEEDS_OPERATOR_REVIEW"
MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_ALLOWED_STATUSES = {
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING,
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_READY,
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_NEEDS_OPERATOR_REVIEW,
}

_REQUIRED_REVIEW_ACTIONS = (
    "review_source_url_and_site",
    "review_article_extraction",
    "review_comments_extraction",
    "review_total_export_manifest",
    "review_asset_hashes",
    "approve_or_reject_queue_item",
)

_PATH_RE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:\\|(?<![A-Za-z])[A-Za-z]:/|\\\\|/(?:home|mnt|Users|Volumes|tmp|var)/)")
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class MSNManualEvidenceReviewAsset:
    role: str
    filename: str
    sha256: str = ""
    byte_count: int = 0


@dataclass(frozen=True)
class MSNManualEvidenceReviewAction:
    action_id: str
    label: str
    required: bool = True
    completed: bool = False


@dataclass(frozen=True)
class MSNManualEvidenceReviewPackage:
    schema_version: str
    queue_item_id: str
    source_url: str
    named_site: str
    named_action: str
    article_title: str
    review_status: str
    reviewer_id: str
    source_issue_count: int
    assets: list[MSNManualEvidenceReviewAsset] = field(default_factory=list)
    review_actions: list[MSNManualEvidenceReviewAction] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    package_hash: str = ""


class MSNManualEvidenceReviewPackageError(ValueError):
    pass


def _ensure_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MSNManualEvidenceReviewPackageError(f"{label} must be a JSON object")
    return value


def _safe_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_filename(value: Any, *, fallback: str) -> str:
    raw = _safe_text(value, default=fallback).replace("\\", "/").split("/")[-1]
    raw = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return raw or fallback


def _safe_id(value: Any) -> str:
    raw = _safe_text(value, default="msn_manual_queue_item")
    safe = _SAFE_NAME_RE.sub("_", raw).strip("._")
    return safe or "msn_manual_queue_item"


def _sha256_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str], default: str = "") -> str:
    for key in keys:
        if key in mapping and _safe_text(mapping[key]):
            return _safe_text(mapping[key])
    return default


def _nested_mapping(mapping: Mapping[str, Any], keys: Sequence[str]) -> Mapping[str, Any]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _asset_from_mapping(asset: Mapping[str, Any], *, fallback_role: str, index: int) -> MSNManualEvidenceReviewAsset:
    role = _safe_id(_first_present(asset, ("role", "asset_role", "type", "kind"), fallback_role))
    filename = _safe_filename(
        _first_present(asset, ("filename", "safe_filename", "name", "relative_path", "path"), f"asset_{index}.json"),
        fallback=f"asset_{index}.json",
    )
    sha256 = _safe_text(_first_present(asset, ("sha256", "hash", "content_sha256", "digest")))
    byte_raw = asset.get("byte_count", asset.get("bytes", asset.get("size", 0)))
    try:
        byte_count = int(byte_raw)
    except (TypeError, ValueError):
        byte_count = 0
    return MSNManualEvidenceReviewAsset(role=role, filename=filename, sha256=sha256, byte_count=max(byte_count, 0))


def _collect_assets_from(value: Any, *, fallback_role: str, assets: list[MSNManualEvidenceReviewAsset]) -> None:
    if isinstance(value, Mapping):
        if any(key in value for key in ("filename", "safe_filename", "name", "relative_path", "path")):
            assets.append(_asset_from_mapping(value, fallback_role=fallback_role, index=len(assets) + 1))
            return
        for key, child in value.items():
            if key in {"asset", "assets", "files", "outputs", "package_files", "safe_artifacts", "manifest", "bundle"} or isinstance(child, (Mapping, list, tuple)):
                _collect_assets_from(child, fallback_role=_safe_id(key), assets=assets)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _collect_assets_from(child, fallback_role=fallback_role, assets=assets)


def _deduplicate_assets(assets: Sequence[MSNManualEvidenceReviewAsset]) -> list[MSNManualEvidenceReviewAsset]:
    seen: set[tuple[str, str, str]] = set()
    result: list[MSNManualEvidenceReviewAsset] = []
    for asset in assets:
        key = (asset.role, asset.filename, asset.sha256)
        if key not in seen:
            seen.add(key)
            result.append(asset)
    return result


def _issue_count(report: Mapping[str, Any]) -> int:
    for key in ("issue_count", "source_issue_count", "issues_count", "warning_count"):
        if key in report:
            try:
                return max(int(report[key]), 0)
            except (TypeError, ValueError):
                return 1
    issues = report.get("issues")
    if isinstance(issues, Sequence) and not isinstance(issues, (str, bytes, bytearray)):
        return len(issues)
    return 0


def _contains_path_like_text(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PATH_RE.search(value))
    if isinstance(value, Mapping):
        return any(_contains_path_like_text(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_path_like_text(child) for child in value)
    return False


def _make_review_actions() -> list[MSNManualEvidenceReviewAction]:
    labels = {
        "review_source_url_and_site": "Confirm source URL, named site, and named action",
        "review_article_extraction": "Review extracted MSN article title/body text",
        "review_comments_extraction": "Review extracted MSN comments payload",
        "review_total_export_manifest": "Review Total Export manifest and package roles",
        "review_asset_hashes": "Review safe asset filenames, hashes, and byte counts",
        "approve_or_reject_queue_item": "Approve or reject the queued evidence item",
    }
    return [MSNManualEvidenceReviewAction(action_id=action, label=labels[action]) for action in _REQUIRED_REVIEW_ACTIONS]


def build_msn_manual_evidence_review_package(
    queue_report: Mapping[str, Any],
    *,
    reviewer_id: str = "operator",
    review_status: str = MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING,
    notes: Sequence[str] | None = None,
) -> MSNManualEvidenceReviewPackage:
    report = _ensure_mapping(queue_report, label="queue_report")
    status = _safe_text(review_status, default=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING)
    if status not in MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_ALLOWED_STATUSES:
        raise MSNManualEvidenceReviewPackageError(f"unsupported review_status: {status}")

    queue_item = _nested_mapping(report, ("queue_item", "evidence_queue_item", "item", "payload")) or report
    package = _nested_mapping(queue_item, ("total_export_package", "total_export", "package", "manifest"))

    queue_item_id = _safe_id(_first_present(queue_item, ("queue_item_id", "item_id", "evidence_item_id", "capture_id"), "msn_manual_queue_item"))
    source_url = _first_present(queue_item, ("source_url", "url"), _first_present(package, ("source_url", "url"), ""))
    named_site = _first_present(queue_item, ("named_site", "site"), _first_present(package, ("named_site", "site"), "msn"))
    named_action = _first_present(queue_item, ("named_action", "action"), _first_present(package, ("named_action", "action"), "msn_manual_capture"))
    article_title = _first_present(queue_item, ("article_title", "title"), _first_present(package, ("article_title", "title"), ""))

    if not source_url:
        raise MSNManualEvidenceReviewPackageError("queue_report must include source_url/url")
    if not article_title:
        article_title = "MSN manual capture review item"

    assets: list[MSNManualEvidenceReviewAsset] = []
    for key in ("assets", "asset_index", "safe_artifacts", "package_files", "files", "outputs", "total_export_package"):
        if key in queue_item:
            _collect_assets_from(queue_item[key], fallback_role=key, assets=assets)
    if package:
        _collect_assets_from(package, fallback_role="total_export_package", assets=assets)
    assets = _deduplicate_assets(assets)

    asset_roles = {asset.role for asset in assets}
    required_roles_present = bool(asset_roles) and any("manifest" in role for role in asset_roles) and any(
        "article" in role or "comments" in role or "bundle" in role for role in asset_roles
    )
    safe_flags = {
        "metadata_only_review_package": True,
        "explicit_operator_artifacts_only": True,
        "no_live_http": True,
        "no_browser_automation": True,
        "no_archive_submission": True,
        "no_media_download": True,
        "no_credential_access": True,
        "no_full_local_paths": not _contains_path_like_text(asdict(MSNManualEvidenceReviewPackage(
            schema_version=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION,
            queue_item_id=queue_item_id,
            source_url=source_url,
            named_site=named_site,
            named_action=named_action,
            article_title=article_title,
            review_status=status,
            reviewer_id=_safe_id(reviewer_id),
            source_issue_count=_issue_count(report),
            assets=assets,
            review_actions=_make_review_actions(),
            notes=list(notes or ()),
            safety_flags={},
        ))),
        "required_asset_roles_present": required_roles_present,
    }

    package_obj = MSNManualEvidenceReviewPackage(
        schema_version=MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION,
        queue_item_id=queue_item_id,
        source_url=source_url,
        named_site=named_site,
        named_action=named_action,
        article_title=article_title,
        review_status=status,
        reviewer_id=_safe_id(reviewer_id),
        source_issue_count=_issue_count(report),
        assets=assets,
        review_actions=_make_review_actions(),
        notes=[_safe_text(note) for note in notes or () if _safe_text(note)],
        safety_flags=safe_flags,
    )
    data = asdict(package_obj)
    data.pop("package_hash", None)
    return MSNManualEvidenceReviewPackage(
        schema_version=package_obj.schema_version,
        queue_item_id=package_obj.queue_item_id,
        source_url=package_obj.source_url,
        named_site=package_obj.named_site,
        named_action=package_obj.named_action,
        article_title=package_obj.article_title,
        review_status=package_obj.review_status,
        reviewer_id=package_obj.reviewer_id,
        source_issue_count=package_obj.source_issue_count,
        assets=package_obj.assets,
        review_actions=package_obj.review_actions,
        notes=package_obj.notes,
        safety_flags=package_obj.safety_flags,
        package_hash=_sha256_json(data),
    )


def msn_manual_evidence_review_package_to_json(package: MSNManualEvidenceReviewPackage) -> str:
    return json.dumps(asdict(package), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
