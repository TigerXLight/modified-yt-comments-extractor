from __future__ import annotations

from dataclasses import fields

from access_keys_catalog import (
    AccessKeysEntryLayout,
    build_default_access_keys_catalog_bundle,
)
from access_keys_metadata import (
    AccessEntryKind,
    AccessEntryMetadata,
    AccessKeysCatalog,
    AccessMode,
    ConnectionTestStatus,
    CredentialStatus,
)
from access_keys_view_model import (
    ACCESS_KEYS_VIEW_MODEL_SCOPE,
    AccessKeysEntryView,
    AccessKeysManagerView,
    AccessKeysSectionView,
    AccessKeysSubgroupView,
    build_access_keys_manager_view,
)


FORBIDDEN_SECRET_FIELDS = {
    "api_key",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "cookie",
    "cookies",
    "authorization_header",
    "browser_profile_path",
}


def _catalog() -> AccessKeysCatalog:
    return AccessKeysCatalog(
        entries=(
            AccessEntryMetadata(
                entry_id="local_whisper",
                entry_kind=AccessEntryKind.ASR_PROVIDER,
                display_name="Local whisper.cpp",
                platform_family="ASR providers",
                access_mode=AccessMode.LOCAL_ONLY,
                credential_status=CredentialStatus.NOT_NEEDED,
                implementation_state="available local baseline",
                supports_phrase_prompts=True,
                project_status="local baseline",
                setup_hint="Configure an existing local executable path.",
            ),
            AccessEntryMetadata(
                entry_id="elevenlabs",
                entry_kind=AccessEntryKind.ASR_PROVIDER,
                display_name="ElevenLabs Scribe v2",
                platform_family="ASR providers",
                access_mode=AccessMode.API_KEY,
                credential_status=CredentialStatus.REQUIRED_MISSING,
                implementation_state="metadata only",
                credential_type="api_key",
                credentials_required=True,
                supports_connection_test=True,
                supports_keyterms=True,
                project_status="candidate",
                privacy_notes="Cloud use remains opt-in.",
                cost_or_rate_limit_notes="Quota and cost may apply.",
                last_test_status=ConnectionTestStatus.TEST_NOT_RUN,
            ),
            AccessEntryMetadata(
                entry_id="youtube",
                entry_kind=AccessEntryKind.SOURCE_ADAPTER,
                display_name="YouTube",
                platform_family="Video and social video",
                access_mode=AccessMode.API_KEY,
                credential_status=CredentialStatus.CONFIGURED_UNTESTED,
                implementation_state="existing comments/live chat flow",
                credential_type="api_key",
                credentials_required=True,
                supports_comments=True,
                supports_replies=True,
                supports_live_chat=True,
                supports_captions_or_transcripts=True,
                access_limitations="Quota limits apply to API operations.",
                last_test_status=ConnectionTestStatus.TEST_NOT_RUN,
            ),
        )
    )


def _serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(_serialized_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(_serialized_keys(nested))
        return keys
    return set()


def _flatten_ids(view: AccessKeysManagerView) -> tuple[str, ...]:
    return tuple(
        entry.entry_id
        for section in view.sections
        for entry in section.entries
    )


def test_backward_compatible_default_grouping() -> None:
    catalog = _catalog()
    view = build_access_keys_manager_view(
        catalog,
        selected_entry_id="elevenlabs",
    )
    assert isinstance(view, AccessKeysManagerView)
    assert view.window_title == "Access & Keys"
    assert view.sidebar_button_label == "KEYS"
    assert view.visible_entry_count == 3
    assert view.selected_entry_id == "elevenlabs"
    assert [section.section_id for section in view.sections] == [
        "ASR providers",
        "Video and social video",
    ]
    assert all(
        isinstance(section, AccessKeysSectionView)
        for section in view.sections
    )
    asr_entries = view.sections[0].entries
    assert all(
        isinstance(entry, AccessKeysEntryView)
        for entry in asr_entries
    )
    assert [entry.entry_id for entry in asr_entries] == [
        "local_whisper",
        "elevenlabs",
    ]
    assert asr_entries[1].selected is True
    assert asr_entries[1].credential_status == "REQUIRED_MISSING"
    assert asr_entries[1].last_test_status == "TEST_NOT_RUN"
    assert asr_entries[1].enabled_capabilities == (
        "connection_test",
        "keyterms",
    )

    query_view = build_access_keys_manager_view(
        catalog,
        search_query=" quota limits ",
    )
    assert query_view.search_query == "quota limits"
    assert query_view.visible_entry_count == 1
    assert query_view.sections[0].entries[0].entry_id == "youtube"

    kind_view = build_access_keys_manager_view(
        catalog,
        entry_kind=AccessEntryKind.SOURCE_ADAPTER,
        platform_family="video and social video",
    )
    assert kind_view.entry_kind_filter == "SOURCE_ADAPTER"
    assert kind_view.platform_family_filter == "video and social video"
    assert kind_view.visible_entry_count == 1
    assert kind_view.sections[0].entries[0].entry_id == "youtube"

    hidden_selection = build_access_keys_manager_view(
        catalog,
        search_query="youtube",
        selected_entry_id="elevenlabs",
    )
    assert hidden_selection.selected_entry_id == ""
    assert hidden_selection.warnings == (
        "Selected access entry is not visible: elevenlabs",
    )

    no_match = build_access_keys_manager_view(
        catalog,
        search_query="not present",
    )
    assert no_match.visible_entry_count == 0
    assert no_match.sections == ()
    assert no_match.empty_message == (
        "No access entries match the current filters."
    )

    empty = build_access_keys_manager_view(AccessKeysCatalog())
    assert empty.empty_message == "No access entries are available."

    duplicate = build_access_keys_manager_view(
        AccessKeysCatalog(
            entries=(catalog.entries[0], catalog.entries[0])
        )
    )
    assert duplicate.warnings == (
        "Duplicate access entry ID: local_whisper",
    )

    serialized = view.to_dict()
    assert serialized["section_count"] == 2
    assert serialized["visible_entry_count"] == 3
    assert serialized["sections"][0]["entry_count"] == 2
    assert serialized["sections"][0]["entries"][1]["selected"] is True
    assert serialized["scope"] == ACCESS_KEYS_VIEW_MODEL_SCOPE


def test_layout_sections_subgroups_aliases_and_order() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    view = build_access_keys_manager_view(
        bundle.catalog,
        layouts=bundle.layouts,
    )
    assert view.visible_entry_count == len(bundle.catalog.entries)
    assert [section.display_name for section in view.sections] == [
        "ASR Providers",
        "Social Media",
        "News Websites",
        "Professional, Jobs, Experts & Portfolios",
        "Workplace, Chat & Collaboration",
        "Archive Services",
        "Browser-Assisted Capture",
    ]
    assert all(
        isinstance(subgroup, AccessKeysSubgroupView)
        for section in view.sections
        for subgroup in section.subgroups
    )

    social = next(
        section
        for section in view.sections
        if section.section_id == "social_media"
    )
    assert [subgroup.display_name for subgroup in social.subgroups] == [
        "Video & Social Video Platforms",
        "Live Streaming Platforms",
        "Creator-Owned & Independent Hubs",
        "Decentralised & Blockchain-Based Video",
        "Short-Form & Entertainment Mobile Apps",
        "Global & Regional Video Giants",
        "Text & Microblogging",
        "Mainstream Visual Social",
        "Alternative, Decentralised & Privacy-Focused Visual Apps",
        "Pure Photography & Creator Hubs",
        "Authentic & Daily Sharing",
        "Visual Discovery & Commercial Platforms",
        "General Community & Discussion",
        "Decentralised & Alternative Communities",
        "Threaded Forums & Link Aggregators",
        "Special-Interest, Anonymous, Q&A & Blogging",
    ]

    twitter = build_access_keys_manager_view(
        bundle.catalog,
        search_query="Twitter",
        layouts=bundle.layouts,
    )
    assert _flatten_ids(twitter) == ("planned:source:x_twitter",)

    blind = build_access_keys_manager_view(
        bundle.catalog,
        search_query="Blind",
        layouts=bundle.layouts,
    )
    assert "planned:professional:teamblind_blind" in _flatten_ids(blind)

    matrix = build_access_keys_manager_view(
        bundle.catalog,
        search_query="Matrix",
        layouts=bundle.layouts,
    )
    assert _flatten_ids(matrix) == (
        "planned:workplace:element_matrix",
    )

    family = build_access_keys_manager_view(
        bundle.catalog,
        platform_family="Social Media",
        layouts=bundle.layouts,
    )
    assert family.visible_entry_count == len(social.entries)
    assert all(
        entry.section_id == "social_media"
        for section in family.sections
        for entry in section.entries
    )

    selected = build_access_keys_manager_view(
        bundle.catalog,
        selected_entry_id="planned:source:flickr",
        layouts=bundle.layouts,
    )
    flickr = next(
        entry
        for section in selected.sections
        for entry in section.entries
        if entry.entry_id == "planned:source:flickr"
    )
    assert flickr.selected is True
    assert flickr.planned_only is True
    assert flickr.section_label == "Social Media"
    assert flickr.subgroup_label == "Pure Photography & Creator Hubs"
    assert "photography" in flickr.tags

    duplicate_layout = build_access_keys_manager_view(
        bundle.catalog,
        layouts=(
            bundle.layouts[0],
            bundle.layouts[0],
        ),
    )
    assert duplicate_layout.warnings == (
        f"Duplicate access layout ID: {bundle.layouts[0].entry_id}",
    )


def test_safe_serialization_and_fields() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    view = build_access_keys_manager_view(
        bundle.catalog,
        selected_entry_id="source:youtube",
        layouts=bundle.layouts,
    )
    serialized = view.to_dict()
    assert serialized["visible_entry_count"] == len(bundle.catalog.entries)
    assert serialized["sections"][0]["subgroup_count"] >= 1
    assert _serialized_keys(serialized).isdisjoint(
        FORBIDDEN_SECRET_FIELDS
    )

    model_field_names = {
        field.name
        for model in (
            AccessKeysEntryLayout,
            AccessKeysEntryView,
            AccessKeysSubgroupView,
            AccessKeysSectionView,
            AccessKeysManagerView,
        )
        for field in fields(model)
    }
    assert model_field_names.isdisjoint(FORBIDDEN_SECRET_FIELDS)
    assert "no GUI widgets" in ACCESS_KEYS_VIEW_MODEL_SCOPE
    assert "credential values/storage/testing" in (
        ACCESS_KEYS_VIEW_MODEL_SCOPE
    )
    assert "provider/API calls" in ACCESS_KEYS_VIEW_MODEL_SCOPE
    assert not hasattr(view, "store_credentials")
    assert not hasattr(view, "test_connection")
    assert not hasattr(view, "open_browser_profile")


def run_self_test() -> None:
    test_backward_compatible_default_grouping()
    test_layout_sections_subgroups_aliases_and_order()
    test_safe_serialization_and_fields()


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys view-model self-test passed.")
