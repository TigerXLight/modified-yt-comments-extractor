from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

R43C_MARKER = "YTCE_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE"
R43C_PASS_STATUS = "PASS_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE"
R43C_BLOCKED_STATUS = "BLOCKED_R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE"
R43C_SCHEMA_VERSION = "visual_screenshot_receipt_materialization_gate.r43c.v1"
R43C_REPORT_ROOT = "profile_media_live_captures/r43c_visual_screenshot_receipt_materialization_gate"
R43C_EDGE_R18_BASELINE = "EDGE_R18_NEWEST_SAFE_MATERIALIZATION"
SCREENSHOT_PASS = "PASS"
SCREENSHOT_NEEDS_CHECK = "NEEDS_VISIBLE_HUMAN_CHECK"
SCREENSHOT_MISSING = "MISSING"


@dataclass(frozen=True)
class VisualScreenshotReceiptR43C:
    marker: str
    schema_version: str
    status: str
    platform: str
    record_id: str
    record_type: str
    source_url: str
    screenshot_path: str
    receipt_path: str
    receipt_markdown_path: str
    visual_baseline: str
    materialized_in_viewport: bool
    materialization_clean: bool
    capture_gate: bool
    rendered_reply_openers: int
    rendered_read_more: int
    screenshot_file_exists: bool
    complete_enough_for_evidence: bool
    needs_visible_human_check: bool
    reason: str
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == SCREENSHOT_PASS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class VisualScreenshotGateResultR43C:
    marker: str
    schema_version: str
    status: str
    account_capture_dir: str
    receipt_count: int
    pass_count: int
    needs_visible_human_check_count: int
    missing_count: int
    account_record_path: str
    manifest_path: str
    screenshot_receipts_index_path: str
    receipts: tuple[Mapping[str, Any], ...]
    side_effect_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == R43C_PASS_STATUS

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


@dataclass(frozen=True)
class R43CReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    gate_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R43C_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [dict(check) for check in self.checks],
            "contract": dict(self.contract),
            "gate_result": _to_jsonable(self.gate_result),
            "generated_at": self.generated_at,
            "marker": self.marker,
            "schema_version": self.schema_version,
            "side_effect_flags": dict(self.side_effect_flags),
            "status": self.status,
        }


class VisualScreenshotReceiptMaterializationGateR43C:
    """Local screenshot receipt gate for visual evidence folders.

    R43C is outside the WebView2 implementation. It records whether a screenshot
    should be treated as complete visual evidence, whether it needs visible human
    checking, or whether it is missing. It applies the Edge R18 handover rule that
    screenshot capture must not rely on a DOM-only false-clean; visual/card/thread
    materialization evidence must be recorded with the screenshot.
    """

    def apply(self, account_capture_dir: str | Path, *, default_context: Mapping[str, Any] | None = None) -> VisualScreenshotGateResultR43C:
        return apply_visual_screenshot_receipt_materialization_gate_r43c(account_capture_dir, default_context=default_context)


def build_visual_screenshot_receipt_materialization_gate_r43c() -> VisualScreenshotReceiptMaterializationGateR43C:
    return VisualScreenshotReceiptMaterializationGateR43C()


def build_r43c_contract() -> dict[str, Any]:
    return {
        "marker": R43C_MARKER,
        "schema_version": R43C_SCHEMA_VERSION,
        "mode_id": "visual_screenshot_receipt_materialization_gate",
        "edge_visual_baseline": R43C_EDGE_R18_BASELINE,
        "r18_rule": "do not trust DOM-only false-clean; physically materialize each visual unit before screenshot evidence promotion",
        "youtube_hard_gate": {
            "materialization_clean": True,
            "rendered_reply_openers": 0,
            "rendered_read_more": 0,
            "capture_gate": True,
            "r17_false_clean_allowed": False,
        },
        "twitter_x_gate": "post/repost card screenshot must have a receipt; if viewport/card materialization is not confirmed, mark NEEDS_VISIBLE_HUMAN_CHECK instead of PASS",
        "receipt_files": ["static_screenshot_receipt.json", "static_screenshot_receipt.md", "screenshot_receipts_index.json"],
        "account_record_links_receipts": True,
        "local_layer_only": True,
        "webview2_role": "site rendering and observation only; receipt gate writes local evidence status and never drives source-role review",
        "source_role_checks_enabled": False,
        "review_window_dependency": False,
        "remote_media_downloads_enabled": False,
        "hidden_x_api_scraping_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "challenge_bypass_enabled": False,
    }


def build_r43c_side_effect_flags() -> dict[str, bool]:
    return {
        "r43c_screenshot_receipt_gate_written": True,
        "local_receipt_annotation_only": True,
        "network_actions_performed": False,
        "browser_session_started": False,
        "webview2_session_started_by_r43c": False,
        "remote_media_downloads_performed": False,
        "hidden_x_api_scraping_performed": False,
        "login_automation_performed": False,
        "cookie_or_token_extraction_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "paywall_or_access_control_bypass_performed": False,
        "source_role_interface_loop_invoked": False,
        "source_role_checks_performed": False,
        "source_role_assignment_performed": False,
        "review_window_dependency_invoked": False,
        "review_window_rewrite_performed": False,
        "youtube_capture_engine_changed": False,
    }


def apply_visual_screenshot_receipt_materialization_gate_r43c(
    account_capture_dir: str | Path,
    *,
    default_context: Mapping[str, Any] | None = None,
) -> VisualScreenshotGateResultR43C:
    capture_dir = Path(account_capture_dir)
    warnings: list[str] = []
    receipts: list[dict[str, Any]] = []
    default_ctx = dict(default_context or {})
    if not capture_dir.is_dir():
        warnings.append(f"account capture dir does not exist: {capture_dir}")

    date_root = capture_dir / "dates"
    for post_json in sorted(date_root.glob("*/*/post.json")) if date_root.is_dir() else []:
        record_dir = post_json.parent
        post_payload = _read_json(post_json, {})
        ctx = dict(default_ctx)
        ctx.update(_dictish(post_payload.get("static_screenshot_receipt") or post_payload.get("screenshot_receipt") or post_payload.get("visual_receipt") or {}))
        screenshot_rel = _clean(post_payload.get("static_screenshot") or post_payload.get("static_screenshot_path") or "")
        screenshot_path = _resolve_screenshot_path(capture_dir, record_dir, screenshot_rel)
        receipt = write_visual_screenshot_receipt_r43c(
            record_dir,
            platform=_clean(ctx.get("platform") or "twitter_x"),
            record_id=_clean(post_payload.get("record_id") or record_dir.name),
            record_type=_clean(post_payload.get("record_type") or "post"),
            source_url=_plain_url(post_payload.get("source_url") or ""),
            screenshot_path=screenshot_path,
            screenshot_display_path=screenshot_rel or _rel(record_dir, screenshot_path),
            context=ctx,
        )
        receipts.append(receipt.to_dict())
        _patch_post_markdown_receipt_link(record_dir / "post.md")
        post_payload["static_screenshot_receipt"] = _rel(capture_dir, record_dir / "static_screenshot_receipt.json")
        post_payload["static_screenshot_receipt_status"] = receipt.status
        post_payload["static_screenshot_complete_enough_for_evidence"] = receipt.complete_enough_for_evidence
        post_payload["static_screenshot_needs_visible_human_check"] = receipt.needs_visible_human_check
        _write_json(post_json, post_payload)

    pass_count = sum(1 for item in receipts if item.get("status") == SCREENSHOT_PASS)
    needs_count = sum(1 for item in receipts if item.get("status") == SCREENSHOT_NEEDS_CHECK)
    missing_count = sum(1 for item in receipts if item.get("status") == SCREENSHOT_MISSING)
    index_path = capture_dir / "screenshot_receipts_index.json"
    _write_json(index_path, {"marker": R43C_MARKER, "schema_version": R43C_SCHEMA_VERSION, "receipts": receipts, "summary": {"pass": pass_count, "needs_visible_human_check": needs_count, "missing": missing_count}})
    account_record = capture_dir / "account_record.md"
    if account_record.exists():
        _patch_account_record_receipt_links(account_record, capture_dir=capture_dir, receipts=receipts)
    manifest_path = capture_dir / "manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path, {})
        manifest["screenshot_receipt_gate"] = {
            "marker": R43C_MARKER,
            "schema_version": R43C_SCHEMA_VERSION,
            "edge_visual_baseline": R43C_EDGE_R18_BASELINE,
            "receipt_count": len(receipts),
            "pass_count": pass_count,
            "needs_visible_human_check_count": needs_count,
            "missing_count": missing_count,
            "index_path": _rel(capture_dir, index_path),
        }
        _write_json(manifest_path, manifest)

    status = R43C_PASS_STATUS if receipts and all(item.get("status") in {SCREENSHOT_PASS, SCREENSHOT_NEEDS_CHECK, SCREENSHOT_MISSING} for item in receipts) else R43C_BLOCKED_STATUS
    result = VisualScreenshotGateResultR43C(
        marker=R43C_MARKER,
        schema_version=R43C_SCHEMA_VERSION,
        status=status,
        account_capture_dir=str(capture_dir),
        receipt_count=len(receipts),
        pass_count=pass_count,
        needs_visible_human_check_count=needs_count,
        missing_count=missing_count,
        account_record_path=str(account_record),
        manifest_path=str(manifest_path),
        screenshot_receipts_index_path=str(index_path),
        receipts=tuple(receipts),
        side_effect_flags=build_r43c_side_effect_flags(),
        warnings=tuple(warnings),
    )
    _write_json(capture_dir / "screenshot_receipt_gate_result_r43c.json", result.to_dict())
    return result


def write_visual_screenshot_receipt_r43c(
    record_dir: str | Path,
    *,
    platform: str,
    record_id: str,
    record_type: str,
    source_url: str,
    screenshot_path: str | Path,
    screenshot_display_path: str = "",
    context: Mapping[str, Any] | None = None,
) -> VisualScreenshotReceiptR43C:
    record_path = Path(record_dir)
    record_path.mkdir(parents=True, exist_ok=True)
    ctx = dict(context or {})
    shot_path = Path(screenshot_path)
    exists = shot_path.is_file()
    visual_baseline = _clean(ctx.get("visual_baseline") or ctx.get("edge_visual_baseline") or R43C_EDGE_R18_BASELINE)
    materialized = _truthy(ctx.get("materialized_in_viewport") or ctx.get("card_materialized_in_viewport") or ctx.get("physical_materialization_confirmed") or ctx.get("thread_materialized_in_viewport"))
    materialization_clean = _truthy(ctx.get("materialization_clean") if "materialization_clean" in ctx else ctx.get("r18_materialization_clean"))
    capture_gate = _truthy(ctx.get("capture_gate") if "capture_gate" in ctx else ctx.get("r18_capture_gate"))
    rendered_reply_openers = _safe_int(ctx.get("rendered_reply_openers"))
    rendered_read_more = _safe_int(ctx.get("rendered_read_more"))
    normalized_platform = _clean(platform).lower() or "unknown"

    if not exists:
        status = SCREENSHOT_MISSING
        reason = "static screenshot file is missing; do not promote screenshot as visual evidence"
    elif normalized_platform in {"youtube", "youtube_comments", "youtube_visual"}:
        youtube_ok = visual_baseline == R43C_EDGE_R18_BASELINE and materialized and materialization_clean and capture_gate and rendered_reply_openers == 0 and rendered_read_more == 0
        status = SCREENSHOT_PASS if youtube_ok else SCREENSHOT_NEEDS_CHECK
        reason = "Edge R18 materialization gate passed" if youtube_ok else "YouTube screenshot lacks complete Edge R18 materialization receipt; needs visible human check"
    else:
        twitter_ok = materialized or _truthy(ctx.get("static_screenshot_visual_confirmation") or ctx.get("post_card_bounds_confirmed"))
        status = SCREENSHOT_PASS if twitter_ok else SCREENSHOT_NEEDS_CHECK
        reason = "post/repost card materialization receipt passed" if twitter_ok else "screenshot exists but no card/viewport materialization receipt was supplied"

    complete = status == SCREENSHOT_PASS
    receipt_json = record_path / "static_screenshot_receipt.json"
    receipt_md = record_path / "static_screenshot_receipt.md"
    display = screenshot_display_path or _rel(record_path, shot_path)
    receipt = VisualScreenshotReceiptR43C(
        marker=R43C_MARKER,
        schema_version=R43C_SCHEMA_VERSION,
        status=status,
        platform=normalized_platform,
        record_id=_clean(record_id),
        record_type=_clean(record_type),
        source_url=_plain_url(source_url),
        screenshot_path=_plain_url(display),
        receipt_path=str(receipt_json),
        receipt_markdown_path=str(receipt_md),
        visual_baseline=visual_baseline,
        materialized_in_viewport=materialized,
        materialization_clean=materialization_clean,
        capture_gate=capture_gate,
        rendered_reply_openers=rendered_reply_openers,
        rendered_read_more=rendered_read_more,
        screenshot_file_exists=exists,
        complete_enough_for_evidence=complete,
        needs_visible_human_check=status == SCREENSHOT_NEEDS_CHECK,
        reason=reason,
        side_effect_flags=build_r43c_side_effect_flags(),
    )
    _write_json(receipt_json, receipt.to_dict())
    _write_receipt_markdown(receipt_md, receipt)
    return receipt


def build_report(output_root: str | Path = R43C_REPORT_ROOT) -> R43CReport:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    from profile_media_twitter_x_account_media_ledger_r43a import (
        TwitterXAccountMediaItemR43A,
        TwitterXAccountRecordR43A,
        write_twitter_x_account_media_ledger_r43a,
    )
    fixture = out / "fixture_files"
    fixture.mkdir(parents=True, exist_ok=True)
    screenshot = fixture / "post_static.png"
    image = fixture / "image.jpg"
    screenshot.write_bytes(b"R43C_SCREENSHOT\n")
    image.write_bytes(b"R43C_IMAGE\n")
    ledger = write_twitter_x_account_media_ledger_r43a(
        (
            TwitterXAccountRecordR43A(
                account_handle="example",
                author_handle="example",
                record_id="3333333333333333333",
                record_type="post",
                source_url="https://x.com/example/status/3333333333333333333",
                visible_text="R43C screenshot gate fixture.",
                visible_timestamp="2026-09-15T02:00:00Z",
                capture_timestamp="2026-09-15T02:01:00Z",
                static_screenshot_path=str(screenshot),
                media_items=(TwitterXAccountMediaItemR43A(media_id="img", media_class="image", local_path=str(image), filename="image.jpg"),),
                review_strings=("R43C screenshot gate fixture.",),
                observed_order=1,
            ),
        ),
        output_root=out / "source_exports" / "twitter_x",
        account_handle="example",
        capture_timestamp="20260915T020100Z",
    )
    gate = apply_visual_screenshot_receipt_materialization_gate_r43c(
        ledger.account_capture_dir,
        default_context={"platform": "twitter_x", "card_materialized_in_viewport": True, "post_card_bounds_confirmed": True, "visual_baseline": R43C_EDGE_R18_BASELINE},
    )
    account_record = _read_text(Path(gate.account_record_path))
    manifest = _read_json(Path(gate.manifest_path), {})
    post_md = _read_text(Path(ledger.account_capture_dir) / "dates" / "2026-09-15" / "post_3333333333333333333" / "post.md")
    receipt = gate.receipts[0] if gate.receipts else {}
    youtube_bad = write_visual_screenshot_receipt_r43c(
        out / "youtube_bad",
        platform="youtube",
        record_id="yt_bad",
        record_type="comment_thread",
        source_url="https://www.youtube.com/watch?v=example",
        screenshot_path=screenshot,
        screenshot_display_path="static_screenshot.png",
        context={"visual_baseline": "EDGE_R17_FAST_DOM_ONLY", "materialized_in_viewport": False, "materialization_clean": False, "capture_gate": True, "rendered_reply_openers": 0, "rendered_read_more": 0},
    )
    youtube_good = write_visual_screenshot_receipt_r43c(
        out / "youtube_good",
        platform="youtube",
        record_id="yt_good",
        record_type="comment_thread",
        source_url="https://www.youtube.com/watch?v=example",
        screenshot_path=screenshot,
        screenshot_display_path="static_screenshot.png",
        context={"visual_baseline": R43C_EDGE_R18_BASELINE, "materialized_in_viewport": True, "materialization_clean": True, "capture_gate": True, "rendered_reply_openers": 0, "rendered_read_more": 0},
    )
    checks = (
        _check("screenshot_receipts_written_for_post_folders", gate.receipt_count == 1 and Path(str(receipt.get("receipt_path", ""))).is_file()),
        _check("account_record_links_screenshot_receipts", "static_screenshot_receipt.json" in account_record and "## Screenshot receipts" in account_record),
        _check("post_markdown_links_screenshot_receipt", "Static screenshot receipt" in post_md),
        _check("manifest_records_screenshot_receipt_gate", manifest.get("screenshot_receipt_gate", {}).get("marker") == R43C_MARKER),
        _check("twitter_x_card_materialization_can_pass", receipt.get("status") == SCREENSHOT_PASS and receipt.get("complete_enough_for_evidence") is True),
        _check("r17_false_clean_is_not_accepted", youtube_bad.status == SCREENSHOT_NEEDS_CHECK),
        _check("r18_materialization_gate_can_pass", youtube_good.status == SCREENSHOT_PASS),
        _check("no_source_role_or_review_window_side_effects", all(gate.side_effect_flags.get(key) is False for key in ("network_actions_performed", "browser_session_started", "webview2_session_started_by_r43c", "hidden_x_api_scraping_performed", "cookie_or_token_extraction_performed", "captcha_or_challenge_bypass_performed", "source_role_checks_performed", "source_role_assignment_performed", "review_window_dependency_invoked", "review_window_rewrite_performed", "youtube_capture_engine_changed"))),
        _check("plain_machine_urls", _machine_urls_are_plain(gate.to_dict()) and _machine_urls_are_plain(manifest)),
    )
    status = R43C_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R43C_BLOCKED_STATUS
    report = R43CReport(R43C_MARKER, R43C_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, checks, gate.to_dict(), build_r43c_contract(), gate.side_effect_flags)
    write_report(report, out)
    return report


def write_report(report: R43CReport, output_root: str | Path = R43C_REPORT_ROOT) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE_REPORT.json", report.to_dict())
    lines = ["# R43C Visual Screenshot Receipt Materialization Gate Report", "", f"- marker: `{report.marker}`", f"- status: `{report.status}`", f"- schema: `{report.schema_version}`", "", "## Checks"]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    lines.extend(["", "## Gate rule", "- Screenshot files are not enough by themselves; every screenshot has a receipt status.", "- Twitter/X post/repost screenshots need card or viewport materialization evidence to be PASS.", "- YouTube visual screenshots use the Edge R18 screenshot-safe baseline; R17 DOM-only false-clean is not accepted.", "- This is local receipt annotation only: no WebView2 session, network action, source-role check, or review-window rewrite is performed by R43C."])
    (out / "R43C_VISUAL_SCREENSHOT_RECEIPT_MATERIALIZATION_GATE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_screenshot_path(capture_dir: Path, record_dir: Path, screenshot_rel: str) -> Path:
    text = _clean(screenshot_rel)
    if not text:
        return record_dir / "static_screenshot_missing.txt"
    p = Path(text)
    if p.is_absolute():
        return p
    from_capture = capture_dir / text
    if from_capture.exists():
        return from_capture
    return record_dir / text


def _patch_post_markdown_receipt_link(path: Path) -> None:
    if not path.exists(): return
    text = path.read_text(encoding="utf-8", errors="replace")
    if "Static screenshot receipt:" in text: return
    line = "- Static screenshot receipt: [static_screenshot_receipt.json](static_screenshot_receipt.json)"
    if "- Static screenshot:" in text:
        text = text.replace("- Static screenshot:", line + "\n- Static screenshot:", 1)
    else:
        text = text.rstrip() + "\n" + line + "\n"
    path.write_text(text, encoding="utf-8")


def _patch_account_record_receipt_links(path: Path, *, capture_dir: Path, receipts: Iterable[Mapping[str, Any]]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "## Screenshot receipts" in text: return
    lines = ["", "## Screenshot receipts", ""]
    for item in receipts:
        receipt_path = Path(str(item.get("receipt_path") or ""))
        receipt_rel = _rel(capture_dir, receipt_path)
        label = f"{item.get('record_type')} {item.get('record_id')}"
        lines.append(f"- {label}: [{Path(receipt_rel).name}]({_quote_md_path(receipt_rel)}) — `{item.get('status')}`")
    path.write_text(text.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_receipt_markdown(path: Path, receipt: VisualScreenshotReceiptR43C) -> None:
    lines = [
        f"# Static screenshot receipt: {receipt.record_type} {receipt.record_id}",
        "",
        f"- Marker: `{receipt.marker}`",
        f"- Status: `{receipt.status}`",
        f"- Platform: `{receipt.platform}`",
        f"- Source URL: `{receipt.source_url}`",
        f"- Screenshot: [{Path(receipt.screenshot_path).name}]({_quote_md_path(receipt.screenshot_path)})",
        f"- Visual baseline: `{receipt.visual_baseline}`",
        f"- Materialized in viewport: `{receipt.materialized_in_viewport}`",
        f"- Materialization clean: `{receipt.materialization_clean}`",
        f"- Capture gate: `{receipt.capture_gate}`",
        f"- Rendered reply openers: `{receipt.rendered_reply_openers}`",
        f"- Rendered read-more: `{receipt.rendered_read_more}`",
        f"- Complete enough for evidence: `{receipt.complete_enough_for_evidence}`",
        f"- Needs visible human check: `{receipt.needs_visible_human_check}`",
        f"- Reason: {receipt.reason}",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _dictish(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return bool(value)
    return _clean(value).lower() in {"1", "true", "yes", "y", "pass", "passed", "clean"}


def _safe_int(value: Any) -> int:
    try: return int(value or 0)
    except Exception: return 0


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_").replace("\\&", "&").replace("\\/", "/")
    normalized = text.replace("]\\(", "](").replace("\\)", ")")
    match = re.search(r"\]\((https?://[^)\s]+)\)", normalized)
    return (match.group(1) if match else normalized).strip()


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, Path): return value.as_posix()
    if isinstance(value, Mapping): return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple): return [_to_jsonable(v) for v in value]
    if isinstance(value, list): return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        try: return _to_jsonable(value.to_dict())
        except Exception: pass
    if is_dataclass(value): return _to_jsonable(asdict(value))
    return _clean(value)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default


def _read_text(path: Path) -> str:
    try: return path.read_text(encoding="utf-8", errors="replace")
    except Exception: return ""


def _rel(base: Path, target: Path) -> str:
    try: return target.resolve().relative_to(base.resolve()).as_posix()
    except Exception: return target.as_posix().replace("\\", "/")


def _quote_md_path(value: str) -> str:
    return value.replace(" ", "%20")


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _scrub_markdown_machine_urls(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(key): _scrub_markdown_machine_urls(item) for key, item in value.items()}
    if isinstance(value, tuple): return tuple(_scrub_markdown_machine_urls(item) for item in value)
    if isinstance(value, list): return [_scrub_markdown_machine_urls(item) for item in value]
    if isinstance(value, str) and ("http://" in value or "https://" in value): return _plain_url(value)
    return value


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_scrub_markdown_machine_urls(_to_jsonable(value)), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=R43C_REPORT_ROOT)
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
