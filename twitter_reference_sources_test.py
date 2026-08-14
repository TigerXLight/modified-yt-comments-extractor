from __future__ import annotations

import json
import tempfile
from pathlib import Path

from twitter_reference_sources import (
    build_twitter_reference_registry,
    inspect_chromium_extension_manifest,
    twitter_reference_sources,
    write_twitter_reference_registry,
)


def test_reference_registry_contains_user_supplied_reference_families() -> None:
    refs = twitter_reference_sources()
    ids = {item.reference_id for item in refs}
    required = {
        "twitter_exporter_rxliuli_chromium_extension",
        "twitter_filter_skills_rxliuli",
        "twitter_filter_rxliuli_store",
        "clean_twitter_rxliuli_store",
        "xkit_rxliuli",
        "twitter_openapi_rxliuli_or_fa0311",
        "ffmpeg_online_rxliuli",
        "webdatamaster_rxliuli",
        "google_translate_api_free_rxliuli",
        "twitter_web_exporter_prinsss",
        "web_exporter_eight04",
        "x_article_exporter_annismckenzie",
        "video_download_helper_chromium_extension",
        "vdhcoapp_aclap",
        "vdhcoapp_releases_aclap",
        "video_downloader_professional_chromium_extension",
        "video_downloader_pro_alasim",
        "seal_android_video_downloader",
        "youtube_js_paulrouget",
        "libav_js_paulrouget",
        "webcc_paulrouget",
        "console_gui_tools_paulrouget",
        "pathfinder_paulrouget",
        "jocly_aclap",
    }
    assert required <= ids
    twitter_exporter = next(item for item in refs if item.reference_id == "twitter_exporter_rxliuli_chromium_extension")
    assert "https://x.com/**" in twitter_exporter.host_permissions
    assert "UserMedia" in twitter_exporter.relevant_patterns
    assert "GraphQL" in twitter_exporter.implementation_use
    filter_ref = next(item for item in refs if item.reference_id == "twitter_filter_rxliuli_store")
    assert filter_ref.implementation_area == "api_response_interception_and_rule_engine"
    vdh = next(item for item in refs if item.reference_id == "video_download_helper_chromium_extension")
    assert "<all_urls>" in vdh.host_permissions
    assert "webRequest" in vdh.permissions
    assert vdh.implementation_area == "browser_media_discovery_and_download_worker"


def test_low_priority_items_are_marked_without_being_lost() -> None:
    refs = {item.reference_id: item for item in twitter_reference_sources()}
    assert refs["jocly_aclap"].implementation_area == "not_currently_relevant"
    assert refs["pathfinder_paulrouget"].source_kind == "github_reference_low_priority"


def test_local_manifest_inspection_reads_chromium_manifest() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68b_ext_manifest_") as tmp:
        root = Path(tmp)
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "name": "Twitter Exporter",
                    "version": "0.8.58",
                    "description": "fixture",
                    "permissions": ["cookies", "scripting"],
                    "host_permissions": ["https://x.com/**", "https://api.x.com/**"],
                    "background": {"service_worker": "background.js"},
                    "action": {"default_popup": "popup.html", "default_title": "Twitter Exporter"},
                }
            ),
            encoding="utf-8",
        )
        manifest = inspect_chromium_extension_manifest(root)
    assert manifest["name"] == "Twitter Exporter"
    assert manifest["version"] == "0.8.58"
    assert "https://api.x.com/**" in manifest["host_permissions"]
    assert manifest["background_service_worker"] == "background.js"


def test_write_reference_registry_json() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68b_ref_registry_") as tmp:
        output = Path(tmp) / "twitter_reference_registry.json"
        write_twitter_reference_registry(output)
        data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "twitter_reference_sources.v68b"
    assert data["reference_count"] >= 24
    assert any(item["reference_id"] == "twitter_filter_rxliuli_store" for item in data["references"])


def main() -> None:
    test_reference_registry_contains_user_supplied_reference_families()
    test_low_priority_items_are_marked_without_being_lost()
    test_local_manifest_inspection_reads_chromium_manifest()
    test_write_reference_registry_json()
    print("twitter_reference_sources_test OK")


if __name__ == "__main__":
    main()
