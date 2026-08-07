from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = "lightweight_in_app_browser_capture_v1"
PACKAGE_SCHEMA_VERSION = "lightweight_in_app_browser_capture_package_v1"
APPROVAL_PREFIX = "APPROVE_LIGHTWEIGHT_BROWSER"
DEFAULT_ARTIFACT_ROLES = (
    "article_html_or_text",
    "comments_json_or_text",
    "dom_snapshot",
    "screenshot",
    "metadata_json",
)


class LightweightBrowserCaptureError(ValueError):
    pass


def _normalise_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def _safe_id(value: Any, fallback: str = "item") -> str:
    text = _normalise_text(value).lower()
    text = re.sub(r"[^a-z0-9_.-]+", ".", text).strip("._-")
    text = re.sub(r"\.{2,}", ".", text)
    return text or fallback


def _stable_hash(payload: Any, length: int = 12) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_normalise_text(value)] if _normalise_text(value) else []
    if isinstance(value, Iterable):
        return [_normalise_text(item) for item in value if _normalise_text(item)]
    text = _normalise_text(value)
    return [text] if text else []


def _host_matches(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower().strip(".")
    return host == domain or host.endswith("." + domain)


def validate_operator_url(source_url: str, allowed_domains: Iterable[str]) -> dict[str, Any]:
    url = _normalise_text(source_url)
    parsed = urlparse(url)
    issues: list[str] = []
    if parsed.scheme not in {"http", "https"}:
        issues.append("source_url must use http or https")
    if not parsed.netloc:
        issues.append("source_url must include a network location")
    domains = _as_list(allowed_domains)
    host = (parsed.hostname or "").lower()
    if domains and not any(_host_matches(host, domain) for domain in domains):
        issues.append("source_url host is not covered by adapter domains")
    return {
        "source_url": url,
        "scheme": parsed.scheme,
        "host": host,
        "allowed_domains": domains,
        "valid": not issues,
        "issues": issues,
    }


def normalise_adapter_spec(adapter: dict[str, Any]) -> dict[str, Any]:
    adapter_id = _safe_id(adapter.get("adapter_id") or adapter.get("id"), "adapter")
    domains = _as_list(adapter.get("domains"))
    artifact_roles = _as_list(adapter.get("artifact_roles")) or list(DEFAULT_ARTIFACT_ROLES)
    capture_surfaces = _as_list(adapter.get("capture_surfaces"))
    url_patterns = _as_list(adapter.get("url_patterns"))
    return {
        "schema_version": "source_adapter_binding_v1",
        "adapter_id": adapter_id,
        "display_name": _normalise_text(adapter.get("display_name")) or adapter_id.replace("_", " ").title(),
        "domains": domains,
        "url_patterns": url_patterns,
        "source_kind": _normalise_text(adapter.get("source_kind")) or "web",
        "operator_only": bool(adapter.get("operator_only", True)),
        "requires_lightweight_browser": bool(adapter.get("requires_lightweight_browser", True)),
        "capture_surfaces": capture_surfaces,
        "artifact_roles": artifact_roles,
        "extraction_notes": _as_list(adapter.get("extraction_notes")),
    }


def make_approval_token(browser_job_id: str) -> str:
    return f"{APPROVAL_PREFIX}:{browser_job_id}"


def build_capture_job(
    adapter: dict[str, Any],
    source_url: str,
    *,
    job_label: str = "operator_capture",
    requested_artifacts: Iterable[str] | None = None,
    render_wait_ms: int = 3000,
    viewport: str = "1365x768",
    full_page_screenshot: bool = True,
    approval_token: str | None = None,
) -> dict[str, Any]:
    spec = normalise_adapter_spec(adapter)
    url_validation = validate_operator_url(source_url, spec["domains"])
    if not url_validation["valid"]:
        raise LightweightBrowserCaptureError("; ".join(url_validation["issues"]))
    if render_wait_ms < 0 or render_wait_ms > 120000:
        raise LightweightBrowserCaptureError("render_wait_ms must be between 0 and 120000")
    requested = _as_list(requested_artifacts) or list(spec["artifact_roles"])
    unsupported = [role for role in requested if role not in spec["artifact_roles"]]
    if unsupported:
        raise LightweightBrowserCaptureError("requested artifact role is not supported by adapter: " + ", ".join(unsupported))

    job_seed = {
        "adapter_id": spec["adapter_id"],
        "source_url": url_validation["source_url"],
        "job_label": _safe_id(job_label, "operator_capture"),
        "requested_artifacts": requested,
        "render_wait_ms": int(render_wait_ms),
        "viewport": viewport,
        "full_page_screenshot": bool(full_page_screenshot),
    }
    browser_job_id = f"{spec['adapter_id']}.browser_capture.{_stable_hash(job_seed)}"
    required_token = make_approval_token(browser_job_id)
    approved = approval_token == required_token
    artifact_targets = [
        {
            "role": role,
            "filename": f"{browser_job_id}.{_safe_id(role)}.operator_supplied",
            "required": role in {"article_html_or_text", "dom_snapshot", "metadata_json"},
            "operator_supplied": True,
        }
        for role in requested
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "browser_job_id": browser_job_id,
        "adapter": spec,
        "source_url": url_validation["source_url"],
        "url_validation": url_validation,
        "job_label": _safe_id(job_label, "operator_capture"),
        "approval_required": True,
        "approval_token": required_token,
        "approval_token_supplied": bool(approval_token),
        "approval_status": "APPROVED_OPERATOR_READY" if approved else "WAITING_FOR_OPERATOR_APPROVAL",
        "live_network_default": False,
        "manual_or_live_actions_started": False,
        "render_wait_ms": int(render_wait_ms),
        "viewport": viewport,
        "full_page_screenshot": bool(full_page_screenshot),
        "artifact_targets": artifact_targets,
        "operator_steps": [
            "Review the source URL and adapter binding before using the launch script.",
            "Run the generated .cmd with the exact approval token only when live navigation is approved.",
            "Save DOM/text, screenshot, metadata, and comments artifacts into the requested target files.",
            "Feed saved artifacts into the shared extraction/capture bundle pipeline.",
        ],
    }


def build_devtools_snippets(job: dict[str, Any]) -> dict[str, str]:
    prefix = _safe_id(job.get("browser_job_id"), "browser_capture")
    dom_json = {
        "schema_version": "operator_dom_snapshot_v1",
        "browser_job_id": job.get("browser_job_id"),
        "source_url": job.get("source_url"),
    }
    dom_header = json.dumps(dom_json, ensure_ascii=False, sort_keys=True)
    dom_snapshot = f"""// {prefix} DOM snapshot helper. Operator runs manually after approval.\n(() => {{\n  const payload = {dom_header};\n  payload.title = document.title || '';\n  payload.location = String(location.href);\n  payload.text = document.body ? document.body.innerText : '';\n  payload.html = document.documentElement ? document.documentElement.outerHTML : '';\n  copy(JSON.stringify(payload, null, 2));\n  return payload;\n}})();\n"""
    shadow_scan = f"""// {prefix} shadow-root text scanner. Operator runs manually when a source uses shadow roots.\n(() => {{\n  const rows = [];\n  const walk = (node, path) => {{\n    if (!node) return;\n    if (node.shadowRoot) {{\n      rows.push({{ path, text: node.shadowRoot.innerText || '', html: node.shadowRoot.innerHTML || '' }});\n      node.shadowRoot.querySelectorAll('*').forEach((child, index) => walk(child, `${{path}} > shadow *:nth(${{index}})`));\n    }}\n    if (node.querySelectorAll) node.querySelectorAll('*').forEach((child, index) => walk(child, `${{path}} > *:nth(${{index}})`));\n  }};\n  walk(document.documentElement, 'html');\n  const payload = {{ schema_version: 'operator_shadow_root_scan_v1', browser_job_id: '{job.get('browser_job_id')}', source_url: '{job.get('source_url')}', rows }};\n  copy(JSON.stringify(payload, null, 2));\n  return payload;\n}})();\n"""
    metadata = f"""// {prefix} metadata helper. Operator runs manually after approval.\n(() => {{\n  const metas = Array.from(document.querySelectorAll('meta')).map((m) => ({{\n    name: m.getAttribute('name') || '',\n    property: m.getAttribute('property') || '',\n    content: m.getAttribute('content') || ''\n  }}));\n  const payload = {{ schema_version: 'operator_page_metadata_v1', browser_job_id: '{job.get('browser_job_id')}', source_url: String(location.href), title: document.title || '', metas }};\n  copy(JSON.stringify(payload, null, 2));\n  return payload;\n}})();\n"""
    return {
        "dom_snapshot_js": dom_snapshot,
        "shadow_root_scan_js": shadow_scan,
        "metadata_js": metadata,
    }


def build_windows_launch_script(job: dict[str, Any]) -> str:
    token = job["approval_token"]
    url = job["source_url"].replace('"', "")
    wait_ms = int(job.get("render_wait_ms", 3000))
    return f"""@echo off\r\nsetlocal\r\nif "%~1" NEQ "{token}" (\r\n  echo Approval token missing or incorrect.\r\n  echo Expected: {token}\r\n  exit /b 2\r\n)\r\necho Approved operator browser capture job: {job['browser_job_id']}\r\necho URL: {url}\r\necho Render wait target: {wait_ms} ms\r\nstart "" "{url}"\r\necho Browser opened by explicit operator approval. Save artifacts using the generated snippets/templates.\r\nexit /b 0\r\n"""


def build_artifact_manifest_template(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lightweight_in_app_browser_artifact_manifest_template_v1",
        "browser_job_id": job["browser_job_id"],
        "adapter_id": job["adapter"]["adapter_id"],
        "source_url": job["source_url"],
        "manual_or_live_actions_started": False,
        "operator_notes": "Fill this after approved capture. Do not claim artifacts exist until saved.",
        "expected_artifacts": job["artifact_targets"],
        "saved_artifacts": [],
    }


def build_capture_package(
    adapter: dict[str, Any],
    source_url: str,
    *,
    job_label: str = "operator_capture",
    requested_artifacts: Iterable[str] | None = None,
    render_wait_ms: int = 3000,
    viewport: str = "1365x768",
    full_page_screenshot: bool = True,
    approval_token: str | None = None,
) -> dict[str, Any]:
    job = build_capture_job(
        adapter,
        source_url,
        job_label=job_label,
        requested_artifacts=requested_artifacts,
        render_wait_ms=render_wait_ms,
        viewport=viewport,
        full_page_screenshot=full_page_screenshot,
        approval_token=approval_token,
    )
    package_seed = {
        "browser_job_id": job["browser_job_id"],
        "adapter_id": job["adapter"]["adapter_id"],
        "source_url": job["source_url"],
    }
    package_id = f"{job['adapter']['adapter_id']}.lightweight_browser_package.{_stable_hash(package_seed)}"
    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_id": package_id,
        "browser_job_id": job["browser_job_id"],
        "adapter_id": job["adapter"]["adapter_id"],
        "source_url": job["source_url"],
        "capture_job": job,
        "windows_launch_script": build_windows_launch_script(job),
        "devtools_snippets": build_devtools_snippets(job),
        "artifact_manifest_template": build_artifact_manifest_template(job),
        "safety": {
            "live_network_default": False,
            "approval_required_before_navigation": True,
            "tests_must_not_open_browser": True,
            "no_archive_submission": True,
            "no_content_success_claim": True,
        },
    }
    package["verification"] = verify_capture_package(package)
    return package


def verify_capture_package(package: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    job = package.get("capture_job") or {}
    if package.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        issues.append("unexpected package schema_version")
    if not package.get("package_id"):
        issues.append("package_id is required")
    if not job.get("approval_required"):
        issues.append("capture job must require approval")
    if job.get("live_network_default") is not False:
        issues.append("live_network_default must be false")
    if job.get("manual_or_live_actions_started") is not False:
        issues.append("package must not claim manual or live actions started")
    if not str(job.get("approval_token", "")).startswith(APPROVAL_PREFIX + ":"):
        issues.append("approval token is missing")
    script = package.get("windows_launch_script", "")
    if job.get("approval_token") and job.get("approval_token") not in script:
        issues.append("launch script must gate on the approval token")
    if "start \"\"" in script and "%~1" not in script:
        issues.append("launch script opens a URL without argument-gated approval")
    artifact_targets = job.get("artifact_targets") or []
    if not artifact_targets:
        issues.append("artifact targets are required")
    for target in artifact_targets:
        filename = str(target.get("filename", ""))
        if ":\\" in filename or filename.startswith("/") or ".." in Path(filename).parts:
            issues.append("artifact target filename must be relative and safe")
    safety = package.get("safety") or {}
    if safety.get("no_content_success_claim") is not True:
        issues.append("package must not claim content capture success")
    return {
        "schema_version": "lightweight_in_app_browser_capture_verifier_v1",
        "package_id": package.get("package_id"),
        "browser_job_id": package.get("browser_job_id"),
        "adapter_id": package.get("adapter_id"),
        "verified": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def load_json_file(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LightweightBrowserCaptureError("JSON file must contain an object")
    return data
