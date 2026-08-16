from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_database_runtime import (
    PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION,
    ProfileMediaRuntimeState,
    build_profile_media_runtime_state,
    default_profile_media_runtime_state_path,
    load_profile_media_runtime_state,
    runtime_state_from_payload,
    save_profile_media_runtime_state,
)


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        state_path = tmp_path / "state" / "profile_media_database_runtime_state.json"

        missing = load_profile_media_runtime_state(state_path)
        assert_true(missing.sidebar_mode == "FILES", "missing state must default to FILES mode")
        assert_true(not missing.filesystem_work_performed, "missing state must not imply filesystem work")

        state = build_profile_media_runtime_state("DATABASE")
        saved = save_profile_media_runtime_state(state, state_path)
        loaded = load_profile_media_runtime_state(state_path)
        assert_true(saved.sidebar_mode == "DATABASE", "saved state should keep DATABASE mode")
        assert_true(loaded.sidebar_mode == "DATABASE", "loaded state should keep DATABASE mode")
        assert_true(loaded.schema_version == PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION, "schema version mismatch")
        assert_true(not any(loaded.safety_claims.values()), "mode toggle must not record side effects")

        invalid = runtime_state_from_payload({"sidebar_mode": "nonsense", "folder_move_performed": True})
        assert_true(invalid.sidebar_mode == "FILES", "invalid mode should coerce to FILES")
        assert_true(invalid.folder_move_performed, "explicit side-effect flag should be preserved when provided")

        default_path = default_profile_media_runtime_state_path(appdata_root=tmp_path)
        assert_true(default_path == tmp_path / "YTCE" / "profile_media_database_runtime_state.json", "default path mismatch")

    print("profile_media_database_runtime v75p OK")


if __name__ == "__main__":
    main()
