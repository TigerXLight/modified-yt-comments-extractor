from __future__ import annotations

from source_adapter_fixture_matrix import build_source_adapter_fixture_matrix
from source_adapter_fixture_matrix_verifier import verify_source_adapter_fixture_matrix


def test_verifier_accepts_valid_matrix_and_rejects_live_flags() -> None:
    matrix = build_source_adapter_fixture_matrix([{"adapter_id": "article", "source_kind": "web", "domains": ["article.example"]}])
    assert verify_source_adapter_fixture_matrix(matrix)["verified"] is True
    bad = dict(matrix)
    bad["operator_summary"] = dict(matrix["operator_summary"])
    bad["operator_summary"]["manual_or_live_actions_started"] = True
    verification = verify_source_adapter_fixture_matrix(bad)
    assert verification["verified"] is False
    assert verification["issue_count"] >= 1


if __name__ == "__main__":
    test_verifier_accepts_valid_matrix_and_rejects_live_flags()
    print("Source Adapter Fixture Matrix verifier self-test passed.")
