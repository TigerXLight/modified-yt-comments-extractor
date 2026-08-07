from __future__ import annotations

from source_adapter_capture_session import CAPTURE_SESSION_STATUS, build_source_adapter_capture_session, output_documents


def _sample_action_kit() -> dict:
    return {
        "source_adapter_capture_action_kit_id": "source_adapter_capture_action_kit.example",
        "adapters": [
            {
                "adapter_id": "article",
                "display_name": "Article",
                "source_kind": "web",
                "artifact_roles": ["article_html_or_text", "metadata_json"],
            }
        ],
        "artifact_intake_templates": {
            "templates": [
                {"adapter_id": "article", "artifact_role": "article_html_or_text"},
                {"adapter_id": "article", "artifact_role": "metadata_json"},
            ]
        },
    }


def _sample_receipts() -> list[dict]:
    return [
        {
            "adapter_id": "article",
            "artifact_role": "article_html_or_text",
            "artifact_basename": "article.html",
            "byte_count": 100,
            "sha256": "a" * 64,
        },
        {
            "adapter_id": "article",
            "artifact_role": "metadata_json",
            "artifact_basename": "metadata.json",
            "byte_count": 20,
            "sha256": "b" * 64,
        },
    ]


def test_builds_capture_session() -> None:
    package = build_source_adapter_capture_session(_sample_action_kit(), _sample_receipts(), operator_approval_id="approval.1")
    assert package["capture_session_status"] == CAPTURE_SESSION_STATUS
    assert package["source_adapter_capture_session_id"].startswith("source_adapter_capture_session.")
    assert package["adapter_count"] == 1
    assert package["receipt_count"] == 2
    assert package["artifact_collection_handoff"]["ready_for_source_artifact_collection"] is True
    assert package["safety_contract"]["artifact_bytes_read_by_this_stage"] is False


def test_rejects_unsafe_artifact_basename() -> None:
    receipts = _sample_receipts()
    receipts[0] = dict(receipts[0], artifact_basename="../article.html")
    try:
        build_source_adapter_capture_session(_sample_action_kit(), receipts)
    except ValueError as exc:
        assert "safe basename" in str(exc) or "path separators" in str(exc)
    else:
        raise AssertionError("unsafe artifact basename was accepted")


def test_requires_all_template_receipts() -> None:
    try:
        build_source_adapter_capture_session(_sample_action_kit(), _sample_receipts()[:1])
    except ValueError as exc:
        assert "missing required artifact receipts" in str(exc)
    else:
        raise AssertionError("missing receipt was accepted")


def test_output_documents_have_expected_roles() -> None:
    docs = output_documents(build_source_adapter_capture_session(_sample_action_kit(), _sample_receipts()))
    assert sorted(docs) == [
        "source_adapter_artifact_collection_handoff",
        "source_adapter_capture_artifact_receipt_index",
        "source_adapter_capture_session_operator_summary",
        "source_adapter_capture_session_package",
        "source_adapter_capture_session_record",
    ]


if __name__ == "__main__":
    test_builds_capture_session()
    test_rejects_unsafe_artifact_basename()
    test_requires_all_template_receipts()
    test_output_documents_have_expected_roles()
    print("Source Adapter Capture Session self-test passed.")
