from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_release_audit_bridge import build_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_store import store_source_adapter_release_audit_bridge
from source_adapter_release_audit_bridge_test import fixture_release_index_bridge


def main() -> None:
    package = build_source_adapter_release_audit_bridge(fixture_release_index_bridge())
    with TemporaryDirectory() as tmp:
        receipt = store_source_adapter_release_audit_bridge(package, tmp)
    assert receipt["store_status"] == "STORED"
    assert receipt["output_file_count"] == 5
    assert receipt["release_audit_count"] == 1
    assert receipt["verification"]["verified"] is True
    assert all(item["byte_count"] > 0 and item["sha256"] for item in receipt["stored_files"])


if __name__ == "__main__":
    main()
    print("Source Adapter Release Audit Bridge store self-test passed.")
