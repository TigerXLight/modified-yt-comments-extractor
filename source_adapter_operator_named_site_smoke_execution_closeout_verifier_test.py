from __future__ import annotations

from copy import deepcopy

from source_adapter_operator_named_site_smoke_execution_closeout import example_operator_named_site_smoke_execution_closeout_package
from source_adapter_operator_named_site_smoke_execution_closeout_verifier import verify_source_adapter_operator_named_site_smoke_execution_closeout


def main() -> None:
    package = example_operator_named_site_smoke_execution_closeout_package()
    verified = verify_source_adapter_operator_named_site_smoke_execution_closeout(package)
    assert verified["verified"], verified
    broken = deepcopy(package)
    broken["source_adapter_operator_named_site_receipt_acceptance_index"]["keys_accounts_redacted_credential_references_ok"] = False
    broken_result = verify_source_adapter_operator_named_site_smoke_execution_closeout(broken)
    assert not broken_result["verified"]
    assert any(issue["issue_id"] == "keys_accounts_redaction" for issue in broken_result["issues"])
    print("Source Adapter Operator Named Site Smoke Execution Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
