from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_ARCHIVE_HANDOFF_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Adapter Release Audit Bridge",
        "source_archive_handoff",
        "provider tasks",
        "result templates",
        "READY_FOR_SHARED_ARCHIVE_RESULT_INTAKE",
        "archive result intake",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, f"missing documentation phrases: {missing}"


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Handoff Bridge docs self-test passed.")
