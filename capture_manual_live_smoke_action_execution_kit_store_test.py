from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_manual_live_smoke_action_execution_kit import build_manual_live_smoke_action_execution_kit
from capture_manual_live_smoke_action_execution_kit_store import (
    manual_live_smoke_action_execution_kit_store_result_to_json,
    store_manual_live_smoke_action_execution_kit,
)


def test_store_execution_kit_writes_commands_and_safe_hashes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        kit = build_manual_live_smoke_action_execution_kit(
            site_id="msn",
            action_id="msn_article_capture",
            source_url="https://www.msn.com/en-gb/news/example",
            operator_intent="Run approved MSN article smoke action.",
            file_prefix="msn_article",
        )
        result = store_manual_live_smoke_action_execution_kit(output_directory=tmp_path, kit=kit)
        names = {artifact.file_name for artifact in result.artifacts}
        assert "msn_article_run_approved_action.cmd" in names
        assert all((tmp_path / artifact.file_name).exists() for artifact in result.artifacts)
        rendered = manual_live_smoke_action_execution_kit_store_result_to_json(result)
        assert str(tmp_path) not in rendered
        assert json.loads(rendered)["implementation_bundle"] is True


if __name__ == "__main__":
    test_store_execution_kit_writes_commands_and_safe_hashes()
    print("Manual live smoke action execution kit store self-test passed.")
