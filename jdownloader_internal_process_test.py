from __future__ import annotations

import tempfile
from pathlib import Path

from jdownloader_internal_paths import JD_RUNTIME_DIR, LOCAL_JD_INSTALLED_ROOT
from jdownloader_internal_process import (
    JDownloaderInternalProcessManager,
    repair_project_local_runtime,
    runtime_preflight,
    is_project_local_runtime,
    select_internal_runtime_command,
)


class FakeProcess:
    pid = 4321

    def __init__(self) -> None:
        self._returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True
        self._returncode = 0

    def wait(self, timeout=None):
        return self._returncode

    def kill(self) -> None:
        self.killed = True
        self._returncode = -9


def test_runtime_path_must_be_project_local() -> None:
    assert is_project_local_runtime(JD_RUNTIME_DIR) is True
    assert is_project_local_runtime(LOCAL_JD_INSTALLED_ROOT) is False


def test_start_uses_project_local_runtime_and_reuses_warm_process() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Path(tmp) / "third_party" / "jdownloader" / "runtime" / "JDownloader 2"
        # This temporary path is intentionally outside the repo, so it should be rejected.
        manager = JDownloaderInternalProcessManager(runtime_dir=runtime, cnl_probe=lambda: False)
        report = manager.start()
        assert report.status == "failed"
        assert "Runtime directory is not under" in report.errors[0]

    calls: list[dict[str, object]] = []

    def fake_popen(command, **kwargs):
        calls.append({"command": tuple(command), **kwargs})
        return FakeProcess()

    probe_state = {"ready": False}

    def fake_probe() -> bool:
        return bool(probe_state["ready"])

    def fake_popen_ready(command, **kwargs):
        probe_state["ready"] = True
        return fake_popen(command, **kwargs)

    manager = JDownloaderInternalProcessManager(
        runtime_dir=JD_RUNTIME_DIR,
        popen_factory=fake_popen_ready,
        cnl_probe=fake_probe,
    )
    report = manager.start()
    assert report.status == "READY"
    assert report.project_local_runtime is True
    assert report.external_appdata_used_as_primary is False
    assert report.pid == 4321
    assert calls
    assert str(JD_RUNTIME_DIR) in str(calls[0]["cwd"])
    warm = manager.start()
    assert warm.status == "READY"
    assert warm.warm_job is True


def test_blocks_preexisting_cnl_endpoint_before_starting() -> None:
    import jdownloader_internal_process as process_module

    calls: list[object] = []

    def fake_popen(command, **kwargs):
        calls.append(command)
        return FakeProcess()

    original = process_module.project_local_jdownloader_process_running
    try:
        process_module.project_local_jdownloader_process_running = lambda _runtime_dir=JD_RUNTIME_DIR: False
        manager = JDownloaderInternalProcessManager(
            runtime_dir=JD_RUNTIME_DIR,
            popen_factory=fake_popen,
            cnl_probe=lambda: True,
        )
        report = manager.start()
        assert report.status == "blocked_external_cnl_port"
        assert report.external_cnl_port_in_use is True
        assert report.external_appdata_used_as_primary is False
        assert not calls
    finally:
        process_module.project_local_jdownloader_process_running = original


def test_reuses_existing_project_local_runtime_when_detected() -> None:
    import jdownloader_internal_process as process_module

    original = process_module.project_local_jdownloader_process_running
    try:
        process_module.project_local_jdownloader_process_running = lambda _runtime_dir=JD_RUNTIME_DIR: True
        manager = JDownloaderInternalProcessManager(runtime_dir=JD_RUNTIME_DIR, cnl_probe=lambda: True)
        report = manager.start()
        assert report.status == "READY"
        assert report.warm_job is True
        assert report.external_cnl_port_in_use is False
    finally:
        process_module.project_local_jdownloader_process_running = original


def test_process_reports_do_not_include_sensitive_cfg_payload_names() -> None:
    manager = JDownloaderInternalProcessManager(runtime_dir=JD_RUNTIME_DIR, cnl_probe=lambda: False)
    report_text = str(manager.status().to_dict())
    forbidden = (
        "AccountSettings.accounts.ejs",
        "downloadList",
        "linkcollector",
        "cookies",
        "tokens",
    )
    for value in forbidden:
        assert value not in report_text


def test_preflight_reports_missing_install4j_for_incomplete_runtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Path(tmp) / "repo" / "third_party" / "jdownloader" / "runtime" / "JDownloader 2"
        runtime.mkdir(parents=True)
        (runtime / "JDownloader.jar").write_bytes(b"jar")
        (runtime / "Core.jar").write_bytes(b"core")
        report = runtime_preflight(runtime)
        assert report.ready_for_exe_launch is False
        assert ".install4j" in report.missing
        assert "libs" in report.missing


def test_repair_report_redacts_sensitive_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source"
        runtime = Path(__file__).resolve().parent / "third_party" / "jdownloader" / "runtime" / "test_repair_runtime"
        # Use a project-local path so repair safety check can pass without touching real runtime.
        if runtime.exists():
            import shutil

            shutil.rmtree(runtime)
        try:
            (source / ".install4j").mkdir(parents=True)
            (source / "libs").mkdir()
            (source / "jd" / "plugins").mkdir(parents=True)
            (source / "cfg" / "plugins" / "youtube").mkdir(parents=True)
            (source / "JDownloader2.exe").write_bytes(b"exe")
            (source / "JDownloader.jar").write_bytes(b"jar")
            (source / "Core.jar").write_bytes(b"core")
            (source / "cfg" / "org.jdownloader.api.RemoteAPIConfig.json").write_text("{}", encoding="utf-8")
            (source / "cfg" / "plugins" / "youtube" / "Youtube.json").write_text("{}", encoding="utf-8")
            (source / "cfg" / "org.jdownloader.settings.AccountSettings.accounts.ejs").write_text("secret", encoding="utf-8")
            report = repair_project_local_runtime(source_dir=source, runtime_dir=runtime)
            text = str(report.to_dict())
            assert report.skipped_sensitive_count == 1
            assert "AccountSettings.accounts.ejs" not in text
            assert not (runtime / "cfg" / "org.jdownloader.settings.AccountSettings.accounts.ejs").exists()
        finally:
            if runtime.exists():
                import shutil

                shutil.rmtree(runtime)


def test_select_command_prefers_project_jar_when_available() -> None:
    command = select_internal_runtime_command(JD_RUNTIME_DIR)
    assert command
    assert str(JD_RUNTIME_DIR) in " ".join(command) or command[0].endswith("JDownloader2.exe")


def main() -> None:
    test_runtime_path_must_be_project_local()
    test_start_uses_project_local_runtime_and_reuses_warm_process()
    test_blocks_preexisting_cnl_endpoint_before_starting()
    test_reuses_existing_project_local_runtime_when_detected()
    test_process_reports_do_not_include_sensitive_cfg_payload_names()
    test_preflight_reports_missing_install4j_for_incomplete_runtime()
    test_repair_report_redacts_sensitive_files()
    test_select_command_prefers_project_jar_when_available()
    print("jdownloader_internal_process_test OK")


if __name__ == "__main__":
    main()
