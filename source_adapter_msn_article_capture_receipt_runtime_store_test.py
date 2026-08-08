from source_adapter_msn_article_capture_receipt_runtime import build_record
from source_adapter_msn_article_capture_receipt_runtime_store import RuntimeStore, read_records, write_records
import tempfile


def test_store_append_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/records.jsonl"
        store = RuntimeStore(path)
        store.append(build_record("one", input_refs=["a"], output_refs=["b"]))
        store.append(build_record("two", input_refs=["c"], output_refs=["d"]))
        records = store.read_all()
    assert [record.runtime_id for record in records] == ["one", "two"]


def test_write_records_helper():
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/records.jsonl"
        write_records(path, [build_record("helper", input_refs=["in"], output_refs=["out"])])
        records = read_records(path)
    assert len(records) == 1
    assert records[0].runtime_id == "helper"


if __name__ == "__main__":
    test_store_append_and_read()
    test_write_records_helper()
    print("Source Adapter MSN Article Capture Receipt Runtime store self-test passed.")
