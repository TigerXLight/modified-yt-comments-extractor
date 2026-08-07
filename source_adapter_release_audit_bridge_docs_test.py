from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_RELEASE_AUDIT_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Adapter Release Audit Bridge",
        "source_adapter_release_audit_bridge_v1",
        "source_release_audit",
        "READY_FOR_SHARED_ARCHIVE_HANDOFF",
        "multi-adapter batches",
        "source_archive_handoff",
    ]
    for phrase in required:
        assert phrase in text


if __name__ == "__main__":
    main()
    print("Source Adapter Release Audit Bridge docs self-test passed.")
