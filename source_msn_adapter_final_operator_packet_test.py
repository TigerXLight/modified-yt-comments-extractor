#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_final_operator_packet import build_operator_packet, write_operator_packet


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        output = Path(td) / "output"
        out = Path(td) / "packet"
        root.mkdir()
        output.mkdir()

        # Create a small positive live evidence file and a few representative repo artifacts.
        (output / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_RESULT.json").write_text(
            json.dumps({"status": "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE", "passed": True}),
            encoding="utf-8",
        )
        for name in [
            "source_msn_adapter_manifest.py",
            "source_msn_adapter_live_evidence_validator.py",
            "source_msn_adapter_final_operator_packet.py",
            "MSN_SOURCE_ADAPTER_COMPLETION_BOUNDARY_LOCK.md",
        ]:
            (root / name).write_text("x\n", encoding="utf-8")

        packet = build_operator_packet(root, output)
        assert packet.final_state == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
        assert packet.live_completion_allowed is True
        paths = write_operator_packet(packet, out)
        for key in ("json", "markdown", "csv", "cmd"):
            assert Path(paths[key]).exists(), key
        md = (out / "MSN_SOURCE_ADAPTER_FINAL_OPERATOR_PACKET.md").read_text(encoding="utf-8")
        assert "Final completion requires positive manual/live evidence" in md

    print("MSN final operator packet self-test passed.")


if __name__ == "__main__":
    main()
