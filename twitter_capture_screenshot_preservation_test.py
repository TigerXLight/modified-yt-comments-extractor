from __future__ import annotations

import tempfile
from pathlib import Path

from twitter_capture_screenshot_preservation import (
    build_capture_preservation_manifest,
    build_reference_family_capture_matrix,
    build_twitter_exporter_safety_matrix,
    plan_full_page_capture,
    render_capture_preservation_summary,
)


SOURCE_URL = "https://x.com/example/with_replies"


def test_full_page_plan_steps_to_bottom_with_overlap() -> None:
    plan = plan_full_page_capture(
        source_url=SOURCE_URL,
        page_width=390,
        page_height=2200,
        viewport_width=390,
        viewport_height=720,
        overlap_px=120,
    )
    assert plan.total_steps == 4
    assert plan.steps[0].y == 0
    assert plan.steps[-1].y == 1480
    assert plan.steps[-1].y + plan.steps[-1].capture_height == 2200
    assert plan.completion_boundary_reached is True
    assert plan.steps[1].overlap_top_px == 120
    assert plan.steps[-1].filename.endswith("y001480.png")
    assert "GoFullPage/PageCap/webshot-style" in plan.reference_family
    assert plan.browser_extension_dependency_required is False
    assert plan.external_upload_performed is False


def test_capture_manifest_records_hashes_and_offline_safety() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        viewport = root / "viewport.txt"
        full = root / "full-page.txt"
        dom = root / "rendered_dom_snapshot.html"
        viewport.write_text("viewport screenshot placeholder\n", encoding="utf-8")
        full.write_text("full page screenshot placeholder\n", encoding="utf-8")
        dom.write_text("<html><body>Rendered X timeline fixture</body></html>\n", encoding="utf-8")
        manifest = build_capture_preservation_manifest(
            source_url=SOURCE_URL,
            output_folder=root,
            page_width=390,
            page_height=1600,
            viewport_width=390,
            viewport_height=700,
            cursor_state={
                "pages_count": 1,
                "last_cursor_out": "cursor-next",
                "soft_page_budget": 3,
                "rate_limit_remaining": 8,
            },
            now_epoch=1_800_000_000,
            rendered_dom_path=dom,
            viewport_screenshot_path=viewport,
            full_page_screenshot_path=full,
            media_urls=("https://pbs.twimg.com/media/example.jpg",),
        )
        data = manifest.to_dict()
        assert data["source_url"] == SOURCE_URL
        assert data["canonical_url"].startswith("https://x.com/")
        assert data["rendered_dom_sha256"]
        assert data["viewport_screenshot"]["sha256"]
        assert data["full_page_screenshot"]["size_bytes"] > 0
        assert data["cursor_continuation"]["safe_to_continue"] is True
        assert data["cursor_continuation"]["no_network_action"] is True
        assert data["no_write_actions"] is True
        assert data["browser_launch_performed"] is False
        assert data["web_download_performed"] is False
        assert data["media_download_performed"] is False
        assert data["official_x_api_used"] is False
        assert "scroll_steps:" in render_capture_preservation_summary(manifest)


def test_cursor_continuation_respects_soft_pause_and_cooldown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = build_capture_preservation_manifest(
            source_url=SOURCE_URL,
            output_folder=tmp,
            page_width=390,
            page_height=1200,
            viewport_width=390,
            viewport_height=700,
            cursor_state={
                "pages_count": 3,
                "last_cursor_out": "cursor-after-budget",
                "soft_page_budget": 3,
                "rate_limit_remaining": 0,
                "rate_limit_reset_epoch": 1_900_000_000,
            },
            now_epoch=1_800_000_000,
        )
        cursor = manifest.cursor_continuation
        assert cursor.safe_to_continue is False
        assert cursor.soft_page_budget_reached is True
        assert cursor.cooldown_respected is False
        assert "soft_page_budget_pause_boundary" in cursor.warnings
        assert "cooldown_until_reset_boundary" in cursor.warnings
        assert manifest.web_download_performed is False


def test_reference_and_exporter_matrices_are_safe() -> None:
    reference = build_reference_family_capture_matrix()
    assert any(row["status"] == "REIMPLEMENTED_PROOF" for row in reference)
    assert all(row["copied_code_or_assets"] is False for row in reference)
    safety = build_twitter_exporter_safety_matrix()
    unsafe = [row for row in safety if row.get("status") == "UNSAFE_OUT_OF_SCOPE"]
    assert unsafe
    assert any(row["capability"] == "posting" and row["safe"] is False for row in unsafe)
    assert any(row["capability"] == "export_summary" and row["safe"] is True for row in safety)


if __name__ == "__main__":
    test_full_page_plan_steps_to_bottom_with_overlap()
    test_capture_manifest_records_hashes_and_offline_safety()
    test_cursor_continuation_respects_soft_pause_and_cooldown()
    test_reference_and_exporter_matrices_are_safe()
    print("twitter_capture_screenshot_preservation_test: PASS")
