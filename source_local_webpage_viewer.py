from __future__ import annotations

import hashlib
import html
import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


LOCAL_WEBPAGE_VIEWER_SCHEMA_VERSION = "source_local_webpage_viewer_v1"
LOCAL_VIEWER_READY = "LOCAL_VIEWER_READY"
LOCAL_VIEWER_PARTIAL = "LOCAL_VIEWER_PARTIAL"


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_file(path)


def _relative_link(from_dir: Path, target: Path) -> str:
    return Path(os.path.relpath(target.resolve(), start=from_dir.resolve())).as_posix()


@dataclass(frozen=True)
class LocalViewerLinkedFile:
    label: str
    relative_href: str
    sha256: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class LocalWebpageViewerResult:
    status: str
    viewer_dir: str
    index_path: str
    index_sha256: str
    manifest_path: str
    manifest_sha256: str
    open_cmd_path: str
    edge_app_cmd_path: str
    readme_path: str
    linked_files: tuple[LocalViewerLinkedFile, ...] = ()
    errors: tuple[str, ...] = ()
    schema_version: str = LOCAL_WEBPAGE_VIEWER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _known_capture_files(capture_dir: Path) -> tuple[tuple[str, Path], ...]:
    candidates: list[tuple[str, Path]] = [
        ("Best viewable page: rendered-page.html", capture_dir / "rendered-page.html"),
        ("ReplayWeb partial archive: rendered-page.warc.gz", capture_dir / "rendered-page.warc.gz"),
        ("Raw WARC source: rendered-page.warc", capture_dir / "rendered-page.warc"),
        ("Strict WACZ: experimental/possibly unsupported", capture_dir / "archive.viewable-live-capture.wacz"),
        ("ReplayWeb-compatible WACZ: preferred when valid", capture_dir / "archive.replayweb-compatible.wacz"),
        ("Validation JSON", capture_dir / "validation.json"),
        ("Capture manifest", capture_dir / "capture-manifest.json"),
        ("Static evidence view", capture_dir / "static-evidence.html"),
        ("Static page view", capture_dir / "static-page-view.html"),
        ("Static text view", capture_dir / "static-text-view.html"),
        ("Static page text Markdown", capture_dir / "static-page-text.md"),
    ]
    screenshot_dir = capture_dir / "screenshots"
    for name in ("article-top.png", "full-page.png", "comments-region.png", "full-comments-thread.png"):
        candidates.append((f"Screenshot: {name}", screenshot_dir / name))
    for path in sorted(capture_dir.glob("msn-comments-v35-profile-stats*")):
        if path.is_file() and path.suffix.lower() in {".json", ".txt", ".md", ".html", ".csv"}:
            candidates.append((f"MSN comments/profile export: {path.name}", path))
    return tuple(candidates)


def _link_rows(links: Sequence[LocalViewerLinkedFile]) -> str:
    if not links:
        return "<p>No matching files were present when the local viewer was generated.</p>"
    rows = []
    for item in links:
        digest = f"<code>{html.escape(item.sha256)}</code>" if item.sha256 else "not recorded"
        rows.append(
            "<li>"
            f"<a href=\"{html.escape(item.relative_href)}\">{html.escape(item.label)}</a>"
            f" <span class=\"meta\">{int(item.size_bytes)} bytes; SHA-256 {digest}</span>"
            "</li>"
        )
    return "<ul>" + "".join(rows) + "</ul>"


def _validation_preview(path: Path) -> str:
    if not path.is_file():
        return "validation.json was not present when this viewer was generated."
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > 12000:
        text = text[:12000] + "\n... truncated for local viewer preview ..."
    return text


def _build_index_html(
    *,
    source_url: str,
    capture_dir_name: str,
    links: Sequence[LocalViewerLinkedFile],
    validation_preview: str,
) -> str:
    primary = [item for item in links if item.label in {"Best viewable page: rendered-page.html", "Validation JSON", "Capture manifest"}]
    replay = [item for item in links if "WARC" in item.label or "WACZ" in item.label]
    screenshots = [item for item in links if item.label.startswith("Screenshot:")]
    text_meta = [item for item in links if item not in primary and item not in replay and item not in screenshots]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Local MSN Capture Viewer</title>
  <style>
    body {{ margin: 0; background: #171717; color: #f4f4f4; font-family: Arial, sans-serif; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 28px 18px 60px; }}
    a {{ color: #74b9ff; }}
    header {{ border-bottom: 1px solid #3a3a3a; margin-bottom: 20px; padding-bottom: 16px; }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    details {{ background: #222; border: 1px solid #3a3a3a; border-radius: 8px; margin: 12px 0; padding: 12px 14px; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    code, pre {{ background: #111; color: #eee; border-radius: 6px; }}
    code {{ padding: 1px 4px; }}
    pre {{ overflow: auto; padding: 12px; white-space: pre-wrap; }}
    .meta {{ color: #bdbdbd; font-size: 12px; }}
    .warning {{ background: #302400; border: 1px solid #7d6500; color: #ffeaa7; padding: 12px; border-radius: 8px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Local MSN Capture Viewer</h1>
    <p><strong>Source URL:</strong><br>{html.escape(source_url)}</p>
    <p><strong>Capture output folder:</strong> {html.escape(capture_dir_name)}</p>
    <p class="warning">This is an offline local review launcher/index. It is not a new browser engine and does not prove ReplayWeb or dynamic MSN runtime visual success.</p>
  </header>
  <details open><summary>Primary files</summary>{_link_rows(primary)}</details>
  <details open><summary>Best viewable page</summary>{_link_rows([item for item in primary if item.label == "Best viewable page: rendered-page.html"])}</details>
  <details><summary>ReplayWeb files</summary>
    <p class="meta">Use <code>rendered-page.warc.gz</code> as the partial/useful ReplayWeb archive candidate. The strict WACZ is preserved but experimental/possibly unsupported; use a ReplayWeb-compatible WACZ only when present and manually validated.</p>
    {_link_rows(replay)}
  </details>
  <details><summary>Screenshots</summary>{_link_rows(screenshots)}</details>
  <details><summary>Text / metadata files</summary>{_link_rows(text_meta)}</details>
  <details><summary>Manual validation checklist</summary>
    <ul>
      <li>Open <code>rendered-page.html</code> and record article/comments visibility.</li>
      <li>Open <code>rendered-page.warc.gz</code> in ReplayWeb.page and record whether the page opens.</li>
      <li>Open <code>archive.viewable-live-capture.wacz</code> in ReplayWeb.page separately as an experimental strict-WACZ check.</li>
      <li>Open <code>archive.replayweb-compatible.wacz</code> when present; it is the preferred WACZ candidate, but still requires manual validation.</li>
      <li>Record privacy modal, slow-page warning, and Archived Page Not Found states in <code>validation.json</code> only after manual viewing.</li>
    </ul>
  </details>
  <details><summary>Runtime / replay notes</summary>
    <p>ReplayWeb/browser visual success remains manual-review-only until the user verifies the generated files.</p>
  </details>
  <details><summary>Validation JSON preview</summary><pre>{html.escape(validation_preview)}</pre></details>
</main>
</body>
</html>
"""


def write_local_webpage_viewer(
    *,
    capture_output_dir: str | Path,
    source_url: str,
    viewer_dir: str | Path | None = None,
) -> LocalWebpageViewerResult:
    capture_dir = Path(capture_output_dir)
    target_dir = Path(viewer_dir) if viewer_dir else capture_dir / "local_viewer"
    target_dir.mkdir(parents=True, exist_ok=True)
    links: list[LocalViewerLinkedFile] = []
    errors: list[str] = []
    for label, path in _known_capture_files(capture_dir):
        if not path.is_file():
            continue
        try:
            href = _relative_link(target_dir, path)
        except Exception:
            errors.append(f"could not create relative link for {path.name}")
            continue
        links.append(
            LocalViewerLinkedFile(
                label=label,
                relative_href=href,
                sha256=_sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    index_html = _build_index_html(
        source_url=source_url,
        capture_dir_name=capture_dir.name,
        links=tuple(links),
        validation_preview=_validation_preview(capture_dir / "validation.json"),
    )
    index_path = target_dir / "local-viewer-index.html"
    index_sha = _write_text(index_path, index_html)
    open_cmd_path = target_dir / "open_local_viewer.cmd"
    open_cmd_sha = _write_text(
        open_cmd_path,
        '@echo off\r\nstart "" "%~dp0local-viewer-index.html"\r\n',
    )
    edge_cmd_path = target_dir / "open_local_viewer_edge_app.cmd"
    edge_cmd_sha = _write_text(
        edge_cmd_path,
        '@echo off\r\n'
        'setlocal\r\n'
        'set "VIEWER=%~dp0local-viewer-index.html"\r\n'
        'where msedge.exe >nul 2>nul\r\n'
        'if %ERRORLEVEL% EQU 0 (\r\n'
        '  set "VIEWER_URL=file:///%VIEWER:\\=/%"\r\n'
        '  start "" msedge.exe --app="%VIEWER_URL%"\r\n'
        ') else (\r\n'
        '  start "" "%VIEWER%"\r\n'
        ')\r\n'
        'endlocal\r\n',
    )
    readme_path = target_dir / "README_LOCAL_VIEWER.txt"
    readme_sha = _write_text(
        readme_path,
        "Local MSN Capture Viewer\r\n\r\n"
        "Open open_local_viewer.cmd for the default browser, or open_local_viewer_edge_app.cmd for Edge app mode.\r\n"
        "This viewer is an offline index over generated local capture files. It does not perform network access.\r\n",
    )
    manifest_path = target_dir / "local-viewer-manifest.json"
    manifest = {
        "schema_version": LOCAL_WEBPAGE_VIEWER_SCHEMA_VERSION,
        "status": LOCAL_VIEWER_READY if links else LOCAL_VIEWER_PARTIAL,
        "source_url": source_url,
        "capture_output_dir_name": capture_dir.name,
        "index_file": index_path.name,
        "index_sha256": index_sha,
        "open_cmd_file": open_cmd_path.name,
        "open_cmd_sha256": open_cmd_sha,
        "edge_app_cmd_file": edge_cmd_path.name,
        "edge_app_cmd_sha256": edge_cmd_sha,
        "readme_file": readme_path.name,
        "readme_sha256": readme_sha,
        "linked_files": [item.to_dict() for item in links],
        "errors": errors,
        "network_access_performed": False,
        "browser_engine_implemented": False,
    }
    manifest_sha = _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return LocalWebpageViewerResult(
        status=LOCAL_VIEWER_READY if links else LOCAL_VIEWER_PARTIAL,
        viewer_dir=str(target_dir),
        index_path=str(index_path),
        index_sha256=index_sha,
        manifest_path=str(manifest_path),
        manifest_sha256=manifest_sha,
        open_cmd_path=str(open_cmd_path),
        edge_app_cmd_path=str(edge_cmd_path),
        readme_path=str(readme_path),
        linked_files=tuple(links),
        errors=tuple(errors),
    )
