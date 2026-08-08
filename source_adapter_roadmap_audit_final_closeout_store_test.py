from __future__ import annotations

import tempfile

from source_adapter_roadmap_audit_final_closeout import example_roadmap_audit_final_closeout_package
from source_adapter_roadmap_audit_final_closeout_store import store_source_adapter_roadmap_audit_final_closeout


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_roadmap_audit_final_closeout(example_roadmap_audit_final_closeout_package(), tmp)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 5
        assert result["closed_section_count"] >= 31
        assert result["verification"]["verified"] is True
    print("Source Adapter Roadmap Audit Final Closeout store self-test passed.")


if __name__ == "__main__":
    main()
