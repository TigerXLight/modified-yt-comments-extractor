from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_RELEASE_REGRESSION_NEXT_ROADMAP_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Release Regression Next Roadmap Closeout",
        "source_adapter_release_regression_next_roadmap_closeout_v1",
        "KEYS/ACCOUNTS",
        "source_adapter_release_notes_manifest",
        "source_adapter_regular_regression_promotion_queue",
        "source_adapter_operator_live_execution_monitor_manifest",
        "source_adapter_next_roadmap_handoff",
    ]
    for item in required:
        assert item in text, item
    print("Source Adapter Release Regression Next Roadmap Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
