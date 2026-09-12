from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from profile_media_twitter_x_adapter_closeout_r42gf import (
    R42GF_MARKER,
    SIDE_EFFECT_BOUNDARY,
    canonical_twitter_x_url,
    render_report,
    validate_twitter_x_adapter_closeout,
    write_report,
)


def test_url_unwrap_and_canonicalization() -> None:
    assert canonical_twitter_x_url("[https://x.com/example/status/123](https://x.com/example/status/123)") == "https://x.com/example/status/123"
    assert canonical_twitter_x_url("<twitter.com/example>") == "https://twitter.com/example"


def test_twitter_x_routes_stay_out_of_generic_article_lane() -> None:
    report = validate_twitter_x_adapter_closeout(
        Path(__file__).resolve().parent,
        sample_urls=(
            "https://x.com/example/status/1234567890",
            "https://twitter.com/example",
            "https://x.com/i/lists/1234567890",
        ),
    )
    assert report.passed, render_report(report)
    assert report.marker == R42GF_MARKER
    assert all(item.source_family == "twitter_x" for item in report.route_closeouts)
    assert all(item.source_family != "generic_article" for item in report.route_closeouts)
    assert any(item.route_kind == "single_status_media" for item in report.route_closeouts)
    assert any(item.route_kind == "user_timeline_strict_limited" for item in report.route_closeouts)
    assert any(item.route_kind == "list_timeline_workaround" for item in report.route_closeouts)
    assert report.local_exporter_closeout.review_status == "USER_REVIEW_REQUIRED"
    assert report.local_exporter_closeout.provenance_status == "USER_SUPPLIED_LOCAL_EXPORT"
    assert report.local_exporter_closeout.summary_only
    assert report.local_exporter_closeout.user_review_required
    assert report.local_exporter_closeout.no_raw_tweet_text_in_summary
    assert report.local_exporter_closeout.no_full_local_paths_in_summary
    assert report.local_exporter_closeout.false_claim_flags_clear
    assert "no network fetch" in report.side_effects
    assert "no X write action" in report.side_effects


def test_report_writer_and_cli_accept_repeated_urls() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_r42gf_cli_") as tmp:
        out = Path(tmp) / "out"
        report = validate_twitter_x_adapter_closeout(
            Path(__file__).resolve().parent,
            sample_urls=(
                "[https://x.com/example/status/123](https://x.com/example/status/123)",
                "https://twitter.com/example",
                "https://x.com/i/lists/1234567890",
            ),
        )
        json_path, md_path = write_report(report, out)
        assert json_path.is_file()
        assert md_path.is_file()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["marker"] == R42GF_MARKER
        assert payload["passed"] is True

        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "profile_media_twitter_x_adapter_closeout_r42gf.py"),
                "--source-root",
                str(Path(__file__).resolve().parent),
                "--output-root",
                str(out / "cli"),
                "--url",
                "https://x.com/example/status/1234567890",
                "--url",
                "https://twitter.com/example",
                "--url",
                "https://x.com/i/lists/1234567890",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "R42GF Twitter/X adapter closeout" in completed.stdout
        assert "family=twitter_x" in completed.stdout
        assert "family=generic_article" not in completed.stdout
        assert (out / "cli" / "r42gf_twitter_x_adapter_closeout.json").is_file()
        assert (out / "cli" / "r42gf_twitter_x_adapter_closeout.md").is_file()


def test_source_family_matrix_twitter_row_is_r42gf_closed() -> None:
    from profile_media_source_family_matrix_r42gc import (
        STATUS_VALIDATED_CURRENT_METHOD,
        SOURCE_FAMILY_CAPABILITIES,
        classify_source_family,
    )

    twitter_capability = next(cap for cap in SOURCE_FAMILY_CAPABILITIES if cap.family_id == "twitter_x")
    assert twitter_capability.comments == STATUS_VALIDATED_CURRENT_METHOD
    assert twitter_capability.images == STATUS_VALIDATED_CURRENT_METHOD
    assert twitter_capability.video_audio == STATUS_VALIDATED_CURRENT_METHOD
    assert twitter_capability.screenshots == STATUS_VALIDATED_CURRENT_METHOD
    assert "R42GF" in " ".join(twitter_capability.notes)

    decision = classify_source_family("https://x.com/example/status/1234567890")
    assert decision.family_id == "twitter_x"
    assert decision.adapter_hint == "twitter_x"
    assert decision.supported


def run_self_test() -> None:
    test_url_unwrap_and_canonicalization()
    test_twitter_x_routes_stay_out_of_generic_article_lane()
    test_report_writer_and_cli_accept_repeated_urls()
    test_source_family_matrix_twitter_row_is_r42gf_closed()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_twitter_x_adapter_closeout_r42gf_test OK")
