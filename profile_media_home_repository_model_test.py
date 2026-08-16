from __future__ import annotations

from profile_media_home_repository_model import parse_home_classification_path, render_home_classification_path


def test_taxonomy_case_is_action_type_time_source_context() -> None:
    parsed = parse_home_classification_path(
        r"Sexual offences\Rape\Adults\Direct\Non-religious or not identified\June 2026\Belfast Telegraph\21 Jun - Creepy stepdad who harassed young woman for 10 months avoids jail - White"
    )
    assert parsed.case_is_person_only is False
    assert parsed.case_designation_rule == "classification_action_time_source_context"
    assert parsed.publisher_or_platform == "Belfast Telegraph"
    assert parsed.month_or_date == "June 2026"
    assert parsed.event_or_source_title.startswith("21 Jun - Creepy stepdad")
    assert parsed.folder_scan_performed is False


def test_existing_source_bucket_path_is_read_without_scan() -> None:
    parsed = parse_home_classification_path(
        "Cases/Demo/Sources/Social Media/Offline/Archived post bundle/manifest.json"
    )
    assert parsed.source_bucket == "Social Media/Offline"
    assert parsed.event_or_source_title == "Archived post bundle"
    assert parsed.automatic_classification_performed is False
    text = render_home_classification_path(parsed)
    assert "Source bucket: Social Media/Offline" in text


if __name__ == "__main__":
    test_taxonomy_case_is_action_type_time_source_context()
    test_existing_source_bucket_path_is_read_without_scan()
    print("profile_media_home_repository_model v76k2 OK")
