from pathlib import Path


def test_docs_cover_controller_provider_closeout() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Controller Provider Closeout",
        "runtime dispatch table",
        "provider execution registry",
        "KEYS/ACCOUNTS",
        "manual/live smoke",
        "SOURCE_ADAPTER_RUNTIME_READY_FOR_PRIORITY_FIXTURES_AND_MANUAL_LIVE_SMOKE",
    ]
    for needle in required:
        assert needle in text


if __name__ == "__main__":
    test_docs_cover_controller_provider_closeout()
    print("Source Adapter Runtime Controller Provider Closeout docs self-test passed.")
