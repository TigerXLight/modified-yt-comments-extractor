from source_adapter_priority_site_pack_execution_closeout import example_priority_site_pack_execution_closeout_package
from source_adapter_priority_site_pack_execution_closeout_verifier import verify_source_adapter_priority_site_pack_execution_closeout


def main() -> None:
    package = example_priority_site_pack_execution_closeout_package()
    result = verify_source_adapter_priority_site_pack_execution_closeout(package)
    assert result["verified"] is True, result
    assert result["issue_count"] == 0
    assert result["priority_site_pack_count"] >= 7
    assert result["manual_smoke_row_count"] >= result["priority_site_pack_count"]
    broken = dict(package)
    broken["source_adapter_priority_site_pack_execution_handoff"] = dict(package["source_adapter_priority_site_pack_execution_handoff"])
    broken["source_adapter_priority_site_pack_execution_handoff"]["ready_for_local_fixture_execution"] = False
    broken_result = verify_source_adapter_priority_site_pack_execution_closeout(broken)
    assert broken_result["verified"] is False
    print("Source Adapter Priority Site Pack Execution Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
