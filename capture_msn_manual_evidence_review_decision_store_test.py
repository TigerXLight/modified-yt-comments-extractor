from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_evidence_review_decision import build_msn_manual_evidence_review_decision
from capture_msn_manual_evidence_review_decision_store import store_msn_manual_evidence_review_decision
from capture_msn_manual_evidence_review_decision_test import _package


def test_store_writes_safe_decision_files() -> None:
    package = _package()
    decision = build_msn_manual_evidence_review_decision(
        package,
        review_decision="APPROVED",
        completed_action_ids=[action["action_id"] for action in package["review_actions"]],
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = store_msn_manual_evidence_review_decision(decision, tmp)
        assert report.output_file_count == 2
        names = {stored.filename for stored in report.stored_files}
        assert any(name.endswith(".evidence_review_decision.json") for name in names)
        assert any(name.endswith(".evidence_queue_update.json") for name in names)
        for stored in report.stored_files:
            data = (Path(tmp) / stored.filename).read_bytes()
            assert len(data) == stored.byte_count
            payload = json.loads(data.decode("utf-8"))
            assert "file_role" in payload
            assert ":\\" not in stored.filename


if __name__ == "__main__":
    test_store_writes_safe_decision_files()
    print("MSN manual Evidence Review decision store self-test passed.")
