from __future__ import annotations

from copy import deepcopy

from source_adapter_provider_backend_interfaces import build_source_adapter_provider_backend_interfaces
from source_adapter_provider_backend_interfaces_verifier import verify_source_adapter_provider_backend_interfaces


def main() -> None:
    package = build_source_adapter_provider_backend_interfaces().as_dict()
    result = verify_source_adapter_provider_backend_interfaces(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0
    assert result["provider_backend_execution_receipt_row_count"] == 25
    bad = deepcopy(package)
    bad["source_adapter_provider_backend_execution_receipt_batch"]["provider_backend_execution_receipt_rows"][0]["raw_credential"] = "not allowed"
    bad_result = verify_source_adapter_provider_backend_interfaces(bad)
    assert bad_result["verified"] is False
    assert any(issue["issue_id"] == "secret_like_material_present" for issue in bad_result["issues"])
    print("Source Adapter Provider Backend Interfaces verifier self-test passed.")


if __name__ == "__main__":
    main()
