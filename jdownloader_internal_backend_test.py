from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from jdownloader_internal_backend import (
    build_internal_youtube_download_command,
    detect_jdownloader_internal_capabilities,
    preferred_youtube_media_backend,
    run_internal_jdownloader_probe,
)
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID, YTDLP_FALLBACK_BACKEND_ID


def test_internal_backend_detection_does_not_use_external_install_as_primary() -> None:
    caps = detect_jdownloader_internal_capabilities()
    assert caps.backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
    assert caps.installed_external_is_bootstrap_source_only is True
    if not caps.runtime_present:
        assert caps.primary_runtime_path == ""
        assert preferred_youtube_media_backend() == YTDLP_FALLBACK_BACKEND_ID


def test_internal_command_manifest_targets_bridge_not_ytdlp() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        command = build_internal_youtube_download_command(
            source_url="https://www.youtube.com/watch?v=abc123",
            output_dir=tmp,
            package_name="Package",
            max_height=1080,
        )
        assert command.backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert "ytce.jdbridge.YtceJDownloaderEngine" in command.command
        assert "yt-dlp" not in " ".join(command.command).lower()
        assert "--url" in command.command
        assert "--start-runtime" in command.command
        assert "--submit-job" in command.command
        assert "--timeout-seconds" in command.command
        assert command.start_runtime is True
        assert command.submit_job is True
        assert command.fallback_backend_id == YTDLP_FALLBACK_BACKEND_ID


def test_probe_report_writes_capabilities_without_running_external_gui() -> None:
    seen = []

    def runner(command):
        seen.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, stdout='{"status":"ok"}', stderr="")

    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "probe.json"
        report = run_internal_jdownloader_probe(runner=runner, write_report=report_path)
        assert report.status == "PROBE_COMPLETED"
        assert seen and "YtceJDownloaderEngine" in " ".join(seen[0])
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["capabilities"]["backend_id"] == JDOWNLOADER_INTERNAL_BACKEND_ID
        assert data["capabilities"]["installed_external_is_bootstrap_source_only"] is True


def main() -> None:
    test_internal_backend_detection_does_not_use_external_install_as_primary()
    test_internal_command_manifest_targets_bridge_not_ytdlp()
    test_probe_report_writes_capabilities_without_running_external_gui()
    print("jdownloader_internal_backend_test OK")


if __name__ == "__main__":
    main()
