from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jdownloader_internal_job import InternalJDownloaderJobResult
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID
from shared_media_backend import (
    SHARED_MEDIA_BACKEND_ARCHITECTURE_TAG,
    SHARED_MEDIA_BACKEND_ID_JDOWNLOADER,
    build_shared_jdownloader_media_request,
    run_shared_jdownloader_media_backend,
)


def test_shared_jdownloader_backend_writes_plan_and_runs_job() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v67_shared_backend_") as tmp:
        root = Path(tmp)
        request = build_shared_jdownloader_media_request(
            source_adapter_id="youtube",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=root / "downloads",
            package_name="YTCE shared backend test",
            source_title_or_id="shared backend test",
            max_height=1080,
            components=("video", "audio", "thumbnail"),
            video=True,
            audio=True,
            image=True,
            description=True,
            wait=True,
            plan_json_path=root / "jdownloader-internal-command.json",
        )

        def fake_runner(job_request):
            manifest_path = Path(job_request.manifest_path)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text('{"status":"success","files":[]}', encoding="utf-8")
            return InternalJDownloaderJobResult(
                status="success",
                phase="completed",
                manifest_path=str(manifest_path),
                source_url=job_request.source_url,
                output_dir=job_request.output_dir,
                engine_status="started",
                readiness_status="READY",
                submission_status="accepted_or_unknown",
                files_count=0,
            )

        result = run_shared_jdownloader_media_backend(request, internal_job_runner=fake_runner)

        assert result.shared_backend_id == SHARED_MEDIA_BACKEND_ID_JDOWNLOADER
        assert result.backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert result.status == "success"
        assert result.source_adapter_id == "youtube"
        assert result.plan_json_paths
        plan = json.loads(Path(result.plan_json_paths[0]).read_text(encoding="utf-8"))
        assert plan["backend_id"] == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert "--submit-job" in plan["command"]
        assert result.plan_summary["shared_backend_id"] == SHARED_MEDIA_BACKEND_ID_JDOWNLOADER
        assert result.plan_summary["source_adapter_id"] == "youtube"


def test_architecture_tag_is_explicit() -> None:
    assert SHARED_MEDIA_BACKEND_ARCHITECTURE_TAG == "source_adapter_declares_shared_backend_executes"


def main() -> None:
    test_shared_jdownloader_backend_writes_plan_and_runs_job()
    test_architecture_tag_is_explicit()
    print("shared_media_backend_test OK")


if __name__ == "__main__":
    main()
