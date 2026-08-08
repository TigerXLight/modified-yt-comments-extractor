from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote, urlencode

from capture_archivebox import ArchiveBoxCommandPlan


SOURCE_ARCHIVE_EXECUTION_BRIDGE_SCHEMA_VERSION = "source_archive_execution_bridge_v1"
SOURCE_ARCHIVE_EXECUTION_SCOPE = (
    "archive execution bridge with injectable HTTP/subprocess clients; tests use fake clients "
    "only and perform no real external archive provider or ArchiveBox calls"
)


class ArchiveExecutionStatus(str, Enum):
    REQUEST_BUILT = "request_built"
    SUCCESS = "success"
    SUBMISSION_STARTED = "submission_started"
    CHALLENGE_USER_HANDOFF = "challenge_user_handoff"
    DNS_DIAGNOSTIC = "dns_diagnostic"
    APPROVAL_REQUIRED = "approval_required"
    DEPENDENCY_NOT_FOUND = "dependency_not_found"
    TIMEOUT = "timeout"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class ArchiveProviderKind(str, Enum):
    WAYBACK = "wayback"
    ARCHIVE_TODAY = "archive_today"
    ARCHIVEBOX = "archivebox"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


def _redact(value: object) -> str:
    text = str(value or "")
    for token in ("authorization", "cookie", "password", "api_key", "token", "secret"):
        text = text.replace(token, "[REDACTED]").replace(token.upper(), "[REDACTED]")
    return text[:4000]


@dataclass(frozen=True)
class ArchiveHttpRequest:
    provider: ArchiveProviderKind
    operation: str
    method: str
    url: str
    target_url: str
    explicit_submit_required: bool = False
    explicit_submit_granted: bool = False
    body: str = ""
    headers: tuple[tuple[str, str], ...] = ()
    scope: str = SOURCE_ARCHIVE_EXECUTION_SCOPE
    schema_version: str = SOURCE_ARCHIVE_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ArchiveHttpResult:
    result_id: str
    request: ArchiveHttpRequest
    status: ArchiveExecutionStatus
    http_status: int = 0
    response_excerpt: str = ""
    archive_url: str = ""
    challenge_required: bool = False
    external_call_performed_by_fake_client: bool = False
    warnings: tuple[str, ...] = ()
    scope: str = SOURCE_ARCHIVE_EXECUTION_SCOPE
    schema_version: str = SOURCE_ARCHIVE_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ArchiveBoxExecutionResult:
    execution_id: str
    status: ArchiveExecutionStatus
    command: tuple[str, ...]
    mode: str
    profile: str
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    approval_required: bool = True
    approval_granted: bool = False
    dry_run: bool = False
    timeout_seconds: int = 0
    expected_output: str = ""
    warnings: tuple[str, ...] = ()
    scope: str = SOURCE_ARCHIVE_EXECUTION_SCOPE
    schema_version: str = SOURCE_ARCHIVE_EXECUTION_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


HttpClient = Callable[[ArchiveHttpRequest], Mapping[str, Any]]
Runner = Callable[..., Any]


def build_wayback_availability_request(target_url: str) -> ArchiveHttpRequest:
    return ArchiveHttpRequest(
        provider=ArchiveProviderKind.WAYBACK,
        operation="availability_check",
        method="GET",
        url="https://archive.org/wayback/available?" + urlencode({"url": target_url}),
        target_url=target_url,
    )


def build_wayback_cdx_request(target_url: str) -> ArchiveHttpRequest:
    return ArchiveHttpRequest(
        provider=ArchiveProviderKind.WAYBACK,
        operation="cdx_history",
        method="GET",
        url="https://web.archive.org/cdx?" + urlencode({"url": target_url, "output": "json"}),
        target_url=target_url,
    )


def build_wayback_submit_request(target_url: str, *, explicit_submit_granted: bool = False) -> ArchiveHttpRequest:
    return ArchiveHttpRequest(
        provider=ArchiveProviderKind.WAYBACK,
        operation="submit",
        method="POST",
        url="https://web.archive.org/save/" + quote(target_url, safe=""),
        target_url=target_url,
        explicit_submit_required=True,
        explicit_submit_granted=explicit_submit_granted,
    )


def build_archive_today_check_request(target_url: str, *, mirror: str = "archive.ph") -> ArchiveHttpRequest:
    return ArchiveHttpRequest(
        provider=ArchiveProviderKind.ARCHIVE_TODAY,
        operation="availability_check",
        method="GET",
        url=f"https://{mirror}/" + quote(target_url, safe=""),
        target_url=target_url,
    )


def build_archive_today_submit_request(target_url: str, *, explicit_submit_granted: bool = False, mirror: str = "archive.ph") -> ArchiveHttpRequest:
    return ArchiveHttpRequest(
        provider=ArchiveProviderKind.ARCHIVE_TODAY,
        operation="submit",
        method="POST",
        url=f"https://{mirror}/submit/",
        target_url=target_url,
        explicit_submit_required=True,
        explicit_submit_granted=explicit_submit_granted,
        body=urlencode({"url": target_url}),
    )


def build_archive_dns_diagnostic_result(*, provider: ArchiveProviderKind, mirror: str, note: str) -> ArchiveHttpResult:
    request = ArchiveHttpRequest(
        provider=provider,
        operation="dns_diagnostic",
        method="DIAGNOSTIC",
        url=mirror,
        target_url="",
    )
    return ArchiveHttpResult(
        result_id="archive_dns_diagnostic_" + _sha16((provider.value, mirror, note)),
        request=request,
        status=ArchiveExecutionStatus.DNS_DIAGNOSTIC,
        response_excerpt=note,
        warnings=("DNS/mirror diagnostic is metadata only; no live lookup was performed.",),
    )


def execute_archive_http_request(request: ArchiveHttpRequest, *, http_client: HttpClient) -> ArchiveHttpResult:
    if request.explicit_submit_required and not request.explicit_submit_granted:
        return ArchiveHttpResult(
            result_id="archive_http_" + _sha16((request.to_dict(), "approval_required")),
            request=request,
            status=ArchiveExecutionStatus.APPROVAL_REQUIRED,
            warnings=("Explicit operator approval is required before archive submit.",),
        )
    try:
        response = dict(http_client(request))
    except Exception as exc:
        return ArchiveHttpResult(
            result_id="archive_http_" + _sha16((request.to_dict(), "failed")),
            request=request,
            status=ArchiveExecutionStatus.FAILED,
            warnings=(f"Archive HTTP client failed: {type(exc).__name__}",),
        )
    body = _redact(response.get("body", ""))
    status_code = int(response.get("status", response.get("status_code", 0)) or 0)
    challenge = "captcha" in body.lower() or "challenge" in body.lower()
    archive_url = str(response.get("archive_url") or "")
    status = ArchiveExecutionStatus.SUCCESS
    if challenge and request.provider == ArchiveProviderKind.ARCHIVE_TODAY:
        status = ArchiveExecutionStatus.CHALLENGE_USER_HANDOFF
    elif request.operation == "submit" and 200 <= status_code < 400:
        status = ArchiveExecutionStatus.SUBMISSION_STARTED
    elif status_code >= 400 or status_code <= 0:
        status = ArchiveExecutionStatus.FAILED
    return ArchiveHttpResult(
        result_id="archive_http_" + _sha16((request.to_dict(), status_code, body[:200])),
        request=request,
        status=status,
        http_status=status_code,
        response_excerpt=body[:500],
        archive_url=archive_url,
        challenge_required=challenge,
        external_call_performed_by_fake_client=True,
    )


def execute_archivebox_command(
    plan: ArchiveBoxCommandPlan,
    *,
    runner: Runner | None = None,
    approval_granted: bool = False,
    dry_run: bool = False,
    timeout_seconds: int = 120,
) -> ArchiveBoxExecutionResult:
    command = tuple(str(part) for part in plan.command)
    if dry_run:
        return ArchiveBoxExecutionResult(
            execution_id="archivebox_execution_" + _sha16((command, "dry_run")),
            status=ArchiveExecutionStatus.DRY_RUN,
            command=command,
            mode=plan.mode,
            profile=plan.profile,
            dry_run=True,
            approval_granted=approval_granted,
            timeout_seconds=timeout_seconds,
            expected_output=plan.expected_output,
            warnings=("Dry run: ArchiveBox command was not executed.",),
        )
    if not approval_granted:
        return ArchiveBoxExecutionResult(
            execution_id="archivebox_execution_" + _sha16((command, "approval_required")),
            status=ArchiveExecutionStatus.APPROVAL_REQUIRED,
            command=command,
            mode=plan.mode,
            profile=plan.profile,
            approval_granted=False,
            timeout_seconds=timeout_seconds,
            expected_output=plan.expected_output,
            warnings=("Explicit operator approval is required before ArchiveBox execution.",),
        )
    selected_runner = runner or subprocess.run
    try:
        completed = selected_runner(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return ArchiveBoxExecutionResult(
            execution_id="archivebox_execution_" + _sha16((command, "missing")),
            status=ArchiveExecutionStatus.DEPENDENCY_NOT_FOUND,
            command=command,
            mode=plan.mode,
            profile=plan.profile,
            approval_granted=True,
            timeout_seconds=timeout_seconds,
            expected_output=plan.expected_output,
            warnings=("ArchiveBox command dependency was not found.",),
        )
    except subprocess.TimeoutExpired:
        return ArchiveBoxExecutionResult(
            execution_id="archivebox_execution_" + _sha16((command, "timeout")),
            status=ArchiveExecutionStatus.TIMEOUT,
            command=command,
            mode=plan.mode,
            profile=plan.profile,
            approval_granted=True,
            timeout_seconds=timeout_seconds,
            expected_output=plan.expected_output,
            warnings=("ArchiveBox command timed out.",),
        )
    status = ArchiveExecutionStatus.SUCCESS if int(getattr(completed, "returncode", 1)) == 0 else ArchiveExecutionStatus.FAILED
    return ArchiveBoxExecutionResult(
        execution_id="archivebox_execution_" + _sha16((command, getattr(completed, "returncode", None))),
        status=status,
        command=command,
        mode=plan.mode,
        profile=plan.profile,
        stdout=_redact(getattr(completed, "stdout", "")),
        stderr=_redact(getattr(completed, "stderr", "")),
        returncode=int(getattr(completed, "returncode", 1)),
        approval_granted=True,
        timeout_seconds=timeout_seconds,
        expected_output=plan.expected_output,
    )

