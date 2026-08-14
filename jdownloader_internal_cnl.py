from __future__ import annotations

import json
import re
import tempfile
import time
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from jdownloader_internal_download_monitor import create_youtube_download_output_dir, safe_download_folder_name
from jdownloader_internal_paths import JD_SOURCE_TREE_DIR
from jdownloader_internal_process import CNL_HOST, CNL_PORT, cnl_jdcheck_responds, project_local_jdownloader_process_running


MARKDOWN_URL_RE = re.compile(
    r"^\s*\[([a-zA-Z][a-zA-Z0-9+.-]*://[^\]]+)\]\(\s*([a-zA-Z][a-zA-Z0-9+.-]*://[^)\s]+)\s*\)\s*$"
)

JD_BASE_URL = f"http://{CNL_HOST}:{CNL_PORT}"
CNL_PERMISSION_BYPASS_REFERER = f"{JD_BASE_URL}/flashgot"



@dataclass(frozen=True)
class NormalizedUrl:
    original_url: str
    normalized_url: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CnlRouteAttempt:
    route: str
    method: str
    url: str
    parameters: tuple[str, ...]
    timeout_seconds: float
    http_status: int = 0
    response_excerpt: str = ""
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CnlSourceRouteReport:
    supported_routes: tuple[str, ...]
    supported_parameters: tuple[str, ...]
    source_files: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CnlSubmissionReport:
    submission_status: str
    attempts: tuple[CnlRouteAttempt, ...]
    accepted_route: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CnlDiagnosticReport:
    status: str
    original_url: str
    normalized_url: str
    output_dir: str
    jdcheck_json_ready: bool
    project_local_runtime_detected: bool
    routes: CnlSourceRouteReport
    submission: CnlSubmissionReport | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


UrlOpener = Callable[[Request, float], tuple[int, str]]


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


def normalize_http_url_for_jdownloader(value: str, *, http_only: bool = True) -> NormalizedUrl:
    original = str(value or "").strip()
    text = original.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"\"", "'"}:
        text = text[1:-1].strip()
    warnings: list[str] = []
    match = MARKDOWN_URL_RE.match(text)
    if match:
        label_url, target_url = match.groups()
        text = target_url.strip()
        warnings.append("Markdown link syntax was normalized to plain URL.")
        if label_url.strip() != target_url.strip():
            warnings.append("Markdown link label URL differed from target; target URL was used.")
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Unsupported URL input; pass a plain http(s) URL.")
    if http_only and parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Unsupported URL input; only http(s) URLs are allowed.")
    if "[" in text or "](" in text:
        raise ValueError("Unsupported URL input; Markdown link syntax remained after normalization.")
    return NormalizedUrl(original_url=original, normalized_url=text, warnings=tuple(warnings))


def normalize_internal_jdownloader_url(value: str, *, http_only: bool = True) -> NormalizedUrl:
    return normalize_http_url_for_jdownloader(value, http_only=http_only)


def inspect_cnl_source_routes(source_tree_dir: str | Path = JD_SOURCE_TREE_DIR) -> CnlSourceRouteReport:
    root = Path(source_tree_dir)
    files = (
        root / "src" / "org" / "jdownloader" / "api" / "cnl2" / "Cnl2APIBasics.java",
        root / "src" / "org" / "jdownloader" / "api" / "cnl2" / "ExternInterfaceImpl.java",
        root / "src" / "org" / "jdownloader" / "api" / "cnl2" / "Cnl2APIFlash.java",
        root / "src" / "org" / "jdownloader" / "api" / "cnl2" / "FlashGotAPI.java",
        root / "src" / "org" / "jdownloader" / "api" / "cnl2" / "CnlQueryStorable.java",
    )
    texts: list[str] = []
    present: list[str] = []
    warnings: list[str] = []
    for path in files:
        if not path.is_file():
            warnings.append(f"Missing CNL source file: {path.name}")
            continue
        present.append(str(path))
        texts.append(path.read_text(encoding="utf-8", errors="replace"))
    joined = "\n".join(texts)
    routes: list[str] = []
    if '@ApiMethodName("flash")' in joined or ('@ApiMethodName("")' in joined and '@ApiNamespace("flash")' in joined):
        routes.append("/flash")
    if '@ApiMethodName("add")' in joined:
        routes.append("/flash/add")
    if '@ApiMethodName("addcrypted2")' in joined:
        routes.append("/flash/addcrypted2")
    if '@ApiMethodName("flashgot")' in joined or "flashgot(" in joined:
        routes.append("/flashgot")
    if '@ApiMethodName("jdcheck.js")' in joined or "jdcheck.js" in joined:
        routes.append("/jdcheck.js")
    if '@ApiMethodName("jdcheckjson")' in joined or "jdcheckjson" in joined:
        routes.append("/jdcheckjson")
    parameters = tuple(
        name
        for name in (
            "urls",
            "source",
            "package",
            "url",
            "dir",
            "autostart",
            "descriptions",
            "password",
            "sourceUrl",
            "packageName",
            "destinationFolder",
            "autoStart",
            "autoConfirm",
        )
        if name in joined
    )
    if not routes:
        warnings.append("No CNL routes were detected from vendored source.")
    return CnlSourceRouteReport(
        supported_routes=tuple(routes),
        supported_parameters=parameters,
        source_files=tuple(present),
        warnings=tuple(warnings),
    )


def _default_url_opener(request: Request, timeout_seconds: float) -> tuple[int, str]:
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(16384).decode("utf-8", errors="replace")
        return response.status, body


def _cnl_request_headers() -> dict[str, str]:
    """Headers that avoid JDownloader's CNL permission dialog for local YTCE calls.

    The vendored ExternInterfaceImpl.askPermission() explicitly bypasses the
    dialog when the Referer URL path is /flashgot on a loopback host. Without
    this header, /flash/add and /flashgot can wait on a GUI permission dialog,
    which looks like a client-side HTTP timeout.
    """
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "YTCE-Internal-JDownloader/1.0",
        "Referer": CNL_PERMISSION_BYPASS_REFERER,
        "Origin": JD_BASE_URL,
        "Accept": "*/*",
        "Connection": "close",
    }


def _attempt_route(
    *,
    route: str,
    method: str,
    params: Mapping[str, str],
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    start = time.monotonic()
    url = f"{JD_BASE_URL}{route}"
    parameter_names = tuple(params.keys())
    data = urlencode(params).encode("utf-8")
    headers = _cnl_request_headers()
    request = Request(
        url,
        data=data if method == "POST" else None,
        headers=headers,
        method=method,
    )
    if method == "GET":
        request = Request(
            f"{url}?{urlencode(params)}",
            headers=headers,
            method="GET",
        )
        url = request.full_url
    try:
        status, body = opener(request, timeout_seconds)
        return CnlRouteAttempt(
            route=route,
            method=method,
            url=url,
            parameters=parameter_names,
            timeout_seconds=timeout_seconds,
            http_status=status,
            response_excerpt=(body or "")[:1000],
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:
        return CnlRouteAttempt(
            route=route,
            method=method,
            url=url,
            parameters=parameter_names,
            timeout_seconds=timeout_seconds,
            duration_ms=int((time.monotonic() - start) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


def _cnl_attempt_is_accepted(attempt: CnlRouteAttempt) -> bool:
    if attempt.error or not (200 <= attempt.http_status < 300):
        return False
    body = (attempt.response_excerpt or "").strip().lower()
    if body.startswith("failed"):
        return False
    if attempt.route == "/flashgot" and body:
        return True
    return "success" in body or "jdownloader" in body or body == "true"


def _cnl_attempt_was_sent_but_response_timed_out(attempt: CnlRouteAttempt) -> bool:
    """Treat a read timeout from a READY local JD endpoint as submit-unknown.

    For JDownloader CNL, the request can be received and the link crawler can
    continue working while the HTTP response remains blocked. In that case,
    retrying more CNL routes can duplicate jobs. The safer internal behavior is
    to monitor the intended output folder and let the manifest report timeout if
    no files appear.
    """
    if attempt.http_status:
        return False
    if not attempt.error:
        return False
    if not attempt.error.lower().startswith("timeouterror:"):
        return False
    return attempt.route in ("/flashgot", "/flash/add")


def _remoteapi_arg(value: Any) -> str:
    return quote(json.dumps(value, ensure_ascii=False, separators=(",", ":")), safe="{}[]:,\"")


def _remoteapi_get_url(route: str, args: Sequence[Any]) -> str:
    query = "&".join(_remoteapi_arg(arg) for arg in args)
    return f"{JD_BASE_URL}{route}?{query}" if query else f"{JD_BASE_URL}{route}"


def _attempt_remoteapi_route(
    *,
    route: str,
    args: Sequence[Any],
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    start = time.monotonic()
    url = _remoteapi_get_url(route, args)
    request = Request(
        url,
        headers={
            "User-Agent": "YTCE-Internal-JDownloader/1.0",
            "Accept": "application/json,*/*",
            "Connection": "close",
        },
        method="GET",
    )
    try:
        status, body = opener(request, timeout_seconds)
        return CnlRouteAttempt(
            route=route,
            method="GET",
            url=url,
            parameters=tuple(f"arg{i}" for i, _arg in enumerate(args)),
            timeout_seconds=timeout_seconds,
            http_status=status,
            response_excerpt=(body or "")[:1000],
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:
        return CnlRouteAttempt(
            route=route,
            method="GET",
            url=url,
            parameters=tuple(f"arg{i}" for i, _arg in enumerate(args)),
            timeout_seconds=timeout_seconds,
            duration_ms=int((time.monotonic() - start) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


def _remoteapi_attempt_is_accepted(attempt: CnlRouteAttempt) -> bool:
    if attempt.error or not (200 <= attempt.http_status < 300):
        return False
    body = (attempt.response_excerpt or "").strip()
    if not body:
        return True
    lowered = body.lower()
    if lowered.startswith("failed") or "exception" in lowered or "badparameter" in lowered:
        return False
    return True


def _remoteapi_response_data(attempt: CnlRouteAttempt) -> Any:
    body = (attempt.response_excerpt or "").strip()
    if not body:
        return None
    try:
        payload = json.loads(body)
    except Exception:
        return None
    if isinstance(payload, Mapping) and "data" in payload:
        return payload.get("data")
    return payload


def _query_linkgrabber_packages(
    *,
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    query = {
        "startAt": 0,
        "maxResults": 1000,
        "bytesTotal": True,
        "childCount": True,
        "enabled": True,
        "hosts": True,
        "saveTo": True,
        "status": True,
    }
    return _attempt_remoteapi_route(
        route="/linkgrabberv2/queryPackages",
        args=(query,),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )


def _query_download_packages(
    *,
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    query = {
        "startAt": 0,
        "maxResults": 1000,
        "bytesTotal": True,
        "childCount": True,
        "enabled": True,
        "hosts": True,
        "saveTo": True,
        "status": True,
        "running": True,
        "finished": True,
    }
    return _attempt_remoteapi_route(
        route="/downloadsV2/queryPackages",
        args=(query,),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )


def _package_uuid_matches_output(package: Mapping[str, Any], *, package_name: str, output_dir: str | Path) -> bool:
    name = str(package.get("name") or "")
    save_to = str(package.get("saveTo") or "")
    expected_output = str(output_dir)
    if name != package_name:
        return False
    if expected_output and save_to:
        return save_to.lower().rstrip("\\/") == expected_output.lower().rstrip("\\/")
    return True


def _find_remoteapi_package_uuid(attempt: CnlRouteAttempt, *, package_name: str, output_dir: str | Path) -> int | None:
    data = _remoteapi_response_data(attempt)
    if not isinstance(data, list):
        return None
    fallback_uuid: int | None = None
    for package in data:
        if not isinstance(package, Mapping):
            continue
        name = str(package.get("name") or "")
        if name == package_name and fallback_uuid is None:
            try:
                fallback_uuid = int(package.get("uuid"))
            except Exception:
                fallback_uuid = None
        if _package_uuid_matches_output(package, package_name=package_name, output_dir=output_dir):
            try:
                return int(package.get("uuid"))
            except Exception:
                return fallback_uuid
    return fallback_uuid


def _force_linkgrabber_package_to_downloads(
    *,
    package_name: str,
    output_dir: str | Path,
    timeout_seconds: float,
    opener: UrlOpener,
) -> tuple[list[CnlRouteAttempt], list[str], list[str]]:
    attempts: list[CnlRouteAttempt] = []
    warnings: list[str] = []
    errors: list[str] = []
    started = time.monotonic()
    package_uuid: int | None = None

    # Crawler jobs can finish after addLinks returns. Poll LinkGrabber for the
    # exact YTCE package, then explicitly move it to the Downloads list.
    while time.monotonic() - started < max(3.0, timeout_seconds):
        query_attempt = _query_linkgrabber_packages(timeout_seconds=3.0, opener=opener)
        attempts.append(query_attempt)
        package_uuid = _find_remoteapi_package_uuid(
            query_attempt,
            package_name=package_name,
            output_dir=output_dir,
        )
        if package_uuid is not None:
            break
        time.sleep(1.0)

    if package_uuid is None:
        errors.append(f"Could not find LinkGrabber package {package_name!r} to move into Downloads.")
        return attempts, warnings, errors

    set_dir_attempt = _attempt_remoteapi_route(
        route="/linkgrabberv2/setDownloadDirectory",
        args=(str(output_dir), [package_uuid]),
        timeout_seconds=5.0,
        opener=opener,
    )
    attempts.append(set_dir_attempt)
    if not _remoteapi_attempt_is_accepted(set_dir_attempt):
        warnings.append("Could not confirm LinkGrabber package download directory before moving it to Downloads.")

    move_attempt = _attempt_remoteapi_route(
        route="/linkgrabberv2/moveToDownloadlist",
        args=([], [package_uuid]),
        timeout_seconds=8.0,
        opener=opener,
    )
    attempts.append(move_attempt)
    if not _remoteapi_attempt_is_accepted(move_attempt):
        errors.append("Could not confirm LinkGrabber package moveToDownloadlist.")
        return attempts, warnings, errors

    # Start the global download controller as a belt-and-braces step. The
    # package-specific IDs change after moving into Downloads, so use start first
    # and only force-download if we can find the moved package in downloadsV2.
    start_attempt = _attempt_remoteapi_route(
        route="/downloadcontroller/start",
        args=(),
        timeout_seconds=5.0,
        opener=opener,
    )
    attempts.append(start_attempt)
    if not _remoteapi_attempt_is_accepted(start_attempt):
        warnings.append("Could not confirm downloadcontroller/start after moveToDownloadlist.")

    download_query_attempt = _query_download_packages(timeout_seconds=5.0, opener=opener)
    attempts.append(download_query_attempt)
    download_uuid = _find_remoteapi_package_uuid(
        download_query_attempt,
        package_name=package_name,
        output_dir=output_dir,
    )
    if download_uuid is not None:
        force_attempt = _attempt_remoteapi_route(
            route="/downloadcontroller/forceDownload",
            args=([], [download_uuid]),
            timeout_seconds=5.0,
            opener=opener,
        )
        attempts.append(force_attempt)
        if not _remoteapi_attempt_is_accepted(force_attempt):
            warnings.append("Could not confirm package-specific forceDownload after moveToDownloadlist.")
    else:
        warnings.append("Moved YTCE package to Downloads but could not re-query the new package UUID for forceDownload.")

    warnings.append("Forced YTCE LinkGrabber package into Downloads and requested download start.")
    return attempts, warnings, errors


def _attempt_linkgrabber_v2_addlinks(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str,
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    query = {
        "links": source_url,
        "packageName": package_name,
        "destinationFolder": str(output_dir),
        "autostart": True,
        "deepDecrypt": False,
        "overwritePackagizerRules": True,
        "assignJobID": True,
        "sourceUrl": CNL_PERMISSION_BYPASS_REFERER,
        "comment": "YTCE internal JDownloader RemoteAPI submission",
    }
    return _attempt_remoteapi_route(
        route="/linkgrabberv2/addLinks",
        args=(query,),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )

def submit_cnl_multiroute(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str,
    timeout_seconds: float = 8.0,
    total_timeout_seconds: float = 30.0,
    opener: UrlOpener = _default_url_opener,
    routes: Sequence[str] | None = None,
) -> CnlSubmissionReport:
    started = time.monotonic()
    route_report = inspect_cnl_source_routes()
    supported = set(route_report.supported_routes)
    # The local 9666 interface is the CNL/FlashGot API, not the MyJDownloader
    # RemoteAPI. On this runtime, /linkgrabberv2/* returns HTTP 501. Prefer the
    # /flash/add returns quickly and accepts autostart=true. Keep /flashgot as
    # fallback; it accepts autostart=1 but may spend longer in the JD crawler
    # before returning.
    ordered_routes = tuple(routes or ("/flashgot", "/flash/add"))
    attempts: list[CnlRouteAttempt] = []
    warnings: list[str] = list(route_report.warnings)
    base_params = {
        "urls": source_url,
        "url": source_url,
        "source": CNL_PERMISSION_BYPASS_REFERER,
        "referer": CNL_PERMISSION_BYPASS_REFERER,
        "package": package_name,
        "packageName": package_name,
        "dir": str(output_dir),
        # Route-specific value is normalised below:
        # /flashgot expects "1"; /flash/add expects "true".
        "autostart": "1",
        "autoStart": "1",
        "autoConfirm": "1",
        "descriptions": "YTCE internal JDownloader CNL submission",
    }
    for route in ordered_routes:
        if total_timeout_seconds > 0 and time.monotonic() - started >= total_timeout_seconds:
            return CnlSubmissionReport(
                submission_status="failed",
                attempts=tuple(attempts),
                warnings=tuple(warnings),
                errors=("CNL submission total timeout elapsed before all routes were attempted.",),
            )
        if route == "/remoteapi/linkgrabberv2/addLinks":
            remaining = total_timeout_seconds - (time.monotonic() - started) if total_timeout_seconds > 0 else timeout_seconds
            effective_timeout = max(0.01, min(timeout_seconds, remaining)) if total_timeout_seconds > 0 else timeout_seconds
            attempt = _attempt_linkgrabber_v2_addlinks(
                source_url=source_url,
                output_dir=output_dir,
                package_name=package_name,
                timeout_seconds=effective_timeout,
                opener=opener,
            )
            attempts.append(attempt)
            if _remoteapi_attempt_is_accepted(attempt):
                force_attempts, force_warnings, force_errors = _force_linkgrabber_package_to_downloads(
                    package_name=package_name,
                    output_dir=output_dir,
                    timeout_seconds=max(12.0, min(30.0, total_timeout_seconds)),
                    opener=opener,
                )
                attempts.extend(force_attempts)
                warnings.extend(force_warnings)
                errors.extend(force_errors)
                if force_errors:
                    warnings.append("RemoteAPI addLinks accepted the package, but the forced move/start step did not fully confirm.")
                return CnlSubmissionReport(
                    submission_status="accepted_or_unknown",
                    attempts=tuple(attempts),
                    accepted_route="/linkgrabberv2/addLinks+moveToDownloadlist",
                    warnings=tuple(
                        warnings
                        + [
                            "Submitted via local JDownloader LinkGrabber v2 RemoteAPI, then explicitly moved the YTCE package to Downloads.",
                        ]
                    ),
                    errors=tuple(errors),
                )
            warnings.append("Local LinkGrabber v2 RemoteAPI addLinks did not confirm acceptance; falling back to CNL routes.")
            continue
        if route not in supported:
            warnings.append(f"Route {route} is not present in vendored source; skipped.")
            continue
        methods = ("POST", "GET") if route == "/flash/add" else ("POST",)
        for method in methods:
            if total_timeout_seconds > 0 and time.monotonic() - started >= total_timeout_seconds:
                return CnlSubmissionReport(
                    submission_status="failed",
                    attempts=tuple(attempts),
                    warnings=tuple(warnings),
                    errors=("CNL submission total timeout elapsed before all routes were attempted.",),
                )
            remaining = total_timeout_seconds - (time.monotonic() - started) if total_timeout_seconds > 0 else timeout_seconds
            effective_timeout = max(0.01, min(timeout_seconds, remaining)) if total_timeout_seconds > 0 else timeout_seconds
            route_params = dict(base_params)
            if route == "/flash/add":
                # ExternInterfaceImpl.java checks "true". A value of "1" queues
                # the package but does not set AutoConfirm/AutoStart.
                route_params["autostart"] = "true"
                route_params["autoStart"] = "true"
                route_params["autoConfirm"] = "true"
            elif route == "/flashgot":
                # FlashGotAPI checks for "1".
                route_params["autostart"] = "1"
                route_params["autoStart"] = "1"
                route_params["autoConfirm"] = "1"
            attempt = _attempt_route(
                route=route,
                method=method,
                params=route_params,
                timeout_seconds=effective_timeout,
                opener=opener,
            )
            attempts.append(attempt)
            if _cnl_attempt_is_accepted(attempt):
                return CnlSubmissionReport(
                    submission_status="accepted_or_unknown",
                    attempts=tuple(attempts),
                    accepted_route=route,
                    warnings=tuple(warnings),
                )
            if _cnl_attempt_was_sent_but_response_timed_out(attempt):
                return CnlSubmissionReport(
                    submission_status="accepted_or_unknown",
                    attempts=tuple(attempts),
                    accepted_route=route,
                    warnings=tuple(
                        warnings
                        + [
                            "CNL request timed out while waiting for JD response; treating as submitted-unknown and monitoring output folder.",
                            "No additional CNL routes were attempted to avoid duplicate LinkGrabber jobs.",
                        ]
                    ),
                )
    return CnlSubmissionReport(
        submission_status="failed",
        attempts=tuple(attempts),
        warnings=tuple(warnings),
        errors=("All supported CNL submission routes failed or timed out.",),
    )


def diagnose_cnl(
    *,
    source_url: str,
    output_dir: str | Path | None = None,
    submit: bool = False,
    route_timeout_seconds: float = 8.0,
    total_timeout_seconds: float = 30.0,
    opener: UrlOpener = _default_url_opener,
) -> CnlDiagnosticReport:
    normalized = normalize_http_url_for_jdownloader(source_url)
    out = Path(output_dir) if output_dir is not None else create_youtube_download_output_dir(
        safe_title_or_id=safe_download_folder_name("cnl_diagnostic"),
        root=Path(tempfile.gettempdir()) / "YTCE_JDOWNLOADER_CNL_DIAGNOSTICS",
    )
    out.mkdir(parents=True, exist_ok=True)
    routes = inspect_cnl_source_routes()
    jd_ready = cnl_jdcheck_responds()
    project_local = project_local_jdownloader_process_running()
    warnings = list(normalized.warnings)
    errors: list[str] = []
    submission = None
    if submit:
        submission = submit_cnl_multiroute(
            source_url=normalized.normalized_url,
            output_dir=out,
            package_name="YTCE CNL diagnostic",
            timeout_seconds=route_timeout_seconds,
            total_timeout_seconds=total_timeout_seconds,
            opener=opener,
        )
        warnings.extend(submission.warnings)
        errors.extend(submission.errors)
    status = "ready" if jd_ready and project_local else "not_ready"
    if submission and submission.submission_status == "failed":
        status = "submission_failed"
    return CnlDiagnosticReport(
        status=status,
        original_url=normalized.original_url,
        normalized_url=normalized.normalized_url,
        output_dir=str(out),
        jdcheck_json_ready=jd_ready,
        project_local_runtime_detected=project_local,
        routes=routes,
        submission=submission,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Diagnose YTCE internal JDownloader CNL submission routes.")
    parser.add_argument("url")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--route-timeout-seconds", type=float, default=8.0)
    parser.add_argument("--total-timeout-seconds", type=float, default=30.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = diagnose_cnl(
            source_url=args.url,
            output_dir=args.output_dir or None,
            submit=args.submit,
            route_timeout_seconds=args.route_timeout_seconds,
            total_timeout_seconds=args.total_timeout_seconds,
        )
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}, indent=2, ensure_ascii=False))
        return 2
    print(f"Original URL: {report.original_url}")
    print(f"Normalized URL: {report.normalized_url}")
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
