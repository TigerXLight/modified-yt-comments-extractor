from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_msn_adapter_manifest import (
    MSN_SOURCE_ADAPTER_NAME,
    MSN_SOURCE_ADAPTER_SCHEMA_VERSION,
    MsnSourceAdapterBundle,
)


MSN_ADAPTER_READINESS_SCHEMA_VERSION = "msn_source_adapter_readiness_v1"

READINESS_CONFIDENT = "CONFIDENT"
READINESS_PARTIAL = "PARTIAL"
READINESS_MISSING = "MISSING"
READINESS_NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
READINESS_STRUCTURALLY_COMPLETE = "STRUCTURALLY_COMPLETE_MANUAL_REVIEW_REQUIRED"
READINESS_NOT_COMPLETE = "NOT_COMPLETE"


@dataclass(frozen=True)
class MsnAdapterReadinessFinding:
    area: str
    status: str
    detail: str
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnAdapterReadinessReport:
    schema_version: str = MSN_ADAPTER_READINESS_SCHEMA_VERSION
    adapter_name: str = MSN_SOURCE_ADAPTER_NAME
    manifest_schema_version: str = MSN_SOURCE_ADAPTER_SCHEMA_VERSION
    overall_status: str = READINESS_NOT_COMPLETE
    article_status: str = READINESS_MISSING
    comments_status: str = READINESS_MISSING
    offline_viewer_status: str = READINESS_MISSING
    media_status: str = READINESS_MISSING
    provenance_status: str = READINESS_MISSING
    findings: tuple[MsnAdapterReadinessFinding, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    manual_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _as_mapping(bundle: MsnSourceAdapterBundle | Mapping[str, Any]) -> Mapping[str, Any]:
    if hasattr(bundle, "to_dict") and callable(bundle.to_dict):
        return bundle.to_dict()
    return bundle


def _manifest(bundle_data: Mapping[str, Any]) -> Mapping[str, Any]:
    manifest = bundle_data.get("manifest")
    return manifest if isinstance(manifest, Mapping) else {}


def _asset_descriptions(manifest: Mapping[str, Any]) -> list[str]:
    output: list[str] = []
    for asset in manifest.get("assets") or []:
        if isinstance(asset, Mapping):
            output.append(str(asset.get("description") or ""))
    return output


def _provenance_records(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [record for record in (manifest.get("provenance_records") or []) if isinstance(record, Mapping)]


def _claim_notes(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [note for note in (manifest.get("claim_notes") or []) if isinstance(note, Mapping)]


def _media_notes(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [note for note in (manifest.get("media_source_chain_notes") or []) if isinstance(note, Mapping)]


def _count_comment_records(provenance: Sequence[Mapping[str, Any]]) -> int:
    return sum(1 for record in provenance if record.get("capture_purpose") == "MSN user comment/profile extraction")


def _count_media_records(bundle_data: Mapping[str, Any]) -> int:
    return sum(1 for record in (bundle_data.get("media_records") or []) if isinstance(record, Mapping))


def _count_local_media(bundle_data: Mapping[str, Any]) -> int:
    return sum(
        1
        for record in (bundle_data.get("media_records") or [])
        if isinstance(record, Mapping) and str(record.get("local_media_path") or "")
    )


def _status_for_article(article: Mapping[str, Any]) -> tuple[str, MsnAdapterReadinessFinding]:
    missing = [
        label
        for label, value in (
            ("title", article.get("title")),
            ("publisher_name", article.get("publisher_name")),
            ("article_text/body_lines", article.get("article_text") or article.get("article_body_lines")),
            ("source_role", article.get("source_role")),
            ("primary_source_status", article.get("primary_source_status")),
        )
        if not value
    ]
    if missing:
        return (
            READINESS_PARTIAL,
            MsnAdapterReadinessFinding(
                area="article_extraction",
                status=READINESS_PARTIAL,
                detail="Article extraction exists but is missing: " + ", ".join(missing),
                blocking=True,
            ),
        )
    return (
        READINESS_CONFIDENT,
        MsnAdapterReadinessFinding(
            area="article_extraction",
            status=READINESS_CONFIDENT,
            detail="Article title, publisher/source, visible body text, source role, and primary-source status are present.",
        ),
    )


def _status_for_comments(manifest: Mapping[str, Any], provenance: Sequence[Mapping[str, Any]]) -> tuple[str, MsnAdapterReadinessFinding]:
    options = set(str(item) for item in (manifest.get("capture_options") or []))
    count = _count_comment_records(provenance)
    if "msn_comments_profile_extraction" not in options:
        return (
            READINESS_MISSING,
            MsnAdapterReadinessFinding(
                area="comments_profile_extraction",
                status=READINESS_MISSING,
                detail="Comments/profile export is not attached to this MSN source adapter bundle.",
                blocking=True,
            ),
        )
    if count <= 0:
        return (
            READINESS_PARTIAL,
            MsnAdapterReadinessFinding(
                area="comments_profile_extraction",
                status=READINESS_PARTIAL,
                detail="Comments/profile option is present but no comment provenance records were found.",
                blocking=True,
            ),
        )
    return (
        READINESS_CONFIDENT,
        MsnAdapterReadinessFinding(
            area="comments_profile_extraction",
            status=READINESS_CONFIDENT,
            detail=f"Comments/profile extraction is attached with {count} comment/reply provenance record(s).",
        ),
    )


def _status_for_offline_viewer(manifest: Mapping[str, Any]) -> tuple[str, MsnAdapterReadinessFinding]:
    descriptions = _asset_descriptions(manifest)
    has_html = any("best viewable rendered HTML" in description for description in descriptions)
    has_warc = any("WARC.GZ" in description for description in descriptions)
    has_viewer = any("offline viewer" in description.lower() or "viewer launcher" in description.lower() for description in descriptions)
    has_strict_wacz = any("strict WACZ" in description for description in descriptions)
    if has_html and has_warc and has_viewer:
        extra = " Strict WACZ is present and should remain labelled experimental." if has_strict_wacz else " Strict WACZ is not present in this bundle."
        return (
            READINESS_CONFIDENT,
            MsnAdapterReadinessFinding(
                area="offline_webpage_viewer",
                status=READINESS_CONFIDENT,
                detail="Rendered HTML, partial ReplayWeb WARC.GZ, and local viewer artifacts are linked." + extra,
            ),
        )
    missing = []
    if not has_html:
        missing.append("rendered-page.html")
    if not has_warc:
        missing.append("rendered-page.warc.gz")
    if not has_viewer:
        missing.append("local viewer")
    return (
        READINESS_PARTIAL,
        MsnAdapterReadinessFinding(
            area="offline_webpage_viewer",
            status=READINESS_PARTIAL,
            detail="Offline webpage/viewer artifacts are incomplete: " + ", ".join(missing),
            blocking=True,
        ),
    )


def _status_for_media(bundle_data: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[str, MsnAdapterReadinessFinding]:
    media_count = _count_media_records(bundle_data)
    local_count = _count_local_media(bundle_data)
    chain_count = len(_media_notes(manifest))
    if media_count <= 0:
        return (
            READINESS_MISSING,
            MsnAdapterReadinessFinding(
                area="media_discovery_download",
                status=READINESS_MISSING,
                detail="No image/video/media candidates are recorded for this MSN source adapter bundle.",
                blocking=True,
            ),
        )
    if local_count > 0:
        return (
            READINESS_CONFIDENT,
            MsnAdapterReadinessFinding(
                area="media_discovery_download",
                status=READINESS_CONFIDENT,
                detail=f"{media_count} media candidate(s) recorded; {local_count} local media asset(s) captured with path/hash where available.",
            ),
        )
    return (
        READINESS_PARTIAL,
        MsnAdapterReadinessFinding(
            area="media_discovery_download",
            status=READINESS_PARTIAL,
            detail=f"{media_count} media candidate(s) and {chain_count} source-chain note(s) recorded, but no local media file is attached yet.",
        ),
    )


def _status_for_provenance(bundle_data: Mapping[str, Any], manifest: Mapping[str, Any], provenance: Sequence[Mapping[str, Any]]) -> tuple[str, MsnAdapterReadinessFinding]:
    article = bundle_data.get("article") or {}
    claim_notes = _claim_notes(manifest)
    has_article_secondary = article.get("source_role") == "SECONDARY_OUTSIDE_PERSPECTIVE"
    has_primary_status = bool(article.get("primary_source_status"))
    has_claim_note = any(note.get("claim_source_role") for note in claim_notes)
    has_media_chain = bool(_media_notes(manifest))
    has_comment_scope = any(
        record.get("source_role") == "PRIMARY_ORIGINAL_AUTHORED"
        and "commenter" in str(record.get("verification_notes") or "").lower()
        for record in provenance
    )
    if has_article_secondary and has_primary_status and has_claim_note and has_media_chain and has_comment_scope:
        return (
            READINESS_CONFIDENT,
            MsnAdapterReadinessFinding(
                area="source_role_provenance",
                status=READINESS_CONFIDENT,
                detail="Article, comment, and media source-role/provenance records preserve primary/secondary/source-chain limits.",
            ),
        )
    missing = []
    if not has_article_secondary:
        missing.append("article secondary/outside perspective role")
    if not has_primary_status:
        missing.append("article primary-source status")
    if not has_claim_note:
        missing.append("claim-level source-role note")
    if not has_media_chain:
        missing.append("media source-chain note")
    if not has_comment_scope:
        missing.append("comment-authorship scope note")
    return (
        READINESS_PARTIAL,
        MsnAdapterReadinessFinding(
            area="source_role_provenance",
            status=READINESS_PARTIAL,
            detail="Source-role/provenance coverage is incomplete: " + ", ".join(missing),
            blocking=True,
        ),
    )


def evaluate_msn_source_adapter_readiness(bundle: MsnSourceAdapterBundle | Mapping[str, Any]) -> MsnAdapterReadinessReport:
    data = _as_mapping(bundle)
    manifest = _manifest(data)
    provenance = _provenance_records(manifest)
    article = data.get("article") if isinstance(data.get("article"), Mapping) else {}

    article_status, article_finding = _status_for_article(article)
    comments_status, comments_finding = _status_for_comments(manifest, provenance)
    offline_status, offline_finding = _status_for_offline_viewer(manifest)
    media_status, media_finding = _status_for_media(data, manifest)
    provenance_status, provenance_finding = _status_for_provenance(data, manifest, provenance)
    findings = (article_finding, comments_finding, offline_finding, media_finding, provenance_finding)
    blocking = any(finding.blocking for finding in findings)
    if not blocking and media_status in {READINESS_CONFIDENT, READINESS_PARTIAL}:
        overall = READINESS_STRUCTURALLY_COMPLETE
    else:
        overall = READINESS_NOT_COMPLETE
    counts = {
        "provenance_records": len(provenance),
        "comment_provenance_records": _count_comment_records(provenance),
        "media_records": _count_media_records(data),
        "local_media_assets": _count_local_media(data),
        "media_source_chain_notes": len(_media_notes(manifest)),
        "claim_notes": len(_claim_notes(manifest)),
        "assets": len(manifest.get("assets") or []),
    }
    limitations = (
        "This readiness report is a structural/offline validation gate; it does not perform live MSN capture.",
        "WARC.GZ replay remains partial unless manually reviewed in ReplayWeb.page.",
        "Strict WACZ must not be claimed successful unless a manual/compatible validation proves it.",
        "Media candidates without local paths/hashes are discovered/registered only, not downloaded evidence files.",
        "MSN or a reposting publisher such as The Independent must not be treated as the original media/source without a located primary source.",
    )
    return MsnAdapterReadinessReport(
        overall_status=overall,
        article_status=article_status,
        comments_status=comments_status,
        offline_viewer_status=offline_status,
        media_status=media_status,
        provenance_status=provenance_status,
        findings=findings,
        counts=counts,
        limitations=limitations,
        manual_review_required=True,
    )


def write_msn_source_adapter_readiness_report(report: MsnAdapterReadinessReport, output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)
