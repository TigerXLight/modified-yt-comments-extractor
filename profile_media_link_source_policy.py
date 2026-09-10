"""Conservative policy for Profile/Media link source objects.

This layer classifies URL objects and their relation to nearby context. It does
not classify claim-span text, fetch URLs, or update media-source counts.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import sys
from pathlib import Path
from typing import Iterable, Mapping

try:
    from profile_media_url_normalizer import normalise_url_record
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from profile_media_url_normalizer import normalise_url_record


OFFICIAL_DOMAINS = {
    "gov.uk",
    "questions-statements.parliament.uk",
    "search-uk-sanctions-list.service.gov.uk",
    "churchofengland.org",
    "archbishopofcanterbury.org",
    "oikoumene.org",
    "legislation.generalconvention.org",
    "vbinder.net",
    "anglicannews.org",
    "chelmsford.anglican.org",
    "eeas.europa.eu",
    "gov.ie",
    "government.nl",
    "birzeit.edu",
}

NEWS_DOMAINS = {
    "metro.co.uk",
    "theguardian.com",
    "episcopalnewsservice.org",
    "anglicanfocus.org.au",
    "newarab.com",
    "wafa.ps",
    "religionmediacentre.org.uk",
    "christiantoday.com",
    "teaonews.co.nz",
}

OPINION_DOMAINS = {
    "premierchristianity.com",
    "psephizo.com",
    "jewishjournal.com",
    "meforum.org",
    "electronicintifada.net",
    "mondoweiss.net",
    "samidoun.net",
    "addameer.org",
    "britainpalestineproject.org",
    "aurdip.org",
}


def _host_matches(hostname: str, domains: set[str]) -> bool:
    host = (hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def _merged_link_record(link_record: Mapping[str, object]) -> dict[str, object]:
    url = str(link_record.get("normalised_url") or link_record.get("url") or "")
    normalised = normalise_url_record(url)
    merged = dict(link_record)
    for key, value in normalised.items():
        merged.setdefault(key, value)
    return merged


def _context_text(record: Mapping[str, object], surrounding_text: str) -> str:
    return " ".join(
        str(part or "")
        for part in (
            surrounding_text,
            record.get("source_context_text"),
            record.get("nearby_heading"),
            record.get("list_label"),
            record.get("anchor_text"),
        )
    ).casefold()


def _base_decision(record: Mapping[str, object], surrounding_text: str) -> dict[str, object]:
    context = _context_text(record, surrounding_text)
    hostname = str(record.get("hostname") or "").lower()
    path = str(record.get("path") or "").lower()
    archive_kind = str(record.get("archive_kind") or "none")

    if archive_kind == "archive_index":
        return {
            "source_object_type": "archive_locator",
            "source_relation_type": "locator_only",
            "default_link_role": "LOCATOR",
            "claim_specific_role": "LOCATOR",
            "role_reason": "Wayback/archive capture list locates preserved copies; it is not source evidence by itself.",
            "confidence": "high",
            "needs_review": False,
            "locator_only": True,
            "preservation_for_url": str(record.get("archive_target_url") or ""),
        }
    if archive_kind == "archived_copy":
        target = str(record.get("archive_target_url") or "")
        return {
            "source_object_type": "archived_copy",
            "source_relation_type": "archive_preservation",
            "default_link_role": "LOCATOR",
            "claim_specific_role": "LOCATOR",
            "role_reason": "Specific archived copy preserves a target URL; count the target object, not the archive wrapper, as source evidence.",
            "confidence": "high",
            "needs_review": False,
            "locator_only": False,
            "preservation_for_url": target,
        }
    if bool(record.get("is_redirect_wrapper")):
        return {
            "source_object_type": "redirect_wrapper",
            "source_relation_type": "locator_only",
            "default_link_role": "LOCATOR",
            "claim_specific_role": "LOCATOR",
            "role_reason": "Redirect wrapper points to another URL; source role follows the resolved target after review.",
            "confidence": "medium",
            "needs_review": True,
            "locator_only": True,
            "preservation_for_url": str(record.get("redirect_target_url") or ""),
        }
    if bool(record.get("is_social_url")):
        platform = str(record.get("social_platform") or "")
        object_type = str(record.get("social_object_type") or "")
        if platform == "youtube" or bool(record.get("is_video_url")):
            return {
                "source_object_type": "video_page",
                "source_relation_type": "own_statement",
                "default_link_role": "PRIMARY",
                "claim_specific_role": "PRIMARY",
                "role_reason": "Video/social media URL is primary for the upload/post object and account statement existence only; factual claims inside remain separately reviewed.",
                "confidence": "medium",
                "needs_review": True,
                "locator_only": False,
                "preservation_for_url": "",
            }
        return {
            "source_object_type": "social_post" if object_type in {"post", "status"} else "supporter_account",
            "source_relation_type": "own_statement",
            "default_link_role": "PRIMARY",
            "claim_specific_role": "PRIMARY",
            "role_reason": "Original social URL is primary for proving that account posted or hosted the object, not for factual truth of claims inside it.",
            "confidence": "medium",
            "needs_review": True,
            "locator_only": False,
            "preservation_for_url": "",
        }
    if _host_matches(hostname, OFFICIAL_DOMAINS):
        official_type = "official_pdf" if path.endswith(".pdf") else "legal_or_government_record" if ".gov." in hostname or hostname.endswith(".gov.uk") or "parliament.uk" in hostname else "official_page"
        return {
            "source_object_type": official_type,
            "source_relation_type": "official_record",
            "default_link_role": "PRIMARY",
            "claim_specific_role": "PRIMARY",
            "role_reason": "Official/institutional URL is primary for that body’s own page, statement, or record only.",
            "confidence": "high",
            "needs_review": False,
            "locator_only": False,
            "preservation_for_url": "",
        }
    if _host_matches(hostname, NEWS_DOMAINS):
        relation = "direct_interview" if any(token in context for token in ("told the paper", "interview", "spoke to", "quoted")) else "reports_another_source"
        return {
            "source_object_type": "news_article",
            "source_relation_type": relation,
            "default_link_role": "SECONDARY",
            "claim_specific_role": "SECONDARY",
            "role_reason": "News/reporting article is a secondary container or witness by default; exact quoted words may be primary for the quoted speaker only.",
            "confidence": "medium",
            "needs_review": "quoted" in context or "told" in context,
            "locator_only": False,
            "preservation_for_url": "",
        }
    if _host_matches(hostname, OPINION_DOMAINS):
        missing_original = any(token in context for token in ("hidden facebook", "original url", "does not provide", "missing original", "no original"))
        reason = "Opinion/commentary article is primary for the author’s own writing or opinion only."
        if missing_original:
            reason += " Nearby context indicates an original source is missing, so the missing original remains unresolved and is not treated as present."
        return {
            "source_object_type": "opinion_article" if "opinion" in context or "opinion" in path else "advocacy_article",
            "source_relation_type": "own_statement" if not missing_original else "summarises_allegation",
            "default_link_role": "PRIMARY",
            "claim_specific_role": "PRIMARY",
            "role_reason": reason,
            "confidence": "medium" if not missing_original else "low",
            "needs_review": True,
            "locator_only": False,
            "preservation_for_url": "",
        }
    if path.endswith(".pdf"):
        return {
            "source_object_type": "metadata_page",
            "source_relation_type": "unknown",
            "default_link_role": "UNKNOWN",
            "claim_specific_role": "UNKNOWN",
            "role_reason": "PDF URL is source-like, but publisher/source relation is not known by deterministic domain policy.",
            "confidence": "low",
            "needs_review": True,
            "locator_only": False,
            "preservation_for_url": "",
        }
    return {
        "source_object_type": "unknown",
        "source_relation_type": "unknown",
        "default_link_role": "UNKNOWN",
        "claim_specific_role": "UNKNOWN",
        "role_reason": "URL object type/source relation is not recognised by deterministic offline policy.",
        "confidence": "low",
        "needs_review": True,
        "locator_only": False,
        "preservation_for_url": "",
    }


def classify_link_source_object(link_record: dict, *, surrounding_text: str = "") -> dict:
    """Classify one extracted link source object without network access."""

    record = _merged_link_record(link_record)
    decision = _base_decision(record, surrounding_text)
    output = dict(record)
    output.update(decision)
    return output


def classify_link_source_objects(link_records: list[dict]) -> list[dict]:
    """Classify and de-duplicate link source records while preserving locators."""

    output: list[dict] = []
    seen_evidence_keys: set[str] = set()
    for record in link_records:
        if not isinstance(record, Mapping):
            continue
        classified = classify_link_source_object(dict(record))
        evidence_key = str(classified.get("preservation_for_url") or classified.get("normalised_url") or classified.get("url") or "").casefold()
        classified["source_object_group_key"] = evidence_key
        if classified.get("claim_specific_role") != "LOCATOR":
            if evidence_key in seen_evidence_keys:
                classified["duplicate_source_object"] = True
            else:
                seen_evidence_keys.add(evidence_key)
                classified["duplicate_source_object"] = False
        else:
            classified["duplicate_source_object"] = False
        output.append(classified)
    return output


def _role_from_mapping(record: Mapping[str, object]) -> str:
    role = str(record.get("claim_specific_role") or record.get("default_link_role") or "UNKNOWN").upper()
    return role if role in {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "LOCATOR"} else "UNKNOWN"


def _url_key(record: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = str(record.get(key) or "").strip()
        if value:
            return value.casefold()
    return ""


def _link_source_row_instance_key(record: Mapping[str, object]) -> str:
    parts = [
        str(record.get("url") or record.get("normalised_url") or "").strip(),
        str(record.get("source_path") or "").strip(),
        str(record.get("source_label") or "").strip(),
        str(record.get("line_number") or "").strip(),
        str(record.get("nearby_heading") or "").strip(),
        str(record.get("list_label") or "").strip(),
    ]
    seed = "|".join(part for part in parts if part)
    if not seed:
        seed = str(record.get("raw_url") or record.get("archive_target_url") or record.get("preservation_for_url") or "").strip()
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:14] if seed else "missing"
    return f"link-row-{digest}"


def resolve_visible_link_source_roles(link_records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Attach UI-facing roles while keeping archive/locator provenance separate.

    Archive and redirect wrappers remain LOCATOR/preservation objects internally.
    The visible source-role text should show the role of the preserved target, so
    Review users see "[SECONDARY] Archive URL" instead of treating LOCATOR as a
    fifth source role.
    """

    objects = [dict(item) for item in link_records if isinstance(item, Mapping)]
    target_role_by_key: dict[str, str] = {}
    target_url_by_key: dict[str, str] = {}
    unique_non_locator_targets: dict[str, dict[str, object]] = {}
    for item in objects:
        item.setdefault("link_source_row_instance_key", _link_source_row_instance_key(item))
        item.setdefault("classifier_default_link_role", _role_from_mapping(item))
        item.setdefault("classifier_default_role_reason", str(item.get("role_reason") or ""))
        role = _role_from_mapping(item)
        if role == "LOCATOR" or bool(item.get("locator_only")):
            continue
        key = _url_key(item, "source_object_group_key", "normalised_url", "url")
        if not key:
            continue
        target_role_by_key[key] = role
        target_url_by_key[key] = str(item.get("normalised_url") or item.get("url") or "").strip()
        if not bool(item.get("duplicate_source_object")):
            unique_non_locator_targets[key] = item

    sole_target_key = ""
    if len(unique_non_locator_targets) == 1:
        sole_target_key = next(iter(unique_non_locator_targets))

    for item in objects:
        internal_role = _role_from_mapping(item)
        item["visible_role_is_locator_metadata"] = internal_role == "LOCATOR" or bool(item.get("locator_only"))
        item["visible_source_role_counts_as_locator"] = False
        item["visible_link_role"] = internal_role if internal_role != "LOCATOR" else "UNKNOWN"
        item["visible_link_source_row_label"] = "Source URL"
        if not item["visible_role_is_locator_metadata"]:
            item["archive_role_inherited_from_target"] = False
            continue

        item["visible_link_source_row_label"] = "Archive URL" if bool(item.get("is_archive_url")) else "Locator URL"
        target_key = _url_key(item, "preservation_for_url", "archive_target_url", "redirect_target_url")
        inherited_key = target_key if target_key in target_role_by_key else ""
        if not inherited_key and sole_target_key and bool(item.get("is_archive_url")):
            inherited_key = sole_target_key
        if inherited_key:
            item["visible_link_role"] = target_role_by_key[inherited_key]
            item["archive_role_inherited_from_target"] = True
            item["inherited_role_source_url"] = target_url_by_key.get(inherited_key, "")
            item["visible_role_reason"] = "Archive/preservation wrapper inherits the visible source role of its target URL."
        else:
            item["archive_role_inherited_from_target"] = False
            item["visible_role_reason"] = "Archive/locator wrapper has no resolved target in this source set; show as Unknown pending review."
    return objects


def build_link_source_preview(link_records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Return a separate preview block for link source objects."""

    objects = resolve_visible_link_source_roles(link_records)
    role_counts = Counter({"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0, "LOCATOR": 0})
    visible_role_counts = Counter({"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0})
    type_counts: Counter[str] = Counter()
    evidence_keys: set[str] = set()
    for item in objects:
        role = _role_from_mapping(item)
        if role not in role_counts:
            role = "UNKNOWN"
        role_counts[role] += 1
        visible_role = str(item.get("visible_link_role") or role).upper()
        if visible_role not in visible_role_counts:
            visible_role = "UNKNOWN"
        visible_role_counts[visible_role] += 1
        type_counts[str(item.get("source_object_type") or "unknown")] += 1
        if role != "LOCATOR" and not item.get("duplicate_source_object"):
            key = str(item.get("source_object_group_key") or item.get("normalised_url") or item.get("url") or "")
            if key:
                evidence_keys.add(key.casefold())
    return {
        "schema_version": "profile-media-link-source-preview-v83b",
        "link_count": len(objects),
        "distinct_non_locator_source_object_count": len(evidence_keys),
        "source_object_counts": dict(type_counts),
        "role_counts": dict(role_counts),
        "visible_role_counts": dict(visible_role_counts),
        "locator_role_is_preservation_metadata": True,
        "objects": objects,
        "link_objects_are_separate_from_claim_role_spans": True,
        "link_objects_do_not_inflate_media_source_counts": True,
    }
