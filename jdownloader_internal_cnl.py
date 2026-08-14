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
JD_DEPRECATED_API_BASE_URL = "http://127.0.0.1:3128"



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
    route_metadata: dict[str, Any] | None = None
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
    return "success" in body or "jdownloader" in body or body in {"true", "ok"}


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
    return attempt.route == "/flashgot"


def _remoteapi_arg(value: Any) -> str:
    return quote(json.dumps(value, ensure_ascii=False, separators=(",", ":")), safe="{}[]:,\"")


def _remoteapi_get_url(route: str, args: Sequence[Any]) -> str:
    query = "&".join(_remoteapi_arg(arg) for arg in args)
    return f"{JD_BASE_URL}{route}?{query}" if query else f"{JD_BASE_URL}{route}"


def _api3128_url(route: str) -> str:
    return f"{JD_DEPRECATED_API_BASE_URL}{route}"


def _attempt_api3128_route(
    *,
    route: str,
    args: Sequence[Any],
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    start = time.monotonic()
    url = _api3128_url(route)
    body = json.dumps({"params": list(args)}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "YTCE-Internal-JDownloader/1.0",
            "Accept": "application/json,*/*",
            "Connection": "close",
        },
        method="POST",
    )
    try:
        status, response_body = opener(request, timeout_seconds)
        return CnlRouteAttempt(
            route=route,
            method="POST",
            url=url,
            parameters=tuple(f"param{i}" for i, _arg in enumerate(args)),
            timeout_seconds=timeout_seconds,
            http_status=status,
            response_excerpt=(response_body or "")[:1000],
            duration_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as exc:
        return CnlRouteAttempt(
            route=route,
            method="POST",
            url=url,
            parameters=tuple(f"param{i}" for i, _arg in enumerate(args)),
            timeout_seconds=timeout_seconds,
            duration_ms=int((time.monotonic() - start) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )


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


def _api3128_attempt_is_accepted(attempt: CnlRouteAttempt) -> bool:
    return _remoteapi_attempt_is_accepted(attempt)


def _api3128_response_data(attempt: CnlRouteAttempt) -> Any:
    return _remoteapi_response_data(attempt)


def _api3128_extract_job_id(attempt: CnlRouteAttempt) -> int | None:
    data = _api3128_response_data(attempt)
    values: list[Any]
    if isinstance(data, list):
        values = data
    else:
        values = [data]
    for value in values:
        if isinstance(value, int):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        if isinstance(value, Mapping):
            for key in ("id", "jobId", "jobID", "crawlerJobId", "uuid"):
                raw = value.get(key)
                try:
                    if raw is not None:
                        return int(raw)
                except Exception:
                    continue
    return None


def _api3128_query_linkcrawler_jobs(
    *,
    job_id: int | None,
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    args: tuple[Any, ...] = ([job_id],) if job_id is not None else ()
    return _attempt_api3128_route(
        route="/linkgrabberv2/queryLinkCrawlerJobs",
        args=args,
        timeout_seconds=timeout_seconds,
        opener=opener,
    )


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


def _api3128_query_linkgrabber_packages(
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
        "name": True,
        "saveTo": True,
        "status": True,
        "uuid": True,
    }
    return _attempt_api3128_route(
        route="/linkgrabberv2/queryPackages",
        args=(query,),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )


def _api3128_query_linkgrabber_links(
    *,
    package_uuid: int | None,
    timeout_seconds: float,
    opener: UrlOpener,
) -> CnlRouteAttempt:
    query: dict[str, Any] = {
        "startAt": 0,
        "maxResults": 1000,
        "enabled": True,
        "host": True,
        "name": True,
        "packageUUIDs": [package_uuid] if package_uuid is not None else [],
        "status": True,
        "url": True,
        "uuid": True,
    }
    return _attempt_api3128_route(
        route="/linkgrabberv2/queryLinks",
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


def _api3128_package_from_attempt(attempt: CnlRouteAttempt, *, package_name: str, output_dir: str | Path) -> Mapping[str, Any] | None:
    data = _api3128_response_data(attempt)
    if not isinstance(data, list):
        return None
    fallback: Mapping[str, Any] | None = None
    for package in data:
        if not isinstance(package, Mapping):
            continue
        if str(package.get("name") or "") == package_name and fallback is None:
            fallback = package
        if _package_uuid_matches_output(package, package_name=package_name, output_dir=output_dir):
            return package
    return fallback


def _api3128_child_count(package: Mapping[str, Any] | None, links_attempt: CnlRouteAttempt | None = None) -> int:
    if package is not None:
        try:
            return int(package.get("childCount") or 0)
        except Exception:
            pass
    if links_attempt is not None:
        data = _api3128_response_data(links_attempt)
        if isinstance(data, list):
            return len(data)
    return 0


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


def submit_api3128_download_route(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str,
    timeout_seconds: float = 5.0,
    package_complete_timeout_seconds: float = 8.0,
    expected_child_count: int = 4,
    opener: UrlOpener = _default_url_opener,
) -> CnlSubmissionReport:
    started = time.monotonic()
    attempts: list[CnlRouteAttempt] = []
    warnings: list[str] = []
    errors: list[str] = []
    metadata: dict[str, Any] = {
        "api3128_enabled": True,
        "api3128_used": False,
        "api3128_api_host": "127.0.0.1",
        "api3128_api_port": 3128,
        "api3128_localhost_only": True,
        "api3128_execution_plan": "addLinks -> wait LinkGrabber stable -> moveToDownloadlist -> downloadcontroller/start",
        "api3128_route_note": "",
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
    query = {
        "links": source_url,
        "packageName": package_name,
        "destinationFolder": str(output_dir),
        "sourceUrl": source_url,
        "autostart": False,
        "overwritePackagizerRules": True,
        "assignJobID": True,
    }
    add_attempt = _attempt_api3128_route(
        route="/linkgrabberv2/addLinks",
        args=(query,),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    attempts.append(add_attempt)
    metadata["api3128_addlinks_ms"] = int(add_attempt.duration_ms or 0)
    if not _api3128_attempt_is_accepted(add_attempt):
        errors.append("API3128 addLinks did not confirm acceptance.")
        return CnlSubmissionReport("failed", tuple(attempts), route_metadata=metadata, warnings=tuple(warnings), errors=tuple(errors))

    job_id = _api3128_extract_job_id(add_attempt)
    package_uuid: int | None = None
    package_complete = False
    stable_count = 0
    last_child_count = -1
    best_child_count = 0

    while time.monotonic() - started < max(1.0, package_complete_timeout_seconds):
        jobs_attempt = _api3128_query_linkcrawler_jobs(job_id=job_id, timeout_seconds=timeout_seconds, opener=opener)
        attempts.append(jobs_attempt)
        packages_attempt = _api3128_query_linkgrabber_packages(timeout_seconds=timeout_seconds, opener=opener)
        attempts.append(packages_attempt)
        package = _api3128_package_from_attempt(packages_attempt, package_name=package_name, output_dir=output_dir)
        if package is not None:
            try:
                package_uuid = int(package.get("uuid"))
            except Exception:
                package_uuid = None
            links_attempt = _api3128_query_linkgrabber_links(
                package_uuid=package_uuid,
                timeout_seconds=timeout_seconds,
                opener=opener,
            )
            attempts.append(links_attempt)
            child_count = _api3128_child_count(package, links_attempt)
            best_child_count = max(best_child_count, child_count)
            metadata["api3128_child_count"] = best_child_count
            if child_count == last_child_count and child_count > 0:
                stable_count += 1
            else:
                stable_count = 0
            last_child_count = child_count
            if child_count >= max(1, expected_child_count) or stable_count >= 2:
                package_complete = True
                break
        time.sleep(0.25)

    metadata["api3128_package_complete_ms"] = int((time.monotonic() - started) * 1000)
    if not package_complete or package_uuid is None:
        errors.append("API3128 package never reached a complete/stable LinkGrabber state before timeout.")
        return CnlSubmissionReport("failed", tuple(attempts), route_metadata=metadata, warnings=tuple(warnings), errors=tuple(errors))

    move_attempt = _attempt_api3128_route(
        route="/linkgrabberv2/moveToDownloadlist",
        args=([], [package_uuid]),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    attempts.append(move_attempt)
    metadata["api3128_move_ms"] = int(move_attempt.duration_ms or 0)
    if not _api3128_attempt_is_accepted(move_attempt):
        errors.append("API3128 moveToDownloadlist did not confirm acceptance.")
        return CnlSubmissionReport("failed", tuple(attempts), route_metadata=metadata, warnings=tuple(warnings), errors=tuple(errors))

    start_attempt = _attempt_api3128_route(
        route="/downloadcontroller/start",
        args=(),
        timeout_seconds=timeout_seconds,
        opener=opener,
    )
    attempts.append(start_attempt)
    metadata["api3128_start_ms"] = int(start_attempt.duration_ms or 0)
    metadata["api3128_first_running_ms"] = int((time.monotonic() - started) * 1000)
    if not _api3128_attempt_is_accepted(start_attempt):
        errors.append("API3128 downloadcontroller/start did not confirm acceptance.")
        return CnlSubmissionReport("failed", tuple(attempts), route_metadata=metadata, warnings=tuple(warnings), errors=tuple(errors))

    metadata["api3128_used"] = True
    metadata["route_used"] = "api3128"
    metadata["api3128_route_note"] = "Submitted via local Deprecated API 127.0.0.1:3128 after LinkGrabber package completed/stabilized."
    return CnlSubmissionReport(
        submission_status="accepted_or_unknown",
        attempts=tuple(attempts),
        accepted_route="/api3128/linkgrabberv2/addLinks+moveToDownloadlist+downloadcontroller/start",
        route_metadata=metadata,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def submit_api3128_then_flashgot_fallback(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str,
    timeout_seconds: float = 5.0,
    total_timeout_seconds: float = 18.0,
    opener: UrlOpener = _default_url_opener,
) -> CnlSubmissionReport:
    api_report = submit_api3128_download_route(
        source_url=source_url,
        output_dir=output_dir,
        package_name=package_name,
        timeout_seconds=timeout_seconds,
        package_complete_timeout_seconds=min(8.0, max(1.0, total_timeout_seconds)),
        opener=opener,
    )
    if api_report.submission_status == "accepted_or_unknown" and api_report.route_metadata and api_report.route_metadata.get("api3128_used"):
        return api_report

    fallback = submit_cnl_multiroute(
        source_url=source_url,
        output_dir=output_dir,
        package_name=package_name,
        timeout_seconds=timeout_seconds,
        total_timeout_seconds=max(1.0, total_timeout_seconds),
        opener=opener,
        routes=("/flashgot",),
    )
    metadata = dict(api_report.route_metadata or {})
    metadata["flashgot_fallback_used"] = True
    metadata["route_used"] = "flashgot" if fallback.submission_status == "accepted_or_unknown" else "api3128_failed"
    attempts = tuple([*api_report.attempts, *fallback.attempts])
    warnings = tuple([*api_report.warnings, *fallback.warnings, "API3128 fast route failed; used /flashgot fallback."])
    errors = tuple(fallback.errors if fallback.submission_status == "accepted_or_unknown" else [*api_report.errors, *fallback.errors])
    return CnlSubmissionReport(
        submission_status=fallback.submission_status,
        attempts=attempts,
        accepted_route=fallback.accepted_route,
        route_metadata=metadata,
        warnings=warnings,
        errors=errors,
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
            if total_timeout_seconds > 0 and time.monotonic() - started >= total_timeout_seconds and not _cnl_attempt_is_accepted(attempt):
                return CnlSubmissionReport(
                    submission_status="failed",
                    attempts=tuple(attempts),
                    warnings=tuple(warnings),
                    errors=("CNL submission total timeout elapsed before all routes were attempted.",),
                )
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
