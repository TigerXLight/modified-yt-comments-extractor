from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_evidence_queue_item_test import _pipeline_payload
from capture_msn_manual_evidence_queue_item import build_msn_manual_evidence_queue_item
from capture_msn_manual_evidence_queue_store import store_msn_manual_evidence_queue_item, msn_manual_evidence_queue_store_result_to_json


def test_store_writes_queue_item_and_index_without_serializing_full_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        item = build_msn_manual_evidence_queue_item(_pipeline_payload())
        result = store_msn_manual_evidence_queue_item(output_dir=tmp, item=item, file_prefix="msn_queue")
        payload = json.loads(msn_manual_evidence_queue_store_result_to_json(result))
        assert payload["file_count"] == 2
        assert payload["ready_for_evidence_queue_review"] is True
        assert (Path(tmp) / payload["files"][0]["file_name"]).is_file()
        assert (Path(tmp) / payload["files"][1]["file_name"]).is_file()
        assert str(tmp) not in msn_manual_evidence_queue_store_result_to_json(result)


if __name__ == "__main__":
    test_store_writes_queue_item_and_index_without_serializing_full_paths()
    print("MSN manual Evidence Queue store self-test passed.")
