from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_internal_cnl import normalize_http_url_for_jdownloader


EXACT_USER_MARKDOWN_URL = "[https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk](https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk)"
EXPECTED_URL = "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"


def main() -> None:
    normalized = normalize_http_url_for_jdownloader(EXACT_USER_MARKDOWN_URL)
    assert normalized.normalized_url == EXPECTED_URL
    assert "[" not in normalized.normalized_url
    assert "](" not in normalized.normalized_url
    assert ")" not in normalized.normalized_url
    cnl_text = (ROOT / "jdownloader_internal_cnl.py").read_text(encoding="utf-8")
    job_text = (ROOT / "jdownloader_internal_job.py").read_text(encoding="utf-8")
    monitor_text = (ROOT / "jdownloader_internal_download_monitor.py").read_text(encoding="utf-8")
    real_cmd = (ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd").read_text(encoding="utf-8")
    diagnose_cmd = (ROOT / "tools" / "jdownloader" / "DIAGNOSE_INTERNAL_JDOWNLOADER_CNL.cmd").read_text(encoding="utf-8")
    assert "normalize_http_url_for_jdownloader" in cnl_text
    assert "total_timeout_seconds" in cnl_text
    assert "route-timeout-seconds" in cnl_text
    for phase in (
        "initialized",
        "runtime_ready_check",
        "cnl_route_inspection",
        "cnl_submission",
        "output_monitor",
        "completed",
        "failed",
        "timeout",
        "cancelled",
    ):
        assert phase in job_text, phase
    assert "write_phase(\"initialized\", \"running\")" in job_text
    assert "KeyboardInterrupt" in job_text
    assert ".tmp" in monitor_text
    for timeout_arg in (
        "--cnl-route-timeout-seconds 8",
        "--cnl-total-timeout-seconds 30",
        "--monitor-timeout-seconds 90",
        "--overall-timeout-seconds 150",
    ):
        assert timeout_arg in real_cmd
    assert "jdownloader_internal_job.py" in real_cmd
    assert "jdownloader_internal_cnl.py" in diagnose_cmd
    assert "youtube_media_download_backend" not in real_cmd
    assert "youtube_media_download_backend" not in diagnose_cmd
    print("assert_jdownloader_internal_timeout_manifest_v31 OK")


if __name__ == "__main__":
    main()
