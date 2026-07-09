from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from capture_options import normalize_capture_option_ids
from context_glossary import TopicResolutionResult, resolve_context_hints
from source_adapters import find_source_adapter


PLAN_STATUS_READY = "ready"
PLAN_STATUS_UNSUPPORTED_SOURCE = "unsupported_source"
PLAN_STATUS_INVALID_SOURCE = "invalid_source"


@dataclass(frozen=True)
class SourceCapturePlan:
    source_url: str = ""
    normalized_url: str = ""
    source_id: str = ""
    adapter_name: str = ""
    adapter_display_name: str = ""
    status: str = PLAN_STATUS_INVALID_SOURCE
    selected_capture_options: tuple[str, ...] = ()
    unknown_capture_options: tuple[str, ...] = ()
    duplicate_capture_options: tuple[str, ...] = ()
    context_result: Optional[TopicResolutionResult] = None
    warnings: tuple[str, ...] = ()


def build_source_capture_plan(
    *,
    source_url: str,
    source_label: str = "",
    title: str = "",
    selected_capture_options: Sequence[str] = (),
    user_terms: Sequence[str] = (),
) -> SourceCapturePlan:
    trimmed_source_url = (source_url or "").strip()
    capture_selection = normalize_capture_option_ids(selected_capture_options)
    warnings = list(capture_selection.warnings)

    adapter = find_source_adapter(trimmed_source_url)
    if adapter is None:
        warnings.append(f"No source adapter supports the URL: {trimmed_source_url or '(empty)'}")
        context_result = resolve_context_hints(
            source_label=source_label,
            source_url=trimmed_source_url,
            title=title,
            user_terms=user_terms,
        )
        return SourceCapturePlan(
            source_url=trimmed_source_url,
            status=PLAN_STATUS_UNSUPPORTED_SOURCE,
            selected_capture_options=capture_selection.selected_option_ids,
            unknown_capture_options=capture_selection.unknown_option_ids,
            duplicate_capture_options=capture_selection.duplicate_option_ids,
            context_result=context_result,
            warnings=tuple(warnings),
        )

    try:
        normalized_url = adapter.normalize_url(trimmed_source_url)
        source_id = adapter.extract_source_id(trimmed_source_url)
    except ValueError as exc:
        warnings.append(str(exc))
        context_result = resolve_context_hints(
            source_label=source_label,
            source_url=trimmed_source_url,
            title=title,
            user_terms=user_terms,
        )
        return SourceCapturePlan(
            source_url=trimmed_source_url,
            status=PLAN_STATUS_INVALID_SOURCE,
            selected_capture_options=capture_selection.selected_option_ids,
            unknown_capture_options=capture_selection.unknown_option_ids,
            duplicate_capture_options=capture_selection.duplicate_option_ids,
            context_result=context_result,
            warnings=tuple(warnings),
        )

    metadata = getattr(adapter, "metadata", None)
    adapter_display_name = getattr(metadata, "display_name", "") or adapter.source_name
    context_result = resolve_context_hints(
        source_label=source_label,
        source_url=normalized_url,
        title=title,
        user_terms=user_terms,
    )
    return SourceCapturePlan(
        source_url=trimmed_source_url,
        normalized_url=normalized_url,
        source_id=source_id,
        adapter_name=adapter.source_name,
        adapter_display_name=adapter_display_name,
        status=PLAN_STATUS_READY,
        selected_capture_options=capture_selection.selected_option_ids,
        unknown_capture_options=capture_selection.unknown_option_ids,
        duplicate_capture_options=capture_selection.duplicate_option_ids,
        context_result=context_result,
        warnings=tuple(warnings),
    )
