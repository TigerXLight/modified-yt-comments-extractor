from __future__ import annotations

from pathlib import Path
import sys

from source_adapter_provider_command_runtime import KEYS_ACCOUNTS_LABEL, build_source_adapter_provider_command_runtime
from source_adapter_provider_command_runtime_verifier import verify_source_adapter_provider_command_runtime_package


def test_provider_command_runtime_executes_all_provider_actions() -> None:
    package = build_source_adapter_provider_command_runtime(extra_env={"EXAMPLE_SECRET_TOKEN": "hidden-token-value"}, timeout_seconds=5).as_dict()
    matrix = package["source_adapter_provider_command_request_matrix"]
    batch = package["source_adapter_provider_command_execution_receipt_batch"]
    assert package["provider_command_runtime_status"] == "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_BUILT"
    assert matrix["provider_command_request_row_count"] == 25
    assert batch["provider_command_execution_receipt_row_count"] == 25
    assert batch["successful_execution_count"] == 25
    assert package["operator_summary"]["keys_accounts_label"] == KEYS_ACCOUNTS_LABEL
    for row in batch["provider_command_execution_receipt_rows"]:
        assert row["execution_succeeded"] is True
        assert Path(row["receipt_path"]).exists()
        assert "hidden-token-value" not in Path(row["receipt_path"]).read_text(encoding="utf-8")
    verification = verify_source_adapter_provider_command_runtime_package(package)
    assert verification["verified"] is True


def test_provider_command_runtime_accepts_real_command_configuration() -> None:
    package = build_source_adapter_provider_command_runtime(action_commands={"archive_submit": [sys.executable, "-c", "print('archive-ok')"]}, timeout_seconds=5).as_dict()
    configured = [row for row in package["source_adapter_provider_command_request_matrix"]["provider_command_request_rows"] if row["provider_action"] == "archive_submit"]
    assert configured
    assert all(row["provider_specific_command_configured"] for row in configured)


if __name__ == "__main__":
    test_provider_command_runtime_executes_all_provider_actions()
    test_provider_command_runtime_accepts_real_command_configuration()
    print("Source Adapter Provider Command Runtime self-test passed.")
