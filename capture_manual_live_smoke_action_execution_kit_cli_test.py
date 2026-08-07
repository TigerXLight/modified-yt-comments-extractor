from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from capture_manual_live_smoke_action_execution_kit_cli import main


def _run_cli(args: list[str]) -> tuple[int, dict]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(args)
    return code, json.loads(buffer.getvalue())


def test_execution_kit_cli_writes_runnable_operator_files_without_serialized_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        code, payload = _run_cli(
            [
                "--site-id",
                "msn",
                "--action-id",
                "msn_comments_shadow_root_capture",
                "--source-url",
                "https://www.msn.com/en-gb/news/example",
                "--operator-intent",
                "Run approved MSN comments smoke action.",
                "--output-directory",
                str(tmp_path),
                "--file-prefix",
                "msn_comments",
            ]
        )
        assert code == 0
        rendered = json.dumps(payload, sort_keys=True)
        assert str(tmp_path) not in rendered
        names = {artifact["file_name"] for artifact in payload["store_result"]["artifacts"]}
        assert "msn_comments_run_approved_action.cmd" in names
        assert "msn_comments_collect_artifacts_template.cmd" in names
        assert "msn_comments_msn_comments_shadow_root_snippet.js" in names
        assert (tmp_path / "msn_comments_run_approved_action.cmd").exists()
        assert payload["operator_approved_execution_supported"] is True


if __name__ == "__main__":
    test_execution_kit_cli_writes_runnable_operator_files_without_serialized_paths()
    print("Manual live smoke action execution kit CLI self-test passed.")
