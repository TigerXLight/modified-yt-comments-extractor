import hashlib
from tempfile import TemporaryDirectory
from pathlib import Path

from capture_warc_wacz import (
    REDACTED_HEADER_VALUE,
    WARC_RECORD_REQUEST,
    WARC_RECORD_RESPONSE,
    WACZIndexEntry,
    WACZPageEntry,
    WACZResourceRecord,
    WACZWARCComponentReference,
    build_wacz_manifest,
    build_warc_manifest,
    build_warc_record,
    sanitize_headers,
)


SECRET_SENTINEL = "SHOULD_NOT_APPEAR"
SOURCE_URL = "https://example.test/article"


def test_warc_record_sanitizes_secret_headers_and_hashes_payload() -> None:
    record = build_warc_record(
        source_url=SOURCE_URL,
        record_kind=WARC_RECORD_RESPONSE,
        status_code=200,
        content_type="text/html",
        timestamp_utc="2026-07-16T00:00:00Z",
        payload=b"<html>fixture</html>",
        headers={
            "Content-Type": "text/html",
            "Authorization": f"Bearer {SECRET_SENTINEL}",
            "Cookie": SECRET_SENTINEL,
            "Set-Cookie": SECRET_SENTINEL,
            "X-API-Key": SECRET_SENTINEL,
        },
    )

    data = record.to_dict()

    assert data["payload_sha256"] == hashlib.sha256(b"<html>fixture</html>").hexdigest()
    assert data["headers"]["Content-Type"] == "text/html"
    assert data["headers"]["Authorization"] == REDACTED_HEADER_VALUE
    assert data["headers"]["Cookie"] == REDACTED_HEADER_VALUE
    assert data["headers"]["Set-Cookie"] == REDACTED_HEADER_VALUE
    assert data["headers"]["X-API-Key"] == REDACTED_HEADER_VALUE
    assert SECRET_SENTINEL not in repr(data)
    assert "requests.get" not in repr(data)


def test_sanitize_headers_is_deterministic_and_path_agnostic() -> None:
    first = sanitize_headers({"b": "2", "a": "1", "Proxy-Authorization": SECRET_SENTINEL})
    second = sanitize_headers({"a": "1", "Proxy-Authorization": SECRET_SENTINEL, "b": "2"})

    assert first == second
    assert list(first) == ["a", "b", "Proxy-Authorization"]
    assert first["Proxy-Authorization"] == REDACTED_HEADER_VALUE
    assert SECRET_SENTINEL not in repr(first)


def test_warc_manifest_hash_is_deterministic_and_fixture_file_hash_is_recorded() -> None:
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "fixture.warc"
        fixture.write_bytes(b"WARC/1.1\r\nfixture\r\n")
        request = build_warc_record(
            source_url=SOURCE_URL,
            record_kind=WARC_RECORD_REQUEST,
            method="GET",
            timestamp_utc="2026-07-16T00:00:00Z",
            headers={"Accept": "text/html"},
        )
        response = build_warc_record(
            source_url=SOURCE_URL,
            record_kind=WARC_RECORD_RESPONSE,
            status_code=200,
            content_type="text/html",
            timestamp_utc="2026-07-16T00:00:01Z",
            payload=b"fixture",
        )

        first = build_warc_manifest(
            source_url=SOURCE_URL,
            records=(request, response),
            fixture_warc_path=str(fixture),
        )
        second = build_warc_manifest(
            source_url=SOURCE_URL,
            records=(request, response),
            fixture_warc_path=str(fixture),
        )
        with TemporaryDirectory() as second_temp_dir:
            same_name_fixture = Path(second_temp_dir) / "fixture.warc"
            same_name_fixture.write_bytes(b"WARC/1.1\r\nfixture\r\n")
            path_independent = build_warc_manifest(
                source_url=SOURCE_URL,
                records=(request, response),
                fixture_warc_path=str(same_name_fixture),
            )
            path_independent_hash = path_independent.to_dict()["manifest_sha256"]

    assert first.warc_sha256 == hashlib.sha256(b"WARC/1.1\r\nfixture\r\n").hexdigest()
    assert first.to_dict()["manifest_sha256"] == second.to_dict()["manifest_sha256"]
    assert first.to_dict()["manifest_sha256"] == path_independent_hash
    assert first.to_dict()["record_count"] == 2
    assert first.to_dict()["capture_execution"] == "not executed"


def test_wacz_manifest_models_index_pages_resources_components_and_fixture_hash() -> None:
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "fixture.wacz"
        fixture.write_bytes(b"PK fixture wacz")
        component_hash = "a" * 64
        manifest = build_wacz_manifest(
            package_id="package_1",
            source_url=SOURCE_URL,
            index_entries=(
                WACZIndexEntry(
                    url=SOURCE_URL,
                    timestamp_utc="2026-07-16T00:00:00Z",
                    warc_record_id="warc_record_1",
                    status_code=200,
                    content_type="text/html",
                ),
            ),
            pages=(
                WACZPageEntry(
                    page_id="page_1",
                    url=SOURCE_URL,
                    title="Fixture page",
                    timestamp_utc="2026-07-16T00:00:00Z",
                ),
            ),
            resources=(
                WACZResourceRecord(
                    resource_id="resource_1",
                    url="https://example.test/style.css",
                    media_type="text/css",
                    sha256="b" * 64,
                    size_bytes=12,
                ),
            ),
            warc_components=(
                WACZWARCComponentReference(
                    path="archive/fixture.warc",
                    sha256=component_hash,
                    record_count=2,
                ),
            ),
            fixture_wacz_path=str(fixture),
        )
        repeated = build_wacz_manifest(
            package_id="package_1",
            source_url=SOURCE_URL,
            index_entries=manifest.index_entries,
            pages=manifest.pages,
            resources=manifest.resources,
            warc_components=manifest.warc_components,
            fixture_wacz_path=manifest.fixture_wacz_path,
        )
        repeated_manifest_sha256 = repeated.to_dict()["manifest_sha256"]
        with TemporaryDirectory() as second_temp_dir:
            same_name_fixture = Path(second_temp_dir) / "fixture.wacz"
            same_name_fixture.write_bytes(b"PK fixture wacz")
            path_independent = build_wacz_manifest(
                package_id="package_1",
                source_url=SOURCE_URL,
                index_entries=manifest.index_entries,
                pages=manifest.pages,
                resources=manifest.resources,
                warc_components=manifest.warc_components,
                fixture_wacz_path=str(same_name_fixture),
            )
            path_independent_hash = path_independent.to_dict()["manifest_sha256"]

    data = manifest.to_dict()

    assert manifest.wacz_sha256 == hashlib.sha256(b"PK fixture wacz").hexdigest()
    assert data["index_entries"][0]["warc_record_id"] == "warc_record_1"
    assert data["pages"][0]["title"] == "Fixture page"
    assert data["resources"][0]["resource_id"] == "resource_1"
    assert data["warc_components"][0]["sha256"] == component_hash
    assert data["package_execution"] == "not executed"
    assert data["manifest_sha256"] == repeated_manifest_sha256
    assert data["manifest_sha256"] == path_independent_hash
    assert "subprocess" not in repr(data)
    assert "archivebox add" not in repr(data).lower()
    assert "docker compose" not in repr(data).lower()


def run_self_test() -> None:
    test_warc_record_sanitizes_secret_headers_and_hashes_payload()
    test_sanitize_headers_is_deterministic_and_path_agnostic()
    test_warc_manifest_hash_is_deterministic_and_fixture_file_hash_is_recorded()
    test_wacz_manifest_models_index_pages_resources_components_and_fixture_hash()


if __name__ == "__main__":
    run_self_test()
    print("Capture WARC/WACZ self-test passed.")
