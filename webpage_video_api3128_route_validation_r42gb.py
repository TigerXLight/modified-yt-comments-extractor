from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from webpage_video_api3128_route_r42fx import (
    STATUS_PLAN_ONLY,
    STATUS_UNSUPPORTED,
    build_webpage_video_api3128_handoff_plan,
    should_attempt_webpage_video_api3128_first,
)

R42GB_MARKER = "YTCE_R42GB_SELECTED_WEBPAGE_MEDIA_API3128_ROUTE_VALIDATION"
VALIDATION_STATUS_PASS = "pass"
VALIDATION_STATUS_FAIL = "fail"
VALIDATION_STATUS_WARNING = "warning"


@dataclass(frozen=True)
class R42GBValidationCheck:
    check_id: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R42GBRouteDecision:
    media_url: str
    source_url: str
    kind: str
    extension: str
    mime_type: str
    should_attempt_api3128_first: bool
    plan_status: str
    route_preference: str
    backend_id: str
    route_used: str
    yt_dlp_role: str
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class R42GBValidationReport:
    marker: str
    scope: str
    source_root: str
    checks: tuple[R42GBValidationCheck, ...]
    sample_route_decisions: tuple[R42GBRouteDecision, ...]
    conclusion: str
    side_effects: str = "no network fetch, no archive submission, no media download, no screenshot, no CAPTCHA/access bypass"

    @property
    def passed(self) -> bool:
        return all(check.status != VALIDATION_STATUS_FAIL for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "scope": self.scope,
            "source_root": self.source_root,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "sample_route_decisions": [decision.to_dict() for decision in self.sample_route_decisions],
            "conclusion": self.conclusion,
            "side_effects": self.side_effects,
        }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _check_contains(text: str, needle: str, check_id: str, detail: str) -> R42GBValidationCheck:
    if needle in text:
        return R42GBValidationCheck(check_id, VALIDATION_STATUS_PASS, detail)
    return R42GBValidationCheck(check_id, VALIDATION_STATUS_FAIL, f"Missing expected text: {needle!r}")


def _method_body(source_text: str, method_name: str) -> str:
    needle = f"def {method_name}("
    start = source_text.find(needle)
    if start < 0:
        return ""
    next_method = source_text.find("\n    def ", start + len(needle))
    if next_method < 0:
        return source_text[start:]
    return source_text[start:next_method]


def _position_check(text: str, earlier: str, later: str, check_id: str, detail: str) -> R42GBValidationCheck:
    first = text.find(earlier)
    second = text.find(later)
    if first >= 0 and second >= 0 and first < second:
        return R42GBValidationCheck(check_id, VALIDATION_STATUS_PASS, detail)
    if first < 0:
        return R42GBValidationCheck(check_id, VALIDATION_STATUS_FAIL, f"Missing first marker: {earlier!r}")
    if second < 0:
        return R42GBValidationCheck(check_id, VALIDATION_STATUS_FAIL, f"Missing second marker: {later!r}")
    return R42GBValidationCheck(check_id, VALIDATION_STATUS_FAIL, f"Wrong order: {earlier!r} does not appear before {later!r}")


def build_route_decision_sample(
    *,
    media_url: str,
    source_url: str = "",
    kind: str = "",
    extension: str = "",
    mime_type: str = "",
) -> R42GBRouteDecision:
    should_attempt = should_attempt_webpage_video_api3128_first(
        media_url,
        extension=extension,
        mime_type=mime_type,
        kind=kind,
        source_url=source_url,
    )
    plan = build_webpage_video_api3128_handoff_plan(
        media_url=media_url,
        source_url=source_url,
        output_dir="r42gb_validation_only_no_download",
        resource_id="r42gb-validation-sample",
        display_name="R42GB validation sample",
        extension=extension,
        mime_type=mime_type,
        kind=kind,
    )
    return R42GBRouteDecision(
        media_url=media_url,
        source_url=source_url,
        kind=kind,
        extension=extension,
        mime_type=mime_type,
        should_attempt_api3128_first=bool(should_attempt),
        plan_status=plan.status,
        route_preference=plan.route_preference,
        backend_id=plan.backend_id,
        route_used=plan.route_used,
        yt_dlp_role=plan.yt_dlp_role,
        warning=plan.warning,
    )


def _sample_decisions() -> tuple[R42GBRouteDecision, ...]:
    return (
        build_route_decision_sample(
            media_url="https://cdn.example.test/video.mp4",
            source_url="https://metro.co.uk/example-story/",
            kind="file",
            extension=".mp4",
            mime_type="video/mp4",
        ),
        build_route_decision_sample(
            media_url="https://cdn.example.test/master.m3u8",
            source_url="https://metro.co.uk/example-story/",
            kind="stream",
            extension=".m3u8",
            mime_type="application/vnd.apple.mpegurl",
        ),
        build_route_decision_sample(
            media_url="https://player.vimeo.com/video/123456",
            source_url="https://metro.co.uk/example-story/",
            kind="embed",
        ),
        build_route_decision_sample(
            media_url="http://127.0.0.1:8765/video.mp4",
            source_url="http://127.0.0.1:8765/page.html",
            kind="file",
            extension=".mp4",
            mime_type="video/mp4",
        ),
    )


def validate_selected_webpage_media_api3128_route(source_root: str | Path = ".") -> R42GBValidationReport:
    root = Path(source_root)
    checks: list[R42GBValidationCheck] = []

    main_path = root / "main.py"
    route_path = root / "webpage_video_api3128_route_r42fx.py"
    bridge_path = root / "webpage_video_resource_bridge.py"
    candidate_path = root / "webpage_video_candidate_backend.py"

    if not main_path.is_file():
        checks.append(R42GBValidationCheck("main_exists", VALIDATION_STATUS_FAIL, "main.py is missing."))
        main_text = ""
    else:
        main_text = _read_text(main_path)
        checks.append(R42GBValidationCheck("main_exists", VALIDATION_STATUS_PASS, "main.py exists."))
    method = _method_body(main_text, "_download_webpage_video_audio_resource_to_session_file")
    if method:
        checks.append(R42GBValidationCheck("selected_resource_method_found", VALIDATION_STATUS_PASS, "Selected Video & Audio FILES intake method found."))
    else:
        checks.append(R42GBValidationCheck("selected_resource_method_found", VALIDATION_STATUS_FAIL, "Selected Video & Audio FILES intake method was not found."))

    checks.append(_check_contains(method, "download_webpage_video_audio_item_via_api3128", "main_imports_api3128_route", "The selected-resource download path imports the API3128/JDownloader handoff."))
    checks.append(_check_contains(method, "should_attempt_webpage_video_api3128_first", "main_checks_api3128_before_download", "The selected-resource download path calls the API3128-first decision helper."))
    checks.append(_position_check(method, "should_attempt_webpage_video_api3128_first", "urllib.request.urlopen", "api3128_decision_before_direct_fetch", "API3128/JDownloader decision appears before the direct urllib fetch fallback."))
    checks.append(_position_check(method, "download_webpage_video_audio_item_via_api3128", "urllib.request.urlopen", "api3128_handoff_before_direct_fetch", "API3128/JDownloader handoff appears before the direct urllib fetch fallback."))
    checks.append(_check_contains(method, "route_result.local_file_paths[0]", "api3128_success_returns_local_file", "A successful API3128/JDownloader result returns its completed local media file."))
    checks.append(_check_contains(method, "Stream/embed media candidates require the API3128-backed JDownloader internal route", "stream_candidates_do_not_silently_fall_back_to_direct_fetch", "Stream/embed candidates fail loudly if API3128 cannot return a file, instead of pretending direct fetch is universal."))
    checks.append(_check_contains(method, "yt-dlp is fallback/reference only", "ytdlp_remains_fallback_reference_only", "The user-facing stream/embed failure keeps yt-dlp as fallback/reference only."))

    if route_path.is_file():
        route_text = _read_text(route_path)
        checks.append(R42GBValidationCheck("route_helper_exists", VALIDATION_STATUS_PASS, "webpage_video_api3128_route_r42fx.py exists."))
        checks.append(_check_contains(route_text, "side_effects_performed=False", "plan_builder_side_effect_free", "Plan construction is explicitly side-effect-free."))
        checks.append(_check_contains(route_text, "shared_media_backend", "route_uses_shared_jdownloader_backend", "Execution path delegates to the shared JDownloader media backend when no test injection is provided."))
        checks.append(_check_contains(route_text, "fallback_only_after_jdownloader_api3128", "route_records_ytdlp_fallback_role", "Route metadata records yt-dlp as fallback only after API3128."))
    else:
        checks.append(R42GBValidationCheck("route_helper_exists", VALIDATION_STATUS_FAIL, "webpage_video_api3128_route_r42fx.py is missing."))

    if bridge_path.is_file():
        bridge_text = _read_text(bridge_path)
        checks.append(_check_contains(bridge_text, "route_preference=", "resource_bridge_records_route_preference", "Video/audio SourceResourceItem provenance records route preference."))
        checks.append(_check_contains(bridge_text, "JDownloader crawler/API3128", "resource_bridge_warns_embed_route", "Embedded/player resources warn that JDownloader/API3128 should be preferred."))
    else:
        checks.append(R42GBValidationCheck("resource_bridge_exists", VALIDATION_STATUS_WARNING, "webpage_video_resource_bridge.py was not present in this context."))

    if candidate_path.is_file():
        candidate_text = _read_text(candidate_path)
        checks.append(_check_contains(candidate_text, "try_jdownloader_api3128_before_yt_dlp", "candidate_backend_default_route_preference", "Candidate discovery default route preference is API3128 before yt-dlp."))
    else:
        checks.append(R42GBValidationCheck("candidate_backend_exists", VALIDATION_STATUS_WARNING, "webpage_video_candidate_backend.py was not present in this context."))

    sample_decisions = _sample_decisions()
    public_failures = [
        decision.media_url
        for decision in sample_decisions[:3]
        if not decision.should_attempt_api3128_first or decision.plan_status != STATUS_PLAN_ONLY
    ]
    local_failure = sample_decisions[3].should_attempt_api3128_first or sample_decisions[3].plan_status != STATUS_UNSUPPORTED
    if public_failures:
        checks.append(R42GBValidationCheck("sample_public_candidates_prefer_api3128", VALIDATION_STATUS_FAIL, "Public candidates did not prefer API3128: " + ", ".join(public_failures)))
    else:
        checks.append(R42GBValidationCheck("sample_public_candidates_prefer_api3128", VALIDATION_STATUS_PASS, "Public file, stream and embedded-player samples all prefer API3128/JDownloader."))
    if local_failure:
        checks.append(R42GBValidationCheck("sample_local_fixture_skips_api3128", VALIDATION_STATUS_FAIL, "Localhost fixture did not remain on direct/local path handling."))
    else:
        checks.append(R42GBValidationCheck("sample_local_fixture_skips_api3128", VALIDATION_STATUS_PASS, "Localhost fixture remains direct/local and does not invoke API3128."))

    conclusion = (
        "R42GB PASS: selected public webpage media candidates are validated as API3128/JDownloader-first, "
        "while localhost/local fixtures remain on the direct/local path."
    )
    if any(check.status == VALIDATION_STATUS_FAIL for check in checks):
        conclusion = "R42GB FAIL: selected webpage media API3128/JDownloader-first validation found one or more blocking checks."

    return R42GBValidationReport(
        marker=R42GB_MARKER,
        scope="validation only for selected public webpage Video & Audio FILES intake route",
        source_root=str(root),
        checks=tuple(checks),
        sample_route_decisions=sample_decisions,
        conclusion=conclusion,
    )


def render_r42gb_validation_markdown(report: R42GBValidationReport) -> str:
    lines = [
        "# R42GB selected webpage media API3128/JDownloader route validation",
        "",
        f"Marker: `{report.marker}`",
        f"Passed: `{str(report.passed).lower()}`",
        f"Scope: {report.scope}",
        f"Source root: `{report.source_root}`",
        "",
        "## Conclusion",
        "",
        report.conclusion,
        "",
        "## Side-effect boundary",
        "",
        report.side_effects,
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- `{check.status}` `{check.check_id}` — {check.detail}")
    lines.extend(["", "## Sample route decisions", ""])
    for decision in report.sample_route_decisions:
        lines.append(
            "- "
            f"`{decision.plan_status}` API3128-first=`{str(decision.should_attempt_api3128_first).lower()}` "
            f"route=`{decision.route_used}` backend=`{decision.backend_id}` yt-dlp-role=`{decision.yt_dlp_role}` "
            f"url=`{decision.media_url}`"
        )
    lines.append("")
    return "\n".join(lines)


def write_r42gb_validation_report(report: R42GBValidationReport, output_root: str | Path) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "r42gb_selected_webpage_media_api3128_route_validation.json"
    md_path = root / "r42gb_selected_webpage_media_api3128_route_validation.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_r42gb_validation_markdown(report), encoding="utf-8")
    return json_path, md_path


def _print_summary(report: R42GBValidationReport, json_path: Path | None = None, md_path: Path | None = None) -> None:
    print("R42GB selected webpage media API3128/JDownloader route validation")
    print("Passed:", str(report.passed).lower())
    print("Conclusion:", report.conclusion)
    print("Checks:", f"{sum(1 for check in report.checks if check.status == VALIDATION_STATUS_PASS)} pass / {sum(1 for check in report.checks if check.status == VALIDATION_STATUS_WARNING)} warning / {sum(1 for check in report.checks if check.status == VALIDATION_STATUS_FAIL)} fail")
    print("Side effects:", report.side_effects)
    if json_path:
        print("JSON:", json_path)
    if md_path:
        print("MARKDOWN:", md_path)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the R42GB selected webpage media API3128/JDownloader-first route.")
    parser.add_argument("--source-root", default=".", help="Project/source root to inspect.")
    parser.add_argument("--output-root", default="", help="Optional output directory for JSON + Markdown report.")
    args = parser.parse_args(tuple(argv) if argv is not None else None)
    report = validate_selected_webpage_media_api3128_route(args.source_root)
    json_path = md_path = None
    if args.output_root:
        json_path, md_path = write_r42gb_validation_report(report, args.output_root)
    _print_summary(report, json_path=json_path, md_path=md_path)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
