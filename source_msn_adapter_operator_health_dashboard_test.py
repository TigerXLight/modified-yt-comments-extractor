from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_operator_health_dashboard import (
    REPO_REQUIRED_FILES,
    build_dashboard,
    write_dashboard,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        target = root / "target"
        out = root / "out"
        repo.mkdir()
        target.mkdir()
        for name in REPO_REQUIRED_FILES:
            _touch(repo / name)

        report = build_dashboard(repo, target)
        assert report.overall_status == "READY_FOR_LIVE_EVIDENCE", report.overall_status
        paths = write_dashboard(report, out)
        assert Path(paths["json"]).exists()
        assert Path(paths["markdown"]).exists()
        assert Path(paths["csv"]).exists()

        live = target / "MSN_LIVE_EVIDENCE_RESULT.json"
        live.write_text(json.dumps({"final_status": "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"}), encoding="utf-8")
        promoted = build_dashboard(repo, target)
        assert promoted.overall_status == "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE", promoted.overall_status

        (repo / REPO_REQUIRED_FILES[0]).unlink()
        missing = build_dashboard(repo, target)
        assert missing.overall_status == "INCOMPLETE_TOOLING", missing.overall_status

    print("MSN operator health dashboard self-test passed.")


if __name__ == "__main__":
    main()
