from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from source_msn_live_viewable_capture_cli import (
    LIVE_VIEWABLE_CAPTURE_BLOCKED,
    LIVE_VIEWABLE_CAPTURE_COMPLETED,
    LIVE_VIEWABLE_CAPTURE_DRY_RUN,
    build_live_viewable_capture_plan,
    run_live_viewable_capture,
)
from source_msn_vertical_live_validation import DEFAULT_MSN_VERTICAL_URL

TARGET_URL = (
    "https://www.msn.com"
    "/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"
    "?ocid=edgemobile&PC=EMMX01#comments"
)


def _write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _fake_artifact(label: str, path: Path, payload: bytes = b"fake-png") -> dict[str, object]:
    _write(path, payload)
    return {
        "label": label,
        "path": str(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "width": 1,
        "height": 1,
    }


def _fake_validation_runner(*, source_url: str, output_directory: str | Path, headless: bool = True):
    output_root = Path(output_directory)
    profile_root = output_root / "android_mobile_chromium"
    profile_root.mkdir(parents=True, exist_ok=True)
    dom = "<html><head><title>MSN Article</title></head><body><article><h1>Arrest made after shot fired outside York mosque</h1><p>Body.</p></article><section>Comment one</section></body></html>"
    (profile_root / "final_rendered_dom.html").write_text(dom, encoding="utf-8")
    article = _fake_artifact("android_mobile_chromium_faithful_article_screenshot", profile_root / "faithful_article_region.png")
    full = _fake_artifact("android_mobile_chromium_faithful_full_page_screenshot", profile_root / "faithful_full_page.png")
    comments = _fake_artifact("android_mobile_chromium_faithful_comments_screenshot", profile_root / "faithful_comments_visible.png")
    warc_text = "WARC/1.0\r\nWARC-Type: request\r\nWARC-Target-URI: {0}\r\n\r\nGET /en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o HTTP/1.1\r\nHost: www.msn.com\r\n\r\nWARC/1.0\r\nWARC-Type: response\r\nWARC-Target-URI: {0}\r\n\r\nHTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n{1}".format(source_url.split("#", 1)[0], dom)
    warc_path = _write(output_root / "local_web_archive" / "archive" / "data.warc", warc_text.encode("utf-8"))
    wacz_path = _write(output_root / "local_web_archive" / "archive.wacz", b"fake-wacz")
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps({"source_url": source_url, "artifacts": []}), encoding="utf-8")
    return SimpleNamespace(
        source_url=source_url,
        canonical_url=source_url.split("#", 1)[0],
        output_directory=str(output_root),
        status_matrix={"browser_runtime": "RENDERED_BROWSER_LIVE_TESTED"},
        manifest_path=str(manifest_path),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        artifacts=(
            article,
            full,
            comments,
            {"label": "standard_warc", "path": str(warc_path), "sha256": hashlib.sha256(warc_path.read_bytes()).hexdigest(), "size_bytes": warc_path.stat().st_size},
            {"label": "standard_wacz", "path": str(wacz_path), "sha256": hashlib.sha256(wacz_path.read_bytes()).hexdigest(), "size_bytes": wacz_path.stat().st_size},
        ),
        summary={
            "best_profile": {
                "profile_name": "android_mobile_chromium",
                "title": "MSN Article",
                "article_text_chars": 5,
                "comment_count": 1,
                "final_url": source_url,
            }
        },
    )


def test_target_url_and_output_dir_are_required() -> None:
    plan = build_live_viewable_capture_plan(target_url="", output_dir="")
    assert plan.status == LIVE_VIEWABLE_CAPTURE_BLOCKED
    assert "target URL is required" in plan.errors
    assert "new output directory is required" in plan.errors


def test_configured_msn_url_is_raw_and_not_markdown_link() -> None:
    assert DEFAULT_MSN_VERTICAL_URL.startswith("https://www.msn.com/")
    assert "ar-AA29207o" in DEFAULT_MSN_VERTICAL_URL
    assert DEFAULT_MSN_VERTICAL_URL.endswith("#comments")
    assert "&PC=EMMX01" in DEFAULT_MSN_VERTICAL_URL
    assert "[" not in DEFAULT_MSN_VERTICAL_URL
    assert "]" not in DEFAULT_MSN_VERTICAL_URL
    assert ("](" + "https://") not in DEFAULT_MSN_VERTICAL_URL
    assert ("\\" + "&PC=") not in DEFAULT_MSN_VERTICAL_URL
    assert ("%5B" + "https") not in DEFAULT_MSN_VERTICAL_URL
    assert DEFAULT_MSN_VERTICAL_URL == TARGET_URL


def test_dry_run_plan_does_not_create_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "new_capture"
        plan = run_live_viewable_capture(target_url=TARGET_URL, output_dir=output_dir, dry_run=True)
        assert plan.status == LIVE_VIEWABLE_CAPTURE_DRY_RUN
        assert not output_dir.exists()
        assert any("Open rendered-page.html" in step for step in plan.manual_next_steps)


def test_existing_nonempty_output_dir_is_refused() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "existing"
        output_dir.mkdir()
        (output_dir / "old.txt").write_text("do not overwrite", encoding="utf-8")
        try:
            run_live_viewable_capture(
                target_url=TARGET_URL,
                output_dir=output_dir,
                dependency_check=lambda: (),
                validation_runner=_fake_validation_runner,
            )
        except FileExistsError as error:
            assert "already exists" in str(error)
        else:
            raise AssertionError("expected nonempty output directory refusal")


def test_missing_runtime_dependencies_write_actionable_validation_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "capture"
        result = run_live_viewable_capture(
            target_url=TARGET_URL,
            output_dir=output_dir,
            write_validation_json=True,
            dependency_check=lambda: ("playwright is not importable; install/configure Playwright before running live capture",),
            validation_runner=_fake_validation_runner,
        )
        assert result.status == LIVE_VIEWABLE_CAPTURE_BLOCKED
        validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
        assert "playwright" in " ".join(validation["errors"])
        assert validation["replay_tested"] is False


def test_fake_live_capture_writes_expected_side_by_side_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "capture"
        accepted = Path(tmp) / "old" / "archive.wacz"
        _write(accepted, b"accepted-old-capture")
        before = accepted.read_bytes()
        seen: dict[str, str] = {}

        def recording_runner(*, source_url: str, output_directory: str | Path, headless: bool = True):
            seen["source_url"] = source_url
            return _fake_validation_runner(source_url=source_url, output_directory=output_directory, headless=headless)

        result = run_live_viewable_capture(
            target_url=TARGET_URL,
            output_dir=output_dir,
            runner_source_url=DEFAULT_MSN_VERTICAL_URL,
            capture_comments=True,
            write_wacz=True,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=True,
            write_validation_json=True,
            write_local_viewer=True,
            dependency_check=lambda: (),
            validation_runner=recording_runner,
        )
        assert result.status == LIVE_VIEWABLE_CAPTURE_COMPLETED
        assert seen["source_url"] == DEFAULT_MSN_VERTICAL_URL
        assert (output_dir / "rendered-page.html").is_file()
        assert (output_dir / "rendered-page.warc").is_file()
        assert (output_dir / "rendered-page.warc.gz").is_file()
        assert (output_dir / "archive.viewable-live-capture.wacz").is_file()
        assert (output_dir / "screenshots" / "article-top.png").is_file()
        assert (output_dir / "screenshots" / "full-page.png").is_file()
        assert (output_dir / "screenshots" / "comments-region.png").is_file()
        assert (output_dir / "capture-manifest.json").is_file()
        assert (output_dir / "validation.json").is_file()
        assert (output_dir / "local_viewer" / "local-viewer-index.html").is_file()
        validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
        assert result.validation_json_hash == hashlib.sha256((output_dir / "validation.json").read_bytes()).hexdigest()
        assert "validation_json_hash" not in validation
        assert validation["target_url"] == TARGET_URL
        assert validation["requested_target_url"] == TARGET_URL
        assert validation["runner_source_url"] == DEFAULT_MSN_VERTICAL_URL
        assert validation["canonical_source_url"] == DEFAULT_MSN_VERTICAL_URL.split("#", 1)[0]
        assert validation["local_viewer_index_path"] == result.local_viewer_index_path
        assert validation["article_title_found"] is True
        assert validation["article_body_found"] is True
        assert validation["comments_found"] is True
        assert validation["comment_count"] == 1
        assert validation["replay_tested"] is False
        assert validation["replay_result"] == "NOT_TESTED"
        assert validation["archived_page_not_found"] == "manual_review_required"
        with gzip.open(output_dir / "rendered-page.warc.gz", "rb") as handle:
            warc_text = handle.read().decode("utf-8", errors="replace")
        assert "GET /en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o" in warc_text
        assert accepted.read_bytes() == before


def test_runner_value_error_is_written_to_validation_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "capture"

        def rejecting_runner(*, source_url: str, output_directory: str | Path, headless: bool = True):
            raise ValueError("rendered MSN validation is approved for the configured MSN URL only")

        result = run_live_viewable_capture(
            target_url=TARGET_URL,
            output_dir=output_dir,
            runner_source_url=DEFAULT_MSN_VERTICAL_URL,
            write_wacz=True,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=True,
            write_validation_json=True,
            write_local_viewer=True,
            dependency_check=lambda: (),
            validation_runner=rejecting_runner,
        )

        assert result.status == LIVE_VIEWABLE_CAPTURE_BLOCKED
        validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
        assert validation["status"] == LIVE_VIEWABLE_CAPTURE_BLOCKED
        assert validation["target_url"] == TARGET_URL
        assert validation["requested_target_url"] == TARGET_URL
        assert validation["runner_source_url"] == DEFAULT_MSN_VERTICAL_URL
        assert "approved for the configured MSN URL" in " ".join(validation["errors"])
        assert (output_dir / "local_viewer" / "local-viewer-index.html").is_file()


def _fake_validation_runner_without_warc(*, source_url: str, output_directory: str | Path, headless: bool = True):
    result = _fake_validation_runner(source_url=source_url, output_directory=output_directory, headless=headless)
    source_root = Path(result.output_directory)
    (source_root / "local_web_archive" / "archive" / "data.warc").unlink()
    (source_root / "local_web_archive" / "archive.wacz").unlink()
    return result


def test_rendered_html_fallback_writes_warc_when_browser_warc_is_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "capture"
        result = run_live_viewable_capture(
            target_url=TARGET_URL,
            output_dir=output_dir,
            write_wacz=False,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=False,
            write_validation_json=True,
            dependency_check=lambda: (),
            validation_runner=_fake_validation_runner_without_warc,
        )
        assert result.status == LIVE_VIEWABLE_CAPTURE_COMPLETED
        validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
        assert validation["warc_source"] == "rendered_html_fallback"
        with gzip.open(output_dir / "rendered-page.warc.gz", "rb") as handle:
            warc_text = handle.read().decode("utf-8", errors="replace")
        assert "GET /en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o" in warc_text
        assert "Content-Type: text/html; charset=utf-8" in warc_text
def test_validation_json_never_claims_replay_visual_success_before_manual_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "capture"
        run_live_viewable_capture(
            target_url=TARGET_URL,
            output_dir=output_dir,
            write_wacz=True,
            write_warc=True,
            write_rendered_html=True,
            write_screenshots=True,
            write_validation_json=True,
            dependency_check=lambda: (),
            validation_runner=_fake_validation_runner,
        )
        validation = json.loads((output_dir / "validation.json").read_text(encoding="utf-8"))
        assert validation["replay_tested"] is False
        assert validation["replay_result"] == "NOT_TESTED"
        assert validation["article_visible"] == "manual_review_required"
        assert validation["comments_visible"] == "manual_review_required"
        assert "REPLAY_VISUALLY_VERIFIED" not in json.dumps(validation, sort_keys=True)
def run_self_test() -> None:
    test_target_url_and_output_dir_are_required()
    test_configured_msn_url_is_raw_and_not_markdown_link()
    test_dry_run_plan_does_not_create_outputs()
    test_existing_nonempty_output_dir_is_refused()
    test_missing_runtime_dependencies_write_actionable_validation_json()
    test_fake_live_capture_writes_expected_side_by_side_outputs()
    test_runner_value_error_is_written_to_validation_json()
    test_rendered_html_fallback_writes_warc_when_browser_warc_is_missing()
    test_validation_json_never_claims_replay_visual_success_before_manual_review()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_live_viewable_capture_test passed")
