from __future__ import annotations
import json, tempfile, zipfile
from pathlib import Path
from twitter_reference_pack_index import build_reference_pack_index, write_reference_pack_index

def _fake(path: Path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("root/01_local_browser_extension_archives/Twitter Exporter 0.8.58_0.zip", "x")
        z.writestr("root/02_high_priority_source_refs/rxliuli__twitter-openapi/README.md", "x")
        z.writestr("root/02_high_priority_source_refs/prinsss__twitter-web-exporter/LICENSE", "x")
        z.writestr("root/03_lower_priority_media_refs/paulrouget__libav.js/README.md", "x")
        z.writestr("root/04_extra_source_refs/mrcoles__full-page-screen-capture-chrome-extension/api.js", "x")
        z.writestr("root/04_extra_source_refs/copperline-labs__rendex-mcp/src/tools/screenshot.ts", "x")
        z.writestr("root/REFERENCE_SOURCE_MANIFEST.json", "{}")

def test_index_zip():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "pack.zip"; _fake(p)
        idx = build_reference_pack_index(p)
    assert idx.total_paths == 7
    assert idx.local_extension_archives
    assert "rxliuli__twitter-openapi" in idx.high_priority_sources
    assert "paulrouget__libav.js" in idx.lower_priority_media_sources
    assert "mrcoles__full-page-screen-capture-chrome-extension" in idx.extra_capture_sources
    assert any(c.cluster_id == "twitter_api_export" and c.matched_paths for c in idx.clusters)
    assert any(c.cluster_id == "screenshot_render_pdf" and c.matched_paths for c in idx.clusters)

def test_write_json():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "pack.zip"; o = Path(tmp) / "index.json"; _fake(p)
        write_reference_pack_index(p, o)
        data = json.loads(o.read_text(encoding="utf-8"))
    assert data["schema_version"] == "twitter_reference_pack_index.v69"
    assert data["total_paths"] == 7

def main():
    test_index_zip(); test_write_json()
    print("twitter_reference_pack_index_test OK")

if __name__ == "__main__":
    main()
