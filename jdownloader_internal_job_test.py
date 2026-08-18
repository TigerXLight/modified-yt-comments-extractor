from __future__ import annotations

import json
import tempfile
from pathlib import Path

from jdownloader_internal_job import (
    CnlRouteAttempt,
    CnlSubmissionResult,
    build_youtube_job_request,
    inspect_cnl_source_support,
    normalize_jdownloader_source_url,
    run_internal_youtube_job,
    submit_youtube_job_via_cnl,
)
from jdownloader_internal_paths import JD_RUNTIME_DIR
from jdownloader_internal_process import JDownloaderInternalProcessManager


class FakeReadyManager:
    def start(self):
        from jdownloader_internal_process import JDownloaderProcessReport

        return JDownloaderProcessReport(
            status="READY",
            runtime_dir=str(JD_RUNTIME_DIR),
            executable_path=str(JD_RUNTIME_DIR / "JDownloader2.exe"),
            pid=5678,
            project_local_runtime=True,
            external_appdata_used_as_primary=False,
            readiness_status="READY",
            launch_state="READY",
            cwd=str(JD_RUNTIME_DIR),
        )


class FakeNotReadyManager:
    def start(self):
        from jdownloader_internal_process import JDownloaderProcessReport

        return JDownloaderProcessReport(
            status="READY_TIMEOUT",
            runtime_dir=str(JD_RUNTIME_DIR),
            executable_path=str(JD_RUNTIME_DIR / "JDownloader2.exe"),
            pid=5678,
            project_local_runtime=True,
            external_appdata_used_as_primary=False,
            readiness_status="READY_TIMEOUT",
            launch_state="READY_TIMEOUT",
            cwd=str(JD_RUNTIME_DIR),
        )


class FakeProcess:
    pid = 5678

    def poll(self):
        return None

    def terminate(self) -> None:
        pass

    def wait(self, timeout=None):
        return 0


def _fake_popen(command, **kwargs):
    return FakeProcess()


def test_markdown_url_is_normalized_and_garbage_rejected() -> None:
    url, warnings = normalize_jdownloader_source_url(
        " [https://youtu.be/visible?si=old](  https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk  ) "
    )
    assert url == "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"
    assert "Markdown link syntax" in warnings[0]
    request = build_youtube_job_request(
        source_url=' "[https://youtu.be/abc](https://youtu.be/abc)" ',
        output_dir=Path(tempfile.gettempdir()) / "ytce_v29_url_test",
    )
    assert request.source_url == "https://youtu.be/abc"
    assert request.original_source_url.strip().startswith('"[')
    assert request.normalized_from_markdown is True
    try:
        normalize_jdownloader_source_url("not a url")
    except ValueError as error:
        assert "plain http" in str(error)
    else:
        raise AssertionError("garbage URL was accepted")


def test_cnl_source_support_is_verified_from_vendored_source() -> None:
    support = inspect_cnl_source_support()
    assert support.supported is True
    assert "flashgot" in support.endpoint_names
    assert "add" in support.endpoint_names
    assert "urls" in support.parameter_names
    assert "package" in support.parameter_names
    assert "dir" in support.parameter_names


def test_job_submission_writes_manifest_with_project_local_engine() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
            wait=False,
        )
        manager = FakeReadyManager()

        def submitter(_request):
            return CnlSubmissionResult(
                status="accepted_or_unknown",
                accepted_route="/flash/add",
                http_status=200,
                response_text="JDownloader",
                attempts=(
                    CnlRouteAttempt(
                        route="/flash/add",
                        method="POST",
                        url="http://127.0.0.1:9666/flash/add",
                        parameters=("urls", "package", "dir"),
                        timeout_seconds=1,
                        http_status=200,
                        response_excerpt="JDownloader",
                    ),
                ),
            )

        result = run_internal_youtube_job(request, manager=manager, submitter=submitter)
        assert result.status == "partial"
        assert result.submission_status == "accepted_or_unknown"
        assert result.submission_attempts_count == 1
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["backend_id"] == "jdownloader_internal"
        assert manifest["phase"] == "completed"
        assert manifest["source_url"] == "https://youtu.be/example"
        assert manifest["original_source_url"] == "https://youtu.be/example"
        assert manifest["normalized_source_url"] == "https://youtu.be/example"
        assert manifest["submission_status"] == "accepted_or_unknown"
        assert manifest["submission_attempts"][0]["route"] == "/flash/add"
        assert manifest["engine"]["project_local_runtime"] is True
        assert manifest["engine"]["external_appdata_used_as_primary"] is False
        assert "completion monitoring was not requested" in "\n".join(manifest["warnings"])


def test_job_wait_success_collects_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
            wait=True,
            timeout_seconds=5,
        )
        manager = FakeReadyManager()

        def submitter(active_request):
            Path(active_request.output_dir, "video.mp4").write_bytes(b"video")
            return CnlSubmissionResult(status="accepted_or_unknown", accepted_route="/flashgot", http_status=200, response_text="JDownloader")

        result = run_internal_youtube_job(request, manager=manager, submitter=submitter)
        assert result.status == "success"
        assert result.files_count == 1
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["phase"] == "completed"
        assert manifest["files"][0]["kind"] == "video"


def test_job_blocks_preexisting_external_cnl_and_writes_failure_manifest() -> None:
    import jdownloader_internal_process as process_module

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
        )
        original = process_module.project_local_jdownloader_process_running
        try:
            process_module.project_local_jdownloader_process_running = lambda _runtime_dir=JD_RUNTIME_DIR: False
            manager = JDownloaderInternalProcessManager(runtime_dir=JD_RUNTIME_DIR, cnl_probe=lambda: True)
            result = run_internal_youtube_job(request, manager=manager, submitter=lambda _request: CnlSubmissionResult(status="submitted"))
        finally:
            process_module.project_local_jdownloader_process_running = original
        assert result.status == "failed"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["engine"]["external_cnl_port_in_use"] is True
        assert manifest["engine"]["external_appdata_used_as_primary"] is False


def test_job_does_not_submit_when_engine_is_not_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="[https://youtu.be/example](https://youtu.be/example)",
            output_dir=root / "downloads",
            package_name="YTCE test package",
        )
        manager = FakeNotReadyManager()
        submitted = []

        def submitter(active_request):
            submitted.append(active_request)
            return CnlSubmissionResult(status="submitted")

        result = run_internal_youtube_job(request, manager=manager, submitter=submitter)
        assert result.status == "failed"
        assert result.submission_status == "not_attempted_not_ready"
        assert not submitted
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["normalized_source_url"] == "https://youtu.be/example"
        assert manifest["original_source_url"].startswith("[https://")
        assert manifest["submission_status"] == "not_attempted_not_ready"
        assert manifest["phase"] == "failed"
        assert manifest["submission_attempts"] == []
        assert any("Markdown link syntax" in warning for warning in manifest["warnings"])


def test_initial_manifest_is_written_before_submission() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
        )

        def submitter(active_request):
            manifest = json.loads(Path(active_request.manifest_path).read_text(encoding="utf-8"))
            assert manifest["status"] == "running"
            assert manifest["phase"] == "cnl_submission"
            assert manifest["submission_status"] == "submitting"
            assert manifest["normalized_source_url"] == "https://youtu.be/example"
            return CnlSubmissionResult(status="accepted_or_unknown")

        result = run_internal_youtube_job(request, manager=FakeReadyManager(), submitter=submitter)
        assert result.status == "partial"


def test_monitor_timeout_updates_manifest_without_hanging() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
            wait=True,
            monitor_timeout_seconds=0.01,
            overall_timeout_seconds=5,
        )
        result = run_internal_youtube_job(
            request,
            manager=FakeReadyManager(),
            submitter=lambda _request: CnlSubmissionResult(status="accepted_or_unknown", accepted_route="/flashgot"),
        )
        assert result.status == "timeout"
        assert result.phase == "timeout"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["status"] == "timeout"
        assert manifest["phase"] == "timeout"
        assert manifest["submission_status"] == "accepted_or_unknown"


def test_keyboard_interrupt_writes_cancelled_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
        )

        def submitter(_request):
            raise KeyboardInterrupt

        try:
            run_internal_youtube_job(request, manager=FakeReadyManager(), submitter=submitter)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("KeyboardInterrupt was swallowed")
        manifest = json.loads(Path(request.manifest_path).read_text(encoding="utf-8"))
        assert manifest["status"] == "cancelled"
        assert manifest["phase"] == "cancelled"
        assert "cancelled by operator" in "\n".join(manifest["errors"])


def test_accepted_without_files_is_partial_not_failed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
            wait=False,
        )
        result = run_internal_youtube_job(
            request,
            manager=FakeReadyManager(),
            submitter=lambda _request: CnlSubmissionResult(status="accepted_or_unknown", accepted_route="/flashgot"),
        )
        assert result.status == "partial"
        assert result.submission_status == "accepted_or_unknown"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["status"] == "partial"
        assert manifest["phase"] == "completed"
        assert manifest["errors"] == []


def test_failed_submission_remains_failed_with_attempts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request = build_youtube_job_request(
            source_url="https://youtu.be/example",
            output_dir=root / "downloads",
            package_name="YTCE test package",
        )
        attempt = CnlRouteAttempt(
            route="/flash/add",
            method="POST",
            url="http://127.0.0.1:9666/flash/add",
            parameters=("urls",),
            timeout_seconds=1,
            error="TimeoutError: timed out",
        )
        result = run_internal_youtube_job(
            request,
            manager=FakeReadyManager(),
            submitter=lambda _request: CnlSubmissionResult(status="failed", attempts=(attempt,), errors=("all routes failed",)),
        )
        assert result.status == "failed"
        manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
        assert manifest["submission_status"] == "failed"
        assert manifest["phase"] == "failed"
        assert manifest["submission_attempts"][0]["error"] == "TimeoutError: timed out"



def test_api3128_submission_does_not_emit_legacy_cnl_permission_warning() -> None:
    import jdownloader_internal_job as job_module
    from jdownloader_internal_cnl import CnlSubmissionReport

    request = build_youtube_job_request(
        source_url="https://youtu.be/example",
        output_dir=Path(tempfile.gettempdir()) / "ytce_v65b_api3128_warning_test",
        package_name="YTCE api3128 package",
        wait=False,
    )

    def fake_submitter(**_kwargs):
        attempt = CnlRouteAttempt(
            route="/linkgrabberv2/addLinks",
            method="POST",
            url="http://127.0.0.1:3128/linkgrabberv2/addLinks",
            parameters=(),
            timeout_seconds=1,
            http_status=200,
            response_excerpt="ok",
        )
        return CnlSubmissionReport(
            submission_status="accepted_or_unknown",
            attempts=(attempt,),
            accepted_route="/api3128/linkgrabberv2/addLinks+moveToDownloadlist+downloadcontroller/start",
            route_metadata={
                "api3128_enabled": True,
                "api3128_used": True,
                "api3128_api_host": "127.0.0.1",
                "api3128_api_port": 3128,
                "api3128_localhost_only": True,
                "api3128_route_note": "submitted by test",
                "flashgot_fallback_used": False,
                "route_used": "api3128",
            },
            warnings=(),
            errors=(),
        )

    original = job_module.submit_api3128_then_flashgot_fallback
    try:
        job_module.submit_api3128_then_flashgot_fallback = fake_submitter
        result = submit_youtube_job_via_cnl(request)
    finally:
        job_module.submit_api3128_then_flashgot_fallback = original

    assert result.accepted_route.startswith("/api3128/")
    assert result.route_metadata["route_used"] == "api3128"
    assert result.route_metadata["api3128_used"] is True
    assert result.route_metadata.get("route_label", "").startswith("JDownloader API3128")
    assert result.route_metadata.get("yt_dlp_role") == "fallback_only_after_jdownloader_routes"
    assert result.route_metadata.get("yt_dlp_used") is False
    assert not any("CNL may require operator permission" in warning for warning in result.warnings)


def test_flashgot_fallback_keeps_cnl_permission_warning() -> None:
    import jdownloader_internal_job as job_module
    from jdownloader_internal_cnl import CnlSubmissionReport

    request = build_youtube_job_request(
        source_url="https://youtu.be/example",
        output_dir=Path(tempfile.gettempdir()) / "ytce_v65b_flashgot_warning_test",
        package_name="YTCE flashgot package",
        wait=False,
    )

    def fake_submitter(**_kwargs):
        attempt = CnlRouteAttempt(
            route="/flashgot",
            method="POST",
            url="http://127.0.0.1:9666/flashgot",
            parameters=(),
            timeout_seconds=1,
            http_status=200,
            response_excerpt="JDownloader",
        )
        return CnlSubmissionReport(
            submission_status="accepted_or_unknown",
            attempts=(attempt,),
            accepted_route="/flashgot",
            route_metadata={
                "api3128_enabled": True,
                "api3128_used": False,
                "flashgot_fallback_used": True,
                "route_used": "flashgot",
            },
            warnings=("API3128 fast route failed; used /flashgot fallback.",),
            errors=(),
        )

    original = job_module.submit_api3128_then_flashgot_fallback
    try:
        job_module.submit_api3128_then_flashgot_fallback = fake_submitter
        result = submit_youtube_job_via_cnl(request)
    finally:
        job_module.submit_api3128_then_flashgot_fallback = original

    assert result.accepted_route == "/flashgot"
    assert result.route_metadata["flashgot_fallback_used"] is True
    assert result.route_metadata.get("route_label", "").startswith("JDownloader FlashGot")
    assert result.route_metadata.get("yt_dlp_role") == "fallback_only_after_jdownloader_routes"
    assert any("CNL may require operator permission" in warning for warning in result.warnings)

def main() -> None:
    test_markdown_url_is_normalized_and_garbage_rejected()
    test_cnl_source_support_is_verified_from_vendored_source()
    test_job_submission_writes_manifest_with_project_local_engine()
    test_job_wait_success_collects_files()
    test_job_blocks_preexisting_external_cnl_and_writes_failure_manifest()
    test_job_does_not_submit_when_engine_is_not_ready()
    test_initial_manifest_is_written_before_submission()
    test_monitor_timeout_updates_manifest_without_hanging()
    test_keyboard_interrupt_writes_cancelled_manifest()
    test_accepted_without_files_is_partial_not_failed()
    test_failed_submission_remains_failed_with_attempts()
    test_api3128_submission_does_not_emit_legacy_cnl_permission_warning()
    test_flashgot_fallback_keeps_cnl_permission_warning()
    print("jdownloader_internal_job_test OK")


if __name__ == "__main__":
    main()
