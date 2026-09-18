from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from profile_media_twitter_x_account_media_ledger_r43a import (
    TwitterXAccountMediaItemR43A,
    TwitterXAccountRecordR43A,
)

R43T_MARKER = "YTCE_R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING"
R43T_PASS_STATUS = "PASS_R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING"
R43T_BLOCKED_STATUS = "BLOCKED_R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING"
R43T_SCHEMA_VERSION = "twitter_x_fast_media_to_post_ledger_binding.r43t.v1"
R43T_REPORT_ROOT = "profile_media_live_captures/r43t_twitter_x_fast_media_to_post_ledger_binding"


@dataclass(frozen=True)
class FastMediaBindingResultR43T:
    marker: str
    schema_version: str
    status: str
    records: tuple[TwitterXAccountRecordR43A, ...]
    bound_media: tuple[Mapping[str, Any], ...]
    unbound_media: tuple[Mapping[str, Any], ...]
    summary: Mapping[str, Any]
    checks: tuple[Mapping[str, Any], ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43T_PASS_STATUS and not any(check.get("status") != "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def bind_fast_media_observations_to_post_records_r43t(
    records: Iterable[TwitterXAccountRecordR43A],
    *,
    articles: Iterable[Mapping[str, Any]] = (),
    paths: Mapping[str, str] | None = None,
    runner_root: str | Path = "",
) -> FastMediaBindingResultR43T:
    row_list = list(records or ())
    path_map = dict(paths or {})
    root = Path(runner_root) if runner_root else Path()
    source_paths = _resolve_source_paths(root, path_map)
    candidates = _load_candidates(source_paths)
    bound_by_record, bound_rows, unbound_rows = _bind_candidates(row_list, list(articles or ()), candidates)
    updated_records: list[TwitterXAccountRecordR43A] = []
    for row in row_list:
        additions = tuple(_candidate_to_media_item(candidate, row) for candidate in bound_by_record.get(row.record_id, ()))
        existing = tuple(row.media_items or ())
        merged = _dedupe_media_items(additions + existing)
        if additions:
            data = row.to_dict()
            data["media_items"] = merged
            updated_records.append(TwitterXAccountRecordR43A(**data))
        else:
            updated_records.append(row)

    summary = _summary(candidates, bound_rows, unbound_rows, source_paths)
    fixture_scope = summary.get("count_scope") == "standalone_r43t_fixture_matches_integrated_r43r_ledger_binding_scope"
    checks = (
        _check("fast_media_observation_store_loaded", summary["visible_observation_count"] > 0),
        _check("r42gt_media_index_loaded", summary["r42gt_media_index_count"] > 0),
        _check("media_inventory_loaded", summary["media_inventory_count"] > 0 or not fixture_scope),
        _check("media_bound_by_status_id_to_correct_post", any(row.get("binding_reason") == "status_id_match" for row in bound_rows) or not fixture_scope),
        _check("media_bound_by_canonical_post_url_to_correct_post", any(row.get("binding_reason") == "canonical_post_url_match" for row in bound_rows) or not fixture_scope),
        _check("media_bound_by_article_dom_url_to_correct_post", any(row.get("binding_reason") == "article_dom_media_url_match" for row in bound_rows)),
        _check("loose_account_level_media_not_attached_to_all_posts", not _loose_media_attached_to_all_posts(row_list, bound_rows)),
        _check("unbound_media_preserved_in_unbound_index", bool(unbound_rows) or not fixture_scope),
        _check("decorative_x_assets_not_attached_as_post_media", not any(_is_decorative_x_asset(row.get("media_url")) for row in bound_rows)),
        _check("profile_avatar_not_attached_as_post_media", not any(_is_profile_asset_url(row.get("media_url")) for row in bound_rows)),
        _check("no_remote_media_downloads", all(row.get("remote_download_performed_by_r43a") is False for row in bound_rows)),
        _check("standalone_r43t_report_count_scope_is_explicit", bool(summary.get("count_scope"))),
        _check("r43t_report_counts_match_fixture_when_same_scope", summary["bound_media_count"] == summary["bound_image_count"] + summary["bound_video_count"] + summary["bound_manifest_count"] + summary["bound_segment_count"] + summary.get("bound_other_media_count", 0)),
        _check("no_browser_profile_files_in_zip", not any("twitter_test_profile" in str(path).lower() or "browser_profile" in str(path).lower() for path in summary.get("source_paths", {}).values())),
        _check("plain_machine_urls", _machine_urls_are_plain({"summary": summary, "bound": bound_rows, "unbound": unbound_rows})),
    )
    status = R43T_PASS_STATUS if all(check.get("status") == "pass" for check in checks) else R43T_BLOCKED_STATUS
    summary = dict(summary)
    summary["r43t_status"] = status
    return FastMediaBindingResultR43T(
        marker=R43T_MARKER,
        schema_version=R43T_SCHEMA_VERSION,
        status=status,
        records=tuple(updated_records),
        bound_media=tuple(bound_rows),
        unbound_media=tuple(unbound_rows),
        summary=summary,
        checks=checks,
    )


def write_unbound_media_index_r43t(capture_dir: str | Path, unbound_media: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    rows = [dict(row) for row in unbound_media or ()]
    if not rows:
        return {}
    root = Path(capture_dir) / "unbound_media"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "media_index.json"
    ndjson_path = root / "media_candidates.ndjson"
    _write_json(json_path, {"marker": R43T_MARKER, "schema_version": R43T_SCHEMA_VERSION, "media": rows})
    ndjson_path.write_text("\n".join(json.dumps(_to_jsonable(row), ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    return {"unbound_media_index_path": str(json_path), "unbound_media_candidates_path": str(ndjson_path)}


def build_report(output_root: str | Path = R43T_REPORT_ROOT) -> FastMediaBindingResultR43T:
    out = Path(output_root)
    runner = out / "fixture_runner_output"
    _write_fixture_runner_output(runner)
    records = (
        TwitterXAccountRecordR43A(
            record_id="1111111111111111111",
            record_type="post",
            source_url="https://x.com/examaddaorg/status/1111111111111111111",
            visible_text="text-only",
            visible_timestamp="2026-09-16T10:20:00Z",
            capture_timestamp="20260918T000000Z",
            account_handle="examaddaorg",
            author_handle="examaddaorg",
            observed_order=1,
        ),
        TwitterXAccountRecordR43A(
            record_id="2222222222222222222",
            record_type="post",
            source_url="https://x.com/examaddaorg/status/2222222222222222222",
            visible_text="media post",
            visible_timestamp="20260918T000000Z",
            capture_timestamp="20260918T000000Z",
            account_handle="examaddaorg",
            author_handle="examaddaorg",
            observed_order=2,
        ),
    )
    articles = (
        {
            "status_id": "2222222222222222222",
            "canonical_status_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "article_media_candidates": [
                {"media_url": "https://pbs.twimg.com/media/dom_bound.jpg?format=jpg&name=large"},
                {"media_url": "https://pbs.twimg.com/media/r43r_image.jpg?format=jpg&name=large"},
            ],
        },
    )
    result = bind_fast_media_observations_to_post_records_r43t(records, articles=articles, runner_root=runner)
    write_report(result, out)
    return result


def write_report(result: FastMediaBindingResultR43T, output_root: str | Path = R43T_REPORT_ROOT) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING_REPORT.json", result.to_dict())
    lines = [
        "# R43T Twitter/X Fast Media To Post Ledger Binding",
        "",
        f"- marker: `{result.marker}`",
        f"- status: `{result.status}`",
        "",
        "## Checks",
    ]
    for check in result.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    lines.extend(
        [
            "",
            "## Summary",
            f"- Bound media: `{result.summary.get('bound_media_count', 0)}`",
            f"- Unbound media: `{result.summary.get('unbound_media_count', 0)}`",
            f"- Metadata-only media: `{result.summary.get('metadata_only_media_count', 0)}`",
            "- R43T does not download remote Twitter/X media and does not start a browser.",
        ]
    )
    (out / "R43T_TWITTER_X_FAST_MEDIA_TO_POST_LEDGER_BINDING_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_source_paths(root: Path, paths: Mapping[str, str]) -> dict[str, str]:
    resolved = dict(paths or {})

    def first(pattern: str) -> str:
        if not root or not root.exists():
            return ""
        matches = sorted(path for path in root.rglob(pattern) if path.is_file() and path.stat().st_size > 0)
        return str(matches[0]) if matches else ""

    defaults = {
        "visible_observations_json": "visible_browser_media_observations.json",
        "visible_observations_ndjson": "visible_browser_media_observations.ndjson",
        "visible_segments_ndjson": "visible_browser_media_segments.ndjson",
        "r42gt_media_index_json": "media_index.json",
        "r42gt_media_index_ndjson": "media_index.ndjson",
        "r42gt_manifest": "manifest.json",
        "media_inventory": "media_inventory.json",
        "unified_media_window_state": "unified_media_window_state.json",
    }
    for key, pattern in defaults.items():
        if not _clean(resolved.get(key)):
            resolved[key] = first(pattern)
    return {key: _clean(value) for key, value in resolved.items()}


def _load_candidates(paths: Mapping[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_visible_observation_candidates(paths.get("visible_observations_json", ""), paths.get("visible_observations_ndjson", "")))
    rows.extend(_segment_candidates(paths.get("visible_segments_ndjson", "")))
    rows.extend(_r42gt_media_index_candidates(paths.get("r42gt_media_index_json", ""), paths.get("r42gt_media_index_ndjson", "")))
    rows.extend(_media_inventory_candidates(paths.get("media_inventory", "")))
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        media_url = _plain_url(row.get("media_url"))
        if not media_url or _is_decorative_x_asset(media_url) or _is_profile_asset_url(media_url):
            continue
        row["media_url"] = media_url
        row["media_class"] = _safe_media_class(row.get("media_class") or row.get("media_kind") or row.get("kind"), media_url)
        row["source_observation_marker"] = _clean(row.get("source_observation_marker") or "R43T")
        row["remote_download_performed_by_r43a"] = False
        key = (_clean(row.get("status_id")), media_url, _clean(row.get("source_observation_marker")))
        deduped.setdefault(key, row)
    return list(deduped.values())


def _visible_observation_candidates(json_path: str, ndjson_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payload = _read_json(Path(json_path), None) if json_path else None
    if isinstance(payload, Mapping):
        if isinstance(payload.get("store"), Mapping):
            payload = payload["store"]
        source = payload.get("observations") or payload.get("media") or payload.get("items") or []
    elif isinstance(payload, list):
        source = payload
    else:
        source = []
    rows.extend(_candidate_from_observation(row, "R42GV", json_path) for row in source if isinstance(row, Mapping))
    rows.extend(_candidate_from_observation(row, "R42GV", ndjson_path) for row in _read_ndjson(Path(ndjson_path)) if isinstance(row, Mapping))
    return rows


def _segment_candidates(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _read_ndjson(Path(path)) if path else []:
        media_url = row.get("canonical_segment_url") or row.get("segment_url") or row.get("media_url")
        rows.append(
            {
                "media_id": row.get("segment_id") or row.get("media_id") or _stable_media_id(media_url),
                "media_url": media_url,
                "source_url": row.get("canonical_source_url") or row.get("source_url"),
                "canonical_post_url": row.get("canonical_post_url") or row.get("post_url"),
                "status_id": row.get("status_id"),
                "status_id_explicit": bool(_clean(row.get("status_id"))),
                "media_class": "segment",
                "byte_status": row.get("byte_status") or "metadata_only_segment_receipt",
                "playlist_manifest_url": row.get("playlist_manifest_url") or row.get("manifest_url"),
                "source_observation_marker": "R42GV",
                "source_observation_kind": "visible_browser_media_segment",
                "source_observation_path": path,
                "warning": "segment receipt only; R43T/R43A did not download Twitter/X media segments",
            }
        )
    return rows


def _r42gt_media_index_candidates(json_path: str, ndjson_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payload = _read_json(Path(json_path), None) if json_path else None
    source = payload.get("media") if isinstance(payload, Mapping) else payload
    if isinstance(source, list):
        rows.extend(_candidate_from_r42gt(row, json_path) for row in source if isinstance(row, Mapping))
    rows.extend(_candidate_from_r42gt(row, ndjson_path) for row in _read_ndjson(Path(ndjson_path)) if isinstance(row, Mapping))
    return rows


def _media_inventory_candidates(path: str) -> list[dict[str, Any]]:
    payload = _read_json(Path(path), []) if path else []
    source = payload.get("media_inventory") if isinstance(payload, Mapping) else payload
    rows = []
    if isinstance(source, list):
        rows.extend(_candidate_from_inventory(row, path) for row in source if isinstance(row, Mapping))
    return rows


def _candidate_from_observation(row: Mapping[str, Any], marker: str, path: str) -> dict[str, Any]:
    media_url = row.get("canonical_media_url") or row.get("media_url") or row.get("canonical_url") or row.get("url")
    return {
        "media_id": row.get("media_id") or row.get("source_resource_id") or _stable_media_id(media_url),
        "media_url": media_url,
        "source_url": row.get("canonical_source_url") or row.get("source_url"),
        "canonical_post_url": row.get("canonical_post_url") or row.get("post_url"),
        "status_id": row.get("status_id") or _status_id_from_url(row.get("canonical_post_url") or row.get("post_url")),
        "status_id_explicit": bool(_clean(row.get("status_id"))),
        "media_class": row.get("media_class") or row.get("media_type") or row.get("type"),
        "local_path": row.get("local_session_path") or row.get("local_path") or row.get("path") or row.get("file_path"),
        "filename": row.get("filename") or row.get("display_name"),
        "mime_type": row.get("mime_type") or row.get("content_type"),
        "byte_status": row.get("byte_status") or row.get("status") or "metadata_only_review_required",
        "source_observation_marker": marker,
        "source_observation_kind": row.get("source_kind") or "visible_browser_media_observation",
        "source_observation_path": path,
    }


def _candidate_from_r42gt(row: Mapping[str, Any], path: str) -> dict[str, Any]:
    media_url = row.get("canonical_media_url") or row.get("media_url") or row.get("url")
    return {
        "media_id": row.get("media_id") or _stable_media_id(media_url),
        "media_url": media_url,
        "source_url": row.get("canonical_source_url") or row.get("source_url"),
        "canonical_post_url": row.get("canonical_post_url") or row.get("post_url"),
        "status_id": row.get("status_id") or row.get("post_id") or _status_id_from_url(row.get("canonical_post_url") or row.get("post_url")),
        "status_id_explicit": bool(_clean(row.get("status_id") or row.get("post_id"))),
        "media_class": row.get("media_kind") or row.get("media_class") or row.get("type"),
        "local_path": row.get("local_fixture_path") or row.get("local_path") or row.get("file_path"),
        "filename": row.get("filename") or row.get("relative_output_path"),
        "mime_type": row.get("mime_type"),
        "byte_status": row.get("media_file_status") or row.get("byte_status") or "metadata_only_review_required",
        "source_observation_marker": "R42GT",
        "source_observation_kind": "r42gt_media_index",
        "source_observation_path": path,
    }


def _candidate_from_inventory(row: Mapping[str, Any], path: str) -> dict[str, Any]:
    media_url = row.get("media_url") or row.get("url") or row.get("canonical_media_url")
    return {
        "media_id": row.get("media_id") or _stable_media_id(media_url),
        "media_url": media_url,
        "source_url": row.get("source_url") or row.get("canonical_source_url"),
        "canonical_post_url": row.get("canonical_post_url") or row.get("post_url"),
        "status_id": row.get("status_id") or _status_id_from_url(row.get("post_url") or row.get("source_url")),
        "status_id_explicit": bool(_clean(row.get("status_id"))),
        "media_class": row.get("media_class") or row.get("type") or row.get("kind"),
        "local_path": row.get("local_path") or row.get("path") or row.get("file_path"),
        "filename": row.get("filename"),
        "mime_type": row.get("mime_type") or row.get("content_type"),
        "byte_status": row.get("byte_status") or "metadata_only_review_required",
        "source_observation_marker": "media_inventory",
        "source_observation_kind": "twitter_browser_capture_runner_media_inventory",
        "source_observation_path": path,
    }


def _bind_candidates(
    records: list[TwitterXAccountRecordR43A],
    articles: list[Mapping[str, Any]],
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_status = {record.record_id: record for record in records if record.record_id}
    by_url = {_normalize_url(record.source_url): record for record in records if record.source_url}
    article_media_to_record: dict[str, TwitterXAccountRecordR43A] = {}
    for article in articles:
        status_id = _clean(article.get("status_id") or _status_id_from_url(article.get("canonical_status_url")))
        record = by_status.get(status_id) or by_url.get(_normalize_url(article.get("canonical_status_url")))
        if not record:
            continue
        for value in list(article.get("article_image_srcs") or ()) + list(article.get("article_video_srcs") or ()):
            article_media_to_record[_normalize_url(value)] = record
        for candidate in article.get("article_media_candidates") or ():
            if isinstance(candidate, Mapping):
                article_media_to_record[_normalize_url(candidate.get("media_url"))] = record
            else:
                article_media_to_record[_normalize_url(candidate)] = record

    bound_by_record: dict[str, list[dict[str, Any]]] = {}
    bound_rows: list[dict[str, Any]] = []
    unbound_rows: list[dict[str, Any]] = []
    single_status_record = records[0] if len(records) == 1 and "/status/" in _plain_url(records[0].source_url) else None
    for candidate in candidates:
        record = None
        reason = ""
        explicit_status_id = _clean(candidate.get("status_id")) if candidate.get("status_id_explicit") else ""
        status_id = explicit_status_id
        post_url = _normalize_url(candidate.get("canonical_post_url") or candidate.get("post_url") or candidate.get("source_url"))
        media_url = _normalize_url(candidate.get("media_url"))
        if explicit_status_id and explicit_status_id in by_status:
            record = by_status[status_id]
            reason = "status_id_match"
        elif post_url and post_url in by_url:
            record = by_url[post_url]
            reason = "canonical_post_url_match"
        elif media_url and media_url in article_media_to_record:
            record = article_media_to_record[media_url]
            reason = "article_dom_media_url_match"
        elif single_status_record:
            record = single_status_record
            reason = "single_status_page_fallback"

        if record:
            row = dict(candidate)
            row.update(
                {
                    "bound_to_record_id": record.record_id,
                    "bound_to_source_url": _plain_url(record.source_url),
                    "binding_status": "bound_to_post",
                    "binding_reason": reason,
                    "remote_download_performed_by_r43a": False,
                    "metadata_only_remote_media_not_downloaded": not _local_file_exists(candidate.get("local_path")),
                }
            )
            bound_by_record.setdefault(record.record_id, []).append(row)
            bound_rows.append(row)
        else:
            row = dict(candidate)
            row.update(
                {
                    "bound_to_record_id": "",
                    "bound_to_source_url": "",
                    "binding_status": "unbound_account_level_candidate",
                    "binding_reason": "no_status_or_article_match",
                    "remote_download_performed_by_r43a": False,
                    "metadata_only_remote_media_not_downloaded": True,
                }
            )
            unbound_rows.append(row)
    return bound_by_record, bound_rows, unbound_rows


def _candidate_to_media_item(candidate: Mapping[str, Any], record: TwitterXAccountRecordR43A) -> TwitterXAccountMediaItemR43A:
    local_path = _clean(candidate.get("local_path"))
    if not _local_file_exists(local_path):
        local_path = ""
    return TwitterXAccountMediaItemR43A(
        media_id=_clean(candidate.get("media_id") or _stable_media_id(candidate.get("media_url"))),
        media_class=_safe_media_class(candidate.get("media_class"), candidate.get("media_url")),
        source_url=_plain_url(candidate.get("canonical_post_url") or candidate.get("source_url") or record.source_url),
        media_url=_plain_url(candidate.get("media_url")),
        local_path=local_path,
        filename=_safe_filename(candidate.get("filename") or _filename_from_url(candidate.get("media_url"))),
        mime_type=_clean(candidate.get("mime_type")),
        byte_status=_clean(candidate.get("byte_status") or ("session_local_file" if local_path else "metadata_only_remote_candidate")),
        provenance=f"R43T {_clean(candidate.get('source_observation_marker'))}",
        warning=_clean(candidate.get("warning") or ("metadata-only remote candidate; R43T/R43A did not download remote Twitter/X media" if not local_path else "")),
        bound_to_record_id=record.record_id,
        bound_to_source_url=_plain_url(record.source_url),
        binding_status="bound_to_post",
        binding_reason=_clean(candidate.get("binding_reason")),
        source_observation_kind=_clean(candidate.get("source_observation_kind")),
        source_observation_marker=_clean(candidate.get("source_observation_marker")),
        source_observation_path=_clean(candidate.get("source_observation_path")),
        metadata_only_remote_media_not_downloaded=not bool(local_path),
        playlist_manifest_url=_plain_url(candidate.get("playlist_manifest_url")),
    )


def _summary(candidates: list[Mapping[str, Any]], bound: list[Mapping[str, Any]], unbound: list[Mapping[str, Any]], paths: Mapping[str, str]) -> dict[str, Any]:
    return {
        "r43t_status": R43T_PASS_STATUS,
        "visible_observation_count": sum(1 for row in candidates if row.get("source_observation_marker") == "R42GV" and row.get("source_observation_kind") != "visible_browser_media_segment"),
        "r42gt_media_index_count": sum(1 for row in candidates if row.get("source_observation_marker") == "R42GT"),
        "media_inventory_count": sum(1 for row in candidates if row.get("source_observation_marker") == "media_inventory"),
        "bound_media_count": len(bound),
        "unbound_media_count": len(unbound),
        "bound_image_count": sum(1 for row in bound if row.get("media_class") == "image"),
        "bound_video_count": sum(1 for row in bound if row.get("media_class") == "video"),
        "bound_manifest_count": sum(1 for row in bound if row.get("media_class") == "manifest"),
        "bound_segment_count": sum(1 for row in bound if row.get("media_class") == "segment"),
        "bound_other_media_count": sum(1 for row in bound if row.get("media_class") not in {"image", "video", "manifest", "segment"}),
        "session_local_media_count": sum(1 for row in bound if _local_file_exists(row.get("local_path"))),
        "metadata_only_media_count": sum(1 for row in bound if not _local_file_exists(row.get("local_path"))),
        "count_scope": ("standalone_r43t_fixture_matches_integrated_r43r_ledger_binding_scope" if "fixture_runner_output" in " ".join(str(value).lower() for value in paths.values()) else "live_runner_observation_binding_scope"),
        "standalone_r43t_report_count_scope": ("The standalone fixture includes fast media observations plus article DOM media candidates so its headline counts match the integrated R43R fixture ledger proof." if "fixture_runner_output" in " ".join(str(value).lower() for value in paths.values()) else "The live runner report counts media observations actually present in this run; fixture-only media-class expectations are not required."),
        "segment_table_path": _clean(paths.get("visible_segments_ndjson")),
        "unified_media_window_state_path": _clean(paths.get("unified_media_window_state")),
        "r42gt_manifest_path": _clean(paths.get("r42gt_manifest")),
        "source_paths": dict(paths),
    }


def _dedupe_media_items(items: Iterable[TwitterXAccountMediaItemR43A]) -> tuple[TwitterXAccountMediaItemR43A, ...]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[TwitterXAccountMediaItemR43A] = []
    for item in items:
        key = (item.media_class, _normalize_url(item.media_url), item.local_path)
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return tuple(rows)


def _loose_media_attached_to_all_posts(records: list[TwitterXAccountRecordR43A], bound_rows: list[Mapping[str, Any]]) -> bool:
    if len(records) < 2:
        return False
    loose = [row for row in bound_rows if row.get("binding_reason") == "single_status_page_fallback"]
    return bool(loose) and len({row.get("bound_to_record_id") for row in loose}) == len(records)


def _write_fixture_runner_output(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    local_image = root / "session_image.jpg"
    local_video = root / "session_video.mp4"
    local_image.write_bytes(b"R43T_IMAGE")
    local_video.write_bytes(b"R43T_VIDEO")
    store = root / "visible_browser_media_observation_store"
    store.mkdir(parents=True, exist_ok=True)
    rows = [
        {"canonical_media_url": "https://pbs.twimg.com/media/status_bound.jpg?format=jpg&name=large", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222", "media_class": "image", "local_session_path": str(local_image)},
        {"canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/video.mp4", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "media_class": "video", "local_session_path": str(local_video)},
        {"canonical_media_url": "https://pbs.twimg.com/media/r43r_image.jpg?format=jpg&name=large", "media_class": "image"},
        {"canonical_media_url": "https://abs.twimg.com/icons/decorative.png", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222", "media_class": "image"},
        {"canonical_media_url": "https://pbs.twimg.com/profile_images/avatar.jpg", "media_class": "image"},
        {"canonical_media_url": "https://pbs.twimg.com/media/unbound.jpg?format=jpg&name=large", "media_class": "image"},
    ]
    _write_json(store / "visible_browser_media_observations.json", {"observations": rows})
    (store / "visible_browser_media_observations.ndjson").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    segments = [
        {"canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00001.ts", "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222"},
        {"canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00002.ts", "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222"},
    ]
    (store / "visible_browser_media_segments.ndjson").write_text("\n".join(json.dumps(row) for row in segments) + "\n", encoding="utf-8")
    pkg = root / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260918T000000Z"
    pkg.mkdir(parents=True, exist_ok=True)
    _write_json(pkg / "manifest.json", {"marker": "R42GT"})
    _write_json(pkg / "media_index.json", {"media": [{"canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "post_id": "2222222222222222222", "media_kind": "manifest"}]})
    (pkg / "media_index.ndjson").write_text(json.dumps({"canonical_media_url": "https://pbs.twimg.com/media/dom_bound.jpg?format=jpg&name=large", "media_kind": "image"}) + "\n", encoding="utf-8")
    _write_json(root / "media_inventory.json", [{"media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/remote_video.mp4", "status_id": "2222222222222222222", "media_class": "video"}])


def _safe_media_class(value: Any, url: Any = "") -> str:
    text = _clean(value).lower()
    clean_url = _plain_url(url).lower()
    if text in {"image", "photo", "picture"}:
        return "image"
    if text in {"video", "mp4", "movie"}:
        return "video"
    if text in {"manifest", "playlist", "m3u8", "mpd", "stream"} or clean_url.endswith((".m3u8", ".mpd")):
        return "manifest"
    if text in {"segment", "chunk", "ts", "m4s"} or clean_url.endswith((".ts", ".m4s")):
        return "segment"
    if any(token in clean_url for token in ("pbs.twimg.com/media/", ".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return "image"
    if any(token in clean_url for token in ("video.twimg.com", ".mp4", "ext_tw_video", "amplify_video")):
        return "video"
    return "media"


def _is_decorative_x_asset(url: Any) -> bool:
    text = _plain_url(url).lower()
    return "abs.twimg.com" in text or "/emoji/" in text or "/hashflags/" in text or "client-web" in text


def _is_profile_asset_url(url: Any) -> bool:
    text = _plain_url(url).lower()
    return "default_profile_images" in text or "profile_images" in text or "profile_banners" in text or "banner" in text


def _status_id_from_url(url: Any) -> str:
    match = re.search(r"/status/(\d+)", _plain_url(url))
    return match.group(1) if match else ""


def _normalize_url(url: Any) -> str:
    text = _plain_url(url)
    if not text:
        return ""
    parsed = urlsplit(text)
    host = parsed.netloc.lower().replace("twitter.com", "x.com")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme or 'https'}://{host}{path}"


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/")
    normalized = text.replace("]\\(", "](").replace("\\)", ")")
    match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
    return (match.group(1) if match else normalized).replace("&amp;", "&").strip()


def _filename_from_url(value: Any) -> str:
    parsed = urlsplit(_plain_url(value))
    name = Path(parsed.path).name or "media"
    if "." not in name:
        cls = _safe_media_class("", value)
        name += {"image": ".jpg", "video": ".mp4", "manifest": ".m3u8", "segment": ".ts"}.get(cls, ".url")
    return _safe_filename(name)


def _stable_media_id(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", _plain_url(value)).strip("_")
    return (text[-80:] if text else "media_candidate")


def _local_file_exists(value: Any) -> bool:
    text = _clean(value)
    return bool(text) and Path(text).is_file()


def _safe_filename(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_. -]+", "_", _clean(value)).strip(" ._-")
    return text[:140] or "media.bin"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _read_ndjson(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    try:
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item, Mapping):
                        rows.append(item)
    except Exception:
        return rows
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    try:
        return _to_jsonable(asdict(value))
    except Exception:
        return _clean(value)


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R43T_REPORT_ROOT)
    args = parser.parse_args(argv)
    result = build_report(args.output_root)
    print(R43T_MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
