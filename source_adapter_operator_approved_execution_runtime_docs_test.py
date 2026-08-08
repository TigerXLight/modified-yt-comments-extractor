from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME.md").read_text(encoding="utf-8")
    required = [
        "actual callable operator-approved execution runtime",
        "not plan-only",
        "browser capture",
        "archive submission",
        "release upload",
        "file-library publishing",
        "KEYS/ACCOUNTS",
        "redacted reference hashes",
        "all capabilities remain implementation scope",
        "SOURCE_ADAPTER_OPERATOR_APPROVED_EXECUTION_RUNTIME_READY_FOR_PROVIDER_AND_GUI_INTEGRATION",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing
    print("Source Adapter Operator Approved Execution Runtime docs self-test passed.")


if __name__ == "__main__":
    main()
