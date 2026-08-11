from __future__ import annotations

import tempfile
from pathlib import Path

from source_capture_interaction_metadata import (
    ACCEPTED_ARTICLE_SCREENSHOT,
    ACCEPTED_COMMENTS_SCREENSHOT,
    PREFERRED_REPLAY_SCREENSHOT,
    build_interaction_metadata,
)


def _write(path: Path, content: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_artifact_backed_steps_and_screenshots_are_recorded() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prod = root / "production"
        live = root / "live_capture"
        _write(prod / "screenshots" / ACCEPTED_ARTICLE_SCREENSHOT, b"article")
        _write(prod / "screenshots" / ACCEPTED_COMMENTS_SCREENSHOT, b"comments")
        _write(live / "screenshots" / PREFERRED_REPLAY_SCREENSHOT, b"preferred")
        _write(live / "screenshots" / "full-page.png", b"too-long")
        _write(live / "rendered-page.warc.gz", b"warc")
        _write(live / "rendered-page.html", b"html")
        _write(live / "browser_capture" / "android_mobile_chromium" / "comments.json", b"[]")
        _write(live / "browser_capture" / "action_log.jsonl", b'{"action":"scroll"}\n')
        metadata = build_interaction_metadata(
            target_url="https://www.msn.com/x?ocid=edgemobile&PC=EMMX01",
            normalized_target_url="https://www.msn.com/x?ocid=edgemobile&PC=EMMX01",
            capture_roots=[str(live)],
            production_roots=[str(prod)],
        )
        statuses = {item.status for item in metadata.accepted_primary_screenshots}
        assert "ACCEPTED_PRIMARY_ARTICLE_SCREENSHOT" in statuses
        assert "ACCEPTED_PRIMARY_COMMENTS_SCREENSHOT" in statuses
        step_status = {step.step_id: step.status for step in metadata.steps}
        assert step_status["open_article"] == "RECORDED"
        assert step_status["scroll_article"] == "RECORDED"
        assert step_status["open_comments"] in {"RECORDED", "INFERRED_FROM_ARTIFACTS"}
        assert step_status["write_archive_files"] == "RECORDED"
        assert metadata.status == "RECORDED_WITH_PRIMARY_SCREENSHOTS"
        assert not metadata.warnings


def run_self_test() -> None:
    test_artifact_backed_steps_and_screenshots_are_recorded()


if __name__ == "__main__":
    run_self_test()
    print("source_capture_interaction_metadata_test OK")
