import json
import tempfile
from pathlib import Path

from capture_msn_manual_release_pipeline_closeout_cli import main


def test_cli_builds_and_stores_closeout():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "release_section_closeout.json"
        source.write_text(
            json.dumps(
                {
                    "queue_item_id": "msn.queue",
                    "release_id": "msn.queue.release.1234",
                    "stored_files": [
                        {"filename": "safe.json", "role": "safe", "sha256": "e" * 64, "byte_count": 55}
                    ],
                }
            ),
            encoding="utf-8",
        )
        out_dir = tmp_path / "out"
        code = main(["--release-section-closeout-json", str(source), "--out-dir", str(out_dir)])
        assert code == 0
        assert len(list(out_dir.glob("*.json"))) == 3


if __name__ == "__main__":
    test_cli_builds_and_stores_closeout()
    print("MSN manual release pipeline closeout CLI self-test passed.")
