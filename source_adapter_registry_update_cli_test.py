import json
from pathlib import Path
from tempfile import TemporaryDirectory

from source_adapter_registry_update_cli import main


def test_cli_writes_registry_update_package():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        handoff = root / "handoff.json"
        out_dir = root / "out"
        handoff.write_text(
            json.dumps(
                {
                    "source_adapter_coverage_acceptance_id": "source_adapter_coverage_acceptance.example",
                    "handoff_status": "READY_FOR_ADAPTER_REGISTRY_UPDATE",
                    "adapters": [
                        {
                            "adapter_id": "article",
                            "coverage_status": "ACCEPTED_SHARED_FIXTURE_COVERAGE",
                            "shared_stage_coverage": ["content_extraction"],
                            "accepted_for_shared_pipeline": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        assert main(["--adapter-registry-handoff", str(handoff), "--output-dir", str(out_dir), "--json"]) == 0
        files = sorted(out_dir.glob("*.json"))
        assert len(files) == 5


if __name__ == "__main__":
    test_cli_writes_registry_update_package()
    print("Source Adapter Registry Update CLI self-test passed.")
