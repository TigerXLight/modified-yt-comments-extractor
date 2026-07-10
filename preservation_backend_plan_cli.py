# Evidence bundle integration: preservation backend CLI flags.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from capture_method_metadata import available_capture_methods
from preservation_backend_plan import (
    REPORT_FORMATS,
    build_preservation_backend_plan,
    render_preservation_backend_plan,
)
from preservation_evidence_bundle import (
    BUNDLE_STATUSES,
    build_preservation_evidence_bundle,
    build_preservation_evidence_item,
)


def _read_input(path: str) -> dict[str, Any]:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"input file not found: {input_path}")
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {input_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object")
    return data


def _optional_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return value


def _build_plan_from_input(
    data: dict[str, Any],
    *,
    capture_method_ids: Sequence[str] | None = None,
    evidence_bundle=None,
):
    return build_preservation_backend_plan(
        source_url=_optional_string(data, "source_url"),
        selected_backend_ids=_optional_string_list(data, "selected_backend_ids"),
        selected_format_ids=_optional_string_list(data, "selected_format_ids"),
        selected_capture_method_ids=(
            list(capture_method_ids)
            if capture_method_ids is not None
            else _optional_string_list(data, "selected_capture_method_ids")
        ),
        media_preservation_choice=_optional_string(
            data, "media_preservation_choice"
        ),
        notes=_optional_string(data, "notes"),
        evidence_bundle=evidence_bundle,
    )


def write_report_output(output_path: str, text: str, *, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"output path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _parse_preservation_evidence_item(value: str):
    parts = [part.strip() for part in str(value or "").split(":")]
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise ValueError(
            "evidence item must use artifact_id:artifact_format[:capture_method_id]"
        )
    return build_preservation_evidence_item(
        artifact_id=parts[0],
        artifact_format=parts[1],
        capture_method_id=parts[2] if len(parts) == 3 else "",
    )


def _build_cli_evidence_bundle(
    *,
    source_url: str = "",
    bundle_label: str = "",
    status: str = "",
    notes: str = "",
    item_values: Sequence[str] = (),
):
    if not (status or bundle_label or notes or item_values):
        return None
    items = tuple(_parse_preservation_evidence_item(value) for value in item_values)
    return build_preservation_evidence_bundle(
        source_url=source_url or "",
        bundle_label=bundle_label or "",
        status=status or "planned",
        notes=notes or "",
        items=items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a local preservation backend plan without fetch/capture/archive execution.",
    )
    parser.add_argument(
        "--input",
        default="",
        help="Optional JSON input path. Without input, renders available backend/format options with no selections.",
    )
    parser.add_argument(
        "--format",
        choices=REPORT_FORMATS,
        default="markdown",
        help="Output format.",
    )
    parser.add_argument("--output", default="", help="Optional output path.")
    parser.add_argument(
        "--capture-method",
        action="append",
        choices=tuple(
            method.method_id for method in available_capture_methods()
        ),
        default=None,
        help="Optional repeatable capture-method ID to include as planning metadata.",
    )
    parser.add_argument(
        "--evidence-bundle-status",
        choices=BUNDLE_STATUSES,
        default="",
        help="Optional metadata-only evidence bundle status.",
    )
    parser.add_argument(
        "--evidence-bundle-label",
        default="",
        help="Optional metadata-only evidence bundle label.",
    )
    parser.add_argument(
        "--evidence-item",
        action="append",
        default=[],
        help="Repeatable metadata-only artifact_id:artifact_format[:capture_method_id] evidence item.",
    )
    parser.add_argument(
        "--evidence-notes",
        default="",
        help="Optional metadata-only evidence bundle notes.",
    )
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
        data = _read_input(args.input) if args.input else {}
        evidence_bundle = _build_cli_evidence_bundle(
            source_url=_optional_string(data, "source_url") if data else "",
            bundle_label=args.evidence_bundle_label,
            status=args.evidence_bundle_status,
            notes=args.evidence_notes,
            item_values=args.evidence_item,
        )
        plan = _build_plan_from_input(
            data,
            capture_method_ids=args.capture_method,
            evidence_bundle=evidence_bundle,
        )
        rendered = render_preservation_backend_plan(
            plan,
            output_format=args.format,
        )
        if args.output:
            write_report_output(args.output, rendered, overwrite=args.overwrite)
        else:
            print(rendered)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
