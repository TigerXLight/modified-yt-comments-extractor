from __future__ import annotations

from source_adapter_roadmap_audit_final_closeout import (
    HANDOFF_STATUS,
    REQUIRED_ROADMAP_SECTIONS,
    STATUS,
    build_source_adapter_roadmap_audit_final_closeout,
    example_operator_named_site_smoke_execution_closeout_package,
)


def main() -> None:
    package = build_source_adapter_roadmap_audit_final_closeout(
        example_operator_named_site_smoke_execution_closeout_package(),
        release_notes=["Release note from test."],
        operator_id="test_operator",
    ).as_dict()
    assert package["roadmap_audit_final_closeout_status"] == STATUS
    assert package["source_adapter_final_release_handoff"]["handoff_status"] == HANDOFF_STATUS
    completion = package["source_adapter_roadmap_completion_index"]
    assert completion["closed_section_count"] >= len(REQUIRED_ROADMAP_SECTIONS)
    assert completion["missing_sections"] == []
    assert package["source_adapter_regression_promotion_manifest"]["ready_promotion_row_count"] >= 7
    assert package["source_adapter_live_execution_acceptance_manifest"]["keys_accounts_redacted_credential_references_ok"] is True
    assert package["source_adapter_master_coverage_audit_closeout"]["keys_accounts_label"] == "KEYS/ACCOUNTS"
    assert package["operator_summary"]["next_actions"]
    print("Source Adapter Roadmap Audit Final Closeout self-test passed.")


if __name__ == "__main__":
    main()
