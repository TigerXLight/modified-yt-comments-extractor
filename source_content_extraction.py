from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = "source_content_extraction_v1"
TEXT_ROLE_CANDIDATES = {
    "article_html_or_text",
    "saved_article_html_or_text",
    "article_html",
    "article_text",
    "content_html_or_text",
    "dom_snapshot",
    "page_text",
}


@dataclass(frozen=True)
class SourceContentArtifact:
    role: str
    path: str
    filename: str | None = None


@dataclass(frozen=True)
class ExtractedContent:
    adapter_id: str
    source_url: str
    artifact_filename: str
    artifact_role: str
    title: str
    body_text: str
    body_paragraphs: list[str]
    extraction_method: str
    source_domain: str
    warnings: list[str] = field(default_factory=list)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _safe_id_text(value: str, *, fallback: str = "source") -> str:
    value = _safe_text(value).lower()
    value = re.sub(r"[^a-z0-9_.-]+", ".", value).strip("._-")
    return value[:80] or fallback


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


def _strip_json_content(raw: str) -> tuple[str, str, list[str]] | None:
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    title = _safe_text(payload.get("title") or payload.get("headline") or payload.get("name"))
    body = _safe_text(
        payload.get("body")
        or payload.get("body_text")
        or payload.get("text")
        or payload.get("content")
        or payload.get("article")
    )
    paragraphs = payload.get("paragraphs") or payload.get("body_paragraphs")
    if isinstance(paragraphs, list):
        body_paragraphs = [_collapse_spaces(_safe_text(item)) for item in paragraphs if _safe_text(item)]
        if not body and body_paragraphs:
            body = "\n\n".join(body_paragraphs)
    else:
        body_paragraphs = split_paragraphs(body)
    if not title and body_paragraphs:
        title = body_paragraphs[0]
        body_paragraphs = body_paragraphs[1:] or body_paragraphs
        body = "\n\n".join(body_paragraphs)
    if not title and not body:
        return None
    return title, body, body_paragraphs


def _extract_first(patterns: Iterable[str], raw: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _collapse_spaces(html.unescape(_strip_tags(match.group(1))))
    return ""


def _strip_tags(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<noscript\b[^>]*>.*?</noscript>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"</(p|div|li|h[1-6]|section|article)>\s*", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def _collapse_spaces(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t \f\v]+", " ", value)
    value = re.sub(r" *\n+ *", "\n", value)
    return value.strip()


def split_paragraphs(raw: str) -> list[str]:
    raw = _collapse_spaces(raw)
    if not raw:
        return []
    chunks = re.split(r"\n{1,}|(?<=[.!?])\s{2,}", raw)
    paragraphs = [_collapse_spaces(chunk) for chunk in chunks if _collapse_spaces(chunk)]
    return paragraphs


def extract_content_from_artifact_text(
    raw_text: str,
    *,
    adapter_id: str,
    source_url: str,
    artifact_filename: str,
    artifact_role: str,
) -> ExtractedContent:
    raw_text = _safe_text(raw_text)
    warnings: list[str] = []
    if not raw_text:
        raise ValueError("artifact text is empty")

    json_result = _strip_json_content(raw_text)
    if json_result is not None:
        title, body_text, body_paragraphs = json_result
        method = "shared_json_content_fields"
    else:
        looks_html = bool(re.search(r"<\s*(html|article|body|h1|p|div|meta|title)\b", raw_text, re.I))
        if looks_html:
            title = _extract_first(
                (
                    r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)[\"']",
                    r"<meta[^>]+name=[\"']title[\"'][^>]+content=[\"']([^\"']+)[\"']",
                    r"<h1[^>]*>(.*?)</h1>",
                    r"<title[^>]*>(.*?)</title>",
                ),
                raw_text,
            )
            article_match = re.search(r"<article\b[^>]*>(.*?)</article>", raw_text, flags=re.IGNORECASE | re.DOTALL)
            body_candidate = article_match.group(1) if article_match else raw_text
            body_text = _collapse_spaces(_strip_tags(body_candidate))
            body_paragraphs = split_paragraphs(body_text)
            method = "shared_html_heuristic"
        else:
            lines = [_collapse_spaces(line) for line in raw_text.splitlines() if _collapse_spaces(line)]
            title = lines[0] if lines else ""
            body_paragraphs = lines[1:] if len(lines) > 1 else lines
            body_text = "\n\n".join(body_paragraphs)
            method = "shared_plain_text_heuristic"

    if body_paragraphs and title and body_paragraphs[0] == title and len(body_paragraphs) > 1:
        body_paragraphs = body_paragraphs[1:]
        body_text = "\n\n".join(body_paragraphs)
    if not title and body_paragraphs:
        title = body_paragraphs[0]
    if not body_paragraphs and body_text:
        body_paragraphs = split_paragraphs(body_text)
    if not body_text and body_paragraphs:
        body_text = "\n\n".join(body_paragraphs)
    if not title:
        warnings.append("missing_title")
    if not body_text:
        warnings.append("missing_body_text")

    return ExtractedContent(
        adapter_id=_safe_id_text(adapter_id, fallback="unknown_adapter"),
        source_url=_safe_text(source_url),
        artifact_filename=_safe_basename(artifact_filename),
        artifact_role=_safe_id_text(artifact_role, fallback="article_html_or_text"),
        title=title,
        body_text=body_text,
        body_paragraphs=body_paragraphs,
        extraction_method=method,
        source_domain=urlparse(_safe_text(source_url)).netloc.lower(),
        warnings=warnings,
    )


def _artifact_from_dict(item: dict[str, Any]) -> SourceContentArtifact | None:
    role = _safe_text(item.get("role") or item.get("artifact_role") or item.get("type"))
    path = _safe_text(item.get("path") or item.get("file_path") or item.get("artifact_path") or item.get("source_path"))
    filename = _safe_text(item.get("filename") or item.get("name")) or None
    if not role:
        return None
    if not path and filename:
        path = filename
    if not path:
        return None
    return SourceContentArtifact(role=role, path=path, filename=filename)


def extract_artifacts_from_collection_payload(payload: dict[str, Any]) -> list[SourceContentArtifact]:
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
    artifacts: list[SourceContentArtifact] = []
    for item in candidates:
        artifact = _artifact_from_dict(item)
        if artifact:
            artifacts.append(artifact)
    return artifacts


def load_artifact_collection(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def _select_content_artifact(artifacts: list[SourceContentArtifact]) -> SourceContentArtifact:
    if not artifacts:
        raise ValueError("at least one artifact is required")
    for artifact in artifacts:
        if artifact.role in TEXT_ROLE_CANDIDATES:
            return artifact
    for artifact in artifacts:
        if "article" in artifact.role or "content" in artifact.role or "dom" in artifact.role:
            return artifact
    return artifacts[0]


def build_source_content_extraction(
    *,
    adapter_id: str,
    source_url: str,
    artifacts: list[SourceContentArtifact],
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    selected = _select_content_artifact(artifacts)
    artifact_path = Path(selected.path)
    if not artifact_path.is_absolute() and base_dir is not None:
        artifact_path = Path(base_dir) / artifact_path
    raw = read_text_artifact(artifact_path)
    filename = selected.filename or artifact_path.name
    content = extract_content_from_artifact_text(
        raw,
        adapter_id=adapter_id,
        source_url=source_url,
        artifact_filename=filename,
        artifact_role=selected.role,
    )
    body_hash = _sha256_text(content.body_text)
    content_id = ".".join(
        [
            _safe_id_text(content.adapter_id, fallback="adapter"),
            "content",
            body_hash[:12],
        ]
    )
    artifact_summaries = []
    for artifact in artifacts:
        name = artifact.filename or Path(artifact.path).name
        artifact_summaries.append(
            {
                "role": _safe_id_text(artifact.role, fallback="artifact"),
                "filename": _safe_basename(name),
                "selected_for_content": artifact is selected,
            }
        )
    extraction = {
        "schema_version": SCHEMA_VERSION,
        "content_id": content_id,
        "adapter_id": content.adapter_id,
        "source_url": content.source_url,
        "source_domain": content.source_domain,
        "selected_artifact": {
            "role": content.artifact_role,
            "filename": content.artifact_filename,
        },
        "artifacts": artifact_summaries,
        "title": content.title,
        "body_text": content.body_text,
        "body_paragraphs": content.body_paragraphs,
        "body_paragraph_count": len(content.body_paragraphs),
        "body_sha256": body_hash,
        "extraction_method": content.extraction_method,
        "warnings": content.warnings,
        "operator_summary": {
            "live_network_used": False,
            "folder_scan_used": False,
            "full_local_paths_serialized": False,
            "status": "CONTENT_EXTRACTED_FROM_EXPLICIT_ARTIFACT",
        },
    }
    extraction["extraction_handoff"] = {
        "schema_version": "source_content_extraction_handoff_v1",
        "content_id": content_id,
        "adapter_id": content.adapter_id,
        "source_url": content.source_url,
        "title": content.title,
        "body_sha256": body_hash,
        "next_stage": "source_comment_extraction_or_capture_bundle",
        "required_next_inputs": [
            "comments_json_or_text when comments are available",
            "content_extraction_json",
            "artifact_collection_manifest_json",
        ],
    }
    return extraction


def build_source_content_extraction_from_collection(
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
    return build_source_content_extraction(
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
