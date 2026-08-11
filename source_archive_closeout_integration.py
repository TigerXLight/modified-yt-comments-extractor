from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


SIDECAR_NAMES = (
    "memento_archive_discovery.json",
    "memento_archive_discovery.txt",
    "warcreate_style_interaction_metadata.json",
    "warcreate_style_interaction_metadata.txt",
)


def _get_value(obj: Any, names: Iterable[str]) -> Any:
    if obj is None:
        return None
    for name in names:
        if isinstance(obj, dict) and name in obj:
            value = obj.get(name)
            if value:
                return value
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value:
                return value
    return None


def normalize_closeout_url(value: str | None) -> str:
    """Normalize URLs that passed through CMD/Markdown escaping.

    The important production defect was literal ^& in target URLs.  This
    function strips CMD caret escapes and removes markdown wrapper noise when
    copied through chat or logs.
    """
    if not value:
        return ""
    text = str(value).strip().strip('"').strip("'")
    if text.startswith("[") and "](" in text and text.endswith(")"):
        start = text.find("](") + 2
        text = text[start:-1]
    text = text.replace("^&", "&")
    text = text.replace("\\&", "&")
    text = text.replace("%5E%26", "%26")
    text = text.replace("%5e%26", "%26")
    return text


def article_url_without_fragment(value: str | None) -> str:
    url = normalize_closeout_url(value)
    if not url:
        return ""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _coerce_path(value: Any) -> Path | None:
    if not value:
        return None
    try:
        path = Path(str(value))
    except Exception:
        return None
    return path


def resolve_archive_metadata_inputs(result: Any = None, args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None) -> dict[str, str]:
    kwargs = kwargs or {}

    output_root = _coerce_path(
        _get_value(kwargs, ("output_dir", "output_root", "root"))
        or _get_value(result, ("output_dir", "output_root", "root"))
    )

    if output_root is None:
        for name in ("html_export", "json_export", "comments_html", "comments_json", "rendered_page_html"):
            p = _coerce_path(_get_value(result, (name,)))
            if p:
                output_root = p.parent
                break

    if output_root is None and args:
        # Last-resort: a positional Path/string that already exists or looks like an output directory.
        for item in args:
            p = _coerce_path(item)
            if p and (p.exists() or "msn_" in str(p).lower()):
                output_root = p
                break

    if output_root is None:
        raise RuntimeError("archive metadata integration could not resolve output_root")

    target_url = (
        _get_value(kwargs, ("article_url", "target_url", "source_url", "comments_url", "url"))
        or _get_value(result, ("article_url", "target_url", "source_url", "comments_url", "url"))
    )
    target_url = article_url_without_fragment(str(target_url) if target_url else "")
    if not target_url:
        raise RuntimeError("archive metadata integration could not resolve target_url")

    capture_root = _coerce_path(
        _get_value(kwargs, ("capture_root", "live_capture_root"))
        or _get_value(result, ("capture_root", "live_capture_root"))
    )
    if capture_root is None:
        candidate = output_root / "live_capture"
        if candidate.exists():
            capture_root = candidate
    if capture_root is None:
        rendered = _coerce_path(_get_value(result, ("rendered_page_html",)))
        if rendered and rendered.exists():
            capture_root = rendered.parent
    if capture_root is None:
        capture_root = output_root / "live_capture"

    return {
        "output_root": str(output_root),
        "target_url": target_url,
        "capture_root": str(capture_root),
        "production_root": str(output_root),
    }


def _print_sidecar_paths(output_root: Path) -> None:
    for name in SIDECAR_NAMES:
        path = output_root / name
        label = name.upper().replace(".", "_")
        print(f"{label}: {path if path.exists() else ''}")


def attach_archive_metadata_to_closeout_result(result: Any = None, args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None) -> dict[str, str]:
    """Generate archive-discovery and WARCreate-style sidecars for a closeout.

    This is intentionally non-fatal for production closeout.  It writes sidecars
    if possible and prints their paths, but failure should not overturn an
    already honest capture/export decision.
    """
    inputs = resolve_archive_metadata_inputs(result=result, args=args, kwargs=kwargs)
    output_root = Path(inputs["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)

    cli = Path(__file__).resolve().parent / "source_archive_metadata_cli.py"
    if not cli.exists():
        raise RuntimeError(f"source_archive_metadata_cli.py not found: {cli}")

    cmd = [
        sys.executable,
        str(cli),
        "--target-url",
        inputs["target_url"],
        "--output-dir",
        inputs["output_root"],
        "--capture-root",
        inputs["capture_root"],
        "--production-root",
        inputs["production_root"],
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(cmd, cwd=str(Path(__file__).resolve().parent), text=True, capture_output=True, env=env)
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print("ARCHIVE_METADATA_STDERR: " + completed.stderr.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(f"archive metadata CLI failed with exit code {completed.returncode}")

    _print_sidecar_paths(output_root)

    if isinstance(result, dict):
        result["memento_archive_discovery_json"] = str(output_root / "memento_archive_discovery.json")
        result["memento_archive_discovery_txt"] = str(output_root / "memento_archive_discovery.txt")
        result["warcreate_style_interaction_metadata_json"] = str(output_root / "warcreate_style_interaction_metadata.json")
        result["warcreate_style_interaction_metadata_txt"] = str(output_root / "warcreate_style_interaction_metadata.txt")
    else:
        for attr, name in (
            ("memento_archive_discovery_json", "memento_archive_discovery.json"),
            ("memento_archive_discovery_txt", "memento_archive_discovery.txt"),
            ("warcreate_style_interaction_metadata_json", "warcreate_style_interaction_metadata.json"),
            ("warcreate_style_interaction_metadata_txt", "warcreate_style_interaction_metadata.txt"),
        ):
            try:
                setattr(result, attr, str(output_root / name))
            except Exception:
                pass
    return inputs
