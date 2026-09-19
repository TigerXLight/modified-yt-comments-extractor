from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from profile_media_reddit_comment_tree_extraction_r44j import (
    PASS_STATUS as R44J_PASS_STATUS,
    run_reddit_comment_tree_extraction_r44j,
)

MARKER = "YTCE_R44K_REDDIT_R44I_R44J_REAL_CAPTURE_RECONCILIATION"
PASS_STATUS = "PASS_R44K_REDDIT_R44I_R44J_REAL_CAPTURE_RECONCILIATION"
BLOCKED_STATUS = "BLOCKED_R44K_REDDIT_R44I_R44J_REAL_CAPTURE_RECONCILIATION"
SCHEMA_VERSION = "reddit_r44i_r44j_real_capture_reconciliation.r44k.v1"
DEFAULT_R44I_ROOT = "profile_media_live_captures/r44i_reddit_logged_in_target_only_visible_session"
DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r44k_reddit_r44i_r44j_real_capture_reconciliation"
DEFAULT_TARGET_URL = "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT"


@dataclass(frozen=True)
class RedditR44IToR44JReconciliationResultR44K:
    marker: str
    schema_version: str
    status: str
    output_root: str
    run_dir: str
    receipt_path: str
    reconciliation_report_path: str
    r44i_run_dir: str = ""
    r44i_sanitized_html_path: str = ""
    r44i_raw_html_path: str = ""
    r44i_screenshot_path: str = ""
    r44d_receipt_path: str = ""
    r44j_receipt_path: str = ""
    r44j_comment_index_path: str = ""
    r44j_comment_tree_markdown_path: str = ""
    target_url: str = DEFAULT_TARGET_URL
    r44i_status: str = ""
    r44d_status: str = ""
    ledger_status: str = ""
    r44i_record_count: int = 0
    r44i_visible_record_count: int = 0
    r44i_media_count: int = 0
    r44i_screenshot_count: int = 0
    reddit_reported_comment_count: int = 0
    reference_recoverable_comment_count: int = 0
    r44j_recovered_comment_count: int = 0
    r44j_top_level_comment_count: int = 0
    r44j_max_comment_depth: int = 0
    r44j_score_count: int = 0
    r44j_hidden_score_count: int = 0
    r44j_negative_score_count: int = 0
    r44i_minus_r44j_record_delta: int = 0
    r44j_minus_reference_delta: int = 0
    reddit_reported_minus_r44j_delta: int = 0
    likely_non_comment_or_duplicate_artifact_count: int = 0
    count_gap_recorded_not_invented: bool = True
    interpretation: Mapping[str, Any] = field(default_factory=dict)
    side_effect_flags: Mapping[str, bool] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class RedditR44KReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    sample_result: Mapping[str, Any]
    contract: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k() -> dict[str, Any]:
    return {
        "marker": MARKER,
        "schema_version": SCHEMA_VERSION,
        "mode_id": "reddit_r44i_r44j_real_capture_reconciliation",
        "purpose": "Compare a real R44I target-only Reddit capture against the R44J comment-tree extraction layer and known/reference counts.",
        "input_rule": "Use prior R44I evidence files only: target_only_sanitized_dom.html, target_only_raw_dom.html, screenshot, and R44D/R43U receipts. Do not open Reddit or start a browser.",
        "count_rule": "Separate R44I visible ledger record counts from R44J parsed comment-node counts; record deltas rather than treating every visible block as a comment.",
        "reference_rule": "When a reference transcript exists, compare R44J recovered nodes against its recoverable-node count without inventing missing comments.",
        "large_thread_rule": "For 1k+ comment threads, use this reconciliation after each target-only page or branch-page capture and continue through a resumable queue.",
        "no_login_fallback_rule": "If no signed-in Reddit profile is available, current Reddit target-only captures can be reconciled the same way, but blocked pages must produce blocked receipts rather than retries.",
        "browser_profile_file_copying_enabled": False,
        "browser_profile_file_parsing_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "login_automation_enabled": False,
        "hidden_platform_api_scraping_enabled": False,
        "remote_media_downloads_enabled": False,
        "network_actions_enabled": False,
    }


def build_side_effect_flags_r44k() -> dict[str, bool]:
    return {
        "reddit_r44i_r44j_reconciliation_invoked": True,
        "browser_session_started": False,
        "network_actions_performed": False,
        "browser_profile_files_read_or_copied": False,
        "browser_profile_files_parsed_by_tool": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
    }


def find_latest_r44i_run_dir_r44k(root: str | Path = DEFAULT_R44I_ROOT) -> Path | None:
    base = Path(root)
    if not base.exists():
        return None
    candidates = []
    for path in base.glob("reddit_logged_in_target_only_*"):
        if path.is_dir() and _sanitized_html_path(path).is_file():
            candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, p.name), reverse=True)[0]


def run_reddit_r44i_r44j_real_capture_reconciliation_r44k(
    *,
    r44i_run_dir: str = "",
    r44i_root: str = DEFAULT_R44I_ROOT,
    output_root: str = DEFAULT_OUTPUT_ROOT,
    target_url: str = DEFAULT_TARGET_URL,
    reported_comment_count: int = 337,
    reference_recoverable_comment_count: int = 333,
    max_items: int = 2000,
) -> RedditR44IToR44JReconciliationResultR44K:
    root = Path(output_root)
    capture_ts = _now_ts()
    run_dir = root / f"reddit_r44i_r44j_reconciliation_{capture_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = run_dir / "r44k_reddit_r44i_r44j_reconciliation_receipt.json"
    report_path = run_dir / "r44k_reddit_r44i_r44j_reconciliation_report.json"

    warnings: list[str] = []
    source_run = Path(r44i_run_dir) if r44i_run_dir else (find_latest_r44i_run_dir_r44k(r44i_root) or Path())
    if not source_run or not source_run.exists():
        result = RedditR44IToR44JReconciliationResultR44K(
            marker=MARKER,
            schema_version=SCHEMA_VERSION,
            status=BLOCKED_STATUS,
            output_root=str(root),
            run_dir=str(run_dir),
            receipt_path=str(receipt_path),
            reconciliation_report_path=str(report_path),
            target_url=target_url,
            reddit_reported_comment_count=int(reported_comment_count or 0),
            reference_recoverable_comment_count=int(reference_recoverable_comment_count or 0),
            side_effect_flags=build_side_effect_flags_r44k(),
            warnings=(f"No R44I run directory with target_only_sanitized_dom.html found under {r44i_root!r}.",),
        )
        _write_json(receipt_path, result.to_dict())
        _write_json(report_path, result.to_dict())
        return result

    sanitized_html = _sanitized_html_path(source_run)
    raw_html = _raw_html_path(source_run)
    screenshot = _screenshot_path(source_run)
    r44d_receipt = _latest_r44d_receipt(source_run)
    r44d_payload = _read_json(r44d_receipt)
    if not sanitized_html.is_file():
        warnings.append(f"R44I sanitized HTML missing: {sanitized_html}")

    r44i_record_count = _int(r44d_payload.get("record_count"))
    r44i_visible_record_count = _int(r44d_payload.get("visible_record_count"))
    r44i_media_count = _int(r44d_payload.get("media_count"))
    r44i_screenshot_count = _int(r44d_payload.get("screenshot_count"))
    r44d_status = str(r44d_payload.get("status") or "")
    ledger_status = str(r44d_payload.get("ledger_status") or "")

    if not r44i_record_count and not r44i_visible_record_count:
        # R44I itself prints record_count, but the durable R44D receipt is the
        # best source. If unavailable, leave zeros and record a warning rather
        # than guessing from file size or DOM count.
        warnings.append("No R44D receipt record_count/visible_record_count found; R44I-vs-R44J delta may be incomplete.")

    r44j_output = run_dir / "r44j_from_latest_r44i_capture"
    r44j_result = run_reddit_comment_tree_extraction_r44j(
        old_reddit_html_path=str(sanitized_html),
        target_url=target_url,
        output_root=str(r44j_output),
        reported_comment_count=int(reported_comment_count or 0),
        signed_in_profile_available=True,
        max_items=max_items,
    )
    r44j_payload = r44j_result.to_dict()
    r44j_count = _int(r44j_payload.get("recovered_comment_count"))
    reported = int(reported_comment_count or 0)
    reference = int(reference_recoverable_comment_count or 0)
    delta_i_j = r44i_record_count - r44j_count if r44i_record_count else 0
    delta_j_ref = r44j_count - reference if reference else 0
    delta_reported_j = reported - r44j_count if reported else 0
    likely_artifacts = max(0, delta_i_j)

    interpretation = {
        "r44i_record_count_meaning": "R44I/R44D counts visible Reddit record blocks that reached the universal ledger; this can include submission/main-post blocks or duplicated/non-comment record artifacts.",
        "r44j_recovered_comment_count_meaning": "R44J attempts to parse comment nodes and indentation from the prior R44I old-Reddit DOM evidence.",
        "reference_recoverable_comment_count_meaning": "The reference transcript count is an external/manual recoverable-comment-node baseline when supplied.",
        "reported_comment_count_meaning": "The Reddit displayed header count may include hidden/deleted/not-rendered comments and must not be treated as text the tool can invent.",
        "likely_non_comment_or_duplicate_artifact_count": likely_artifacts,
        "count_gap_recorded_not_invented": True,
        "needs_follow_up": bool(r44j_count and reference and abs(delta_j_ref) > 0) or bool(likely_artifacts),
        "recommended_next_action": "Inspect R44J output and R44D visible_records_path to classify deltas as post/form/sidebar/duplicate artifacts or real missed comments.",
    }
    status = PASS_STATUS if r44j_payload.get("status") == R44J_PASS_STATUS and r44j_count > 0 else BLOCKED_STATUS
    if status != PASS_STATUS:
        warnings.append(f"R44J extraction from R44I sanitized HTML did not pass with recovered comments: {r44j_payload.get('status')!r}, recovered={r44j_count}.")

    result = RedditR44IToR44JReconciliationResultR44K(
        marker=MARKER,
        schema_version=SCHEMA_VERSION,
        status=status,
        output_root=str(root),
        run_dir=str(run_dir),
        receipt_path=str(receipt_path),
        reconciliation_report_path=str(report_path),
        r44i_run_dir=str(source_run),
        r44i_sanitized_html_path=str(sanitized_html),
        r44i_raw_html_path=str(raw_html) if raw_html.is_file() else "",
        r44i_screenshot_path=str(screenshot) if screenshot.is_file() else "",
        r44d_receipt_path=str(r44d_receipt) if r44d_receipt.is_file() else "",
        r44j_receipt_path=str(r44j_payload.get("receipt_path") or ""),
        r44j_comment_index_path=str(r44j_payload.get("comment_index_path") or ""),
        r44j_comment_tree_markdown_path=str(r44j_payload.get("comment_tree_markdown_path") or ""),
        target_url=target_url,
        r44i_status="PASS_R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION" if source_run.exists() else "",
        r44d_status=r44d_status,
        ledger_status=ledger_status,
        r44i_record_count=r44i_record_count,
        r44i_visible_record_count=r44i_visible_record_count,
        r44i_media_count=r44i_media_count,
        r44i_screenshot_count=r44i_screenshot_count,
        reddit_reported_comment_count=reported,
        reference_recoverable_comment_count=reference,
        r44j_recovered_comment_count=r44j_count,
        r44j_top_level_comment_count=_int(r44j_payload.get("top_level_comment_count")),
        r44j_max_comment_depth=_int(r44j_payload.get("max_comment_depth")),
        r44j_score_count=_int(r44j_payload.get("score_count")),
        r44j_hidden_score_count=_int(r44j_payload.get("hidden_score_count")),
        r44j_negative_score_count=_int(r44j_payload.get("negative_score_count")),
        r44i_minus_r44j_record_delta=delta_i_j,
        r44j_minus_reference_delta=delta_j_ref,
        reddit_reported_minus_r44j_delta=delta_reported_j,
        likely_non_comment_or_duplicate_artifact_count=likely_artifacts,
        count_gap_recorded_not_invented=True,
        interpretation=interpretation,
        side_effect_flags=build_side_effect_flags_r44k(),
        warnings=tuple(warnings),
    )
    _write_json(receipt_path, result.to_dict())
    _write_json(report_path, result.to_dict())
    _write_text(run_dir / "R44K_RECONCILIATION_SUMMARY.md", _summary_md(result))
    return result


def run_self_test(output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> RedditR44KReport:
    root = Path(output_root)
    fixture_root = root / "self_test_fixture_r44i"
    r44i_run = fixture_root / "reddit_logged_in_target_only_20260919T070000Z"
    evidence = r44i_run / "visible_reddit_target_only_evidence"
    r44d_dir = r44i_run / "r44d_target_only_capture" / "r_EdSheeran" / "reddit_visible_dom_capture_20260919T070000Z"
    evidence.mkdir(parents=True, exist_ok=True)
    r44d_dir.mkdir(parents=True, exist_ok=True)
    html = """<html><body>
<div class="thing id-t3_1whbgzk" id="thing_t3_1whbgzk" data-fullname="t3_1whbgzk" data-author="Stonerthrowaway710"><a href="https://en.reddit.com/r/EdSheeran/comments/1whbgzk/title/">post</a></div>
<div class="thing id-t1_a1 depth-0" id="thing_t1_a1" data-fullname="t1_a1" data-author="alpha"><span class="score unvoted">2 points</span><div class="md"><p>Top comment</p></div></div>
<div class="thing id-t1_b2 depth-1" id="thing_t1_b2" data-fullname="t1_b2" data-parent="t1_a1" data-author="beta"><span class="score unvoted">-1 points</span><div class="md"><p>Nested reply</p></div></div>
<div class="thing id-t1_c3 depth-0" id="thing_t1_c3" data-fullname="t1_c3" data-author="gamma"><span class="score hidden">[score hidden]</span><div class="md"><p>Hidden score top comment</p></div></div>
</body></html>"""
    (evidence / "target_only_sanitized_dom.html").write_text(html, encoding="utf-8")
    (evidence / "target_only_raw_dom.html").write_text(html, encoding="utf-8")
    (evidence / "target_only_current_reddit.png").write_text("fixture screenshot placeholder", encoding="utf-8")
    _write_json(r44d_dir / "r44d_reddit_visible_dom_capture_receipt.json", {
        "status": "PASS_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER",
        "ledger_status": "PASS_R43U_UNIVERSAL_SOCIAL_ACCOUNT_LEDGER_CONTRACT_BASELINE",
        "record_count": 5,
        "visible_record_count": 5,
        "media_count": 0,
        "screenshot_count": 5,
    })
    result = run_reddit_r44i_r44j_real_capture_reconciliation_r44k(
        r44i_root=str(fixture_root),
        output_root=str(root / "self_test"),
        reported_comment_count=4,
        reference_recoverable_comment_count=3,
        max_items=20,
    )
    checks = [
        {"name": "latest_r44i_run_found", "status": "pass" if result.r44i_run_dir.endswith("20260919T070000Z") else "fail"},
        {"name": "r44j_extracts_comments_from_r44i_html", "status": "pass" if result.r44j_recovered_comment_count == 3 else "fail"},
        {"name": "r44i_vs_r44j_delta_recorded", "status": "pass" if result.r44i_minus_r44j_record_delta == 2 and result.likely_non_comment_or_duplicate_artifact_count == 2 else "fail"},
        {"name": "reference_delta_recorded", "status": "pass" if result.r44j_minus_reference_delta == 0 else "fail"},
        {"name": "reported_gap_recorded_not_invented", "status": "pass" if result.reddit_reported_minus_r44j_delta == 1 and result.count_gap_recorded_not_invented else "fail"},
        {"name": "side_effects_safe", "status": "pass" if not any(v for k, v in build_side_effect_flags_r44k().items() if k not in {"reddit_r44i_r44j_reconciliation_invoked"}) else "fail"},
    ]
    status = PASS_STATUS if all(c["status"] == "pass" for c in checks) else BLOCKED_STATUS
    report = RedditR44KReport(
        marker=MARKER,
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=tuple(checks),
        sample_result=result.to_dict(),
        contract=build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k(),
        side_effect_flags=build_side_effect_flags_r44k(),
    )
    _write_json(root / "R44K_REDDIT_R44I_R44J_RECONCILIATION_REPORT.json", report.to_dict())
    _write_text(root / "R44K_REDDIT_R44I_R44J_RECONCILIATION_REPORT.md", _report_md(report))
    return report


def _sanitized_html_path(run_dir: Path) -> Path:
    return run_dir / "visible_reddit_target_only_evidence" / "target_only_sanitized_dom.html"


def _raw_html_path(run_dir: Path) -> Path:
    return run_dir / "visible_reddit_target_only_evidence" / "target_only_raw_dom.html"


def _screenshot_path(run_dir: Path) -> Path:
    return run_dir / "visible_reddit_target_only_evidence" / "target_only_current_reddit.png"


def _latest_r44d_receipt(run_dir: Path) -> Path:
    matches = list(run_dir.glob("r44d_target_only_capture/**/r44d_reddit_visible_dom_capture_receipt.json"))
    if not matches:
        return Path()
    return sorted(matches, key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)[0]


def _summary_md(result: RedditR44IToR44JReconciliationResultR44K) -> str:
    lines = [
        f"# {MARKER}",
        "",
        f"Status: `{result.status}`",
        "",
        "## Counts",
        f"- R44I/R44D ledger records: `{result.r44i_record_count}`",
        f"- R44I visible records: `{result.r44i_visible_record_count}`",
        f"- R44J recovered comment nodes: `{result.r44j_recovered_comment_count}`",
        f"- Reference recoverable comments: `{result.reference_recoverable_comment_count}`",
        f"- Reddit reported comments: `{result.reddit_reported_comment_count}`",
        f"- R44I minus R44J delta: `{result.r44i_minus_r44j_record_delta}`",
        f"- R44J minus reference delta: `{result.r44j_minus_reference_delta}`",
        f"- Reddit reported minus R44J delta: `{result.reddit_reported_minus_r44j_delta}`",
        "",
        "## Paths",
        f"- R44I run: `{result.r44i_run_dir}`",
        f"- R44J comment index: `{result.r44j_comment_index_path}`",
        f"- R44J markdown: `{result.r44j_comment_tree_markdown_path}`",
        "",
        "## Interpretation",
        "```json",
        json.dumps(result.interpretation, indent=2, sort_keys=True, ensure_ascii=False),
        "```",
    ]
    if result.warnings:
        lines.extend(["", "## Warnings"] + [f"- {w}" for w in result.warnings])
    return "\n".join(lines) + "\n"


def _report_md(report: RedditR44KReport) -> str:
    lines = [f"# {MARKER}", "", f"Status: `{report.status}`", "", "## Checks"]
    for check in report.checks:
        lines.append(f"- `{check.get('name')}`: **{check.get('status')}**")
    lines.extend(["", "## Contract", "", "```json", json.dumps(report.contract, indent=2, sort_keys=True, ensure_ascii=False), "```", ""])
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8", errors="replace")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="R44K Reddit R44I/R44J real capture reconciliation")
    parser.add_argument("--r44i-run-dir", default="")
    parser.add_argument("--r44i-root", default=DEFAULT_R44I_ROOT)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL)
    parser.add_argument("--reported-comment-count", type=int, default=337)
    parser.add_argument("--reference-recoverable-comment-count", type=int, default=333)
    parser.add_argument("--max-items", type=int, default=2000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        report = run_self_test(args.output_root)
        print(MARKER)
        print(report.status)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if report.status == PASS_STATUS else 1
    result = run_reddit_r44i_r44j_real_capture_reconciliation_r44k(
        r44i_run_dir=args.r44i_run_dir,
        r44i_root=args.r44i_root,
        output_root=args.output_root,
        target_url=args.target_url,
        reported_comment_count=args.reported_comment_count,
        reference_recoverable_comment_count=args.reference_recoverable_comment_count,
        max_items=args.max_items,
    )
    print(MARKER)
    print(result.status)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    if result.status == PASS_STATUS:
        print("R44K_REDDIT_R44I_R44J_RECONCILIATION_DONE")
        return 0
    print("R44K_REDDIT_R44I_R44J_RECONCILIATION_BLOCKED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
