from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jdownloader_internal_download_monitor import (
    build_download_manifest,
    collect_completed_files,
    create_youtube_download_output_dir,
    safe_download_folder_name,
    wait_for_download_completion,
    write_download_manifest,
)
from jdownloader_internal_cnl import (
    CnlRouteAttempt,
    inspect_cnl_source_routes,
    normalize_internal_jdownloader_url,
    submit_api3128_then_flashgot_fallback,
    submit_cnl_multiroute,
)
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID
from jdownloader_internal_process import JDownloaderInternalProcessManager, READY, default_process_manager


CNL_FLASHGOT_URL = "http://127.0.0.1:9666/flashgot"
MANIFEST_NAME = "jdownloader-internal-download-manifest.json"


@dataclass(frozen=True)
class CnlSourceSupport:
    supported: bool
    source_files: tuple[str, ...]
    endpoint_names: tuple[str, ...]
    parameter_names: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CnlSubmissionResult:
    status: str
    endpoint_url: str = CNL_FLASHGOT_URL
    accepted_route: str = ""
    http_status: int = 0
    response_text: str = ""
    elapsed_ms: int = 0
    attempts: tuple[CnlRouteAttempt, ...] = ()
    route_metadata: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class InternalJDownloaderJobRequest:
    source_url: str
    output_dir: str
    package_name: str
    original_source_url: str = ""
    normalized_from_markdown: bool = False
    max_height: int = 1080
    video: bool = True
    audio: bool = True
    image: bool = True
    description: bool = True
    wait: bool = False
    timeout_seconds: int = 600
    cnl_route_timeout_seconds: float = 8.0
    cnl_total_timeout_seconds: float = 30.0
    monitor_timeout_seconds: float = 90.0
    overall_timeout_seconds: float = 150.0
    manifest_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class InternalJDownloaderJobResult:
    status: str
    manifest_path: str
    source_url: str
    output_dir: str
    engine_status: str
    readiness_status: str = ""
    submission_status: str = ""
    phase: str = ""
    original_source_url: str = ""
    normalized_source_url: str = ""
    submission_attempts_count: int = 0
    files_count: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


Submitter = Callable[[InternalJDownloaderJobRequest], CnlSubmissionResult]


def _submission_attempt_dicts(submission: CnlSubmissionResult | None) -> tuple[dict[str, Any], ...]:
    if submission is None:
        return ()
    return tuple(attempt.to_dict() for attempt in getattr(submission, "attempts", ()) or ())


def _submission_accepted(status: str) -> bool:
    return status in {"submitted", "accepted_or_unknown"}


def _empty_engine_report() -> dict[str, Any]:
    return {
        "backend_id": JDOWNLOADER_INTERNAL_BACKEND_ID,
        "status": "not_started",
        "project_local_runtime": False,
        "external_appdata_used_as_primary": False,
    }


def _write_job_manifest(
    *,
    request: InternalJDownloaderJobRequest,
    manifest_path: Path,
    phase: str,
    status: str,
    engine: Mapping[str, Any] | None,
    timings: Mapping[str, int],
    files: Sequence[Any],
    submission_status: str = "",
    submission_attempts: Sequence[Mapping[str, Any]] = (),
    warnings: Sequence[str] = (),
    errors: Sequence[str] = (),
    route_metadata: Mapping[str, Any] | None = None,
) -> None:
    manifest = build_download_manifest(
        source_url=request.source_url,
        normalized_source_url=request.source_url,
        original_source_url=request.original_source_url,
        output_dir=request.output_dir,
        status=status,
        phase=phase,
        engine=engine or _empty_engine_report(),
        timings=timings,
        files=files,
        submission_status=submission_status,
        submission_attempts=submission_attempts,
        route_metadata=route_metadata,
        warnings=tuple(warnings),
        errors=errors,
    )
    write_download_manifest(manifest, manifest_path)


def _remaining_timeout_seconds(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    return deadline - time.monotonic()


def _overall_timeout_elapsed(deadline: float | None) -> bool:
    remaining = _remaining_timeout_seconds(deadline)
    return remaining is not None and remaining <= 0


def _call_submitter(submitter: Submitter, request: InternalJDownloaderJobRequest) -> CnlSubmissionResult:
    if submitter is submit_youtube_job_via_cnl:
        return submitter(request, timeout_seconds=request.cnl_route_timeout_seconds)
    return submitter(request)


def normalize_jdownloader_source_url(value: str) -> tuple[str, tuple[str, ...]]:
    normalized = normalize_internal_jdownloader_url(value)
    return normalized.normalized_url, normalized.warnings


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def inspect_cnl_source_support(source_tree_dir: str | Path | None = None) -> CnlSourceSupport:
    route_report = inspect_cnl_source_routes(source_tree_dir) if source_tree_dir is not None else inspect_cnl_source_routes()
    endpoints = tuple(route.rsplit("/", 1)[-1] or "flash" for route in route_report.supported_routes)
    parameters = route_report.supported_parameters
    supported = "/flash/add" in route_report.supported_routes and "/flashgot" in route_report.supported_routes
    if not {"urls", "package", "dir"}.issubset(set(parameters)):
        supported = False
    warnings = list(route_report.warnings)
    if not supported:
        warnings.append("Vendored CNL source did not expose the expected /flash/add, /flashgot, and urls/package/dir parameters.")
    return CnlSourceSupport(
        supported=supported,
        source_files=route_report.source_files,
        endpoint_names=endpoints,
        parameter_names=parameters,
        warnings=tuple(warnings),
    )



def _cnl_operator_permission_warning_needed(accepted_route: str, route_metadata: Mapping[str, Any] | None) -> bool:
    # True only for legacy CNL/FlashGot. API3128 does not use the CNL permission-dialog route.
    route = dict(route_metadata or {})
    if bool(route.get("api3128_used")) or str(route.get("route_used", "")).lower() == "api3128":
        return False
    if bool(route.get("flashgot_fallback_used")):
        return True
    accepted = str(accepted_route or "").lower()
    route_used = str(route.get("route_used", "") or "").lower()
    return accepted.startswith("/flash") or route_used in {"flashgot", "/flashgot", "flash/add", "/flash/add"}


def submit_youtube_job_via_cnl(request: InternalJDownloaderJobRequest, *, timeout_seconds: float = 15.0) -> CnlSubmissionResult:
    start = time.monotonic()
    report = submit_api3128_then_flashgot_fallback(
        source_url=request.source_url,
        output_dir=request.output_dir,
        package_name=request.package_name,
        timeout_seconds=request.cnl_route_timeout_seconds or timeout_seconds,
        total_timeout_seconds=request.cnl_total_timeout_seconds,
    )
    accepted_attempt = next((attempt for attempt in report.attempts if attempt.route == report.accepted_route and not attempt.error), None)
    warnings = list(report.warnings)
    if _cnl_operator_permission_warning_needed(report.accepted_route, report.route_metadata):
        warnings.append('CNL may require operator permission inside JDownloader if this source is not pre-authorized.')
    return CnlSubmissionResult(
        status=report.submission_status,
        endpoint_url=accepted_attempt.url if accepted_attempt else CNL_FLASHGOT_URL,
        accepted_route=report.accepted_route,
        http_status=accepted_attempt.http_status if accepted_attempt else 0,
        response_text=accepted_attempt.response_excerpt if accepted_attempt else "",
        elapsed_ms=int((time.monotonic() - start) * 1000),
        attempts=report.attempts,
        route_metadata=dict(report.route_metadata or {}),
        warnings=warnings,
        errors=report.errors,
    )


def build_youtube_job_request(
    *,
    source_url: str,
    output_dir: str | Path | None = None,
    package_name: str = "",
    source_title_or_id: str = "",
    max_height: int = 1080,
    video: bool = True,
    audio: bool = True,
    image: bool = True,
    description: bool = True,
    wait: bool = False,
    timeout_seconds: int = 600,
    cnl_route_timeout_seconds: float = 8.0,
    cnl_total_timeout_seconds: float = 30.0,
    monitor_timeout_seconds: float | None = None,
    overall_timeout_seconds: float = 150.0,
) -> InternalJDownloaderJobRequest:
    original_url = source_url
    normalized_url, url_warnings = normalize_jdownloader_source_url(source_url)
    safe_name = safe_download_folder_name(source_title_or_id or package_name or "youtube_media")
    out = Path(output_dir) if output_dir is not None else create_youtube_download_output_dir(safe_title_or_id=safe_name)
    out.mkdir(parents=True, exist_ok=True)
    return InternalJDownloaderJobRequest(
        source_url=normalized_url,
        output_dir=str(out),
        package_name=package_name or safe_name,
        original_source_url=original_url,
        normalized_from_markdown=bool(url_warnings),
        max_height=int(max_height or 0),
        video=video,
        audio=audio,
        image=image,
        description=description,
        wait=wait,
        timeout_seconds=int(timeout_seconds or 0),
        cnl_route_timeout_seconds=float(cnl_route_timeout_seconds or 0),
        cnl_total_timeout_seconds=float(cnl_total_timeout_seconds or 0),
        monitor_timeout_seconds=float(monitor_timeout_seconds if monitor_timeout_seconds is not None else timeout_seconds),
        overall_timeout_seconds=float(overall_timeout_seconds or 0),
        manifest_path=str(out / MANIFEST_NAME),
    )


def _zero_timings() -> dict[str, int]:
    return {
        "engine_start_ms": 0,
        "ready_wait_ms": 0,
        "job_submit_ms": 0,
        "link_resolution_ms": 0,
        "download_wait_ms": 0,
        "first_file_seen_ms": 0,
        "pre_download_wait_ms": 0,
        "jd_finding_links_wait_ms": 0,
        "active_download_ms": 0,
        "postprocess_import_ms": 0,
        "total_ms": 0,
    }


def run_internal_youtube_job(
    request: InternalJDownloaderJobRequest,
    *,
    manager: JDownloaderInternalProcessManager | None = None,
    submitter: Submitter = submit_youtube_job_via_cnl,
    progress: Callable[[str], None] | None = None,
) -> InternalJDownloaderJobResult:
    active_manager = manager or default_process_manager()
    timings = _zero_timings()
    warnings: list[str] = []
    errors: list[str] = []
    total_start = time.monotonic()
    if request.normalized_from_markdown:
        warnings.append("Markdown link syntax was normalized to plain URL.")
    output_dir = Path(request.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(request.manifest_path) if request.manifest_path else output_dir / MANIFEST_NAME
    deadline = total_start + request.overall_timeout_seconds if request.overall_timeout_seconds > 0 else None
    engine_report: Any = None
    submission: CnlSubmissionResult | None = None
    submission_attempts: tuple[dict[str, Any], ...] = ()
    route_metadata: dict[str, Any] = {
        "api3128_enabled": True,
        "api3128_used": False,
        "api3128_addlinks_ms": 0,
        "api3128_package_complete_ms": 0,
        "api3128_child_count": 0,
        "api3128_move_ms": 0,
        "api3128_start_ms": 0,
        "api3128_first_running_ms": 0,
        "api3128_finished_ms": 0,
        "flashgot_fallback_used": False,
        "route_used": "",
    }
    files: tuple[Any, ...] = ()

    def set_phase(phase: str) -> None:
        if progress is not None:
            progress(f"Phase: {phase}")

    def write_phase(phase: str, status: str, *, submission_status: str = "", phase_errors: Sequence[str] | None = None) -> None:
        active_errors = errors if phase_errors is None else list(phase_errors)
        _write_job_manifest(
            request=request,
            manifest_path=manifest_path,
            phase=phase,
            status=status,
            engine=engine_report.to_dict() if engine_report is not None else _empty_engine_report(),
            timings=timings,
            files=files,
            submission_status=submission_status or (submission.status if submission is not None else ""),
            submission_attempts=submission_attempts,
            route_metadata=route_metadata,
            warnings=warnings,
            errors=active_errors,
        )

    try:
        set_phase("initialized")
        write_phase("initialized", "running")

        if _overall_timeout_elapsed(deadline):
            errors.append("Overall timeout elapsed before runtime readiness check.")
            write_phase("timeout", "timeout", submission_status="not_attempted_timeout")
            return InternalJDownloaderJobResult(
                status="timeout",
                phase="timeout",
                manifest_path=str(manifest_path),
                source_url=request.source_url,
                output_dir=str(output_dir),
                engine_status="not_started",
                submission_status="not_attempted_timeout",
                original_source_url=request.original_source_url,
                normalized_source_url=request.source_url,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        set_phase("runtime_ready_check")
        write_phase("runtime_ready_check", "running", submission_status="not_attempted_runtime_ready_check")
        engine_start = time.monotonic()
        engine_report = active_manager.start()
        timings["engine_start_ms"] = int((time.monotonic() - engine_start) * 1000)
        timings["ready_wait_ms"] = int(engine_report.ready_wait_ms or 0)
        warnings.extend(engine_report.warnings)
        errors.extend(engine_report.errors)
        if engine_report.errors:
            write_phase("failed", "failed", submission_status="not_attempted_engine_failed")
            return InternalJDownloaderJobResult(
                status="failed",
                phase="failed",
                manifest_path=str(manifest_path),
                source_url=request.source_url,
                output_dir=str(output_dir),
                engine_status=engine_report.status,
                readiness_status=engine_report.readiness_status,
                submission_status="not_attempted_engine_failed",
                original_source_url=request.original_source_url,
                normalized_source_url=request.source_url,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        if engine_report.readiness_status != READY:
            errors.append("Internal JDownloader was not ready; job submission was not attempted.")
            write_phase("failed", "failed", submission_status="not_attempted_not_ready")
            return InternalJDownloaderJobResult(
                status="failed",
                phase="failed",
                manifest_path=str(manifest_path),
                source_url=request.source_url,
                output_dir=str(output_dir),
                engine_status=engine_report.status,
                readiness_status=engine_report.readiness_status,
                submission_status="not_attempted_not_ready",
                original_source_url=request.original_source_url,
                normalized_source_url=request.source_url,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        if _overall_timeout_elapsed(deadline):
            errors.append("Overall timeout elapsed before CNL submission.")
            write_phase("timeout", "timeout", submission_status="not_attempted_timeout")
            return InternalJDownloaderJobResult(
                status="timeout",
                phase="timeout",
                manifest_path=str(manifest_path),
                source_url=request.source_url,
                output_dir=str(output_dir),
                engine_status=engine_report.status,
                readiness_status=engine_report.readiness_status,
                submission_status="not_attempted_timeout",
                original_source_url=request.original_source_url,
                normalized_source_url=request.source_url,
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        set_phase("cnl_route_inspection")
        write_phase("cnl_route_inspection", "running", submission_status="not_attempted_route_inspection")
        inspect_cnl_source_routes()

        set_phase("cnl_submission")
        write_phase("cnl_submission", "running", submission_status="submitting")
        submit_start = time.monotonic()
        submission = _call_submitter(submitter, request)
        timings["job_submit_ms"] = int((time.monotonic() - submit_start) * 1000)
        warnings.extend(submission.warnings)
        errors.extend(submission.errors)
        submission_attempts = _submission_attempt_dicts(submission)
        route_metadata.update(dict(submission.route_metadata or {}))
        write_phase("cnl_submission", "running" if _submission_accepted(submission.status) else "failed")

        if not _submission_accepted(submission.status):
            if not errors:
                errors.append(f"Internal JDownloader submission returned {submission.status}.")
            files = collect_completed_files(output_dir)
            write_phase("failed", "failed")
            return InternalJDownloaderJobResult(
                status="failed",
                phase="failed",
                manifest_path=str(manifest_path),
                source_url=request.source_url,
                output_dir=str(output_dir),
                engine_status=engine_report.status,
                readiness_status=engine_report.readiness_status,
                submission_status=submission.status,
                original_source_url=request.original_source_url,
                normalized_source_url=request.source_url,
                submission_attempts_count=len(submission_attempts),
                files_count=len(files),
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        if request.wait:
            set_phase("output_monitor")
            write_phase("output_monitor", "running")
            wait_start = time.monotonic()
            remaining = _remaining_timeout_seconds(deadline)
            monitor_timeout = request.monitor_timeout_seconds if request.monitor_timeout_seconds > 0 else request.timeout_seconds
            if remaining is not None:
                monitor_timeout = max(0.01, min(monitor_timeout, remaining))
            monitor = wait_for_download_completion(
                output_dir,
                timeout_seconds=monitor_timeout,
                poll_interval_seconds=0.25,
                stable_checks_required=1,
            )
            timings["download_wait_ms"] = int((time.monotonic() - wait_start) * 1000)
            timings["first_file_seen_ms"] = int(monitor.first_file_seen_ms or 0)
            timings["pre_download_wait_ms"] = int(monitor.pre_download_wait_ms or 0)
            timings["jd_finding_links_wait_ms"] = int(monitor.pre_download_wait_ms or 0)
            timings["link_resolution_ms"] = int(monitor.pre_download_wait_ms or 0)
            timings["active_download_ms"] = int(monitor.active_download_ms or 0)
            if route_metadata.get("api3128_used"):
                route_metadata["api3128_finished_ms"] = int(
                    int(route_metadata.get("api3128_package_complete_ms", 0) or 0)
                    + int(monitor.elapsed_ms or timings["download_wait_ms"])
                )
            files = monitor.files
            warnings.extend(monitor.warnings)
            errors.extend(monitor.errors)
            status = monitor.status
            phase = "completed" if status == "success" else ("timeout" if status == "timeout" else status)
        else:
            status = "partial"
            phase = "completed"
            files = collect_completed_files(output_dir)
            warnings.append("Job accepted or queued by internal JDownloader; completion monitoring was not requested by this GUI path.")

        timings["total_ms"] = int((time.monotonic() - total_start) * 1000)
        write_phase(phase, status)
        return InternalJDownloaderJobResult(
            status=status,
            phase=phase,
            manifest_path=str(manifest_path),
            source_url=request.source_url,
            output_dir=str(output_dir),
            engine_status=engine_report.status,
            readiness_status=engine_report.readiness_status,
            submission_status=submission.status,
            original_source_url=request.original_source_url,
            normalized_source_url=request.source_url,
            submission_attempts_count=len(submission_attempts),
            files_count=len(files),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )
    except KeyboardInterrupt:
        errors.append("Job cancelled by operator.")
        timings["total_ms"] = int((time.monotonic() - total_start) * 1000)
        write_phase("cancelled", "cancelled", phase_errors=errors)
        raise
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        timings["total_ms"] = int((time.monotonic() - total_start) * 1000)
        write_phase("failed", "failed", phase_errors=errors)
        return InternalJDownloaderJobResult(
            status="failed",
            phase="failed",
            manifest_path=str(manifest_path),
            source_url=request.source_url,
            output_dir=str(output_dir),
            engine_status=engine_report.status if engine_report is not None else "not_started",
            readiness_status=engine_report.readiness_status if engine_report is not None else "",
            submission_status=submission.status if submission is not None else "not_attempted_exception",
            original_source_url=request.original_source_url,
            normalized_source_url=request.source_url,
            submission_attempts_count=len(submission_attempts),
            files_count=len(files),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Submit a YouTube job to the project-local internal JDownloader runtime.")
    parser.add_argument("url")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--package-name", default="YTCE YouTube media")
    parser.add_argument("--max-height", type=int, default=1080)
    parser.add_argument("--video", action="store_true")
    parser.add_argument("--audio", action="store_true")
    parser.add_argument("--image", action="store_true")
    parser.add_argument("--description", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--cnl-route-timeout-seconds", type=float, default=8.0)
    parser.add_argument("--cnl-total-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--monitor-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--overall-timeout-seconds", type=float, default=150.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    any_component = args.video or args.audio or args.image or args.description
    request = build_youtube_job_request(
        source_url=args.url,
        output_dir=args.output_dir or None,
        package_name=args.package_name,
        source_title_or_id=args.package_name or args.url,
        max_height=args.max_height,
        video=args.video or not any_component,
        audio=args.audio or not any_component,
        image=args.image or not any_component,
        description=args.description or not any_component,
        wait=args.wait,
        timeout_seconds=args.timeout_seconds,
        cnl_route_timeout_seconds=args.cnl_route_timeout_seconds,
        cnl_total_timeout_seconds=args.cnl_total_timeout_seconds,
        monitor_timeout_seconds=args.monitor_timeout_seconds,
        overall_timeout_seconds=args.overall_timeout_seconds,
    )
    print(f"ORIGINAL_URL: {request.original_source_url}")
    print(f"NORMALIZED_URL: {request.source_url}")
    print(f"MANIFEST: {request.manifest_path}")
    try:
        result = run_internal_youtube_job(request, progress=print)
    except KeyboardInterrupt:
        print("CANCELLED: operator interrupted the internal JDownloader job.")
        print(f"MANIFEST: {request.manifest_path}")
        return 130
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    print(f"MANIFEST: {result.manifest_path}")
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
