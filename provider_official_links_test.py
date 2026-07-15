from __future__ import annotations

from urllib.parse import urlparse

from access_keys_catalog import build_default_access_keys_catalog_bundle
from provider_official_links import (
    LINK_TYPE_CREDENTIAL_SETUP,
    LINK_TYPE_DEVELOPER_DOCS,
    LINK_TYPE_PRICING,
    LINK_TYPE_RELEASES,
    LINK_TYPE_REPOSITORY,
    LINK_TYPE_WEBSITE,
    OFFICIAL_LINK_METADATA_BY_ENTRY_ID,
    all_official_link_metadata,
    is_safe_official_url,
    official_link_buttons_for_entry,
    official_link_labels,
)


COMMERCIAL_ASR_ENTRY_IDS = {
    "asr:elevenlabs_scribe",
    "asr:assemblyai_universal_3_5_pro",
    "asr:deepgram_nova_3",
    "asr:speechmatics_enhanced",
    "asr:azure_speech",
    "asr:google_stt_video_enhanced",
    "asr:cohere_transcribe",
    "asr:google_stt_latest_long",
    "asr:aws_transcribe_custom_vocabulary",
}

FORBIDDEN_URL_TEXT = (
    "api_key",
    "access_token",
    "refresh_token",
    "password=",
    "secret=",
    "token=",
)

FORBIDDEN_HOSTS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "google.com",
    "www.google.com",
}


def _metadata(entry_id: str):
    metadata = OFFICIAL_LINK_METADATA_BY_ENTRY_ID.get(entry_id)
    assert metadata is not None, entry_id
    return metadata


def _link_types(entry_id: str) -> set[str]:
    return {link.link_type for link in _metadata(entry_id).links}


def _all_links():
    for metadata in all_official_link_metadata():
        for link in metadata.links:
            yield metadata.entry_id, link


def test_every_catalog_entry_has_link_metadata_record() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    catalog_entry_ids = {entry.entry_id for entry in bundle.catalog.entries}
    metadata_entry_ids = {
        metadata.entry_id
        for metadata in all_official_link_metadata()
    }

    assert catalog_entry_ids == metadata_entry_ids
    assert len(metadata_entry_ids) == len(all_official_link_metadata())


def test_website_coverage_is_present_or_explicit_gap() -> None:
    for metadata in all_official_link_metadata():
        link_types = {link.link_type for link in metadata.links}
        declared = set(metadata.not_applicable) | set(metadata.coverage_gaps)
        assert (
            LINK_TYPE_WEBSITE in link_types
            or LINK_TYPE_REPOSITORY in link_types
            or LINK_TYPE_WEBSITE in declared
        ), (
            metadata.entry_id,
            metadata.to_dict(),
        )


def test_commercial_cloud_asr_links_cover_docs_credentials_and_pricing() -> None:
    for entry_id in COMMERCIAL_ASR_ENTRY_IDS:
        link_types = _link_types(entry_id)
        assert LINK_TYPE_WEBSITE in link_types, entry_id
        assert LINK_TYPE_DEVELOPER_DOCS in link_types, entry_id
        assert LINK_TYPE_CREDENTIAL_SETUP in link_types, entry_id
        assert LINK_TYPE_PRICING in link_types, entry_id


def test_local_open_source_provider_omits_fake_key_and_pricing_links() -> None:
    link_types = _link_types("asr:whisper_cpp_vulkan_large_v3_turbo")
    assert LINK_TYPE_REPOSITORY in link_types
    assert LINK_TYPE_DEVELOPER_DOCS in link_types
    assert LINK_TYPE_RELEASES in link_types
    assert LINK_TYPE_CREDENTIAL_SETUP not in link_types
    assert LINK_TYPE_PRICING not in link_types


def test_social_video_platform_links_include_applicable_official_sources() -> None:
    youtube_types = _link_types("source:youtube")
    assert LINK_TYPE_WEBSITE in youtube_types
    assert LINK_TYPE_DEVELOPER_DOCS in youtube_types
    assert LINK_TYPE_CREDENTIAL_SETUP in youtube_types

    tiktok_types = _link_types("planned:source:tiktok")
    assert LINK_TYPE_WEBSITE in tiktok_types
    assert LINK_TYPE_DEVELOPER_DOCS in tiktok_types
    assert LINK_TYPE_CREDENTIAL_SETUP in tiktok_types

    consumer_types = _link_types("planned:source:nebula")
    assert LINK_TYPE_WEBSITE in consumer_types
    assert LINK_TYPE_DEVELOPER_DOCS not in consumer_types
    assert LINK_TYPE_CREDENTIAL_SETUP not in consumer_types


def test_urls_are_safe_https_official_destinations() -> None:
    for entry_id, link in _all_links():
        assert is_safe_official_url(link.url), (entry_id, link)
        parsed = urlparse(link.url)
        assert parsed.scheme == "https"
        assert parsed.hostname
        assert parsed.hostname.casefold() not in FORBIDDEN_HOSTS
        lowered = link.url.casefold()
        assert not any(token in lowered for token in FORBIDDEN_URL_TEXT), (
            entry_id,
            link.url,
        )


def test_no_duplicate_buttons_or_urls_per_entry() -> None:
    for metadata in all_official_link_metadata():
        labels = [link.label for link in metadata.links]
        urls = [link.url for link in metadata.links]
        assert len(labels) == len(set(labels)), metadata.entry_id
        assert len(urls) == len(set(urls)), metadata.entry_id


def test_link_button_helpers_are_deterministic() -> None:
    assert official_link_labels() == official_link_labels()
    assert official_link_buttons_for_entry("asr:elevenlabs_scribe") == (
        ("Provider website", "https://elevenlabs.io/"),
        ("Developer documentation", "https://elevenlabs.io/docs"),
        ("Get API key", "https://elevenlabs.io/app/settings/api-keys"),
        ("View current pricing", "https://elevenlabs.io/pricing"),
        ("Service status", "https://status.elevenlabs.io/"),
    )
    assert official_link_buttons_for_entry("browser:dedicated_capture_profile") == ()


def run_self_test() -> None:
    test_every_catalog_entry_has_link_metadata_record()
    test_website_coverage_is_present_or_explicit_gap()
    test_commercial_cloud_asr_links_cover_docs_credentials_and_pricing()
    test_local_open_source_provider_omits_fake_key_and_pricing_links()
    test_social_video_platform_links_include_applicable_official_sources()
    test_urls_are_safe_https_official_destinations()
    test_no_duplicate_buttons_or_urls_per_entry()
    test_link_button_helpers_are_deterministic()


if __name__ == "__main__":
    run_self_test()
    print("Provider official links self-test passed.")
