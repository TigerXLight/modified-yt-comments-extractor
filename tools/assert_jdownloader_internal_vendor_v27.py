from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_internal_backend import detect_jdownloader_internal_capabilities
from jdownloader_internal_paths import JD_REQUIRED_YOUTUBE_SOURCE_PATHS, JDOWNLOADER_INTERNAL_BACKEND_ID


def main() -> None:
    required = [
        ROOT / "third_party" / "jdownloader" / "README_YTCE_JDOWNLOADER_VENDOR.md",
        ROOT / "third_party" / "jdownloader" / "manifests" / "jdownloader_required_files.json",
        ROOT / "tools" / "jdownloader" / "BOOTSTRAP_JDOWNLOADER_VENDOR.cmd",
        ROOT / "tools" / "jdownloader" / "VERIFY_JDOWNLOADER_VENDOR.cmd",
        ROOT / "tools" / "jdownloader" / "BUILD_INTERNAL_JDOWNLOADER_RUNTIME.cmd",
        ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_PROBE.cmd",
        ROOT / "jdownloader_internal_paths.py",
        ROOT / "jdownloader_internal_vendor.py",
        ROOT / "jdownloader_internal_backend.py",
    ]
    for path in required:
        assert path.exists(), str(path)
    manifest_text = (ROOT / "third_party" / "jdownloader" / "manifests" / "jdownloader_required_files.json").read_text(encoding="utf-8")
    assert "src.zip" in manifest_text
    assert "JDownloader 2.zip" in manifest_text
    assert "YoutubeDashV2.java" in manifest_text
    assert "ExternInterfaceImpl.java" in manifest_text
    assert "AddLinksQuery.java" in manifest_text
    assert "jd/plugins/hoster/YoutubeDashV2.java" in JD_REQUIRED_YOUTUBE_SOURCE_PATHS
    caps = detect_jdownloader_internal_capabilities()
    assert caps.backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
    assert caps.installed_external_is_bootstrap_source_only is True
    print("assert_jdownloader_internal_vendor_v27 OK")


if __name__ == "__main__":
    main()
