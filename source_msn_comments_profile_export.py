from __future__ import annotations

import csv
import datetime as _dt
import html
import json
import re
from collections import OrderedDict
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit


MSN_COMMENTS_PROFILE_EXPORT_SCHEMA_VERSION = "msn_comments_profile_export_v1"
MSN_COMMENTS_PROFILE_EXPORTER = "msn_comments_v35_profile_stats_export"
MSN_DELETED_PLACEHOLDER_TEXT = "This comment was deleted because it didn't meet our guidelines"
PRIMARY_SOURCE_LOCATED = "PRIMARY_SOURCE_LOCATED"
PRIMARY_ORIGINAL_AUTHORED_SOURCE = "PRIMARY_ORIGINAL_AUTHORED_SOURCE"
COMMENT_SOURCE_ROLE_SCOPE = "limited_to_comment_or_reply_text_authored_by_the_commenter_at_capture_time"

CLAIM_SOURCE_ROLE_FIELDS = (
    "claim_text",
    "claim_type",
    "claim_source_role",
    "source_role_scope",
    "source_role_limitation",
    "authored_or_posted_at",
    "captured_at_utc",
    "event_time_or_claim_time",
    "temporal_gap_note",
    "currentness_status",
    "primary_source_status",
    "source_chain_gap",
    "closed_loop_reporting_flag",
    "first_uploader_known",
    "first_uploader_url",
    "first_seen_by_user_utc",
    "media_acquired_at_utc",
    "file_obtained_delay_note",
    "publisher_framing_summary",
    "removed_or_missing_context_note",
    "identity_claim_basis",
    "appearance_claim_basis",
    "forensic_claim_basis",
    "family_or_authority_claim_basis",
    "open_source_media_available",
    "corroborating_sources",
    "contradicting_sources",
    "verification_notes",
)
MANUAL_EVIDENCE_NOTE_FIELDS = (
    "source_role",
    "publisher_name",
    "publisher_framing_summary",
    "visible_source_credit",
    "claimed_original_source",
    "original_source_url",
    "original_author_or_uploader",
    "same_media_seen_on_other_urls",
    "source_author_correction_url",
    "source_author_correction_text_or_path",
    "notes_on_context_dispute",
    "manual_source_note",
)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    return value


def clean_text(value: Any) -> str:
    text = str(value or "").replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", clean_text(value)).strip()


def number_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace(",", "")
    if text in ("", "None", "null"):
        return ""
    if text in ("-", "\u2013", "\u2014"):
        return "0"
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def canonicalize_profile_url(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parts = urlsplit(text)
    if not parts.scheme or not parts.netloc:
        return text.split("?", 1)[0].split("#", 1)[0]
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def extract_profile_cid(url_or_cid: Any) -> str:
    text = str(url_or_cid or "")
    match = re.search(r"(cid-[A-Za-z0-9_-]+)", text)
    return match.group(1) if match else ""


def walk_comment_items(items: Iterable[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for item in items or []:
        yield item
        yield from walk_comment_items(item.get("replies") or [])


def count_comment_items(items: Iterable[Mapping[str, Any]]) -> int:
    return sum(1 + count_comment_items(item.get("replies") or []) for item in items or [])


def parse_profile_card_text_for_author(text: Any, author: Any) -> dict[str, str] | None:
    body = compact_text(text)
    name = compact_text(author)
    if not body or not name or name == "Unknown":
        return None
    pattern = (
        r"(?<!\w)"
        + re.escape(name)
        + r"\.?\s+Comments\s+([\d,]+|-)\s+Likes\s+([\d,]+|-)\s+Followers\s+([\d,]+|-)"
    )
    match = re.search(pattern, body, re.IGNORECASE)
    if not match:
        return None
    return {
        "account_comments": number_text(match.group(1)),
        "account_likes": number_text(match.group(2)),
        "account_followers": number_text(match.group(3)),
        "profile_stats_method": "profile_card_text",
    }


def _nested_user_stats(obj: Any, *, author: str = "", profile_cid: str = "") -> dict[str, str] | None:
    found: list[dict[str, str]] = []

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            ident = str(value.get("id") or value.get("author_profile_cid") or "")
            name = str(value.get("primaryName") or value.get("name") or "")
            has_counts = any(
                key in value
                for key in (
                    "likesCount",
                    "postsCount",
                    "followersCount",
                    "reactionsCount",
                    "commentSummary",
                    "reactionSummary",
                    "followSummary",
                )
            )
            matches_identity = bool(
                (profile_cid and ident == profile_cid)
                or (author and name and compact_text(name).lower() == compact_text(author).lower())
            )
            if matches_identity and has_counts:
                comments = value.get("postsCount")
                likes = value.get("likesCount", value.get("reactionsCount"))
                followers = value.get("followersCount")
                comment_summary = value.get("commentSummary") if isinstance(value.get("commentSummary"), Mapping) else {}
                reaction_summary = value.get("reactionSummary") if isinstance(value.get("reactionSummary"), Mapping) else {}
                follow_summary = value.get("followSummary") if isinstance(value.get("followSummary"), Mapping) else {}
                if comments is None:
                    comments = comment_summary.get("totalCount")
                if likes is None:
                    likes = reaction_summary.get("totalCount")
                if followers is None:
                    for sub in follow_summary.get("subFollowSummaries") or []:
                        if isinstance(sub, Mapping) and sub.get("type") in ("FollowBy", "Follower", "Followers"):
                            followers = sub.get("totalCount")
                            break
                    if followers is None:
                        followers = follow_summary.get("totalCount")
                candidate = {
                    "account_comments": number_text(comments),
                    "account_likes": number_text(likes),
                    "account_followers": number_text(followers),
                    "profile_stats_method": "embedded_user_object",
                }
                if candidate["account_comments"] or candidate["account_likes"] or candidate["account_followers"]:
                    found.append(candidate)
            for key, child in value.items():
                if key in ("primaryAvatar", "avatarUrl", "email"):
                    continue
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(obj)
    found.sort(
        key=lambda item: sum(bool(item[key]) for key in ("account_comments", "account_likes", "account_followers")),
        reverse=True,
    )
    return found[0] if found else None


def profile_stats_from_item(item: Mapping[str, Any]) -> dict[str, str]:
    existing = {
        "account_comments": number_text(item.get("account_comments")),
        "account_likes": number_text(item.get("account_likes")),
        "account_followers": number_text(item.get("account_followers")),
        "profile_stats_method": "existing_item_fields",
    }
    if existing["account_comments"] or existing["account_likes"] or existing["account_followers"]:
        return existing
    author = str(item.get("author") or "")
    profile_cid = str(item.get("author_profile_cid") or extract_profile_cid(item.get("author_profile_url")))
    parsed = parse_profile_card_text_for_author(item.get("profile_card_text"), author)
    if parsed:
        return parsed
    for text in (item.get("vote_debug") or {}).get("social_texts", []) if isinstance(item.get("vote_debug"), Mapping) else []:
        parsed = parse_profile_card_text_for_author(text, author)
        if parsed:
            return parsed
    nested = _nested_user_stats(item.get("_header_for_hover"), author=author, profile_cid=profile_cid)
    if nested:
        return nested
    nested = _nested_user_stats(item.get("debug"), author=author, profile_cid=profile_cid)
    if nested:
        return nested
    return {
        "account_comments": "",
        "account_likes": "",
        "account_followers": "",
        "profile_stats_method": "not_found",
    }


def default_msn_comment_source_role_metadata(item: Mapping[str, Any]) -> OrderedDict[str, Any]:
    text = clean_text(item.get("text"))
    return OrderedDict(
        (
            ("claim_text", text),
            ("claim_type", "comment_authorship"),
            ("claim_source_role", PRIMARY_ORIGINAL_AUTHORED_SOURCE),
            ("source_role_scope", COMMENT_SOURCE_ROLE_SCOPE),
            (
                "source_role_limitation",
                "The commenter's own comment/reply is primary/original authored evidence only for authorship of this captured text; it is not automatically primary evidence for real-world incident claims inside the comment.",
            ),
            ("authored_or_posted_at", str(item.get("date") or item.get("published_at") or item.get("posted_at") or "")),
            ("captured_at_utc", str(item.get("captured_at_utc") or "")),
            ("event_time_or_claim_time", ""),
            ("temporal_gap_note", ""),
            ("currentness_status", "UNKNOWN"),
            ("primary_source_status", PRIMARY_SOURCE_LOCATED),
            ("source_chain_gap", False),
            ("closed_loop_reporting_flag", False),
            ("first_uploader_known", False),
            ("first_uploader_url", ""),
            ("first_seen_by_user_utc", ""),
            ("media_acquired_at_utc", ""),
            ("file_obtained_delay_note", ""),
            ("publisher_framing_summary", ""),
            ("source_role", PRIMARY_ORIGINAL_AUTHORED_SOURCE),
            ("publisher_name", ""),
            ("visible_source_credit", ""),
            ("claimed_original_source", ""),
            ("original_source_url", ""),
            ("original_author_or_uploader", ""),
            ("same_media_seen_on_other_urls", []),
            ("source_author_correction_url", ""),
            ("source_author_correction_text_or_path", ""),
            ("notes_on_context_dispute", ""),
            ("manual_source_note", ""),
            ("removed_or_missing_context_note", ""),
            ("identity_claim_basis", ""),
            ("appearance_claim_basis", ""),
            ("forensic_claim_basis", ""),
            ("family_or_authority_claim_basis", ""),
            ("open_source_media_available", ""),
            ("corroborating_sources", []),
            ("contradicting_sources", []),
            ("verification_notes", "MSN comments/profile exporter default; incident-level claims still require operator review."),
        )
    )


def normalize_comment_item(item: Mapping[str, Any]) -> OrderedDict[str, Any]:
    stats = profile_stats_from_item(item)
    raw_profile_url = str(
        item.get("author_profile_url_raw")
        or item.get("author_profile_href_raw_attr")
        or item.get("author_profile_url")
        or ""
    )
    canonical_profile = canonicalize_profile_url(item.get("author_profile_url") or raw_profile_url)
    profile_cid = str(item.get("author_profile_cid") or extract_profile_cid(canonical_profile or raw_profile_url))
    text = clean_text(item.get("text"))
    deleted = bool(item.get("deleted_placeholder") or MSN_DELETED_PLACEHOLDER_TEXT in text)
    out: OrderedDict[str, Any] = OrderedDict()
    out["source_comment_id"] = str(item.get("source_comment_id") or item.get("id") or "")
    out["type"] = str(item.get("type") or item.get("comment_type") or "Parent Comment")
    out["author"] = str(item.get("author") or "Unknown")
    out["date"] = str(item.get("date") or item.get("published_at") or item.get("posted_at") or "")
    out["author_profile_url"] = canonical_profile
    out["author_profile_url_raw"] = raw_profile_url
    out["author_profile_href_raw_attr"] = str(item.get("author_profile_href_raw_attr") or raw_profile_url)
    out["author_profile_cid"] = profile_cid
    out["account_comments"] = stats.get("account_comments", "")
    out["account_likes"] = stats.get("account_likes", "")
    out["account_followers"] = stats.get("account_followers", "")
    out["profile_stats_status"] = (
        "found" if out["account_comments"] or out["account_likes"] or out["account_followers"] else "not_found"
    )
    out["profile_stats_method"] = stats.get("profile_stats_method", "")
    out["likes"] = number_text(item.get("likes"))
    out["dislikes"] = number_text(item.get("dislikes"))
    out["text"] = text
    out["deleted_placeholder"] = deleted
    out["source_filter"] = str(item.get("source_filter") or item.get("sort_filter") or "")
    out["capture_source_note"] = str(item.get("capture_source_note") or "")
    out["source_role_metadata"] = default_msn_comment_source_role_metadata(out)
    out["replies"] = [normalize_comment_item(reply) for reply in item.get("replies") or []]
    return out


def comment_item_key(item: Mapping[str, Any]) -> str:
    if item.get("source_comment_id"):
        return str(item["source_comment_id"])
    return compact_text(
        "|".join(
            [
                str(item.get("type") or ""),
                str(item.get("author") or ""),
                str(item.get("date") or ""),
                str(item.get("text") or "")[:240],
            ]
        )
    ).lower()


def _merge_replies(existing: OrderedDict[str, Any], incoming: Mapping[str, Any]) -> None:
    by_key: OrderedDict[str, OrderedDict[str, Any]] = OrderedDict(
        (comment_item_key(reply), reply) for reply in existing.get("replies") or []
    )
    for reply in incoming.get("replies") or []:
        key = comment_item_key(reply)
        if key in by_key:
            merge_comment_item(by_key[key], reply)
        else:
            by_key[key] = OrderedDict(reply)
    existing["replies"] = list(by_key.values())


def merge_comment_item(existing: OrderedDict[str, Any], incoming: Mapping[str, Any]) -> OrderedDict[str, Any]:
    _merge_replies(existing, incoming)
    for field in (
        "author",
        "date",
        "author_profile_url",
        "author_profile_url_raw",
        "author_profile_href_raw_attr",
        "author_profile_cid",
        "account_comments",
        "account_likes",
        "account_followers",
        "likes",
        "dislikes",
        "source_filter",
        "capture_source_note",
    ):
        if not existing.get(field) and incoming.get(field):
            existing[field] = incoming[field]
    if len(str(incoming.get("text") or "")) > len(str(existing.get("text") or "")):
        existing["text"] = incoming.get("text", "")
        existing["source_role_metadata"] = default_msn_comment_source_role_metadata(existing)
    if incoming.get("profile_stats_status") == "found":
        existing["profile_stats_status"] = "found"
        if incoming.get("profile_stats_method"):
            existing["profile_stats_method"] = incoming.get("profile_stats_method")
    existing["deleted_placeholder"] = bool(existing.get("deleted_placeholder") or incoming.get("deleted_placeholder"))
    return existing


def _assign_human_ids(comments: Sequence[OrderedDict[str, Any]]) -> None:
    for index, comment in enumerate(comments, 1):
        comment["human_id"] = f"C{index:04d}"

        def assign_replies(replies: Sequence[OrderedDict[str, Any]], parent_id: str) -> None:
            for reply_index, reply in enumerate(replies, 1):
                reply["human_id"] = f"R{reply_index:04d}"
                reply["parent_human_id"] = parent_id
                assign_replies(reply.get("replies") or [], reply["human_id"])

        assign_replies(comment.get("replies") or [], comment["human_id"])


def _profile_key(item: Mapping[str, Any]) -> str:
    return str(item.get("author_profile_cid") or item.get("author_profile_url") or item.get("author") or "")


def build_profiles(comments: Sequence[Mapping[str, Any]]) -> list[OrderedDict[str, Any]]:
    profiles: OrderedDict[str, OrderedDict[str, Any]] = OrderedDict()
    for item in walk_comment_items(comments):
        if item.get("deleted_placeholder") or item.get("author") == "Unknown":
            continue
        key = _profile_key(item)
        if not key:
            continue
        if key not in profiles:
            profiles[key] = OrderedDict(
                author=item.get("author", ""),
                profile_cid=item.get("author_profile_cid", ""),
                canonical_url=item.get("author_profile_url", ""),
                raw_urls=[],
                account_comments=item.get("account_comments", ""),
                account_likes=item.get("account_likes", ""),
                account_followers=item.get("account_followers", ""),
                profile_stats_status=item.get("profile_stats_status", ""),
                profile_stats_method=item.get("profile_stats_method", ""),
                appearances=0,
                item_ids=[],
            )
        profile = profiles[key]
        profile["appearances"] += 1
        if item.get("human_id"):
            profile["item_ids"].append(item["human_id"])
        raw_url = item.get("author_profile_url_raw")
        if raw_url and raw_url not in profile["raw_urls"]:
            profile["raw_urls"].append(raw_url)
        for profile_field, item_field in (
            ("account_comments", "account_comments"),
            ("account_likes", "account_likes"),
            ("account_followers", "account_followers"),
            ("canonical_url", "author_profile_url"),
            ("profile_cid", "author_profile_cid"),
            ("profile_stats_method", "profile_stats_method"),
        ):
            if not profile.get(profile_field) and item.get(item_field):
                profile[profile_field] = item[item_field]
        profile["profile_stats_status"] = (
            "found"
            if profile.get("account_comments") or profile.get("account_likes") or profile.get("account_followers")
            else "not_found"
        )
    return sorted(profiles.values(), key=lambda profile: str(profile.get("author") or "").lower())


def propagate_profile_stats(comments: Sequence[OrderedDict[str, Any]], profiles: Sequence[Mapping[str, Any]]) -> None:
    by_key: dict[str, Mapping[str, Any]] = {}
    for profile in profiles:
        for key in (profile.get("profile_cid"), profile.get("canonical_url"), profile.get("author")):
            if key:
                by_key[str(key)] = profile
    for item in walk_comment_items(comments):
        profile = by_key.get(_profile_key(item)) or by_key.get(str(item.get("author_profile_url") or ""))
        if not profile:
            continue
        for field in ("account_comments", "account_likes", "account_followers"):
            if profile.get(field):
                item[field] = profile[field]
        if profile.get("profile_stats_method"):
            item["profile_stats_method"] = profile["profile_stats_method"]
        item["profile_stats_status"] = (
            "found" if item.get("account_comments") or item.get("account_likes") or item.get("account_followers") else "not_found"
        )


@dataclass(frozen=True)
class MsnCommentsProfileExport:
    source_url: str
    title: str
    comments: tuple[Mapping[str, Any], ...]
    profiles: tuple[Mapping[str, Any], ...]
    input_files: tuple[Mapping[str, Any], ...] = ()
    input_sorts: tuple[str, ...] = ()
    shown_msn_count: int = 0
    schema_version: str = MSN_COMMENTS_PROFILE_EXPORT_SCHEMA_VERSION
    exporter: str = MSN_COMMENTS_PROFILE_EXPORTER

    @property
    def parents_captured(self) -> int:
        return len(self.comments)

    @property
    def items_captured(self) -> int:
        return count_comment_items(self.comments)

    @property
    def deleted_placeholders(self) -> int:
        return sum(1 for item in walk_comment_items(self.comments) if item.get("deleted_placeholder"))

    @property
    def items_with_comment_votes(self) -> int:
        return sum(1 for item in walk_comment_items(self.comments) if item.get("likes") or item.get("dislikes"))

    @property
    def profiles_with_account_stats(self) -> int:
        return sum(1 for profile in self.profiles if profile.get("profile_stats_status") == "found")

    def to_dict(self, *, generated_at: str = "") -> dict[str, Any]:
        return {
            "comments": _value_for_dict(list(self.comments)),
            "deleted_placeholders": self.deleted_placeholders,
            "exporter": self.exporter,
            "generated_at": generated_at,
            "input_files": _value_for_dict(list(self.input_files)),
            "input_sorts": list(self.input_sorts),
            "items_captured": self.items_captured,
            "items_with_comment_votes": self.items_with_comment_votes,
            "parents_captured": self.parents_captured,
            "profiles": _value_for_dict(list(self.profiles)),
            "profiles_captured": len(self.profiles),
            "profiles_with_account_stats": self.profiles_with_account_stats,
            "schema_version": self.schema_version,
            "shown_msn_count": self.shown_msn_count,
            "source_url": self.source_url,
            "title": self.title,
        }


def build_msn_comments_profile_export(captures: Sequence[Mapping[str, Any]]) -> MsnCommentsProfileExport:
    merged: OrderedDict[str, OrderedDict[str, Any]] = OrderedDict()
    input_files: list[Mapping[str, Any]] = []
    input_sorts: list[str] = []
    title = ""
    source_url = ""
    shown_count = 0
    for index, capture in enumerate(captures, 1):
        title = title or str(capture.get("title") or "")
        source_url = source_url or str(capture.get("source_url") or "")
        sort_filter = str(capture.get("sort_filter") or capture.get("filter") or "")
        if sort_filter and sort_filter not in input_sorts:
            input_sorts.append(sort_filter)
        shown_count = max(shown_count, int(capture.get("shown_msn_count") or capture.get("declared_comment_count") or 0))
        input_files.append(
            {
                "file": str(capture.get("file") or f"capture_{index}"),
                "sort_filter": sort_filter,
                "parents": len(capture.get("comments") or []),
                "items_captured": capture.get("items_captured") or count_comment_items(capture.get("comments") or []),
            }
        )
        for raw_item in capture.get("comments") or []:
            item = normalize_comment_item(raw_item)
            item["source_filter"] = item.get("source_filter") or sort_filter
            key = comment_item_key(item)
            if key in merged:
                merge_comment_item(merged[key], item)
            else:
                merged[key] = item
    comments = list(merged.values())
    _assign_human_ids(comments)
    profiles = build_profiles(comments)
    propagate_profile_stats(comments, profiles)
    profiles = build_profiles(comments)
    return MsnCommentsProfileExport(
        source_url=source_url,
        title=title,
        comments=tuple(comments),
        profiles=tuple(profiles),
        input_files=tuple(input_files),
        input_sorts=tuple(input_sorts),
        shown_msn_count=shown_count,
    )


def load_msn_comments_captures(paths: Sequence[str | Path]) -> list[Mapping[str, Any]]:
    captures = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, Mapping):
            enriched = dict(data)
            enriched.setdefault("file", Path(path).name)
            captures.append(enriched)
    return captures


def compact_comment_block(item: Mapping[str, Any], *, indent: int = 0, include_reply_marker: bool = False) -> str:
    pad = "  " * indent
    lines: list[str] = []
    if include_reply_marker:
        lines.append(pad + "Reply")
    header = "[Deleted comment]" if item.get("deleted_placeholder") else str(item.get("author") or "Unknown")
    if item.get("date"):
        header += f" · {item.get('date')}"
    lines.extend([pad + header, ""])
    for line in str(item.get("text") or "").splitlines():
        lines.append(pad + line)
    lines.extend(["", pad + f"👍 {item.get('likes','')} 👎 {item.get('dislikes','')}".rstrip()])
    return "\n".join(lines).rstrip()


def full_comment_block(item: Mapping[str, Any], *, index: int | None = None, indent: int = 0) -> str:
    pad = "  " * indent
    label = (
        f"Comment label: [{index}] Parent Comment {item.get('human_id','')}"
        if indent == 0
        else f"Reply label: {item.get('human_id','')} to {item.get('parent_human_id','')}"
    )
    lines = [
        pad + label,
        pad + f"Type: {item.get('type','')}",
        pad + f"ID: {item.get('human_id','')}",
        pad + f"Source comment ID: {item.get('source_comment_id','')}",
        pad + f"Author: {item.get('author','')}",
        pad + f"Date: {item.get('date','')}",
        pad + f"Author profile: {item.get('author_profile_url','')}",
        pad + f"Profile CID: {item.get('author_profile_cid','')}",
        pad + f"Comment likes: {item.get('likes','')}",
        pad + f"Comment dislikes: {item.get('dislikes','')}",
        pad + f"Account comments: {item.get('account_comments','')}",
        pad + f"Account likes: {item.get('account_likes','')}",
        pad + f"Account followers: {item.get('account_followers','')}",
        pad + f"Deleted placeholder: {item.get('deleted_placeholder')}",
        pad + "Evidence/source-role details:",
        pad + f"Claim source role: {(item.get('source_role_metadata') or {}).get('claim_source_role','')}",
        pad + f"Source role: {(item.get('source_role_metadata') or {}).get('source_role','')}",
        pad + f"Primary source status: {(item.get('source_role_metadata') or {}).get('primary_source_status','')}",
        pad + f"Source chain gap: {(item.get('source_role_metadata') or {}).get('source_chain_gap','')}",
        pad + f"Publisher framing summary: {(item.get('source_role_metadata') or {}).get('publisher_framing_summary','')}",
        pad + f"Claimed original source: {(item.get('source_role_metadata') or {}).get('claimed_original_source','')}",
        pad + f"Notes on context dispute: {(item.get('source_role_metadata') or {}).get('notes_on_context_dispute','')}",
        pad + f"Source role scope: {(item.get('source_role_metadata') or {}).get('source_role_scope','')}",
        pad + f"Source role limitation: {(item.get('source_role_metadata') or {}).get('source_role_limitation','')}",
        pad + "Result:",
        compact_comment_block(item, indent=indent),
    ]
    return "\n".join(lines).rstrip()


def render_msn_comments_text(export: MsnCommentsProfileExport, *, full: bool = False) -> str:
    lines = [
        "MSN Comments Export - " + ("Full Export" if full else "Readable Export"),
        "=" * 70,
        "",
        f"Source URL: {export.source_url}",
        f"Title: {export.title}",
        f"Exporter: {export.exporter}",
        f"Input sorts: {', '.join(export.input_sorts)}",
        f"Shown MSN count: {export.shown_msn_count}",
        f"Parents captured: {export.parents_captured}",
        f"Items captured: {export.items_captured}",
        f"Deleted placeholders: {export.deleted_placeholders}",
        f"Items with comment votes: {export.items_with_comment_votes}",
        f"Profiles: {len(export.profiles)}",
        f"Profiles with account stats: {export.profiles_with_account_stats}",
        "-" * 70,
        "",
        "COMMENTS AND REPLIES",
        "=" * 70,
        "",
    ]
    for index, comment in enumerate(export.comments, 1):
        lines.append(full_comment_block(comment, index=index) if full else compact_comment_block(comment))
        for reply in comment.get("replies") or []:
            lines.extend(["", full_comment_block(reply, indent=1) if full else compact_comment_block(reply, indent=1, include_reply_marker=True)])
        lines.extend(["", "-" * 70, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_profiles_text(export: MsnCommentsProfileExport) -> str:
    lines = [
        "MSN Commenter Profiles",
        "=" * 70,
        "",
        f"Profiles: {len(export.profiles)}",
        f"Profiles with account stats: {export.profiles_with_account_stats}",
        "",
    ]
    for profile in export.profiles:
        lines.extend(
            [
                str(profile.get("author", "")),
                f"Profile: {profile.get('canonical_url','')}",
                f"CID: {profile.get('profile_cid','')}",
                f"Account comments: {profile.get('account_comments','')}",
                f"Account likes: {profile.get('account_likes','')}",
                f"Account followers: {profile.get('account_followers','')}",
                f"Appearances: {profile.get('appearances','')}",
                f"Items: {'; '.join(profile.get('item_ids') or [])}",
                "-" * 70,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_msn_comments_markdown(export: MsnCommentsProfileExport) -> str:
    return (
        "# MSN Comments Profile Export\n\n"
        "## Summary\n\n"
        f"- Source URL: {export.source_url}\n"
        f"- Title: {export.title}\n"
        f"- Parents captured: {export.parents_captured}\n"
        f"- Items captured: {export.items_captured}\n"
        f"- Deleted placeholders: {export.deleted_placeholders}\n"
        f"- Profiles with account stats: {export.profiles_with_account_stats}/{len(export.profiles)}\n\n"
        "## Readable Comments\n\n"
        "```text\n"
        + render_msn_comments_text(export, full=False)
        + "```\n"
    )


def _html_json(value: Any) -> str:
    return html.escape(json.dumps(_value_for_dict(value), ensure_ascii=False), quote=False)


def render_msn_comments_html(export: MsnCommentsProfileExport) -> str:
    compact_txt = render_msn_comments_text(export, full=False)
    full_txt = render_msn_comments_text(export, full=True)
    profiles_txt = render_profiles_text(export)
    summary = (
        f"Parents: {export.parents_captured} · Items: {export.items_captured} · "
        f"Deleted: {export.deleted_placeholders} · Profiles: {len(export.profiles)} · "
        f"Profiles with account stats: {export.profiles_with_account_stats}"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MSN Comments Profile Export</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 18px; background: #181818; color: #f1f1f1; }}
button, input, select {{ background: #242424; color: #f1f1f1; border: 1px solid #666; border-radius: 4px; padding: 5px 8px; }}
input[type=text] {{ width: 34rem; max-width: 88vw; }}
.toolbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 10px 0; }}
.single-field {{ width: 100%; min-height: 66vh; box-sizing: border-box; background: #0f0f0f; color: #f1f1f1; border: 1px solid #555; border-radius: 8px; padding: 12px; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 13px; }}
.result {{ border-top: 1px solid #555; padding: 10px 0; white-space: pre-wrap; font-family: Consolas, monospace; }}
.small {{ color: #bbb; font-size: 12px; }}
a {{ color: #8ab4ff; }}
</style>
</head>
<body>
<h1>MSN Comments Profile Export</h1>
<p class="small">{html.escape(summary)}</p>
<p class="small">Source URL: {html.escape(export.source_url)}</p>
<section aria-label="Search comments">
  <div class="toolbar">
    <input id="searchBox" type="text" placeholder="Search comments and replies">
    <select id="searchMode"><option value="all">all words</option><option value="any">any word</option></select>
    <label><input id="searchAdditionalInfo" type="checkbox"> Additional information for search results</label>
    <button id="searchButton" onclick="runSearch()">Search</button>
    <button id="copySearchPlain" onclick="copyText(resultsPlainText)">Copy search results</button>
    <button id="downloadSearchTxt" onclick="downloadText('msn-comments-search-results.txt', resultsPlainText)">Download TXT</button>
    <button id="downloadSearchJson" onclick="downloadText('msn-comments-search-results.json', JSON.stringify(resultsJson, null, 2))">Download JSON</button>
  </div>
  <div id="searchResults" class="small">No search run yet.</div>
</section>
<section aria-label="Full comments export">
  <div class="toolbar">
    <label><input id="fullAdditionalInfo" type="checkbox" onchange="renderFullBox()"> Additional information for full export box</label>
    <button id="copyFullPlain" onclick="copyText(document.getElementById('fullExportBox').value)">Copy visible TXT export</button>
    <button id="downloadFullTxt" onclick="downloadText('msn-comments-visible-export.txt', document.getElementById('fullExportBox').value)">Download TXT</button>
  </div>
  <textarea id="fullExportBox" class="single-field" spellcheck="false"></textarea>
</section>
<details><summary>Profiles</summary><pre>{html.escape(profiles_txt)}</pre></details>
<details><summary>Evidence/source-role details</summary><pre>{html.escape(", ".join(CLAIM_SOURCE_ROLE_FIELDS + MANUAL_EVIDENCE_NOTE_FIELDS))}</pre></details>
<script>
const comments = {json.dumps(_value_for_dict(list(export.comments)), ensure_ascii=False)};
const compactExport = {json.dumps(compact_txt, ensure_ascii=False)};
const fullExport = {json.dumps(full_txt, ensure_ascii=False)};
let resultsPlainText = "";
let resultsJson = [];
function walk(items, callback) {{
  for (const item of items) {{
    callback(item);
    walk(item.replies || [], callback);
  }}
}}
function plainBlock(item) {{
  const header = (item.deleted_placeholder ? "[Deleted comment]" : (item.author || "Unknown")) + (item.date ? " · " + item.date : "");
  return [header, "", item.text || "", "", "👍 " + (item.likes || "") + " 👎 " + (item.dislikes || "")].join("\\n").trim();
}}
function infoBlock(item) {{
  const role = item.source_role_metadata || {{}};
  return [
    "Comment label: " + (item.human_id || ""),
    "Type: " + (item.type || ""),
    "Source comment ID: " + (item.source_comment_id || ""),
    "Author profile: " + (item.author_profile_url || ""),
    "Profile CID: " + (item.author_profile_cid || ""),
    "Account comments: " + (item.account_comments || ""),
    "Account likes: " + (item.account_likes || ""),
    "Account followers: " + (item.account_followers || ""),
    "Evidence/source-role details:",
    "Claim source role: " + (role.claim_source_role || ""),
    "Source role: " + (role.source_role || ""),
    "Primary source status: " + (role.primary_source_status || ""),
    "Source chain gap: " + String(role.source_chain_gap ?? ""),
    "Publisher name: " + (role.publisher_name || ""),
    "Publisher framing summary: " + (role.publisher_framing_summary || ""),
    "Visible source credit: " + (role.visible_source_credit || ""),
    "Claimed original source: " + (role.claimed_original_source || ""),
    "Original source URL: " + (role.original_source_url || ""),
    "Source-author correction URL: " + (role.source_author_correction_url || ""),
    "Source-author correction text/path: " + (role.source_author_correction_text_or_path || ""),
    "Notes on context dispute: " + (role.notes_on_context_dispute || ""),
    "Source role scope: " + (role.source_role_scope || ""),
    "Source role limitation: " + (role.source_role_limitation || ""),
    "Result:",
    plainBlock(item)
  ].join("\\n");
}}
function terms() {{ return document.getElementById("searchBox").value.toLowerCase().split(/\\s+/).filter(Boolean); }}
function matches(item, words, mode) {{
  const role = item.source_role_metadata || {{}};
  const haystack = [
    item.author, item.date, item.text, item.author_profile_url, item.author_profile_cid,
    role.claim_source_role, role.source_role, role.primary_source_status, role.publisher_name,
    role.publisher_framing_summary, role.claimed_original_source, role.notes_on_context_dispute,
    String(role.source_chain_gap ?? "")
  ].join(" ").toLowerCase();
  return mode === "any" ? words.some(word => haystack.includes(word)) : words.every(word => haystack.includes(word));
}}
function runSearch() {{
  const words = terms();
  const mode = document.getElementById("searchMode").value;
  const withInfo = document.getElementById("searchAdditionalInfo").checked;
  const hits = [];
  walk(comments, item => {{ if (!words.length || matches(item, words, mode)) hits.push(item); }});
  resultsJson = hits;
  resultsPlainText = hits.map(item => withInfo ? infoBlock(item) : plainBlock(item)).join("\\n\\n" + "-".repeat(60) + "\\n\\n");
  document.getElementById("searchResults").innerHTML = "<p>" + hits.length + " result(s)</p><pre>" + escapeHtml(resultsPlainText) + "</pre>";
}}
function renderFullBox() {{
  document.getElementById("fullExportBox").value = document.getElementById("fullAdditionalInfo").checked ? fullExport : compactExport;
}}
function copyText(text) {{ navigator.clipboard && navigator.clipboard.writeText(text); }}
function downloadText(name, text) {{
  const blob = new Blob([text], {{type: "text/plain;charset=utf-8"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}}
function escapeHtml(text) {{ return String(text).replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[ch])); }}
renderFullBox();
</script>
</body>
</html>
"""


@dataclass(frozen=True)
class MsnCommentsProfileExportFiles:
    output_dir: str
    json_path: str
    txt_path: str
    full_txt_path: str
    markdown_path: str
    html_path: str
    profiles_json_path: str
    profiles_csv_path: str
    profiles_txt_path: str
    profiles_html_path: str
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def write_msn_comments_profile_exports(
    export: MsnCommentsProfileExport,
    output_dir: str | Path,
    *,
    base_name: str = "msn-comments-v35-profile-stats",
    generated_at: str = "",
) -> MsnCommentsProfileExportFiles:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = generated_at or _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    payload = export.to_dict(generated_at=generated)
    json_path = out / f"{base_name}.json"
    txt_path = out / f"{base_name}.txt"
    full_txt_path = out / f"{base_name}-full.txt"
    markdown_path = out / f"{base_name}.md"
    html_path = out / f"{base_name}.html"
    profiles_json_path = out / f"{base_name}-profiles.json"
    profiles_csv_path = out / f"{base_name}-profiles.csv"
    profiles_txt_path = out / f"{base_name}-profiles.txt"
    profiles_html_path = out / f"{base_name}-profiles.html"
    manifest_path = out / f"{base_name}-manifest.json"

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(render_msn_comments_text(export, full=False), encoding="utf-8")
    full_txt_path.write_text(render_msn_comments_text(export, full=True), encoding="utf-8")
    markdown_path.write_text(render_msn_comments_markdown(export), encoding="utf-8")
    html_path.write_text(render_msn_comments_html(export), encoding="utf-8")
    profiles_json_path.write_text(json.dumps(_value_for_dict(list(export.profiles)), ensure_ascii=False, indent=2), encoding="utf-8")
    profiles_txt_path.write_text(render_profiles_text(export), encoding="utf-8")
    profiles_html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>MSN Profiles</title><pre>"
        + html.escape(render_profiles_text(export))
        + "</pre>",
        encoding="utf-8",
    )
    with profiles_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        columns = [
            "author",
            "profile_cid",
            "canonical_url",
            "account_comments",
            "account_likes",
            "account_followers",
            "appearances",
            "item_ids",
            "profile_stats_method",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for profile in export.profiles:
            row = {column: profile.get(column, "") for column in columns}
            row["item_ids"] = "; ".join(profile.get("item_ids") or [])
            writer.writerow(row)
    files = MsnCommentsProfileExportFiles(
        output_dir=str(out),
        json_path=str(json_path),
        txt_path=str(txt_path),
        full_txt_path=str(full_txt_path),
        markdown_path=str(markdown_path),
        html_path=str(html_path),
        profiles_json_path=str(profiles_json_path),
        profiles_csv_path=str(profiles_csv_path),
        profiles_txt_path=str(profiles_txt_path),
        profiles_html_path=str(profiles_html_path),
        manifest_path=str(manifest_path),
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": MSN_COMMENTS_PROFILE_EXPORT_SCHEMA_VERSION,
                "source_url": export.source_url,
                "title": export.title,
                "counts": {
                    "parents": export.parents_captured,
                    "items": export.items_captured,
                    "deleted_placeholders": export.deleted_placeholders,
                    "items_with_comment_votes": export.items_with_comment_votes,
                    "profiles": len(export.profiles),
                    "profiles_with_account_stats": export.profiles_with_account_stats,
                },
                "files": files.to_dict(),
                "offline_article_archive_preserved": True,
                "manual_live_capture_required": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return files


def build_offline_article_comments_integration_manifest(
    *,
    article_archive_dir: str | Path,
    comments_export_files: MsnCommentsProfileExportFiles,
) -> dict[str, Any]:
    archive_dir = Path(article_archive_dir)
    expected_article_files = (
        "rendered-page.html",
        "rendered-page.warc.gz",
        "archive.viewable-live-capture.wacz",
        "capture-manifest.json",
        "validation.json",
        "local_viewer/open_local_viewer.cmd",
    )
    return {
        "schema_version": MSN_COMMENTS_PROFILE_EXPORT_SCHEMA_VERSION,
        "offline_article_archive_preserved": True,
        "article_archive_dir": str(archive_dir),
        "article_archive_files": {
            name: {"name": name, "present": (archive_dir / name).is_file()} for name in expected_article_files
        },
        "comments_profile_export_files": comments_export_files.to_dict(),
        "integration_status": "MSN_OFFLINE_ARTICLE_ARCHIVE_PLUS_COMMENTS_PROFILE_EXPORT_READY",
    }


def build_msn_comments_profile_export_from_paths(paths: Sequence[str | Path]) -> MsnCommentsProfileExport:
    return build_msn_comments_profile_export(load_msn_comments_captures(paths))
