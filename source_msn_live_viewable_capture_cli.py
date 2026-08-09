from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from source_local_webpage_viewer import write_local_webpage_viewer


MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION = "msn_live_viewable_capture_v1"
LIVE_VIEWABLE_CAPTURE_DRY_RUN = "LIVE_VIEWABLE_CAPTURE_DRY_RUN"
LIVE_VIEWABLE_CAPTURE_READY = "LIVE_VIEWABLE_CAPTURE_READY"
LIVE_VIEWABLE_CAPTURE_COMPLETED = "LIVE_VIEWABLE_CAPTURE_COMPLETED"
LIVE_VIEWABLE_CAPTURE_BLOCKED = "LIVE_VIEWABLE_CAPTURE_BLOCKED"
LIVE_VIEWABLE_CAPTURE_FAILED = "LIVE_VIEWABLE_CAPTURE_FAILED"
REPLAY_RESULT_NOT_TESTED = "NOT_TESTED"
DEFAULT_DEVICE_PROFILE = "android-mobile"

MANUAL_REPLAY_STEPS = (
    "Open rendered-page.html directly in a browser and confirm the article is visible.",
    "Open rendered-page.warc.gz in ReplayWeb.page and report whether the article is visible.",
    "Open archive.viewable-live-capture.wacz in ReplayWeb.page only as a separate WACZ replay check.",
    "Record whether comments are visible, partial, or absent.",
    "Record whether ReplayWeb shows Archived Page Not Found, a privacy modal, or a slow-page warning.",
)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_value_for_dict(payload), indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return _sha256_file(path)


def _write_json_with_self_hash(path: Path, payload: Mapping[str, Any], hash_key: str = "validation_json_hash") -> str:
    mutable = dict(payload)
    mutable.pop(hash_key, None)
    _write_json(path, mutable)
    return _sha256_file(path)


@dataclass(frozen=True)
class LiveViewableCapturePlan:
    status: str
    target_url: str
    output_dir: str
    device_profile: str
    capture_comments: bool
    write_wacz: bool
    write_warc: bool
    write_rendered_html: bool
    write_screenshots: bool
    write_validation_json: bool
    write_local_viewer: bool = False
    previous_accepted_archive_preserved: bool = True
    manual_next_steps: tuple[str, ...] = MANUAL_REPLAY_STEPS
    errors: tuple[str, ...] = ()
    schema_version: str = MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LiveViewableCaptureResult:
    status: str
    live_capture_started_at: str
    target_url: str
    output_dir: str
    browser_engine: str
    device_profile: str
    user_agent: str
    article_title_found: bool
    article_body_found: bool
    hero_image_found: bool
    comments_found: bool
    comment_count: int
    screenshots: Mapping[str, str]
    requested_target_url: str = ""
    runner_source_url: str = ""
    canonical_source_url: str = ""
    rendered_html_path: str = ""
    rendered_html_hash: str = ""
    warc_path: str = ""
    warc_hash: str = ""
    warc_gz_path: str = ""
    warc_gz_hash: str = ""
    wacz_path: str = ""
    wacz_hash: str = ""
    capture_manifest_path: str = ""
    capture_manifest_hash: str = ""
    validation_json_path: str = ""
    validation_json_hash: str = ""
    local_viewer_index_path: str = ""
    local_viewer_index_hash: str = ""
    local_viewer_manifest_path: str = ""
    local_viewer_open_cmd: str = ""
    local_viewer_edge_app_cmd: str = ""
    replay_tested: bool = False
    replay_result: str = REPLAY_RESULT_NOT_TESTED
    article_visible: str = "manual_review_required"
    comments_visible: str = "manual_review_required"
    slow_page_warning: str = "manual_review_required"
    privacy_modal: str = "manual_review_required"
    archived_page_not_found: str = "manual_review_required"
    notes: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    manual_next_steps: tuple[str, ...] = MANUAL_REPLAY_STEPS
    previous_accepted_archive_preserved: bool = True
    schema_version: str = MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def build_live_viewable_capture_plan(
    *,
    target_url: str,
    output_dir: str | Path,
    device_profile: str = DEFAULT_DEVICE_PROFILE,
    capture_comments: bool = True,
    write_wacz: bool = True,
    write_warc: bool = True,
    write_rendered_html: bool = True,
    write_screenshots: bool = True,
    write_validation_json: bool = True,
    write_local_viewer: bool = False,
) -> LiveViewableCapturePlan:
    errors: list[str] = []
    if not str(target_url or "").strip():
        errors.append("target URL is required")
    if not str(output_dir or "").strip():
        errors.append("new output directory is required")
    return LiveViewableCapturePlan(
        status=LIVE_VIEWABLE_CAPTURE_BLOCKED if errors else LIVE_VIEWABLE_CAPTURE_DRY_RUN,
        target_url=str(target_url or ""),
        output_dir=str(output_dir or ""),
        device_profile=device_profile,
        capture_comments=bool(capture_comments),
        write_wacz=bool(write_wacz),
        write_warc=bool(write_warc),
        write_rendered_html=bool(write_rendered_html),
        write_screenshots=bool(write_screenshots),
        write_validation_json=bool(write_validation_json),
        write_local_viewer=bool(write_local_viewer),
        errors=tuple(errors),
    )


def _ensure_output_dir(path: Path, *, allow_existing_output_dir: bool) -> None:
    if path.exists():
        if not path.is_dir():
            raise FileExistsError(f"output path exists and is not a directory: {path}")
        if any(path.iterdir()) and not allow_existing_output_dir:
            raise FileExistsError(
                "output directory already exists and is not empty; choose a new side-by-side folder "
                "or pass --allow-existing-output-dir"
            )
    path.mkdir(parents=True, exist_ok=True)


def _runtime_dependency_errors() -> tuple[str, ...]:
    missing = []
    if importlib.util.find_spec("playwright") is None:
        missing.append("playwright is not importable; install/configure Playwright before running live capture")
    if importlib.util.find_spec("warcio") is None:
        missing.append("warcio is not importable; install repository dependencies before writing WARC/WACZ outputs")
    return tuple(missing)


def _warc_request_path(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return path


def _write_minimal_rendered_page_warc(*, html_path: Path, target_url: str, destination: Path) -> tuple[str, str]:
    if not html_path.is_file():
        return "", ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite generated artifact: {destination}")
    html_bytes = html_path.read_bytes()
    request = (
        "WARC/1.0\r\n"
        "WARC-Type: request\r\n"
        f"WARC-Target-URI: {target_url.split('#', 1)[0]}\r\n"
        "Content-Type: application/http; msgtype=request\r\n\r\n"
        f"GET {_warc_request_path(target_url.split('#', 1)[0])} HTTP/1.1\r\n"
        f"Host: {urlsplit(target_url).netloc}\r\n\r\n"
    ).encode("utf-8")
    response_headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_bytes)}\r\n\r\n"
    ).encode("utf-8")
    response = (
        "WARC/1.0\r\n"
        "WARC-Type: response\r\n"
        f"WARC-Target-URI: {target_url.split('#', 1)[0]}\r\n"
        "Content-Type: application/http; msgtype=response\r\n\r\n"
    ).encode("utf-8") + response_headers + html_bytes
    destination.write_bytes(request + response)
    return str(destination), _sha256_file(destination)


def _copy_file(source: Path, destination: Path) -> tuple[str, str]:
    if not source.is_file():
        return "", ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite generated artifact: {destination}")
    shutil.copy2(source, destination)
    return str(destination), _sha256_file(destination)


def _gzip_file(source: Path, destination: Path) -> tuple[str, str]:
    if not source.is_file():
        return "", ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite generated artifact: {destination}")
    with source.open("rb") as src, gzip.open(destination, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return str(destination), _sha256_file(destination)


def _artifact_path_by_label(artifacts: Sequence[Any], fragment: str) -> str:
    needle = fragment.lower()
    for artifact in artifacts:
        data = artifact.to_dict() if hasattr(artifact, "to_dict") else dict(artifact)
        if needle in str(data.get("label") or "").lower():
            return str(data.get("path") or "")
    return ""


def _best_profile_name(summary: Mapping[str, Any]) -> str:
    best = summary.get("best_profile") if isinstance(summary.get("best_profile"), Mapping) else {}
    return str(best.get("profile_name") or "android_mobile_chromium")


def _best_profile(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    best = summary.get("best_profile")
    return best if isinstance(best, Mapping) else {}


def _build_capture_manifest(result: Any, normalized: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION,
        "target_url": normalized["target_url"],
        "requested_target_url": normalized.get("requested_target_url", normalized["target_url"]),
        "runner_source_url": normalized.get("runner_source_url", ""),
        "canonical_source_url": normalized.get("canonical_source_url", ""),
        "output_dir": normalized["output_dir"],
        "source_validation_manifest": str(getattr(result, "manifest_path", "")),
        "source_validation_manifest_sha256": str(getattr(result, "manifest_sha256", "")),
        "normalized_outputs": dict(normalized),
        "old_accepted_capture_preserved": True,
        "dynamic_replay_visual_success_claimed": False,
        "manual_replay_required": True,
    }


def _write_blocked_result(
    *,
    output_root: Path,
    requested_target_url: str,
    runner_source_url: str,
    device_profile: str,
    errors: Sequence[str],
    write_validation_json: bool,
    write_local_viewer: bool,
    notes: Sequence[str] = (),
) -> LiveViewableCaptureResult:
    validation_payload: dict[str, Any] = {
        "schema_version": MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION,
        "status": LIVE_VIEWABLE_CAPTURE_BLOCKED,
        "live_capture_started_at": _utc_now_iso(),
        "target_url": requested_target_url,
        "requested_target_url": requested_target_url,
        "runner_source_url": runner_source_url,
        "canonical_source_url": "",
        "output_dir": str(output_root),
        "browser_engine": "chromium",
        "device_profile": device_profile,
        "user_agent": "",
        "article_title_found": False,
        "article_body_found": False,
        "hero_image_found": False,
        "comments_found": False,
        "comment_count": 0,
        "screenshots": {},
        "replay_tested": False,
        "replay_result": REPLAY_RESULT_NOT_TESTED,
        "article_visible": "manual_review_required",
        "comments_visible": "manual_review_required",
        "slow_page_warning": "manual_review_required",
        "privacy_modal": "manual_review_required",
        "archived_page_not_found": "manual_review_required",
        "errors": list(errors),
        "notes": list(notes or ("Install/configure missing dependencies or fix the approved URL, then rerun the same command.",)),
        "manual_next_steps": list(MANUAL_REPLAY_STEPS),
        "previous_accepted_archive_preserved": True,
    }
    validation_json_path = ""
    validation_json_hash = ""
    if write_validation_json:
        validation_json_path = str(output_root / "validation.json")
        validation_payload["validation_json_path"] = validation_json_path
        validation_json_hash = _write_json_with_self_hash(Path(validation_json_path), validation_payload)
        validation_payload["validation_json_hash"] = validation_json_hash
    local_viewer_index_path = ""
    local_viewer_index_hash = ""
    local_viewer_manifest_path = ""
    local_viewer_open_cmd = ""
    local_viewer_edge_app_cmd = ""
    if write_local_viewer:
        viewer = write_local_webpage_viewer(capture_output_dir=output_root, source_url=requested_target_url)
        local_viewer_index_path = viewer.index_path
        local_viewer_index_hash = viewer.index_sha256
        local_viewer_manifest_path = viewer.manifest_path
        local_viewer_open_cmd = viewer.open_cmd_path
        local_viewer_edge_app_cmd = viewer.edge_app_cmd_path
        validation_payload.update(
            {
                "local_viewer_index_path": local_viewer_index_path,
                "local_viewer_index_hash": local_viewer_index_hash,
                "local_viewer_manifest_path": local_viewer_manifest_path,
                "local_viewer_open_cmd": local_viewer_open_cmd,
                "local_viewer_edge_app_cmd": local_viewer_edge_app_cmd,
            }
        )
        if write_validation_json and validation_json_path:
            validation_json_hash = _write_json_with_self_hash(Path(validation_json_path), validation_payload)
    return LiveViewableCaptureResult(
        status=LIVE_VIEWABLE_CAPTURE_BLOCKED,
        live_capture_started_at=str(validation_payload["live_capture_started_at"]),
        target_url=requested_target_url,
        requested_target_url=requested_target_url,
        runner_source_url=runner_source_url,
        output_dir=str(output_root),
        browser_engine="chromium",
        device_profile=device_profile,
        user_agent="",
        article_title_found=False,
        article_body_found=False,
        hero_image_found=False,
        comments_found=False,
        comment_count=0,
        screenshots={},
        validation_json_path=validation_json_path,
        validation_json_hash=validation_json_hash,
        local_viewer_index_path=local_viewer_index_path,
        local_viewer_index_hash=local_viewer_index_hash,
        local_viewer_manifest_path=local_viewer_manifest_path,
        local_viewer_open_cmd=local_viewer_open_cmd,
        local_viewer_edge_app_cmd=local_viewer_edge_app_cmd,
        errors=tuple(errors),
        notes=tuple(validation_payload["notes"]),
    )


def _normalize_outputs(
    *,
    validation_result: Any,
    output_root: Path,
    requested_target_url: str,
    runner_source_url: str,
    device_profile: str,
    write_rendered_html: bool,
    write_warc: bool,
    write_wacz: bool,
    write_screenshots: bool,
    write_validation_json: bool,
    write_local_viewer: bool,
    started_at: str,
) -> LiveViewableCaptureResult:
    summary = getattr(validation_result, "summary", {}) or {}
    best_profile = _best_profile(summary)
    source_capture_root = Path(str(getattr(validation_result, "output_directory", "")))
    profile_name = _best_profile_name(summary)
    profile_root = source_capture_root / profile_name
    artifacts = tuple(getattr(validation_result, "artifacts", ()) or ())

    rendered_html_path = ""
    rendered_html_hash = ""
    if write_rendered_html:
        rendered_html_path, rendered_html_hash = _copy_file(
            profile_root / "final_rendered_dom.html",
            output_root / "rendered-page.html",
        )

    warc_path = ""
    warc_hash = ""
    warc_gz_path = ""
    warc_gz_hash = ""
    warc_source = ""
    if write_warc:
        source_warc = source_capture_root / "local_web_archive" / "archive" / "data.warc"
        rendered_html_source = Path(rendered_html_path) if rendered_html_path else profile_root / "final_rendered_dom.html"
        if source_warc.is_file():
            warc_path, warc_hash = _copy_file(source_warc, output_root / "rendered-page.warc")
            warc_gz_path, warc_gz_hash = _gzip_file(source_warc, output_root / "rendered-page.warc.gz")
            warc_source = "captured_browser_warc"
        else:
            warc_path, warc_hash = _write_minimal_rendered_page_warc(html_path=rendered_html_source, target_url=runner_source_url, destination=output_root / "rendered-page.warc")
            warc_gz_path, warc_gz_hash = _gzip_file(Path(warc_path), output_root / "rendered-page.warc.gz") if warc_path else ("", "")
            warc_source = "rendered_html_fallback" if warc_path else "unavailable"

    wacz_path = ""
    wacz_hash = ""
    wacz_source = ""
    if write_wacz:
        source_wacz = source_capture_root / "local_web_archive" / "archive.wacz"
        wacz_path, wacz_hash = _copy_file(
            source_wacz,
            output_root / "archive.viewable-live-capture.wacz",
        )
        wacz_source = "captured_browser_wacz" if wacz_path else "unavailable"

    screenshot_outputs: dict[str, str] = {}
    if write_screenshots:
        screenshot_root = output_root / "screenshots"
        for key, fragment, filename in (
            ("article_top", "faithful_article", "article-top.png"),
            ("full_page", "faithful_full_page", "full-page.png"),
            ("comments_region", "faithful_comments", "comments-region.png"),
            ("full_comments_thread", "derived_comments_full_thread", "full-comments-thread.png"),
        ):
            source = _artifact_path_by_label(artifacts, fragment)
            if source:
                copied, _ = _copy_file(Path(source), screenshot_root / filename)
                screenshot_outputs[key] = copied

    comments_count = int(best_profile.get("comment_count") or summary.get("comment_count") or 0)
    canonical_source_url = str(getattr(validation_result, "canonical_url", "") or best_profile.get("final_url") or runner_source_url)
    validation_payload: dict[str, Any] = {
        "schema_version": MSN_LIVE_VIEWABLE_CAPTURE_SCHEMA_VERSION,
        "status": LIVE_VIEWABLE_CAPTURE_COMPLETED,
        "live_capture_started_at": started_at,
        "target_url": requested_target_url,
        "requested_target_url": requested_target_url,
        "runner_source_url": runner_source_url,
        "canonical_source_url": canonical_source_url,
        "output_dir": str(output_root),
        "browser_engine": "chromium",
        "device_profile": device_profile,
        "user_agent": "android-mobile profile from source_msn_rendered_browser_validation",
        "article_title_found": bool(best_profile.get("title")),
        "article_body_found": bool(int(best_profile.get("article_text_chars") or 0)),
        "hero_image_found": bool(screenshot_outputs.get("article_top")),
        "comments_found": comments_count > 0,
        "comment_count": comments_count,
        "screenshots": screenshot_outputs,
        "rendered_html_path": rendered_html_path,
        "rendered_html_hash": rendered_html_hash,
        "warc_path": warc_path,
        "warc_hash": warc_hash,
        "warc_gz_path": warc_gz_path,
        "warc_gz_hash": warc_gz_hash,
        "wacz_path": wacz_path,
        "wacz_hash": wacz_hash,
        "replay_tested": False,
        "replay_result": REPLAY_RESULT_NOT_TESTED,
        "article_visible": "manual_review_required",
        "comments_visible": "manual_review_required",
        "slow_page_warning": "manual_review_required",
        "privacy_modal": "manual_review_required",
        "archived_page_not_found": "manual_review_required",
        "rendered_output_status": "side_by_side_outputs_ready",
        "warc_source": warc_source,
        "wacz_source": wacz_source,
        "side_by_side_output_names": [name for name, value in {"rendered-page.html": rendered_html_path, "rendered-page.warc": warc_path, "rendered-page.warc.gz": warc_gz_path, "archive.viewable-live-capture.wacz": wacz_path}.items() if value],
        "notes": [
            "Live MSN capture workflow generated side-by-side outputs; manual ReplayWeb/browser validation is still required.",
            "No claim is made that the original dynamic WACZ replay is visually successful.",
        ],
        "manual_next_steps": list(MANUAL_REPLAY_STEPS),
        "previous_accepted_archive_preserved": True,
    }
    manifest_payload = _build_capture_manifest(validation_result, validation_payload)
    capture_manifest_path = output_root / "capture-manifest.json"
    capture_manifest_hash = _write_json(capture_manifest_path, manifest_payload)
    validation_payload["capture_manifest_path"] = str(capture_manifest_path)
    validation_payload["capture_manifest_hash"] = capture_manifest_hash

    validation_json_path = ""
    validation_json_hash = ""
    if write_validation_json:
        validation_json_path = str(output_root / "validation.json")
        validation_payload["validation_json_path"] = validation_json_path
        validation_json_hash = _write_json_with_self_hash(Path(validation_json_path), validation_payload)
        validation_payload["validation_json_hash"] = validation_json_hash
    local_viewer_index_path = ""
    local_viewer_index_hash = ""
    local_viewer_manifest_path = ""
    local_viewer_open_cmd = ""
    local_viewer_edge_app_cmd = ""
    if write_local_viewer:
        viewer = write_local_webpage_viewer(capture_output_dir=output_root, source_url=requested_target_url)
        local_viewer_index_path = viewer.index_path
        local_viewer_index_hash = viewer.index_sha256
        local_viewer_manifest_path = viewer.manifest_path
        local_viewer_open_cmd = viewer.open_cmd_path
        local_viewer_edge_app_cmd = viewer.edge_app_cmd_path
        validation_payload.update(
            {
                "local_viewer_index_path": local_viewer_index_path,
                "local_viewer_index_hash": local_viewer_index_hash,
                "local_viewer_manifest_path": local_viewer_manifest_path,
                "local_viewer_open_cmd": local_viewer_open_cmd,
                "local_viewer_edge_app_cmd": local_viewer_edge_app_cmd,
            }
        )
        if write_validation_json and validation_json_path:
            validation_json_hash = _write_json_with_self_hash(Path(validation_json_path), validation_payload)
    return LiveViewableCaptureResult(
        status=LIVE_VIEWABLE_CAPTURE_COMPLETED,
        live_capture_started_at=started_at,
        target_url=requested_target_url,
        output_dir=str(output_root),
        browser_engine="chromium",
        device_profile=device_profile,
        user_agent=str(validation_payload["user_agent"]),
        requested_target_url=requested_target_url,
        runner_source_url=runner_source_url,
        canonical_source_url=canonical_source_url,
        article_title_found=bool(validation_payload["article_title_found"]),
        article_body_found=bool(validation_payload["article_body_found"]),
        hero_image_found=bool(validation_payload["hero_image_found"]),
        comments_found=bool(validation_payload["comments_found"]),
        comment_count=comments_count,
        screenshots=screenshot_outputs,
        rendered_html_path=rendered_html_path,
        rendered_html_hash=rendered_html_hash,
        warc_path=warc_path,
        warc_hash=warc_hash,
        warc_gz_path=warc_gz_path,
        warc_gz_hash=warc_gz_hash,
        wacz_path=wacz_path,
        wacz_hash=wacz_hash,
        capture_manifest_path=str(capture_manifest_path),
        capture_manifest_hash=capture_manifest_hash,
        validation_json_path=validation_json_path,
        validation_json_hash=validation_json_hash,
        local_viewer_index_path=local_viewer_index_path,
        local_viewer_index_hash=local_viewer_index_hash,
        local_viewer_manifest_path=local_viewer_manifest_path,
        local_viewer_open_cmd=local_viewer_open_cmd,
        local_viewer_edge_app_cmd=local_viewer_edge_app_cmd,
        notes=tuple(validation_payload["notes"]),
    )


def run_live_viewable_capture(
    *,
    target_url: str,
    output_dir: str | Path,
    runner_source_url: str = "",
    device_profile: str = DEFAULT_DEVICE_PROFILE,
    capture_comments: bool = True,
    write_wacz: bool = True,
    write_warc: bool = True,
    write_rendered_html: bool = True,
    write_screenshots: bool = True,
    write_validation_json: bool = True,
    write_local_viewer: bool = False,
    dry_run: bool = False,
    allow_existing_output_dir: bool = False,
    headed: bool = False,
    dependency_check: Callable[[], tuple[str, ...]] = _runtime_dependency_errors,
    validation_runner: Callable[..., Any] | None = None,
) -> LiveViewableCapturePlan | LiveViewableCaptureResult:
    from source_msn_vertical_live_validation import DEFAULT_MSN_VERTICAL_URL

    requested_target_url = str(target_url or "")
    effective_runner_source_url = str(runner_source_url or DEFAULT_MSN_VERTICAL_URL)
    plan = build_live_viewable_capture_plan(
        target_url=requested_target_url,
        output_dir=output_dir,
        device_profile=device_profile,
        capture_comments=capture_comments,
        write_wacz=write_wacz,
        write_warc=write_warc,
        write_rendered_html=write_rendered_html,
        write_screenshots=write_screenshots,
        write_validation_json=write_validation_json,
        write_local_viewer=write_local_viewer,
    )
    if plan.errors or dry_run:
        return plan
    output_root = Path(output_dir)
    _ensure_output_dir(output_root, allow_existing_output_dir=allow_existing_output_dir)
    dependency_errors = dependency_check()
    if dependency_errors:
        return _write_blocked_result(
            output_root=output_root,
            requested_target_url=requested_target_url,
            runner_source_url=effective_runner_source_url,
            device_profile=device_profile,
            errors=dependency_errors,
            write_validation_json=write_validation_json,
            write_local_viewer=write_local_viewer,
            notes=("Install/configure missing browser/archive dependencies, then rerun the same command.",),
        )
    started_at = _utc_now_iso()
    if validation_runner is None:
        from source_msn_rendered_browser_validation import run_msn_rendered_browser_validation

        validation_runner = run_msn_rendered_browser_validation
    try:
        validation_result = validation_runner(
            source_url=effective_runner_source_url,
            output_directory=output_root / "browser_capture",
            headless=not headed,
        )
    except ValueError as error:
        return _write_blocked_result(
            output_root=output_root,
            requested_target_url=requested_target_url,
            runner_source_url=effective_runner_source_url,
            device_profile=device_profile,
            errors=(str(error),),
            write_validation_json=write_validation_json,
            write_local_viewer=write_local_viewer,
            notes=(
                "Rendered MSN validation rejected the configured URL. Confirm DEFAULT_MSN_VERTICAL_URL is the raw approved URL, then rerun.",
            ),
        )
    return _normalize_outputs(
        validation_result=validation_result,
        output_root=output_root,
        requested_target_url=requested_target_url,
        runner_source_url=effective_runner_source_url,
        device_profile=device_profile,
        write_rendered_html=write_rendered_html,
        write_warc=write_warc,
        write_wacz=write_wacz,
        write_screenshots=write_screenshots,
        write_validation_json=write_validation_json,
        write_local_viewer=write_local_viewer,
        started_at=started_at,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live MSN viewable recapture workflow for side-by-side local artifacts.")
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device-profile", default=DEFAULT_DEVICE_PROFILE, choices=("android-mobile", "desktop"))
    parser.add_argument("--capture-comments", action="store_true")
    parser.add_argument("--write-wacz", action="store_true")
    parser.add_argument("--write-warc", action="store_true")
    parser.add_argument("--write-rendered-html", action="store_true")
    parser.add_argument("--write-screenshots", action="store_true")
    parser.add_argument("--write-validation-json", action="store_true")
    parser.add_argument("--write-local-viewer", action="store_true")
    parser.add_argument("--dry-run", "--plan", action="store_true")
    parser.add_argument("--allow-existing-output-dir", action="store_true")
    parser.add_argument("--headed", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_live_viewable_capture(
        target_url=args.target_url,
        output_dir=args.output_dir,
        device_profile=args.device_profile,
        capture_comments=bool(args.capture_comments),
        write_wacz=bool(args.write_wacz),
        write_warc=bool(args.write_warc),
        write_rendered_html=bool(args.write_rendered_html),
        write_screenshots=bool(args.write_screenshots),
        write_validation_json=bool(args.write_validation_json),
        write_local_viewer=bool(args.write_local_viewer),
        dry_run=bool(args.dry_run),
        allow_existing_output_dir=bool(args.allow_existing_output_dir),
        headed=bool(args.headed),
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    if isinstance(result, LiveViewableCapturePlan):
        return 0 if not result.errors else 2
    return 0 if result.status == LIVE_VIEWABLE_CAPTURE_COMPLETED else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
