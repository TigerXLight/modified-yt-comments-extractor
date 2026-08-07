from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_manual_live_smoke_action_implementation import (
    build_manual_live_smoke_action_plan,
    execute_manual_live_smoke_action_plan,
)
from capture_manual_live_smoke_action_run_store import (
    manual_live_smoke_action_run_store_result_to_json,
    store_manual_live_smoke_action_run,
)


def test_store_writes_safe_artifacts_without_paths() -> None:
    plan = build_manual_live_smoke_action_plan(
        site_id="msn",
        action_id="msn_article_capture",
        source_url="https://www.msn.com/en-gb/news/example",
        operator_intent="Prepare operator action.",
        dry_run=True,
    )
    run = execute_manual_live_smoke_action_plan(plan)
    with tempfile.TemporaryDirectory() as tmp:
        result = store_manual_live_smoke_action_run(output_dir=tmp, plan=plan, run=run, file_prefix="msn_article")
        assert result.artifact_count == 3
        names = [artifact.file_name for artifact in result.artifacts]
        assert names == ["msn_article_plan.json", "msn_article_run.json", "msn_article_store_result.json"]
        for artifact in result.artifacts:
            path = Path(tmp) / artifact.file_name
            assert path.exists()
            assert path.stat().st_size == artifact.byte_count
        payload = json.loads(manual_live_smoke_action_run_store_result_to_json(result))
        assert "no_full_local_paths_serialized" in payload["safety_flags"]
        assert tmp not in manual_live_smoke_action_run_store_result_to_json(result)


if __name__ == "__main__":
    test_store_writes_safe_artifacts_without_paths()
    print("Manual live smoke action run store self-test passed.")
