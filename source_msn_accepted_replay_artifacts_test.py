
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from source_msn_accepted_replay_artifacts import (
    ReferenceSpec,
    artifact_root,
    check_references,
    make_next_session_upload_bundle,
    status_from_checks,
    write_reference_index,
)


def test_reference_checks_and_status() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        good = root / "good.txt"
        good.write_text("hello", encoding="utf-8")
        specs = [
            ReferenceSpec("good", "role", str(good), "good.txt", required=True),
            ReferenceSpec("optional missing", "role", str(root / "missing.txt"), "missing.txt"),
        ]
        checks = check_references(specs)
        assert checks[0].exists
        assert not checks[1].exists
        assert status_from_checks(checks) == "ACCEPTED_MSN_REPLAY_REFERENCES_READY"


def test_reference_index_writes_background_dashboard() -> None:
    with tempfile.TemporaryDirectory() as td:
        index = write_reference_index(repo_root=td)
        assert index.is_file()
        dashboard = index.parent / "accepted-msn-replay-reference-dashboard.html"
        assert dashboard.is_file()
        payload = json.loads(index.read_text(encoding="utf-8"))
        assert payload["case_id"] == "msn_york_mosque_20260812"
        assert "accepted_routes" in payload


def test_upload_bundle_with_custom_specs() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source"
        source.mkdir()
        (source / "a.txt").write_text("alpha", encoding="utf-8")
        specs = [ReferenceSpec("folder", "role", str(source), "folder")]
        bundle = make_next_session_upload_bundle(repo_root=root, output_dir=root, specs=specs)
        assert bundle.is_file()
        with zipfile.ZipFile(bundle, "r") as z:
            names = set(z.namelist())
            assert "folder/a.txt" in names
            assert "manifest/msn_accepted_replay_reference_manifest.json" in names


if __name__ == "__main__":
    test_reference_checks_and_status()
    test_reference_index_writes_background_dashboard()
    test_upload_bundle_with_custom_specs()
    print("source_msn_accepted_replay_artifacts_test OK")
