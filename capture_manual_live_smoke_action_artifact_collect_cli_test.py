from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from capture_manual_live_smoke_action_artifact_collect_cli import main


def _run_cli(args: list[str]) -> tuple[int, dict]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(args)
    return code, json.loads(buffer.getvalue())


def test_cli_collects_artifact_and_writes_observation_packet_without_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        comments = tmp_path / "comments.json"
        comments.write_text('{"comments": ["visible"]}\n', encoding="utf-8")
        code, payload = _run_cli(
            [
                "--site-id",
                "msn",
                "--action-id",
                "msn_comments_shadow_root_capture",
                "--operator-summary",
                "Collected operator-visible MSN comments after approved action run.",
                "--artifact",
                f"comments_text={comments}",
                "--output-json",
                str(tmp_path / "draft.json"),
                "--packet-output-dir",
                str(tmp_path),
            ]
        )
        assert code == 0
        rendered = json.dumps(payload, sort_keys=True)
        assert str(tmp_path) not in rendered
        assert payload["draft"]["observed_artifacts"][0]["file_name"] == "comments.json"
        assert payload["packet_store_result"]["files"][0]["file_name"] == "capture_manual_live_smoke_observation_packet.json"
        assert (tmp_path / "draft.json").exists()
        assert (tmp_path / "capture_manual_live_smoke_observation_packet.json").exists()


if __name__ == "__main__":
    test_cli_collects_artifact_and_writes_observation_packet_without_paths()
    print("Manual live smoke action artifact collect CLI self-test passed.")
