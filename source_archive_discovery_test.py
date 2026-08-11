from __future__ import annotations

import json
import tempfile

import source_archive_discovery as sad
from source_archive_discovery import (
    TimeMapLookupResult,
    archive_query_variants,
    discover_archives,
    normalize_target_url,
    parse_cdx_json,
    write_discovery_sidecars,
)


def test_normalize_removes_cmd_and_markdown_escaping() -> None:
    raw = "[https://www.msn.com/x?ocid=edgemobile^&PC=EMMX01](https://www.msn.com/x?ocid=edgemobile\\&PC=EMMX01)"
    assert normalize_target_url(raw) == "https://www.msn.com/x?ocid=edgemobile&PC=EMMX01"


def test_variants_include_exact_and_no_query() -> None:
    variants = archive_query_variants("https://www.msn.com/x?ocid=edgemobile&PC=EMMX01#comments")
    labels = [label for label, _ in variants]
    values = [value for _, value in variants]
    assert "exact" in labels
    assert "without_fragment" in labels
    assert "without_query_or_fragment" in labels
    assert "https://www.msn.com/x" in values


def test_parse_cdx_json_records_archive_urls() -> None:
    payload = json.dumps([
        ["timestamp", "original", "statuscode", "mimetype", "digest", "length"],
        ["20260811154652", "https://www.msn.com/x", "200", "text/html", "ABC", "123"],
    ]).encode("utf-8")
    records = parse_cdx_json(payload, query_variant="exact")
    assert len(records) == 1
    assert records[0].archive_url == "https://web.archive.org/web/20260811154652/https://www.msn.com/x"
    assert records[0].query_variant == "exact"


def test_no_network_sidecar_contains_clean_url_and_no_caret_queries() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = discover_archives("https://www.msn.com/x?ocid=edgemobile^&PC=EMMX01", network=False)
        json_path, txt_path = write_discovery_sidecars(result, tmp)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        text = txt_path.read_text(encoding="utf-8")
        assert data["target_url"].endswith("ocid=edgemobile&PC=EMMX01")
        assert "^&" not in data["target_url"]
        assert "^&" not in text
        assert "NETWORK_DISABLED_MANUAL_CANDIDATES_ONLY" in text
        assert "TIMEMAP_RESULTS" in text


def test_partial_cdx_error_status_is_not_reported_as_no_mementos() -> None:
    original_fetch_cdx = sad.fetch_cdx_records
    original_fetch_timemap = sad.fetch_timemap_summary

    def fake_fetch_cdx(query_url: str, *, query_variant: str = "", timeout: int = 30):
        if query_variant == "exact":
            return [], "TimeoutError: simulated timeout"
        return [], None

    def fake_fetch_timemap(timemap_url: str, *, label: str = "timemap", timeout: int = 20):
        return TimeMapLookupResult(label=label, timemap_url=timemap_url, status="NO_TIMEMAP_MEMENTOS_FOUND")

    sad.fetch_cdx_records = fake_fetch_cdx  # type: ignore[assignment]
    sad.fetch_timemap_summary = fake_fetch_timemap  # type: ignore[assignment]
    try:
        result = discover_archives("https://www.msn.com/x?ocid=edgemobile&PC=EMMX01", network=True)
    finally:
        sad.fetch_cdx_records = original_fetch_cdx  # type: ignore[assignment]
        sad.fetch_timemap_summary = original_fetch_timemap  # type: ignore[assignment]

    assert result.status == "ARCHIVE_LOOKUP_PARTIAL_ERROR_NO_MEMENTOS_CONFIRMED"
    assert any("TimeoutError" in item for item in result.errors)


def test_timemap_only_discovery_is_recorded() -> None:
    original_fetch_cdx = sad.fetch_cdx_records
    original_fetch_timemap = sad.fetch_timemap_summary

    def fake_fetch_cdx(query_url: str, *, query_variant: str = "", timeout: int = 30):
        return [], None

    def fake_fetch_timemap(timemap_url: str, *, label: str = "timemap", timeout: int = 20):
        if label == "exact":
            return TimeMapLookupResult(
                label=label,
                timemap_url=timemap_url,
                status="MEMENTOS_FOUND",
                memento_count=1,
                first_memento_url="https://web.archive.org/web/20260811154652/https://www.msn.com/x",
                latest_memento_url="https://web.archive.org/web/20260811154652/https://www.msn.com/x",
            )
        return TimeMapLookupResult(label=label, timemap_url=timemap_url, status="NO_TIMEMAP_MEMENTOS_FOUND")

    sad.fetch_cdx_records = fake_fetch_cdx  # type: ignore[assignment]
    sad.fetch_timemap_summary = fake_fetch_timemap  # type: ignore[assignment]
    try:
        result = discover_archives("https://www.msn.com/x?ocid=edgemobile&PC=EMMX01", network=True)
    finally:
        sad.fetch_cdx_records = original_fetch_cdx  # type: ignore[assignment]
        sad.fetch_timemap_summary = original_fetch_timemap  # type: ignore[assignment]

    assert result.status == "MEMENTOS_FOUND_TIMEMAP_ONLY"
    assert result.memento_count == 1


def run_self_test() -> None:
    test_normalize_removes_cmd_and_markdown_escaping()
    test_variants_include_exact_and_no_query()
    test_parse_cdx_json_records_archive_urls()
    test_no_network_sidecar_contains_clean_url_and_no_caret_queries()
    test_partial_cdx_error_status_is_not_reported_as_no_mementos()
    test_timemap_only_discovery_is_recorded()


if __name__ == "__main__":
    run_self_test()
    print("source_archive_discovery_test OK")
