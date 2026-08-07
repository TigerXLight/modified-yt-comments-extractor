from __future__ import annotations

import tempfile
from pathlib import Path

from capture_msn_manual_approved_export_handoff_test import _decision
from capture_msn_manual_approved_export_handoff import build_msn_manual_approved_export_handoff
from capture_msn_manual_approved_export_handoff_store import store_msn_manual_approved_export_handoff


def main() -> None:
    handoff = build_msn_manual_approved_export_handoff(_decision())
    with tempfile.TemporaryDirectory() as tmp:
        report = store_msn_manual_approved_export_handoff(handoff, tmp)
        assert report.output_file_count == 2
        assert all(stored.filename for stored in report.stored_files)
        assert all(stored.sha256 for stored in report.stored_files)
        assert all(stored.byte_count == (Path(tmp) / stored.filename).stat().st_size for stored in report.stored_files)
    print("MSN manual approved export handoff store self-test passed.")


if __name__ == "__main__":
    main()
