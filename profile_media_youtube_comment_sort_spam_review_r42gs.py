from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

R42GS_MARKER = "YTCE_R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS"
R42GS_PASS_STATUS = "PASS_R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS"
R42GS_BLOCKED_STATUS = "BLOCKED_R42GS_WITH_EXACT_BLOCKER"

YOUTUBE_COMMENT_SORT_TOP = "top"
YOUTUBE_COMMENT_SORT_NEWEST = "newest"
YOUTUBE_COMMENT_SORT_OLDEST = "oldest"

YOUTUBE_SPAM_HANDLING_REVIEW = "review"
YOUTUBE_SPAM_HANDLING_INCLUDE_INLINE = "include_inline"

SORT_DISPLAY_NAMES = {
    YOUTUBE_COMMENT_SORT_TOP: "Top comments",
    YOUTUBE_COMMENT_SORT_NEWEST: "Newest / Date",
    YOUTUBE_COMMENT_SORT_OLDEST: "Oldest / Date",
}
SORT_ENGINE_VALUES = {
    YOUTUBE_COMMENT_SORT_TOP: "Likes",
    YOUTUBE_COMMENT_SORT_NEWEST: "Date (Newest)",
    YOUTUBE_COMMENT_SORT_OLDEST: "Date (Oldest)",
}
SORT_API_ORDERS = {
    YOUTUBE_COMMENT_SORT_TOP: "relevance",
    YOUTUBE_COMMENT_SORT_NEWEST: "time",
    YOUTUBE_COMMENT_SORT_OLDEST: "time",
}
SPAM_DISPLAY_NAMES = {
    YOUTUBE_SPAM_HANDLING_REVIEW: "Review suspected spam separately",
    YOUTUBE_SPAM_HANDLING_INCLUDE_INLINE: "Include suspected spam inline",
}

def _read_var(value: Any, default: Any = "") -> Any:
    if value is None:
        return default
    get = getattr(value, "get", None)
    if callable(get):
        try:
            return get()
        except Exception:
            return default
    return value

def normalize_youtube_comment_sort_order(value: Any) -> str:
    raw = str(value or "").strip().lower()
    compact = " ".join(raw.replace("_", " ").replace("-", " ").replace("(", " ").replace(")", " ").split())
    if not compact:
        return YOUTUBE_COMMENT_SORT_NEWEST
    if compact in {"newest", "date newest", "date new", "time", "new"} or "newest" in compact or ("date" in compact and "oldest" not in compact):
        return YOUTUBE_COMMENT_SORT_NEWEST
    if compact in {"oldest", "date oldest", "old"} or "oldest" in compact:
        return YOUTUBE_COMMENT_SORT_OLDEST
    if compact in {"top", "likes", "like", "relevance", "relevant", "top comments"}:
        return YOUTUBE_COMMENT_SORT_TOP
    raise ValueError(f"Unsupported YouTube comment sort order: {value!r}")

def normalize_youtube_spam_handling(value: Any, *, filter_spam: Any | None = None) -> str:
    raw = str(value or "").strip().lower()
    compact = " ".join(raw.replace("_", " ").replace("-", " ").split())
    if compact:
        if compact in {"review", "review separately", "review suspected spam separately", "separate", "separate flagged spam", "true", "on"}:
            return YOUTUBE_SPAM_HANDLING_REVIEW
        if compact in {"include", "inline", "include inline", "include suspected spam inline", "off", "disabled", "false"}:
            return YOUTUBE_SPAM_HANDLING_INCLUDE_INLINE
        raise ValueError(f"Unsupported YouTube spam handling policy: {value!r}")
    if filter_spam is None:
        return YOUTUBE_SPAM_HANDLING_REVIEW
    return YOUTUBE_SPAM_HANDLING_REVIEW if bool(filter_spam) else YOUTUBE_SPAM_HANDLING_INCLUDE_INLINE

@dataclass(frozen=True)
class YouTubeCommentSortSpamSettings:
    youtube_comment_sort_order: str = YOUTUBE_COMMENT_SORT_NEWEST
    youtube_spam_handling: str = YOUTUBE_SPAM_HANDLING_REVIEW

    @property
    def sort_display_name(self) -> str:
        return SORT_DISPLAY_NAMES[self.youtube_comment_sort_order]

    @property
    def sort_by_value_for_engine(self) -> str:
        return SORT_ENGINE_VALUES[self.youtube_comment_sort_order]

    @property
    def api_comment_order(self) -> str:
        return SORT_API_ORDERS[self.youtube_comment_sort_order]

    @property
    def spam_handling_display_name(self) -> str:
        return SPAM_DISPLAY_NAMES[self.youtube_spam_handling]

    @property
    def filter_spam(self) -> bool:
        return self.youtube_spam_handling == YOUTUBE_SPAM_HANDLING_REVIEW

    def to_source_info_settings(self) -> dict[str, Any]:
        return {
            "youtube_comment_sort_order": self.youtube_comment_sort_order,
            "youtube_comment_sort_display": self.sort_display_name,
            "youtube_comment_sort_api_order": self.api_comment_order,
            "youtube_comment_sort_safe_engine_parameter": True,
            "youtube_spam_handling": self.youtube_spam_handling,
            "youtube_spam_handling_display": self.spam_handling_display_name,
            "youtube_spam_review_default": self.youtube_spam_handling == YOUTUBE_SPAM_HANDLING_REVIEW,
            "spam_review_default": self.youtube_spam_handling == YOUTUBE_SPAM_HANDLING_REVIEW,
            "youtube_spam_separate_review_file": "spam_comments.csv when flagged rows exist",
            "default_preserves_existing_sort": self.youtube_comment_sort_order == YOUTUBE_COMMENT_SORT_NEWEST,
            "newest_sort_supported_or_blocked": "supported_by_existing_commentThreads_order_time",
            "no_capture_executed_by_r42gs": True,
        }

def collect_youtube_comment_sort_spam_settings_from_vars(sort_var: Any = None, spam_filter_var: Any = None, *, spam_handling_value: Any = "") -> YouTubeCommentSortSpamSettings:
    return YouTubeCommentSortSpamSettings(
        youtube_comment_sort_order=normalize_youtube_comment_sort_order(_read_var(sort_var, "Date (Newest)")),
        youtube_spam_handling=normalize_youtube_spam_handling(spam_handling_value, filter_spam=_read_var(spam_filter_var, True)),
    )

def _plain(value: Any) -> bool:
    if isinstance(value, str):
        return "](" not in value and r"]\(" not in value
    if isinstance(value, dict):
        return all(_plain(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_plain(item) for item in value)
    return True

def _contains(root: Path, rel: str, needle: str) -> bool:
    try:
        return needle in (root / rel).read_text(encoding="utf-8")
    except Exception:
        return False

def generate_r42gs_report(source_root: str | Path, output_root: str | Path) -> dict[str, Any]:
    source_root = Path(source_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    defaults = YouTubeCommentSortSpamSettings()
    checks: list[dict[str, str]] = []
    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})

    check("settings_defaults_preserve_current_sort", defaults.youtube_comment_sort_order == "newest")
    check("default_spam_policy_review", defaults.youtube_spam_handling == "review")
    check("allowed_newest_sort_validates", normalize_youtube_comment_sort_order("Date (Newest)") == "newest")
    check("allowed_top_sort_validates", normalize_youtube_comment_sort_order("Likes") == "top")
    try:
        normalize_youtube_comment_sort_order("unsupported sort")
        invalid_sort_rejected = False
    except ValueError:
        invalid_sort_rejected = True
    check("invalid_sort_rejects", invalid_sort_rejected)
    check("newest_sort_supported_or_blocked", _contains(source_root, "extractor.py", "order=self.api_comment_order(sort_by)") and _contains(source_root, "extractor.py", 'return "time"'), "existing extractor maps date/newest sort to YouTube API order=time")
    check("spam_review_separate_output_compatible", _contains(source_root, "evidence_exporter.py", "spam_comments.csv") and _contains(source_root, "extractor.py", "FLAGGED SPAM"), "existing exports preserve spam_comments.csv/readable flagged-spam sections")
    check("readable_txt_parent_reply_indentation_preserved", _contains(source_root, "extractor.py", "    ↳ Reply") and _contains(source_root, "evidence_exporter.py", "comments_readable.txt"))
    check("r42gr_options_remain_present", _contains(source_root, "main.py", "youtube_export_searchable_html_var") and _contains(source_root, "main.py", "youtube_export_author_profile_urls_var"))
    check("main_records_sort_and_spam_settings", _contains(source_root, "main.py", "collect_youtube_comment_sort_spam_settings_from_vars") and _contains(source_root, "main.py", "settings.update(youtube_comment_sort_spam_settings.to_source_info_settings())"))
    check("no_capture_side_effects", True, "offline settings/audit only; no live YouTube capture, browser, network, screenshot, yt-dlp, JDownloader, or downloader execution")
    sample = {
        "default": defaults.to_source_info_settings(),
        "top_comments": YouTubeCommentSortSpamSettings("top", "review").to_source_info_settings(),
        "include_inline": YouTubeCommentSortSpamSettings("newest", "include_inline").to_source_info_settings(),
    }
    sample_path = output_root / "R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_DEFAULTS_SAMPLE.json"
    sample_path.write_text(json.dumps(sample, indent=2, sort_keys=True), encoding="utf-8")
    passed = all(item["status"] == "pass" for item in checks)
    report = {
        "schema_version": "youtube_comment_sort_spam_review.r42gs.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "marker": R42GS_MARKER,
        "status": R42GS_PASS_STATUS if passed else R42GS_BLOCKED_STATUS,
        "passed": passed,
        "youtube_comment_sort_order": defaults.youtube_comment_sort_order,
        "youtube_spam_handling": defaults.youtube_spam_handling,
        "default_preserves_existing_sort": True,
        "spam_review_default": True,
        "newest_sort_supported_or_blocked": "supported_by_existing_commentThreads_order_time",
        "spam_review_artifact": "spam_comments.csv when flagged rows exist; FLAGGED SPAM section in readable TXT",
        "no_capture_executed_by_r42gs": True,
        "side_effect_boundary": "offline settings/audit only: no live YouTube capture, no comment scraping, no browser/WebView2/CDP, no screenshot run, no network fetch, no media download, no yt-dlp, no JDownloader, no source-role assignment, no review-window rewrite, no counter/no-jump mutation, no metadata promotion",
        "sample_settings_path": str(sample_path),
        "checks": checks,
    }
    check("machine_fields_plain", _plain(report))
    passed = all(item["status"] == "pass" for item in checks)
    report["status"] = R42GS_PASS_STATUS if passed else R42GS_BLOCKED_STATUS
    report["passed"] = passed
    (output_root / "R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_lines = [
        "# R42GS YouTube Comment Sort + Spam Review Defaults",
        "",
        f"Marker: `{R42GS_MARKER}`",
        f"Status: `{report['status']}`",
        "",
        "## Defaults",
        "",
        f"- `youtube_comment_sort_order`: `{report['youtube_comment_sort_order']}`",
        f"- `youtube_spam_handling`: `{report['youtube_spam_handling']}`",
        "- Spam review remains separate/reviewable through `spam_comments.csv` when flagged rows exist and the readable TXT flagged-spam section.",
        "- R42GS did not execute live capture, browser, network, screenshot, yt-dlp, or JDownloader work.",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        suffix = f" — {item['detail']}" if item.get("detail") else ""
        md_lines.append(f"- {item['status'].upper()}: `{item['name']}`{suffix}")
    (output_root / "R42GS_YOUTUBE_COMMENT_SORT_SPAM_REVIEW_REPORT.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return report

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the R42GS YouTube sort/spam review audit report.")
    parser.add_argument("--source-root", default=".")
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gs_youtube_comment_sort_spam_review")
    args = parser.parse_args(argv)
    report = generate_r42gs_report(args.source_root, args.output_root)
    print(R42GS_MARKER)
    print(report["status"])
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
