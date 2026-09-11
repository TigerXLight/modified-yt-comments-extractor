from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_universal_source_capability_matrix_r42fx import (
    METRO_CAPABILITY,
    STATUS_NOT_TESTED,
    STATUS_TESTED_TRUE,
    build_metro_archive_availability_scan,
    classify_archive_candidate,
    detect_site_key,
    write_scan_report,
)

LIVE = "https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"
WAYBACK = "https://web.archive.org/web/20260717224516/https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/"
ARCHIVE_TODAY = "https://archive.ph/6mr3C"


def test_metro_profile_records_tested_and_not_tested_boundaries() -> None:
    assert detect_site_key(LIVE) == "metro"
    assert METRO_CAPABILITY.article_text == STATUS_TESTED_TRUE
    assert METRO_CAPABILITY.screenshots == STATUS_TESTED_TRUE
    assert METRO_CAPABILITY.comments == STATUS_NOT_TESTED
    assert "api3128" in METRO_CAPABILITY.media_route_preference


def test_archive_candidate_parsing() -> None:
    wayback = classify_archive_candidate(WAYBACK, live_url=LIVE)
    archive_today = classify_archive_candidate(ARCHIVE_TODAY, live_url=LIVE)
    assert wayback.provider == "wayback"
    assert wayback.saved_at == "20260717224516"
    assert wayback.status == "supplied"
    assert archive_today.provider == "archive_today"
    assert archive_today.status == "supplied"


def test_scan_is_side_effect_free_and_writes_reports() -> None:
    scan = build_metro_archive_availability_scan(
        live_url=LIVE,
        wayback_url=WAYBACK,
        archive_today_url=ARCHIVE_TODAY,
    )
    assert scan.side_effects_performed is False
    assert scan.capability.comments == STATUS_NOT_TESTED
    assert len(scan.archive_candidates) == 2
    assert any("no network fetch" in line for line in scan.summary_lines)
    with tempfile.TemporaryDirectory() as tmp:
        json_path, md_path = write_scan_report(scan, tmp)
        assert json_path.is_file()
        assert md_path.is_file()
        payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        assert payload["site_key"] == "metro"
        assert payload["side_effects_performed"] is False


if __name__ == "__main__":
    test_metro_profile_records_tested_and_not_tested_boundaries()
    test_archive_candidate_parsing()
    test_scan_is_side_effect_free_and_writes_reports()
    print("profile_media_universal_source_capability_matrix_r42fx_test OK")
