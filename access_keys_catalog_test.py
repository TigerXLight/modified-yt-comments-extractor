from __future__ import annotations

from dataclasses import fields

from access_keys_catalog import (
    TOP_LEVEL_SECTIONS,
    AccessKeysCatalogBundle,
    AccessKeysEntryLayout,
    build_default_access_keys_catalog,
    build_default_access_keys_catalog_bundle,
    layout_by_entry_id,
)
from access_keys_metadata import (
    AccessEntryKind,
    AccessMode,
    CredentialStatus,
)
from access_keys_view_model import build_access_keys_manager_view


REQUIRED_PLANNED_TITLES = {
    "Vimeo",
    "TikTok",
    "Dailymotion",
    "Rumble",
    "PeerTube",
    "Twitch",
    "Kick",
    "YouTube Live",
    "Nebula",
    "Floatplane",
    "Odysee",
    "DTube",
    "Triller",
    "Clapper",
    "Bilibili",
    "Youku",
    "X / Twitter",
    "Threads",
    "Bluesky",
    "Mastodon / Fediverse",
    "Instagram",
    "Pixelfed",
    "Vero",
    "Monnett",
    "Flashes",
    "VSCO",
    "Glass",
    "Flickr",
    "BeReal",
    "Pinksky",
    "Locket",
    "Pinterest",
    "Lemon8",
    "Reddit",
    "Lemmy",
    "Kbin",
    "Discuit",
    "Squabbles",
    "Tildes",
    "Hacker News",
    "Lobsters",
    "4chan",
    "Quora",
    "Tumblr",
    "LinkedIn",
    "Wellfound / AngelList",
    "Hired",
    "TeamBlind / Blind",
    "Fishbowl",
    "Behance",
    "Dribbble",
    "GitHub",
    "ResearchGate",
    "Lunchclub",
    "Xing",
    "Alignable",
    "Microsoft Teams",
    "Google Chat",
    "Webex App",
    "Mattermost",
    "Rocket.Chat",
    "Zulip",
    "Element / Matrix",
    "Wire",
    "Guild",
    "Flock",
    "Wayback Machine Archive Check",
    "Wayback / Internet Archive Submit-Save",
    "archive.ph / archive.today-style Service",
    "Local ArchiveBox-Style Preservation",
    "Dedicated Capture Browser Profile",
    "Advanced User-Selected Existing Browser Profile",
}

REQUIRED_EXISTING_TITLES = {"YouTube", "News Website"}

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


def _matching_ids(
    bundle: AccessKeysCatalogBundle,
    query: str,
) -> tuple[str, ...]:
    view = build_access_keys_manager_view(
        bundle.catalog,
        search_query=query,
        layouts=bundle.layouts,
    )
    return tuple(
        entry.entry_id
        for section in view.sections
        for entry in section.entries
    )


def run_self_test() -> None:
    bundle = build_default_access_keys_catalog_bundle()
    assert isinstance(bundle, AccessKeysCatalogBundle)
    assert build_default_access_keys_catalog() == bundle.catalog
    assert bundle.catalog.entries
    assert len(bundle.catalog.entries) == len(bundle.layouts)

    entry_ids = [entry.entry_id for entry in bundle.catalog.entries]
    assert len(entry_ids) == len(set(entry_ids))

    layout_ids = [layout.entry_id for layout in bundle.layouts]
    assert len(layout_ids) == len(set(layout_ids))
    assert set(entry_ids) == set(layout_ids)

    layouts = layout_by_entry_id(bundle.layouts)
    assert set(layouts) == set(entry_ids)

    display_names = {entry.display_name for entry in bundle.catalog.entries}
    assert REQUIRED_PLANNED_TITLES <= display_names
    assert REQUIRED_EXISTING_TITLES <= display_names

    canonical_names = [
        layout.canonical_name.casefold()
        for layout in bundle.layouts
        if layout.canonical_name
    ]
    assert len(canonical_names) == len(set(canonical_names))
    assert sum(name == "youtube" for name in canonical_names) == 1
    assert sum(name == "tiktok" for name in canonical_names) == 1

    ordered_section_labels: list[str] = []
    for layout in sorted(
        bundle.layouts,
        key=lambda item: (
            item.section_order,
            item.subgroup_order,
            item.entry_order,
        ),
    ):
        if layout.section_label not in ordered_section_labels:
            ordered_section_labels.append(layout.section_label)
    assert ordered_section_labels == [
        label for _section_id, label, _order in TOP_LEVEL_SECTIONS
    ]

    planned_entries = [
        entry
        for entry in bundle.catalog.entries
        if entry.implementation_state == "planned metadata only"
    ]
    assert planned_entries
    assert all(
        entry.credential_status is CredentialStatus.UNSUPPORTED
        for entry in planned_entries
    )
    assert all(
        entry.project_status == "planned; no adapter or runtime access"
        for entry in planned_entries
    )
    assert all(entry.access_limitations for entry in planned_entries)

    youtube = next(
        entry
        for entry in bundle.catalog.entries
        if entry.entry_id == "source:youtube"
    )
    assert youtube.display_name == "YouTube"
    assert youtube.implementation_state == "registered source adapter metadata"
    assert youtube.access_mode is AccessMode.API_KEY
    assert youtube.supports_comments is True
    assert youtube.supports_replies is True
    assert youtube.supports_live_chat is True
    assert "YouTube Data API key" in youtube.setup_hint

    news = next(
        entry
        for entry in bundle.catalog.entries
        if entry.entry_id == "source:news_website"
    )
    assert news.display_name == "News Website"
    assert "metadata" in news.implementation_state
    news_layout = layouts[news.entry_id]
    assert news_layout.section_label == "News Websites"
    assert "site-specific" in " ".join(news_layout.tags).casefold()

    archive_check = next(
        entry
        for entry in bundle.catalog.entries
        if entry.entry_id == "archive:wayback_check"
    )
    archive_submit = next(
        entry
        for entry in bundle.catalog.entries
        if entry.entry_id == "archive:wayback_submit"
    )
    assert archive_check.entry_kind is AccessEntryKind.ARCHIVE_SERVICE
    assert archive_submit.entry_kind is AccessEntryKind.ARCHIVE_SERVICE
    assert archive_check.entry_id != archive_submit.entry_id
    assert "archive check" in layouts[archive_check.entry_id].planned_capabilities
    assert "archive submit" in layouts[archive_submit.entry_id].planned_capabilities

    browser_entries = [
        entry
        for entry in bundle.catalog.entries
        if entry.entry_kind is AccessEntryKind.BROWSER_ASSISTED_CAPTURE
    ]
    assert len(browser_entries) == 2
    assert all(
        "No password, cookie, or session harvesting"
        in entry.privacy_notes
        for entry in browser_entries
    )

    alias_expectations = {
        "Twitter": "planned:source:x_twitter",
        "X": "planned:source:x_twitter",
        "AngelList": "planned:professional:wellfound_angellist",
        "Blind": "planned:professional:teamblind_blind",
        "Matrix": "planned:workplace:element_matrix",
        "Internet Archive": "archive:wayback_check",
        "Flickr": "planned:source:flickr",
        "Monnett": "planned:source:monnett",
        "Flashes": "planned:source:flashes",
    }
    for query, expected_id in alias_expectations.items():
        assert expected_id in _matching_ids(bundle, query), (query, expected_id)

    serialized = bundle.to_dict()
    assert serialized["layout_count"] == len(bundle.layouts)
    assert serialized["catalog"]["entry_count"] == len(bundle.catalog.entries)
    assert [item["entry_id"] for item in serialized["layouts"]] == layout_ids

    model_fields = {
        field.name
        for model in (AccessKeysEntryLayout, AccessKeysCatalogBundle)
        for field in fields(model)
    }
    assert model_fields.isdisjoint(FORBIDDEN_SECRET_FIELDS)

    assert not hasattr(bundle, "store_credentials")
    assert not hasattr(bundle, "test_connection")
    assert not hasattr(bundle, "open_browser_profile")


if __name__ == "__main__":
    run_self_test()
    print("Access & Keys catalog self-test passed.")
