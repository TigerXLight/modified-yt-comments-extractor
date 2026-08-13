from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jdownloader_internal_cnl import inspect_cnl_source_routes, normalize_internal_jdownloader_url


def main() -> None:
    required = [
        ROOT / "jdownloader_internal_cnl.py",
        ROOT / "jdownloader_internal_cnl_test.py",
        ROOT / "jdownloader_internal_job.py",
        ROOT / "jdownloader_internal_job_test.py",
        ROOT / "tools" / "jdownloader" / "DIAGNOSE_INTERNAL_JDOWNLOADER_CNL.cmd",
        ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd",
    ]
    for path in required:
        assert path.exists(), str(path)
    normalized = normalize_internal_jdownloader_url(
        " [https://youtu.be/visible](  https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk  ) "
    )
    assert normalized.normalized_url == "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"
    assert normalized.warnings
    routes = inspect_cnl_source_routes()
    for route in ("/flash", "/flash/add", "/flash/addcrypted2", "/flashgot", "/jdcheck.js", "/jdcheckjson"):
        assert route in routes.supported_routes, route
    for parameter in ("urls", "package", "dir", "autostart"):
        assert parameter in routes.supported_parameters, parameter
    cnl_text = (ROOT / "jdownloader_internal_cnl.py").read_text(encoding="utf-8")
    job_text = (ROOT / "jdownloader_internal_job.py").read_text(encoding="utf-8")
    monitor_text = (ROOT / "jdownloader_internal_download_monitor.py").read_text(encoding="utf-8")
    real_cmd = (ROOT / "tools" / "jdownloader" / "RUN_INTERNAL_JDOWNLOADER_YOUTUBE_REAL_TEST.cmd").read_text(encoding="utf-8")
    diagnose_cmd = (ROOT / "tools" / "jdownloader" / "DIAGNOSE_INTERNAL_JDOWNLOADER_CNL.cmd").read_text(encoding="utf-8")
    assert "MARKDOWN_URL_RE" in cnl_text
    assert "submit_cnl_multiroute" in cnl_text
    assert "submission_attempts" in job_text
    assert "accepted_or_unknown" in job_text
    assert "submission_attempts" in monitor_text
    assert "jdownloader_internal_job.py" in real_cmd
    assert "jdownloader_internal_cnl.py" in diagnose_cmd
    assert "youtube_media_download_backend" not in real_cmd
    assert "youtube_media_download_backend" not in diagnose_cmd
    print("assert_jdownloader_internal_cnl_v30 OK")


if __name__ == "__main__":
    main()
