from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Sequence


ACCESS_KEYS_METADATA_SCOPE = (
    "local non-secret Access & Keys metadata/status model only; no credential "
    "storage, key testing, provider/API calls, browser integration, archive "
    "execution, source fetching, scraping, media download, GUI, or runtime wiring"
)

REPORT_FORMATS = ("markdown", "text", "json")


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AccessMode(_StringEnum):
    NO_CREDENTIALS_REQUIRED = "NO_CREDENTIALS_REQUIRED"
    API_KEY = "API_KEY"
    OAUTH_OR_BROWSER_LOGIN = "OAUTH_OR_BROWSER_LOGIN"
    APP_PASSWORD = "APP_PASSWORD"
    USER_AUTHENTICATED_BROWSER_PROFILE = "USER_AUTHENTICATED_BROWSER_PROFILE"
    DEDICATED_CAPTURE_BROWSER_PROFILE = "DEDICATED_CAPTURE_BROWSER_PROFILE"
    MANUAL_IMPORT_ONLY = "MANUAL_IMPORT_ONLY"
    LOCAL_ONLY = "LOCAL_ONLY"
    BLOCKED_OR_NOT_CONFIGURED = "BLOCKED_OR_NOT_CONFIGURED"


class CredentialStatus(_StringEnum):
    NOT_NEEDED = "NOT_NEEDED"
    OPTIONAL = "OPTIONAL"
    REQUIRED_MISSING = "REQUIRED_MISSING"
    CONFIGURED_UNTESTED = "CONFIGURED_UNTESTED"
    CONFIGURED_TEST_PASSED = "CONFIGURED_TEST_PASSED"
    CONFIGURED_TEST_FAILED = "CONFIGURED_TEST_FAILED"
    EXPIRED_OR_REVOKED = "EXPIRED_OR_REVOKED"
    DISABLED_BY_USER = "DISABLED_BY_USER"
    UNSUPPORTED = "UNSUPPORTED"


class ConnectionTestStatus(_StringEnum):
    TEST_NOT_SUPPORTED = "TEST_NOT_SUPPORTED"
    TEST_NOT_RUN = "TEST_NOT_RUN"
    TEST_RUNNING = "TEST_RUNNING"
    TEST_PASSED = "TEST_PASSED"
    TEST_FAILED = "TEST_FAILED"
    TEST_SKIPPED_BY_USER = "TEST_SKIPPED_BY_USER"


class AccessEntryKind(_StringEnum):
    ASR_PROVIDER = "ASR_PROVIDER"
    SOURCE_ADAPTER = "SOURCE_ADAPTER"
    ARCHIVE_SERVICE = "ARCHIVE_SERVICE"
    BROWSER_ASSISTED_CAPTURE = "BROWSER_ASSISTED_CAPTURE"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_for_dict(item) for key, item in value.items()}
    return value


def _dataclass_to_dict(instance: Any) -> dict[str, Any]:
    return {
        key: _value_for_dict(value)
        for key, value in asdict(instance).items()
    }


@dataclass(frozen=True)
class AccessEntryMetadata:
    entry_id: str
    entry_kind: AccessEntryKind
    display_name: str
    platform_family: str
    access_mode: AccessMode
    credential_status: CredentialStatus
    implementation_state: str = ""
    credential_type: str = ""
    credentials_required: bool = False
    credentials_optional: bool = False
    supports_browser_capture: bool = False
    supports_manual_import: bool = False
    supports_connection_test: bool = False
    supports_comments: bool = False
    supports_replies: bool = False
    supports_live_chat: bool = False
    supports_captions_or_transcripts: bool = False
    supports_visible_text: bool = False
    supports_article_text: bool = False
    supports_screenshot: bool = False
    supports_archive_check: bool = False
    supports_archive_submit: bool = False
    supports_media_evidence: bool = False
    supports_keyterms: bool = False
    supports_custom_vocabulary: bool = False
    supports_phrase_prompts: bool = False
    project_status: str = ""
    setup_hint: str = ""
    privacy_notes: str = ""
    cost_or_rate_limit_notes: str = ""
    access_limitations: str = ""
    last_tested_at_utc: str = ""
    last_test_status: ConnectionTestStatus = ConnectionTestStatus.TEST_NOT_SUPPORTED

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class ConnectionTestMetadata:
    entry_id: str
    status: ConnectionTestStatus
    user_triggered: bool = False
    tested_at_utc: str = ""
    test_type: str = ""
    safe_diagnostic: str = ""
    cost_or_rate_limit_warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass(frozen=True)
class AccessKeysCatalog:
    entries: tuple[AccessEntryMetadata, ...] = ()
    test_results: tuple[ConnectionTestMetadata, ...] = ()
    scope: str = ACCESS_KEYS_METADATA_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return access_keys_catalog_to_dict(self)


def build_access_keys_catalog(
    entries: Sequence[AccessEntryMetadata] = (),
    test_results: Sequence[ConnectionTestMetadata] = (),
) -> AccessKeysCatalog:
    return AccessKeysCatalog(
        entries=tuple(entries),
        test_results=tuple(test_results),
    )


def access_entry_metadata_to_dict(
    entry: AccessEntryMetadata,
) -> dict[str, Any]:
    return entry.to_dict()


def connection_test_metadata_to_dict(
    result: ConnectionTestMetadata,
) -> dict[str, Any]:
    return result.to_dict()


def access_keys_catalog_to_dict(
    catalog: AccessKeysCatalog,
) -> dict[str, Any]:
    return {
        "scope": catalog.scope,
        "entry_count": len(catalog.entries),
        "entries": [entry.to_dict() for entry in catalog.entries],
        "test_result_count": len(catalog.test_results),
        "test_results": [result.to_dict() for result in catalog.test_results],
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _enabled_capabilities(entry: AccessEntryMetadata) -> str:
    capability_names = (
        "browser_capture",
        "manual_import",
        "connection_test",
        "comments",
        "replies",
        "live_chat",
        "captions_or_transcripts",
        "visible_text",
        "article_text",
        "screenshot",
        "archive_check",
        "archive_submit",
        "media_evidence",
        "keyterms",
        "custom_vocabulary",
        "phrase_prompts",
    )
    enabled = [
        name
        for name in capability_names
        if getattr(entry, f"supports_{name}")
    ]
    return ", ".join(enabled) if enabled else "none"


def build_access_keys_markdown(catalog: AccessKeysCatalog) -> str:
    lines = [
        "# Access & Keys Metadata",
        "",
        "Local non-secret metadata/status only. This report does not store or test credentials, call providers/APIs, use browser profiles, fetch sources, check or submit archives, scrape pages, download media, or wire into the GUI/runtime.",
        "",
        f"- Entry count: {len(catalog.entries)}",
        f"- Recorded test-result count: {len(catalog.test_results)}",
        "",
    ]

    if not catalog.entries:
        lines.append("No access entries are registered in this catalog.")
    else:
        for entry in catalog.entries:
            lines.extend(
                [
                    f"## {entry.display_name}",
                    "",
                    f"- Entry ID: {entry.entry_id}",
                    f"- Entry kind: {entry.entry_kind.value}",
                    f"- Platform family: {entry.platform_family}",
                    f"- Implementation state: {entry.implementation_state or 'not stated'}",
                    f"- Access mode: {entry.access_mode.value}",
                    f"- Credential type: {entry.credential_type or 'not stated'}",
                    f"- Credential status: {entry.credential_status.value}",
                    f"- Credentials required: {_yes_no(entry.credentials_required)}",
                    f"- Credentials optional: {_yes_no(entry.credentials_optional)}",
                    f"- Connection test supported: {_yes_no(entry.supports_connection_test)}",
                    f"- Last test status: {entry.last_test_status.value}",
                    f"- Enabled capabilities: {_enabled_capabilities(entry)}",
                ]
            )
            if entry.project_status:
                lines.append(f"- Project status: {entry.project_status}")
            if entry.last_tested_at_utc:
                lines.append(f"- Last tested at UTC: {entry.last_tested_at_utc}")
            if entry.setup_hint:
                lines.append(f"- Setup hint: {entry.setup_hint}")
            if entry.privacy_notes:
                lines.append(f"- Privacy notes: {entry.privacy_notes}")
            if entry.cost_or_rate_limit_notes:
                lines.append(
                    f"- Cost/rate-limit notes: {entry.cost_or_rate_limit_notes}"
                )
            if entry.access_limitations:
                lines.append(f"- Access limitations: {entry.access_limitations}")
            lines.append("")

    if catalog.test_results:
        lines.extend(["## Recorded Connection-Test Metadata", ""])
        for result in catalog.test_results:
            lines.extend(
                [
                    f"### {result.entry_id}",
                    "",
                    f"- Status: {result.status.value}",
                    f"- Explicitly user-triggered: {_yes_no(result.user_triggered)}",
                    f"- Tested at UTC: {result.tested_at_utc or 'not recorded'}",
                    f"- Test type: {result.test_type or 'not stated'}",
                    f"- Safe diagnostic: {result.safe_diagnostic or 'none'}",
                    f"- Cost/rate-limit warning: {result.cost_or_rate_limit_warning or 'none'}",
                    "",
                ]
            )

    return "\n".join(lines).rstrip()


def build_access_keys_text(catalog: AccessKeysCatalog) -> str:
    lines = [
        "Access & Keys metadata",
        "Scope: local non-secret metadata/status only; no credential storage/testing, provider/API, browser, source-fetch, archive, scraping, media-download, GUI, or runtime behavior is performed.",
        f"entry_count: {len(catalog.entries)}",
        f"test_result_count: {len(catalog.test_results)}",
    ]

    if not catalog.entries:
        lines.append("No access entries are registered in this catalog.")
    else:
        for entry in catalog.entries:
            lines.extend(
                [
                    "",
                    f"{entry.entry_id} ({entry.display_name})",
                    f"entry_kind: {entry.entry_kind.value}",
                    f"platform_family: {entry.platform_family}",
                    f"implementation_state: {entry.implementation_state}",
                    f"access_mode: {entry.access_mode.value}",
                    f"credential_type: {entry.credential_type}",
                    f"credential_status: {entry.credential_status.value}",
                    f"credentials_required: {entry.credentials_required}",
                    f"credentials_optional: {entry.credentials_optional}",
                    f"supports_connection_test: {entry.supports_connection_test}",
                    f"last_test_status: {entry.last_test_status.value}",
                    f"enabled_capabilities: {_enabled_capabilities(entry)}",
                ]
            )
            if entry.project_status:
                lines.append(f"project_status: {entry.project_status}")
            if entry.last_tested_at_utc:
                lines.append(f"last_tested_at_utc: {entry.last_tested_at_utc}")
            if entry.setup_hint:
                lines.append(f"setup_hint: {entry.setup_hint}")
            if entry.privacy_notes:
                lines.append(f"privacy_notes: {entry.privacy_notes}")
            if entry.cost_or_rate_limit_notes:
                lines.append(
                    f"cost_or_rate_limit_notes: {entry.cost_or_rate_limit_notes}"
                )
            if entry.access_limitations:
                lines.append(f"access_limitations: {entry.access_limitations}")

    if catalog.test_results:
        lines.extend(["", "recorded_connection_test_metadata:"])
        for result in catalog.test_results:
            lines.extend(
                [
                    f"- entry_id: {result.entry_id}",
                    f"  status: {result.status.value}",
                    f"  user_triggered: {result.user_triggered}",
                    f"  tested_at_utc: {result.tested_at_utc}",
                    f"  test_type: {result.test_type}",
                    f"  safe_diagnostic: {result.safe_diagnostic}",
                    "  cost_or_rate_limit_warning: "
                    f"{result.cost_or_rate_limit_warning}",
                ]
            )

    return "\n".join(lines)


def render_access_keys_catalog(
    catalog: AccessKeysCatalog,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_access_keys_markdown(catalog)
    if output_format == "text":
        return build_access_keys_text(catalog)
    if output_format == "json":
        return json.dumps(
            access_keys_catalog_to_dict(catalog),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
