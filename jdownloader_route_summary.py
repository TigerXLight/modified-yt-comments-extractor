from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping

from jdownloader_internal_paths import JDOWNLOADER_INTERNAL_BACKEND_ID, YTDLP_FALLBACK_BACKEND_ID


JDOWNLOADER_API3128_ROUTE_ID = "api3128"
JDOWNLOADER_FLASHGOT_ROUTE_ID = "flashgot"
JDOWNLOADER_API3128_ROUTE_LABEL = "JDownloader API3128 local Deprecated API fast route"
JDOWNLOADER_FLASHGOT_ROUTE_LABEL = "JDownloader FlashGot/CNL fallback route"
JDOWNLOADER_UNKNOWN_ROUTE_LABEL = "JDownloader route not yet resolved"
JDOWNLOADER_ROUTE_PREFERENCE = "jdownloader_internal_api3128_preferred_before_yt_dlp"
YTDLP_FALLBACK_ROLE = "fallback_only_after_jdownloader_routes"


@dataclass(frozen=True)
class JDownloaderRouteSummary:
    route_used: str = ""
    route_label: str = JDOWNLOADER_UNKNOWN_ROUTE_LABEL
    route_preference: str = JDOWNLOADER_ROUTE_PREFERENCE
    backend_id: str = JDOWNLOADER_INTERNAL_BACKEND_ID
    api3128_enabled: bool = False
    api3128_used: bool = False
    flashgot_fallback_used: bool = False
    yt_dlp_used: bool = False
    yt_dlp_role: str = YTDLP_FALLBACK_ROLE
    api3128_package_complete_ms: int = 0
    api3128_first_running_ms: int = 0
    api3128_finished_ms: int = 0
    evidence_note: str = ""

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


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _route_dict(route_metadata: Mapping[str, Any] | None = None, *, manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if route_metadata is not None:
        return dict(route_metadata)
    data = dict(manifest or {})
    raw = data.get("route_metadata")
    if isinstance(raw, Mapping):
        route = dict(raw)
    else:
        route = {}
    for key in (
        "route_used",
        "api3128_enabled",
        "api3128_used",
        "flashgot_fallback_used",
        "api3128_package_complete_ms",
        "api3128_first_running_ms",
        "api3128_finished_ms",
        "route_label",
        "route_preference",
        "yt_dlp_used",
        "yt_dlp_role",
    ):
        if key in data and key not in route:
            route[key] = data[key]
    return route


def summarize_jdownloader_route_metadata(
    route_metadata: Mapping[str, Any] | None = None,
    *,
    manifest: Mapping[str, Any] | None = None,
) -> JDownloaderRouteSummary:
    """Return a stable, user-facing summary of the JDownloader execution route.

    V78A keeps the proven JDownloader API3128 route as the preferred video
    path.  yt-dlp remains a fallback/reference route and must not be implied
    when a JDownloader manifest reports API3128 or FlashGot/CNL metadata.
    """
    route = _route_dict(route_metadata, manifest=manifest)
    raw_route = str(route.get("route_used") or "").strip().lower()
    api3128_used = bool(route.get("api3128_used")) or raw_route == JDOWNLOADER_API3128_ROUTE_ID
    flashgot_used = bool(route.get("flashgot_fallback_used")) or raw_route in {JDOWNLOADER_FLASHGOT_ROUTE_ID, "/flashgot"}
    api3128_enabled = bool(route.get("api3128_enabled", True if api3128_used or flashgot_used else False))
    if api3128_used:
        route_used = JDOWNLOADER_API3128_ROUTE_ID
        route_label = JDOWNLOADER_API3128_ROUTE_LABEL
        evidence_note = "Submitted through JDownloader local API3128 after LinkGrabber stabilization."
    elif flashgot_used:
        route_used = JDOWNLOADER_FLASHGOT_ROUTE_ID
        route_label = JDOWNLOADER_FLASHGOT_ROUTE_LABEL
        evidence_note = "API3128 was unavailable or did not complete; JDownloader FlashGot/CNL fallback was used."
    else:
        route_used = raw_route
        route_label = str(route.get("route_label") or JDOWNLOADER_UNKNOWN_ROUTE_LABEL)
        evidence_note = "JDownloader route metadata was missing or incomplete."
    return JDownloaderRouteSummary(
        route_used=route_used,
        route_label=route_label,
        route_preference=str(route.get("route_preference") or JDOWNLOADER_ROUTE_PREFERENCE),
        backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
        api3128_enabled=api3128_enabled,
        api3128_used=api3128_used,
        flashgot_fallback_used=flashgot_used,
        yt_dlp_used=bool(route.get("yt_dlp_used", False)),
        yt_dlp_role=str(route.get("yt_dlp_role") or YTDLP_FALLBACK_ROLE),
        api3128_package_complete_ms=_int_value(route.get("api3128_package_complete_ms")),
        api3128_first_running_ms=_int_value(route.get("api3128_first_running_ms")),
        api3128_finished_ms=_int_value(route.get("api3128_finished_ms")),
        evidence_note=str(route.get("evidence_note") or evidence_note),
    )


def normalize_jdownloader_route_metadata(route_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    route = dict(route_metadata or {})
    summary = summarize_jdownloader_route_metadata(route)
    route.setdefault("api3128_enabled", summary.api3128_enabled)
    route["api3128_used"] = summary.api3128_used
    route["flashgot_fallback_used"] = summary.flashgot_fallback_used
    route["route_used"] = summary.route_used
    route["route_label"] = summary.route_label
    route["route_preference"] = summary.route_preference
    route["preferred_backend_id"] = JDOWNLOADER_INTERNAL_BACKEND_ID
    route["fallback_backend_id"] = YTDLP_FALLBACK_BACKEND_ID
    route["yt_dlp_used"] = summary.yt_dlp_used
    route["yt_dlp_role"] = summary.yt_dlp_role
    route["evidence_note"] = summary.evidence_note
    return route
