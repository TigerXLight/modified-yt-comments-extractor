from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_account_tracking_export_surface_r43d import (
    R43D_PASS_STATUS,
    build_twitter_x_account_tracking_export_surface_r43d,
)
from profile_media_twitter_x_live_evidence_to_account_ledger_r43r import (
    R43R_PASS_STATUS,
    materialize_live_twitter_x_evidence_to_account_ledger_r43r,
)


class _FakeR43NResult:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


class _FakeR43NHarness:
    def __init__(self, runner_root: Path) -> None:
        self.runner_root = runner_root
        self.requests: list[dict] = []

    def run_smoke(self, request: dict) -> _FakeR43NResult:
        self.requests.append(dict(request))
        run_dir = Path(request["output_root"]) / "r43n_fixture_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        r43o_dir = run_dir / "r43o"
        r43o_dir.mkdir(parents=True, exist_ok=True)
        r43p_receipt = r43o_dir / "r43p_runner_output_promotion_receipt.json"
        r43o_receipt = r43o_dir / "visible_session_binding_receipt.json"
        r43n_receipt = run_dir / "live_smoke_observation_receipt.json"
        live_paths = [
            str(self.runner_root / "rendered_dom_snapshot.html"),
            str(self.runner_root / "screenshot.png"),
            str(self.runner_root / "visible_browser_media_observation_store" / "visible_browser_media_observations.ndjson"),
        ]
        r43p_payload = {
            "status": "PASS_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION",
            "runner_output_dir": str(self.runner_root),
            "promoted_live_observation_paths": live_paths,
            "promoted_observed_post_count": 3,
            "promoted_observed_media_count": 1,
            "promoted_observed_screenshot_count": 1,
            "promoted_network_event_count": 1,
            "promoted_api_page_count": 1,
            "promoted_response_body_count": 1,
            "promoted_non_fixture_observation_evidence": True,
        }
        _write_json(r43p_receipt, r43p_payload)
        receipt = {
            "status": "PASS_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT",
            "blocker_reason": "",
            "normalized_url": request["account_url"],
            "r43o_visible_session_binding_status": "PASS_R43O_LIVE_TWITTER_X_VISIBLE_SESSION_BINDING",
            "visible_session_binding_receipt_path": str(r43o_receipt),
            "r43p_runner_output_promotion_status": "PASS_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION",
            "r43p_runner_output_promotion_receipt_path": str(r43p_receipt),
            "promoted_observed_post_count": 3,
            "promoted_observed_media_count": 1,
            "promoted_observed_screenshot_count": 1,
            "promoted_network_event_count": 1,
            "promoted_api_page_count": 1,
            "promoted_response_body_count": 1,
            "promoted_live_observation_paths": live_paths,
            "promoted_non_fixture_observation_evidence": True,
        }
        _write_json(r43o_receipt, receipt)
        _write_json(r43n_receipt, receipt)
        return _FakeR43NResult(
            {
                "status": "PASS_R43N_LIVE_TWITTER_X_SINGLE_ACCOUNT_SMOKE_HARNESS_REAL_OBSERVATION_RECEIPT",
                "run_dir": str(run_dir),
                "report_json_path": str(run_dir / "R43N_REPORT.json"),
                "progress_events_path": str(run_dir / "live_smoke_progress_events.ndjson"),
                "materialization_receipts_index_path": str(run_dir / "live_smoke_materialization_receipts_index.json"),
                "observation_receipt_path": str(r43n_receipt),
                "observation_receipt": receipt,
                "blocker_reason": "",
            }
        )


def test_r43r_materializes_dom_articles_to_account_ledger() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner_root = root / "runner_output"
        _write_runner_fixture(runner_root)
        result = materialize_live_twitter_x_evidence_to_account_ledger_r43r(
            {
                "source_url": "[https://x.com/examaddaorg](https://x.com/examaddaorg)",
                "account_handle": "examaddaorg",
                "capture_timestamp": "20260917T060000Z",
                "runner_output_dir": str(runner_root),
                "ledger_output_root": str(root / "source_exports" / "twitter_x"),
            }
        )
        assert result.status == R43R_PASS_STATUS
        capture_dir = Path(result.account_capture_dir)
        assert (capture_dir / "account_record.md").is_file()
        assert len((capture_dir / "account_timeline.ndjson").read_text(encoding="utf-8").splitlines()) == 3
        assert len(list((capture_dir / "dates").glob("*"))) >= 2
        assert len(list(capture_dir.glob("dates/*/post_*/post.md"))) == 3
        assert len(list(capture_dir.glob("dates/*/post_*/static_screenshot.png"))) == 3

        account_record = (capture_dir / "account_record.md").read_text(encoding="utf-8")
        timeline_rows = [
            json.loads(line)
            for line in (capture_dir / "account_timeline.ndjson").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        media_index = json.loads((capture_dir / "media_index.json").read_text(encoding="utf-8"))
        fast_summary = result.account_ledger_summary["fast_media_binding_summary"]
        assert fast_summary["raw_bound_media_candidate_count"] == fast_summary["bound_media_count"]
        assert fast_summary["ledger_media_item_count"] == len(media_index)
        assert result.account_ledger_summary["r43t_ledger_media_item_count"] == len(media_index)
        assert result.account_ledger_summary["r43t_raw_bound_media_candidate_count"] >= result.account_ledger_summary["r43t_ledger_media_item_count"]
        post_jsons = [json.loads(path.read_text(encoding="utf-8")) for path in capture_dir.glob("dates/*/post_*/post.json")]
        ambiguous_post_json = capture_dir / "dates" / "unknown_date" / "post_3333333333333333333" / "post.json"
        wrong_ambiguous_post_json = capture_dir / "dates" / "2026-09-17" / "post_3333333333333333333" / "post.json"

        assert "First visible tweet with text" in account_record
        assert "dates/unknown_date/" in account_record
        assert ambiguous_post_json.is_file()
        assert not wrong_ambiguous_post_json.exists()
        ambiguous_post = json.loads(ambiguous_post_json.read_text(encoding="utf-8"))
        assert ambiguous_post["visible_timestamp"] == "unknown_date"
        assert ambiguous_post["visible_date_folder"] == "unknown_date"
        assert ambiguous_post["date_source"] == "unknown_ambiguous_month_day_visible_time"
        assert any("Ambiguous visible date" in warning for warning in ambiguous_post["warnings"])
        timeline_333 = next(row for row in timeline_rows if row["record_id"] == "3333333333333333333")
        assert timeline_333["visible_date_folder"] == "unknown_date"
        assert timeline_333["date_source"] == "unknown_ambiguous_month_day_visible_time"
        timeline_222 = next(row for row in timeline_rows if row["record_id"] == "2222222222222222222")
        assert timeline_222["visible_date_folder"] == "2026-09-17"
        assert timeline_222["date_source"] == "capture_date_from_relative_visible_time"
        assert any(item["media_url"].startswith("https://pbs.twimg.com/media/") for item in media_index)
        assert any(item["binding_reason"] == "status_id_match" for item in media_index)
        assert any(item["binding_reason"] == "canonical_post_url_match" for item in media_index)
        assert any(item["binding_reason"] == "article_dom_media_url_match" for item in media_index)
        assert any("/media/images/" in item["local_export_path"].replace("\\", "/") and item["copied_local_bytes"] for item in media_index)
        assert any("/media/videos/" in item["local_export_path"].replace("\\", "/") and item["copied_local_bytes"] for item in media_index)
        assert any("/media/manifests/" in item["local_export_path"].replace("\\", "/") for item in media_index)
        assert any("/media/segments/" in item["local_export_path"].replace("\\", "/") for item in media_index)
        assert (capture_dir / "unbound_media" / "media_index.json").is_file()
        assert len(list(capture_dir.glob("dates/*/post_*/static_screenshot_receipt.json"))) == 3
        assert not any("abs.twimg.com" in item.get("media_url", "") for item in media_index)
        assert not any("profile_images" in item.get("media_url", "") for item in media_index)
        assert all(item.get("remote_download_performed_by_r43a") is False for item in media_index)
        assert all(row["screenshot_scope"] == "session_visible_page_fallback" for row in post_jsons)
        assert all(row["screenshot_is_article_crop"] is False for row in post_jsons)


def test_r43d_explicit_live_materializes_r43r_account_ledger() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner_root = root / "runner_output"
        _write_runner_fixture(runner_root)
        harness = _FakeR43NHarness(runner_root)
        surface = build_twitter_x_account_tracking_export_surface_r43d(
            live_smoke_harness=harness,
            output_root=root / "r43d",
        )
        result = surface.run_account_export(
            {
                "account_url": "https://x.com/examaddaorg",
                "account_handle": "examaddaorg",
                "capture_timestamp": "20260917T060000Z",
                "explicit_live_mode": True,
                "run_visible_live": True,
                "browser_user_data_dir": "C:/Users/fahad/AppData/Local/YTCE/twitter_test_profile",
                "browser_executable_path": "C:/Users/fahad/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
                "max_items": 3,
                "max_scrolls": 2,
            }
        )
        assert result.status == R43D_PASS_STATUS
        assert Path(result.account_record_path).is_file()
        assert Path(result.manifest_path).is_file()
        assert Path(result.media_index_path).is_file()
        assert result.record_count == 3
        assert result.post_count == 3
        assert result.media_count >= 6
        assert result.screenshot_count == 3
        assert result.account_ledger_summary["ledger_post_count"] == 3
        assert result.account_ledger_summary["fast_media_binding_summary"]["bound_media_count"] >= 6
        assert result.live_evidence_summary["account_ledger_summary"]["ledger_post_count"] == 3
        assert harness.requests[0]["browser_executable_path"].endswith("chrome.exe")


def _write_runner_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "screenshot.png").write_bytes(b"r43r screenshot")
    (root / "network_events.jsonl").write_text("{}\n", encoding="utf-8")
    local_image = root / "session_image.jpg"
    local_video = root / "session_video.mp4"
    local_image.write_bytes(b"R43T_LOCAL_IMAGE")
    local_video.write_bytes(b"R43T_LOCAL_VIDEO")
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
            "canonical_media_url": "https://pbs.twimg.com/media/valid_fixture.jpg?format=jpg&name=large",
            "media_class": "image",
        },
        {
            "canonical_media_url": "https://abs.twimg.com/icons/decorative.png",
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
    segments = [
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
    (store / "visible_browser_media_segments.ndjson").write_text("\n".join(json.dumps(row) for row in segments) + "\n", encoding="utf-8")
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
    (root / "rendered_dom_snapshot.html").write_text(
        """
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
<div>Relative-time tweet with attached media.</div>
<img src="https://pbs.twimg.com/media/valid_fixture.jpg?format=jpg&amp;name=large">
<img src="https://abs.twimg.com/icons/decorative.png">
</article>
<article data-testid="tweet">
<div>Exam Adda</div><div>@examaddaorg</div>
<time>Sep 14</time>
<a href="https://x.com/examaddaorg/status/3333333333333333333">status</a>
<div>Ambiguous month-day tweet.</div>
<img src="https://pbs.twimg.com/profile_images/avatar.jpg">
</article>
</body></html>
""",
        encoding="utf-8",
    )


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    test_r43r_materializes_dom_articles_to_account_ledger()
    test_r43d_explicit_live_materializes_r43r_account_ledger()
    print("R43R tests passed")
