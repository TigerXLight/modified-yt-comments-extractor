from __future__ import annotations

from source_adapter_operational_runtime_bundle_closeout import build_package
from source_adapter_operational_runtime_bundle_closeout_verifier import verify_operational_runtime_bundle_closeout_package


def test_operational_runtime_bundle_closeout_verifier() -> None:
    package = build_package(operator_id="verifier_operator")
    result = verify_operational_runtime_bundle_closeout_package(package)
    assert result["verified"] is True
    package["keys_accounts_label"] = "KEYS"
    result = verify_operational_runtime_bundle_closeout_package(package)
    assert result["verified"] is False
    assert "keys_accounts_label_mismatch" in result["issues"]


if __name__ == "__main__":
    test_operational_runtime_bundle_closeout_verifier()
    print("Source Adapter Operational Runtime Bundle Closeout verifier self-test passed.")
