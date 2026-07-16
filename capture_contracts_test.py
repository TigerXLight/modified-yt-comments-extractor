import json

from capture_contracts import (
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    CAPTURE_CONTRACT_SCOPE,
    CaptureSession,
    build_capture_artifact,
    build_capture_request,
    capture_session_to_json,
    stable_capture_id,
)
from capture_status import (
    COMPLETENESS_COMPLETE,
    FIDELITY_FAITHFUL,
    FIDELITY_STRUCTURED_EXTRACTION,
    OPERATIONAL_STATUS_MODEL_ONLY,
)


def test_stable_capture_id_is_deterministic_and_path_agnostic() -> None:
    first = stable_capture_id("request", "https://example.test/a", ("article",))
    second = stable_capture_id("request", "https://example.test/a", ("article",))
    third = stable_capture_id("request", "https://example.test/b", ("article",))

    assert first == second
    assert first != third
    assert "\\" not in first
    assert "/" not in first


def test_capture_request_serializes_options_without_side_effects() -> None:
    request = build_capture_request(
        source_url="https://localhost.test/article/static",
        requested_scopes=("article", "outline"),
        adapter_id="fixture_article",
        canonical_url="https://localhost.test/article/static",
        user_label="Fixture article",
        options={"depth": 1, "flags": ("no_live_network", "localhost_only")},
    )

    data = request.to_dict()
    assert data["operational_status"] == OPERATIONAL_STATUS_MODEL_ONLY
    assert data["requested_scopes"] == ["article", "outline"]
    assert data["options"]["flags"] == ["no_live_network", "localhost_only"]


def test_capture_artifacts_match_rev4_schema_required_fields() -> None:
    article = build_capture_artifact(
        session_id="session_1",
        source_url="https://localhost.test/article/static",
        artifact_type=ARTIFACT_TYPE_ARTICLE_TEXT,
        capture_method="fixture_article_extractor",
        relative_path="article/article.txt",
        sha256="a" * 64,
        completeness=COMPLETENESS_COMPLETE,
        fidelity=FIDELITY_STRUCTURED_EXTRACTION,
        created_at_utc="2026-07-16T00:00:00Z",
        warnings=("localhost fixture only",),
    )

    data = article.to_dict()
    for field in (
        "schema_version",
        "artifact_id",
        "session_id",
        "source_url",
        "artifact_type",
        "capture_method",
        "created_at_utc",
        "sha256",
        "relative_path",
        "completeness",
        "fidelity",
    ):
        assert field in data
    assert data["artifact_type"] == ARTIFACT_TYPE_ARTICLE_TEXT
    assert data["sha256"] == "a" * 64
    assert data["warnings"] == ["localhost fixture only"]


def test_capture_session_keeps_article_outline_and_comments_separate() -> None:
    request = build_capture_request(
        source_url="https://localhost.test/article/static",
        requested_scopes=("article", "outline", "comments"),
    )
    artifacts = (
        build_capture_artifact(
            session_id="session_2",
            source_url=request.source_url,
            artifact_type=ARTIFACT_TYPE_ARTICLE_TEXT,
            capture_method="fixture_article_extractor",
            relative_path="article/article.txt",
            sha256="b" * 64,
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc="2026-07-16T00:00:00Z",
        ),
        build_capture_artifact(
            session_id="session_2",
            source_url=request.source_url,
            artifact_type=ARTIFACT_TYPE_PAGE_OUTLINE,
            capture_method="fixture_page_outline",
            relative_path="page/outline.json",
            sha256="c" * 64,
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_FAITHFUL,
            created_at_utc="2026-07-16T00:00:01Z",
        ),
        build_capture_artifact(
            session_id="session_2",
            source_url=request.source_url,
            artifact_type=ARTIFACT_TYPE_COMMENTS_JSONL,
            capture_method="fixture_comments",
            relative_path="comments/comments.jsonl",
            sha256="d" * 64,
            completeness=COMPLETENESS_COMPLETE,
            fidelity=FIDELITY_STRUCTURED_EXTRACTION,
            created_at_utc="2026-07-16T00:00:02Z",
        ),
    )
    session = CaptureSession(
        session_id="session_2",
        request=request,
        created_at_utc="2026-07-16T00:00:00Z",
        artifacts=artifacts,
    )

    data = session.to_dict()
    assert data["scope"] == CAPTURE_CONTRACT_SCOPE
    assert [artifact["artifact_type"] for artifact in data["artifacts"]] == [
        ARTIFACT_TYPE_ARTICLE_TEXT,
        ARTIFACT_TYPE_PAGE_OUTLINE,
        ARTIFACT_TYPE_COMMENTS_JSONL,
    ]
    rendered = capture_session_to_json(session)
    loaded = json.loads(rendered)
    assert loaded["session_id"] == "session_2"
    assert "requests.get" not in rendered
    assert "playwright.chromium.launch" not in rendered


def test_artifact_validation_rejects_unknown_types_and_bad_digests() -> None:
    try:
        build_capture_artifact(
            session_id="session_3",
            source_url="https://localhost.test/",
            artifact_type="REAL_SITE_FETCH",
            capture_method="fixture",
            relative_path="bad.txt",
        )
    except ValueError as exc:
        assert "Unknown capture artifact type" in str(exc)
    else:
        raise AssertionError("unknown artifact type should fail")

    try:
        build_capture_artifact(
            session_id="session_3",
            source_url="https://localhost.test/",
            artifact_type=ARTIFACT_TYPE_ARTICLE_TEXT,
            capture_method="fixture",
            relative_path="bad.txt",
            sha256="not-a-digest",
        )
    except ValueError as exc:
        assert "sha256" in str(exc)
    else:
        raise AssertionError("bad sha256 should fail")


def run_self_test() -> None:
    test_stable_capture_id_is_deterministic_and_path_agnostic()
    test_capture_request_serializes_options_without_side_effects()
    test_capture_artifacts_match_rev4_schema_required_fields()
    test_capture_session_keeps_article_outline_and_comments_separate()
    test_artifact_validation_rejects_unknown_types_and_bad_digests()


if __name__ == "__main__":
    run_self_test()
    print("Capture contracts self-test passed.")
