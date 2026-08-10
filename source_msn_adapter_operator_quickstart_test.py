from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_operator_quickstart import build_quickstart, write_quickstart


def test_operator_quickstart_outputs_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "msn_output"
        out = Path(tmp) / "quickstart"
        root.mkdir()
        bundle = build_quickstart(root, out, "python")
        paths = write_quickstart(bundle)
        assert paths["json"].is_file()
        assert paths["markdown"].is_file()
        assert paths["cmd"].is_file()
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert data["decision_boundary"].startswith("No real MSN COMPLETE")
        assert len(data["commands"]) == 7
        cmd_text = paths["cmd"].read_text(encoding="utf-8")
        assert "source_msn_adapter_certification_archive.py" in cmd_text
        assert "source_msn_adapter_release_promotion.py" in cmd_text


if __name__ == "__main__":
    test_operator_quickstart_outputs_commands()
    print("MSN operator quickstart self-test passed.")
