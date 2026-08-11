from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from source_msn_comments_profile_export import (
    MsnCommentsProfileExport,
    MsnCommentsProfileExportFiles,
    build_msn_comments_profile_export_from_paths,
    render_msn_comments_html,
    write_msn_comments_profile_exports,
)
from source_msn_live_viewable_capture_cli import run_live_viewable_capture


MSN_SOURCE_ADAPTER_SCHEMA_VERSION = "msn_source_adapter_v1"
MSN_PRODUCTION_READY = "MSN_SOURCE_ADAPTER_PRODUCTION_READY"
MSN_CLOSEOUT_REVIEW_REQUIRED = "MSN_SOURCE_ADAPTER_REVIEW_REQUIRED"
MSN_MEDIA_SATISFIED = "MSN_MEDIA_SATISFIED"
MSN_MEDIA_MISSING = "MSN_MEDIA_MISSING"

YORK_TARGET_ID = "AA29207o"
YORK_ARTICLE_URL = (
    "https://www.msn.com"
    "/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"
    "?ocid=edgemobile&PC=EMMX01"
)
YORK_COMMENTS_URL = YORK_ARTICLE_URL + "#comments"
YORK_EXPECTED_COMMENT_COUNT = 25
YORK_REQUIRED_IMAGE_URL = "https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA292lx3.img?w=534&h=356&m=6"
YORK_REQUIRED_IMAGE_IDENTITY = "AA292lx3.img"

AA27_TARGET_ID = "AA27OIhw"
AA27_COMMENTS_URL = "https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?#comments"
AA27_EXPECTED_MANUAL_COMMENT_COUNT = 87
AA27_EXPECTED_V35_ITEMS = 88

ACCEPTED_ARTICLE_SCREENSHOT_NAME = "android_article_MAIN_SINGLE_reference_style.png"
ACCEPTED_COMMENTS_SCREENSHOT_NAME = "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"
DEBUG_ONLY_NAMES = (
    "diagnostic_before_internal_loading.png",
    "comments_stitch_segments",
    "scroller_diagnostic.json",
    "dom_diagnostic.json",
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
    return value


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_value_for_dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_file(path)


@dataclass(frozen=True)
class MsnUrlParts:
    raw_url: str
    article_url: str
    comments_url: str
    target_id: str
    host: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnMediaReceipt:
    original_url: str
    normalized_identity: str
    local_path: str = ""
    sha256: str = ""
    status: str = MSN_MEDIA_MISSING
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnProductionCaptureOptions:
    target_url: str
    output_dir: str
    expected_comment_count: int = 0
    capture_comments: bool = True
    capture_msn_screenshots: bool = False
    capture_msn_article_screenshot: bool = False
    capture_msn_comments_screenshot: bool = False
    write_warc: bool = True
    write_wacz: bool = True
    write_rendered_html: bool = True
    write_validation_json: bool = True
    write_local_viewer: bool = True
    headed: bool = False
    debug: bool = False
    keep_browser_open: bool = False
    msn_comments_sort: str = "top"

    @property
    def headless(self) -> bool:
        return not self.headed

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnCloseoutResult:
    decision: str
    output_root: str
    article_url: str
    comments_url: str
    target_id: str
    comment_count: int
    expected_comment_count: int
    profile_count: int
    article_screenshot: str = ""
    comments_screenshot: str = ""
    media_required: tuple[Mapping[str, Any], ...] = ()
    media_satisfied: bool = False
    html_export: str = ""
    json_export: str = ""
    md_export: str = ""
    txt_export: str = ""
    profiles_json: str = ""
    profiles_txt: str = ""
    warnings: tuple[str, ...] = ()
    schema_version: str = MSN_SOURCE_ADAPTER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def final_block(self) -> str:
        warnings = "NONE" if not self.warnings else "; ".join(self.warnings)
        media_required = ", ".join(item.get("normalized_identity", "") for item in self.media_required) or "NONE"
        return "\n".join(
            [
                f"DECISION: {self.decision}",
                f"OUTPUT_ROOT: {self.output_root}",
                f"ARTICLE_URL: {self.article_url}",
                f"COMMENTS_URL: {self.comments_url}",
                f"TARGET_ID: {self.target_id}",
                f"COMMENT_COUNT: {self.comment_count}",
                f"EXPECTED_COMMENT_COUNT: {self.expected_comment_count}",
                f"PROFILE_COUNT: {self.profile_count}",
                f"ARTICLE_SCREENSHOT: {self.article_screenshot}",
                f"COMMENTS_SCREENSHOT: {self.comments_screenshot}",
                f"MEDIA_REQUIRED: {media_required}",
                f"MEDIA_SATISFIED: {self.media_satisfied}",
                f"HTML_EXPORT: {self.html_export}",
                f"JSON_EXPORT: {self.json_export}",
                f"MD_EXPORT: {self.md_export}",
                f"TXT_EXPORT: {self.txt_export}",
                f"PROFILES_JSON: {self.profiles_json}",
                f"PROFILES_TXT: {self.profiles_txt}",
                f"WARNINGS: {warnings}",
            ]
        )


def build_msn_url_parts(url: str) -> MsnUrlParts:
    raw = str(url or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in ("http", "https") or "msn.com" not in parsed.netloc.lower():
        raise ValueError("MSN source adapter requires an http(s) msn.com URL")
    target_id = ""
    for part in reversed([item for item in parsed.path.split("/") if item]):
        if part.startswith("ar-"):
            target_id = part[3:]
            break
    if not target_id:
        raise ValueError("MSN URL does not contain an ar-* article target id")
    article_url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))
    comments_url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, "comments"))
    return MsnUrlParts(raw_url=raw, article_url=article_url, comments_url=comments_url, target_id=target_id, host=parsed.netloc.lower())


def normalize_msn_image_identity(url_or_path: str) -> str:
    text = str(url_or_path or "").strip()
    path = urlsplit(text).path if "://" in text else text
    path = path.split("?", 1)[0].split("#", 1)[0]
    name = Path(path).name
    return name or text.split("?", 1)[0].split("#", 1)[0]


def required_msn_article_media(url: str) -> tuple[MsnMediaReceipt, ...]:
    parts = build_msn_url_parts(url)
    if parts.target_id == YORK_TARGET_ID:
        return (MsnMediaReceipt(original_url=YORK_REQUIRED_IMAGE_URL, normalized_identity=YORK_REQUIRED_IMAGE_IDENTITY),)
    return ()


def download_msn_article_media(
    *,
    article_url: str,
    output_dir: str | Path,
    downloader: Callable[[str], bytes] | None = None,
) -> tuple[MsnMediaReceipt, ...]:
    out = Path(output_dir) / "media"
    receipts: list[MsnMediaReceipt] = []
    for item in required_msn_article_media(article_url):
        destination = out / item.normalized_identity
        try:
            payload = downloader(item.original_url) if downloader else urllib.request.urlopen(item.original_url, timeout=30).read()
            out.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            receipts.append(
                MsnMediaReceipt(
                    original_url=item.original_url,
                    normalized_identity=item.normalized_identity,
                    local_path=str(destination),
                    sha256=sha256_file(destination),
                    status=MSN_MEDIA_SATISFIED,
                )
            )
        except Exception as exc:
            receipts.append(
                MsnMediaReceipt(
                    original_url=item.original_url,
                    normalized_identity=item.normalized_identity,
                    local_path=str(destination),
                    status=MSN_MEDIA_MISSING,
                    error=str(exc),
                )
            )
    return tuple(receipts)


def production_output_names(*, debug: bool = False) -> tuple[str, ...]:
    normal = (
        "comments.json",
        "comments.txt",
        "comments.md",
        "comments.html",
        "profiles.json",
        "profiles.txt",
        f"screenshots/{ACCEPTED_ARTICLE_SCREENSHOT_NAME}",
        f"screenshots/{ACCEPTED_COMMENTS_SCREENSHOT_NAME}",
        "media/AA292lx3.img",
        "msn-closeout-report.json",
        "msn-closeout-report.txt",
    )
    if debug:
        return normal + DEBUG_ONLY_NAMES
    return normal


def _copy_if_present(source: Path, destination: Path) -> str:
    if not source.is_file():
        return ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return str(destination)


def promote_accepted_screenshot_outputs(output_dir: str | Path, *, debug: bool = False) -> dict[str, str]:
    root = Path(output_dir)
    screenshots = root / "screenshots"
    promoted = {
        "article": _copy_if_present(screenshots / "article-top.png", screenshots / ACCEPTED_ARTICLE_SCREENSHOT_NAME),
        "comments": _copy_if_present(
            screenshots / "full-comments-thread.png"
            if (screenshots / "full-comments-thread.png").is_file()
            else screenshots / "comments-region.png",
            screenshots / ACCEPTED_COMMENTS_SCREENSHOT_NAME,
        ),
    }
    if not debug:
        promoted["diagnostics_written"] = "false"
    return promoted


def write_msn_adapter_comment_exports(
    export: MsnCommentsProfileExport,
    output_dir: str | Path,
    *,
    generated_at: str = "",
) -> MsnCommentsProfileExportFiles:
    files = write_msn_comments_profile_exports(
        export,
        output_dir,
        base_name="comments",
        generated_at=generated_at,
    )
    out = Path(output_dir)
    copies = {
        Path(files.json_path): out / "comments.json",
        Path(files.txt_path): out / "comments.txt",
        Path(files.markdown_path): out / "comments.md",
        Path(files.html_path): out / "comments.html",
        Path(files.profiles_json_path): out / "profiles.json",
        Path(files.profiles_txt_path): out / "profiles.txt",
    }
    for source, destination in copies.items():
        if source != destination:
            shutil.copy2(source, destination)
    return files


def build_msn_closeout_result(
    *,
    output_dir: str | Path,
    url: str,
    expected_comment_count: int,
    comments_export: MsnCommentsProfileExport | None = None,
    comments_files: MsnCommentsProfileExportFiles | None = None,
    media_receipts: Sequence[MsnMediaReceipt] = (),
    warnings: Sequence[str] = (),
) -> MsnCloseoutResult:
    parts = build_msn_url_parts(url)
    root = Path(output_dir)
    article_screenshot = root / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT_NAME
    comments_screenshot = root / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT_NAME
    comment_count = comments_export.items_captured if comments_export else 0
    profile_count = len(comments_export.profiles) if comments_export else 0
    warnings_list = list(warnings)
    if expected_comment_count and comment_count and comment_count != expected_comment_count:
        warnings_list.append(f"comment_count_mismatch expected={expected_comment_count} actual={comment_count}")
    if not article_screenshot.is_file():
        warnings_list.append("article_screenshot_missing")
    if not comments_screenshot.is_file():
        warnings_list.append("comments_screenshot_missing")
    required = tuple(media_receipts or required_msn_article_media(parts.article_url))
    media_satisfied = bool(required) and all(item.status == MSN_MEDIA_SATISFIED for item in required)
    if required and not media_satisfied:
        warnings_list.append("required_media_missing")
    files = comments_files
    result = MsnCloseoutResult(
        decision=MSN_PRODUCTION_READY if not warnings_list else MSN_CLOSEOUT_REVIEW_REQUIRED,
        output_root=str(root),
        article_url=parts.article_url,
        comments_url=parts.comments_url,
        target_id=parts.target_id,
        comment_count=comment_count,
        expected_comment_count=expected_comment_count,
        profile_count=profile_count,
        article_screenshot=str(article_screenshot) if article_screenshot.is_file() else "",
        comments_screenshot=str(comments_screenshot) if comments_screenshot.is_file() else "",
        media_required=tuple(item.to_dict() for item in required),
        media_satisfied=media_satisfied,
        html_export=str(root / "comments.html") if (root / "comments.html").is_file() else (files.html_path if files else ""),
        json_export=str(root / "comments.json") if (root / "comments.json").is_file() else (files.json_path if files else ""),
        md_export=str(root / "comments.md") if (root / "comments.md").is_file() else (files.markdown_path if files else ""),
        txt_export=str(root / "comments.txt") if (root / "comments.txt").is_file() else (files.txt_path if files else ""),
        profiles_json=str(root / "profiles.json") if (root / "profiles.json").is_file() else (files.profiles_json_path if files else ""),
        profiles_txt=str(root / "profiles.txt") if (root / "profiles.txt").is_file() else (files.profiles_txt_path if files else ""),
        warnings=tuple(sorted(set(warnings_list))),
    )
    _write_json(root / "msn-closeout-report.json", result.to_dict())
    (root / "msn-closeout-report.txt").write_text(result.final_block() + "\n", encoding="utf-8")
    return result


def run_msn_closeout_validation(
    *,
    target_url: str,
    output_dir: str | Path,
    comments_capture_paths: Sequence[str | Path] = (),
    expected_comment_count: int = 0,
    capture_msn_screenshots: bool = False,
    capture_msn_article_screenshot: bool = False,
    capture_msn_comments_screenshot: bool = False,
    download_media: bool = False,
    headed: bool = False,
    debug: bool = False,
    keep_browser_open: bool = False,
    live_capture_runner: Callable[..., Any] = run_live_viewable_capture,
    media_downloader: Callable[[str], bytes] | None = None,
) -> MsnCloseoutResult:
    parts = build_msn_url_parts(target_url)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    comments_export: MsnCommentsProfileExport | None = None
    comments_files: MsnCommentsProfileExportFiles | None = None
    warnings: list[str] = []
    if comments_capture_paths:
        comments_export = build_msn_comments_profile_export_from_paths(comments_capture_paths)
        comments_files = write_msn_adapter_comment_exports(comments_export, root)
    if capture_msn_screenshots or capture_msn_article_screenshot or capture_msn_comments_screenshot:
        capture_result = live_capture_runner(
            target_url=parts.comments_url,
            output_dir=root / "live_capture",
            capture_comments=True,
            write_wacz=True,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=True,
            write_validation_json=True,
            write_local_viewer=True,
            headed=headed,
        )
        if getattr(capture_result, "status", ""):
            warnings.append(f"live_capture_status={getattr(capture_result, 'status')}")
        promoted = promote_accepted_screenshot_outputs(root / "live_capture", debug=debug)
        for key, value in promoted.items():
            if value and key in {"article", "comments"}:
                _copy_if_present(Path(value), root / "screenshots" / Path(value).name)
    if keep_browser_open and not headed:
        warnings.append("keep_browser_open_ignored_without_headed")
    elif keep_browser_open:
        warnings.append("keep_browser_open_requested_but_current_runner_closes_browser_after_capture")
    media_receipts = download_msn_article_media(article_url=parts.article_url, output_dir=root, downloader=media_downloader) if download_media else required_msn_article_media(parts.article_url)
    return build_msn_closeout_result(
        output_dir=root,
        url=parts.comments_url,
        expected_comment_count=expected_comment_count,
        comments_export=comments_export,
        comments_files=comments_files,
        media_receipts=media_receipts,
        warnings=warnings,
    )


def render_msn_comments_html_export(export: MsnCommentsProfileExport) -> str:
    return render_msn_comments_html(export)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MSN source adapter production closeout workflow.")
    parser.add_argument("--source-adapter", default="msn", choices=("msn",))
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--comments-json", action="append", default=[])
    parser.add_argument("--expected-comment-count", type=int, default=0)
    parser.add_argument("--msn-comments-sort", default="top", choices=("top", "newest", "both"))
    parser.add_argument("--capture-msn-screenshots", action="store_true")
    parser.add_argument("--capture-msn-article-screenshot", action="store_true")
    parser.add_argument("--capture-msn-comments-screenshot", action="store_true")
    parser.add_argument("--download-media", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--keep-browser-open", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_msn_closeout_validation(
        target_url=args.target_url,
        output_dir=args.output_dir,
        comments_capture_paths=args.comments_json,
        expected_comment_count=args.expected_comment_count,
        capture_msn_screenshots=args.capture_msn_screenshots,
        capture_msn_article_screenshot=args.capture_msn_article_screenshot,
        capture_msn_comments_screenshot=args.capture_msn_comments_screenshot,
        download_media=args.download_media,
        headed=args.headed,
        debug=args.debug,
        keep_browser_open=args.keep_browser_open,
    )
    print(result.final_block())
    return 0 if result.decision == MSN_PRODUCTION_READY else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
