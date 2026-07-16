from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from capture_options import (
    CAPTURE_ARCHIVE_CHECK,
    CAPTURE_ARCHIVE_SUBMIT,
    CAPTURE_CAPTIONS_TRANSCRIPTS,
    CAPTURE_COMMENTS,
    CAPTURE_DISPUTED_FRAMING_NOTES,
    CAPTURE_FULL_PAGE_SCREENSHOT,
    CAPTURE_HTML_SNAPSHOT,
    CAPTURE_LIVE_CHAT,
    CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS,
    CAPTURE_POSTS,
    CAPTURE_READABLE_ARTICLE_TEXT,
    CAPTURE_REPLIES,
    CAPTURE_SOURCE_ROLE_LABELS,
    CAPTURE_STAGE_AVAILABLE,
    CAPTURE_STAGE_FUTURE_ONLY,
    CAPTURE_VIDEO_MEDIA_EVIDENCE,
    CAPTURE_VISIBLE_PAGE_TEXT,
    get_capture_option,
)
from source_capture_plan import SourceCapturePlan, build_source_capture_plan
from source_plan_provenance import provenance_from_source_capture_plan


CONTRACT_STATUS_SUPPORTED_BY_ADAPTER = "supported_by_adapter"
CONTRACT_STATUS_PLANNED_CONTRACT_ONLY = "planned_contract_only"
CONTRACT_STATUS_FUTURE_ONLY = "future_only"
CONTRACT_STATUS_UNSUPPORTED_BY_ADAPTER = "unsupported_by_adapter"
CONTRACT_STATUS_REQUIRES_EXTERNAL_SERVICE = "requires_external_service"
CONTRACT_STATUS_UNKNOWN_OPTION = "unknown_option"

EXECUTION_EXISTING_RUNTIME_ELSEWHERE = "existing_runtime_elsewhere"
EXECUTION_LOCAL_METADATA_ONLY = "local_metadata_only"
EXECUTION_FUTURE_USER_TRIGGERED = "future_user_triggered"
EXECUTION_NO_RUNTIME_CAPTURE = "no_runtime_capture"

COMPLETENESS_RUNTIME_DEPENDENT = "runtime_dependent"
COMPLETENESS_METADATA_ONLY = "metadata_only_not_captured"
COMPLETENESS_UNSUPPORTED = "unsupported_not_captured"
COMPLETENESS_EXTERNAL_APPROVAL_REQUIRED = "external_approval_required"


@dataclass(frozen=True)
class SourceCaptureContractItem:
    option_id: str
    display_name: str = ""
    contract_status: str = CONTRACT_STATUS_UNKNOWN_OPTION
    execution_mode: str = EXECUTION_NO_RUNTIME_CAPTURE
    completeness_status: str = COMPLETENESS_METADATA_ONLY
    adapter_supports_option: bool = False
    requires_user_trigger: bool = True
    requires_user_confirmation: bool = False
    sends_data_to_external_service: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceCaptureContract:
    source_url: str = ""
    normalized_url: str = ""
    adapter_name: str = ""
    adapter_display_name: str = ""
    plan_status: str = ""
    items: tuple[SourceCaptureContractItem, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = (
        "local source capture contract only; no fetch, capture, network, "
        "archive, screenshot, scraping, browser, download, provider, credential, "
        "or GUI behavior"
    )


def _adapter_supports_option(plan: SourceCapturePlan, option_id: str) -> bool:
    adapter_name = plan.adapter_name
    if not adapter_name:
        return False

    # Keep this mapping intentionally narrow. It records adapter-declared
    # capability only; it does not execute the corresponding capture.
    from source_adapters import find_source_adapter_by_name

    adapter = find_source_adapter_by_name(adapter_name)
    if adapter is None:
        return False

    capabilities = adapter.capabilities
    if option_id == CAPTURE_COMMENTS:
        return capabilities.supports_comments
    if option_id == CAPTURE_REPLIES:
        return capabilities.supports_replies
    if option_id == CAPTURE_LIVE_CHAT:
        return capabilities.supports_livechat
    if option_id == CAPTURE_CAPTIONS_TRANSCRIPTS:
        return capabilities.supports_transcripts
    return False


def _is_existing_runtime_elsewhere(plan: SourceCapturePlan, option_id: str) -> bool:
    return plan.adapter_name == "youtube" and option_id in {
        CAPTURE_COMMENTS,
        CAPTURE_REPLIES,
        CAPTURE_LIVE_CHAT,
    }


def _contract_item_from_option(
    plan: SourceCapturePlan,
    option_id: str,
) -> SourceCaptureContractItem:
    option = get_capture_option(option_id)
    if option is None:
        return SourceCaptureContractItem(
            option_id=option_id,
            contract_status=CONTRACT_STATUS_UNKNOWN_OPTION,
            completeness_status=COMPLETENESS_UNSUPPORTED,
            warnings=(f"Unknown capture option: {option_id}",),
        )

    warnings: list[str] = []
    adapter_supports = _adapter_supports_option(plan, option_id)
    sends_external = bool(option.sends_data_to_external_service)
    requires_confirmation = bool(option.requires_user_confirmation)

    if option_id in (CAPTURE_ARCHIVE_CHECK, CAPTURE_ARCHIVE_SUBMIT):
        status = CONTRACT_STATUS_REQUIRES_EXTERNAL_SERVICE
        execution_mode = EXECUTION_NO_RUNTIME_CAPTURE
        completeness = COMPLETENESS_EXTERNAL_APPROVAL_REQUIRED
        warnings.append(
            f"{option.display_name} is external archive behavior and is not executed by this contract."
        )
    elif option.stage == CAPTURE_STAGE_FUTURE_ONLY:
        status = CONTRACT_STATUS_FUTURE_ONLY
        execution_mode = EXECUTION_FUTURE_USER_TRIGGERED
        completeness = COMPLETENESS_METADATA_ONLY
        warnings.append(
            f"{option.display_name} is future-only metadata here; no capture is performed."
        )
    elif _is_existing_runtime_elsewhere(plan, option_id):
        status = CONTRACT_STATUS_SUPPORTED_BY_ADAPTER
        execution_mode = EXECUTION_EXISTING_RUNTIME_ELSEWHERE
        completeness = COMPLETENESS_RUNTIME_DEPENDENT
        warnings.append(
            f"{option.display_name} is supported by the current YouTube runtime elsewhere; this contract does not fetch it."
        )
    elif adapter_supports:
        status = CONTRACT_STATUS_SUPPORTED_BY_ADAPTER
        execution_mode = EXECUTION_FUTURE_USER_TRIGGERED
        completeness = COMPLETENESS_METADATA_ONLY
        warnings.append(
            f"{option.display_name} is adapter-supported metadata here, but this contract does not execute capture."
        )
    elif option_id in {
        CAPTURE_POSTS,
        CAPTURE_VISIBLE_PAGE_TEXT,
        CAPTURE_READABLE_ARTICLE_TEXT,
        CAPTURE_FULL_PAGE_SCREENSHOT,
        CAPTURE_HTML_SNAPSHOT,
    }:
        status = CONTRACT_STATUS_PLANNED_CONTRACT_ONLY
        execution_mode = EXECUTION_FUTURE_USER_TRIGGERED
        completeness = COMPLETENESS_METADATA_ONLY
        warnings.append(
            f"{option.display_name} needs a future explicit user-triggered capture workflow; no content is captured."
        )
    else:
        status = CONTRACT_STATUS_UNSUPPORTED_BY_ADAPTER
        execution_mode = EXECUTION_NO_RUNTIME_CAPTURE
        completeness = COMPLETENESS_UNSUPPORTED
        warnings.append(
            f"{option.display_name} is not supported by adapter {plan.adapter_name or '(none)'} in this local contract."
        )

    if option_id == CAPTURE_READABLE_ARTICLE_TEXT:
        warnings.append(
            "Readable/article text must be explicitly selected; comments-only capture must not force article-body extraction."
        )
    if option_id == CAPTURE_HTML_SNAPSHOT:
        warnings.append(
            "HTML snapshot provenance must distinguish raw saved HTML from selected or print-cleaned HTML."
        )
    if option_id in {
        CAPTURE_MEDIA_SOURCE_CHAIN_FIELDS,
        CAPTURE_DISPUTED_FRAMING_NOTES,
        CAPTURE_SOURCE_ROLE_LABELS,
    }:
        execution_mode = EXECUTION_LOCAL_METADATA_ONLY

    return SourceCaptureContractItem(
        option_id=option.option_id,
        display_name=option.display_name,
        contract_status=status,
        execution_mode=execution_mode,
        completeness_status=completeness,
        adapter_supports_option=adapter_supports,
        requires_user_trigger=True,
        requires_user_confirmation=requires_confirmation,
        sends_data_to_external_service=sends_external,
        warnings=tuple(warnings),
    )


def build_source_capture_contract(
    *,
    source_url: str,
    source_label: str = "",
    title: str = "",
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
) -> SourceCaptureContract:
    plan = build_source_capture_plan(
        source_url=source_url,
        source_label=source_label,
        title=title,
        selected_capture_options=selected_capture_options,
        user_terms=user_terms,
    )
    option_ids = plan.selected_capture_options + plan.unknown_capture_options
    items = tuple(_contract_item_from_option(plan, option_id) for option_id in option_ids)
    warnings = list(plan.warnings)
    for item in items:
        warnings.extend(item.warnings)

    return SourceCaptureContract(
        source_url=plan.source_url,
        normalized_url=plan.normalized_url,
        adapter_name=plan.adapter_name,
        adapter_display_name=plan.adapter_display_name,
        plan_status=plan.status,
        items=items,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def source_capture_contract_to_dict(
    contract: SourceCaptureContract,
) -> dict[str, Any]:
    provenance = provenance_from_source_capture_plan(
        SourceCapturePlan(
            source_url=contract.source_url,
            normalized_url=contract.normalized_url,
            adapter_name=contract.adapter_name,
            adapter_display_name=contract.adapter_display_name,
            status=contract.plan_status,
            warnings=contract.warnings,
        )
    )
    return {
        "adapter_display_name": contract.adapter_display_name,
        "adapter_name": contract.adapter_name,
        "items": [
            {
                "adapter_supports_option": item.adapter_supports_option,
                "completeness_status": item.completeness_status,
                "contract_status": item.contract_status,
                "display_name": item.display_name,
                "execution_mode": item.execution_mode,
                "option_id": item.option_id,
                "requires_user_confirmation": item.requires_user_confirmation,
                "requires_user_trigger": item.requires_user_trigger,
                "sends_data_to_external_service": item.sends_data_to_external_service,
                "warnings": list(item.warnings),
            }
            for item in contract.items
        ],
        "normalized_url": contract.normalized_url,
        "plan_status": contract.plan_status,
        "provenance": provenance.to_dict(),
        "scope": contract.scope,
        "source_url": contract.source_url,
        "warnings": list(contract.warnings),
    }


def summarize_source_capture_contract(contract: SourceCaptureContract) -> str:
    lines = [
        "Source capture contract",
        f"Scope: {contract.scope}",
        f"Source URL: {contract.source_url}",
        f"Normalized URL: {contract.normalized_url or '(none)'}",
        f"Plan status: {contract.plan_status}",
        f"Adapter: {contract.adapter_display_name or contract.adapter_name or '(none)'}",
        "Capture options:",
    ]
    if not contract.items:
        lines.append("- (none)")
    for item in contract.items:
        lines.append(
            f"- {item.option_id}: {item.contract_status}; "
            f"execution={item.execution_mode}; completeness={item.completeness_status}"
        )
        for warning in item.warnings:
            lines.append(f"  warning: {warning}")
    lines.append("Warnings:")
    if contract.warnings:
        for warning in contract.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def source_capture_contract_to_json(contract: SourceCaptureContract) -> str:
    return json.dumps(
        source_capture_contract_to_dict(contract),
        indent=2,
        sort_keys=True,
    )
