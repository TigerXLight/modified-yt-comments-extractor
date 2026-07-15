import asr_settings_dialog


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
    assert settings["compute_type"] == "whisper.cpp"


def test_legacy_vulkan_values_infer_whispercpp_engine() -> None:
    settings = asr_settings_dialog.normalize_asr_settings(
        {
            "model_name": "large-v3",
            "device": "vulkan",
            "compute_type": "whisper.cpp",
        }
    )

    assert settings["engine"] == asr_settings_dialog.ASR_ENGINE_WHISPERCPP_VULKAN
    assert settings["profile_name"] == asr_settings_dialog.ASR_BEST_TESTED_PROFILE


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


def run_self_test() -> None:
    test_best_tested_profile_normalizes_to_real_whispercpp_runner_settings()
    test_legacy_vulkan_values_infer_whispercpp_engine()
    test_engine_selector_values_expose_actual_engines()
    test_asr_check_prevents_duplicate_worker_while_busy()
    test_asr_check_finishes_through_ui_thread_callback()
    test_stale_or_destroyed_check_callback_does_not_update_dialog()


if __name__ == "__main__":
    run_self_test()
    print("asr_settings_dialog_test.py: OK")
