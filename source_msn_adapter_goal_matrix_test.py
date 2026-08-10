from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_goal_matrix import (
    COMPLETE,
    CONFIDENT_WITH_MANUAL_REVIEW,
    PASS,
    PARTIAL,
    build_goal_matrix,
    write_goal_matrix,
)


def test_goal_matrix_complete_when_all_required_pass() -> None:
    status = {
        "article": PASS,
        "comments": PASS,
        "profiles": PASS,
        "offline_viewer": PASS,
        "archive": PASS,
        "media": PASS,
        "video": "NOT_APPLICABLE",
        "source_roles": PASS,
        "source_chain": PASS,
        "readiness_reports": PASS,
        "done_acceptance_reports": PASS,
        "manual_live_result": PASS,
    }
    matrix = build_goal_matrix(status)
    assert matrix.final_status == COMPLETE
    assert matrix.static_status == PASS
    assert matrix.live_status == PASS


def test_goal_matrix_confident_when_only_manual_live_missing() -> None:
    status = {
        "article": PASS,
        "comments": PASS,
        "profiles": PASS,
        "offline_viewer": PASS,
        "archive": PASS,
        "media": PASS,
        "video": "NOT_APPLICABLE",
        "source_roles": PASS,
        "source_chain": PASS,
        "readiness_reports": PASS,
        "done_acceptance_reports": PASS,
        "manual_live_result": PARTIAL,
    }
    matrix = build_goal_matrix(status)
    assert matrix.final_status == CONFIDENT_WITH_MANUAL_REVIEW
    assert matrix.static_status == PASS
    assert "manual_live_result" in matrix.missing_live


def test_goal_matrix_writes_outputs() -> None:
    matrix = build_goal_matrix({"article": PASS})
    with tempfile.TemporaryDirectory() as tmp:
        written = write_goal_matrix(matrix, Path(tmp))
        assert Path(written["json"]).exists()
        assert Path(written["markdown"]).exists()
        loaded = json.loads(Path(written["json"]).read_text(encoding="utf-8"))
        assert loaded["schema"].startswith("msn.source_adapter.goal_matrix")


if __name__ == "__main__":
    test_goal_matrix_complete_when_all_required_pass()
    test_goal_matrix_confident_when_only_manual_live_missing()
    test_goal_matrix_writes_outputs()
    print("MSN goal matrix self-test passed.")
