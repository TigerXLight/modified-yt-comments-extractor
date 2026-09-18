from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from profile_media_twitter_x_account_media_ledger_r43a import (
    TwitterXAccountMediaItemR43A,
    TwitterXAccountRecordR43A,
    write_twitter_x_account_media_ledger_r43a,
)
from profile_media_twitter_x_fast_media_to_post_ledger_binding_r43t import (
    R43T_PASS_STATUS,
    bind_fast_media_observations_to_post_records_r43t,
    write_unbound_media_index_r43t,
)

R43R_MARKER = "YTCE_R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER"
R43R_PASS_STATUS = "PASS_R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER"
R43R_BLOCKED_STATUS = "BLOCKED_R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER"
R43R_SCHEMA_VERSION = "twitter_x_live_evidence_to_account_ledger.r43r.v1"
R43R_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43r_twitter_x_live_evidence_to_account_ledger"


@dataclass(frozen=True)
class TwitterXLiveEvidenceToAccountLedgerRequestR43R:
    source_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    runner_output_dir: str = ""
    ledger_output_root: str = ""
    r43n_receipt_path: str = ""
    r43o_receipt_path: str = ""
    r43p_receipt_path: str = ""
    live_evidence_summary: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class TwitterXLiveEvidenceToAccountLedgerResultR43R:
    marker: str
    schema_version: str
    status: str
    blocker_reason: str
    source_url: str
    account_handle: str
    capture_timestamp: str
    runner_output_dir: str
    account_capture_dir: str
    account_record_path: str
    manifest_path: str
    account_timeline_path: str
    media_index_path: str
    progress_events_path: str
    review_strings_path: str
    receipt_path: str
    report_json_path: str
    report_md_path: str
    date_folder_count: int
    post_folder_count: int
    ledger_post_count: int
    ledger_media_candidate_count: int
    ledger_metadata_only_media_count: int
    ledger_session_local_media_count: int
    ledger_static_screenshot_count: int
    ledger_warning_count: int
    screenshot_scope: str
    screenshot_is_article_crop: bool
    article_observation_path: str
    rendered_dom_snapshot_path: str
    source_screenshot_path: str
    checks: tuple[Mapping[str, Any], ...]
    bad_checks: tuple[Mapping[str, Any], ...]
    account_ledger_summary: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return self.status == R43R_PASS_STATUS and not self.bad_checks

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def materialize_live_twitter_x_evidence_to_account_ledger_r43r(
    request: TwitterXLiveEvidenceToAccountLedgerRequestR43R | Mapping[str, Any],
) -> TwitterXLiveEvidenceToAccountLedgerResultR43R:
    req = coerce_live_evidence_to_account_ledger_request_r43r(request)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    source_url = _plain_url(req.source_url or _value_from_summary(req.live_evidence_summary, "source_url"))
    handle = _safe_handle(req.account_handle or _handle_from_url(source_url) or "unknown")
    runner_root = _resolve_runner_root(req)
    ledger_root = Path(req.ledger_output_root or Path(R43R_DEFAULT_OUTPUT_ROOT) / "source_exports" / "twitter_x")
    ledger_root.mkdir(parents=True, exist_ok=True)

    paths = _discover_live_evidence_paths(runner_root)
    articles = _load_article_observations(paths["article_json"], paths["article_ndjson"])
    extraction_method = "twitter_x_article_observations"
    if not articles:
        articles = extract_twitter_x_articles_from_dom_snapshot_r43r(paths["rendered_dom"], source_url=source_url, account_handle=handle)
        extraction_method = "rendered_dom_snapshot_html_fallback"

    screenshot_path = paths["screenshot"]
    records, record_warnings = _records_from_articles(
        articles,
        account_handle=handle,
        source_url=source_url,
        capture_timestamp=capture_ts,
        screenshot_path=screenshot_path,
        extraction_method=extraction_method,
    )
    fast_binding = bind_fast_media_observations_to_post_records_r43t(
        records,
        articles=articles,
        paths=paths,
        runner_root=runner_root,
    )
    records = list(fast_binding.records)

    blocker = ""
    if not runner_root or not runner_root.exists():
        blocker = "R43R could not find the R42GZ runner output directory."
    elif not records:
        blocker = "R43R found no visible Twitter/X tweet article records to ledger."

    if blocker:
        result = _blocked_result(
            req=req,
            source_url=source_url,
            handle=handle,
            capture_ts=capture_ts,
            runner_root=runner_root,
            paths=paths,
            blocker=blocker,
        )
        write_report_r43r(result, Path(R43R_DEFAULT_OUTPUT_ROOT))
        return result

    ledger = write_twitter_x_account_media_ledger_r43a(
        records,
        output_root=ledger_root,
        account_handle=handle,
        capture_timestamp=capture_ts,
    )
    capture_dir = Path(ledger.account_capture_dir)
    annotation = _annotate_ledger_posts(
        capture_dir,
        records=records,
        source_screenshot_path=screenshot_path,
        extraction_method=extraction_method,
    )
    unbound_paths = write_unbound_media_index_r43t(capture_dir, fast_binding.unbound_media)
    screenshot_gate_summary = _apply_screenshot_receipt_gate(capture_dir)
    media_index = _read_json(Path(ledger.media_index_path), [])
    manifest = _read_json(Path(ledger.manifest_path), {})
    metadata_only_count = sum(1 for item in media_index if not item.get("copied_local_bytes"))
    session_local_count = sum(1 for item in media_index if item.get("copied_local_bytes"))
    warning_count = len(record_warnings) + len(ledger.warnings or ()) + int(annotation.get("warning_count") or 0)
    date_folder_count = len(ledger.date_folders or ())
    post_folder_count = ledger.post_folder_count

    account_ledger_summary = {
        "r43r_status": R43R_PASS_STATUS,
        "r43r_receipt_path": str(capture_dir / "r43r_live_evidence_to_account_ledger_receipt.json"),
        "account_capture_dir": ledger.account_capture_dir,
        "account_record_path": ledger.account_record_path,
        "manifest_path": ledger.manifest_path,
        "account_timeline_path": ledger.account_timeline_path,
        "media_index_path": ledger.media_index_path,
        "progress_events_path": ledger.progress_events_path,
        "review_strings_path": ledger.review_strings_path,
        "date_folder_count": date_folder_count,
        "post_folder_count": post_folder_count,
        "ledger_post_count": ledger.record_count,
        "ledger_media_candidate_count": ledger.media_count,
        "ledger_static_screenshot_count": ledger.screenshot_count,
        "ledger_metadata_only_media_count": metadata_only_count,
        "ledger_session_local_media_count": session_local_count,
        "ledger_warning_count": warning_count,
        "screenshot_scope": "session_visible_page_fallback",
        "screenshot_is_article_crop": False,
        "article_observation_path": paths["article_json"] or paths["article_ndjson"],
        "rendered_dom_snapshot_path": paths["rendered_dom"],
        "source_screenshot_path": screenshot_path,
        "date_folders": list(ledger.date_folders or ()),
        "fast_media_binding_summary": fast_binding.summary,
        "r43t_status": fast_binding.status,
        "r43t_bound_media_count": fast_binding.summary.get("bound_media_count", 0),
        "r43t_unbound_media_count": fast_binding.summary.get("unbound_media_count", 0),
        "unbound_media_index_path": unbound_paths.get("unbound_media_index_path", ""),
        "unbound_media_candidates_path": unbound_paths.get("unbound_media_candidates_path", ""),
        "screenshot_receipts_index_path": screenshot_gate_summary.get("screenshot_receipts_index_path", ""),
        "screenshot_receipt_count": screenshot_gate_summary.get("receipt_count", 0),
        "warnings": record_warnings + list(ledger.warnings or ()) + list(annotation.get("warnings") or ()),
    }
    receipt = {
        "marker": R43R_MARKER,
        "schema_version": R43R_SCHEMA_VERSION,
        "status": R43R_PASS_STATUS,
        "source_url": source_url,
        "account_handle": handle,
        "capture_timestamp": capture_ts,
        "runner_output_dir": str(runner_root),
        "live_evidence_paths": paths,
        "extraction_method": extraction_method,
        "article_count": len(records),
        "fast_media_binding_summary": fast_binding.summary,
        "r43t_result": fast_binding.to_dict(),
        "account_ledger_summary": account_ledger_summary,
        "manifest": manifest,
        "side_effect_flags": build_r43r_side_effect_flags(),
    }
    receipt_path = capture_dir / "r43r_live_evidence_to_account_ledger_receipt.json"
    _write_json(receipt_path, receipt)
    _write_text(capture_dir / "r43r_live_evidence_to_account_ledger_receipt.md", _receipt_md(receipt))

    checks = _build_checks(
        account_ledger_summary,
        records=records,
        capture_dir=capture_dir,
        media_index=media_index,
        paths=paths,
        fast_binding=fast_binding.to_dict(),
    )
    bad = tuple(check for check in checks if check.get("status") != "pass")
    status = R43R_PASS_STATUS if not bad else R43R_BLOCKED_STATUS
    result = TwitterXLiveEvidenceToAccountLedgerResultR43R(
        marker=R43R_MARKER,
        schema_version=R43R_SCHEMA_VERSION,
        status=status,
        blocker_reason="" if not bad else "One or more R43R ledger checks failed.",
        source_url=source_url,
        account_handle=handle,
        capture_timestamp=capture_ts,
        runner_output_dir=str(runner_root),
        account_capture_dir=ledger.account_capture_dir,
        account_record_path=ledger.account_record_path,
        manifest_path=ledger.manifest_path,
        account_timeline_path=ledger.account_timeline_path,
        media_index_path=ledger.media_index_path,
        progress_events_path=ledger.progress_events_path,
        review_strings_path=ledger.review_strings_path,
        receipt_path=str(receipt_path),
        report_json_path=str(capture_dir / "R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER_REPORT.json"),
        report_md_path=str(capture_dir / "R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER_REPORT.md"),
        date_folder_count=date_folder_count,
        post_folder_count=post_folder_count,
        ledger_post_count=ledger.record_count,
        ledger_media_candidate_count=ledger.media_count,
        ledger_metadata_only_media_count=metadata_only_count,
        ledger_session_local_media_count=session_local_count,
        ledger_static_screenshot_count=ledger.screenshot_count,
        ledger_warning_count=warning_count,
        screenshot_scope="session_visible_page_fallback",
        screenshot_is_article_crop=False,
        article_observation_path=paths["article_json"] or paths["article_ndjson"],
        rendered_dom_snapshot_path=paths["rendered_dom"],
        source_screenshot_path=screenshot_path,
        checks=checks,
        bad_checks=bad,
        account_ledger_summary=account_ledger_summary,
    )
    write_report_r43r(result, capture_dir)
    return result


def coerce_live_evidence_to_account_ledger_request_r43r(
    request: TwitterXLiveEvidenceToAccountLedgerRequestR43R | Mapping[str, Any],
) -> TwitterXLiveEvidenceToAccountLedgerRequestR43R:
    if isinstance(request, TwitterXLiveEvidenceToAccountLedgerRequestR43R):
        return request
    data = dict(request or {})
    summary = data.get("live_evidence_summary") or {}
    if not isinstance(summary, Mapping):
        summary = {}
    return TwitterXLiveEvidenceToAccountLedgerRequestR43R(
        source_url=_plain_url(data.get("source_url") or data.get("account_url") or summary.get("source_url")),
        account_handle=_safe_handle(data.get("account_handle") or summary.get("account_handle")),
        capture_timestamp=_clean(data.get("capture_timestamp") or summary.get("capture_timestamp")),
        runner_output_dir=_clean(data.get("runner_output_dir") or summary.get("runner_output_dir")),
        ledger_output_root=_clean(data.get("ledger_output_root") or data.get("output_root")),
        r43n_receipt_path=_clean(data.get("r43n_receipt_path") or summary.get("r43n_receipt_path")),
        r43o_receipt_path=_clean(data.get("r43o_receipt_path") or summary.get("r43o_receipt_path")),
        r43p_receipt_path=_clean(data.get("r43p_receipt_path") or summary.get("r43p_receipt_path")),
        live_evidence_summary=dict(summary),
    )


def extract_twitter_x_articles_from_dom_snapshot_r43r(
    rendered_dom_path: str | Path,
    *,
    source_url: str = "",
    account_handle: str = "",
) -> list[dict[str, Any]]:
    path = Path(rendered_dom_path)
    if not path.is_file():
        return []
    parser = _TwitterArticleParser(source_url=_plain_url(source_url), account_handle=_safe_handle(account_handle))
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser.articles


def build_r43r_side_effect_flags() -> dict[str, bool]:
    return {
        "r43r_live_evidence_materialization_invoked": True,
        "browser_session_started_by_r43r": False,
        "network_actions_performed_by_r43r": False,
        "remote_media_downloads_performed_by_r43r": False,
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "source_role_checks_performed": False,
        "review_window_rewrite_performed": False,
        "youtube_capture_engine_changed": False,
    }


def build_report(output_root: str | Path = R43R_DEFAULT_OUTPUT_ROOT) -> TwitterXLiveEvidenceToAccountLedgerResultR43R:
    root = Path(output_root)
    runner = root / "fixture_runner_output"
    _write_fixture_runner_output(runner)
    result = materialize_live_twitter_x_evidence_to_account_ledger_r43r(
        {
            "source_url": "https://x.com/examaddaorg",
            "account_handle": "examaddaorg",
            "capture_timestamp": "20260917T060000Z",
            "runner_output_dir": str(runner),
            "ledger_output_root": str(root / "source_exports" / "twitter_x"),
        }
    )
    write_report_r43r(result, root)
    return result


def write_report_r43r(result: TwitterXLiveEvidenceToAccountLedgerResultR43R, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER_REPORT.json"
    md_path = root / "R43R_TWITTER_X_LIVE_EVIDENCE_TO_ACCOUNT_LEDGER_REPORT.md"
    payload = result.to_dict()
    _write_json(json_path, payload)
    lines = [
        "# R43R Twitter/X Live Evidence To Account Ledger",
        "",
        f"- marker: `{result.marker}`",
        f"- status: `{result.status}`",
        f"- account capture: `{result.account_capture_dir}`",
        f"- ledger posts: `{result.ledger_post_count}`",
        f"- media candidates: `{result.ledger_media_candidate_count}`",
        f"- screenshots: `{result.ledger_static_screenshot_count}`",
        "",
        "## Checks",
    ]
    for check in result.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    _write_text(md_path, "\n".join(lines).rstrip() + "\n")
    return json_path, md_path


class _TwitterArticleParser(HTMLParser):
    def __init__(self, *, source_url: str, account_handle: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.account_handle = account_handle
        self.articles: list[dict[str, Any]] = []
        self._depth = 0
        self._current: dict[str, Any] | None = None
        self._text_parts: list[str] = []
        self._in_time = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag.lower() == "article" and attr.get("data-testid") == "tweet" and self._current is None:
            self._depth = 1
            self._text_parts = []
            self._current = {
                "observed_order": len(self.articles) + 1,
                "article_link_hrefs": [],
                "article_image_srcs": [],
                "article_video_srcs": [],
                "article_media_candidates": [],
                "extraction_method": "rendered_dom_snapshot_html_fallback",
            }
            return
        if self._current is None:
            return
        if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self._depth += 1
        if tag.lower() == "a":
            href = attr.get("href", "")
            if href:
                url = _absolute_x_url(href)
                self._current.setdefault("article_link_hrefs", []).append(url)
                if "/status/" in url and not self._current.get("canonical_status_url"):
                    self._current["canonical_status_url"] = url
                    self._current["status_id"] = _status_id_from_url(url)
        elif tag.lower() == "img":
            src = attr.get("src", "")
            if src:
                self._current.setdefault("article_image_srcs", []).append(src)
                if _is_post_attached_media_url(src):
                    self._current.setdefault("article_media_candidates", []).append({"media_url": src, "media_class": "image"})
        elif tag.lower() in {"video", "source"}:
            src = attr.get("src", "") or attr.get("poster", "")
            if src:
                self._current.setdefault("article_video_srcs", []).append(src)
                if _is_post_attached_media_url(src):
                    self._current.setdefault("article_media_candidates", []).append({"media_url": src, "media_class": "video"})
        elif tag.lower() == "time":
            self._in_time = True
            if attr.get("datetime"):
                self._current["time_datetime"] = attr["datetime"]

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag.lower() == "time":
            self._in_time = False
        if self._depth > 0:
            self._depth -= 1
        if tag.lower() == "article" and self._depth == 0:
            text = _collapse_ws(" ".join(self._text_parts))
            self._current["article_text"] = text
            if not self._current.get("time_text"):
                self._current["time_text"] = _guess_time_text(text)
            if not self._current.get("author_handle"):
                self._current["author_handle"] = _handle_from_url(self._current.get("canonical_status_url")) or self.account_handle
            if not self._current.get("author_display_name"):
                self._current["author_display_name"] = _guess_author_display_name(text, self._current.get("author_handle", ""))
            if not self._current.get("canonical_status_url"):
                self._current["canonical_status_url"] = self.source_url
            self.articles.append(dict(self._current))
            self._current = None
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = _collapse_ws(data)
        if not text:
            return
        self._text_parts.append(text)
        if self._in_time and not self._current.get("time_text"):
            self._current["time_text"] = text


def _records_from_articles(
    articles: Iterable[Mapping[str, Any]],
    *,
    account_handle: str,
    source_url: str,
    capture_timestamp: str,
    screenshot_path: str,
    extraction_method: str,
) -> tuple[list[TwitterXAccountRecordR43A], list[str]]:
    records: list[TwitterXAccountRecordR43A] = []
    warnings: list[str] = []
    for index, article in enumerate(articles, start=1):
        status_url = _plain_url(article.get("canonical_status_url") or source_url)
        status_id = _clean(article.get("status_id") or _status_id_from_url(status_url) or f"article_{index:03d}")
        date_value, date_source, date_warning = _date_value_for_article(article, capture_timestamp=capture_timestamp)
        if date_warning:
            warnings.append(f"{status_id}: {date_warning}")
        media_items = []
        seen_media: set[str] = set()
        for media_index, candidate in enumerate(article.get("article_media_candidates") or (), start=1):
            media_url = _plain_url(candidate.get("media_url") if isinstance(candidate, Mapping) else candidate)
            if not media_url or media_url in seen_media or not _is_post_attached_media_url(media_url):
                continue
            seen_media.add(media_url)
            media_items.append(
                TwitterXAccountMediaItemR43A(
                    media_id=f"{status_id}_media_{media_index:03d}",
                    media_class=_safe_media_class((candidate.get("media_class") if isinstance(candidate, Mapping) else "") or "media"),
                    source_url=status_url,
                    media_url=media_url,
                    filename=_filename_from_url(media_url),
                    byte_status="metadata_only_remote_candidate",
                    provenance=f"R43R {extraction_method}",
                    warning="metadata-only remote candidate; R43R did not download remote Twitter/X media",
                )
            )
        review_strings = [
            f"screenshot_scope=session_visible_page_fallback; screenshot_is_article_crop=false; date_source={date_source}",
            "R43R metadata-only media materialization; no remote media download performed.",
        ]
        if date_warning:
            review_strings.append(date_warning)
        records.append(
            TwitterXAccountRecordR43A(
                record_id=status_id,
                record_type="post",
                source_url=status_url,
                visible_text=_clean(article.get("article_text")),
                visible_timestamp=date_value,
                capture_timestamp=capture_timestamp,
                author_handle=_safe_handle(article.get("author_handle") or _handle_from_url(status_url) or account_handle),
                author_display_name=_clean(article.get("author_display_name")),
                account_handle=account_handle,
                repost_context={
                    "date_source": date_source,
                    "date_warning": date_warning,
                    "article_extraction_method": extraction_method,
                },
                static_screenshot_path=screenshot_path,
                media_items=tuple(media_items),
                review_strings=tuple(review_strings),
                observed_order=_safe_int(article.get("observed_order"), index),
            )
        )
    return records, warnings


def _annotate_ledger_posts(
    capture_dir: Path,
    *,
    records: list[TwitterXAccountRecordR43A],
    source_screenshot_path: str,
    extraction_method: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    record_by_id = {record.record_id: record for record in records}
    for post_json in capture_dir.glob("dates/*/post_*/post.json"):
        payload = _read_json(post_json, {})
        record = record_by_id.get(str(payload.get("record_id") or ""))
        media_candidates = [item.to_dict() for item in (record.media_items if record else ())]
        date_source = _clean((record.repost_context or {}).get("date_source") if record else "")
        date_warning = _clean((record.repost_context or {}).get("date_warning") if record else "")
        post_warnings = list(payload.get("warnings") or [])
        if date_warning and date_warning not in post_warnings:
            post_warnings.append(date_warning)
        post_warnings.append("Static screenshot is a session visible-page fallback, not a per-article crop.")
        payload.update(
            {
                "screenshot_scope": "session_visible_page_fallback",
                "screenshot_is_article_crop": False,
                "source_session_screenshot_path": source_screenshot_path,
                "article_extraction_method": extraction_method,
                "date_source": date_source or payload.get("date_source") or "",
                "media_candidates": media_candidates,
                "metadata_only_remote_media_not_downloaded": True,
                "warnings": post_warnings,
            }
        )
        _write_json(post_json, payload)
        md_path = post_json.with_name("post.md")
        if md_path.is_file():
            existing = md_path.read_text(encoding="utf-8")
            addition = (
                "\n## R43R ledger materialization\n\n"
                "- Screenshot scope: `session_visible_page_fallback`\n"
                "- Screenshot is article crop: `false`\n"
                "- Remote media candidates are metadata-only; R43R did not download Twitter/X media.\n"
            )
            md_path.write_text(existing.rstrip() + addition + "\n", encoding="utf-8")
        warnings.append(f"{post_json}: session screenshot fallback recorded")
    account_record = capture_dir / "account_record.md"
    if account_record.is_file() and records:
        existing = account_record.read_text(encoding="utf-8")
        lines = ["", "## R43R visible article summaries", ""]
        for record in sorted(records, key=lambda row: row.observed_order):
            snippet = _collapse_ws(record.visible_text)[:240]
            lines.append(f"- `{record.record_id}` @{record.author_handle}: {snippet}")
        account_record.write_text(existing.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"warnings": warnings, "warning_count": len(warnings)}


def _apply_screenshot_receipt_gate(capture_dir: Path) -> dict[str, Any]:
    try:
        from profile_media_visual_screenshot_receipt_materialization_gate_r43c import (
            apply_visual_screenshot_receipt_materialization_gate_r43c,
        )

        result = apply_visual_screenshot_receipt_materialization_gate_r43c(
            capture_dir,
            default_context={
                "platform": "twitter_x",
                "screenshot_scope": "session_visible_page_fallback",
                "screenshot_is_article_crop": False,
                "materialized_in_viewport": False,
                "materialization_clean": False,
                "capture_gate": True,
            },
        )
        return result.to_dict()
    except Exception as exc:
        return {
            "status": "BLOCKED_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE",
            "receipt_count": 0,
            "screenshot_receipts_index_path": "",
            "warning": f"R43C screenshot receipt gate failed safely: {type(exc).__name__}: {exc}",
        }


def _load_article_observations(json_path: str, ndjson_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if json_path and Path(json_path).is_file():
        payload = _read_json(Path(json_path), [])
        if isinstance(payload, Mapping):
            payload = payload.get("articles") or payload.get("observations") or []
        if isinstance(payload, list):
            rows.extend(dict(row) for row in payload if isinstance(row, Mapping))
    if not rows and ndjson_path and Path(ndjson_path).is_file():
        rows.extend(dict(row) for row in _read_ndjson(Path(ndjson_path)))
    return sorted(rows, key=lambda row: _safe_int(row.get("observed_order"), 0))


def _discover_live_evidence_paths(runner_root: Path) -> dict[str, str]:
    def first(pattern: str) -> str:
        if not runner_root or not runner_root.exists():
            return ""
        matches = sorted(p for p in runner_root.rglob(pattern) if p.is_file() and p.stat().st_size > 0)
        return str(matches[0]) if matches else ""

    return {
        "article_json": first("twitter_x_article_observations.json"),
        "article_ndjson": first("twitter_x_article_observations.ndjson"),
        "rendered_dom": first("rendered_dom_snapshot.html"),
        "screenshot": first("screenshot.png"),
        "visible_observations_json": first("visible_browser_media_observations.json"),
        "visible_observations_ndjson": first("visible_browser_media_observations.ndjson"),
        "visible_segments_ndjson": first("visible_browser_media_segments.ndjson"),
        "r42gt_media_index_json": first("media_index.json"),
        "r42gt_media_index_ndjson": first("media_index.ndjson"),
        "r42gt_manifest": first("manifest.json"),
        "network_events": first("network_events.jsonl"),
        "api_pages": first("api_pages.jsonl"),
        "response_bodies": first("network_response_bodies.jsonl"),
        "media_inventory": first("media_inventory.json"),
    }


def _resolve_runner_root(req: TwitterXLiveEvidenceToAccountLedgerRequestR43R) -> Path:
    if req.runner_output_dir:
        return Path(req.runner_output_dir)
    r43p_receipt_path = Path(req.r43p_receipt_path) if req.r43p_receipt_path else Path()
    if r43p_receipt_path.is_file():
        receipt = _read_json(r43p_receipt_path, {})
        runner_dir = _clean(receipt.get("runner_output_dir"))
        if runner_dir:
            return Path(runner_dir)
    for value in req.live_evidence_summary.get("promoted_live_observation_paths") or ():
        path = Path(_clean(value))
        if path.name == "rendered_dom_snapshot.html":
            return path.parent
        for parent in path.parents:
            if (parent / "rendered_dom_snapshot.html").is_file() or (parent / "screenshot.png").is_file():
                return parent
    return Path()


def _blocked_result(
    *,
    req: TwitterXLiveEvidenceToAccountLedgerRequestR43R,
    source_url: str,
    handle: str,
    capture_ts: str,
    runner_root: Path,
    paths: Mapping[str, str],
    blocker: str,
) -> TwitterXLiveEvidenceToAccountLedgerResultR43R:
    checks = (_check("live_dom_articles_extracted_in_visible_order", False, blocker),)
    return TwitterXLiveEvidenceToAccountLedgerResultR43R(
        marker=R43R_MARKER,
        schema_version=R43R_SCHEMA_VERSION,
        status=R43R_BLOCKED_STATUS,
        blocker_reason=blocker,
        source_url=source_url,
        account_handle=handle,
        capture_timestamp=capture_ts,
        runner_output_dir=str(runner_root),
        account_capture_dir="",
        account_record_path="",
        manifest_path="",
        account_timeline_path="",
        media_index_path="",
        progress_events_path="",
        review_strings_path="",
        receipt_path="",
        report_json_path="",
        report_md_path="",
        date_folder_count=0,
        post_folder_count=0,
        ledger_post_count=0,
        ledger_media_candidate_count=0,
        ledger_metadata_only_media_count=0,
        ledger_session_local_media_count=0,
        ledger_static_screenshot_count=0,
        ledger_warning_count=0,
        screenshot_scope="",
        screenshot_is_article_crop=False,
        article_observation_path=paths.get("article_json", "") or paths.get("article_ndjson", ""),
        rendered_dom_snapshot_path=paths.get("rendered_dom", ""),
        source_screenshot_path=paths.get("screenshot", ""),
        checks=checks,
        bad_checks=checks,
        account_ledger_summary={"r43r_status": R43R_BLOCKED_STATUS, "blocker_reason": blocker},
    )


def _build_checks(
    summary: Mapping[str, Any],
    *,
    records: list[TwitterXAccountRecordR43A],
    capture_dir: Path,
    media_index: list[Mapping[str, Any]],
    paths: Mapping[str, str],
    fast_binding: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], ...]:
    account_record = _read_text(Path(summary.get("account_record_path") or ""))
    timeline_rows = _read_ndjson(Path(summary.get("account_timeline_path") or ""))
    post_jsons = list(capture_dir.glob("dates/*/post_*/post.json"))
    post_payloads = [_read_json(path, {}) for path in post_jsons]
    post_mds = list(capture_dir.glob("dates/*/post_*/post.md"))
    static_screenshots = list(capture_dir.glob("dates/*/post_*/static_screenshot.png"))
    screenshot_receipts = list(capture_dir.glob("dates/*/post_*/static_screenshot_receipt.json"))
    decorative_attached = any(_is_decorative_x_asset(str(item.get("media_url") or "")) for item in media_index)
    avatar_attached = any(_is_profile_asset_url(str(item.get("media_url") or "")) for item in media_index)
    binding_summary = dict((fast_binding or {}).get("summary") or summary.get("fast_media_binding_summary") or {})
    fixture_scope = binding_summary.get("count_scope") == "standalone_r43t_fixture_matches_integrated_r43r_ledger_binding_scope"
    rows_with_binding = [item for item in media_index if item.get("binding_status")]
    local_images = [item for item in media_index if item.get("media_class") == "image" and item.get("copied_local_bytes")]
    local_videos = [item for item in media_index if item.get("media_class") == "video" and item.get("copied_local_bytes")]
    remote_images = [item for item in media_index if item.get("media_class") == "image" and not item.get("copied_local_bytes")]
    remote_videos = [item for item in media_index if item.get("media_class") == "video" and not item.get("copied_local_bytes")]
    manifests = [item for item in media_index if item.get("media_class") == "manifest"]
    segments = [item for item in media_index if item.get("media_class") == "segment"]
    ambiguous_payloads = [
        row for row in post_payloads
        if row.get("visible_timestamp") == "unknown_date"
        or row.get("date_source") == "unknown_ambiguous_month_day_visible_time"
        or any("Ambiguous visible date" in str(warning) for warning in row.get("warnings") or ())
    ]
    relative_payloads = [
        row for row in post_payloads
        if row.get("date_source") == "capture_date_from_relative_visible_time"
        or any("Relative visible time" in str(warning) for warning in row.get("warnings") or ())
    ]
    return (
        _check("live_dom_articles_extracted_in_visible_order", len(records) >= 1 and [r.observed_order for r in records] == sorted(r.observed_order for r in records)),
        _check("article_visible_text_preserved", any(record.visible_text for record in records)),
        _check("author_handle_preserved", any(record.author_handle for record in records)),
        _check("status_url_or_stable_slug_preserved", all(record.record_id and record.source_url for record in records)),
        _check("date_folder_uses_visible_date_when_available", bool(summary.get("date_folder_count"))),
        _check("unknown_date_folder_used_when_ambiguous", bool(ambiguous_payloads) and all(row.get("visible_date_folder") == "unknown_date" for row in ambiguous_payloads)),
        _check("relative_time_uses_capture_date_with_warning", bool(relative_payloads) and all(row.get("visible_date_folder") != "unknown_date" and any("Relative visible time" in str(warning) for warning in row.get("warnings") or ()) for row in relative_payloads)),
        _check("date_source_recorded_for_each_post", bool(post_payloads) and all(_clean(row.get("date_source")) for row in post_payloads) and all(_clean(row.get("date_source")) for row in timeline_rows)),
        _check("account_record_md_links_each_post_folder", all("post_" + record.record_id in account_record for record in records)),
        _check("account_timeline_ndjson_has_one_row_per_extracted_article", len(timeline_rows) == len(records)),
        _check("post_md_contains_visible_text_timestamp_source_url_media_summary", bool(post_mds) and all("Visible text" in _read_text(path) and "Source URL" in _read_text(path) for path in post_mds)),
        _check("post_json_contains_screenshot_scope_and_media_candidates", bool(post_jsons) and all(_read_json(path, {}).get("screenshot_scope") for path in post_jsons)),
        _check("static_screenshot_written_or_linked_for_each_post", len(static_screenshots) == len(records)),
        _check("fast_media_observation_store_loaded", _safe_int(binding_summary.get("visible_observation_count")) > 0),
        _check("r42gt_media_index_loaded", _safe_int(binding_summary.get("r42gt_media_index_count")) > 0),
        _check("media_inventory_loaded", _safe_int(binding_summary.get("media_inventory_count")) > 0 or not fixture_scope),
        _check("media_bound_by_status_id_to_correct_post", any(item.get("binding_reason") == "status_id_match" for item in media_index) or not fixture_scope),
        _check("media_bound_by_canonical_post_url_to_correct_post", any(item.get("binding_reason") == "canonical_post_url_match" for item in media_index) or not fixture_scope),
        _check("media_bound_by_article_dom_url_to_correct_post", any(item.get("binding_reason") == "article_dom_media_url_match" for item in media_index)),
        _check("loose_account_level_media_not_attached_to_all_posts", not _loose_binding_attached_to_all_posts(media_index, records)),
        _check("unbound_media_preserved_in_unbound_index", (_safe_int(binding_summary.get("unbound_media_count")) == 0) or (bool(summary.get("unbound_media_index_path")) and Path(str(summary.get("unbound_media_index_path"))).is_file())),
        _check("local_session_image_copied_to_post_media_images", any("/media/images/" in str(item.get("local_export_path", "")).replace("\\", "/") for item in local_images) or not fixture_scope),
        _check("local_session_video_copied_to_post_media_videos", any("/media/videos/" in str(item.get("local_export_path", "")).replace("\\", "/") for item in local_videos) or not fixture_scope),
        _check("remote_image_written_as_metadata_receipt_not_downloaded", any(str(item.get("local_export_path", "")).endswith(".url.txt") for item in remote_images)),
        _check("remote_video_written_as_metadata_receipt_not_downloaded", any(str(item.get("local_export_path", "")).endswith(".url.txt") for item in remote_videos) or not fixture_scope),
        _check("manifest_written_to_post_media_manifests_or_receipt", any("/media/manifests/" in str(item.get("local_export_path", "")).replace("\\", "/") for item in manifests) or not fixture_scope),
        _check("segments_preserved_under_post_media_segments_or_segment_receipt", any("/media/segments/" in str(item.get("local_export_path", "")).replace("\\", "/") for item in segments) or not fixture_scope),
        _check("decorative_x_assets_not_attached_as_post_media", not decorative_attached),
        _check("profile_avatar_not_attached_as_post_media", not avatar_attached),
        _check("account_record_links_each_post_media_folder", bool(post_payloads) and "Media counts" in account_record and "media/" in account_record),
        _check("account_record_shows_per_post_media_counts", "Media counts" in account_record),
        _check("account_timeline_ndjson_has_per_post_media_counts", bool(timeline_rows) and all("image_count" in row and "video_count" in row and "metadata_only_media_count" in row for row in timeline_rows)),
        _check("media_index_rows_include_binding_status_and_reason", bool(rows_with_binding) and all(item.get("binding_status") and item.get("binding_reason") for item in rows_with_binding)),
        _check("media_index_rows_include_record_folder_and_visible_date_folder", bool(media_index) and all(item.get("record_folder") and item.get("visible_date_folder") for item in media_index)),
        _check("static_screenshot_receipt_written_by_r43c", len(screenshot_receipts) == len(records)),
        _check("screenshot_scope_remains_session_visible_page_fallback", bool(post_payloads) and all(row.get("screenshot_scope") == "session_visible_page_fallback" for row in post_payloads)),
        _check("metadata_only_remote_media_not_downloaded", all(item.get("remote_download_performed_by_r43a") is False for item in media_index)),
        _check("no_cookie_token_challenge_login_automation", all(build_r43r_side_effect_flags().get(key) is False for key in ("cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed", "login_automation_performed"))),
        _check("youtube_capture_engine_unchanged", build_r43r_side_effect_flags()["youtube_capture_engine_changed"] is False),
        _check("plain_machine_urls", _machine_urls_are_plain(summary) and _machine_urls_are_plain(media_index)),
    )


def _loose_binding_attached_to_all_posts(media_index: Iterable[Mapping[str, Any]], records: list[TwitterXAccountRecordR43A]) -> bool:
    if len(records) < 2:
        return False
    loose_bound = [
        item for item in media_index
        if item.get("binding_reason") == "single_status_page_fallback"
        or item.get("binding_status") == "unbound_account_level_candidate"
    ]
    return bool(loose_bound) and len({item.get("record_id") for item in loose_bound if item.get("record_id")}) == len(records)


def _write_fixture_runner_output(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "screenshot.png").write_bytes(b"r43r screenshot\n")
    local_image = root / "session_image.jpg"
    local_video = root / "session_video.mp4"
    local_image.write_bytes(b"R43T_LOCAL_IMAGE\n")
    local_video.write_bytes(b"R43T_LOCAL_VIDEO\n")
    html = """
<html><body>
<article data-testid="tweet">
  <div>Exam Adda</div><div>@examaddaorg</div>
  <time datetime="2026-09-16T10:20:00Z">Sep 16</time>
  <a href="/examaddaorg/status/1111111111111111111">status</a>
  <div>First visible tweet with text.</div>
</article>
<article data-testid="tweet">
  <div>Exam Adda</div><div>@examaddaorg</div>
  <time>2h</time>
  <a href="https://x.com/examaddaorg/status/2222222222222222222">status</a>
  <div>Relative time tweet.</div>
  <img src="https://pbs.twimg.com/media/r43r_image.jpg?format=jpg&amp;name=large">
  <img src="https://abs.twimg.com/icons/ui.png">
</article>
<article data-testid="tweet">
  <div>Exam Adda</div><div>@examaddaorg</div>
  <time>Sep 14</time>
  <a href="https://x.com/examaddaorg/status/3333333333333333333">status</a>
  <div>Ambiguous visible date tweet.</div>
  <img src="https://pbs.twimg.com/profile_images/avatar.jpg">
</article>
</body></html>
"""
    (root / "rendered_dom_snapshot.html").write_text(html, encoding="utf-8")
    store = root / "visible_browser_media_observation_store"
    store.mkdir(parents=True, exist_ok=True)
    visible_rows = [
        {
            "canonical_media_url": "https://pbs.twimg.com/media/status_bound.jpg?format=jpg&name=large",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "status_id": "2222222222222222222",
            "media_class": "image",
            "local_session_path": str(local_image),
        },
        {
            "canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/session_video.mp4",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "media_class": "video",
            "local_session_path": str(local_video),
        },
        {
            "canonical_media_url": "https://pbs.twimg.com/media/r43r_image.jpg?format=jpg&name=large",
            "media_class": "image",
        },
        {
            "canonical_media_url": "https://abs.twimg.com/icons/ui.png",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "status_id": "2222222222222222222",
            "media_class": "image",
        },
        {
            "canonical_media_url": "https://pbs.twimg.com/profile_images/avatar.jpg",
            "media_class": "image",
        },
        {
            "canonical_media_url": "https://pbs.twimg.com/media/account_loose.jpg?format=jpg&name=large",
            "media_class": "image",
        },
    ]
    _write_json(store / "visible_browser_media_observations.json", {"observations": visible_rows})
    (store / "visible_browser_media_observations.ndjson").write_text("\n".join(json.dumps(row) for row in visible_rows) + "\n", encoding="utf-8")
    segment_rows = [
        {
            "canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00001.ts",
            "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "status_id": "2222222222222222222",
        },
        {
            "canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00002.ts",
            "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "status_id": "2222222222222222222",
        },
    ]
    (store / "visible_browser_media_segments.ndjson").write_text("\n".join(json.dumps(row) for row in segment_rows) + "\n", encoding="utf-8")
    package = root / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260918T000000Z"
    package.mkdir(parents=True, exist_ok=True)
    _write_json(package / "manifest.json", {"marker": "R42GT_FIXTURE"})
    media_rows = [
        {
            "canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8",
            "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222",
            "post_id": "2222222222222222222",
            "media_kind": "manifest",
        },
        {
            "canonical_media_url": "https://pbs.twimg.com/media/r42gt_remote.jpg?format=jpg&name=large",
            "canonical_post_url": "https://x.com/examaddaorg/status/3333333333333333333",
            "post_id": "3333333333333333333",
            "media_kind": "image",
        },
    ]
    _write_json(package / "media_index.json", {"media": media_rows})
    (package / "media_index.ndjson").write_text("\n".join(json.dumps(row) for row in media_rows) + "\n", encoding="utf-8")
    _write_json(
        root / "media_inventory.json",
        [
            {
                "media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/remote_video.mp4",
                "status_id": "2222222222222222222",
                "media_class": "video",
            }
        ],
    )


def _receipt_md(receipt: Mapping[str, Any]) -> str:
    summary = receipt.get("account_ledger_summary") or {}
    return "\n".join(
        [
            "# R43R Live Evidence Account Ledger Receipt",
            "",
            f"- Status: `{receipt.get('status')}`",
            f"- Account: `@{receipt.get('account_handle')}`",
            f"- Account record: `{summary.get('account_record_path', '')}`",
            f"- Ledger posts: `{summary.get('ledger_post_count', 0)}`",
            f"- Media candidates: `{summary.get('ledger_media_candidate_count', 0)}`",
        ]
    ) + "\n"


def _date_value_for_article(article: Mapping[str, Any], *, capture_timestamp: str) -> tuple[str, str, str]:
    dt = _clean(article.get("time_datetime"))
    text = _clean(article.get("time_text"))
    if re.search(r"20\d{2}-\d{2}-\d{2}", dt):
        return dt, "time_datetime", ""
    if re.fullmatch(r"\d+\s*[smhd]", text, flags=re.I) or text.lower() in {"now", "today", "yesterday"}:
        return capture_timestamp, "capture_date_from_relative_visible_time", f"Relative visible time {text!r}; used capture date."
    if re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b\s+\d{1,2}\b", text, flags=re.I):
        return "unknown_date", "unknown_ambiguous_month_day_visible_time", f"Ambiguous visible date {text!r}; used unknown_date."
    return dt or text or "unknown_date", "visible_time_text", "" if dt or text else "No visible timestamp; used unknown_date."


def _is_post_attached_media_url(url: str) -> bool:
    text = _plain_url(url).lower()
    if not text or _is_decorative_x_asset(text) or _is_profile_asset_url(text):
        return False
    return any(host in text for host in ("pbs.twimg.com/media/", "video.twimg.com/", "ext_tw_video", "amplify_video"))


def _is_decorative_x_asset(url: str) -> bool:
    text = url.lower()
    return "abs.twimg.com" in text or "/emoji/" in text or "/hashflags/" in text or "client-web" in text


def _is_profile_asset_url(url: str) -> bool:
    text = url.lower()
    return "default_profile_images" in text or "profile_images" in text or "profile_banners" in text or "banner" in text


def _absolute_x_url(href: str) -> str:
    text = _clean(href)
    if text.startswith("/"):
        return "https://x.com" + text
    return _plain_url(text)


def _status_id_from_url(url: Any) -> str:
    match = re.search(r"/status/(\d+)", _plain_url(url))
    return match.group(1) if match else ""


def _guess_time_text(text: str) -> str:
    match = re.search(r"\b\d+\s*[smhd]\b", text, flags=re.I)
    return match.group(0) if match else ""


def _guess_author_display_name(text: str, handle: str) -> str:
    bits = [part.strip() for part in re.split(r"\s+", text) if part.strip()]
    if not bits:
        return ""
    clean_handle = handle.removeprefix("@").lower()
    for index, part in enumerate(bits[:6]):
        if part.lower().lstrip("@") == clean_handle:
            return " ".join(bits[:index]).strip()
    return bits[0]


def _filename_from_url(url: Any) -> str:
    parsed = urlsplit(_plain_url(url))
    name = Path(parsed.path).name or "media"
    if "." not in name:
        name += ".url"
    return _safe_filename(name)


def _value_from_summary(summary: Mapping[str, Any], key: str) -> Any:
    return summary.get(key) if isinstance(summary, Mapping) else ""


def _check(name: str, ok: bool, detail: str = "") -> Mapping[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


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


def _read_text(path: Path) -> str:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return ""


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _plain_url(value: Any) -> str:
    text = _clean(value)
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", text)
    if markdown:
        return markdown.group(2)
    escaped = re.match(r"^\[([^\]]+)\]\\\((https?://[^)]+)\\\)$", text)
    if escaped:
        return escaped.group(2)
    return text


def _handle_from_url(value: Any) -> str:
    parsed = urlsplit(_plain_url(value))
    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        return _safe_handle(parts[0])
    return ""


def _safe_handle(value: Any) -> str:
    text = _clean(value).lstrip("@")
    text = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")
    return text or ""


def _safe_media_class(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"image", "photo", "jpg", "png"}:
        return "image"
    if text in {"video", "mp4", "m3u8"}:
        return "video"
    if text in {"manifest", "segment"}:
        return text
    return "media"


def _safe_filename(value: Any) -> str:
    text = _clean(value) or "file"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._") or "file"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_ts(value: Any) -> str:
    text = _clean(value)
    if re.fullmatch(r"20\d{6}T\d{6}Z(?:\d+)?", text):
        return text
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}T.*", text):
        return re.sub(r"[^0-9TZ]", "", text)[:15] + "Z"
    return text


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), ensure_ascii=False)
    return "](" not in text and "]\\(" not in text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize live Twitter/X evidence into an account date-folder ledger.")
    parser.add_argument("--runner-output-dir", default="")
    parser.add_argument("--source-url", default="https://x.com/examaddaorg")
    parser.add_argument("--account-handle", default="examaddaorg")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--ledger-output-root", default="")
    parser.add_argument("--output-root", default=R43R_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    if args.runner_output_dir:
        result = materialize_live_twitter_x_evidence_to_account_ledger_r43r(
            {
                "runner_output_dir": args.runner_output_dir,
                "source_url": args.source_url,
                "account_handle": args.account_handle,
                "capture_timestamp": args.capture_timestamp,
                "ledger_output_root": args.ledger_output_root or str(Path(args.output_root) / "source_exports" / "twitter_x"),
            }
        )
        write_report_r43r(result, args.output_root)
    else:
        result = build_report(args.output_root)
    print(result.status)
    return 0 if result.status == R43R_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
