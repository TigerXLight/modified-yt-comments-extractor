from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from twitter_capture_current_capabilities_v77a import (
    build_twitter_capture_capability_audit,
    render_twitter_capture_capability_audit_text,
)
from twitter_capture_profile_media_provenance import (
    build_twitter_profile_media_provenance,
    render_profile_media_provenance_summary,
)
from twitter_capture_screenshot_preservation import (
    build_capture_preservation_manifest,
    build_reference_family_capture_matrix,
    build_twitter_exporter_safety_matrix,
    render_capture_preservation_summary,
)


DEFAULT_SOURCE_URL = "https://x.com/example/with_replies"
DEFAULT_FIXTURE_DIR = Path("testdata/twitter_capture_v77a_fixture")


def build_cli_payload(source_url: str, fixture_dir: Path) -> dict:
    rendered_dom = fixture_dir / "rendered_dom_snapshot.html"
    viewport = fixture_dir / "screenshots" / "viewport_capture.txt"
    full_page = fixture_dir / "screenshots" / "full_page_capture.txt"
    preservation = build_capture_preservation_manifest(
        source_url=source_url,
        output_folder=fixture_dir,
        page_width=390,
        page_height=2200,
        viewport_width=390,
        viewport_height=720,
        cursor_state={
            "pages_count": 1,
            "last_cursor_out": "cursor-v77a-next",
            "soft_page_budget": 3,
            "rate_limit_remaining": 8,
        },
        now_epoch=1_800_000_000,
        rendered_dom_path=rendered_dom,
        viewport_screenshot_path=viewport,
        full_page_screenshot_path=full_page,
        media_urls=("https://pbs.twimg.com/media/example.jpg",),
        rendered_dom_status="rendered_dom_fixture_available",
    )
    provenance = build_twitter_profile_media_provenance(
        source_url="https://x.com/example/status/1877644315867963403",
        display_name="Example User",
        post_text="Fixture post text for V77A provenance bridge.",
        created_at="2026-08-16T10:00:00Z",
        screenshot_references=tuple(ref.to_dict() for ref in preservation.screenshot_references),
        media_references=({"media_url": "https://pbs.twimg.com/media/example.jpg", "source_url": source_url},),
        rendered_dom_status=preservation.rendered_dom_status,
        cursor_state=preservation.cursor_continuation.to_dict(),
        rate_limit_or_cooldown_state={
            "rate_limit_remaining": preservation.cursor_continuation.rate_limit_remaining,
            "cooldown_until_epoch": preservation.cursor_continuation.cooldown_until_epoch,
        },
    )
    audit = build_twitter_capture_capability_audit()
    return {
        "schema_version": "twitter_capture_v77a_cli_summary",
        "source_url": source_url,
        "offline_test_only": True,
        "live_browser_capable_later": True,
        "browser_launch_performed": False,
        "web_download_performed": False,
        "media_download_performed": False,
        "official_x_api_used": False,
        "unsafe_twitter_actions_absent": True,
        "preservation_manifest": preservation.to_dict(),
        "profile_media_provenance": provenance.to_dict(),
        "capability_audit": audit.to_dict(),
        "reference_family_capture_matrix": build_reference_family_capture_matrix(),
        "twitter_exporter_safety_matrix": build_twitter_exporter_safety_matrix(),
    }


def render_payload_text(payload: dict) -> str:
    preservation = payload["preservation_manifest"]
    provenance = payload["profile_media_provenance"]
    audit = payload["capability_audit"]
    lines = [
        "V77A TWITTER/X CAPTURE PRESERVATION PROOF",
        f"offline_test_only: {payload['offline_test_only']}",
        f"browser_launch_performed: {payload['browser_launch_performed']}",
        f"web_download_performed: {payload['web_download_performed']}",
        f"media_download_performed: {payload['media_download_performed']}",
        f"official_x_api_used: {payload['official_x_api_used']}",
        f"unsafe_twitter_actions_absent: {payload['unsafe_twitter_actions_absent']}",
        "",
        render_capture_preservation_summary(_manifest_from_dict_for_text(preservation)),
        "",
        render_profile_media_provenance_summary(_provenance_from_dict_for_text(provenance)),
        "",
        render_twitter_capture_capability_audit_text(_audit_from_dict_for_text(audit)),
    ]
    return "\n".join(lines)


def _manifest_from_dict_for_text(data: dict):
    from twitter_capture_screenshot_preservation import (
        TwitterCapturePreservationManifest,
        TwitterCursorContinuationProof,
        TwitterFullPageCapturePlan,
        TwitterFullPageCaptureStep,
        TwitterScreenshotArtifactReference,
    )

    def ref(value):
        return TwitterScreenshotArtifactReference(**value) if value else None

    plan = TwitterFullPageCapturePlan(
        **{
            **data["scroll_plan"],
            "steps": tuple(TwitterFullPageCaptureStep(**step) for step in data["scroll_plan"]["steps"]),
        }
    )
    return TwitterCapturePreservationManifest(
        **{
            **data,
            "viewport_screenshot": ref(data.get("viewport_screenshot")),
            "full_page_screenshot": ref(data.get("full_page_screenshot")),
            "scroll_plan": plan,
            "cursor_continuation": TwitterCursorContinuationProof(**data["cursor_continuation"]),
            "screenshot_references": tuple(TwitterScreenshotArtifactReference(**item) for item in data.get("screenshot_references", [])),
            "media_urls": tuple(data.get("media_urls", [])),
            "warnings": tuple(data.get("warnings", [])),
        }
    )


def _provenance_from_dict_for_text(data: dict):
    from twitter_capture_profile_media_provenance import TwitterProfileMediaProvenanceRecord

    return TwitterProfileMediaProvenanceRecord(
        **{
            **data,
            "screenshot_references": tuple(data.get("screenshot_references", [])),
            "media_references": tuple(data.get("media_references", [])),
            "warnings": tuple(data.get("warnings", [])),
        }
    )


def _audit_from_dict_for_text(data: dict):
    from twitter_capture_current_capabilities_v77a import TwitterCaptureCapabilityAudit, TwitterCaptureCapabilityRow

    return TwitterCaptureCapabilityAudit(
        **{
            **data,
            "rows": tuple(TwitterCaptureCapabilityRow(**row) for row in data.get("rows", [])),
            "unsafe_out_of_scope_actions": tuple(data.get("unsafe_out_of_scope_actions", [])),
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the offline V77A Twitter/X screenshot preservation and Profile/Media provenance proof.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--fixture-dir", default=str(DEFAULT_FIXTURE_DIR))
    parser.add_argument("--print-text", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_cli_payload(args.source_url, Path(args.fixture_dir))
    if args.print_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    if args.print_text or not args.print_json:
        print(render_payload_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
