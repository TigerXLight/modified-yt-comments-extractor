from source_adapter_online_asr_visual_parity_guard_runtime import build_default_record, build_record, read_record, summarise_record, write_record
import tempfile


def test_default_record_summary():
    record = build_default_record()
    summary = summarise_record(record)
    assert summary["stage"] == "online_asr_visual_parity_guard"
    assert summary["credential_policy"] == "redacted_reference_only"
    assert summary["input_count"] >= 1
    assert len(summary["digest"]) == 64


def test_round_trip_file_write():
    record = build_record("case-1", input_refs=["in"], output_refs=["out"], operator_approved=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = write_record(f"{tmp}/record.json", record)
        loaded = read_record(path)
    assert loaded.runtime_id == "case-1"
    assert loaded.operator_approved is True
    assert loaded.output_refs == ("out",)


if __name__ == "__main__":
    test_default_record_summary()
    test_round_trip_file_write()
    print("Source Adapter Online ASR Visual Parity Guard Runtime self-test passed.")
