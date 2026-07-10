from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from context_glossary import TopicResolutionResult, phrase_prompt_terms, resolve_context_hints


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


def context_glossary_result_to_dict(result: TopicResolutionResult) -> dict[str, Any]:
    data = _dataclass_to_plain(result)
    data["phrase_prompt_terms"] = list(phrase_prompt_terms(result.glossary_terms))
    data["scope"] = (
        "local/manual context and glossary normalization only; "
        "no fetch/capture/network/provider/GUI behavior is performed"
    )
    return data


def load_context_glossary_input(input_path: str) -> Mapping[str, Any]:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise ValueError("input JSON must be an object")
    return data


def build_context_glossary_from_input(data: Mapping[str, Any]) -> TopicResolutionResult:
    user_terms = data.get("user_terms", ())
    if isinstance(user_terms, str):
        raise ValueError("user_terms must be a list of strings")

    return resolve_context_hints(
        source_label=str(data.get("source_label", "")),
        source_url=str(data.get("source_url", "")),
        title=str(data.get("title", "")),
        user_terms=tuple(str(item) for item in user_terms),
    )


def _format_list(values: Sequence[str], *, empty: str = "none") -> str:
    if not values:
        return empty
    return ", ".join(values)


def build_context_glossary_markdown(result: TopicResolutionResult) -> str:
    prompt_terms = phrase_prompt_terms(result.glossary_terms)
    lines = [
        "# Context / Glossary Report",
        "",
        "Local/manual context and glossary normalization only. This report does not fetch URLs, download media, call providers, use network/archive services, scrape pages, capture screenshots, store credentials, inspect ZIPs, or wire into the GUI.",
        "",
        "## Source",
        "",
        f"- Source label: {result.source_label or 'none'}",
        f"- Source URL: {result.source_url or 'none'}",
        "",
        "## Summary",
        "",
        f"- Context hint count: {len(result.context_hints)}",
        f"- Glossary term count: {len(result.glossary_terms)}",
        f"- Phrase prompt term count: {len(prompt_terms)}",
    ]

    if result.context_hints:
        lines.extend(["", "## Context Hints", ""])
        for hint in result.context_hints:
            lines.append(
                f"- {hint.label or hint.source}: {hint.value} "
                f"(source={hint.source}, confidence={hint.confidence:.2f})"
            )

    if result.glossary_terms:
        lines.extend(["", "## Glossary Terms", ""])
        for term in result.glossary_terms:
            aliases = _format_list(term.aliases)
            lines.append(
                f"- {term.text} (category={term.category}, source={term.source}, aliases={aliases}, case_sensitive={term.case_sensitive})"
            )

    if prompt_terms:
        lines.extend(["", "## Phrase Prompt Terms", ""])
        for term in prompt_terms:
            lines.append(f"- {term}")

    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")

    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- User review is required before glossary terms affect ASR prompts, provider keyterms, QA checks, or transcript decisions.",
            "- Context and glossary terms are not ground truth and are not a replacement for transcription.",
        ]
    )
    return "\n".join(lines)


def build_context_glossary_text(result: TopicResolutionResult) -> str:
    prompt_terms = phrase_prompt_terms(result.glossary_terms)
    lines = [
        "Context / glossary report",
        "Scope: local/manual normalization only; no fetch/capture/network/provider/GUI behavior is performed.",
        "",
        f"Source label: {result.source_label or 'none'}",
        f"Source URL: {result.source_url or 'none'}",
        f"Context hint count: {len(result.context_hints)}",
        f"Glossary term count: {len(result.glossary_terms)}",
        f"Phrase prompt term count: {len(prompt_terms)}",
    ]

    if result.context_hints:
        lines.append("Context hints:")
        for hint in result.context_hints:
            lines.append(
                f"- {hint.label or hint.source}: {hint.value} "
                f"(source={hint.source}, confidence={hint.confidence:.2f})"
            )

    if result.glossary_terms:
        lines.append("Glossary terms:")
        for term in result.glossary_terms:
            lines.append(
                f"- {term.text} (category={term.category}, source={term.source})"
            )

    if prompt_terms:
        lines.append("Phrase prompt terms:")
        lines.extend(f"- {term}" for term in prompt_terms)

    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)

    lines.append("User review required before ASR prompt/keyterm or transcript use.")
    return "\n".join(lines)


def render_context_glossary(result: TopicResolutionResult, *, output_format: str) -> str:
    if output_format == "markdown":
        return build_context_glossary_markdown(result)
    if output_format == "text":
        return build_context_glossary_text(result)
    if output_format == "json":
        return json.dumps(
            context_glossary_result_to_dict(result),
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
        description="Render local/manual context glossary hints without fetch/capture/network behavior.",
    )
    parser.add_argument("--input", required=True, help="Path to context/glossary JSON input.")
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
        data = load_context_glossary_input(args.input)
        result = build_context_glossary_from_input(data)
        rendered = render_context_glossary(result, output_format=args.format)
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
