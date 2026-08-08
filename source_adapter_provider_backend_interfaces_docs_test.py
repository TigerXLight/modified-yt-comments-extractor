from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES.md").read_text(encoding="utf-8")
    required = [
        "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_BUILT",
        "SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_READY_FOR_GUI_CONTROLLER_AND_PROVIDER_SPECIFIC_BACKENDS",
        "browser_capture",
        "archive_submit",
        "release_upload",
        "file_library_publish",
        "credential_lookup",
        "KEYS/ACCOUNTS",
        "provider-specific backends",
    ]
    for item in required:
        assert item in text, item
    print("Source Adapter Provider Backend Interfaces docs self-test passed.")


if __name__ == "__main__":
    main()
