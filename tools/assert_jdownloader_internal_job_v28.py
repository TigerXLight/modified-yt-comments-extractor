from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_internal_job import inspect_cnl_source_support
from jdownloader_internal_paths import JD_RUNTIME_DIR, LOCAL_JD_INSTALLED_ROOT
from jdownloader_internal_process import is_project_local_runtime


def main() -> None:
    required = [
        ROOT / "jdownloader_internal_process.py",
        ROOT / "jdownloader_internal_job.py",
        ROOT / "jdownloader_internal_download_monitor.py",
        ROOT / "jdownloader_internal_process_test.py",
        ROOT / "jdownloader_internal_job_test.py",
        ROOT / "jdownloader_internal_download_monitor_test.py",
        ROOT / "tools" / "jdownloader" / "MANAGE_INTERNAL_JDOWNLOADER_PROCESS.cmd",
        ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd",
    ]
    for path in required:
        assert path.exists(), str(path)
    assert is_project_local_runtime(JD_RUNTIME_DIR) is True
    assert is_project_local_runtime(LOCAL_JD_INSTALLED_ROOT) is False
    support = inspect_cnl_source_support()
    assert support.supported is True
    assert "flashgot" in support.endpoint_names
    assert "urls" in support.parameter_names
    assert "package" in support.parameter_names
    assert "dir" in support.parameter_names
    process_text = (ROOT / "jdownloader_internal_process.py").read_text(encoding="utf-8")
    job_text = (ROOT / "jdownloader_internal_job.py").read_text(encoding="utf-8")
    queue_text = (ROOT / "youtube_gui_media_queue.py").read_text(encoding="utf-8")
    cmd_text = (ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd").read_text(encoding="utf-8")
    assert "blocked_external_cnl_port" in process_text
    assert "LOCAL_JD_INSTALLED_ROOT" in process_text
    assert "external_appdata_used_as_primary=False" in process_text
    assert "submit_youtube_job_via_cnl" in job_text
    assert "wait_for_download_completion" in job_text
    assert "run_internal_youtube_job" in queue_text
    assert "internal_job_runner" in queue_text
    assert "yt-dlp fallback" in cmd_text
    assert "jdownloader_internal_job.py" in cmd_text
    assert "yt-dlp" not in job_text.lower()
    print("assert_jdownloader_internal_job_v28 OK")


if __name__ == "__main__":
    main()
