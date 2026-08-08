from __future__ import annotations

import tempfile
from pathlib import Path

from source_operator_approval_gateway import (
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_token,
)
from source_unified_execution_runner import (
    UnifiedExecutionJobOptions,
    UnifiedExecutionJobStatus,
    run_unified_local_execution_job,
)


FIXTURE_HTML = """
<html><body>
  <article><h1>Local story</h1><p>Fixture article body.</p></article>
  <div data-comment-id="c1" data-author="A">Comment one</div>
  <div data-event-id="l1" data-author="Chat">Live chat one</div>
  <video src="/local/video.mp4"></video>
</body></html>
"""


def test_unapproved_local_job_is_blocked_before_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_unified_local_execution_job(
            source_url="local-fixture://story",
            fixture_html=FIXTURE_HTML,
            output_directory=temp_dir,
            options=UnifiedExecutionJobOptions(run_browser_capture=True),
        )
        assert result.status == UnifiedExecutionJobStatus.BLOCKED
        assert result.failure_receipts
        assert not (Path(temp_dir) / "browser" / "rendered_dom.html").exists()


def test_approved_local_job_runs_existing_bridges_and_writes_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        media = root / "fixture video.mp4"
        media.write_bytes(b"video-bytes")
        actions = (
            OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
            OperatorExecutionAction.SCREENSHOT_CAPTURE,
            OperatorExecutionAction.ARTICLE_CAPTURE,
            OperatorExecutionAction.PAGE_OUTLINE_CAPTURE,
            OperatorExecutionAction.COMMENTS_CAPTURE,
            OperatorExecutionAction.LIVECHAT_CAPTURE,
            OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
            OperatorExecutionAction.ARCHIVE_CHECK,
            OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
        )
        token = build_operator_approval_token(
            actions=actions,
            scope=OperatorExecutionScope.LOCAL_TEMP,
            approved_by_operator=True,
            allow_external_network=True,
        )
        result = run_unified_local_execution_job(
            source_url="local-fixture://story",
            fixture_html=FIXTURE_HTML,
            output_directory=root / "out",
            options=UnifiedExecutionJobOptions(
                run_browser_capture=True,
                run_media_copy=True,
                run_archive_check=True,
                write_offline_bundle=True,
                selected_media_resource_ids=("m1",),
                element_selector="article",
            ),
            approval_token=token,
            media_resources=({"resource_id": "m1", "path": str(media), "media_type": "video"},),
            archive_http_client=lambda request: {
                "status": 200,
                "body": '{"archived_snapshots":{}}',
                "archive_url": "https://web.archive.org/web/1/local-fixture",
            },
        )
        assert result.status == UnifiedExecutionJobStatus.COMPLETED
        assert result.browser_result is not None
        assert result.media_copy_queue is not None
        assert result.archive_result is not None
        assert result.offline_bundle_result is not None
        assert (root / "out" / "browser" / "rendered_dom.html").is_file()
        assert (root / "out" / "browser" / "faithful_full_page.png").is_file()
        assert (root / "out" / "media" / "fixture_video.mp4").is_file()
        assert (root / "out" / "offline_bundle.zip").is_file()
        assert result.artifact_hashes
        assert "offline_bundle_written" in result.behavior_event_labels
        assert result.external_network_performed is False
        assert result.archive_provider_real_call_performed is False


if __name__ == "__main__":
    test_unapproved_local_job_is_blocked_before_artifacts()
    test_approved_local_job_runs_existing_bridges_and_writes_artifacts()
    print("source_unified_execution_runner_test.py passed")
