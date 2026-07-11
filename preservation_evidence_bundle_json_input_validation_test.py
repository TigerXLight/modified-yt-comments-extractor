from preservation_evidence_bundle import (
    build_preservation_evidence_bundle_from_dict,
    preservation_evidence_bundle_to_dict,
)


def _expect_value_error(data, expected: str) -> None:
    try:
        build_preservation_evidence_bundle_from_dict(data)
    except ValueError as exc:
        message = str(exc)
        assert expected in message, message
    else:
        raise AssertionError(f"Expected ValueError containing: {expected}")


def run_self_test() -> None:
    bundle = build_preservation_evidence_bundle_from_dict(
        {
            "source_url": " https://www.telegraph.co.uk/news/example/ ",
            "source_id": "example",
            "source_name": "news_website",
            "bundle_label": "Input evidence",
            "status": "manual_supplied",
            "notes": "Metadata only.",
            "uploaded": True,
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "capture_method_id": "scrollable_container_screenshot",
                    "artifact_role": "primary",
                    "origin": "manual",
                    "path_hint": r"captures\comments.png",
                    "notes": "JSON input path hint only.",
                    "sha256": "not-computed",
                }
            ],
        }
    )
    data = preservation_evidence_bundle_to_dict(bundle)
    assert data["source_url"] == "https://www.telegraph.co.uk/news/example/"
    assert data["bundle_label"] == "Input evidence"
    assert data["status"] == "manual_supplied"
    assert "uploaded" not in data
    assert data["items"][0]["artifact_id"] == "screenshot"
    assert data["items"][0]["artifact_format"] == "png"
    assert data["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert data["items"][0]["artifact_role"] == "primary"
    assert data["items"][0]["origin"] == "manual"
    assert data["items"][0]["path_hint"] == r"captures\comments.png"
    assert data["items"][0]["notes"] == "JSON input path hint only."
    assert "sha256" not in data["items"][0]
    assert "no file open" in data["scope"]

    none_normalized_bundle = build_preservation_evidence_bundle_from_dict(
        {
            "source_url": None,
            "source_id": None,
            "source_name": None,
            "bundle_label": None,
            "notes": None,
            "items": [
                {
                    "artifact_id": "metadata",
                    "artifact_format": "json",
                    "capture_method_id": None,
                    "artifact_role": None,
                    "origin": None,
                    "path_hint": None,
                    "notes": None,
                    "limitations": None,
                }
            ],
        }
    )
    none_data = preservation_evidence_bundle_to_dict(none_normalized_bundle)
    assert none_data["source_url"] == ""
    assert none_data["source_id"] == ""
    assert none_data["source_name"] == ""
    assert none_data["bundle_label"] == ""
    assert none_data["notes"] == ""
    assert none_data["items"][0]["capture_method_id"] == ""
    assert none_data["items"][0]["artifact_role"] == "supporting"
    assert none_data["items"][0]["origin"] == "unknown"
    assert none_data["items"][0]["path_hint"] == ""
    assert none_data["items"][0]["notes"] == ""
    assert none_data["items"][0]["limitations"] == ""

    _expect_value_error({"items": "screenshot"}, "evidence_bundle.items must be a list")
    _expect_value_error({"items": ["screenshot"]}, "evidence bundle item must be an object")
    _expect_value_error(
        {"items": [{"artifact_id": 123, "artifact_format": "png"}]},
        "artifact_id must be a string",
    )
    _expect_value_error(
        {"items": [{"artifact_id": "", "artifact_format": "png"}]},
        "artifact_id must not be empty",
    )
    _expect_value_error(
        {"items": [{"artifact_id": "screenshot", "artifact_format": ""}]},
        "artifact_format must not be empty",
    )
    _expect_value_error({"bundle_label": 123}, "bundle_label must be a string")
    _expect_value_error({"source_url": 123}, "source_url must be a string")
    _expect_value_error({"source_id": 123}, "source_id must be a string")
    _expect_value_error({"source_name": 123}, "source_name must be a string")
    _expect_value_error({"notes": 123}, "notes must be a string")
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "capture_method_id": 123,
                }
            ]
        },
        "capture_method_id must be a string",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "path_hint": 123,
                }
            ]
        },
        "path_hint must be a string",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "notes": 123,
                }
            ]
        },
        "notes must be a string",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "limitations": 123,
                }
            ]
        },
        "limitations must be a string",
    )
    _expect_value_error({"status": "complete"}, "invalid bundle status")
    _expect_value_error(
        {"items": [{"artifact_id": "screenshot", "artifact_format": "exe"}]},
        "invalid artifact format",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "capture_method_id": "unknown_capture",
                }
            ]
        },
        "invalid capture method ID",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "artifact_role": "lead",
                }
            ]
        },
        "invalid artifact role",
    )
    _expect_value_error(
        {
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "origin": "camera",
                }
            ]
        },
        "invalid artifact origin",
    )
    _expect_value_error(
        {
            "items": [
                {"artifact_id": "screenshot", "artifact_format": "png"},
                {"artifact_id": "screenshot", "artifact_format": "html"},
            ]
        },
        "duplicate artifact IDs: screenshot",
    )


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle JSON input validation self-test passed.")
