from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from source_capture_plan import SourceCapturePlan, build_source_capture_plan


REPORT_FORMATS = ("markdown", "text", "json")


def _dataclass_to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _dataclass_to_plain(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_dataclass_to_plain(item) for item in value]
    if isinstance(value, list):
        return [_dataclass_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _dataclass_to_plain(item)
            for key, item in value.items()
        }
    return value


def source_capture_plan_to_dict(plan: SourceCapturePlan) -> dict[str, Any]:
    return _dataclass_to_plain(plan)


def load_source_capture_plan_input(input_path: str) -> Mapping[str, Any]:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise ValueError("input JSON must be an object")
    if "source_url" not in data:
        raise ValueError("input JSON must include source_url")
    return data


def build_source_capture_plan_from_input(data: Mapping[str, Any]) -> SourceCapturePlan:
    selected_capture_options = data.get("selected_capture_options", ())
    user_terms = data.get("user_terms", ())

    if isinstance(selected_capture_options, str):
        raise ValueError("selected_capture_options must be a list of strings")
    if isinstance(user_terms, str):
        raise ValueError("user_terms must be a list of strings")

    return build_source_capture_plan(
        source_url=str(data.get("source_url", "")),
        source_label=str(data.get("source_label", "")),
        title=str(data.get("title", "")),
        selected_capture_options=tuple(str(item) for item in selected_capture_options),
        user_terms=tuple(str(item) for item in user_terms),
    )


def _format_list(values: Sequence[str], *, empty: str = "none") -> str:
    if not values:
        return empty
    return ", ".join(values)


def _render_context_markdown(plan: SourceCapturePlan) -> list[str]:
    result = plan.context_result
    if result is None:
        return ["## Context / Glossary", "", "- Context result: none"]

    lines = [
        "## Context / Glossary",
        "",
        f"- Source label: {result.source_label or 'none'}",
        f"- Source URL: {result.source_url or 'none'}",
        f"- Context hint count: {len(result.context_hints)}",
        f"- Glossary term count: {len(result.glossary_terms)}",
    ]

    if result.context_hints:
        lines.extend(["", "### Context Hints"])
        for hint in result.context_hints:
            lines.append(
                f"- {hint.label or hint.source}: {hint.value} "
                f"(source={hint.source}, confidence={hint.confidence:.2f})"
            )

    if result.glossary_terms:
        lines.extend(["", "### Glossary Terms"])
        for term in result.glossary_terms:
            aliases = _format_list(term.aliases)
            lines.append(
                f"- {term.text} (category={term.category}, source={term.source}, aliases={aliases})"
            )

    if result.warnings:
        lines.extend(["", "### Context Warnings"])
        for warning in result.warnings:
            lines.append(f"- {warning}")

    return lines


def build_source_capture_plan_markdown(plan: SourceCapturePlan) -> str:
    lines = [
        "# Source Capture Plan",
        "",
        "Local/manual planning only. This report does not fetch URLs, download media, call providers, use network/archive services, scrape pages, capture screenshots, store credentials, inspect ZIPs, or wire into the GUI.",
        "",
        "## Source",
        "",
        f"- Status: {plan.status}",
        f"- Source URL: {plan.source_url or 'none'}",
        f"- Normalized URL: {plan.normalized_url or 'none'}",
        f"- Source ID: {plan.source_id or 'none'}",
        f"- Adapter: {plan.adapter_display_name or plan.adapter_name or 'none'}",
        "",
        "## Capture Options",
        "",
        f"- Selected: {_format_list(plan.selected_capture_options)}",
        f"- Unknown: {_format_list(plan.unknown_capture_options)}",
        f"- Duplicates: {_format_list(plan.duplicate_capture_options)}",
    ]
    if plan.warnings:
        lines.extend(["", "## Plan Warnings", ""])
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    lines.extend(["", *_render_context_markdown(plan)])
    return "\n".join(lines)


def build_source_capture_plan_text(plan: SourceCapturePlan) -> str:
    lines = [
        "Source capture plan",
        "Scope: local/manual planning only; no fetch/capture/network/provider/GUI behavior is performed.",
        "",
        f"Status: {plan.status}",
        f"Source URL: {plan.source_url or 'none'}",
        f"Normalized URL: {plan.normalized_url or 'none'}",
        f"Source ID: {plan.source_id or 'none'}",
        f"Adapter: {plan.adapter_display_name or plan.adapter_name or 'none'}",
        f"Selected capture options: {_format_list(plan.selected_capture_options)}",
        f"Unknown capture options: {_format_list(plan.unknown_capture_options)}",
        f"Duplicate capture options: {_format_list(plan.duplicate_capture_options)}",
    ]

    if plan.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in plan.warnings)

    if plan.context_result is not None:
        result = plan.context_result
        lines.extend(
            [
                "",
                "Context / glossary:",
                f"Source label: {result.source_label or 'none'}",
                f"Source URL: {result.source_url or 'none'}",
                f"Context hint count: {len(result.context_hints)}",
                f"Glossary term count: {len(result.glossary_terms)}",
            ]
        )
        for hint in result.context_hints:
            lines.append(
                f"- Hint {hint.label or hint.source}: {hint.value} "
                f"(source={hint.source}, confidence={hint.confidence:.2f})"
            )
        for term in result.glossary_terms:
            lines.append(
                f"- Term {term.text} (category={term.category}, source={term.source})"
            )

    return "\n".join(lines)


def render_source_capture_plan(plan: SourceCapturePlan, *, output_format: str) -> str:
    if output_format == "markdown":
        return build_source_capture_plan_markdown(plan)
    if output_format == "text":
        return build_source_capture_plan_text(plan)
    if output_format == "json":
        return json.dumps(
            source_capture_plan_to_dict(plan),
            indent=2,
            sort_keys=True,
        )
    raise ValueError(f"unsupported output format: {output_format}")


def write_report_output(output_path: str, text: str, *, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local/manual source capture plan without fetch/capture/network behavior.",
    )
    parser.add_argument("--input", required=True, help="Path to source capture plan JSON input.")
    parser.add_argument(
        "--format",
        choices=REPORT_FORMATS,
        default="markdown",
        help="Output format.",
    )
    parser.add_argument("--output", default="", help="Optional output path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_source_capture_plan_input(args.input)
        plan = build_source_capture_plan_from_input(data)
        rendered = render_source_capture_plan(plan, output_format=args.format)
        if args.output:
            write_report_output(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except FileNotFoundError as exc:
        print(f"error: input file not found: {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, FileExistsError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
