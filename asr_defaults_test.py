import os
import tempfile

import asr_defaults


def test_asr_defaults_persist_engine_and_profile_without_plain_fallback() -> None:
    original_appdata = os.environ.get("APPDATA")
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["APPDATA"] = tmpdir
        try:
            asr_defaults.save_asr_defaults(
                model_name="large-v3",
                speaker_name="Speaker 1",
                language="en",
                initial_prompt="Caltheris",
                device="vulkan",
                compute_type="",
                engine="whispercpp_vulkan",
                profile_name="Best-tested local profile",
            )
            loaded = asr_defaults.load_asr_defaults()
        finally:
            if original_appdata is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = original_appdata

    assert loaded["engine"] == "whispercpp_vulkan"
    assert loaded["profile_name"] == "Best-tested local profile"
    assert loaded["model_name"] == "large-v3"
    assert loaded["device"] == "vulkan"
    assert loaded["compute_type"] == ""


def run_self_test() -> None:
    test_asr_defaults_persist_engine_and_profile_without_plain_fallback()


if __name__ == "__main__":
    run_self_test()
    print("asr_defaults_test.py: OK")
