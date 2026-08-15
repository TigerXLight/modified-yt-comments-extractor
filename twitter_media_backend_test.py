from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared_media_backend import SharedMediaBackendResult
from twitter_media_backend import (
    TWITTER_MEDIA_BACKEND_PROFILE_ID,
    build_twitter_media_backend_plan,
    build_twitter_shared_media_backend_request,
    is_twitter_direct_media_url,
    normalize_twitter_media_source_url,
    twitter_direct_media_capability_evidence_status,
    run_twitter_media_download_via_shared_backend,
    twitter_jdownloader_capability_status,
)


def _write_manifest(path: Path, tested: bool = False) -> None:
    path.write_text(
        json.dumps(
            {
                "capabilities": {
                    "twitter.com": {
                        "tested": tested,
                        "plugins": [
                            {
                                "plugin_name": "TwitterCom",
                                "plugin_type": "hoster",
                                "relative_path": "jd/plugins/hoster/TwitterCom.class",
                            }
                        ],
                    },
                    "x.com": {
                        "tested": tested,
                        "plugins": [
                            {
                                "plugin_name": "TwitterCom",
                                "plugin_type": "hoster",
                                "relative_path": "jd/plugins/hoster/TwitterCom.class",
                            }
                        ],
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def test_twitter_capability_status_reads_jd_manifest() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68_twitter_cap_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        status = twitter_jdownloader_capability_status(manifest_path)
    assert status.capability_found is True
    assert status.capability_tested is False
    assert "twitter.com" in status.matched_domains
    assert "x.com" in status.matched_domains
    assert "TwitterCom" in status.plugin_names


def test_twitter_media_plan_routes_to_shared_backend_when_allowed() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68_twitter_plan_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        plan = build_twitter_media_backend_plan(
            source_url="https://x.com/example/status/1234567890?utm_source=test",
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=True,
        )
        request = build_twitter_shared_media_backend_request(plan)

    assert plan.profile_id == TWITTER_MEDIA_BACKEND_PROFILE_ID
    assert plan.canonical_url == "https://x.com/example/status/1234567890"
    assert plan.source_id == "x.com/example/status/1234567890"
    assert plan.execution_allowed is True
    assert request.source_adapter_id == "twitter_x"
    assert request.source_url == plan.canonical_url
    assert "video" in request.components


def test_twitter_media_plan_can_gate_untested_jd_support() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68_twitter_gate_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        plan = build_twitter_media_backend_plan(
            source_url="https://twitter.com/example/status/123",
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=False,
        )
    assert plan.execution_allowed is False
    assert "not marked tested" in plan.blocked_reason


def test_run_twitter_media_download_uses_shared_backend_runner_and_claims_completion() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v68_twitter_run_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=True)

        def fake_shared_runner(request):
            return SharedMediaBackendResult(
                shared_backend_id="shared_media_jdownloader",
                backend_id="jdownloader_internal",
                status="success",
                source_adapter_id=request.source_adapter_id,
                source_url=request.source_url,
                output_dir=request.output_dir,
                phase="completed",
                files_count=2,
            )

        result = run_twitter_media_download_via_shared_backend(
            source_url="https://x.com/example/status/123",
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=manifest_path,
            shared_backend_runner=fake_shared_runner,
        )

    assert result.status == "success"
    assert result.evidence_completion_claim == "completed"
    assert result.shared_backend_result is not None
    assert result.shared_backend_result.source_adapter_id == "twitter_x"


def test_twitter_media_plan_accepts_rendered_dom_direct_pbs_media_url() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72f_twitter_direct_media_") as tmp:
        manifest_path = Path(tmp) / "missing_jd_capabilities_manifest.json"
        media_url = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
        plan = build_twitter_media_backend_plan(
            source_url=f"[{media_url}]({media_url})",
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=True,
        )
        request = build_twitter_shared_media_backend_request(plan)

    assert normalize_twitter_media_source_url(f"<{media_url}>") == media_url
    assert is_twitter_direct_media_url(plan.canonical_url) is True
    assert plan.canonical_url == media_url
    assert plan.source_id == "pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    assert plan.execution_allowed is True
    assert plan.blocked_reason == ""
    assert "direct rendered-DOM media URL" in plan.route_note
    assert request.source_adapter_id == "twitter_x_direct_media"
    assert request.source_url == media_url


def test_twitter_direct_media_evidence_allows_strict_execution() -> None:
    direct_url = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
    with tempfile.TemporaryDirectory(prefix="ytce_v72h_twitter_direct_media_evidence_") as tmp:
        root = Path(tmp)
        manifest_path = root / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        evidence_path = root / "twitter_direct_media_jd_capability_evidence.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "schema_version": "twitter_direct_media_jd_capability_evidence.v72h",
                    "tested": True,
                    "source_url": direct_url,
                    "observed_host": "x.com",
                    "status": "success",
                    "phase": "completed",
                    "files_count": 1,
                    "api3128_used": True,
                    "route_used": "api3128",
                    "manifest_path": str(root / "jdownloader-internal-download-manifest.json"),
                }
            ),
            encoding="utf-8",
        )
        evidence = twitter_direct_media_capability_evidence_status(evidence_path)
        plan = build_twitter_media_backend_plan(
            source_url=direct_url,
            output_dir=root / "downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=False,
            direct_media_capability_evidence_path=evidence_path,
        )

    assert evidence.tested is True
    assert plan.execution_allowed is True
    assert plan.blocked_reason == ""
    assert plan.direct_media_capability_evidence is not None
    assert plan.direct_media_capability_evidence.tested is True



def test_twitter_media_plan_blocks_rendered_dom_direct_pbs_media_url_when_strict() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v72g_twitter_direct_media_strict_") as tmp:
        manifest_path = Path(tmp) / "jd_capabilities_manifest.json"
        _write_manifest(manifest_path, tested=False)
        media_url = "https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large"
        plan = build_twitter_media_backend_plan(
            source_url=media_url,
            output_dir=Path(tmp) / "downloads",
            capability_manifest_path=manifest_path,
            allow_untested_jdownloader=False,
        )

    assert plan.execution_allowed is False
    assert "not marked tested" in plan.blocked_reason
    try:
        build_twitter_shared_media_backend_request(plan)
    except ValueError as exc:
        assert "not marked tested" in str(exc)
    else:
        raise AssertionError("strict direct media plan unexpectedly built an executable request")


def main() -> None:
    test_twitter_capability_status_reads_jd_manifest()
    test_twitter_media_plan_routes_to_shared_backend_when_allowed()
    test_twitter_media_plan_can_gate_untested_jd_support()
    test_run_twitter_media_download_uses_shared_backend_runner_and_claims_completion()
    test_twitter_media_plan_accepts_rendered_dom_direct_pbs_media_url()
    test_twitter_direct_media_evidence_allows_strict_execution()
    test_twitter_media_plan_blocks_rendered_dom_direct_pbs_media_url_when_strict()
    print("twitter_media_backend_test OK")


if __name__ == "__main__":
    main()
