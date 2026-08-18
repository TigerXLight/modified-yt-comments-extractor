from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jdownloader_capability_router import (
    JD_CAPABILITY_STATUS_DOMAIN_NOT_INDEXED,
    JD_CAPABILITY_STATUS_INDEXED_DOMAIN,
    JD_CAPABILITY_STATUS_MANIFEST_MISSING,
    JD_CAPABILITY_STATUS_RUNTIME_MISSING,
    JD_CAPABILITY_STATUS_TESTED_VIDEO_DOMAIN,
    build_jdownloader_capability_decision,
    normalize_jdownloader_capability_domain,
)
from jdownloader_internal_backend import JDownloaderInternalCapabilities
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID, YTDLP_FALLBACK_BACKEND_ID


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dev_only": True,
                "startup_safe": "not_loaded_on_app_startup",
                "capabilities": {
                    "youtube.com": {
                        "media_backend": "jdownloader",
                        "tested": True,
                        "supports_video": True,
                        "supports_audio": True,
                        "supports_thumbnail": True,
                        "supports_description": True,
                        "supports_subtitles": "depends_on_source_video",
                        "plugin_types": ["hoster"],
                        "plugins": [
                            {"plugin_type": "hoster", "plugin_name": "YoutubeDashV2", "relative_path": "jd/plugins/hoster/YoutubeDashV2.class"}
                        ],
                    },
                    "vimeo.com": {
                        "media_backend": "jdownloader",
                        "tested": False,
                        "supports_video": "unknown_until_tested",
                        "supports_audio": "unknown_until_tested",
                        "supports_thumbnail": "unknown_until_tested",
                        "supports_description": "unknown_until_tested",
                        "supports_subtitles": "unknown_until_tested",
                        "plugin_types": ["hoster", "decrypter"],
                        "plugins": [
                            {"plugin_type": "hoster", "plugin_name": "VimeoCom", "relative_path": "jd/plugins/hoster/VimeoCom.class"},
                            {"plugin_type": "decrypter", "plugin_name": "VimeoComDecrypter", "relative_path": "jd/plugins/decrypter/VimeoComDecrypter.class"},
                        ],
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_domain_normalization() -> None:
    assert normalize_jdownloader_capability_domain("https://www.youtube.com/watch?v=x") == "youtube.com"
    assert normalize_jdownloader_capability_domain("https://mobile.twitter.com/a/status/1") == "mobile.twitter.com"
    assert normalize_jdownloader_capability_domain("vimeo.com/123") == "vimeo.com"


def test_tested_youtube_domain_prefers_api3128() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest)
        decision = build_jdownloader_capability_decision(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            manifest_path=manifest,
            capabilities=JDownloaderInternalCapabilities(runtime_present=True, primary_runtime_path="runtime"),
        )
        assert decision.capability_status == JD_CAPABILITY_STATUS_TESTED_VIDEO_DOMAIN
        assert decision.recommended_backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert decision.api3128_preferred is True
        assert decision.domain_likely_supported is True
        assert decision.tested is True
        assert decision.supports_video is True
        assert decision.matched_manifest_domain == "youtube.com"
        assert "YoutubeDashV2" in decision.plugin_names
        assert decision.to_dict()["yt_dlp_role"] == "fallback_only_after_jdownloader_routes"


def test_indexed_but_untested_domain_still_tries_jdownloader_first() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest)
        decision = build_jdownloader_capability_decision(
            "https://player.vimeo.com/video/123",
            manifest_path=manifest,
            capabilities=JDownloaderInternalCapabilities(runtime_present=True, primary_runtime_path="runtime"),
        )
        assert decision.capability_status == JD_CAPABILITY_STATUS_INDEXED_DOMAIN
        assert decision.matched_manifest_domain == "vimeo.com"
        assert decision.recommended_backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert decision.api3128_preferred is True
        assert set(decision.plugin_types) == {"hoster", "decrypter"}


def test_unknown_domain_tries_jdownloader_before_ytdlp_when_runtime_exists() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest)
        decision = build_jdownloader_capability_decision(
            "https://example.invalid/watch/1",
            manifest_path=manifest,
            capabilities=JDownloaderInternalCapabilities(runtime_present=True, primary_runtime_path="runtime"),
        )
        assert decision.capability_status == JD_CAPABILITY_STATUS_DOMAIN_NOT_INDEXED
        assert decision.domain_likely_supported is False
        assert decision.recommended_backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert decision.api3128_preferred is True


def test_missing_manifest_does_not_block_jdownloader_runtime_route() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "missing.json"
        decision = build_jdownloader_capability_decision(
            "https://x.com/example/status/1",
            manifest_path=missing,
            capabilities=JDownloaderInternalCapabilities(runtime_present=True, primary_runtime_path="runtime"),
        )
        assert decision.capability_status == JD_CAPABILITY_STATUS_MANIFEST_MISSING
        assert decision.manifest_present is False
        assert decision.recommended_backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert decision.api3128_preferred is True
        assert any("capability manifest not found" in warning.lower() for warning in decision.warnings)


def test_runtime_missing_uses_ytdlp_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest)
        decision = build_jdownloader_capability_decision(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            manifest_path=manifest,
            capabilities=JDownloaderInternalCapabilities(runtime_present=False, warnings=("runtime missing",)),
        )
        assert decision.capability_status == JD_CAPABILITY_STATUS_RUNTIME_MISSING
        assert decision.recommended_backend_id == YTDLP_FALLBACK_BACKEND_ID
        assert decision.api3128_preferred is False
        assert "runtime missing" in decision.warnings


def main() -> None:
    test_domain_normalization()
    test_tested_youtube_domain_prefers_api3128()
    test_indexed_but_untested_domain_still_tries_jdownloader_first()
    test_unknown_domain_tries_jdownloader_before_ytdlp_when_runtime_exists()
    test_missing_manifest_does_not_block_jdownloader_runtime_route()
    test_runtime_missing_uses_ytdlp_fallback()
    print("jdownloader_capability_router_test OK")


if __name__ == "__main__":
    main()
