from __future__ import annotations

from source_adapter_runbook_command_export_runtime import KEYS_ACCOUNTS_LABEL, STATUS, build_package


def test_runbook_command_export_runtime() -> None:
    package = build_package(operator_id="test_operator")
    assert package["status"] == STATUS
    assert package["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    assert package["row_count"] == len(package["rows"])
    assert package["verification"]["verified"] is True
    assert package["secret_material_present"] is False
    assert all(row["receipt_required"] for row in package["rows"])
    assert all(not row["secret_material_present"] for row in package["rows"])


if __name__ == "__main__":
    test_runbook_command_export_runtime()
    print("Source Adapter Runbook Command Export Runtime self-test passed.")
