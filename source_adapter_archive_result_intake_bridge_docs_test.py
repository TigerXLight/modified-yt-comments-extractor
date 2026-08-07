from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_ARCHIVE_RESULT_INTAKE_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "source_adapter_archive_result_intake_bridge.py",
        "source_archive_result_intake",
        "source_adapter_archive_handoff_bridge_v1",
        "READY_FOR_SHARED_ARCHIVE_REVIEW",
        "operator archive result",
    ]
    missing = [text for text in required if text not in doc]
    assert not missing, f"documentation missing: {missing}"


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Result Intake Bridge docs self-test passed.")
