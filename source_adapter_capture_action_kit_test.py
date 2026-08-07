from __future__ import annotations

from source_adapter_capture_action_kit import ACTION_KIT_STATUS, build_source_adapter_capture_action_kit, output_documents


def _sample_setup() -> dict:
    return {
        "source_adapter_capture_setup_id": "source_adapter_capture_setup.example",
        "adapters": [
            {
                "adapter_id": "article",
                "display_name": "Article",
                "source_kind": "web",
                "artifact_roles": ["article_html_or_text", "metadata_json", "screenshot"],
            }
        ],
    }


def test_builds_action_kit() -> None:
    package = build_source_adapter_capture_action_kit(_sample_setup())
    assert package["action_kit_status"] == ACTION_KIT_STATUS
    assert package["source_adapter_capture_action_kit_id"].startswith("source_adapter_capture_action_kit.")
    assert package["adapter_count"] == 1
    assert package["action_index"]["action_count"] == 2
    assert package["capture_session_handoff"]["manual_or_live_actions_started"] is False
    assert all(action["requires_explicit_approval"] for action in package["action_index"]["actions"])


def test_rejects_unsafe_adapter_id() -> None:
    try:
        build_source_adapter_capture_action_kit({"adapters": [{"adapter_id": "../bad"}]})
    except ValueError as exc:
        assert "safe identifier" in str(exc) or "traversal" in str(exc)
    else:
        raise AssertionError("unsafe adapter_id was accepted")


def test_output_documents_have_expected_roles() -> None:
    package = build_source_adapter_capture_action_kit(_sample_setup())
    docs = output_documents(package)
    assert sorted(docs) == [
        "source_adapter_capture_action_index",
        "source_adapter_capture_action_kit_package",
        "source_adapter_capture_action_operator_summary",
        "source_adapter_capture_artifact_intake_templates",
        "source_adapter_capture_session_handoff",
    ]
    assert docs["source_adapter_capture_artifact_intake_templates"]["template_count"] == 3


if __name__ == "__main__":
    test_builds_action_kit()
    test_rejects_unsafe_adapter_id()
    test_output_documents_have_expected_roles()
    print("Source Adapter Capture Action Kit self-test passed.")
