from __future__ import annotations

from source_adapter_priority_fixture_pack_implementation import (
    HANDOFF_STATUS,
    STATUS,
    build_source_adapter_priority_fixture_pack_implementation,
)
from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package


def main() -> None:
    package = build_source_adapter_priority_fixture_pack_implementation(
        example_runtime_gui_provider_implementation_package(),
        operator_id="tester",
        fixture_pack_notes=["local fixture dispatch implementation"],
    ).as_dict()
    assert package["priority_fixture_pack_implementation_status"] == STATUS
    assert package["source_adapter_priority_fixture_pack_implementation_handoff"]["handoff_status"] == HANDOFF_STATUS
    assert package["source_adapter_priority_fixture_pack_catalog"]["fixture_pack_count"] == 5
    execution_count = package["source_adapter_priority_fixture_pack_execution_matrix"]["fixture_pack_execution_row_count"]
    receipt_count = package["source_adapter_priority_fixture_pack_dispatch_receipt_batch"]["fixture_pack_dispatch_receipt_count"]
    assert execution_count == receipt_count
    assert execution_count >= 20
    assert package["operator_summary"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    print("Source Adapter Priority Fixture Pack Implementation self-test passed.")


if __name__ == "__main__":
    main()
