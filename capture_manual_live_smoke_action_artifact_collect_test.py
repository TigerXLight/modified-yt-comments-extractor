from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path


from capture_manual_live_smoke_action_artifact_collect import (
    collect_manual_live_smoke_action_observation_draft,
    manual_live_smoke_action_observation_draft_to_json,
    parse_manual_live_smoke_artifact_arg,
)


def test_collects_operator_supplied_artifact_hashes_without_serializing_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact = tmp_path / "comments.json"
        payload = b'{"comments": ["one", "two"]}\n'
        artifact.write_bytes(payload)
        draft = collect_manual_live_smoke_action_observation_draft(
            site_id="msn",
            action_id="msn_comments_shadow_root_capture",
            operator_summary="Operator captured visible comments from the named MSN comments action.",
            artifacts=[f"comments_text={artifact}"],
        )
        assert draft.observed_artifacts[0].file_name == "comments.json"
        assert draft.observed_artifacts[0].sha256 == hashlib.sha256(payload).hexdigest()
        text = manual_live_smoke_action_observation_draft_to_json(draft)
        assert str(tmp_path) not in text
        assert "comments.json" in text
        assert "completed_capture_claimed" in text
        assert json.loads(text)["observation_packet_input"]["observed_artifacts"][0]["role"] == "comments_text"


def test_rejects_unknown_artifact_role_and_bad_extension() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact = tmp_path / "comments.exe"
        artifact.write_bytes(b"not allowed")
        try:
            collect_manual_live_smoke_action_observation_draft(
                site_id="msn",
                action_id="msn_comments_shadow_root_capture",
                operator_summary="Collect comments.",
                artifacts=[f"unknown_role={artifact}"],
            )
        except ValueError:
            pass
        else:
            raise AssertionError("unknown artifact role was accepted")
        try:
            collect_manual_live_smoke_action_observation_draft(
                site_id="msn",
                action_id="msn_comments_shadow_root_capture",
                operator_summary="Collect comments.",
                artifacts=[f"comments_text={artifact}"],
            )
        except ValueError:
            pass
        else:
            raise AssertionError("bad extension was accepted")


def test_parse_role_equals_path_syntax() -> None:
    parsed = parse_manual_live_smoke_artifact_arg("article_text=example.txt")
    assert parsed.role == "article_text"
    assert parsed.source_path == Path("example.txt")


if __name__ == "__main__":
    test_collects_operator_supplied_artifact_hashes_without_serializing_paths()
    test_rejects_unknown_artifact_role_and_bad_extension()
    test_parse_role_equals_path_syntax()
    print("Manual live smoke action artifact collect self-test passed.")
