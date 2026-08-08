from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_audit_log_replay_runtime_store import write_audit_log_replay_runtime_package


def test_audit_log_replay_runtime_store() -> None:
    with TemporaryDirectory() as tmp:
        result = write_audit_log_replay_runtime_package(tmp, operator_id="store_operator")
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 3
        assert result["verification"]["verified"] is True
        for stored_file in result["stored_files"]:
            assert stored_file["byte_count"] > 0
            assert stored_file["sha256"]


if __name__ == "__main__":
    test_audit_log_replay_runtime_store()
    print("Source Adapter Audit Log Replay Runtime store self-test passed.")
