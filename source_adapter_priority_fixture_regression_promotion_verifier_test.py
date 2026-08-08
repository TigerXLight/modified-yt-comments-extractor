from __future__ import annotations

from copy import deepcopy

from source_adapter_priority_fixture_regression_promotion import example_priority_fixture_regression_promotion_package
from source_adapter_priority_fixture_regression_promotion_verifier import verify_source_adapter_priority_fixture_regression_promotion


def main() -> None:
    package = example_priority_fixture_regression_promotion_package()
    verification = verify_source_adapter_priority_fixture_regression_promotion(package)
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    assert verification["promoted_regression_queue_row_count"] == 20

    live_row_package = deepcopy(package)
    live_row = live_row_package["source_adapter_priority_fixture_regression_queue"]["promoted_regression_queue_rows"][0]
    live_row["execution_mode"] = "live"
    live_row["live_execution_allowed"] = True
    live_verification = verify_source_adapter_priority_fixture_regression_promotion(live_row_package)
    assert live_verification["verified"] is False
    assert any(issue["issue_id"] in {"promoted_row_not_dry_run", "promoted_row_live_execution_allowed_not_false"} for issue in live_verification["issues"])

    smoke_package = deepcopy(package)
    smoke_package["source_adapter_named_site_smoke_operator_approval_gate"]["named_site_smoke_gate_rows"][0]["smoke_executed"] = True
    smoke_verification = verify_source_adapter_priority_fixture_regression_promotion(smoke_package)
    assert smoke_verification["verified"] is False
    assert any(issue["issue_id"] == "smoke_gate_smoke_executed_not_false" for issue in smoke_verification["issues"])

    keys_package = deepcopy(package)
    keys_package["operator_summary"]["keys_accounts_label"] = "KEYS"
    keys_verification = verify_source_adapter_priority_fixture_regression_promotion(keys_package)
    assert keys_verification["verified"] is False
    assert any(issue["issue_id"] == "keys_accounts_label_changed" for issue in keys_verification["issues"])
    print("Source Adapter Priority Fixture Regression Promotion verifier self-test passed.")


if __name__ == "__main__":
    main()
