from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_final_command_index import build_command_index, write_command_index


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        target = root / "target"
        out = root / "out"
        repo.mkdir()
        target.mkdir()
        text = build_command_index(repo, target, out)
        assert "READY_FOR_LIVE_EVIDENCE" in text
        assert "source_msn_adapter_operator_health_dashboard.py" in text
        paths = write_command_index(repo, target, out)
        assert Path(paths["markdown"]).exists()
        assert Path(paths["cmd"]).exists()
        assert "COMPLETE`" not in text.split("Until positive manual/live evidence exists")[0]
    print("MSN final command index self-test passed.")


if __name__ == "__main__":
    main()
