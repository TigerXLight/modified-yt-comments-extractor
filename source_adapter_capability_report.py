from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from source_adapters import AVAILABLE_SOURCE_ADAPTERS, SourceAdapter


REPORT_FORMATS = ("markdown", "text", "json")


@dataclass(frozen=True)
class SourceAdapterCapabilityRecord:
    adapter_id: str
    display_name: str
    platform_family: str
    credential_type: str
    credentials_required: bool
    credentials_optional: bool
    supports_browser_capture: bool
    supports_manual_import: bool
    test_connection_supported: bool
    capabilities: dict[str, bool]
    setup_hint: str = ""
    privacy_notes: str = ""
    cost_or_rate_limit_notes: str = ""
    access_limitations: str = ""


@dataclass(frozen=True)
class SourceAdapterCapabilityReport:
    records: tuple[SourceAdapterCapabilityRecord, ...]
    scope: str = (
        "local source adapter metadata report only; no fetch, capture, "
        "network, provider, archive, browser, scraping, credential, or GUI behavior"
    )


def _adapter_capabilities_to_dict(adapter: SourceAdapter) -> dict[str, bool]:
    capabilities = adapter.capabilities
    return {
        "supports_author_channel_ids": capabilities.supports_author_channel_ids,
        "supports_comments": capabilities.supports_comments,
        "supports_likes": capabilities.supports_likes,
        "supports_livechat": capabilities.supports_livechat,
        "supports_replies": capabilities.supports_replies,
        "supports_timestamps": capabilities.supports_timestamps,
        "supports_transcripts": capabilities.supports_transcripts,
    }


def source_adapter_capability_record_from_adapter(
    adapter: SourceAdapter,
) -> SourceAdapterCapabilityRecord:
    metadata = adapter.metadata
    return SourceAdapterCapabilityRecord(
        adapter_id=adapter.source_name,
        display_name=metadata.display_name or adapter.source_name,
        platform_family=metadata.platform_family,
        credential_type=metadata.credential_type,
        credentials_required=metadata.credentials_required,
        credentials_optional=metadata.credentials_optional,
        supports_browser_capture=metadata.supports_browser_capture,
        supports_manual_import=metadata.supports_manual_import,
        test_connection_supported=metadata.test_connection_supported,
        capabilities=_adapter_capabilities_to_dict(adapter),
        setup_hint=metadata.setup_hint,
        privacy_notes=metadata.privacy_notes,
        cost_or_rate_limit_notes=metadata.cost_or_rate_limit_notes,
        access_limitations=metadata.access_limitations,
    )


def build_source_adapter_capability_report(
    adapters: Sequence[SourceAdapter] = AVAILABLE_SOURCE_ADAPTERS,
) -> SourceAdapterCapabilityReport:
    records = tuple(
        source_adapter_capability_record_from_adapter(adapter)
        for adapter in adapters
    )
    return SourceAdapterCapabilityReport(records=records)


def source_adapter_capability_report_to_dict(
    report: SourceAdapterCapabilityReport,
) -> dict[str, Any]:
    return {
        "scope": report.scope,
        "adapter_count": len(report.records),
        "source_adapters": [
            {
                "access_limitations": record.access_limitations,
                "adapter_id": record.adapter_id,
                "capabilities": dict(sorted(record.capabilities.items())),
                "cost_or_rate_limit_notes": record.cost_or_rate_limit_notes,
                "credential_type": record.credential_type,
                "credentials_optional": record.credentials_optional,
                "credentials_required": record.credentials_required,
                "display_name": record.display_name,
                "platform_family": record.platform_family,
                "privacy_notes": record.privacy_notes,
                "setup_hint": record.setup_hint,
                "supports_browser_capture": record.supports_browser_capture,
                "supports_manual_import": record.supports_manual_import,
                "test_connection_supported": record.test_connection_supported,
            }
            for record in report.records
        ],
    }


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _format_enabled_capabilities(record: SourceAdapterCapabilityRecord) -> str:
    enabled = [
        name
        for name, is_supported in sorted(record.capabilities.items())
        if is_supported
    ]
    if not enabled:
        return "none"
    return ", ".join(enabled)


def build_source_adapter_capability_markdown(
    report: SourceAdapterCapabilityReport,
) -> str:
    lines = [
        "# Source Adapter Capability Report",
        "",
        "Local source adapter metadata report only. This report does not fetch URLs, download media, call providers, use network/archive services, scrape pages, capture screenshots, store credentials, test credentials, inspect ZIPs, or wire into the GUI.",
        "",
        f"- Adapter count: {len(report.records)}",
        "",
    ]

    if not report.records:
        lines.append("No source adapters are registered.")
        return "\n".join(lines)

    for record in report.records:
        lines.extend(
            [
                f"## {record.display_name}",
                "",
                f"- Adapter ID: {record.adapter_id}",
                f"- Platform family: {record.platform_family}",
                f"- Credential type: {record.credential_type}",
                f"- Credentials required: {_format_bool(record.credentials_required)}",
                f"- Credentials optional: {_format_bool(record.credentials_optional)}",
                f"- Browser capture supported: {_format_bool(record.supports_browser_capture)}",
                f"- Manual import supported: {_format_bool(record.supports_manual_import)}",
                f"- Test connection supported: {_format_bool(record.test_connection_supported)}",
                f"- Enabled capabilities: {_format_enabled_capabilities(record)}",
            ]
        )
        if record.setup_hint:
            lines.append(f"- Setup hint: {record.setup_hint}")
        if record.privacy_notes:
            lines.append(f"- Privacy notes: {record.privacy_notes}")
        if record.cost_or_rate_limit_notes:
            lines.append(f"- Cost/rate-limit notes: {record.cost_or_rate_limit_notes}")
        if record.access_limitations:
            lines.append(f"- Access limitations: {record.access_limitations}")
        lines.append("")

    return "\n".join(lines).rstrip()


def build_source_adapter_capability_text(
    report: SourceAdapterCapabilityReport,
) -> str:
    lines = [
        "Source adapter capability report",
        "Scope: local metadata only; no fetch/capture/network/provider/archive/browser/scraping/credential/GUI behavior is performed.",
        f"Adapter count: {len(report.records)}",
    ]

    if not report.records:
        lines.append("No source adapters are registered.")
        return "\n".join(lines)

    for record in report.records:
        lines.extend(
            [
                "",
                f"{record.adapter_id} ({record.display_name})",
                f"platform_family: {record.platform_family}",
                f"credential_type: {record.credential_type}",
                f"credentials_required: {record.credentials_required}",
                f"credentials_optional: {record.credentials_optional}",
                f"supports_browser_capture: {record.supports_browser_capture}",
                f"supports_manual_import: {record.supports_manual_import}",
                f"test_connection_supported: {record.test_connection_supported}",
                f"enabled_capabilities: {_format_enabled_capabilities(record)}",
            ]
        )
        if record.setup_hint:
            lines.append(f"setup_hint: {record.setup_hint}")
        if record.privacy_notes:
            lines.append(f"privacy_notes: {record.privacy_notes}")
        if record.cost_or_rate_limit_notes:
            lines.append(f"cost_or_rate_limit_notes: {record.cost_or_rate_limit_notes}")
        if record.access_limitations:
            lines.append(f"access_limitations: {record.access_limitations}")

    return "\n".join(lines)


def render_source_adapter_capability_report(
    report: SourceAdapterCapabilityReport,
    *,
    output_format: str,
) -> str:
    if output_format == "markdown":
        return build_source_adapter_capability_markdown(report)
    if output_format == "text":
        return build_source_adapter_capability_text(report)
    if output_format == "json":
        return json.dumps(
            source_adapter_capability_report_to_dict(report),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")
