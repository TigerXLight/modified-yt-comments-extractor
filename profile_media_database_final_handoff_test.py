from __future__ import annotations

from profile_media_database_final_handoff import (
    build_profile_media_final_handoff,
    profile_media_final_handoff_payload,
    render_profile_media_final_handoff_text,
)


def test_final_handoff_lists_full_chain_and_next_action() -> None:
    handoff = build_profile_media_final_handoff()
    payload = profile_media_final_handoff_payload(handoff, include_text=True)
    assert payload["status"] == "ready_for_manual_gui_smoke_then_clickable_ui_polish"
    assert payload["latest_pack"] == "V76J"
    assert payload["implemented_pack_count"] >= 12
    assert "V76I reconciliation closeout" in payload["handoff_text"]
    assert "manual GUI smoke" in payload["next_recommended_action"]


def test_final_handoff_is_read_only() -> None:
    payload = profile_media_final_handoff_payload(build_profile_media_final_handoff())
    assert payload["folder_scan_performed"] is False
    assert payload["file_copy_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


def test_final_handoff_text_renders() -> None:
    text = render_profile_media_final_handoff_text(build_profile_media_final_handoff())
    assert "Profile/Media Database Final Handoff" in text
    assert "V76J manual GUI smoke readiness" in text
    assert "Upload notes" in text


def main() -> int:
    test_final_handoff_lists_full_chain_and_next_action()
    test_final_handoff_is_read_only()
    test_final_handoff_text_renders()
    print("profile_media_database_final_handoff v76j OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
