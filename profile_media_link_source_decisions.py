"""JSONL decisions for Profile/Media link source objects.

Decisions are review events over deterministic link source objects. They do not
change claim-span roles or media-source statement counts.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "profile-media-link-source-decisions-v83c-20260828"
VALID_ROLES = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "LOCATOR"}
VALID_STATUSES = {"accepted", "rejected", "ignored", "changed_role", "note_only"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _role(value: object) -> str:
    role = _clean(value).upper()
    return role if role in VALID_ROLES else ""


def link_source_object_key(record: Mapping[str, Any]) -> str:
    """Return a stable key for matching decision events to a link object."""

    base = _clean(
        record.get("archive_target_url")
        or record.get("preservation_for_url")
        or record.get("normalised_url")
        or record.get("url")
    ).casefold()
    discriminator = "|".join(
        part.casefold()
        for part in (
            _clean(record.get("nearby_heading")),
            _clean(record.get("list_label")),
            _clean(record.get("source_path")),
        )
        if part
    )
    if not base:
        base = _clean(record.get("raw_url")).casefold()
    digest = hashlib.sha1(discriminator.encode("utf-8")).hexdigest()[:12] if discriminator else "default"
    return f"{base}|{digest}"


def normalise_link_source_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise one decision event for JSONL persistence."""

    selected_role = _role(decision.get("selected_role"))
    status = _clean(decision.get("decision_status")).casefold()
    if status == "ignored":
        # V83D/R34 wording uses "Ignore from active evidence" in the UI while
        # preserving the existing JSONL/storage meaning: inactive evidence rows
        # are stored as rejected for compatibility with previous decisions.
        status = "rejected"
    if status not in VALID_STATUSES:
        status = "changed_role" if selected_role else "note_only"
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    link_key = _clean(decision.get("link_object_key"))
    if not link_key:
        link_key = link_source_object_key(decision)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _clean(decision.get("created_at")) or now,
        "decision_id": _clean(decision.get("decision_id"))
        or hashlib.sha1(f"{link_key}|{now}|{status}|{selected_role}|{_clean(decision.get('decision_note'))}".encode("utf-8")).hexdigest()[:16],
        "link_object_key": link_key,
        "url": _clean(decision.get("url")),
        "normalised_url": _clean(decision.get("normalised_url")),
        "archive_target_url": _clean(decision.get("archive_target_url") or decision.get("preservation_for_url")),
        "selected_role": selected_role,
        "selected_source_object_type": _clean(decision.get("selected_source_object_type") or decision.get("source_object_type")),
        "selected_source_relation_type": _clean(decision.get("selected_source_relation_type") or decision.get("source_relation_type")),
        "decision_status": status,
        "decision_note": _clean(decision.get("decision_note")),
        "previous_role": _clean(decision.get("previous_role") or decision.get("claim_specific_role") or decision.get("default_link_role")),
        "previous_reason": _clean(decision.get("previous_reason") or decision.get("role_reason")),
        "source_label": _clean(decision.get("source_label")),
        "source_path": _clean(decision.get("source_path")),
        "line_number": decision.get("line_number") if isinstance(decision.get("line_number"), int) else None,
    }
    return payload


def load_link_source_decisions(path: str | Path) -> list[dict[str, Any]]:
    decision_path = Path(path)
    if not decision_path.is_file():
        return []
    output: list[dict[str, Any]] = []
    for line in decision_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, Mapping):
            output.append(normalise_link_source_decision(row))
    return output


def append_link_source_decision(path: str | Path, decision: Mapping[str, Any]) -> dict[str, Any]:
    decision_path = Path(path)
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    payload = normalise_link_source_decision(decision)
    with decision_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def apply_link_source_decisions(
    objects: Iterable[Mapping[str, Any]],
    decisions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, Mapping):
            continue
        row = normalise_link_source_decision(decision)
        key = _clean(row.get("link_object_key"))
        if key:
            latest[key] = row

    output: list[dict[str, Any]] = []
    for obj in objects:
        if not isinstance(obj, Mapping):
            continue
        item = dict(obj)
        key = _clean(item.get("link_source_row_instance_key") or link_source_object_key(item))
        item.setdefault("link_object_key", key)
        item["link_source_decision_applied"] = False
        decision = latest.get(key) or latest.get(link_source_object_key(item))
        if decision is None:
            output.append(item)
            continue
        item["original_claim_specific_role"] = _clean(item.get("claim_specific_role"))
        item["original_default_link_role"] = _clean(item.get("default_link_role"))
        item["original_role_reason"] = _clean(item.get("role_reason"))
        item["link_source_decision_status"] = _clean(decision.get("decision_status"))
        item["link_source_decision_role"] = _clean(decision.get("selected_role"))
        item["link_source_decision_note"] = _clean(decision.get("decision_note"))
        item["link_source_decision_applied"] = True
        if decision.get("selected_role"):
            item["claim_specific_role"] = decision["selected_role"]
            item["default_link_role"] = decision["selected_role"]
        if decision.get("selected_source_object_type"):
            item["source_object_type"] = decision["selected_source_object_type"]
        if decision.get("selected_source_relation_type"):
            item["source_relation_type"] = decision["selected_source_relation_type"]
        if decision.get("decision_status") == "rejected":
            item["link_source_rejected"] = True
            item["active_link_source_evidence"] = False
        output.append(item)
    return output


def build_link_source_decision_summary(objects: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    role_counts = {role: 0 for role in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "LOCATOR")}
    active_role_counts = {role: 0 for role in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "LOCATOR")}
    status_counts = {status: 0 for status in ("accepted", "rejected", "changed_role", "note_only", "undecided")}
    source_object_groups: dict[str, dict[str, Any]] = {}
    total = 0
    active_evidence = 0
    locator_count = 0
    for obj in objects:
        if not isinstance(obj, Mapping):
            continue
        total += 1
        role = _role(obj.get("claim_specific_role") or obj.get("default_link_role")) or "UNKNOWN"
        role_counts[role] += 1
        rejected = bool(obj.get("link_source_rejected")) or _clean(obj.get("link_source_decision_status")).casefold() == "rejected"
        status = _clean(obj.get("link_source_decision_status")).casefold() or "undecided"
        if status not in status_counts:
            status = "undecided"
        status_counts[status] += 1
        if role == "LOCATOR" or bool(obj.get("locator_only")):
            locator_count += 1
        if not rejected:
            active_role_counts[role] += 1
            if role != "LOCATOR" and not bool(obj.get("locator_only")):
                active_evidence += 1
        group_key = _clean(obj.get("source_object_group_key") or obj.get("archive_target_url") or obj.get("preservation_for_url") or obj.get("normalised_url") or obj.get("url"))
        if group_key:
            group = source_object_groups.setdefault(
                group_key.casefold(),
                {
                    "group_key": group_key,
                    "source_object_count": 0,
                    "locator_count": 0,
                    "active_evidence_count": 0,
                    "urls": [],
                },
            )
            group["source_object_count"] += 1
            group["urls"].append(_clean(obj.get("url") or obj.get("normalised_url")))
            if role == "LOCATOR" or bool(obj.get("locator_only")):
                group["locator_count"] += 1
            elif not rejected:
                group["active_evidence_count"] += 1
    return {
        "schema_version": "profile-media-link-source-decision-summary-v83c",
        "object_count": total,
        "active_evidence_count": active_evidence,
        "locator_count": locator_count,
        "role_counts": role_counts,
        "active_role_counts": active_role_counts,
        "decision_status_counts": status_counts,
        "source_object_group_count": len(source_object_groups),
        "source_object_groups": list(source_object_groups.values()),
        "link_counts_are_separate_from_media_source_statement_counts": True,
    }
