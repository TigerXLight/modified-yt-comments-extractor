from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from source_offline_bundle_writer import OfflineBundleStatus, write_offline_evidence_bundle


class SourceOfflineBundleWriterTest(unittest.TestCase):
    def test_writes_zip_bundle_with_manifest_hashes_and_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            screenshot = root / "page.png"
            screenshot.write_bytes(b"png-fixture")
            output = root / "bundle.zip"
            result = write_offline_evidence_bundle(
                output_zip_path=output,
                source_url="local-fixture://story",
                source_label="Fixture Story",
                article_text="Article text",
                page_outline_text="H1: Fixture",
                html_snapshot="<html><body>Fixture</body></html>",
                comments=({"comment_id": "c1", "text": "summary only"},),
                livechat=({"event_id": "l1", "message": "summary only"},),
                selected_media_metadata=({"resource_id": "m1", "sha256": "abc"},),
                archive_results=({"provider": "wayback", "status": "fake"},),
                screenshot_paths=(screenshot,),
            )
            self.assertEqual(result.status, OfflineBundleStatus.WRITTEN)
            self.assertTrue(output.is_file())
            self.assertGreater(result.size_bytes, 0)
            with zipfile.ZipFile(output, "r") as bundle:
                names = set(bundle.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("source_provenance.json", names)
                self.assertIn("article/article_text.txt", names)
                self.assertIn("screenshots/page.png", names)
                self.assertIn("hashes.json", names)
                manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
                hashes = json.loads(bundle.read("hashes.json").decode("utf-8"))
                self.assertTrue(manifest["no_live_capture_performed"])
                self.assertGreaterEqual(len(hashes["entries"]), 9)


if __name__ == "__main__":
    unittest.main()

