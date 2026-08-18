from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from jdownloader_capabilities import DEFAULT_OUTPUT_PATH
from jdownloader_internal_backend import JDownloaderInternalCapabilities, detect_jdownloader_internal_capabilities
from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID, YTDLP_FALLBACK_BACKEND_ID
from jdownloader_route_summary import JDOWNLOADER_API3128_ROUTE_ID, JDOWNLOADER_ROUTE_PREFERENCE, YTDLP_FALLBACK_ROLE


JD_CAPABILITY_STATUS_RUNTIME_MISSING = "internal_runtime_missing_using_yt_dlp_fallback"
JD_CAPABILITY_STATUS_MANIFEST_MISSING = "jd_capability_manifest_missing_try_api3128_then_fallback"
JD_CAPABILITY_STATUS_MANIFEST_UNREADABLE = "jd_capability_manifest_unreadable_try_api3128_then_fallback"
JD_CAPABILITY_STATUS_TESTED_VIDEO_DOMAIN = "jd_tested_video_domain_api3128_preferred"
JD_CAPABILITY_STATUS_INDEXED_DOMAIN = "jd_indexed_domain_api3128_preferred"
JD_CAPABILITY_STATUS_DOMAIN_NOT_INDEXED = "jd_domain_not_indexed_try_api3128_then_fallback"


@dataclass(frozen=True)
class JDownloaderCapabilityDecision:
    source_url: str
    normalized_domain: str = ""
    manifest_path: str = ""
    manifest_present: bool = False
    manifest_loaded: bool = False
    manifest_dev_only: bool = True
    startup_safe: str = "not_loaded_on_app_startup"
    runtime_present: bool = False
    primary_runtime_path: str = ""
    recommended_backend_id: str = YTDLP_FALLBACK_BACKEND_ID
    fallback_backend_id: str = YTDLP_FALLBACK_BACKEND_ID
    route_preference: str = JDOWNLOADER_ROUTE_PREFERENCE
    api3128_route_id: str = JDOWNLOADER_API3128_ROUTE_ID
    api3128_preferred: bool = False
    yt_dlp_role: str = YTDLP_FALLBACK_ROLE
    capability_status: str = JD_CAPABILITY_STATUS_MANIFEST_MISSING
    decision_label: str = "JDownloader capability manifest missing; try API3128 first when runtime is available, then fallback."
    domain_likely_supported: bool = False
    tested: bool = False
    supports_video: Any = "unknown_until_tested"
    supports_audio: Any = "unknown_until_tested"
    supports_thumbnail: Any = "unknown_until_tested"
    supports_description: Any = "unknown_until_tested"
    supports_subtitles: Any = "unknown_until_tested"
    plugin_types: tuple[str, ...] = ()
    plugin_count: int = 0
    plugin_names: tuple[str, ...] = ()
    matched_manifest_domain: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


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


def normalize_jdownloader_capability_domain(value: str) -> str:
    text = str(value or "").strip().strip('"').strip("'").lower()
    if not text:
        return ""
    if "://" not in text and "/" not in text:
        host = text
    else:
        parsed = urlparse(text if "://" in text else "https://" + text)
        host = parsed.netloc or parsed.path.split("/", 1)[0]
    host = host.split("@")[-1]
    host = host.split(":", 1)[0]
    host = re.sub(r"^www\.", "", host)
    return host.strip(".")


def _load_manifest(path: Path) -> tuple[dict[str, Any], tuple[str, ...]]:
    if not path.is_file():
        return {}, (f"JDownloader capability manifest not found: {path}",)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, (f"JDownloader capability manifest could not be read: {type(exc).__name__}: {exc}",)
    if not isinstance(data, dict):
        return {}, ("JDownloader capability manifest root is not a JSON object.",)
    return data, ()


def _match_domain(capabilities: Mapping[str, Any], normalized_domain: str) -> tuple[str, Mapping[str, Any]]:
    if not normalized_domain:
        return "", {}
    if normalized_domain in capabilities and isinstance(capabilities[normalized_domain], Mapping):
        return normalized_domain, capabilities[normalized_domain]
    for domain in sorted((str(key) for key in capabilities.keys()), key=len, reverse=True):
        if normalized_domain == domain or normalized_domain.endswith("." + domain):
            raw = capabilities.get(domain)
            if isinstance(raw, Mapping):
                return domain, raw
    return "", {}


def _plugin_names(capability: Mapping[str, Any]) -> tuple[str, ...]:
    names: list[str] = []
    plugins = capability.get("plugins")
    if isinstance(plugins, list):
        for item in plugins:
            if isinstance(item, Mapping):
                name = str(item.get("plugin_name") or "").strip()
                if name and name not in names:
                    names.append(name)
    return tuple(names[:12])


def build_jdownloader_capability_decision(
    source_url: str,
    *,
    manifest_path: str | Path = DEFAULT_OUTPUT_PATH,
    capabilities: JDownloaderInternalCapabilities | None = None,
) -> JDownloaderCapabilityDecision:
    """Explain whether YTCE should try JDownloader/API3128 before yt-dlp.

    This is an on-demand capability surface. It reads the generated
    jd_capabilities_manifest.json only when explicitly called; it does not scan
    JDownloader plugins and must not run on app startup.
    """
    caps = capabilities or detect_jdownloader_internal_capabilities()
    normalized_domain = normalize_jdownloader_capability_domain(source_url)
    path = Path(manifest_path)
    manifest, manifest_warnings = _load_manifest(path)
    warnings = [*caps.warnings, *manifest_warnings]
    runtime_present = bool(caps.runtime_present)
    if not runtime_present:
        return JDownloaderCapabilityDecision(
            source_url=str(source_url or ""),
            normalized_domain=normalized_domain,
            manifest_path=str(path),
            manifest_present=path.is_file(),
            manifest_loaded=bool(manifest),
            manifest_dev_only=bool(manifest.get("dev_only", True)) if manifest else True,
            startup_safe=str(manifest.get("startup_safe") or "not_loaded_on_app_startup") if manifest else "not_loaded_on_app_startup",
            runtime_present=False,
            primary_runtime_path=str(caps.primary_runtime_path or ""),
            recommended_backend_id=YTDLP_FALLBACK_BACKEND_ID,
            api3128_preferred=False,
            capability_status=JD_CAPABILITY_STATUS_RUNTIME_MISSING,
            decision_label="Project-local JDownloader runtime is missing; use yt-dlp fallback until the runtime is available.",
            warnings=tuple(warnings),
        )

    manifest_present = path.is_file()
    manifest_loaded = bool(manifest)
    if not manifest_present:
        return JDownloaderCapabilityDecision(
            source_url=str(source_url or ""),
            normalized_domain=normalized_domain,
            manifest_path=str(path),
            manifest_present=False,
            manifest_loaded=False,
            runtime_present=True,
            primary_runtime_path=str(caps.primary_runtime_path or ""),
            recommended_backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
            api3128_preferred=True,
            capability_status=JD_CAPABILITY_STATUS_MANIFEST_MISSING,
            decision_label="Capability manifest is missing; try JDownloader API3128 first, then yt-dlp fallback if JD cannot crawl it.",
            warnings=tuple(warnings),
        )
    if not manifest_loaded:
        return JDownloaderCapabilityDecision(
            source_url=str(source_url or ""),
            normalized_domain=normalized_domain,
            manifest_path=str(path),
            manifest_present=True,
            manifest_loaded=False,
            runtime_present=True,
            primary_runtime_path=str(caps.primary_runtime_path or ""),
            recommended_backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
            api3128_preferred=True,
            capability_status=JD_CAPABILITY_STATUS_MANIFEST_UNREADABLE,
            decision_label="Capability manifest is unreadable; try JDownloader API3128 first, then yt-dlp fallback if JD cannot crawl it.",
            warnings=tuple(warnings),
        )

    manifest_capabilities = manifest.get("capabilities")
    if not isinstance(manifest_capabilities, Mapping):
        manifest_capabilities = {}
    matched_domain, capability = _match_domain(manifest_capabilities, normalized_domain)
    if not capability:
        return JDownloaderCapabilityDecision(
            source_url=str(source_url or ""),
            normalized_domain=normalized_domain,
            manifest_path=str(path),
            manifest_present=True,
            manifest_loaded=True,
            manifest_dev_only=bool(manifest.get("dev_only", True)),
            startup_safe=str(manifest.get("startup_safe") or "not_loaded_on_app_startup"),
            runtime_present=True,
            primary_runtime_path=str(caps.primary_runtime_path or ""),
            recommended_backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
            api3128_preferred=True,
            capability_status=JD_CAPABILITY_STATUS_DOMAIN_NOT_INDEXED,
            decision_label="Domain is not indexed in the JD capability manifest; still try JDownloader API3128 before yt-dlp because JD may resolve it through a generic crawler or updated plugin.",
            domain_likely_supported=False,
            warnings=tuple(warnings),
        )

    plugin_types = tuple(str(item) for item in capability.get("plugin_types", ()) if str(item).strip())
    plugin_names = _plugin_names(capability)
    tested = bool(capability.get("tested", False))
    supports_video = capability.get("supports_video", "unknown_until_tested")
    if tested and supports_video is True:
        status = JD_CAPABILITY_STATUS_TESTED_VIDEO_DOMAIN
        label = "Domain is YTCE-tested for JDownloader video handling; use API3128 as the preferred route."
    else:
        status = JD_CAPABILITY_STATUS_INDEXED_DOMAIN
        label = "Domain is indexed in the JD capability manifest; try API3128 first, then yt-dlp fallback if the crawler fails."
    return JDownloaderCapabilityDecision(
        source_url=str(source_url or ""),
        normalized_domain=normalized_domain,
        manifest_path=str(path),
        manifest_present=True,
        manifest_loaded=True,
        manifest_dev_only=bool(manifest.get("dev_only", True)),
        startup_safe=str(manifest.get("startup_safe") or "not_loaded_on_app_startup"),
        runtime_present=True,
        primary_runtime_path=str(caps.primary_runtime_path or ""),
        recommended_backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
        api3128_preferred=True,
        capability_status=status,
        decision_label=label,
        domain_likely_supported=True,
        tested=tested,
        supports_video=supports_video,
        supports_audio=capability.get("supports_audio", "unknown_until_tested"),
        supports_thumbnail=capability.get("supports_thumbnail", "unknown_until_tested"),
        supports_description=capability.get("supports_description", "unknown_until_tested"),
        supports_subtitles=capability.get("supports_subtitles", "unknown_until_tested"),
        plugin_types=plugin_types,
        plugin_count=len(capability.get("plugins", ()) or ()),
        plugin_names=plugin_names,
        matched_manifest_domain=matched_domain,
        warnings=tuple(warnings),
    )
