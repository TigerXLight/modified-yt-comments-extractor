from __future__ import annotations

from pathlib import Path


def test_runbook_command_export_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_RUNBOOK_COMMAND_EXPORT_RUNTIME.md").read_text(encoding="utf-8")
    assert "Runbook Command Export Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_RUNBOOK_COMMAND_EXPORT_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_runbook_command_export_runtime_docs()
    print("Source Adapter Runbook Command Export Runtime docs self-test passed.")
