from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from capture_manual_live_smoke_action_run_cli import main


def _run_cli(args: list[str]) -> tuple[int, dict]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(args)
    return code, json.loads(buffer.getvalue())


def test_list_actions_cli() -> None:
    code, payload = _run_cli(["--list-actions"])
    assert code == 0
    assert any(action["key"] == "msn:msn_comments_shadow_root_capture" for action in payload["actions"])


def test_dry_run_cli_stores_safe_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        code, payload = _run_cli(
            [
                "--site-id",
                "msn",
                "--action-id",
                "msn_comments_shadow_root_capture",
                "--source-url",
                "https://www.msn.com/en-gb/news/example",
                "--operator-intent",
                "Run manual comments smoke action.",
                "--output-dir",
                tmp,
                "--file-prefix",
                "msn_comments_action",
            ]
        )
        assert code == 0
        assert payload["plan"]["dry_run"] is True
        assert payload["run"]["execution_allowed"] is False
        names = [artifact["file_name"] for artifact in payload["store_result"]["artifacts"]]
        assert "msn_comments_action_plan.json" in names
        assert "msn_comments_action_run.json" in names
        assert all((Path(tmp) / name).exists() for name in names)


if __name__ == "__main__":
    test_list_actions_cli()
    test_dry_run_cli_stores_safe_files()
    print("Manual live smoke action run CLI self-test passed.")
