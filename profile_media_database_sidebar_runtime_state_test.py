from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "main.py"


def assert_contains(text: str, needle: str, message: str) -> None:
    if needle not in text:
        raise AssertionError(message)


def assert_not_contains(text: str, needle: str, message: str) -> None:
    if needle in text:
        raise AssertionError(message)


def main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    assert_contains(text, "self.profile_media_runtime_state_path", "runtime state path must be stored on the app instance")
    assert_contains(text, "_load_profile_media_sidebar_mode_for_startup", "startup load helper missing")
    assert_contains(text, "_save_profile_media_sidebar_mode_for_runtime", "runtime save helper missing")
    assert_contains(text, "save_profile_media_runtime_state", "toggle mode should persist through runtime helper")
    assert_contains(text, "build_profile_media_runtime_state", "toggle mode should build sanitized runtime state")
    assert_not_contains(text, 'self.profile_media_sidebar_mode: str = "FILES"\n        self.profile_media_database_mode_var = None', "hard-coded startup mode should not bypass persisted mode")
    forbidden_runtime = (
        "os.rename(",
        "shutil.move(",
        "shutil.copy(",
        "shutil.copy2(",
        "mkdir(",
    )
    window = text[text.find("def _load_profile_media_sidebar_mode_for_startup"):text.find("def _create_profile_media_database_mode_toggle_section")]
    for token in forbidden_runtime:
        assert_not_contains(window, token, f"sidebar runtime-state bridge must not perform filesystem operation {token}")
    print("profile_media_database_sidebar_runtime_state v75p OK")


if __name__ == "__main__":
    main()
