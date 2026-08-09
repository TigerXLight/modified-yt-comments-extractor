from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import subprocess
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION = "source_local_web_archive_actions_v1"

VIEWER_NOT_CONFIGURED = "VIEWER_NOT_CONFIGURED"
VIEWER_CONFIGURED = "VIEWER_CONFIGURED"
USER_LOCAL_INSTALL_NOT_AVAILABLE = "USER_LOCAL_INSTALL_NOT_AVAILABLE"
STRUCTURAL_WACZ_VALID = "STRUCTURAL_WACZ_VALID"
REPLAY_OPENED = "REPLAY_OPENED"
REPLAY_PARTIAL = "REPLAY_PARTIAL"
REPLAY_VISUALLY_VERIFIED = "REPLAY_VISUALLY_VERIFIED"
USER_VISUAL_CONFIRMATION_REQUIRED = "USER_VISUAL_CONFIRMATION_REQUIRED"
REPLAY_FAILED = "REPLAY_FAILED"

SHOW_FILES_READY = "SHOW_FILES_READY"
SHOW_FILES_PREVIEWED = "SHOW_FILES_PREVIEWED"
OPEN_ARCHIVE_PREVIEWED = "OPEN_ARCHIVE_PREVIEWED"

LOCAL_WEB_ARCHIVE_SCOPE = (
    "Local Web Archive ReplayWeb.page action state; verifies caller-selected local WACZ "
    "and manifest artifacts, builds safe argument-array launch previews, and performs no "
    "live site access, archive submission, credential use, browser-profile access, or "
    "external viewer launch unless a caller explicitly supplies an execution launcher"
)

REPLAYWEB_RELEASES_LATEST_API_URL = (
    "https://api.github.com/repos/webrecorder/replayweb.page/releases/latest"
)
REPLAYWEB_OFFICIAL_RELEASES_URL = "https://github.com/webrecorder/replayweb.page/releases/latest"
REPLAYWEB_OFFICIAL_WEB_APP_URL = "https://replayweb.page/"

REQUIRED_WACZ_ENTRIES = frozenset(
    {
        "datapackage.json",
        "pages/pages.jsonl",
        "indexes/index.cdx.gz",
    }
)


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path_name(path: str | Path) -> str:
    return Path(path).name


def _load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ReplayWebReleaseAsset:
    name: str
    browser_download_url: str
    size_bytes: int
    content_type: str = ""
    official_source: str = REPLAYWEB_OFFICIAL_RELEASES_URL

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ReplayWebReleaseMetadata:
    status: str
    tag_name: str = ""
    release_name: str = ""
    html_url: str = ""
    windows_assets: tuple[ReplayWebReleaseAsset, ...] = ()
    official_api_url: str = REPLAYWEB_RELEASES_LATEST_API_URL
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["windows_asset_count"] = len(self.windows_assets)
        return data


@dataclass(frozen=True)
class ReplayWebViewerDetection:
    status: str
    executable_path: str = ""
    executable_name: str = ""
    executable_sha256: str = ""
    version_hint: str = ""
    detection_source: str = ""
    searched_names: tuple[str, ...] = ()
    configuration_help: str = (
        "Set REPLAYWEBPAGE_PATH to the ReplayWeb.page desktop executable, or install the "
        "official user-local ReplayWeb.page desktop app."
    )
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebArchiveVerificationResult:
    status: str
    wacz_name: str
    wacz_sha256: str = ""
    wacz_size_bytes: int = 0
    manifest_name: str = ""
    manifest_sha256: str = ""
    zip_integrity_ok: bool = False
    required_entries_present: bool = False
    missing_required_entries: tuple[str, ...] = ()
    datapackage_profile: str = ""
    wacz_version: str = ""
    page_count: int = 0
    index_line_count: int = 0
    warc_record_count: int = 0
    expected_source_url_found: bool = False
    replayweb_acceptance_basis: str = "structural verification only"
    comments_json_count: int = 0
    comments_jsonl_count: int = 0
    declared_comment_count: int = 0
    top_level_comment_count: int = 0
    reply_count: int = 0
    comments_complete: bool = False
    comments_evidence_status: str = "not_checked"
    faithful_comments_screenshot_name: str = ""
    faithful_comments_screenshot_sha256: str = ""
    derived_comments_visual_name: str = ""
    derived_comments_visual_sha256: str = ""
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION
    scope: str = LOCAL_WEB_ARCHIVE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebArchiveCommandPreview:
    status: str
    argv: tuple[str, ...] = ()
    shell: bool = False
    executed: bool = False
    message: str = ""
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["argv_name_only"] = tuple(_safe_path_name(item) if index == 0 else item for index, item in enumerate(self.argv))
        return data


@dataclass(frozen=True)
class LocalWebArchiveActionState:
    archive_name: str
    capture_locally_status: str
    open_archive_status: str
    show_files_status: str
    verify_status: str
    replay_visual_status: str
    viewer: ReplayWebViewerDetection
    verification: LocalWebArchiveVerificationResult
    open_preview: LocalWebArchiveCommandPreview
    show_files_preview: LocalWebArchiveCommandPreview
    browser_pwa_status: str
    browser_pwa_note: str
    no_live_site_access_performed: bool = True
    no_archive_submit_performed: bool = True
    no_credentials_or_cookies_used: bool = True
    no_second_source_tested: bool = True
    schema_version: str = REPLAYWEB_LOCAL_ARCHIVE_SCHEMA_VERSION
    scope: str = LOCAL_WEB_ARCHIVE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def parse_replayweb_release_metadata(payload: Mapping[str, Any]) -> ReplayWebReleaseMetadata:
    assets: list[ReplayWebReleaseAsset] = []
    for asset in payload.get("assets") or ():
        if not isinstance(asset, Mapping):
            continue
        name = str(asset.get("name") or "")
        lowered = name.lower()
        if not (lowered.endswith(".exe") or lowered.endswith(".zip")):
            continue
        if "replayweb.page" not in lowered:
            continue
        assets.append(
            ReplayWebReleaseAsset(
                name=name,
                browser_download_url=str(asset.get("browser_download_url") or ""),
                size_bytes=int(asset.get("size") or 0),
                content_type=str(asset.get("content_type") or ""),
                official_source=str(payload.get("html_url") or REPLAYWEB_OFFICIAL_RELEASES_URL),
            )
        )
    return ReplayWebReleaseMetadata(
        status="OFFICIAL_RELEASE_METADATA_PARSED",
        tag_name=str(payload.get("tag_name") or ""),
        release_name=str(payload.get("name") or ""),
        html_url=str(payload.get("html_url") or ""),
        windows_assets=tuple(sorted(assets, key=lambda item: item.name)),
    )


def default_replaywebpage_candidate_paths(env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    values = dict(os.environ if env is None else env)
    local_app_data = values.get("LOCALAPPDATA", "")
    user_profile = values.get("USERPROFILE", "")
    candidates: list[Path] = []
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "Programs" / "ReplayWeb.page" / "ReplayWeb.page.exe",
                Path(local_app_data) / "ReplayWeb.page" / "ReplayWeb.page.exe",
            ]
        )
    if user_profile:
        candidates.extend(
            [
                Path(user_profile) / "AppData" / "Local" / "Programs" / "ReplayWeb.page" / "ReplayWeb.page.exe",
                Path(user_profile) / "Downloads" / "ReplayWeb.page.exe",
            ]
        )
    candidates.append(Path(__file__).resolve().parent / ".local_tools" / "ReplayWeb.page" / "ReplayWeb.page.exe")
    return tuple(candidates)


def _version_hint_from_name(path: Path) -> str:
    match = re.search(r"ReplayWeb\.page[-_ ]?([0-9]+(?:\.[0-9]+){1,3}(?:[-A-Za-z0-9.]*?)?)(?:\.(?:exe|zip|dmg|appimage))?$", path.name, re.IGNORECASE)
    return match.group(1) if match else ""


def detect_replaywebpage_viewer(
    *,
    env: Mapping[str, str] | None = None,
    candidate_paths: Sequence[str | Path] | None = None,
) -> ReplayWebViewerDetection:
    values = dict(os.environ if env is None else env)
    candidates: list[tuple[str, Path]] = []
    env_path = str(values.get("REPLAYWEBPAGE_PATH") or "").strip()
    if env_path:
        candidates.append(("REPLAYWEBPAGE_PATH", Path(env_path)))
    for path in candidate_paths or default_replaywebpage_candidate_paths(values):
        candidates.append(("auto_detect", Path(path)))

    seen: set[str] = set()
    searched: list[str] = []
    for source, path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        searched.append(path.name or key)
        if path.is_file():
            return ReplayWebViewerDetection(
                status=VIEWER_CONFIGURED,
                executable_path=str(path),
                executable_name=path.name,
                executable_sha256=_sha256_file(path),
                version_hint=_version_hint_from_name(path),
                detection_source=source,
                searched_names=tuple(searched),
            )
    return ReplayWebViewerDetection(
        status=VIEWER_NOT_CONFIGURED,
        searched_names=tuple(searched),
    )


def _safe_json_loads(payload: bytes | str) -> Any:
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    return json.loads(text)


def _parse_pages_jsonl(payload: bytes) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line in payload.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, Mapping) and item.get("url"):
            rows.append(item)
    return rows


def _warc_record_count_from_zip(bundle: zipfile.ZipFile, names: Sequence[str]) -> tuple[int, list[str]]:
    errors: list[str] = []
    count = 0
    try:
        from warcio.archiveiterator import ArchiveIterator
    except Exception as error:
        return 0, [f"warcio unavailable: {error}"]
    for name in names:
        try:
            with bundle.open(name, "r") as stream:
                count += sum(1 for _record in ArchiveIterator(stream))
        except Exception as error:
            errors.append(f"{name}: {error}")
    return count, errors


def _artifact_by_label(artifacts: Sequence[Mapping[str, Any]], contains: str) -> Mapping[str, Any] | None:
    needle = contains.lower()
    for artifact in artifacts:
        if needle in str(artifact.get("label") or "").lower():
            return artifact
    return None


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def _comments_json_count(path: Path) -> int:
    if not path.is_file():
        return 0
    payload = _load_json_file(path)
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, Mapping):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return len(rows)
        return int(payload.get("row_count") or 0)
    return 0


def _manifest_comments_summary(
    manifest: Mapping[str, Any],
    *,
    expected_comment_count: int = 0,
) -> dict[str, Any]:
    artifacts = [item for item in manifest.get("artifacts") or () if isinstance(item, Mapping)]
    comments_json = _artifact_by_label(artifacts, "android_mobile_chromium_comments_json") or _artifact_by_label(artifacts, "comments_json")
    comments_jsonl = _artifact_by_label(artifacts, "android_mobile_chromium_comments_incremental_jsonl") or _artifact_by_label(artifacts, "comments_incremental_jsonl")
    reconciliation = _artifact_by_label(artifacts, "android_mobile_chromium_comments_provider_reconciliation") or _artifact_by_label(artifacts, "comments_provider_reconciliation")
    faithful = _artifact_by_label(artifacts, "android_mobile_chromium_faithful_comments_screenshot") or _artifact_by_label(artifacts, "faithful_comments_screenshot")
    derived = _artifact_by_label(artifacts, "android_mobile_chromium_derived_comments_full_thread_screenshot") or _artifact_by_label(artifacts, "derived_comments_full_thread_screenshot")

    comments_count = _comments_json_count(Path(str(comments_json.get("path") or ""))) if comments_json else 0
    jsonl_count = _count_jsonl_lines(Path(str(comments_jsonl.get("path") or ""))) if comments_jsonl else 0
    declared = 0
    top_level = 0
    replies = 0
    complete = False
    if reconciliation:
        path = Path(str(reconciliation.get("path") or ""))
        if path.is_file():
            data = _load_json_file(path)
            if isinstance(data, Mapping):
                api = data.get("api_reconciliation")
                provider = data.get("provider_reconciliation")
                if isinstance(api, Mapping):
                    declared = int(api.get("declared_total_count") or api.get("total_count") or 0)
                    top_level = int(api.get("root_record_count") or top_level or 0)
                    replies = int(api.get("reply_record_count") or replies or 0)
                if isinstance(provider, Mapping):
                    complete = bool(provider.get("comments_complete"))
                    declared = declared or int(provider.get("declared_total_count") or 0)
                    top_level = int(
                        provider.get("provider_root_count")
                        or provider.get("root_record_count")
                        or provider.get("root_count")
                        or top_level
                        or 0
                    )
                    replies = int(
                        provider.get("provider_reply_count")
                        or provider.get("reply_record_count")
                        or provider.get("reply_count")
                        or replies
                        or 0
                    )
                top_level = top_level or int(data.get("provider_root_count") or 0)
                replies = replies or int(data.get("provider_reply_count") or 0)
    expected = expected_comment_count or declared
    evidence_ok = comments_count > 0 and (not expected or comments_count == expected)
    if declared:
        evidence_ok = evidence_ok and comments_count == declared
    return {
        "comments_json_count": comments_count,
        "comments_jsonl_count": jsonl_count,
        "declared_comment_count": declared,
        "top_level_comment_count": top_level,
        "reply_count": replies,
        "comments_complete": bool(complete or (expected and comments_count == expected and declared == expected)),
        "comments_evidence_status": "COMMENTS_EVIDENCE_VERIFIED" if evidence_ok else "COMMENTS_EVIDENCE_PARTIAL",
        "faithful_comments_screenshot_name": Path(str(faithful.get("path") or "")).name if faithful else "",
        "faithful_comments_screenshot_sha256": str(faithful.get("sha256") or "") if faithful else "",
        "derived_comments_visual_name": Path(str(derived.get("path") or "")).name if derived else "",
        "derived_comments_visual_sha256": str(derived.get("sha256") or "") if derived else "",
    }


def verify_local_web_archive_package(
    wacz_path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    expected_source_url: str = "",
    expected_wacz_sha256: str = "",
    expected_manifest_sha256: str = "",
    expected_comment_count: int = 0,
) -> LocalWebArchiveVerificationResult:
    package = Path(wacz_path)
    errors: list[str] = []
    warnings: list[str] = []
    manifest_name = Path(manifest_path).name if manifest_path else ""
    manifest_sha256 = ""
    comments_summary: dict[str, Any] = {}
    if not package.is_file():
        return LocalWebArchiveVerificationResult(
            status=REPLAY_FAILED,
            wacz_name=package.name,
            manifest_name=manifest_name,
            errors=(f"WACZ file does not exist: {package}",),
        )

    wacz_sha = _sha256_file(package)
    if expected_wacz_sha256 and wacz_sha.lower() != expected_wacz_sha256.lower():
        errors.append("WACZ SHA-256 does not match expected value")
    if manifest_path:
        manifest_file = Path(manifest_path)
        if manifest_file.is_file():
            manifest_sha256 = _sha256_file(manifest_file)
            if expected_manifest_sha256 and manifest_sha256.lower() != expected_manifest_sha256.lower():
                errors.append("Manifest SHA-256 does not match expected value")
            try:
                manifest_payload = _load_json_file(manifest_file)
                if isinstance(manifest_payload, Mapping):
                    comments_summary = _manifest_comments_summary(
                        manifest_payload,
                        expected_comment_count=expected_comment_count,
                    )
            except Exception as error:
                errors.append(f"Manifest parse failed: {error}")
        else:
            errors.append(f"Manifest file does not exist: {manifest_file}")

    names: set[str] = set()
    datapackage: Mapping[str, Any] = {}
    pages: list[Mapping[str, Any]] = []
    index_lines: list[str] = []
    warc_record_count = 0
    try:
        with zipfile.ZipFile(package, "r") as bundle:
            bad_member = bundle.testzip()
            if bad_member:
                errors.append(f"ZIP integrity failed at {bad_member}")
            names = set(bundle.namelist())
            if "datapackage.json" in names:
                datapackage_raw = _safe_json_loads(bundle.read("datapackage.json"))
                if isinstance(datapackage_raw, Mapping):
                    datapackage = datapackage_raw
            if "pages/pages.jsonl" in names:
                pages = _parse_pages_jsonl(bundle.read("pages/pages.jsonl"))
            if "indexes/index.cdx.gz" in names:
                index_lines = [
                    line
                    for line in gzip.decompress(bundle.read("indexes/index.cdx.gz"))
                    .decode("utf-8", errors="replace")
                    .splitlines()
                    if line.strip()
                ]
            warc_names = sorted(name for name in names if name.startswith("archive/") and name.endswith(".warc"))
            warc_record_count, warc_errors = _warc_record_count_from_zip(bundle, warc_names)
            warnings.extend(warc_errors)
    except Exception as error:
        errors.append(f"WACZ ZIP/read failed: {error}")

    missing = tuple(sorted(REQUIRED_WACZ_ENTRIES - names))
    if not any(name.startswith("archive/") and name.endswith(".warc") for name in names):
        missing = tuple(sorted(set(missing) | {"archive/*.warc"}))
    if missing:
        errors.append("Required WACZ entries are missing")

    source_candidates = {
        str(datapackage.get("mainPageUrl") or ""),
        str(((datapackage.get("home") or {}) if isinstance(datapackage.get("home"), Mapping) else {}).get("url") or ""),
    }
    source_candidates.update(str(page.get("url") or "") for page in pages)
    source_candidates.update(index_lines)
    expected_found = True
    if expected_source_url:
        expected_found = any(expected_source_url in candidate for candidate in source_candidates)
        if not expected_found:
            errors.append("Expected source URL was not found in WACZ metadata/index")

    status = STRUCTURAL_WACZ_VALID if not errors else REPLAY_FAILED
    return LocalWebArchiveVerificationResult(
        status=status,
        wacz_name=package.name,
        wacz_sha256=wacz_sha,
        wacz_size_bytes=package.stat().st_size,
        manifest_name=manifest_name,
        manifest_sha256=manifest_sha256,
        zip_integrity_ok=not any("ZIP integrity" in error for error in errors),
        required_entries_present=not missing,
        missing_required_entries=missing,
        datapackage_profile=str(datapackage.get("profile") or ""),
        wacz_version=str(datapackage.get("wacz_version") or ""),
        page_count=len(pages),
        index_line_count=len(index_lines),
        warc_record_count=warc_record_count,
        expected_source_url_found=expected_found,
        comments_json_count=int(comments_summary.get("comments_json_count") or 0),
        comments_jsonl_count=int(comments_summary.get("comments_jsonl_count") or 0),
        declared_comment_count=int(comments_summary.get("declared_comment_count") or 0),
        top_level_comment_count=int(comments_summary.get("top_level_comment_count") or 0),
        reply_count=int(comments_summary.get("reply_count") or 0),
        comments_complete=bool(comments_summary.get("comments_complete")),
        comments_evidence_status=str(comments_summary.get("comments_evidence_status") or "not_checked"),
        faithful_comments_screenshot_name=str(comments_summary.get("faithful_comments_screenshot_name") or ""),
        faithful_comments_screenshot_sha256=str(comments_summary.get("faithful_comments_screenshot_sha256") or ""),
        derived_comments_visual_name=str(comments_summary.get("derived_comments_visual_name") or ""),
        derived_comments_visual_sha256=str(comments_summary.get("derived_comments_visual_sha256") or ""),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_replaywebpage_open_preview(
    wacz_path: str | Path,
    *,
    viewer: ReplayWebViewerDetection | None = None,
) -> LocalWebArchiveCommandPreview:
    detection = viewer or detect_replaywebpage_viewer()
    if detection.status != VIEWER_CONFIGURED or not detection.executable_path:
        return LocalWebArchiveCommandPreview(
            status=VIEWER_NOT_CONFIGURED,
            message=detection.configuration_help,
        )
    return LocalWebArchiveCommandPreview(
        status=OPEN_ARCHIVE_PREVIEWED,
        argv=(detection.executable_path, str(Path(wacz_path))),
        shell=False,
        message="ReplayWeb.page desktop launch preview uses subprocess argument array.",
    )


def open_archive_with_replaywebpage(
    wacz_path: str | Path,
    *,
    viewer: ReplayWebViewerDetection | None = None,
    launcher: Callable[[Sequence[str]], Any] | None = None,
) -> LocalWebArchiveCommandPreview:
    preview = build_replaywebpage_open_preview(wacz_path, viewer=viewer)
    if preview.status != OPEN_ARCHIVE_PREVIEWED:
        return preview
    if launcher is None:
        launcher = lambda argv: subprocess.Popen(list(argv), shell=False)  # noqa: S603
    launcher(preview.argv)
    return LocalWebArchiveCommandPreview(
        status=REPLAY_OPENED,
        argv=preview.argv,
        shell=False,
        executed=True,
        message="ReplayWeb.page desktop viewer launch requested.",
    )


def build_show_local_web_archive_files_preview(wacz_path: str | Path) -> LocalWebArchiveCommandPreview:
    package = Path(wacz_path)
    if os.name == "nt":
        argv = ("explorer.exe", f"/select,{package}")
    else:
        argv = ("xdg-open", str(package.parent))
    return LocalWebArchiveCommandPreview(
        status=SHOW_FILES_READY if package.exists() else REPLAY_FAILED,
        argv=argv,
        shell=False,
        message="Show files command preview selects the WACZ or opens its containing directory.",
    )


def show_local_web_archive_files(
    wacz_path: str | Path,
    *,
    launcher: Callable[[Sequence[str]], Any] | None = None,
) -> LocalWebArchiveCommandPreview:
    preview = build_show_local_web_archive_files_preview(wacz_path)
    if preview.status != SHOW_FILES_READY:
        return preview
    if launcher is None:
        launcher = lambda argv: subprocess.Popen(list(argv), shell=False)  # noqa: S603
    launcher(preview.argv)
    return LocalWebArchiveCommandPreview(
        status=SHOW_FILES_PREVIEWED,
        argv=preview.argv,
        shell=False,
        executed=True,
        message="Local Web Archive file-manager launch requested.",
    )


def build_replayweb_browser_pwa_file_state(wacz_path: str | Path) -> dict[str, Any]:
    return {
        "status": USER_VISUAL_CONFIRMATION_REQUIRED,
        "mode": "browser_pwa",
        "url": REPLAYWEB_OFFICIAL_WEB_APP_URL,
        "wacz_name": Path(wacz_path).name,
        "direct_file_url_supported": False,
        "note": (
            "The official browser/PWA viewer requires the supported file chooser for local "
            "WACZ files; direct file:// source URLs are rejected by ReplayWeb.page."
        ),
    }


def build_local_web_archive_action_state(
    *,
    wacz_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
    expected_source_url: str = "",
    expected_wacz_sha256: str = "",
    expected_manifest_sha256: str = "",
    expected_comment_count: int = 0,
    viewer: ReplayWebViewerDetection | None = None,
) -> LocalWebArchiveActionState:
    archive = Path(wacz_path) if wacz_path else Path("")
    detection = viewer or detect_replaywebpage_viewer()
    verification = (
        verify_local_web_archive_package(
            archive,
            manifest_path=manifest_path,
            expected_source_url=expected_source_url,
            expected_wacz_sha256=expected_wacz_sha256,
            expected_manifest_sha256=expected_manifest_sha256,
            expected_comment_count=expected_comment_count,
        )
        if wacz_path
        else LocalWebArchiveVerificationResult(
            status=REPLAY_PARTIAL,
            wacz_name="",
            manifest_name=Path(manifest_path).name if manifest_path else "",
            warnings=("No WACZ selected for verification.",),
        )
    )
    open_preview = build_replaywebpage_open_preview(archive, viewer=detection)
    show_preview = build_show_local_web_archive_files_preview(archive) if wacz_path else LocalWebArchiveCommandPreview(
        status=REPLAY_PARTIAL,
        message="No WACZ selected for file-manager preview.",
    )
    pwa = build_replayweb_browser_pwa_file_state(archive)
    return LocalWebArchiveActionState(
        archive_name=archive.name,
        capture_locally_status="existing_archive_selected" if wacz_path and archive.exists() else "capture_locally_available",
        open_archive_status=open_preview.status,
        show_files_status=show_preview.status,
        verify_status=verification.status,
        replay_visual_status=USER_VISUAL_CONFIRMATION_REQUIRED,
        viewer=detection,
        verification=verification,
        open_preview=open_preview,
        show_files_preview=show_preview,
        browser_pwa_status=str(pwa["status"]),
        browser_pwa_note=str(pwa["note"]),
    )


def local_web_archive_status_lines(state: LocalWebArchiveActionState) -> tuple[str, ...]:
    viewer_line = (
        f"ReplayWeb.page viewer: configured ({state.viewer.executable_name})"
        if state.viewer.status == VIEWER_CONFIGURED
        else "ReplayWeb.page viewer: VIEWER_NOT_CONFIGURED"
    )
    archive_line = f"Selected archive: {state.archive_name or 'none'}"
    verify_line = f"Verify: {state.verify_status}"
    comments_line = "Comments evidence: not checked"
    if state.verification.comments_json_count or state.verification.declared_comment_count:
        comments_line = (
            "Comments evidence: "
            f"{state.verification.comments_json_count}/{state.verification.declared_comment_count or state.verification.comments_json_count} "
            f"({state.verification.comments_evidence_status})"
        )
    return (
        "Local Web Archive",
        "Default backend: built-in WARC/WACZ + local evidence bundle",
        archive_line,
        viewer_line,
        f"Open archive: {state.open_archive_status}",
        f"Show files: {state.show_files_status}",
        verify_line,
        comments_line,
        f"Replay visual status: {state.replay_visual_status}",
        "Browser/PWA note: local WACZ files require the official file chooser",
        "ArchiveBox backend: optional advanced backend",
        "Network actions performed by status preview: none",
    )
