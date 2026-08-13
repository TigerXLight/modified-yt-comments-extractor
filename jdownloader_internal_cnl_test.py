from __future__ import annotations

import json
import time
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from jdownloader_internal_cnl import (
    diagnose_cnl,
    inspect_cnl_source_routes,
    normalize_http_url_for_jdownloader,
    normalize_internal_jdownloader_url,
    submit_cnl_multiroute,
)


def test_markdown_url_normalization_uses_target_url_and_rejects_garbage() -> None:
    exact = "[https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk](https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk)"
    exact_normalized = normalize_http_url_for_jdownloader(exact)
    assert exact_normalized.normalized_url == "https://youtu.be/uyy2MhKyL9A?si=6dpOf1E9EdXxFtJk"
    assert "[" not in exact_normalized.normalized_url
    assert "](" not in exact_normalized.normalized_url
    assert ")" not in exact_normalized.normalized_url
    markdown = " [https://youtu.be/visible?x=1](  https://youtu.be/target?si=abc  ) "
    normalized = normalize_internal_jdownloader_url(markdown)
    assert normalized.original_url == markdown.strip()
    assert normalized.normalized_url == "https://youtu.be/target?si=abc"
    assert any("Markdown link syntax" in warning for warning in normalized.warnings)
    assert any("differed" in warning for warning in normalized.warnings)
    try:
        normalize_internal_jdownloader_url("file:///tmp/video.mp4")
    except ValueError as error:
        assert "http(s)" in str(error)
    else:
        raise AssertionError("non-http URL was accepted")


def test_source_route_inspection_finds_cnl_routes_and_parameters() -> None:
    report = inspect_cnl_source_routes()
    for route in ("/flash", "/flash/add", "/flash/addcrypted2", "/flashgot", "/jdcheck.js", "/jdcheckjson"):
        assert route in report.supported_routes
    for parameter in ("urls", "package", "dir", "autostart"):
        assert parameter in report.supported_parameters
    assert report.source_files


def test_multiroute_submission_records_timeout_then_success() -> None:
    calls: list[str] = []

    def opener(request, timeout_seconds):
        calls.append(request.full_url)
        if "/flash/add" in request.full_url:
            raise TimeoutError("timed out")
        return 200, "JDownloader"

    with tempfile.TemporaryDirectory() as tmp:
        report = submit_cnl_multiroute(
            source_url="https://youtu.be/example",
            output_dir=tmp,
            package_name="YTCE CNL test",
            timeout_seconds=0.25,
            opener=opener,
            routes=("/flash/add", "/flashgot"),
        )
    assert report.submission_status == "accepted_or_unknown"
    assert report.accepted_route == "/flashgot"
    assert len(report.attempts) >= 2
    assert "TimeoutError" in report.attempts[0].error
    assert report.attempts[-1].http_status == 200
    assert calls


def test_multiroute_total_timeout_stops_remaining_routes() -> None:
    calls: list[str] = []

    def opener(request, timeout_seconds):
        calls.append(request.full_url)
        time.sleep(0.02)
        raise TimeoutError("timed out")

    with tempfile.TemporaryDirectory() as tmp:
        report = submit_cnl_multiroute(
            source_url="https://youtu.be/example",
            output_dir=tmp,
            package_name="YTCE CNL test",
            timeout_seconds=5.0,
            total_timeout_seconds=0.01,
            opener=opener,
            routes=("/flash/add", "/flashgot"),
        )
    assert report.submission_status == "failed"
    assert len(report.attempts) == 1
    assert "total timeout" in report.errors[0]


def test_multiroute_attempt_records_parameters_without_payload_text() -> None:
    seen_params: list[dict[str, list[str]]] = []

    def opener(request, timeout_seconds):
        body = (request.data or b"").decode("utf-8")
        seen_params.append(parse_qs(body or urlsplit(request.full_url).query))
        return 200, "OK"

    with tempfile.TemporaryDirectory() as tmp:
        report = submit_cnl_multiroute(
            source_url="https://youtu.be/example",
            output_dir=tmp,
            package_name="YTCE CNL test",
            opener=opener,
            routes=("/flash/add",),
        )
    attempt = report.attempts[0]
    assert report.submission_status == "accepted_or_unknown"
    assert attempt.route == "/flash/add"
    assert "urls" in attempt.parameters
    assert "package" in attempt.parameters
    assert "dir" in attempt.parameters
    assert seen_params[0]["urls"] == ["https://youtu.be/example"]


def test_diagnostic_dry_run_writes_serializable_report_without_submission() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = diagnose_cnl(source_url="[https://youtu.be/example](https://youtu.be/example)", output_dir=tmp, submit=False)
    data = report.to_dict()
    assert data["original_url"].startswith("[https://")
    assert data["normalized_url"] == "https://youtu.be/example"
    assert "[" not in data["normalized_url"]
    assert "](" not in data["normalized_url"]
    assert data["submission"] is None
    json.dumps(data)


def main() -> None:
    test_markdown_url_normalization_uses_target_url_and_rejects_garbage()
    test_source_route_inspection_finds_cnl_routes_and_parameters()
    test_multiroute_submission_records_timeout_then_success()
    test_multiroute_total_timeout_stops_remaining_routes()
    test_multiroute_attempt_records_parameters_without_payload_text()
    test_diagnostic_dry_run_writes_serializable_report_without_submission()
    print("jdownloader_internal_cnl_test OK")


if __name__ == "__main__":
    main()
