import json
import subprocess
import sys
import tempfile
from pathlib import Path

from preservation_evidence_bundle import (
    build_preservation_evidence_bundle_from_dict,
    preservation_evidence_bundle_to_dict,
)


BUNDLE_INPUT = {
    "source_url": "https://www.telegraph.co.uk/news/example/",
    "bundle_label": "Scope invariant evidence",
    "status": "manual_supplied",
    "items": [
        {
            "artifact_id": "screenshot",
            "artifact_format": "png",
            "capture_method_id": "scrollable_container_screenshot",
            "path_hint": r"captures\\comments.png",
            "notes": "Path hint only; do not inspect.",
        }
    ],
}


def _run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _assert_local_only_bundle(bundle: dict) -> None:
    scope = bundle["scope"].lower()
    assert "no file open" in scope, scope
    assert "scan" in scope, scope
    assert "hash" in scope, scope
    assert "upload" in scope, scope
    assert "capture" in scope, scope
    assert "network" in scope, scope

    item = bundle["items"][0]
    assert item["path_hint"] == r"captures\\comments.png"
    assert item["limitations"]


def run_self_test() -> None:
    bundle = build_preservation_evidence_bundle_from_dict(BUNDLE_INPUT)
    model_data = preservation_evidence_bundle_to_dict(bundle)
    _assert_local_only_bundle(model_data)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "evidence_bundle.json"
        input_path.write_text(json.dumps(BUNDLE_INPUT), encoding="utf-8")

        standalone_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "json",
        )
        assert standalone_result.returncode == 0, standalone_result.stderr
        standalone_bundle = json.loads(standalone_result.stdout)
        _assert_local_only_bundle(standalone_bundle)

        backend_input_path = Path(temp_dir) / "backend_plan.json"
        backend_input_path.write_text(
            json.dumps(
                {
                    "source_url": BUNDLE_INPUT["source_url"],
                    "selected_backend_ids": ["manual_local_files"],
                    "selected_format_ids": ["html"],
                    "evidence_bundle": BUNDLE_INPUT,
                }
            ),
            encoding="utf-8",
        )
        backend_plan_result = _run_command(
            "preservation_backend_plan_cli.py",
            "--input",
            str(backend_input_path),
            "--format",
            "json",
        )
        assert backend_plan_result.returncode == 0, backend_plan_result.stderr
        backend_plan = json.loads(backend_plan_result.stdout)
        backend_bundle = backend_plan.get("evidence_bundle")
        assert isinstance(backend_bundle, dict), backend_plan
        _assert_local_only_bundle(backend_bundle)

        total_export_result = _run_command(
            "total_export_prepare_cli.py",
            "--explain-preservation-plan",
            "--source-url",
            "https://www.telegraph.co.uk/news/example/",
            "--preservation-backend",
            "manual_local_files",
            "--preservation-format",
            "html",
            "--evidence-bundle-input",
            str(input_path),
            "--json",
        )
        assert total_export_result.returncode == 0, total_export_result.stderr
        total_export_plan = json.loads(total_export_result.stdout)
        _assert_local_only_bundle(total_export_plan["evidence_bundle"])


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle scope invariant self-test passed.")
