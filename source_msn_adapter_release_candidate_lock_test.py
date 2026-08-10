from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_release_candidate_lock import (
    EXPECTED_REPO_ARTIFACTS,
    STATE_COMPLETE_WITH_LIVE_EVIDENCE,
    STATE_RC_LOCKED_PENDING_LIVE_EVIDENCE,
    build_release_candidate_lock,
    main,
)


def _write_expected_files(root: Path) -> None:
    for rel in EXPECTED_REPO_ARTIFACTS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"placeholder for {rel}\n", encoding="utf-8")


def test_release_candidate_lock_pending_live_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        out = Path(tmp) / "out"
        root.mkdir()
        _write_expected_files(root)
        lock = build_release_candidate_lock(root, out)
        assert lock.state == STATE_RC_LOCKED_PENDING_LIVE_EVIDENCE
        assert lock.repo_artifacts_present == len(EXPECTED_REPO_ARTIFACTS)
        assert (out / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json").exists()
        assert (out / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.md").exists()
        assert (out / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK_ARTIFACTS.csv").exists()


def test_release_candidate_lock_complete_with_positive_live_result() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        out = Path(tmp) / "out"
        root.mkdir()
        _write_expected_files(root)
        live = Path(tmp) / "live.json"
        live.write_text(json.dumps({"final_decision": "COMPLETE", "operator_result": "PASS"}), encoding="utf-8")
        lock = build_release_candidate_lock(root, out, live)
        assert lock.state == STATE_COMPLETE_WITH_LIVE_EVIDENCE


def test_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        out = Path(tmp) / "out"
        root.mkdir()
        _write_expected_files(root)
        assert main(["--repo-root", str(root), "--output-dir", str(out)]) == 0


if __name__ == "__main__":
    test_release_candidate_lock_pending_live_evidence()
    test_release_candidate_lock_complete_with_positive_live_result()
    test_cli()
    print("MSN release-candidate lock self-test passed.")
