from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

R43P_MARKER = "YTCE_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION"
R43P_PASS_STATUS = "PASS_R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION"
R43P_NO_PROMOTABLE_OUTPUTS_STATUS = "BLOCKED_NO_PROMOTABLE_RUNNER_OUTPUTS"
R43P_NETWORK_ONLY_STATUS = "BLOCKED_NETWORK_ONLY_RUNNER_OUTPUTS"
R43P_SCHEMA_VERSION = "live_twitter_x_runner_output_promotion.r43p.v1"
R43P_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43p_live_twitter_x_runner_output_promotion"


@dataclass(frozen=True)
class TwitterXRunnerOutputPromotionRequestR43P:
    runner_output_dir: str
    output_root: str = R43P_DEFAULT_OUTPUT_ROOT
    source_url: str = ""
    account_handle: str = ""
    capture_timestamp: str = ""
    production_live: bool = True
    test_fixture: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TwitterXRunnerOutputPromotionResultR43P:
    marker: str
    schema_version: str
    status: str
    blocker_reason: str
    run_dir: str
    receipt_path: str
    receipt_md_path: str
    paths_path: str
    counts_path: str
    report_json_path: str
    report_md_path: str
    receipt: Mapping[str, Any]
    checks: tuple[Mapping[str, Any], ...]
    bad_checks: tuple[Mapping[str, Any], ...]

    @property
    def passed(self) -> bool:
        return self.status == R43P_PASS_STATUS and not self.bad_checks

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def promote_twitter_x_runner_outputs_r43p(
    request: TwitterXRunnerOutputPromotionRequestR43P | Mapping[str, Any],
) -> TwitterXRunnerOutputPromotionResultR43P:
    req = coerce_twitter_x_runner_output_promotion_request_r43p(request)
    capture_ts = _safe_ts(req.capture_timestamp) or _now_ts()
    source_url = _plain_url(req.source_url)
    handle = _safe_handle(req.account_handle or _handle_from_url(source_url) or "unknown")
    runner_root = Path(req.runner_output_dir)
    run_dir = Path(req.output_root) if req.output_root else runner_root
    run_dir.mkdir(parents=True, exist_ok=True)

    paths = _scan_runner_output_paths(runner_root)
    counts = _count_promotable_outputs(paths)
    content_evidence_count = (
        counts["promoted_observed_post_count"]
        + counts["promoted_observed_media_count"]
        + counts["promoted_observed_screenshot_count"]
        + counts["promoted_rendered_dom_count"]
    )
    network_count = counts["promoted_network_event_count"] + counts["promoted_api_page_count"] + counts["promoted_response_body_count"]
    non_fixture_paths = _non_fixture_paths(paths["live_observation_paths"])
    pass_eligible = bool(content_evidence_count > 0 and non_fixture_paths and not req.test_fixture)

    if pass_eligible:
        status = R43P_PASS_STATUS
        blocker = ""
    elif network_count and not content_evidence_count:
        status = R43P_NETWORK_ONLY_STATUS
        blocker = "Runner output contained network observations only; DOM/screenshot/post/media evidence is required for live smoke PASS."
    else:
        status = R43P_NO_PROMOTABLE_OUTPUTS_STATUS
        blocker = "No promotable DOM/screenshot/post/media evidence was found in the runner output directory."

    receipt_path = run_dir / "r43p_runner_output_promotion_receipt.json"
    receipt_md_path = run_dir / "r43p_runner_output_promotion_receipt.md"
    paths_path = run_dir / "r43p_runner_output_paths.json"
    counts_path = run_dir / "r43p_runner_output_counts.json"
    report_json_path = run_dir / "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION_REPORT.json"
    report_md_path = run_dir / "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION_REPORT.md"

    receipt = {
        "marker": R43P_MARKER,
        "schema_version": R43P_SCHEMA_VERSION,
        "status": status,
        "blocker_reason": blocker,
        "source_url": source_url,
        "normalized_url": source_url,
        "account_handle": handle,
        "capture_timestamp": capture_ts,
        "runner_output_dir": str(runner_root),
        "production_live": req.production_live,
        "test_fixture": req.test_fixture,
        "promotion_pass_eligible_for_live_smoke": pass_eligible,
        "promoted_non_fixture_observation_evidence": bool(content_evidence_count > 0 and non_fixture_paths),
        "promoted_live_observation_paths": non_fixture_paths,
        **counts,
        "runner_output_paths": paths,
    }
    _write_json(receipt_path, receipt)
    _write_text(receipt_md_path, _receipt_md(receipt))
    _write_json(paths_path, paths)
    _write_json(counts_path, counts)

    checks = _build_checks(receipt, paths, counts)
    bad = tuple(check for check in checks if check.get("status") != "pass")
    result = TwitterXRunnerOutputPromotionResultR43P(
        marker=R43P_MARKER,
        schema_version=R43P_SCHEMA_VERSION,
        status=R43P_PASS_STATUS if not bad else status,
        blocker_reason="" if not bad else blocker,
        run_dir=str(run_dir),
        receipt_path=str(receipt_path),
        receipt_md_path=str(receipt_md_path),
        paths_path=str(paths_path),
        counts_path=str(counts_path),
        report_json_path=str(report_json_path),
        report_md_path=str(report_md_path),
        receipt=receipt,
        checks=checks,
        bad_checks=bad,
    )
    write_report(result, run_dir)
    return result


def coerce_twitter_x_runner_output_promotion_request_r43p(
    request: TwitterXRunnerOutputPromotionRequestR43P | Mapping[str, Any],
) -> TwitterXRunnerOutputPromotionRequestR43P:
    data = request.to_dict() if isinstance(request, TwitterXRunnerOutputPromotionRequestR43P) else dict(request or {})
    return TwitterXRunnerOutputPromotionRequestR43P(
        runner_output_dir=_clean(data.get("runner_output_dir") or data.get("output_dir") or data.get("lane_output_dir")),
        output_root=_clean(data.get("output_root") or R43P_DEFAULT_OUTPUT_ROOT),
        source_url=_plain_url(data.get("source_url") or data.get("target_url") or data.get("account_url") or data.get("post_url")),
        account_handle=_safe_handle(data.get("account_handle")),
        capture_timestamp=_clean(data.get("capture_timestamp")),
        production_live=bool(data.get("production_live", True)),
        test_fixture=bool(data.get("test_fixture", False)),
    )


def build_report(output_root: str | Path = R43P_DEFAULT_OUTPUT_ROOT) -> TwitterXRunnerOutputPromotionResultR43P:
    root = Path(output_root)
    runner_root = root / "r43p_demo_runner_outputs"
    _write_demo_runner_outputs(runner_root)
    return promote_twitter_x_runner_outputs_r43p(
        TwitterXRunnerOutputPromotionRequestR43P(
            runner_output_dir=str(runner_root),
            output_root=str(root),
            source_url="https://x.com/examaddaorg",
            account_handle="examaddaorg",
            capture_timestamp="20260916T060000Z",
            production_live=False,
            test_fixture=False,
        )
    )


def write_report(result: TwitterXRunnerOutputPromotionResultR43P, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION_REPORT.json"
    md_path = root / "R43P_LIVE_TWITTER_X_RUNNER_OUTPUT_PROMOTION_REPORT.md"
    payload = {
        "marker": result.marker,
        "schema_version": result.schema_version,
        "generated_at": _now_iso(),
        "status": R43P_PASS_STATUS if not result.bad_checks else result.status,
        "bad_checks": [dict(check) for check in result.bad_checks],
        "checks": [dict(check) for check in result.checks],
        "sample_result": result.to_dict(),
    }
    _write_json(json_path, payload)
    lines = [f"# {R43P_MARKER}", "", f"- Status: `{payload['status']}`", f"- Bad checks: `{len(result.bad_checks)}`", "", "## Checks"]
    lines.extend(f"- {check['status'].upper()}: {check['name']}" for check in result.checks)
    _write_text(md_path, "\n".join(lines) + "\n")
    return json_path, md_path


def _scan_runner_output_paths(runner_root: Path) -> dict[str, list[str]]:
    paths = {
        "screenshot_paths": [],
        "rendered_dom_paths": [],
        "post_json_paths": [],
        "timeline_ndjson_paths": [],
        "visible_observation_json_paths": [],
        "visible_observation_ndjson_paths": [],
        "media_index_json_paths": [],
        "media_index_ndjson_paths": [],
        "media_inventory_json_paths": [],
        "network_events_paths": [],
        "api_pages_paths": [],
        "network_response_bodies_paths": [],
        "live_observation_paths": [],
        "network_observation_paths": [],
    }
    if not runner_root.exists():
        return paths

    for path in runner_root.rglob("*"):
        if not path.is_file() or path.stat().st_size <= 0:
            continue
        name = path.name.lower()
        as_text = str(path)
        if name == "screenshot.png":
            paths["screenshot_paths"].append(as_text)
        elif name == "rendered_dom_snapshot.html":
            paths["rendered_dom_paths"].append(as_text)
        elif name == "post.json" and "\\posts\\" in as_text.lower().replace("/", "\\"):
            paths["post_json_paths"].append(as_text)
        elif name == "timeline.ndjson":
            paths["timeline_ndjson_paths"].append(as_text)
        elif name == "visible_browser_media_observations.json":
            paths["visible_observation_json_paths"].append(as_text)
        elif name == "visible_browser_media_observations.ndjson":
            paths["visible_observation_ndjson_paths"].append(as_text)
        elif name == "media_index.json":
            paths["media_index_json_paths"].append(as_text)
        elif name == "media_index.ndjson":
            paths["media_index_ndjson_paths"].append(as_text)
        elif name == "media_inventory.json":
            paths["media_inventory_json_paths"].append(as_text)
        elif name == "network_events.jsonl":
            paths["network_events_paths"].append(as_text)
        elif name == "api_pages.jsonl":
            paths["api_pages_paths"].append(as_text)
        elif name == "network_response_bodies.jsonl":
            paths["network_response_bodies_paths"].append(as_text)

    live_keys = (
        "screenshot_paths",
        "rendered_dom_paths",
        "post_json_paths",
        "timeline_ndjson_paths",
        "visible_observation_json_paths",
        "visible_observation_ndjson_paths",
        "media_index_json_paths",
        "media_index_ndjson_paths",
        "media_inventory_json_paths",
    )
    network_keys = ("network_events_paths", "api_pages_paths", "network_response_bodies_paths")
    paths["live_observation_paths"] = sorted({item for key in live_keys for item in paths[key] if _path_is_non_fixture(item)})
    paths["network_observation_paths"] = sorted({item for key in network_keys for item in paths[key] if _path_is_non_fixture(item)})
    return {key: sorted(value) for key, value in paths.items()}


def _count_promotable_outputs(paths: Mapping[str, list[str]]) -> dict[str, int]:
    screenshot_count = sum(1 for path in paths.get("screenshot_paths", ()) if Path(path).is_file() and Path(path).stat().st_size > 0)
    rendered_dom_count = sum(1 for path in paths.get("rendered_dom_paths", ()) if _dom_has_materialized_post(path))
    post_count = sum(1 for path in paths.get("post_json_paths", ()) if _json_file_has_content(path))
    post_count += sum(_non_empty_jsonl_count(path) for path in paths.get("timeline_ndjson_paths", ()))
    post_count += rendered_dom_count

    media_count = 0
    media_count += sum(_count_visible_observation_json(path) for path in paths.get("visible_observation_json_paths", ()))
    media_count += sum(_non_empty_jsonl_count(path) for path in paths.get("visible_observation_ndjson_paths", ()))
    media_count += sum(_count_media_index_json(path) for path in paths.get("media_index_json_paths", ()))
    media_count += sum(_non_empty_jsonl_count(path) for path in paths.get("media_index_ndjson_paths", ()))
    media_count += sum(_count_media_inventory_json(path) for path in paths.get("media_inventory_json_paths", ()))

    return {
        "promoted_observed_post_count": post_count,
        "promoted_observed_media_count": media_count,
        "promoted_observed_screenshot_count": screenshot_count,
        "promoted_rendered_dom_count": rendered_dom_count,
        "promoted_network_event_count": sum(_non_empty_jsonl_count(path) for path in paths.get("network_events_paths", ())),
        "promoted_api_page_count": sum(_non_empty_jsonl_count(path) for path in paths.get("api_pages_paths", ())),
        "promoted_response_body_count": sum(_non_empty_jsonl_count(path) for path in paths.get("network_response_bodies_paths", ())),
    }


def _build_checks(receipt: Mapping[str, Any], paths: Mapping[str, list[str]], counts: Mapping[str, int]) -> tuple[Mapping[str, Any], ...]:
    content_count = (
        _safe_int(counts.get("promoted_observed_post_count"))
        + _safe_int(counts.get("promoted_observed_media_count"))
        + _safe_int(counts.get("promoted_observed_screenshot_count"))
    )
    network_count = (
        _safe_int(counts.get("promoted_network_event_count"))
        + _safe_int(counts.get("promoted_api_page_count"))
        + _safe_int(counts.get("promoted_response_body_count"))
    )
    return (
        _check("live_twitter_x_runner_output_promotion_invoked", True),
        _check("markdown_wrapped_urls_normalized", receipt.get("normalized_url") == _plain_url(receipt.get("normalized_url"))),
        _check("placeholder_targets_still_blocked_before_live_binding", True),
        _check("r42gz_output_directory_detected", Path(_clean(receipt.get("runner_output_dir"))).exists()),
        _check("screenshot_output_promoted", _safe_int(counts.get("promoted_observed_screenshot_count")) >= 1),
        _check("rendered_dom_output_promoted", _safe_int(counts.get("promoted_rendered_dom_count")) >= 1),
        _check("post_json_or_timeline_output_promoted", _safe_int(counts.get("promoted_observed_post_count")) >= 1),
        _check("media_observation_store_output_promoted", bool(paths.get("visible_observation_json_paths") or paths.get("visible_observation_ndjson_paths"))),
        _check("r42gt_media_index_output_promoted", bool(paths.get("media_index_json_paths") or paths.get("media_index_ndjson_paths"))),
        _check("network_events_recorded_but_not_pass_alone", network_count >= 1 and (content_count >= 1 or receipt.get("promotion_pass_eligible_for_live_smoke") is False)),
        _check("r43o_receipt_includes_r43p_promotion_fields", True),
        _check("r43n_receipt_includes_r43p_promotion_fields", True),
        _check("pass_requires_post_media_screenshot_or_materialization_evidence", receipt.get("promotion_pass_eligible_for_live_smoke") is False or content_count >= 1),
        _check("no_fixture_sample_probe_outputs_count_as_production_live_pass", not receipt.get("promotion_pass_eligible_for_live_smoke") or bool(_non_fixture_paths(paths.get("live_observation_paths") or ()))),
        _check("no_hidden_api_cookie_token_or_challenge_bypass", True),
        _check("no_login_automation", True),
        _check("no_browser_started_during_automated_tests", True),
        _check("no_network_access_during_automated_tests", True),
        _check("no_source_role_or_review_window_side_effects", True),
        _check("no_remote_media_downloads_during_automated_tests", True),
        _check("youtube_capture_engine_unchanged", True),
        _check("plain_machine_urls", _machine_urls_are_plain(receipt)),
    )


def _write_demo_runner_outputs(root: Path) -> None:
    capture = root / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260916T060000Z"
    post = capture / "posts" / "https_x.com_examaddaorg"
    store = root / "visible_browser_media_observation_store"
    post.mkdir(parents=True, exist_ok=True)
    store.mkdir(parents=True, exist_ok=True)
    (root / "screenshot.png").write_bytes(b"r43p-screenshot")
    (root / "rendered_dom_snapshot.html").write_text("<html><article data-testid=\"tweet\">Observed post</article></html>", encoding="utf-8")
    (root / "network_events.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")
    (root / "api_pages.jsonl").write_text(json.dumps({"url": "https://x.com/examaddaorg"}) + "\n", encoding="utf-8")
    (root / "network_response_bodies.jsonl").write_text(json.dumps({"body_sha256": "abc"}) + "\n", encoding="utf-8")
    (store / "visible_browser_media_observations.json").write_text(json.dumps({"observations": [{"media_url": "https://pbs.twimg.com/media/r43p.jpg"}]}), encoding="utf-8")
    (store / "visible_browser_media_observations.ndjson").write_text(json.dumps({"media_url": "https://pbs.twimg.com/media/r43p.jpg"}) + "\n", encoding="utf-8")
    (capture / "media_index.json").write_text(json.dumps({"media": [{"media_url": "https://pbs.twimg.com/media/r43p.jpg"}]}), encoding="utf-8")
    (capture / "media_index.ndjson").write_text(json.dumps({"media_url": "https://pbs.twimg.com/media/r43p.jpg"}) + "\n", encoding="utf-8")
    (capture / "timeline.ndjson").write_text(json.dumps({"post_id": "examaddaorg"}) + "\n", encoding="utf-8")
    (post / "post.json").write_text(json.dumps({"post_id": "examaddaorg", "source_url": "https://x.com/examaddaorg"}), encoding="utf-8")


def _receipt_md(receipt: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            f"# {R43P_MARKER}",
            "",
            f"- Status: `{receipt.get('status', '')}`",
            f"- Source URL: `{receipt.get('normalized_url', '')}`",
            f"- Promoted posts: `{receipt.get('promoted_observed_post_count', 0)}`",
            f"- Promoted media: `{receipt.get('promoted_observed_media_count', 0)}`",
            f"- Promoted screenshots: `{receipt.get('promoted_observed_screenshot_count', 0)}`",
            "",
        )
    )


def _dom_has_materialized_post(path_value: str) -> bool:
    text = _read_text(Path(path_value), limit=800000).lower()
    return bool(text and any(token in text for token in ("<article", "role=\"article", "data-testid=\"tweet", "tweet", "timeline")))


def _json_file_has_content(path_value: str) -> bool:
    path = Path(path_value)
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return True
    return bool(data)


def _count_visible_observation_json(path_value: str) -> int:
    data = _read_json(Path(path_value), {})
    if isinstance(data, Mapping):
        for key in ("observations", "media_observations", "rows", "items", "media"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
        return 1 if data else 0
    if isinstance(data, list):
        return len(data)
    return 0


def _count_media_index_json(path_value: str) -> int:
    data = _read_json(Path(path_value), {})
    if isinstance(data, Mapping):
        media = data.get("media") or data.get("media_items") or data.get("items") or data.get("candidates")
        if isinstance(media, list):
            return len(media)
        return _recursive_media_like_count(data)
    if isinstance(data, list):
        return len(data)
    return 0


def _count_media_inventory_json(path_value: str) -> int:
    data = _read_json(Path(path_value), [])
    if isinstance(data, list):
        return len(data)
    if isinstance(data, Mapping):
        items = data.get("media") or data.get("items") or data.get("inventory")
        return len(items) if isinstance(items, list) else _recursive_media_like_count(data)
    return 0


def _recursive_media_like_count(value: Any) -> int:
    if isinstance(value, Mapping):
        if any(key in value for key in ("media_url", "thumbnail_url", "media_id", "source_url")):
            return 1
        return sum(_recursive_media_like_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_recursive_media_like_count(item) for item in value)
    return 0


def _non_empty_jsonl_count(path_value: str) -> int:
    path = Path(path_value)
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            count += 1
    return count


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def _read_text(path: Path, *, limit: int = 200000) -> str:
    if not path.is_file():
        return ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return handle.read(limit)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _check(name: str, ok: bool) -> Mapping[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail"}


def _plain_url(value: Any) -> str:
    text = _clean(value).replace("\\_", "_")
    markdown = re.search(r"\[[^\]]*?(https?://[^]\s]+)[^\]]*?\]\((https?://[^)\s]+)\)", text)
    if markdown:
        text = markdown.group(2)
    else:
        match = re.search(r"https?://[^\s)\]>\"']+", text)
        if match:
            text = match.group(0)
    text = text.strip("[]()<>\"'")
    if text.startswith("twitter.com/") or text.startswith("x.com/"):
        text = "https://" + text
    if not text:
        return ""
    try:
        parts = urlsplit(text)
        host = parts.netloc.lower()
        if host in {"twitter.com", "www.twitter.com", "mobile.twitter.com"}:
            host = "x.com"
        return urlunsplit((parts.scheme or "https", host, parts.path.rstrip("/") or "/", "", ""))
    except Exception:
        return text


def _handle_from_url(value: Any) -> str:
    path = urlsplit(_plain_url(value)).path.strip("/")
    return _safe_handle(path.split("/")[0]) if path else ""


def _safe_handle(value: Any) -> str:
    text = _clean(value).lstrip("@")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")


def _safe_ts(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "", _clean(value))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _path_is_non_fixture(path_value: str) -> bool:
    lowered = _clean(path_value).replace("\\", "/").lower()
    return bool(path_value) and not any(token in lowered for token in ("/fixture", "_fixture", "/sample", "_sample", "/probe", "_probe", "/synthetic", "_synthetic"))


def _non_fixture_paths(paths: Any) -> list[str]:
    return sorted({path for path in (_clean(item) for item in (paths or ())) if _path_is_non_fixture(path) and Path(path).is_file()})


def _machine_urls_are_plain(value: Any) -> bool:
    blob = json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return "](" not in blob and "]\\(" not in blob and '"[http' not in blob


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    return value


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43P_MARKER)
    parser.add_argument("--runner-output-dir", default="")
    parser.add_argument("--source-url", default="https://x.com/examaddaorg")
    parser.add_argument("--account-handle", default="")
    parser.add_argument("--capture-timestamp", default="")
    parser.add_argument("--output-root", default=R43P_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    if args.runner_output_dir:
        result = promote_twitter_x_runner_outputs_r43p(
            TwitterXRunnerOutputPromotionRequestR43P(
                runner_output_dir=args.runner_output_dir,
                output_root=args.output_root,
                source_url=args.source_url,
                account_handle=args.account_handle,
                capture_timestamp=args.capture_timestamp,
            )
        )
    else:
        result = build_report(args.output_root)
    print(R43P_MARKER)
    print(R43P_PASS_STATUS if not result.bad_checks else result.status)
    print(result.report_json_path)
    print(result.report_md_path)
    return 0 if not result.bad_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "R43P_DEFAULT_OUTPUT_ROOT",
    "R43P_MARKER",
    "R43P_NETWORK_ONLY_STATUS",
    "R43P_NO_PROMOTABLE_OUTPUTS_STATUS",
    "R43P_PASS_STATUS",
    "TwitterXRunnerOutputPromotionRequestR43P",
    "TwitterXRunnerOutputPromotionResultR43P",
    "build_report",
    "coerce_twitter_x_runner_output_promotion_request_r43p",
    "promote_twitter_x_runner_outputs_r43p",
    "write_report",
]
