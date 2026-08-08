from __future__ import annotations

from pathlib import Path


def test_total_export_package_assembler_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_ASSEMBLER_RUNTIME.md").read_text(encoding="utf-8")
    assert "Total Export Package Assembler Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_TOTAL_EXPORT_PACKAGE_ASSEMBLER_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_total_export_package_assembler_runtime_docs()
    print("Source Adapter Total Export Package Assembler Runtime docs self-test passed.")
