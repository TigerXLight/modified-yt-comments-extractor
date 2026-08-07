from __future__ import annotations

from source_adapter_capture_action_kit import build_source_adapter_capture_action_kit
from source_adapter_capture_action_kit_verifier import verify_source_adapter_capture_action_kit


def test_verifier_accepts_safe_package() -> None:
    package = build_source_adapter_capture_action_kit(
        {"adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}]}
    )
    result = verify_source_adapter_capture_action_kit(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_started_actions() -> None:
    package = build_source_adapter_capture_action_kit(
        {"adapters": [{"adapter_id": "article", "artifact_roles": ["article_html_or_text"]}]}
    )
    package["action_index"]["actions"][0]["starts_live_or_manual_action"] = True
    result = verify_source_adapter_capture_action_kit(package)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


if __name__ == "__main__":
    test_verifier_accepts_safe_package()
    test_verifier_rejects_started_actions()
    print("Source Adapter Capture Action Kit verifier self-test passed.")
