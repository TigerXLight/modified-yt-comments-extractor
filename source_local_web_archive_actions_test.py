from __future__ import annotations
# R42FJ optional dependency guard: warcio
import importlib.util as _r42fj_importlib_util
import unittest as _r42fj_unittest
if _r42fj_importlib_util.find_spec('warcio') is None:
    raise _r42fj_unittest.SkipTest('optional WARC/archive dependency warcio is not installed')
# R42FJ optional dependency guard end

import gzip
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from source_local_web_archive_actions import (
    OPEN_ARCHIVE_PREVIEWED,
    REPLAY_FAILED,
    REPLAY_OPENED,
    SHOW_FILES_PREVIEWED,
    STRUCTURAL_WACZ_VALID,
    USER_VISUAL_CONFIRMATION_REQUIRED,
    WACZ_REPLAY_COMPATIBILITY_REPAIRED,
    VIEWER_CONFIGURED,
    VIEWER_NOT_CONFIGURED,
    build_local_web_archive_action_state,
    build_replayweb_browser_pwa_file_state,
    build_replaywebpage_open_preview,
    build_show_local_web_archive_files_preview,
    detect_replaywebpage_viewer,
    local_web_archive_status_lines,
    open_archive_with_replaywebpage,
    parse_replayweb_release_metadata,
    repair_local_web_archive_wacz,
    show_local_web_archive_files,
    verify_local_web_archive_package,
)
from source_msn_rendered_browser_validation import CapturedResponse, write_standard_wacz, write_standard_warc


SOURCE_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _sha256(path)


def _build_fixture_archive(root: Path) -> tuple[Path, Path, str, str]:
    comments_json = root / "android_mobile_chromium" / "comments.json"
    comments_jsonl = root / "android_mobile_chromium" / "comments_incremental.jsonl"
    reconciliation = root / "android_mobile_chromium" / "comments_provider_reconciliation.json"
    faithful = root / "android_mobile_chromium" / "faithful_comments_visible.png"
    derived = root / "android_mobile_chromium" / "derived_comments_full_thread.png"
    _write_json(
        comments_json,
        [
            {"comment_id": "c1", "depth": 0, "text": "synthetic root"},
            {"comment_id": "r1", "depth": 1, "parent_comment_id": "c1", "text": "synthetic reply"},
        ],
    )
    comments_jsonl.write_text(
        json.dumps({"comment_id": "c1"}) + "\n" + json.dumps({"comment_id": "r1"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        reconciliation,
        {
            "api_reconciliation": {"declared_total_count": 2},
            "provider_reconciliation": {
                "comments_complete": True,
                "reply_record_count": 1,
                "root_record_count": 1,
            },
        },
    )
    faithful.write_bytes(b"\x89PNG\r\n\x1a\nfixture faithful")
    derived.write_bytes(b"\x89PNG\r\n\x1a\nfixture derived")
    warc = write_standard_warc(
        output_warc_path=root / "local_web_archive" / "archive" / "data.warc",
        responses=(
            CapturedResponse(
                url=SOURCE_URL + "?PC=EMMX01",
                status=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=b"<html><body>fixture story</body></html>",
                resource_type="document",
            ),
            CapturedResponse(
                url="https://assets.msn.com/Z-script.js",
                status=200,
                headers={"content-type": "application/javascript"},
                body=b"console.log('fixture')",
                resource_type="script",
            ),
        ),
        timestamp_utc="2026-08-09T00:00:00Z",
    )
    wacz = write_standard_wacz(
        output_wacz_path=root / "local_web_archive" / "archive.wacz",
        warc_path=warc["path"],
        index_rows=warc["index_rows"],
        source_url=SOURCE_URL,
        title="Arrest made after shot fired outside York mosque",
        text="Arrest made after shot fired outside York mosque fixture article text.",
        timestamp_utc="2026-08-09T00:00:00Z",
    )
    manifest = {
        "schema_version": "fixture_manifest_v1",
        "source_url": SOURCE_URL,
        "artifacts": [
            {
                "label": "android_mobile_chromium_comments_json",
                "path": str(comments_json),
                "sha256": _sha256(comments_json),
            },
            {
                "label": "android_mobile_chromium_comments_incremental_jsonl",
                "path": str(comments_jsonl),
                "sha256": _sha256(comments_jsonl),
            },
            {
                "label": "android_mobile_chromium_comments_provider_reconciliation",
                "path": str(reconciliation),
                "sha256": _sha256(reconciliation),
            },
            {
                "label": "android_mobile_chromium_faithful_comments_screenshot",
                "path": str(faithful),
                "sha256": _sha256(faithful),
            },
            {
                "label": "android_mobile_chromium_derived_comments_full_thread_screenshot",
                "path": str(derived),
                "sha256": _sha256(derived),
            },
            {
                "label": "standard_wacz",
                "path": wacz["path"],
                "sha256": wacz["sha256"],
            },
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_sha = _write_json(manifest_path, manifest)
    return Path(wacz["path"]), manifest_path, wacz["sha256"], manifest_sha


def _rewrite_fixture_as_legacy_replay_incompatible(wacz_path: Path) -> None:
    with zipfile.ZipFile(wacz_path, "r") as source:
        payloads = {name: source.read(name) for name in source.namelist()}

    package = json.loads(payloads["datapackage.json"].decode("utf-8"))
    package["profile"] = "data-package"
    package["wacz_version"] = "1.2.0"
    package["mainPageUrl"] = SOURCE_URL + "#comments"
    package["home"]["url"] = SOURCE_URL + "#comments"
    payloads["datapackage.json"] = (json.dumps(package, indent=2, sort_keys=True) + "\n").encode("utf-8")

    pages = []
    for line in payloads["pages/pages.jsonl"].decode("utf-8").splitlines():
        row = json.loads(line)
        if isinstance(row, dict) and row.get("url"):
            row["url"] = str(row["url"]) + "#comments"
        pages.append(json.dumps(row, sort_keys=True))
    payloads["pages/pages.jsonl"] = ("\n".join(pages) + "\n").encode("utf-8")

    index_lines = gzip.decompress(payloads["indexes/index.cdx.gz"]).decode("utf-8").splitlines()
    broken = []
    for line in reversed(index_lines):
        searchable, timestamp, row_json = line.split(" ", 2)
        broken.append(searchable.upper() + " " + timestamp + " " + row_json)
    payloads["indexes/index.cdx.gz"] = gzip.compress(("\n".join(broken) + "\n").encode("utf-8"), mtime=0)

    with zipfile.ZipFile(wacz_path, "w") as output:
        for name, payload in payloads.items():
            info = zipfile.ZipInfo(name)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED if name.startswith("archive/") or name.endswith(".gz") else zipfile.ZIP_DEFLATED
            output.writestr(info, payload)


def test_parse_replayweb_release_metadata_selects_official_windows_assets() -> None:
    release = parse_replayweb_release_metadata(
        {
            "tag_name": "v2.4.7",
            "name": "ReplayWeb.page App 2.4.7",
            "html_url": "https://github.com/webrecorder/replayweb.page/releases/tag/v2.4.7",
            "assets": [
                {
                    "name": "ReplayWeb.page-2.4.7.exe",
                    "browser_download_url": "https://github.com/webrecorder/replayweb.page/releases/download/v2.4.7/ReplayWeb.page-2.4.7.exe",
                    "size": 194570584,
                    "content_type": "application/octet-stream",
                },
                {"name": "latest.yml", "browser_download_url": "https://example.invalid/latest.yml", "size": 1},
            ],
        }
    )

    assert release.tag_name == "v2.4.7"
    assert release.release_name == "ReplayWeb.page App 2.4.7"
    assert [asset.name for asset in release.windows_assets] == ["ReplayWeb.page-2.4.7.exe"]
    assert release.windows_assets[0].size_bytes == 194570584


def test_detect_replaywebpage_viewer_prefers_configured_env_path() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        exe = Path(temp_dir) / "ReplayWeb.page-2.4.7.exe"
        exe.write_bytes(b"fixture executable placeholder")

        detection = detect_replaywebpage_viewer(
            env={"REPLAYWEBPAGE_PATH": str(exe)},
            candidate_paths=(),
        )

        assert detection.status == VIEWER_CONFIGURED
        assert detection.executable_name == exe.name
        assert detection.version_hint == "2.4.7"
        assert detection.executable_sha256 == _sha256(exe)
        assert detection.detection_source == "REPLAYWEBPAGE_PATH"


def test_missing_replaywebpage_viewer_is_nonfatal() -> None:
    detection = detect_replaywebpage_viewer(
        env={"REPLAYWEBPAGE_PATH": ""},
        candidate_paths=("Z:/missing/ReplayWeb.page.exe",),
    )

    assert detection.status == VIEWER_NOT_CONFIGURED
    assert "Set REPLAYWEBPAGE_PATH" in detection.configuration_help


def test_verify_local_web_archive_package_checks_wacz_manifest_and_comments_evidence() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wacz_path, manifest_path, wacz_sha, manifest_sha = _build_fixture_archive(Path(temp_dir))

        result = verify_local_web_archive_package(
            wacz_path,
            manifest_path=manifest_path,
            expected_source_url=SOURCE_URL,
            expected_wacz_sha256=wacz_sha,
            expected_manifest_sha256=manifest_sha,
            expected_comment_count=2,
        )

        assert result.status == STRUCTURAL_WACZ_VALID
        assert result.required_entries_present is True
        assert result.zip_integrity_ok is True
        assert result.wacz_sha256 == wacz_sha
        assert result.manifest_sha256 == manifest_sha
        assert result.expected_source_url_found is True
        assert result.comments_json_count == 2
        assert result.comments_jsonl_count == 2
        assert result.declared_comment_count == 2
        assert result.top_level_comment_count == 1
        assert result.reply_count == 1
        assert result.comments_complete is True
        assert result.comments_evidence_status == "COMMENTS_EVIDENCE_VERIFIED"
        assert result.faithful_comments_screenshot_name == "faithful_comments_visible.png"
        assert result.derived_comments_visual_name == "derived_comments_full_thread.png"


def test_verify_local_web_archive_package_rejects_wrong_expected_hash_or_url() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wacz_path, manifest_path, _wacz_sha, manifest_sha = _build_fixture_archive(Path(temp_dir))

        result = verify_local_web_archive_package(
            wacz_path,
            manifest_path=manifest_path,
            expected_source_url="https://www.msn.com/wrong-story",
            expected_wacz_sha256="0" * 64,
            expected_manifest_sha256=manifest_sha,
        )

        assert result.status == REPLAY_FAILED
        assert "WACZ SHA-256 does not match expected value" in result.errors
        assert "Expected source URL was not found in WACZ metadata/index" in result.errors


def test_repair_local_web_archive_wacz_fixes_replay_lookup_without_touching_warc() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        wacz_path, _manifest_path, _wacz_sha, _manifest_sha = _build_fixture_archive(root)
        _rewrite_fixture_as_legacy_replay_incompatible(wacz_path)
        original_sha = _sha256(wacz_path)
        with zipfile.ZipFile(wacz_path, "r") as bundle:
            original_warc = bundle.read("archive/data.warc")

        before = verify_local_web_archive_package(wacz_path, expected_source_url=SOURCE_URL + "#comments")
        assert before.status == REPLAY_FAILED
        assert before.datapackage_profile == "data-package"
        assert before.deprecated_datapackage_fields == ("wacz_version", "mainPageUrl")
        assert before.index_sorted is False
        assert before.index_search_keys_canonical is False
        assert before.replay_lookup_ready is False

        repaired_path = root / "local_web_archive" / "archive.replayweb-fixed.wacz"
        repair = repair_local_web_archive_wacz(wacz_path, output_path=repaired_path)

        assert repair.status == WACZ_REPLAY_COMPATIBILITY_REPAIRED
        assert repair.verification_status == STRUCTURAL_WACZ_VALID
        assert repair.input_sha256 == original_sha
        assert _sha256(wacz_path) == original_sha
        assert repair.original_preserved is True
        assert repair.rewritten_index_count == 1
        assert repair.removed_legacy_fields == ("mainPageUrl", "wacz_version")

        after = verify_local_web_archive_package(repaired_path, expected_source_url=SOURCE_URL + "#comments")
        assert after.status == STRUCTURAL_WACZ_VALID
        assert after.datapackage_profile == "wacz"
        assert after.deprecated_datapackage_fields == ()
        assert after.index_sorted is True
        assert after.index_search_keys_canonical is True
        assert after.replay_lookup_ready is True
        assert after.expected_source_url_found is True
        with zipfile.ZipFile(repaired_path, "r") as bundle:
            assert bundle.read("archive/data.warc") == original_warc
            package = json.loads(bundle.read("datapackage.json").decode("utf-8"))
            assert package["home"]["url"] == SOURCE_URL
            assert "#comments" not in bundle.read("pages/pages.jsonl").decode("utf-8")
            index_lines = gzip.decompress(bundle.read("indexes/index.cdx.gz")).decode("utf-8").splitlines()
            assert index_lines == sorted(index_lines, key=lambda line: line.encode("utf-8"))
            assert all(line.split(" ", 1)[0] == line.split(" ", 1)[0].lower() for line in index_lines)

        same_path = repair_local_web_archive_wacz(wacz_path, output_path=wacz_path)
        assert same_path.status == REPLAY_FAILED
        assert "different file" in same_path.errors[0]
        overwrite = repair_local_web_archive_wacz(wacz_path, output_path=repaired_path)
        assert overwrite.status == REPLAY_FAILED
        assert "will not be overwritten" in overwrite.errors[0]


def test_open_and_show_files_build_safe_argument_arrays_without_shell() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        wacz_path, _manifest_path, _wacz_sha, _manifest_sha = _build_fixture_archive(root)
        exe = root / "ReplayWeb.page-2.4.7.exe"
        exe.write_bytes(b"fixture executable placeholder")
        viewer = detect_replaywebpage_viewer(env={"REPLAYWEBPAGE_PATH": str(exe)}, candidate_paths=())

        open_preview = build_replaywebpage_open_preview(wacz_path, viewer=viewer)
        show_preview = build_show_local_web_archive_files_preview(wacz_path)

        assert open_preview.status == OPEN_ARCHIVE_PREVIEWED
        assert open_preview.argv == (str(exe), str(wacz_path))
        assert open_preview.shell is False
        assert show_preview.shell is False
        assert str(wacz_path) in show_preview.argv[-1]

        launched: list[tuple[str, ...]] = []
        opened = open_archive_with_replaywebpage(
            wacz_path,
            viewer=viewer,
            launcher=lambda argv: launched.append(tuple(argv)),
        )
        shown = show_local_web_archive_files(
            wacz_path,
            launcher=lambda argv: launched.append(tuple(argv)),
        )

        assert opened.status == REPLAY_OPENED
        assert shown.status == SHOW_FILES_PREVIEWED
        assert launched[0] == (str(exe), str(wacz_path))
        assert launched[1] == show_preview.argv


def test_local_archive_action_state_keeps_replay_visual_confirmation_separate() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        wacz_path, manifest_path, wacz_sha, manifest_sha = _build_fixture_archive(Path(temp_dir))

        state = build_local_web_archive_action_state(
            wacz_path=wacz_path,
            manifest_path=manifest_path,
            expected_source_url=SOURCE_URL,
            expected_wacz_sha256=wacz_sha,
            expected_manifest_sha256=manifest_sha,
            expected_comment_count=2,
            viewer=detect_replaywebpage_viewer(env={}, candidate_paths=()),
        )
        lines = local_web_archive_status_lines(state)

        assert state.verify_status == STRUCTURAL_WACZ_VALID
        assert state.open_archive_status == VIEWER_NOT_CONFIGURED
        assert state.replay_visual_status == USER_VISUAL_CONFIRMATION_REQUIRED
        assert "Verify: STRUCTURAL_WACZ_VALID" in lines
        assert any("2/2" in line for line in lines)
        assert any("Network actions performed by status preview: none" in line for line in lines)


def test_browser_pwa_file_state_documents_direct_file_url_limitation() -> None:
    state = build_replayweb_browser_pwa_file_state("archive.wacz")

    assert state["status"] == USER_VISUAL_CONFIRMATION_REQUIRED
    assert state["direct_file_url_supported"] is False
    assert "file chooser" in state["note"]


def run_self_test() -> None:
    test_parse_replayweb_release_metadata_selects_official_windows_assets()
    test_detect_replaywebpage_viewer_prefers_configured_env_path()
    test_missing_replaywebpage_viewer_is_nonfatal()
    test_verify_local_web_archive_package_checks_wacz_manifest_and_comments_evidence()
    test_verify_local_web_archive_package_rejects_wrong_expected_hash_or_url()
    test_repair_local_web_archive_wacz_fixes_replay_lookup_without_touching_warc()
    test_open_and_show_files_build_safe_argument_arrays_without_shell()
    test_local_archive_action_state_keeps_replay_visual_confirmation_separate()
    test_browser_pwa_file_state_documents_direct_file_url_limitation()


if __name__ == "__main__":
    run_self_test()
    print("source_local_web_archive_actions.py: OK")


