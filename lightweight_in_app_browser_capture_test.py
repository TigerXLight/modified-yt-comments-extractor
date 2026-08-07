from __future__ import annotations

from lightweight_in_app_browser_capture import (
    LightweightBrowserCaptureError,
    build_capture_job,
    build_capture_package,
    make_approval_token,
    validate_operator_url,
)


def _adapter() -> dict:
    return {
        "adapter_id": "msn_manual",
        "display_name": "MSN Manual",
        "domains": ["msn.com"],
        "artifact_roles": ["article_html_or_text", "comments_json_or_text", "dom_snapshot", "screenshot", "metadata_json"],
        "capture_surfaces": ["article", "comments_shadow_root"],
        "operator_only": True,
        "requires_lightweight_browser": True,
    }


def test_url_validation_allows_subdomains() -> None:
    result = validate_operator_url("https://www.msn.com/en-gb/news/example", ["msn.com"])
    assert result["valid"] is True
    assert result["host"] == "www.msn.com"


def test_capture_job_is_gated_until_exact_token() -> None:
    job = build_capture_job(_adapter(), "https://www.msn.com/en-gb/news/example", requested_artifacts=["dom_snapshot"])
    assert job["approval_status"] == "WAITING_FOR_OPERATOR_APPROVAL"
    token = make_approval_token(job["browser_job_id"])
    approved = build_capture_job(_adapter(), "https://www.msn.com/en-gb/news/example", requested_artifacts=["dom_snapshot"], approval_token=token)
    assert approved["approval_status"] == "APPROVED_OPERATOR_READY"
    assert approved["manual_or_live_actions_started"] is False


def test_capture_package_contains_scripts_and_templates_without_execution_claims() -> None:
    package = build_capture_package(_adapter(), "https://www.msn.com/en-gb/news/example")
    assert package["verification"]["verified"] is True
    assert package["safety"]["live_network_default"] is False
    assert "%~1" in package["windows_launch_script"]
    assert package["capture_job"]["approval_token"] in package["windows_launch_script"]
    assert package["artifact_manifest_template"]["saved_artifacts"] == []


def test_rejects_unsupported_domain_and_artifact() -> None:
    try:
        build_capture_package(_adapter(), "https://example.com/story")
    except LightweightBrowserCaptureError as exc:
        assert "adapter domains" in str(exc)
    else:
        raise AssertionError("expected domain rejection")
    try:
        build_capture_package(_adapter(), "https://msn.com/story", requested_artifacts=["password_dump"])
    except LightweightBrowserCaptureError as exc:
        assert "artifact role" in str(exc)
    else:
        raise AssertionError("expected artifact rejection")


if __name__ == "__main__":
    test_url_validation_allows_subdomains()
    test_capture_job_is_gated_until_exact_token()
    test_capture_package_contains_scripts_and_templates_without_execution_claims()
    test_rejects_unsupported_domain_and_artifact()
    print("Lightweight in-app browser capture self-test passed.")
