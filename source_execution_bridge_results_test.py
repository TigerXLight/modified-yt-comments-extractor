from __future__ import annotations

import json

from source_execution_bridge_results import (
    build_source_execution_bridge_results,
    source_execution_bridge_results_to_json,
)


def test_execution_bridge_results_summarize_real_bridges() -> None:
    results = build_source_execution_bridge_results()
    data = results.to_dict()
    assert data["row_count"] >= 6
    assert data["local_fixture_tested_count"] >= 5
    assert data["mocked_subprocess_tested_count"] >= 2
    assert data["fake_http_tested_count"] >= 1
    assert data["local_artifact_writer_count"] >= 3
    assert data["no_external_sites_accessed"] is True
    assert data["no_user_evidence_files_moved"] is True
    labels = {row["bridge_id"] for row in data["rows"]}
    assert "local_browser_execution" in labels
    assert "archive_provider_archivebox_execution" in labels


def test_execution_bridge_results_serialization_is_deterministic() -> None:
    first = source_execution_bridge_results_to_json(build_source_execution_bridge_results())
    second = source_execution_bridge_results_to_json(build_source_execution_bridge_results())
    assert first == second
    parsed = json.loads(first)
    assert parsed["schema_version"] == "source_execution_bridge_results_v1"


if __name__ == "__main__":
    test_execution_bridge_results_summarize_real_bridges()
    test_execution_bridge_results_serialization_is_deterministic()
    print("source_execution_bridge_results_test.py passed")

