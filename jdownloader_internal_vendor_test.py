from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jdownloader_internal_paths import (
    JD_REQUIRED_CONTROL_SOURCE_PATHS,
    JD_REQUIRED_YOUTUBE_SOURCE_PATHS,
    JD_SOURCE_ARCHIVE_SOURCES,
    JD_RUNTIME_SOURCE_FILES,
    internal_jdownloader_layout,
)
from jdownloader_internal_vendor import JDownloaderVendorReport, VendorFileRecord, write_vendor_manifests


def test_internal_layout_uses_project_vendor_tree() -> None:
    layout = internal_jdownloader_layout()
    assert layout.vendor_root.endswith("third_party\\jdownloader") or layout.vendor_root.endswith("third_party/jdownloader")
    assert layout.runtime_dir.endswith("runtime\\JDownloader 2") or layout.runtime_dir.endswith("runtime/JDownloader 2")


def test_required_manifest_lists_youtube_plugin_and_control_paths() -> None:
    assert "src.zip" in JD_SOURCE_ARCHIVE_SOURCES
    assert "JDownloader.jar" in JD_SOURCE_ARCHIVE_SOURCES
    assert "JDownloader 2.zip" in JD_RUNTIME_SOURCE_FILES
    assert "jd/plugins/hoster/YoutubeDashV2.java" in JD_REQUIRED_YOUTUBE_SOURCE_PATHS
    assert "org/jdownloader/plugins/components/youtube/YoutubeHelper.java" in JD_REQUIRED_YOUTUBE_SOURCE_PATHS
    assert "org/jdownloader/api/cnl2/ExternInterfaceImpl.java" in JD_REQUIRED_CONTROL_SOURCE_PATHS
    assert "org/jdownloader/myjdownloader/client/bindings/AddLinksQuery.java" in JD_REQUIRED_CONTROL_SOURCE_PATHS


def test_write_vendor_manifests_preserves_provenance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        import jdownloader_internal_vendor as vendor

        original = vendor.JD_MANIFESTS_DIR
        vendor.JD_MANIFESTS_DIR = Path(tmp) / "manifests"
        try:
            report = JDownloaderVendorReport(
                vendor_root=str(Path(tmp) / "third_party" / "jdownloader"),
                mode="source-only",
                source_archives=(
                    VendorFileRecord(
                        name="src.zip",
                        source_path="C:/source/src.zip",
                        target_path=str(Path(tmp) / "source_archives" / "src.zip"),
                        copied=True,
                        exists=True,
                        size=12,
                        sha256="abc",
                        provenance="local JDownloader mirror/source path",
                    ),
                ),
            )
            write_vendor_manifests(report)
            manifest = json.loads((vendor.JD_MANIFESTS_DIR / "jdownloader_vendor_manifest.json").read_text(encoding="utf-8"))
            required = json.loads((vendor.JD_MANIFESTS_DIR / "jdownloader_required_files.json").read_text(encoding="utf-8"))
            runtime = json.loads((vendor.JD_MANIFESTS_DIR / "jdownloader_runtime_manifest.json").read_text(encoding="utf-8"))
            assert manifest["source_archives"][0]["provenance"] == "local JDownloader mirror/source path"
            assert "jd/plugins/hoster/YoutubeDashV2.java" in required["youtube_plugin_source_paths"]
            assert runtime["external_installed_jdownloader_is_bootstrap_source_only"] is True
        finally:
            vendor.JD_MANIFESTS_DIR = original


def main() -> None:
    test_internal_layout_uses_project_vendor_tree()
    test_required_manifest_lists_youtube_plugin_and_control_paths()
    test_write_vendor_manifests_preserves_provenance()
    print("jdownloader_internal_vendor_test OK")


if __name__ == "__main__":
    main()
