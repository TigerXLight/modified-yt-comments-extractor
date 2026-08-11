from capture_options import (
    CAPTURE_ARCHIVE_CHECK,
    CAPTURE_ARCHIVE_SUBMIT,
    CAPTURE_COMMENTS,
    CAPTURE_DISPUTED_FRAMING_NOTES,
    CAPTURE_LIVE_CHAT,
    CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS,
    CAPTURE_REPLIES,
    CAPTURE_STAGE_FUTURE_ONLY,
    CAPTURE_STAGE_PLANNED,
    CAPTURE_SOURCE_ROLE_LABELS,
    CAPTURE_VIDEO_MEDIA_EVIDENCE,
    available_capture_options,
    capture_options_requiring_confirmation,
    default_total_export_capture_selection,
    default_total_export_capture_option_ids,
    future_only_capture_option_ids,
    get_capture_option,
    normalize_capture_option_ids,
)


def run_self_test() -> None:
    options = available_capture_options()
    option_ids = [option.option_id for option in options]
    assert len(option_ids) == len(set(option_ids))

    archive_check = get_capture_option(CAPTURE_ARCHIVE_CHECK)
    assert archive_check is not None
    assert archive_check.default_enabled_for_total_export
    assert not archive_check.requires_user_confirmation
    assert not archive_check.sends_data_to_external_service
    assert "failure is not proof" in archive_check.safety_notes

    archive_submit = get_capture_option(CAPTURE_ARCHIVE_SUBMIT)
    assert archive_submit is not None
    assert not archive_submit.default_enabled_for_total_export
    assert archive_submit.requires_user_confirmation
    assert archive_submit.sends_data_to_external_service

    video_media = get_capture_option(CAPTURE_VIDEO_MEDIA_EVIDENCE)
    assert video_media is not None
    assert video_media.stage == CAPTURE_STAGE_FUTURE_ONLY
    assert not video_media.default_enabled_for_total_export
    assert video_media.requires_user_confirmation

    for current_manual_id in (
        CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS,
        CAPTURE_DISPUTED_FRAMING_NOTES,
        CAPTURE_SOURCE_ROLE_LABELS,
    ):
        option = get_capture_option(current_manual_id)
        assert option is not None
        assert option.stage == CAPTURE_STAGE_PLANNED
        assert option.stage != CAPTURE_STAGE_FUTURE_ONLY
        assert option.default_enabled_for_total_export
        assert "Future" not in option.description
        assert "future" not in option.description

    default_ids = default_total_export_capture_option_ids()
    assert CAPTURE_COMMENTS in default_ids
    assert CAPTURE_REPLIES in default_ids
    assert CAPTURE_LIVE_CHAT in default_ids
    assert CAPTURE_ARCHIVE_CHECK in default_ids
    assert CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS in default_ids
    assert CAPTURE_DISPUTED_FRAMING_NOTES in default_ids
    assert CAPTURE_SOURCE_ROLE_LABELS in default_ids
    assert CAPTURE_ARCHIVE_SUBMIT not in default_ids
    assert CAPTURE_VIDEO_MEDIA_EVIDENCE not in default_ids

    future_only_ids = future_only_capture_option_ids()
    assert CAPTURE_VIDEO_MEDIA_EVIDENCE in future_only_ids
    assert CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS not in future_only_ids
    assert CAPTURE_DISPUTED_FRAMING_NOTES not in future_only_ids
    assert CAPTURE_SOURCE_ROLE_LABELS not in future_only_ids

    confirmation_ids = {
        option.option_id for option in capture_options_requiring_confirmation()
    }
    assert CAPTURE_ARCHIVE_SUBMIT in confirmation_ids
    assert CAPTURE_VIDEO_MEDIA_EVIDENCE in confirmation_ids
    assert CAPTURE_ARCHIVE_CHECK not in confirmation_ids

    assert get_capture_option("unknown_option") is None

    normalized = normalize_capture_option_ids(
        [
            " comments ",
            "",
            "archive_check",
            "comments",
            "unknown_option",
            " archive_check ",
            "new_option",
        ]
    )
    assert normalized.selected_option_ids == (CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK)
    assert normalized.unknown_option_ids == ("unknown_option", "new_option")
    assert normalized.duplicate_option_ids == (CAPTURE_COMMENTS, CAPTURE_ARCHIVE_CHECK)
    assert normalized.warnings == (
        "Unknown capture options ignored: unknown_option, new_option",
        "Duplicate capture options ignored: comments, archive_check",
    )

    preserved = normalize_capture_option_ids(["comments", "unknown_option"], allow_unknown=True)
    assert preserved.selected_option_ids == (CAPTURE_COMMENTS, "unknown_option")
    assert preserved.unknown_option_ids == ("unknown_option",)
    assert preserved.warnings == ("Unknown capture options preserved: unknown_option",)

    default_selection = default_total_export_capture_selection()
    assert default_selection.selected_option_ids == default_total_export_capture_option_ids()
    assert default_selection.unknown_option_ids == ()
    assert default_selection.duplicate_option_ids == ()
    assert default_selection.warnings == ()


if __name__ == "__main__":
    run_self_test()
    print("Capture option metadata self-test passed.")
