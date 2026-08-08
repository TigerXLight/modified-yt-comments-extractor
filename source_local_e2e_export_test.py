from __future__ import annotations

import json
import tempfile
from pathlib import Path

from total_export_manifest import read_manifest_json
from source_local_e2e_export import (
    LocalE2EExportStatus,
    write_local_e2e_fixture_total_export,
)


FIXTURE_HTML = """
<html><body>
  <article><h1>Fixture E2E Story</h1><p>Article text for total export.</p></article>
  <div data-comment-id="c1" data-author="A">Comment one</div>
  <div data-event-id="l1" data-author="Chat">Live chat one</div>
  <video src="/clip.mp4"></video>
</body></html>
"""


def test_local_e2e_total_export_writes_package_manifest_and_receipts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = write_local_e2e_fixture_total_export(
            output_directory=temp_dir,
            fixture_html=FIXTURE_HTML,
            selected_media_payloads=(("clip.mp4", b"media", "video"),),
        )
        package_root = Path(temp_dir) / result.package_name
        manifest_path = package_root / result.manifest_name
        assert result.status == LocalE2EExportStatus.WRITTEN
        assert package_root.is_dir()
        assert manifest_path.is_file()
        assert (package_root / "page_capture" / "article_text.txt").is_file()
        assert (package_root / "page_capture" / "visible_page_outline.txt").is_file()
        assert (package_root / "execution" / "browser" / "rendered_dom.html").is_file()
        assert (package_root / "execution" / "browser" / "faithful_full_page.png").is_file()
        assert (package_root / "metadata" / "comments.json").is_file()
        assert (package_root / "metadata" / "livechat.json").is_file()
        assert (package_root / "metadata" / "archive_fake_client_result.json").is_file()
        assert (package_root / "execution" / "offline_bundle.zip").is_file()
        movement = json.loads((package_root / "metadata" / "movement_preview_receipts.json").read_text(encoding="utf-8"))
        assert movement["movement_receipt"]["destination_verified"] is True
        assert movement["completed_evidence_receipt"]["completed_evidence_claimed"] is True
        assert movement["temp_fixture_only"] is True

        manifest = read_manifest_json(str(manifest_path))
        assert len(manifest.assets) >= 12
        assert all(asset.sha256 for asset in manifest.assets)
        assert any(asset.description == "Unified execution bridge sidecar." for asset in manifest.assets)
        assert "No external site" in manifest.notes
        assert result.runner_job.external_network_performed is False
        assert result.live_network_performed is False
        assert result.real_user_evidence_moved is False


if __name__ == "__main__":
    test_local_e2e_total_export_writes_package_manifest_and_receipts()
    print("source_local_e2e_export_test.py passed")
