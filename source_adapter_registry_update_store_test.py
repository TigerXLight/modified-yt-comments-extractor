from tempfile import TemporaryDirectory

from source_adapter_registry_update_store import store_source_adapter_registry_update


def test_store_writes_expected_files():
    with TemporaryDirectory() as tmp:
        summary = store_source_adapter_registry_update(
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
            },
            tmp,
        )
        assert summary["store_status"] == "STORED"
        assert summary["output_file_count"] == 5
        assert all(item["byte_count"] > 0 for item in summary["stored_files"])


if __name__ == "__main__":
    test_store_writes_expected_files()
    print("Source Adapter Registry Update store self-test passed.")
