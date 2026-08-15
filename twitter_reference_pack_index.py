from __future__ import annotations
import json, zipfile
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "twitter_reference_pack_index.v69"

@dataclass(frozen=True)
class ReferencePackCluster:
    cluster_id: str
    purpose: str
    matched_paths: tuple[str, ...]

@dataclass(frozen=True)
class ReferencePackIndex:
    schema_version: str
    source_path: str
    source_kind: str
    total_paths: int
    local_extension_archives: tuple[str, ...]
    high_priority_sources: tuple[str, ...]
    lower_priority_media_sources: tuple[str, ...]
    extra_capture_sources: tuple[str, ...]
    metadata_files: tuple[str, ...]
    license_files: tuple[str, ...]
    clusters: tuple[ReferencePackCluster, ...]
    def to_dict(self) -> dict[str, Any]:
        return _val(self)

def _val(v: Any) -> Any:
    if is_dataclass(v):
        return {k: _val(x) for k, x in asdict(v).items()}
    if isinstance(v, tuple):
        return [_val(x) for x in v]
    if isinstance(v, list):
        return [_val(x) for x in v]
    if isinstance(v, Mapping):
        return {str(k): _val(x) for k, x in v.items()}
    return v

def _paths(source: str | Path) -> tuple[str, ...]:
    p = Path(source)
    if p.is_file() and p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p, "r") as z:
            return tuple(sorted(n.replace("\\","/") for n in z.namelist() if not n.endswith("/")))
    if p.is_dir():
        return tuple(sorted(str(x.relative_to(p)).replace("\\","/") for x in p.rglob("*") if x.is_file()))
    raise FileNotFoundError(source)

def _top(paths: Iterable[str], folder: str) -> tuple[str, ...]:
    out = set()
    marker = f"/{folder}/"
    for raw in paths:
        path = "/" + raw.replace("\\","/")
        if marker in path:
            tail = path.split(marker, 1)[1]
            first = tail.split("/", 1)[0]
            if first:
                out.add(first)
    return tuple(sorted(out))

def _has(path: str, needles: Iterable[str]) -> bool:
    l = path.lower()
    return any(n.lower() in l for n in needles)

def _cluster(paths: tuple[str, ...], cid: str, purpose: str, needles: Iterable[str]) -> ReferencePackCluster:
    return ReferencePackCluster(cid, purpose, tuple(p for p in paths if _has(p, needles))[:200])

def build_reference_pack_index(source_path: str | Path) -> ReferencePackIndex:
    ps = _paths(source_path)
    clusters = (
        _cluster(ps, "twitter_api_export", "X/Twitter GraphQL/API/export, rule engine, user/list/media timeline references.", ("twitter-exporter","twitter-openapi","twitter-web-exporter","twitter-filter","xkit","clean-twitter","web-exporter","WebDataMaster")),
        _cluster(ps, "media_discovery_and_native_helper", "Browser media discovery, webRequest/webNavigation, native helper, ffmpeg/libav, downloader backend references.", ("Video Download Helper","Video Downloader Professional","vdhcoapp","video-downloader-pro","ffmpeg-online","libav.js")),
        _cluster(ps, "screenshot_render_pdf", "Full-page screenshots, rendered browser capture, HTML-to-image/PDF, article export, MCP/browser capture references.", ("GoFullPage","PageCap","full-page-screen-capture","pagecap","rendex-mcp","third-eye","SnapStream","link-to-screenshot","fast-html-to-pdf","webshot-api","x-article-exporter")),
    )
    return ReferencePackIndex(
        SCHEMA_VERSION,
        str(source_path),
        "zip" if Path(source_path).is_file() else "directory",
        len(ps),
        tuple(p for p in ps if "/01_local_browser_extension_archives/" in "/" + p),
        _top(ps, "02_high_priority_source_refs"),
        _top(ps, "03_lower_priority_media_refs"),
        _top(ps, "04_extra_source_refs"),
        tuple(p for p in ps if p.lower().endswith(".metadata.json") or p.lower().endswith("manifest.json"))[:500],
        tuple(p for p in ps if Path(p).name.lower() in {"license","license.txt","license.md","copying","copying.md"})[:500],
        clusters,
    )

def write_reference_pack_index(source_path: str | Path, output_path: str | Path) -> Path:
    idx = build_reference_pack_index(source_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(idx.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return out
