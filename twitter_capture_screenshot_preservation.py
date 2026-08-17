from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from twitter_browser_capture_strategy import canonicalize_browser_capture_url


TWITTER_CAPTURE_PRESERVATION_SCHEMA_VERSION = "twitter_capture_preservation.v77a"


@dataclass(frozen=True)
class TwitterFullPageCaptureStep:
    index: int
    x: int
    y: int
    viewport_width: int
    viewport_height: int
    capture_width: int
    capture_height: int
    overlap_top_px: int
    overlap_left_px: int
    filename: str
    completion_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterFullPageCapturePlan:
    schema_version: str
    source_url: str
    canonical_url: str
    page_width: int
    page_height: int
    viewport_width: int
    viewport_height: int
    overlap_px: int
    scroll_step_px: int
    total_steps: int
    steps: tuple[TwitterFullPageCaptureStep, ...]
    completion_boundary: str
    completion_boundary_reached: bool
    stable_output_dir_name: str
    reference_family: str
    implementation_note: str
    local_only: bool = True
    browser_extension_dependency_required: bool = False
    external_upload_performed: bool = False
    hidden_tracking_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterScreenshotArtifactReference:
    path: str
    filename: str
    mode: str
    sha256: str
    size_bytes: int
    source_url: str
    captured_at_utc: str
    rendered_dom_status: str
    exists: bool

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCursorContinuationProof:
    schema_version: str
    source_url: str
    canonical_url: str
    cursor_in: str
    cursor_out: str
    next_cursor: str
    next_cycle_action: str
    current_page_index: int
    soft_page_budget: int
    soft_page_budget_reached: bool
    rate_limit_remaining: int | None
    rate_limit_reset_epoch: int | None
    cooldown_until_epoch: int | None
    cooldown_respected: bool
    safe_to_continue: bool
    planned_output_dir_name: str
    no_live_browser_action: bool
    no_network_action: bool
    no_write_actions: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterCapturePreservationManifest:
    schema_version: str
    source_url: str
    canonical_url: str
    captured_at_utc: str
    rendered_dom_status: str
    archive_ready_output_folder: str
    viewport_screenshot: TwitterScreenshotArtifactReference | None
    full_page_screenshot: TwitterScreenshotArtifactReference | None
    rendered_dom_path: str
    rendered_dom_sha256: str
    scroll_plan: TwitterFullPageCapturePlan
    cursor_continuation: TwitterCursorContinuationProof
    screenshot_references: tuple[TwitterScreenshotArtifactReference, ...]
    media_urls: tuple[str, ...]
    warnings: tuple[str, ...]
    safe_to_continue: bool
    no_write_actions: bool
    browser_launch_performed: bool = False
    web_download_performed: bool = False
    media_download_performed: bool = False
    official_x_api_used: bool = False
    credential_automation_performed: bool = False
    captcha_bypass_performed: bool = False
    proxy_or_evasion_performed: bool = False

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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_twitter_output_dir_name(source_url: str, suffix: str = "v77a") -> str:
    parsed = urlsplit(canonicalize_browser_capture_url(source_url))
    host = re.sub(r"[^a-z0-9]+", "_", (parsed.netloc or "x").lower()).strip("_")
    path = re.sub(r"[^a-zA-Z0-9]+", "_", parsed.path.strip("/") or "source").strip("_").lower()
    if len(path) > 64:
        path = path[:64].rstrip("_")
    return "_".join(part for part in ("twitter_capture", host, path, suffix) if part)


def _axis_positions(total: int, viewport: int, overlap_px: int) -> tuple[int, ...]:
    total = max(1, int(total))
    viewport = max(1, int(viewport))
    overlap = max(0, min(int(overlap_px), viewport - 1))
    if total <= viewport:
        return (0,)
    step = max(1, viewport - overlap)
    last = max(0, total - viewport)
    positions: list[int] = []
    pos = 0
    while pos < last:
        positions.append(pos)
        pos += step
    positions.append(last)
    return tuple(dict.fromkeys(positions))


def plan_full_page_capture(
    *,
    source_url: str,
    page_width: int,
    page_height: int,
    viewport_width: int,
    viewport_height: int,
    overlap_px: int = 160,
) -> TwitterFullPageCapturePlan:
    canonical = canonicalize_browser_capture_url(source_url)
    x_positions = _axis_positions(page_width, viewport_width, 0)
    y_positions = _axis_positions(page_height, viewport_height, overlap_px)
    total_steps = len(x_positions) * len(y_positions)
    steps: list[TwitterFullPageCaptureStep] = []
    index = 1
    for y in y_positions:
        for x in x_positions:
            capture_width = min(viewport_width, max(1, page_width - x))
            capture_height = min(viewport_height, max(1, page_height - y))
            steps.append(
                TwitterFullPageCaptureStep(
                    index=index,
                    x=x,
                    y=y,
                    viewport_width=int(viewport_width),
                    viewport_height=int(viewport_height),
                    capture_width=int(capture_width),
                    capture_height=int(capture_height),
                    overlap_top_px=0 if y == 0 else int(overlap_px),
                    overlap_left_px=0,
                    filename=f"screenshots/full_page_step_{index:04d}_x{x:06d}_y{y:06d}.png",
                    completion_fraction=round(index / max(1, total_steps), 6),
                )
            )
            index += 1
    last = steps[-1]
    boundary_reached = (last.y + last.capture_height) >= int(page_height) and (last.x + last.capture_width) >= int(page_width)
    return TwitterFullPageCapturePlan(
        schema_version=TWITTER_CAPTURE_PRESERVATION_SCHEMA_VERSION,
        source_url=str(source_url),
        canonical_url=canonical,
        page_width=int(page_width),
        page_height=int(page_height),
        viewport_width=int(viewport_width),
        viewport_height=int(viewport_height),
        overlap_px=int(overlap_px),
        scroll_step_px=max(1, int(viewport_height) - max(0, min(int(overlap_px), int(viewport_height) - 1))),
        total_steps=total_steps,
        steps=tuple(steps),
        completion_boundary="last_step_clamped_to_page_bottom_and_right_edge",
        completion_boundary_reached=boundary_reached,
        stable_output_dir_name=stable_twitter_output_dir_name(source_url),
        reference_family="GoFullPage/PageCap/webshot-style viewport stepping reimplemented in YTCE",
        implementation_note="Independent Python planner: computes scroll positions, overlap, stable filenames, and completion metadata; it does not copy extension code or assets.",
    )


def build_screenshot_artifact_reference(
    path: str | Path,
    *,
    source_url: str,
    mode: str,
    rendered_dom_status: str,
    captured_at_utc: str | None = None,
) -> TwitterScreenshotArtifactReference:
    p = Path(path)
    exists = p.is_file()
    data = p.read_bytes() if exists else b""
    return TwitterScreenshotArtifactReference(
        path=str(p),
        filename=p.name,
        mode=str(mode),
        sha256=hashlib.sha256(data).hexdigest() if data else "",
        size_bytes=len(data),
        source_url=str(source_url),
        captured_at_utc=captured_at_utc or utc_now_iso(),
        rendered_dom_status=str(rendered_dom_status),
        exists=exists,
    )


def build_cursor_continuation_proof(
    *,
    source_url: str,
    cursor_state: Mapping[str, Any],
    now_epoch: int,
) -> TwitterCursorContinuationProof:
    canonical = canonicalize_browser_capture_url(source_url)
    page_index = int(cursor_state.get("pages_count") or cursor_state.get("page_index") or 0)
    soft_budget = int(cursor_state.get("soft_page_budget") or 0)
    cursor_in = str(cursor_state.get("cursor_in") or "")
    cursor_out = str(cursor_state.get("last_cursor_out") or cursor_state.get("cursor_out") or "")
    next_cursor = str(cursor_state.get("next_cursor") or cursor_out or cursor_in)
    remaining_raw = cursor_state.get("rate_limit_remaining")
    remaining = int(remaining_raw) if remaining_raw is not None and str(remaining_raw) != "" else None
    reset_raw = cursor_state.get("rate_limit_reset_epoch")
    reset_epoch = int(reset_raw) if reset_raw is not None and str(reset_raw) != "" else None
    cooldown_raw = cursor_state.get("cooldown_until_epoch") or (reset_epoch if remaining is not None and remaining <= 0 else None)
    cooldown_until = int(cooldown_raw) if cooldown_raw is not None and str(cooldown_raw) != "" else None
    soft_reached = bool(soft_budget and page_index >= soft_budget)
    cooldown_active = bool(cooldown_until and cooldown_until > int(now_epoch))
    safe = bool(next_cursor) and not soft_reached and not cooldown_active
    warnings: list[str] = []
    if soft_reached:
        warnings.append("soft_page_budget_pause_boundary")
    if cooldown_active:
        warnings.append("cooldown_until_reset_boundary")
    if not next_cursor:
        warnings.append("no_next_cursor_available")
    return TwitterCursorContinuationProof(
        schema_version=TWITTER_CAPTURE_PRESERVATION_SCHEMA_VERSION,
        source_url=str(source_url),
        canonical_url=canonical,
        cursor_in=cursor_in,
        cursor_out=cursor_out,
        next_cursor=next_cursor,
        next_cycle_action="plan_next_browser_session_cursor_request" if safe else "pause_or_stop_before_next_request",
        current_page_index=page_index,
        soft_page_budget=soft_budget,
        soft_page_budget_reached=soft_reached,
        rate_limit_remaining=remaining,
        rate_limit_reset_epoch=reset_epoch,
        cooldown_until_epoch=cooldown_until,
        cooldown_respected=not cooldown_active,
        safe_to_continue=safe,
        planned_output_dir_name=stable_twitter_output_dir_name(source_url, suffix=f"cursor_{page_index + 1:04d}"),
        no_live_browser_action=True,
        no_network_action=True,
        no_write_actions=True,
        warnings=tuple(warnings),
    )


def build_reference_family_capture_matrix() -> tuple[dict[str, Any], ...]:
    return (
        {
            "reference_family": "GoFullPage / mrcoles full-page screen capture",
            "useful_behavior_reimplemented": (
                "page_dimension_sampling",
                "viewport_scroll_step_planning",
                "overlap_padding",
                "edge_clamping",
                "completion_fraction",
                "stable_tile_filenames",
            ),
            "copied_code_or_assets": False,
            "status": "REIMPLEMENTED_PROOF",
        },
        {
            "reference_family": "PageCap / webshot-style capture",
            "useful_behavior_reimplemented": (
                "local_artifact_manifest",
                "rendered_dom_status_field",
                "archive_ready_output_folder",
                "hash_and_size_metadata",
            ),
            "copied_code_or_assets": False,
            "status": "REIMPLEMENTED_PROOF",
        },
    )


def build_twitter_exporter_safety_matrix() -> tuple[dict[str, Any], ...]:
    safe = ("export_summary", "cooldown_state", "resumable_cursor_state", "local_only_storage", "json_manifest_output")
    forbidden = ("posting", "deleting", "liking", "following", "unfollowing", "dm_access", "captcha_bypass", "credential_automation", "proxy_or_evasion")
    safe_rows = tuple({"capability": item, "implemented_as": "read_only_planning_or_manifest_state", "safe": True} for item in safe)
    forbidden_rows = tuple({"capability": item, "implemented_as": "not_implemented", "safe": False, "status": "UNSAFE_OUT_OF_SCOPE"} for item in forbidden)
    return safe_rows + forbidden_rows


def build_capture_preservation_manifest(
    *,
    source_url: str,
    output_folder: str | Path,
    page_width: int,
    page_height: int,
    viewport_width: int,
    viewport_height: int,
    cursor_state: Mapping[str, Any],
    now_epoch: int,
    rendered_dom_path: str | Path | None = None,
    viewport_screenshot_path: str | Path | None = None,
    full_page_screenshot_path: str | Path | None = None,
    media_urls: Sequence[str] = (),
    rendered_dom_status: str = "rendered_dom_fallback_planned_or_available",
) -> TwitterCapturePreservationManifest:
    captured_at = utc_now_iso()
    plan = plan_full_page_capture(
        source_url=source_url,
        page_width=page_width,
        page_height=page_height,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )
    cursor = build_cursor_continuation_proof(source_url=source_url, cursor_state=cursor_state, now_epoch=now_epoch)
    references: list[TwitterScreenshotArtifactReference] = []
    viewport_ref = None
    full_ref = None
    if viewport_screenshot_path:
        viewport_ref = build_screenshot_artifact_reference(viewport_screenshot_path, source_url=source_url, mode="viewport", rendered_dom_status=rendered_dom_status, captured_at_utc=captured_at)
        references.append(viewport_ref)
    if full_page_screenshot_path:
        full_ref = build_screenshot_artifact_reference(full_page_screenshot_path, source_url=source_url, mode="full_page", rendered_dom_status=rendered_dom_status, captured_at_utc=captured_at)
        references.append(full_ref)
    dom_path = Path(rendered_dom_path) if rendered_dom_path else None
    dom_bytes = dom_path.read_bytes() if dom_path and dom_path.is_file() else b""
    warnings: list[str] = []
    if not references:
        warnings.append("no_screenshot_artifacts_available")
    if not dom_bytes:
        warnings.append("rendered_dom_artifact_missing")
    return TwitterCapturePreservationManifest(
        schema_version=TWITTER_CAPTURE_PRESERVATION_SCHEMA_VERSION,
        source_url=str(source_url),
        canonical_url=canonicalize_browser_capture_url(source_url),
        captured_at_utc=captured_at,
        rendered_dom_status=str(rendered_dom_status),
        archive_ready_output_folder=str(Path(output_folder)),
        viewport_screenshot=viewport_ref,
        full_page_screenshot=full_ref,
        rendered_dom_path=str(dom_path) if dom_path else "",
        rendered_dom_sha256=hashlib.sha256(dom_bytes).hexdigest() if dom_bytes else "",
        scroll_plan=plan,
        cursor_continuation=cursor,
        screenshot_references=tuple(references),
        media_urls=tuple(str(url) for url in media_urls),
        warnings=tuple(warnings + list(cursor.warnings)),
        safe_to_continue=cursor.safe_to_continue,
        no_write_actions=True,
    )


def render_capture_preservation_summary(manifest: TwitterCapturePreservationManifest) -> str:
    lines = [
        "TWITTER/X CAPTURE PRESERVATION V77A",
        f"source_url: {manifest.source_url}",
        f"canonical_url: {manifest.canonical_url}",
        f"rendered_dom_status: {manifest.rendered_dom_status}",
        f"scroll_steps: {manifest.scroll_plan.total_steps}",
        f"cursor_next_action: {manifest.cursor_continuation.next_cycle_action}",
        f"safe_to_continue: {manifest.safe_to_continue}",
        f"no_write_actions: {manifest.no_write_actions}",
        f"browser_launch_performed: {manifest.browser_launch_performed}",
        f"web_download_performed: {manifest.web_download_performed}",
        f"media_download_performed: {manifest.media_download_performed}",
        f"official_x_api_used: {manifest.official_x_api_used}",
    ]
    if manifest.warnings:
        lines.append("warnings: " + ", ".join(manifest.warnings))
    else:
        lines.append("warnings: NONE")
    return "\n".join(lines)


def write_manifest_json(path: str | Path, manifest: TwitterCapturePreservationManifest) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output
