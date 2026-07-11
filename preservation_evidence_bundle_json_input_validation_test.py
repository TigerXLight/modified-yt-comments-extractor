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
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "capture_method_id": "scrollable_container_screenshot",
                    "artifact_role": "primary",
                    "origin": "manual",
                    "path_hint": r"captures\comments.png",
                    "notes": "JSON input path hint only.",
                }
            ],
        }
    )
    data = preservation_evidence_bundle_to_dict(bundle)
    assert data["source_url"] == "https://www.telegraph.co.uk/news/example/"
    assert data["bundle_label"] == "Input evidence"
    assert data["status"] == "manual_supplied"
    assert data["items"][0]["artifact_id"] == "screenshot"
    assert data["items"][0]["artifact_format"] == "png"
    assert data["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert data["items"][0]["artifact_role"] == "primary"
    assert data["items"][0]["origin"] == "manual"
    assert data["items"][0]["path_hint"] == r"captures\comments.png"
    assert data["items"][0]["notes"] == "JSON input path hint only."
    assert "no file open" in data["scope"]

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
