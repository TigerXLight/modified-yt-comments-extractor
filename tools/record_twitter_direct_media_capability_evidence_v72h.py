from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

DIRECT_HOSTS = {"pbs.twimg.com", "video.twimg.com"}


def _load_json_maybe_wrapped(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(stripped[start : end + 1])


def _is_direct_media_url(url: str) -> bool:
    parsed = urlsplit(str(url or ""))
    return parsed.scheme.lower() in {"http", "https"} and (parsed.hostname or "").lower() in DIRECT_HOSTS


def _route_value(manifest: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key in manifest:
        return manifest.get(key, default)
    route = manifest.get("route_metadata")
    if isinstance(route, Mapping):
        return route.get(key, default)
    return default


def build_evidence(*, result_path: Path | None, manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json_maybe_wrapped(manifest_path)
    if not isinstance(manifest, Mapping):
        raise ValueError("Manifest was not a JSON object.")
    result: Mapping[str, Any] = {}
    if result_path is not None and result_path.is_file():
        loaded = _load_json_maybe_wrapped(result_path)
        if isinstance(loaded, Mapping):
            result = loaded

    source_url = str(manifest.get("source_url") or manifest.get("normalized_source_url") or "")
    if not _is_direct_media_url(source_url):
        raise ValueError(f"Manifest source_url is not a supported Twitter direct media URL: {source_url}")
    files = manifest.get("files") or []
    files_count = len(files) if isinstance(files, list) else int(manifest.get("files_count") or 0)
    status = str(manifest.get("status") or "")
    phase = str(manifest.get("phase") or "")
    api3128_used = bool(_route_value(manifest, "api3128_used", False))
    route_used = str(_route_value(manifest, "route_used", "") or "")
    tested = status == "success" and files_count >= 1 and api3128_used and route_used.lower() == "api3128"
    if not tested:
        raise ValueError(
            "Direct media JD test was not a passing API3128 success: "
            f"status={status!r} files_count={files_count} api3128_used={api3128_used!r} route_used={route_used!r}"
        )
    parsed = urlsplit(source_url)
    return {
        "schema_version": "twitter_direct_media_jd_capability_evidence.v72h",
        "tested": True,
        "source_url": source_url,
        "observed_host": str(parsed.hostname or ""),
        "status": status,
        "phase": phase,
        "files_count": files_count,
        "api3128_used": api3128_used,
        "route_used": route_used,
        "manifest_path": str(manifest_path),
        "result_path": str(result_path or ""),
        "result_status": str(result.get("status") or ""),
        "evidence_source": "live_jdownloader_api3128_direct_twitter_media_test",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record YTCE direct Twitter media JD/API3128 capability evidence from a successful real-run manifest.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", default="")
    parser.add_argument("--output", default="twitter_direct_media_jd_capability_evidence.json")
    args = parser.parse_args()
    result_path = Path(args.result) if args.result else None
    evidence = build_evidence(result_path=result_path, manifest_path=Path(args.manifest))
    output = Path(args.output)
    output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"WROTE {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
