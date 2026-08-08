from __future__ import annotations

from source_adapter_next_roadmap_work_order_execution_closeout import example_next_roadmap_work_order_execution_closeout_package
from source_adapter_runtime_gui_provider_implementation import (
    HANDOFF_STATUS,
    RuntimeControllerRegistry,
    STATUS,
    _payload_for_provider,
    build_source_adapter_runtime_gui_provider_implementation,
)


def main() -> None:
    package = build_source_adapter_runtime_gui_provider_implementation(
        example_next_roadmap_work_order_execution_closeout_package(),
        operator_id="tester",
    ).as_dict()
    assert package["runtime_gui_provider_implementation_status"] == STATUS
    assert package["source_adapter_runtime_gui_provider_implementation_handoff"]["handoff_status"] == HANDOFF_STATUS
    routes = package["source_adapter_runtime_gui_controller_route_registry"]["route_rows"]
    providers = package["source_adapter_runtime_provider_execution_registry"]["provider_rows"]
    assert len(routes) >= 4
    assert len(providers) >= 4
    assert package["source_adapter_keys_accounts_credential_reference_selector"]["sidebar_label"] == "KEYS/ACCOUNTS"
    dispatcher = RuntimeControllerRegistry(routes, providers)
    provider = providers[0]
    receipt = dispatcher.dispatch(
        route_id="source_adapter.gui.runtime.action_palette",
        provider_execution_adapter_id=provider["provider_execution_adapter_id"],
        payload=_payload_for_provider(provider),
        execution_mode="dry_run",
        operator_approval_id="tester.approval",
    )
    assert receipt["receipt_status"] == "SOURCE_ADAPTER_RUNTIME_DISPATCH_RECEIPT_RECORDED"
    assert receipt["missing_receipt_fields"] == []
    print("Source Adapter Runtime GUI Provider Implementation self-test passed.")


if __name__ == "__main__":
    main()
