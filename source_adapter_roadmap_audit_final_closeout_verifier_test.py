from __future__ import annotations

from source_adapter_roadmap_audit_final_closeout import example_roadmap_audit_final_closeout_package
from source_adapter_roadmap_audit_final_closeout_verifier import verify_source_adapter_roadmap_audit_final_closeout


def main() -> None:
    verification = verify_source_adapter_roadmap_audit_final_closeout(example_roadmap_audit_final_closeout_package())
    assert verification["verified"] is True
    assert verification["issue_count"] == 0
    assert verification["handoff_status"].endswith("OPERATOR_MONITORED_LIVE_EXECUTION")
    print("Source Adapter Roadmap Audit Final Closeout verifier self-test passed.")


if __name__ == "__main__":
    main()
