from source_adapter_registry_update import build_source_adapter_registry_update
from source_adapter_registry_update_verifier import verify_source_adapter_registry_update


def test_verifier_accepts_ready_package():
    package = build_source_adapter_registry_update(
        {
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
            "adapters": [
                {
                    "adapter_id": "article",
                    "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                    "shared_stage_coverage": ["content_extraction"],
                    "accepted_for_shared_pipeline": True,
                }
            ],
        }
    )
    result = verify_source_adapter_registry_update(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_blocked_package():
    package = build_source_adapter_registry_update(
        {
            "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
            "handoff_status": "WAITING_FOR_LOCAL_FIXTURE_RESULTS",
            "adapters": [
                {
                    "adapter_id": "article",
                    "coverage_status": "NOT_ACCEPTED",
                    "shared_stage_coverage": [],
                    "accepted_for_shared_pipeline": False,
                }
            ],
        }
    )
    result = verify_source_adapter_registry_update(package)
    assert result["verified"] is False


if __name__ == "__main__":
    test_verifier_accepts_ready_package()
    test_verifier_rejects_blocked_package()
    print("Source Adapter Registry Update verifier self-test passed.")
