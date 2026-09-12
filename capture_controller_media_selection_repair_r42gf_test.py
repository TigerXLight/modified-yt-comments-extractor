from __future__ import annotations

from capture_controller import build_operational_capture_plan
from capture_contracts import (
    ARTIFACT_TYPE_MEDIA_COMPONENT,
    ARTIFACT_TYPE_MEDIA_FILE,
    ARTIFACT_TYPE_MEDIA_INVENTORY,
)
from source_resource_state import build_discussion_capture_options, build_source_resource_row


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456"


def test_msn_source_row_no_longer_injects_fake_media_but_controller_accepts_explicit_media_selection() -> None:
    row = build_source_resource_row(MSN_URL)
    assert row.adapter_id == "msn"
    assert row.video_audio_resources == ()

    selected_ids = (
        f"{row.row_id}:video_audio:user_selected_public_video_candidate",
        f"{row.row_id}:video_audio:user_selected_public_audio_candidate",
    )
    discussion = build_discussion_capture_options(
        (row,),
        selected_row_id=row.row_id,
        webpage_selected=False,
        comments_selected=False,
        comments_screenshot_requested=False,
        livechat_selected=False,
        livechat_screenshot_requested=False,
    )

    result = build_operational_capture_plan(
        row=row,
        discussion=discussion,
        selected_media_resource_ids=selected_ids,
        mux_plan_requested=True,
    )
    artifact_types = [artifact.artifact_type for artifact in result.declared_artifacts]

    assert result.selected_modes == ("media",)
    assert artifact_types == [
        ARTIFACT_TYPE_MEDIA_INVENTORY,
        ARTIFACT_TYPE_MEDIA_FILE,
        ARTIFACT_TYPE_MEDIA_FILE,
        ARTIFACT_TYPE_MEDIA_COMPONENT,
    ]
    assert result.declared_artifacts[0].metadata["selected_resource_ids"] == selected_ids
    assert result.declared_artifacts[1].metadata["download_execution"] == "not executed"
    assert result.declared_artifacts[2].metadata["download_execution"] == "not executed"
    assert result.declared_artifacts[-1].metadata["mock_command_plan_only"] is True
    assert result.declared_artifacts[-1].metadata["selected_resource_ids"] == selected_ids
    assert result.grabbed_source_record is not None
    assert result.grabbed_source_record.metadata_only is True
    assert result.grabbed_source_record.live_capture_performed is False


def run_self_test() -> None:
    test_msn_source_row_no_longer_injects_fake_media_but_controller_accepts_explicit_media_selection()


if __name__ == "__main__":
    run_self_test()
    print("capture_controller_media_selection_repair_r42gf_test OK")
