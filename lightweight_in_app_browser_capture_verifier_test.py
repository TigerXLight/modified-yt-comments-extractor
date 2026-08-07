from __future__ import annotations

from lightweight_in_app_browser_capture import build_capture_package, verify_capture_package
from lightweight_in_app_browser_capture_verifier import verify_store_receipt


def test_package_verifier_rejects_execution_claim() -> None:
    package = build_capture_package({"adapter_id": "x", "domains": ["example.com"]}, "https://example.com/a")
    assert verify_capture_package(package)["verified"] is True
    package["capture_job"]["manual_or_live_actions_started"] = True
    result = verify_capture_package(package)
    assert result["verified"] is False
    assert result["issue_count"] >= 1


def test_store_receipt_verifier_requires_roles() -> None:
    result = verify_store_receipt({"schema_version": "lightweight_in_app_browser_capture_store_v1", "store_status": "STORED", "package_id": "x", "stored_files": [], "verification": {"verified": True}})
    assert result["verified"] is False
    assert "missing stored roles" in result["issues"][0]


if __name__ == "__main__":
    test_package_verifier_rejects_execution_claim()
    test_store_receipt_verifier_requires_roles()
    print("Lightweight in-app browser capture verifier self-test passed.")
