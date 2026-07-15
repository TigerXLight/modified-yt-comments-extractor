import asr_settings_dialog
import sys
import types


class FakeButton:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)


class FakeThread:
    created: list["FakeThread"] = []
    run_immediately = False

    def __init__(self, *, target: object, daemon: bool) -> None:
        self.target = target
        self.daemon = daemon
        FakeThread.created.append(self)

    def start(self) -> None:
        if FakeThread.run_immediately:
            self.target()


def _fake_dialog(settings: dict[str, str]):
    dialog = asr_settings_dialog.AsrSettingsDialog.__new__(
        asr_settings_dialog.AsrSettingsDialog
    )
    dialog._asr_check_busy = False
    dialog._asr_check_generation = 0
    dialog._asr_check_destroyed = False
    dialog.check_button = FakeButton()
    dialog.statuses: list[str] = []
    dialog._collect = lambda: dict(settings)
    dialog._set_setup_status = lambda text: dialog.statuses.append(text)
    dialog._build_asr_setup_status_text = lambda _settings: "completed status"
    dialog.after = lambda _delay, callback: callback()
    dialog.winfo_exists = lambda: True
    return dialog


def test_best_tested_profile_normalizes_to_real_whispercpp_runner_settings() -> None:
    settings = asr_settings_dialog.best_tested_asr_profile_settings()

    assert settings["engine"] == asr_settings_dialog.ASR_ENGINE_WHISPERCPP_VULKAN
    assert settings["model_name"] == "large-v3"
    assert settings["device"] == "vulkan"
    assert settings["compute_type"] == ""


def test_legacy_vulkan_values_infer_whispercpp_engine() -> None:
    settings = asr_settings_dialog.normalize_asr_settings(
        {
            "model_name": "large-v3",
            "device": "vulkan",
            "compute_type": "",
        }
    )

    assert settings["engine"] == asr_settings_dialog.ASR_ENGINE_WHISPERCPP_VULKAN
    assert settings["profile_name"] == asr_settings_dialog.ASR_BEST_TESTED_PROFILE
    assert settings["compute_type"] == ""


def test_engine_selector_values_expose_actual_engines() -> None:
    values = tuple(asr_settings_dialog.ASR_ENGINE_VALUES)

    assert "whisper.cpp" in values[0]
    assert "Vulkan" in values[0]
    assert "faster-whisper" in values[1]
    assert "NVIDIA CUDA" in values[1]
    assert asr_settings_dialog.ASR_BEST_TESTED_PROFILE in asr_settings_dialog.ASR_PROFILES


def test_asr_check_prevents_duplicate_worker_while_busy() -> None:
    original_thread = asr_settings_dialog.threading.Thread
    FakeThread.created = []
    FakeThread.run_immediately = False
    asr_settings_dialog.threading.Thread = FakeThread
    try:
        dialog = _fake_dialog(asr_settings_dialog.best_tested_asr_profile_settings())
        asr_settings_dialog.AsrSettingsDialog._check_asr_setup(dialog)
        asr_settings_dialog.AsrSettingsDialog._check_asr_setup(dialog)
    finally:
        asr_settings_dialog.threading.Thread = original_thread

    assert len(FakeThread.created) == 1
    assert dialog.statuses == ["Checking local ASR setup..."]
    assert dialog.check_button.config["state"] == "disabled"


def test_asr_check_finishes_through_ui_thread_callback() -> None:
    original_thread = asr_settings_dialog.threading.Thread
    FakeThread.created = []
    FakeThread.run_immediately = True
    asr_settings_dialog.threading.Thread = FakeThread
    try:
        dialog = _fake_dialog(asr_settings_dialog.best_tested_asr_profile_settings())
        asr_settings_dialog.AsrSettingsDialog._check_asr_setup(dialog)
    finally:
        asr_settings_dialog.threading.Thread = original_thread
        FakeThread.run_immediately = False

    assert dialog.statuses == ["Checking local ASR setup...", "completed status"]
    assert dialog.check_button.config["state"] == "normal"
    assert dialog._asr_check_busy is False


def test_stale_or_destroyed_check_callback_does_not_update_dialog() -> None:
    dialog = _fake_dialog(asr_settings_dialog.best_tested_asr_profile_settings())
    dialog._asr_check_destroyed = True
    asr_settings_dialog.AsrSettingsDialog._finish_asr_setup_check(dialog, 1, "done")

    assert dialog.statuses == []


def test_readiness_report_uses_one_coherent_whispercpp_selected_configuration() -> None:
    original_fw = sys.modules.get("faster_whisper")
    original_whispercpp = sys.modules.get("asr_whispercpp")
    original_quality = asr_settings_dialog.build_auto_quality_recommendation

    class ExistingPath:
        def exists(self) -> bool:
            return True

    sys.modules["faster_whisper"] = types.SimpleNamespace()
    sys.modules["asr_whispercpp"] = types.SimpleNamespace(
        is_whispercpp_vulkan_available=lambda _model="large-v3": True,
        whispercpp_cli_path=lambda: ExistingPath(),
        whispercpp_model_path=lambda _model="large-v3": ExistingPath(),
    )
    asr_settings_dialog.build_auto_quality_recommendation = lambda _settings: (
        "Resolved selected configuration:",
        "- Engine/backend: whisper.cpp",
        "- Acceleration: Vulkan",
        "- Model: large-v3",
        "- Compute type: Not applicable",
        "- Resolved runner: asr_whispercpp",
    )
    try:
        dialog = asr_settings_dialog.AsrSettingsDialog.__new__(
            asr_settings_dialog.AsrSettingsDialog
        )
        dialog._append_media_tools_check_lines = lambda lines: None
        text = asr_settings_dialog.AsrSettingsDialog._build_asr_setup_status_text(
            dialog,
            asr_settings_dialog.best_tested_asr_profile_settings(),
        )
    finally:
        if original_fw is None:
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = original_fw
        if original_whispercpp is None:
            sys.modules.pop("asr_whispercpp", None)
        else:
            sys.modules["asr_whispercpp"] = original_whispercpp
        asr_settings_dialog.build_auto_quality_recommendation = original_quality

    assert "whisper.cpp binary: Found" in text
    assert "Vulkan support: Ready" in text
    assert "large-v3 model: Found" in text
    assert "Best-tested profile: Ready" in text
    assert "Selected configuration:" in text
    assert "- Engine/backend: whisper.cpp" in text
    assert "- Acceleration: Vulkan" in text
    assert "- Model: large-v3" in text
    assert "- Compute type: Not applicable" in text
    assert "- Resolved runner: asr_whispercpp" in text
    assert "- faster-whisper backend: Installed" in text
    assert "Selected engine: whisper.cpp" not in text
    assert "[INFO] Engine/backend: faster-whisper" not in text
    assert "Selected acceleration: CPU" not in text
    assert "Selected compute type: whisper.cpp" not in text
    assert "compute=whisper.cpp" not in text


def run_self_test() -> None:
    test_best_tested_profile_normalizes_to_real_whispercpp_runner_settings()
    test_legacy_vulkan_values_infer_whispercpp_engine()
    test_engine_selector_values_expose_actual_engines()
    test_asr_check_prevents_duplicate_worker_while_busy()
    test_asr_check_finishes_through_ui_thread_callback()
    test_stale_or_destroyed_check_callback_does_not_update_dialog()
    test_readiness_report_uses_one_coherent_whispercpp_selected_configuration()


if __name__ == "__main__":
    run_self_test()
    print("asr_settings_dialog_test.py: OK")
