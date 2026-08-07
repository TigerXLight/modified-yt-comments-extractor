from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = "source_comment_extraction_v1"
COMMENT_ROLE_CANDIDATES = {
    "comments_json_or_text",
    "saved_comments_json_or_text",
    "comments_json",
    "comments_text",
    "comment_thread_json",
    "replies_json_or_text",
    "livechat_json_or_text",
    "dom_snapshot",
}
COMMENT_TEXT_KEYS = ("text", "body", "comment", "content", "message", "comment_text", "rendered_text")
AUTHOR_KEYS = ("author", "user", "username", "name", "display_name", "author_name", "handle")
REPLY_KEYS = ("replies", "children", "comments", "responses")


@dataclass(frozen=True)
class SourceCommentArtifact:
    role: str
    path: str
    filename: str | None = None


@dataclass(frozen=True)
class ExtractedComment:
    comment_id: str
    author: str
    text: str
    created_at: str
    parent_id: str
    like_count: int | None
    depth: int
    source: str
    warnings: list[str] = field(default_factory=list)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _safe_id_text(value: str, *, fallback: str = "source") -> str:
    value = _safe_text(value).lower()
    value = re.sub(r"[^a-z0-9_.-]+", ".", value).strip("._-")
    return value[:96] or fallback


def _safe_basename(path_or_name: str) -> str:
    name = Path(str(path_or_name)).name.strip()
    if not name or name in {".", ".."}:
        raise ValueError("artifact filename is required")
    if any(part in name for part in ("/", "\\")):
        raise ValueError("artifact filename must be a basename")
    return name


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_text_artifact(path: str | Path) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"artifact file not found: {p}")
    return _decode_bytes(p.read_bytes())


def _collapse_spaces(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t \f\v]+", " ", value)
    value = re.sub(r" *\n+ *", "\n", value)
    return html.unescape(value).strip()


def _strip_tags(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</(p|div|li|article|section|blockquote)>\s*", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def _first_text(payload: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        if key in payload:
            value = payload.get(key)
            if isinstance(value, dict):
                nested = _first_text(value, ("name", "display_name", "username", "handle", "text"))
                if nested:
                    return nested
            elif isinstance(value, list):
                joined = " ".join(_safe_text(item) for item in value if _safe_text(item))
                if joined:
                    return joined
            else:
                text = _safe_text(value)
                if text:
                    return text
    return ""


def _maybe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = _safe_text(value).replace(",", "")
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return None


def _comment_from_mapping(
    payload: dict[str, Any],
    *,
    ordinal: int,
    parent_id: str = "",
    depth: int = 0,
    source: str = "json",
) -> ExtractedComment | None:
    text = _collapse_spaces(_first_text(payload, COMMENT_TEXT_KEYS))
    if not text:
        return None
    raw_id = _safe_text(
        payload.get("id")
        or payload.get("comment_id")
        or payload.get("cid")
        or payload.get("uuid")
        or payload.get("key")
    )
    author = _collapse_spaces(_first_text(payload, AUTHOR_KEYS))
    created_at = _safe_text(
        payload.get("created_at")
        or payload.get("published_at")
        or payload.get("timestamp")
        or payload.get("time")
        or payload.get("date")
    )
    like_count = _maybe_int(
        payload.get("like_count")
        or payload.get("likes")
        or payload.get("upvotes")
        or payload.get("score")
    )
    comment_id = _safe_id_text(raw_id, fallback=f"comment.{ordinal:04d}")
    warnings = [] if author else ["missing_author"]
    return ExtractedComment(
        comment_id=comment_id,
        author=author,
        text=text,
        created_at=created_at,
        parent_id=_safe_id_text(parent_id, fallback="") if parent_id else "",
        like_count=like_count,
        depth=max(0, depth),
        source=source,
        warnings=warnings,
    )


def _iter_comment_dicts(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_comment_dicts(item)
    elif isinstance(payload, dict):
        if any(key in payload for key in COMMENT_TEXT_KEYS):
            yield payload
        for key in ("comments", "items", "results", "data", "threads", "entries"):
            value = payload.get(key)
            if isinstance(value, (list, dict)):
                yield from _iter_comment_dicts(value)


def _extract_json_comments(payload: Any, *, source: str = "json") -> list[ExtractedComment]:
    comments: list[ExtractedComment] = []

    def visit(node: Any, *, parent_id: str = "", depth: int = 0) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item, parent_id=parent_id, depth=depth)
            return
        if not isinstance(node, dict):
            return
        comment = _comment_from_mapping(
            node,
            ordinal=len(comments) + 1,
            parent_id=parent_id,
            depth=depth,
            source=source,
        )
        next_parent = parent_id
        if comment is not None:
            comments.append(comment)
            next_parent = comment.comment_id
        for key in REPLY_KEYS:
            child = node.get(key)
            if isinstance(child, (list, dict)):
                visit(child, parent_id=next_parent, depth=depth + 1 if comment is not None else depth)
        for key in ("items", "results", "data", "threads", "entries"):
            child = node.get(key)
            if isinstance(child, (list, dict)):
                visit(child, parent_id=parent_id, depth=depth)

    visit(payload)
    if comments:
        return _dedupe_comments(comments)
    return _dedupe_comments(
        comment
        for ordinal, item in enumerate(_iter_comment_dicts(payload), start=1)
        if (comment := _comment_from_mapping(item, ordinal=ordinal, source=source)) is not None
    )


def _parse_json_or_ndjson(raw_text: str) -> list[ExtractedComment] | None:
    try:
        payload = json.loads(raw_text)
    except Exception:
        payload = None
    if payload is not None:
        return _extract_json_comments(payload, source="json")

    comments: list[ExtractedComment] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or not line.startswith(("{", "[")):
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        comments.extend(_extract_json_comments(payload, source="ndjson"))
    if comments:
        return _dedupe_comments(comments)
    return None


def _parse_html_comments(raw_text: str) -> list[ExtractedComment] | None:
    if not re.search(r"<\s*(html|body|article|section|div|li|comment)\b", raw_text, flags=re.I):
        return None
    candidates = re.findall(
        r"<(?:article|section|div|li|blockquote)[^>]*(?:comment|reply)[^>]*>(.*?)</(?:article|section|div|li|blockquote)>",
        raw_text,
        flags=re.I | re.S,
    )
    comments: list[ExtractedComment] = []
    if candidates:
        for ordinal, candidate in enumerate(candidates, start=1):
            text = _collapse_spaces(_strip_tags(candidate))
            if text:
                comments.append(
                    ExtractedComment(
                        comment_id=f"comment.{ordinal:04d}",
                        author="",
                        text=text,
                        created_at="",
                        parent_id="",
                        like_count=None,
                        depth=0,
                        source="html_comment_blocks",
                        warnings=["missing_author"],
                    )
                )
    if comments:
        return comments
    stripped = _collapse_spaces(_strip_tags(raw_text))
    return _parse_plain_text_comments(stripped, source="html_text_fallback")


def _parse_plain_text_comments(raw_text: str, *, source: str = "plain_text") -> list[ExtractedComment]:
    text = _collapse_spaces(raw_text)
    if not text:
        return []
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
    if len(blocks) <= 1:
        blocks = [line.strip() for line in text.splitlines() if line.strip()]
    comments: list[ExtractedComment] = []
    for ordinal, block in enumerate(blocks, start=1):
        author = ""
        body = block
        match = re.match(r"^[-*•]?\s*([^:\n]{1,80})\s*:\s*(.+)$", block, flags=re.S)
        if match:
            author = _collapse_spaces(match.group(1))
            body = _collapse_spaces(match.group(2))
        if not body:
            continue
        comments.append(
            ExtractedComment(
                comment_id=f"comment.{ordinal:04d}",
                author=author,
                text=body,
                created_at="",
                parent_id="",
                like_count=None,
                depth=0,
                source=source,
                warnings=[] if author else ["missing_author"],
            )
        )
    return comments


def _dedupe_comments(comments: Iterable[ExtractedComment]) -> list[ExtractedComment]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ExtractedComment] = []
    for comment in comments:
        key = (comment.comment_id, comment.author.lower(), comment.text)
        if key in seen:
            continue
        seen.add(key)
        result.append(comment)
    return result


def extract_comments_from_artifact_text(raw_text: str) -> tuple[list[ExtractedComment], str, list[str]]:
    raw_text = _safe_text(raw_text)
    warnings: list[str] = []
    if not raw_text:
        raise ValueError("comments artifact text is empty")
    parsed = _parse_json_or_ndjson(raw_text)
    if parsed is not None:
        method = "shared_json_or_ndjson_comment_fields"
        comments = parsed
    else:
        html_comments = _parse_html_comments(raw_text)
        if html_comments is not None:
            method = "shared_html_comment_heuristic"
            comments = html_comments
        else:
            method = "shared_plain_text_comment_heuristic"
            comments = _parse_plain_text_comments(raw_text)
    if not comments:
        warnings.append("no_comments_extracted")
    normalized: list[ExtractedComment] = []
    for ordinal, comment in enumerate(comments, start=1):
        comment_id = comment.comment_id or f"comment.{ordinal:04d}"
        normalized.append(
            ExtractedComment(
                comment_id=_safe_id_text(comment_id, fallback=f"comment.{ordinal:04d}"),
                author=_collapse_spaces(comment.author),
                text=_collapse_spaces(comment.text),
                created_at=_safe_text(comment.created_at),
                parent_id=_safe_id_text(comment.parent_id, fallback="") if comment.parent_id else "",
                like_count=comment.like_count,
                depth=max(0, comment.depth),
                source=comment.source,
                warnings=comment.warnings,
            )
        )
    return normalized, method, warnings


def _artifact_from_dict(item: dict[str, Any]) -> SourceCommentArtifact | None:
    role = _safe_text(item.get("role") or item.get("artifact_role") or item.get("type"))
    path = _safe_text(item.get("path") or item.get("file_path") or item.get("artifact_path") or item.get("source_path"))
    filename = _safe_text(item.get("filename") or item.get("name")) or None
    if not role:
        return None
    if not path and filename:
        path = filename
    if not path:
        return None
    return SourceCommentArtifact(role=role, path=path, filename=filename)


def extract_artifacts_from_collection_payload(payload: dict[str, Any]) -> list[SourceCommentArtifact]:
    candidates: list[dict[str, Any]] = []
    for key in ("artifacts", "artifact_entries", "collection", "files"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))
    handoff = payload.get("extraction_handoff")
    if isinstance(handoff, dict):
        value = handoff.get("artifacts") or handoff.get("files")
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))
    artifacts: list[SourceCommentArtifact] = []
    for item in candidates:
        artifact = _artifact_from_dict(item)
        if artifact:
            artifacts.append(artifact)
    return artifacts


def load_artifact_collection(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _select_comment_artifact(artifacts: list[SourceCommentArtifact]) -> SourceCommentArtifact:
    if not artifacts:
        raise ValueError("at least one artifact is required")
    for artifact in artifacts:
        if artifact.role in COMMENT_ROLE_CANDIDATES:
            return artifact
    for artifact in artifacts:
        role = artifact.role.lower()
        name = (artifact.filename or Path(artifact.path).name).lower()
        if "comment" in role or "reply" in role or "livechat" in role or "comment" in name:
            return artifact
    raise ValueError("no comments artifact found in explicit artifact list")


def build_source_comment_extraction(
    *,
    adapter_id: str,
    source_url: str,
    artifacts: list[SourceCommentArtifact],
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    selected = _select_comment_artifact(artifacts)
    artifact_path = Path(selected.path)
    if not artifact_path.is_absolute() and base_dir is not None:
        artifact_path = Path(base_dir) / artifact_path
    raw = read_text_artifact(artifact_path)
    filename = selected.filename or artifact_path.name
    comments, method, warnings = extract_comments_from_artifact_text(raw)
    comment_payloads = [asdict(comment) for comment in comments]
    comment_digest = _sha256_text(json.dumps(comment_payloads, sort_keys=True, ensure_ascii=False))
    adapter = _safe_id_text(adapter_id, fallback="unknown_adapter")
    comment_extraction_id = f"{adapter}.comments.{comment_digest[:12]}"
    artifact_summaries = []
    for artifact in artifacts:
        name = artifact.filename or Path(artifact.path).name
        artifact_summaries.append(
            {
                "role": _safe_id_text(artifact.role, fallback="artifact"),
                "filename": _safe_basename(name),
                "selected_for_comments": artifact is selected,
            }
        )
    extraction = {
        "schema_version": SCHEMA_VERSION,
        "comment_extraction_id": comment_extraction_id,
        "adapter_id": adapter,
        "source_url": _safe_text(source_url),
        "source_domain": urlparse(_safe_text(source_url)).netloc.lower(),
        "selected_artifact": {
            "role": _safe_id_text(selected.role, fallback="comments_json_or_text"),
            "filename": _safe_basename(filename),
        },
        "artifacts": artifact_summaries,
        "comments": comment_payloads,
        "comment_count": len(comment_payloads),
        "comment_sha256": comment_digest,
        "extraction_method": method,
        "warnings": warnings,
        "operator_summary": {
            "live_network_used": False,
            "folder_scan_used": False,
            "full_local_paths_serialized": False,
            "status": "COMMENTS_EXTRACTED_FROM_EXPLICIT_ARTIFACT",
        },
    }
    extraction["extraction_handoff"] = {
        "schema_version": "source_comment_extraction_handoff_v1",
        "comment_extraction_id": comment_extraction_id,
        "adapter_id": adapter,
        "source_url": _safe_text(source_url),
        "comment_sha256": comment_digest,
        "comment_count": len(comment_payloads),
        "next_stage": "source_capture_bundle_or_total_export_package",
        "required_next_inputs": [
            "content_extraction_json when article/content is available",
            "comment_extraction_json",
            "artifact_collection_manifest_json",
        ],
    }
    return extraction


def build_source_comment_extraction_from_collection(
    *,
    artifact_collection_path: str | Path,
    adapter_id: str | None = None,
    source_url: str | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    collection_path = Path(artifact_collection_path)
    payload = load_artifact_collection(collection_path)
    artifacts = extract_artifacts_from_collection_payload(payload)
    resolved_base = base_dir if base_dir is not None else collection_path.parent
    return build_source_comment_extraction(
        adapter_id=adapter_id or _safe_text(payload.get("adapter_id")) or "unknown_adapter",
        source_url=source_url or _safe_text(payload.get("source_url")),
        artifacts=artifacts,
        base_dir=resolved_base,
    )


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    return value
