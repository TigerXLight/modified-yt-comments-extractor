from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_internal_job import normalize_jdownloader_source_url
from jdownloader_internal_process import runtime_preflight


def main() -> None:
    required = [
        ROOT / "tools" / "jdownloader" / "REPAIR_INTERNAL_JDOWNLOADER_RUNTIME.cmd",
        ROOT / "tools" / "jdownloader" / "TEST_INTERNAL_JDOWNLOADER_RUNTIME_START.cmd",
        ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd",
    ]
    for path in required:
        assert path.exists(), str(path)
    process_text = (ROOT / "jdownloader_internal_process.py").read_text(encoding="utf-8")
    job_text = (ROOT / "jdownloader_internal_job.py").read_text(encoding="utf-8")
    real_cmd = (ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd").read_text(encoding="utf-8")
    assert "LAUNCH_ATTEMPTED" in process_text
    assert "INSTALLATION_VALIDATING" in process_text
    assert "READY_TIMEOUT" in process_text
    assert "runtime_preflight" in process_text
    assert "repair_project_local_runtime" in process_text
    assert "blocked_external_cnl_port" in process_text
    assert "normalize_jdownloader_source_url" in job_text
    assert "not_attempted_not_ready" in job_text
    assert "ready_wait_ms" in job_text
    assert "yt-dlp" in real_cmd
    assert "fallback" in real_cmd
    normalized, warnings = normalize_jdownloader_source_url("[https://youtu.be/x](https://youtu.be/x)")
    assert normalized == "https://youtu.be/x"
    assert warnings
    preflight = runtime_preflight()
    assert preflight.project_local_runtime is True
    text = str(preflight.to_dict())
    for forbidden in ("AccountSettings.accounts.ejs", "downloadList", "linkcollector", "cookies", "tokens"):
        assert forbidden not in text
    print("assert_jdownloader_internal_runtime_launch_v29 OK")


if __name__ == "__main__":
    main()

