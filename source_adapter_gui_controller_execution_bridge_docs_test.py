from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_BUILT",
        "SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_READY_FOR_UI_BUTTON_AND_PROVIDER_BACKEND_REPLACEMENT",
        "source_adapter.gui.runtime.action_palette",
        "source_adapter.gui.priority_fixture_pack_runner",
        "source_adapter.gui.live_smoke_receipt_capture",
        "keys_accounts.gui.credential_reference_selector",
        "KEYS/ACCOUNTS",
        "Online ASR",
    ]
    for item in required:
        assert item in text, item
    print("Source Adapter GUI Controller Execution Bridge docs self-test passed.")


if __name__ == "__main__":
    main()
