from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from shared_media_backend import (
    SharedMediaBackendRequest,
    SharedMediaBackendResult,
    build_shared_jdownloader_media_request,
    run_shared_jdownloader_media_backend,
)
from source_adapters import TWITTER_X_SOURCE_ADAPTER


TWITTER_MEDIA_BACKEND_SCHEMA_VERSION = "twitter_media_backend.v68"
TWITTER_MEDIA_BACKEND_PROFILE_ID = "twitter_x_media_shared_backend"
TWITTER_MEDIA_BACKEND_DEFAULT_COMPONENTS = ("video", "audio", "image")
TWITTER_JDOWNLOADER_CAPABILITY_DOMAINS = ("x.com", "twitter.com")
TWITTER_DIRECT_MEDIA_HOSTS = ("pbs.twimg.com", "video.twimg.com")
TWITTER_DIRECT_MEDIA_SCHEMES = ("http", "https")
TWITTER_DIRECT_MEDIA_CAPABILITY_EVIDENCE_PATH = ""


@dataclass(frozen=True)
class TwitterJDownloaderCapabilityStatus:
    capability_manifest_path: str
    capability_found: bool
    capability_tested: bool
    matched_domains: tuple[str, ...] = ()
    plugin_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterDirectMediaCapabilityEvidenceStatus:
    evidence_path: str
    tested: bool
    source_url: str = ""
    observed_host: str = ""
    status: str = ""
    phase: str = ""
    files_count: int = 0
    api3128_used: bool = False
    route_used: str = ""
    manifest_path: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterMediaBackendPlan:
    schema_version: str
    profile_id: str
    source_url: str
    canonical_url: str
    source_id: str
    output_dir: str
    package_name: str
    max_height: int
    components: tuple[str, ...]
    allow_untested_jdownloader: bool
    jdownloader_capability: TwitterJDownloaderCapabilityStatus
    execution_allowed: bool
    direct_media_capability_evidence: TwitterDirectMediaCapabilityEvidenceStatus | None = None
    blocked_reason: str = ""
    route_note: str = "YTCE-owned Twitter/X media request routed to the shared JDownloader API3128 backend."

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterMediaBackendResult:
    status: str
    evidence_completion_claim: str
    plan: TwitterMediaBackendPlan
    shared_backend_result: SharedMediaBackendResult | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


TwitterSharedBackendRunner = Callable[[SharedMediaBackendRequest], SharedMediaBackendResult]


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


def unwrap_twitter_media_input_url(source_url: str) -> str:
    import re

    raw = str(source_url or "").strip()
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", raw)
    if markdown:
        return markdown.group(2).strip()
    angle = re.match(r"^<(https?://[^>]+)>$", raw, flags=re.I)
    if angle:
        return angle.group(1).strip()
    return raw


def is_twitter_direct_media_url(source_url: str) -> bool:
    parsed = urlsplit(unwrap_twitter_media_input_url(source_url))
    return (
        (parsed.scheme or "").lower() in TWITTER_DIRECT_MEDIA_SCHEMES
        and (parsed.hostname or "").lower() in TWITTER_DIRECT_MEDIA_HOSTS
    )


def normalize_twitter_media_source_url(source_url: str) -> str:
    unwrapped = unwrap_twitter_media_input_url(source_url)
    if is_twitter_direct_media_url(unwrapped):
        return unwrapped
    return TWITTER_X_SOURCE_ADAPTER.normalize_url(unwrapped)


def _extract_twitter_media_source_id(canonical_url: str) -> str:
    if is_twitter_direct_media_url(canonical_url):
        parsed = urlsplit(canonical_url)
        path = parsed.path.strip("/")
        host = parsed.hostname or parsed.netloc
        return f"{host}/{path}" if path else str(host or canonical_url)
    return TWITTER_X_SOURCE_ADAPTER.extract_source_id(canonical_url)

def _load_capability_manifest(path: str | Path = "jd_capabilities_manifest.json") -> Mapping[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def twitter_jdownloader_capability_status(
    capability_manifest_path: str | Path = "jd_capabilities_manifest.json",
) -> TwitterJDownloaderCapabilityStatus:
    manifest = _load_capability_manifest(capability_manifest_path)
    capabilities = manifest.get("capabilities", {}) if isinstance(manifest, Mapping) else {}
    matched_domains: list[str] = []
    plugin_names: list[str] = []
    tested = False
    for domain in TWITTER_JDOWNLOADER_CAPABILITY_DOMAINS:
        details = capabilities.get(domain)
        if not isinstance(details, Mapping):
            continue
        matched_domains.append(domain)
        tested = tested or bool(details.get("tested"))
        for plugin in details.get("plugins", ()) or ():
            if isinstance(plugin, Mapping) and plugin.get("plugin_name"):
                plugin_names.append(str(plugin["plugin_name"]))
    return TwitterJDownloaderCapabilityStatus(
        capability_manifest_path=str(capability_manifest_path),
        capability_found=bool(matched_domains),
        capability_tested=tested,
        matched_domains=tuple(sorted(set(matched_domains))),
        plugin_names=tuple(sorted(set(plugin_names))),
    )


def twitter_direct_media_capability_evidence_status(
    evidence_path: str | Path = "",
) -> TwitterDirectMediaCapabilityEvidenceStatus:
    if not str(evidence_path or '').strip():
        return TwitterDirectMediaCapabilityEvidenceStatus(evidence_path='', tested=False)
    path = Path(evidence_path)
    warnings: list[str] = []
    if not path.is_file():
        return TwitterDirectMediaCapabilityEvidenceStatus(evidence_path=str(path), tested=False)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return TwitterDirectMediaCapabilityEvidenceStatus(
            evidence_path=str(path),
            tested=False,
            warnings=(f"Could not read direct media capability evidence: {type(exc).__name__}: {exc}",),
        )
    if not isinstance(payload, Mapping):
        return TwitterDirectMediaCapabilityEvidenceStatus(
            evidence_path=str(path),
            tested=False,
            warnings=("Direct media capability evidence was not a JSON object.",),
        )
    source_url = str(payload.get("source_url") or "")
    observed_host = str(payload.get("observed_host") or "")
    status = str(payload.get("status") or "")
    phase = str(payload.get("phase") or "")
    route_used = str(payload.get("route_used") or "")
    manifest_path = str(payload.get("manifest_path") or "")
    try:
        files_count = int(payload.get("files_count") or 0)
    except Exception:
        files_count = 0
    api3128_used = bool(payload.get("api3128_used"))
    tested = bool(payload.get("tested"))
    if not is_twitter_direct_media_url(source_url):
        tested = False
        if source_url:
            warnings.append("Direct media capability evidence source_url was not a supported Twitter direct media URL.")
    if status != "success":
        tested = False
    if files_count < 1:
        tested = False
    if not api3128_used or route_used.lower() != "api3128":
        tested = False
    return TwitterDirectMediaCapabilityEvidenceStatus(
        evidence_path=str(path),
        tested=tested,
        source_url=source_url,
        observed_host=observed_host,
        status=status,
        phase=phase,
        files_count=files_count,
        api3128_used=api3128_used,
        route_used=route_used,
        manifest_path=manifest_path,
        warnings=tuple(warnings),
    )


def build_twitter_media_backend_plan(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str = "",
    max_height: int = 1080,
    components: Sequence[str] = TWITTER_MEDIA_BACKEND_DEFAULT_COMPONENTS,
    capability_manifest_path: str | Path = "jd_capabilities_manifest.json",
    allow_untested_jdownloader: bool = True,
    direct_media_capability_evidence_path: str | Path = "",
) -> TwitterMediaBackendPlan:
    canonical_url = normalize_twitter_media_source_url(source_url)
    direct_media_url = is_twitter_direct_media_url(canonical_url)
    source_id = _extract_twitter_media_source_id(canonical_url)
    parsed = urlsplit(canonical_url)
    title_part = parsed.path.strip("/").replace("/", "_") or "twitter_x_media"
    resolved_package_name = package_name or f"YTCE - X Twitter - {title_part}"
    capability = twitter_jdownloader_capability_status(capability_manifest_path)
    direct_media_evidence = (
        twitter_direct_media_capability_evidence_status(direct_media_capability_evidence_path)
        if direct_media_url
        else None
    )
    if direct_media_url:
        route_note = "YTCE-owned Twitter/X direct rendered-DOM media URL routed to the shared JDownloader API3128 backend."
        execution_allowed = bool(allow_untested_jdownloader) or (
            capability.capability_found and capability.capability_tested
        ) or bool(direct_media_evidence and direct_media_evidence.tested)
        blocked_reason = ""
        if not execution_allowed:
            if not capability.capability_found:
                blocked_reason = "JDownloader capability manifest does not contain x.com/twitter.com for direct Twitter media URL."
            elif not capability.capability_tested and not bool(direct_media_evidence and direct_media_evidence.tested):
                blocked_reason = "JDownloader x.com/twitter.com capability exists but is not marked tested and no direct Twitter media JD evidence is recorded."
    else:
        execution_allowed = capability.capability_found and (capability.capability_tested or allow_untested_jdownloader)
        blocked_reason = ""
        route_note = "YTCE-owned Twitter/X media request routed to the shared JDownloader API3128 backend."
        if not capability.capability_found:
            blocked_reason = "JDownloader capability manifest does not contain x.com/twitter.com."
        elif not capability.capability_tested and not allow_untested_jdownloader:
            blocked_reason = "JDownloader x.com/twitter.com capability exists but is not marked tested."

    return TwitterMediaBackendPlan(
        schema_version=TWITTER_MEDIA_BACKEND_SCHEMA_VERSION,
        profile_id=TWITTER_MEDIA_BACKEND_PROFILE_ID,
        source_url=source_url,
        canonical_url=canonical_url,
        source_id=source_id,
        output_dir=str(output_dir),
        package_name=resolved_package_name,
        max_height=int(max_height or 0),
        components=tuple(str(component) for component in components),
        allow_untested_jdownloader=bool(allow_untested_jdownloader),
        jdownloader_capability=capability,
        direct_media_capability_evidence=direct_media_evidence,
        execution_allowed=execution_allowed,
        blocked_reason=blocked_reason,
        route_note=route_note,
    )


def build_twitter_shared_media_backend_request(plan: TwitterMediaBackendPlan) -> SharedMediaBackendRequest:
    if not plan.execution_allowed:
        raise ValueError(plan.blocked_reason or "Twitter/X shared media backend execution is not allowed by this plan.")
    direct_media_url = is_twitter_direct_media_url(plan.canonical_url)
    return build_shared_jdownloader_media_request(
        source_adapter_id="twitter_x_direct_media" if direct_media_url else "twitter_x",
        source_url=plan.canonical_url,
        output_dir=plan.output_dir,
        package_name=plan.package_name,
        source_title_or_id=plan.source_id,
        max_height=plan.max_height,
        components=plan.components,
        video="video" in plan.components,
        audio="audio" in plan.components,
        image="image" in plan.components or "thumbnail" in plan.components,
        description=True,
        wait=True,
        timeout_seconds=180,
        monitor_timeout_seconds=120.0,
        overall_timeout_seconds=180.0,
        plan_json_path=str(Path(plan.output_dir).parent / "twitter-jdownloader-command.json"),
    )


def run_twitter_media_download_via_shared_backend(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str = "",
    max_height: int = 1080,
    components: Sequence[str] = TWITTER_MEDIA_BACKEND_DEFAULT_COMPONENTS,
    capability_manifest_path: str | Path = "jd_capabilities_manifest.json",
    allow_untested_jdownloader: bool = True,
    direct_media_capability_evidence_path: str | Path = "",
    shared_backend_runner: TwitterSharedBackendRunner | None = None,
) -> TwitterMediaBackendResult:
    plan = build_twitter_media_backend_plan(
        source_url=source_url,
        output_dir=output_dir,
        package_name=package_name,
        max_height=max_height,
        components=components,
        capability_manifest_path=capability_manifest_path,
        allow_untested_jdownloader=allow_untested_jdownloader,
        direct_media_capability_evidence_path=direct_media_capability_evidence_path,
    )
    if not plan.execution_allowed:
        return TwitterMediaBackendResult(
            status="blocked",
            evidence_completion_claim="not_completed",
            plan=plan,
            warnings=(plan.blocked_reason,),
        )

    request = build_twitter_shared_media_backend_request(plan)
    runner = shared_backend_runner or run_shared_jdownloader_media_backend
    shared_result = runner(request)
    warnings = tuple(shared_result.warnings)
    errors = tuple(shared_result.errors)
    if shared_result.status == "success" and int(shared_result.files_count or 0) > 0:
        claim = "completed"
    elif shared_result.status == "success":
        claim = "completed_no_media_files"
    else:
        claim = "needs_review"

    return TwitterMediaBackendResult(
        status=shared_result.status,
        evidence_completion_claim=claim,
        plan=plan,
        shared_backend_result=shared_result,
        warnings=warnings,
        errors=errors,
    )


def write_twitter_media_backend_plan(path: str | Path, plan: TwitterMediaBackendPlan) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output
