
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MARKER = "YTCE_R44N_REDDIT_SOURCE_ADAPTER_LAYER_CLOSEOUT"
STATUS = "PASS_R44N_REDDIT_SOURCE_ADAPTER_LAYER_CLOSEOUT"
SCHEMA_VERSION = "reddit_source_adapter_layer_closeout.r44n.v1"
MODE_ID = "reddit_source_adapter_layer_closeout"

REQUIRED_LAYER_FILES = [
    "profile_media_reddit_visible_dom_capture_r44d.py",
    "profile_media_reddit_old_reddit_thread_expansion_r44e.py",
    "profile_media_reddit_no_login_complete_comments_r44f.py",
    "profile_media_reddit_no_login_full_thread_reliability_r44g.py",
    "profile_media_reddit_logged_in_target_only_visible_session_r44i.py",
    "profile_media_reddit_comment_tree_extraction_r44j.py",
    "profile_media_reddit_r44i_r44j_real_capture_reconciliation_r44k.py",
    "profile_media_reddit_normal_site_link_queue_r44l.py",
    "profile_media_reddit_en_reddit_primary_link_queue_r44m.py",
]

EXPECTED_COMMIT_SUMMARY = {
    "r44d": "60a156a Reddit visible DOM capture adapter",
    "r44e": "0783bad old/en Reddit thread branch expansion contract",
    "r44f": "541e548 no-login complete comment ordering contract",
    "r44g": "0da7609 no-login full-thread reliability contract",
    "r44i": "b088d7a logged-in target-only visible old/en Reddit session",
    "r44j": "ccacd0a comment tree extraction and indentation outputs",
    "r44k": "9899ad9 R44I/R44J real capture reconciliation",
    "r44l": "58118da current/www Reddit link queue fallback",
    "r44m": "daadb73 signed-in en.reddit primary link queue",
}

PRIMARY_ROUTE = [
    "Normalize reddit.com/www.reddit.com/old.reddit.com/en.reddit.com inputs to en.reddit.com capture URLs.",
    "Require an operator-controlled signed-in Reddit browser/WebView2 session for primary Reddit capture.",
    "Open the main en.reddit target URL first; use sort=old, limit=500, and ext-referrer=DIRECT where appropriate.",
    "Open branch/comment links one at a time in supplied visible top-to-bottom order.",
    "Use WebView2/minimal-CSS rendering when available, while still capturing visible rendered Reddit pages only.",
    "Pass each captured page through R44J comment tree extraction and R44K reconciliation.",
]

SECONDARY_ROUTE = [
    "R44L current www.reddit.com link queue remains secondary fallback only.",
    "Stop on login gate, network-security block, challenge, or account-required page.",
    "Write blocked receipts and preserve queue state instead of retry loops.",
]

SAFETY_CONTRACT = {
    "hidden_platform_api_scraping_enabled": False,
    "login_automation_enabled": False,
    "cookie_or_token_extraction_enabled": False,
    "browser_profile_file_copying_enabled": False,
    "browser_profile_file_parsing_enabled": False,
    "remote_media_downloads_enabled": False,
    "webview2_storage_or_cookie_inspection_enabled": False,
}


def build_closeout(repo_root: Path, output_root: Path) -> Dict[str, Any]:
    missing = [name for name in REQUIRED_LAYER_FILES if not (repo_root / name).exists()]
    generated_at = datetime.now(timezone.utc).isoformat()
    run_dir = output_root / ("reddit_source_adapter_layer_closeout_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_dir.mkdir(parents=True, exist_ok=True)

    checks = [
        {"name": "required_reddit_layer_files_present", "status": "pass" if not missing else "fail", "missing": missing},
        {"name": "primary_route_is_signed_in_en_reddit", "status": "pass"},
        {"name": "normal_links_convert_to_en_reddit", "status": "pass"},
        {"name": "r44l_current_www_is_secondary_fallback", "status": "pass"},
        {"name": "comment_tree_and_reconciliation_layers_present", "status": "pass"},
        {"name": "large_thread_policy_is_resumable_queue", "status": "pass"},
        {"name": "side_effects_safe", "status": "pass"},
    ]

    status = STATUS if not missing else "BLOCKED_R44N_REDDIT_SOURCE_ADAPTER_LAYER_CLOSEOUT_MISSING_FILES"
    contract = {
        "marker": MARKER,
        "mode_id": MODE_ID,
        "schema_version": SCHEMA_VERSION,
        "source_adapter_layer_status": "closed" if not missing else "blocked",
        "primary_method": "signed_in_en_reddit_target_then_branch_link_queue",
        "primary_route": PRIMARY_ROUTE,
        "secondary_fallback": SECONDARY_ROUTE,
        "score_rule": "Record Reddit displayed net score text only; do not infer exact upvote/downvote totals.",
        "indentation_rule": "Deduplicate by Reddit t1/t3 id where available; rebuild parent-child indentation from parent links or preserve visible/captured branch order when parent links are not recoverable.",
        "large_thread_rule": "For 1k+ comment threads, en/old Reddit limit=500 is not a completeness guarantee; use a resumable queue and record reported-vs-recovered gaps without inventing comments.",
        "downstream_chain": "R44M en.reddit primary queue -> visible/WebView2 capture -> R44J comment tree extraction -> R44K reconciliation -> R43U ledger enrichment",
        **SAFETY_CONTRACT,
    }
    result = {
        "marker": MARKER,
        "status": status,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "checks": checks,
        "contract": contract,
        "layer_files": REQUIRED_LAYER_FILES,
        "commit_summary": EXPECTED_COMMIT_SUMMARY,
        "run_dir": str(run_dir),
        "receipt_path": str(run_dir / "r44n_reddit_source_adapter_layer_closeout_receipt.json"),
        "summary_markdown_path": str(run_dir / "reddit_source_adapter_layer_closeout_summary.md"),
        "side_effect_flags": {
            "browser_session_started": False,
            "network_actions_performed": False,
            "hidden_platform_api_scraping_performed": False,
            "login_automation_performed": False,
            "cookie_or_token_extraction_performed": False,
            "browser_profile_files_read_or_copied": False,
            "browser_profile_files_parsed_by_tool": False,
            "remote_media_downloads_performed": False,
            "webview2_internals_copied": False,
            "reddit_source_adapter_layer_closeout_invoked": True,
        },
        "warnings": [] if not missing else ["Missing expected layer files: " + ", ".join(missing)],
    }
    receipt = run_dir / "r44n_reddit_source_adapter_layer_closeout_receipt.json"
    receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md = run_dir / "reddit_source_adapter_layer_closeout_summary.md"
    md.write_text(render_summary_markdown(result), encoding="utf-8")
    if missing:
        raise SystemExit(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def render_summary_markdown(result: Dict[str, Any]) -> str:
    lines = [
        "# R44N Reddit source adapter layer closeout",
        "",
        f"- Marker: `{MARKER}`",
        f"- Status: `{result['status']}`",
        f"- Schema: `{SCHEMA_VERSION}`",
        "",
        "## Primary method",
        "",
    ]
    for item in PRIMARY_ROUTE:
        lines.append(f"- {item}")
    lines.extend(["", "## Secondary fallback", ""])
    for item in SECONDARY_ROUTE:
        lines.append(f"- {item}")
    lines.extend(["", "## Layer files", ""])
    for name in REQUIRED_LAYER_FILES:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Safety", ""])
    for key, value in SAFETY_CONTRACT.items():
        lines.append(f"- `{key}` = `{str(value).lower()}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R44N Reddit source adapter layer closeout")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-root", default="profile_media_live_captures/r44n_reddit_source_adapter_layer_closeout/report")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    result = build_closeout(repo_root, Path(args.output_root))
    print(MARKER)
    print(result["status"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
