from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import jdownloader_internal_job as job_module
from jdownloader_internal_cnl import CnlRouteAttempt, CnlSubmissionReport
from jdownloader_internal_job import build_youtube_job_request, submit_youtube_job_via_cnl

STALE_CNL_WARNING = "CNL may require operator permission inside JDownloader if this source is not pre-authorized."


def _request(name: str):
    return build_youtube_job_request(
        source_url="https://youtu.be/example",
        output_dir=Path(tempfile.gettempdir()) / name,
        package_name=name,
        wait=False,
    )


def test_api3128_route_has_no_cnl_permission_warning() -> None:
    def fake_submitter(**_kwargs):
        attempt = CnlRouteAttempt(
            route="/linkgrabberv2/addLinks",
            method="POST",
            url="http://127.0.0.1:3128/linkgrabberv2/addLinks",
            parameters=(),
            timeout_seconds=1,
            http_status=200,
            response_excerpt="ok",
        )
        return CnlSubmissionReport(
            submission_status="accepted_or_unknown",
            attempts=(attempt,),
            accepted_route="/api3128/linkgrabberv2/addLinks+moveToDownloadlist+downloadcontroller/start",
            route_metadata={
                "api3128_enabled": True,
                "api3128_used": True,
                "api3128_api_host": "127.0.0.1",
                "api3128_api_port": 3128,
                "api3128_localhost_only": True,
                "api3128_route_note": "submitted by test",
                "flashgot_fallback_used": False,
                "route_used": "api3128",
            },
            warnings=(),
            errors=(),
        )

    original = job_module.submit_api3128_then_flashgot_fallback
    try:
        job_module.submit_api3128_then_flashgot_fallback = fake_submitter
        result = submit_youtube_job_via_cnl(_request("ytce_v65b_api3128_assert"))
    finally:
        job_module.submit_api3128_then_flashgot_fallback = original

    assert result.route_metadata["route_used"] == "api3128"
    assert result.route_metadata["api3128_used"] is True
    assert not any(STALE_CNL_WARNING in warning for warning in result.warnings)


def test_flashgot_route_keeps_operator_warning() -> None:
    def fake_submitter(**_kwargs):
        attempt = CnlRouteAttempt(
            route="/flashgot",
            method="POST",
            url="http://127.0.0.1:9666/flashgot",
            parameters=(),
            timeout_seconds=1,
            http_status=200,
            response_excerpt="JDownloader",
        )
        return CnlSubmissionReport(
            submission_status="accepted_or_unknown",
            attempts=(attempt,),
            accepted_route="/flashgot",
            route_metadata={
                "api3128_enabled": True,
                "api3128_used": False,
                "flashgot_fallback_used": True,
                "route_used": "flashgot",
            },
            warnings=("API3128 fast route failed; used /flashgot fallback.",),
            errors=(),
        )

    original = job_module.submit_api3128_then_flashgot_fallback
    try:
        job_module.submit_api3128_then_flashgot_fallback = fake_submitter
        result = submit_youtube_job_via_cnl(_request("ytce_v65b_flashgot_assert"))
    finally:
        job_module.submit_api3128_then_flashgot_fallback = original

    assert result.route_metadata["route_used"] == "flashgot"
    assert result.route_metadata["flashgot_fallback_used"] is True
    assert any(STALE_CNL_WARNING in warning for warning in result.warnings)


def test_source_contains_api3128_manifest_fields() -> None:
    cnl_source = (ROOT / "jdownloader_internal_cnl.py").read_text(encoding="utf-8")
    assert '"api3128_api_host": "127.0.0.1"' in cnl_source
    assert '"api3128_api_port": 3128' in cnl_source
    assert '"api3128_localhost_only": True' in cnl_source
    assert '"api3128_execution_plan":' in cnl_source
    assert '"api3128_route_note"' in cnl_source
    assert 'warnings.append("Submitted via local Deprecated API' not in cnl_source


def main() -> None:
    test_api3128_route_has_no_cnl_permission_warning()
    test_flashgot_route_keeps_operator_warning()
    test_source_contains_api3128_manifest_fields()
    print("assert_jdownloader_api3128_warning_cleanup_v65b OK")


if __name__ == "__main__":
    main()
