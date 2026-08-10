from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

MSN_MANUAL_VALIDATION_SCHEMA_VERSION = "msn_source_adapter_manual_validation_v1"
MSN_MANUAL_VALIDATION_TEMPLATE_JSON = "MSN_MANUAL_LIVE_VALIDATION_TEMPLATE.json"
MSN_MANUAL_VALIDATION_RESULT_JSON = "MSN_MANUAL_LIVE_VALIDATION_RESULT.json"
MSN_MANUAL_VALIDATION_RESULT_MD = "MSN_MANUAL_LIVE_VALIDATION_RESULT.md"

STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_NOT_CHECKED = "NOT_CHECKED"

DEFAULT_CHECKS = (
    "article_title_body_visible",
    "publisher_source_credit_visible",
    "comments_top_newest_exported",
    "comments_replies_deleted_votes_profiles_checked",
    "offline_rendered_html_opens",
    "warc_replay_article_visible_partial_ok",
    "strict_wacz_labelled_experimental",
    "media_inventory_created",
    "image_assets_downloaded_or_status_recorded",
    "video_stream_status_recorded",
    "msn_republisher_not_primary_for_external_media",
    "primary_source_statuses_reviewed",
    "total_package_and_final_validation_reports_written",
)


@dataclass(frozen=True)
class MsnManualValidationCheck:
    check_id: str
    status: str = STATUS_NOT_CHECKED
    evidence_path: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnManualValidationResult:
    schema_version: str = MSN_MANUAL_VALIDATION_SCHEMA_VERSION
    source_url: str = ""
    capture_root: str = ""
    checked_by: str = "manual_operator"
    overall_status: str = STATUS_NOT_CHECKED
    checks: tuple[MsnManualValidationCheck, ...] = ()
    blocking_failures: tuple[str, ...] = ()
    manual_review_notes: tuple[str, ...] = ()
    output_paths: Mapping[str, str] = field(default_factory=dict)

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


def _normalise_status(value: Any) -> str:
    text = str(value or STATUS_NOT_CHECKED).strip().upper().replace(" ", "_")
    aliases = {
        "YES": STATUS_PASS,
        "Y": STATUS_PASS,
        "OK": STATUS_PASS,
        "NO": STATUS_FAIL,
        "N": STATUS_FAIL,
        "MISSING": STATUS_FAIL,
        "PARTLY": STATUS_PARTIAL,
        "PARTIAL_OK": STATUS_PARTIAL,
        "UNCHECKED": STATUS_NOT_CHECKED,
        "NOT_CHECKED": STATUS_NOT_CHECKED,
    }
    return aliases.get(text, text if text in {STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL, STATUS_NOT_CHECKED} else STATUS_NOT_CHECKED)


def make_msn_manual_validation_template(*, source_url: str = "", capture_root: str = "") -> Mapping[str, Any]:
    return {
        "schema_version": MSN_MANUAL_VALIDATION_SCHEMA_VERSION,
        "source_url": source_url,
        "capture_root": capture_root,
        "checked_by": "manual_operator",
        "manual_review_notes": [
            "Do not claim MSN is the primary/original source for republished articles or externally credited media unless separately located.",
            "Record WACZ success only after manual ReplayWeb validation; strict WACZ may remain experimental/possibly unsupported.",
        ],
        "checks": [
            {"check_id": check_id, "status": STATUS_NOT_CHECKED, "evidence_path": "", "note": ""}
            for check_id in DEFAULT_CHECKS
        ],
    }


def _checks_from_mapping(data: Mapping[str, Any]) -> tuple[MsnManualValidationCheck, ...]:
    raw_checks = data.get("checks") or []
    checks: list[MsnManualValidationCheck] = []
    if isinstance(raw_checks, Mapping):
        raw_checks = [{"check_id": key, **(value if isinstance(value, Mapping) else {"status": value})} for key, value in raw_checks.items()]
    if isinstance(raw_checks, list):
        for item in raw_checks:
            if not isinstance(item, Mapping):
                continue
            check_id = str(item.get("check_id") or item.get("id") or "").strip()
            if not check_id:
                continue
            checks.append(
                MsnManualValidationCheck(
                    check_id=check_id,
                    status=_normalise_status(item.get("status")),
                    evidence_path=str(item.get("evidence_path") or item.get("path") or ""),
                    note=str(item.get("note") or ""),
                )
            )
    seen = {check.check_id for check in checks}
    for check_id in DEFAULT_CHECKS:
        if check_id not in seen:
            checks.append(MsnManualValidationCheck(check_id=check_id))
    return tuple(checks)


def build_msn_manual_validation_result(data: Mapping[str, Any]) -> MsnManualValidationResult:
    checks = _checks_from_mapping(data)
    blocking = tuple(check.check_id for check in checks if check.status == STATUS_FAIL)
    if blocking:
        overall = STATUS_FAIL
    elif any(check.status == STATUS_NOT_CHECKED for check in checks):
        overall = STATUS_PARTIAL
    elif any(check.status == STATUS_PARTIAL for check in checks):
        overall = STATUS_PARTIAL
    else:
        overall = STATUS_PASS
    notes_raw = data.get("manual_review_notes") or data.get("notes") or ()
    if isinstance(notes_raw, str):
        notes = (notes_raw,)
    elif isinstance(notes_raw, list):
        notes = tuple(str(item) for item in notes_raw if str(item).strip())
    else:
        notes = ()
    return MsnManualValidationResult(
        source_url=str(data.get("source_url") or ""),
        capture_root=str(data.get("capture_root") or data.get("root") or ""),
        checked_by=str(data.get("checked_by") or "manual_operator"),
        overall_status=overall,
        checks=checks,
        blocking_failures=blocking,
        manual_review_notes=notes,
    )


def render_msn_manual_validation_markdown(result: MsnManualValidationResult | Mapping[str, Any]) -> str:
    data = result.to_dict() if hasattr(result, "to_dict") else result
    lines = [
        "# MSN Manual Live Validation Result",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Source URL: `{data.get('source_url') or 'not supplied'}`",
        f"Capture root: `{data.get('capture_root') or 'not supplied'}`",
        f"Checked by: `{data.get('checked_by') or 'manual_operator'}`",
        f"Overall status: `{data.get('overall_status') or STATUS_NOT_CHECKED}`",
        "",
        "## Checks",
        "",
    ]
    for check in data.get("checks") or []:
        if not isinstance(check, Mapping):
            continue
        lines.append(f"- `{check.get('check_id')}`: `{check.get('status')}`")
        if check.get("evidence_path"):
            lines.append(f"  - Evidence: `{check.get('evidence_path')}`")
        if check.get("note"):
            lines.append(f"  - Note: {check.get('note')}")
    if data.get("blocking_failures"):
        lines.extend(["", "## Blocking failures", ""])
        for failure in data.get("blocking_failures") or []:
            lines.append(f"- `{failure}`")
    if data.get("manual_review_notes"):
        lines.extend(["", "## Manual review notes", ""])
        for note in data.get("manual_review_notes") or []:
            lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Source-role reminder",
            "",
            "MSN, The Independent, a visible Google Street View credit, an agency line, and an unknown original uploader are separate source-chain facts. This validation result records whether the operator checked that separation; it does not automatically decide primary sourcing for every claim.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_msn_manual_validation_template(output_path: str | Path, *, source_url: str = "", capture_root: str = "") -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make_msn_manual_validation_template(source_url=source_url, capture_root=capture_root), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def write_msn_manual_validation_result(input_path: str | Path, *, output_dir: str | Path = "") -> dict[str, str]:
    source = Path(input_path)
    data = json.loads(source.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(data, Mapping):
        raise ValueError("Manual validation input must be a JSON object")
    result = build_msn_manual_validation_result(data)
    out = Path(output_dir) if output_dir else source.parent
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / MSN_MANUAL_VALIDATION_RESULT_JSON
    md_path = out / MSN_MANUAL_VALIDATION_RESULT_MD
    paths = {"manual_validation_json": str(json_path), "manual_validation_markdown": str(md_path)}
    result_with_paths = MsnManualValidationResult(
        source_url=result.source_url,
        capture_root=result.capture_root,
        checked_by=result.checked_by,
        overall_status=result.overall_status,
        checks=result.checks,
        blocking_failures=result.blocking_failures,
        manual_review_notes=result.manual_review_notes,
        output_paths=paths,
    )
    json_path.write_text(json.dumps(result_with_paths.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_msn_manual_validation_markdown(result_with_paths), encoding="utf-8")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or render MSN manual live validation records.")
    sub = parser.add_subparsers(dest="command", required=True)
    template = sub.add_parser("template", help="Write a manual validation template JSON.")
    template.add_argument("output", help="Output template JSON path.")
    template.add_argument("--source-url", default="")
    template.add_argument("--capture-root", default="")
    result = sub.add_parser("result", help="Render a completed manual validation JSON into result JSON/Markdown.")
    result.add_argument("input", help="Completed manual validation JSON path.")
    result.add_argument("--output-dir", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "template":
        path = write_msn_manual_validation_template(args.output, source_url=args.source_url, capture_root=args.capture_root)
        print(f"MSN manual validation template: {path}")
        return 0
    paths = write_msn_manual_validation_result(args.input, output_dir=args.output_dir)
    print(f"MSN manual validation JSON: {paths['manual_validation_json']}")
    print(f"MSN manual validation Markdown: {paths['manual_validation_markdown']}")
    status = build_msn_manual_validation_result(json.loads(Path(args.input).read_text(encoding="utf-8", errors="replace"))).overall_status
    return 0 if status != STATUS_FAIL else 2


if __name__ == "__main__":
    raise SystemExit(main())
