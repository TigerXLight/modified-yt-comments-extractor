"""HOME repository and classification-path helpers for Profile/Media Database.

The HOME database is classification-driven.  A case/event is not simply a
person; it is a classified action/event/time/source context, for example:
Sexual offences / Rape / Adults / Direct / Non-religious or not identified /
June 2026 / Belfast Telegraph / article folder.

This module parses explicit path text only.  It does not scan the filesystem.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROFILE_MEDIA_HOME_REPOSITORY_SCHEMA_VERSION = "profile-media-home-repository-v76k2"

SOURCE_BUCKETS = {
    "Articles",
    "Social Media/Online",
    "Social Media/Offline",
    "Internal Media",
    "Profiles",
    "People",
    "Reference Extants",
}


@dataclass(frozen=True)
class HomeClassificationPath:
    raw_path: str
    normalized_path: str
    classification_parts: tuple[str, ...]
    publisher_or_platform: str = ""
    month_or_date: str = ""
    event_or_source_title: str = ""
    source_bucket: str = ""
    case_is_person_only: bool = False
    case_designation_rule: str = "classification_action_time_source_context"
    schema_version: str = PROFILE_MEDIA_HOME_REPOSITORY_SCHEMA_VERSION
    folder_scan_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _split_path(path: object) -> list[str]:
    text = str(path or "").replace("\\", "/").strip().strip("/")
    return [part.strip() for part in text.split("/") if part.strip()]


def parse_home_classification_path(path: object) -> HomeClassificationPath:
    parts = _split_path(path)
    normalized = "/".join(parts)
    source_bucket = ""
    publisher = ""
    month = ""
    title = parts[-1] if parts else ""

    # Existing source layout inside a case/root.
    if "Sources" in parts:
        idx = parts.index("Sources")
        after = parts[idx + 1 :]
        if len(after) >= 2 and after[0] == "Social Media":
            source_bucket = "/".join(after[:2])
            title = after[2] if len(after) >= 3 else title
        elif after:
            source_bucket = after[0]
            title = after[1] if len(after) >= 2 else title

    # User's hand-made taxonomy layout usually has publisher then event/article folder at the leaf.
    if not source_bucket and len(parts) >= 4:
        publisher = parts[-2]
        title = parts[-1]
        month = next((part for part in reversed(parts[:-2]) if any(ch.isdigit() for ch in part)), "")
    elif len(parts) >= 3:
        publisher = parts[-2]

    case_is_person_only = len(parts) == 1 or (len(parts) == 2 and parts[0].lower() in {"profiles", "people"})
    return HomeClassificationPath(
        raw_path=str(path or ""),
        normalized_path=normalized,
        classification_parts=tuple(parts),
        publisher_or_platform=publisher,
        month_or_date=month,
        event_or_source_title=title,
        source_bucket=source_bucket,
        case_is_person_only=case_is_person_only,
    )


def render_home_classification_path(parsed: HomeClassificationPath) -> str:
    lines = [
        "Profile/Media HOME Classification Path",
        f"Path: {parsed.normalized_path}",
        f"Case rule: {parsed.case_designation_rule}",
        f"Person-only case: {parsed.case_is_person_only}",
        f"Publisher/platform: {parsed.publisher_or_platform or '(not isolated)'}",
        f"Date/month: {parsed.month_or_date or '(not isolated)'}",
        f"Event/source title: {parsed.event_or_source_title or '(none)'}",
        f"Source bucket: {parsed.source_bucket or '(taxonomy path)'}",
        f"Folder scan performed: {parsed.folder_scan_performed}",
        f"Automatic classification performed: {parsed.automatic_classification_performed}",
    ]
    return "\n".join(lines)
