from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import time
import fnmatch
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import URLError
from urllib.request import urlopen

from jdownloader_internal_paths import JD_RUNTIME_DIR, JDOWNLOADER_INTERNAL_BACKEND_ID, LOCAL_JD_INSTALLED_ROOT, REPO_ROOT


CNL_HOST = "127.0.0.1"
CNL_PORT = 9666
CNL_JDCHECK_URL = f"http://{CNL_HOST}:{CNL_PORT}/jdcheckjson"
DEPRECATED_API_PORT = 3128

LAUNCH_ATTEMPTED = "LAUNCH_ATTEMPTED"
INSTALLATION_VALIDATING = "INSTALLATION_VALIDATING"
READY = "READY"
START_FAILED = "START_FAILED"
READY_TIMEOUT = "READY_TIMEOUT"

SENSITIVE_RUNTIME_PATTERNS = (
    "cfg/org.jdownloader.settings.AccountSettings.accounts.ejs",
    "cfg/downloadList*.zip",
    "cfg/linkcollector*.zip",
    "error.log",
    "output.log",
)

PopenFactory = Callable[..., subprocess.Popen[Any]]
CnlProbe = Callable[[], bool]


@dataclass(frozen=True)
class JDownloaderProcessReport:
    status: str
    backend_id: str = JDOWNLOADER_INTERNAL_BACKEND_ID
    runtime_dir: str = ""
    executable_path: str = ""
    pid: int = 0
    started_at_utc: str = ""
    command_line: tuple[str, ...] = ()
    project_local_runtime: bool = False
    external_appdata_used_as_primary: bool = False
    external_cnl_port_in_use: bool = False
    warm_job: bool = False
    readiness_status: str = ""
    launch_state: str = ""
    ready_wait_ms: int = 0
    cwd: str = ""
    preflight_missing: tuple[str, ...] = ()
    stdout_log_path: str = ""
    stderr_log_path: str = ""
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class JDownloaderRuntimePreflightReport:
    runtime_dir: str
    project_local_runtime: bool
    ready_for_exe_launch: bool
    ready_for_jar_launch: bool
    missing: tuple[str, ...] = ()
    present: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class JDownloaderRuntimeRepairReport:
    status: str
    source_dir: str
    runtime_dir: str
    copied_count: int = 0
    skipped_sensitive_count: int = 0
    preflight: JDownloaderRuntimePreflightReport | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def utc_now_text() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_project_local_runtime(runtime_dir: str | Path = JD_RUNTIME_DIR) -> bool:
    runtime = Path(runtime_dir)
    return _is_relative_to(runtime, REPO_ROOT / "third_party" / "jdownloader" / "runtime")


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_sensitive_runtime_relative_path(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in SENSITIVE_RUNTIME_PATTERNS)


def runtime_preflight(runtime_dir: str | Path = JD_RUNTIME_DIR) -> JDownloaderRuntimePreflightReport:
    runtime = Path(runtime_dir)
    required = (
        "JDownloader2.exe",
        "JDownloader.jar",
        "Core.jar",
        ".install4j",
        "libs",
        "jd/plugins",
        "cfg/org.jdownloader.api.RemoteAPIConfig.json",
        "cfg/plugins/youtube/Youtube.json",
    )
    youtube_component = "org/jdownloader/plugins/components/youtube"
    present: list[str] = []
    missing: list[str] = []
    for relative in required:
        path = runtime / Path(relative)
        if path.exists():
            present.append(relative)
        else:
            missing.append(relative)
    if (runtime / youtube_component).exists():
        present.append(youtube_component)
    elif (runtime / "Core.jar").is_file():
        present.append(f"{youtube_component} (expected inside Core.jar)")
    else:
        missing.append(youtube_component)
    warnings: list[str] = []
    if not is_project_local_runtime(runtime):
        warnings.append("Runtime directory is not project-local.")
    if missing:
        warnings.append("Project-local runtime is incomplete for JDownloader2.exe launch.")
    return JDownloaderRuntimePreflightReport(
        runtime_dir=str(runtime),
        project_local_runtime=is_project_local_runtime(runtime),
        ready_for_exe_launch=not missing and (runtime / "JDownloader2.exe").is_file(),
        ready_for_jar_launch=(runtime / "JDownloader.jar").is_file() and (runtime / "Core.jar").is_file(),
        missing=tuple(missing),
        present=tuple(present),
        warnings=tuple(warnings),
    )


def ensure_project_local_deprecated_api_config(runtime_dir: str | Path = JD_RUNTIME_DIR) -> Path:
    """Enable JD's localhost-only Deprecated API in the project runtime config."""
    runtime = Path(runtime_dir)
    if not is_project_local_runtime(runtime):
        raise ValueError("Refusing to edit Deprecated API config outside the project-local JDownloader runtime.")
    cfg_dir = runtime / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    config_path = cfg_dir / "org.jdownloader.api.RemoteAPIConfig.json"
    data: dict[str, Any] = {}
    if config_path.is_file():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except Exception:
            data = {}
    data.update(
        {
            "deprecatedapienabled": True,
            "deprecatedapilocalhostonly": True,
            "deprecatedapiport": DEPRECATED_API_PORT,
            "externinterfaceenabled": True,
            "externinterfacelocalhostonly": True,
        }
    )
    config_path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return config_path


def repair_project_local_runtime(
    *,
    source_dir: str | Path = LOCAL_JD_INSTALLED_ROOT,
    runtime_dir: str | Path = JD_RUNTIME_DIR,
) -> JDownloaderRuntimeRepairReport:
    source = Path(source_dir)
    runtime = Path(runtime_dir)
    warnings: list[str] = []
    errors: list[str] = []
    if not source.is_dir():
        return JDownloaderRuntimeRepairReport(
            status="failed",
            source_dir=str(source),
            runtime_dir=str(runtime),
            errors=("Installed JDownloader source directory was not found.",),
        )
    if not is_project_local_runtime(runtime):
        return JDownloaderRuntimeRepairReport(
            status="failed",
            source_dir=str(source),
            runtime_dir=str(runtime),
            errors=("Refusing to repair a runtime outside third_party/jdownloader/runtime.",),
        )
    copied_count = 0
    skipped_sensitive = 0
    runtime.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        relative = _relative_posix(path, source)
        if _is_sensitive_runtime_relative_path(relative):
            skipped_sensitive += 1
            continue
        target = runtime / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied_count += 1
    preflight = runtime_preflight(runtime)
    status = "ready" if preflight.ready_for_exe_launch or preflight.ready_for_jar_launch else "incomplete"
    if preflight.missing:
        warnings.append("Runtime repair completed but preflight still reports missing launch files.")
    return JDownloaderRuntimeRepairReport(
        status=status,
        source_dir=str(source),
        runtime_dir=str(runtime),
        copied_count=copied_count,
        skipped_sensitive_count=skipped_sensitive,
        preflight=preflight,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def cnl_port_is_open(host: str = CNL_HOST, port: int = CNL_PORT, timeout_seconds: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def cnl_jdcheck_responds(timeout_seconds: float = 0.75) -> bool:
    try:
        with urlopen(CNL_JDCHECK_URL, timeout=timeout_seconds) as response:
            body = response.read(2048).decode("utf-8", errors="replace")
            return response.status == 200 and ("JDownloader" in body or "true" in body.lower())
    except (OSError, URLError, ValueError):
        return False


def project_local_jdownloader_process_running(runtime_dir: str | Path = JD_RUNTIME_DIR) -> bool:
    runtime = Path(runtime_dir)
    command = (
        "Get-Process -Name JDownloader2 -ErrorAction SilentlyContinue | "
        "ForEach-Object { $_.Path }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
    except Exception:
        return False
    for line in (completed.stdout or "").splitlines():
        path = line.strip()
        if path and _is_relative_to(Path(path), runtime):
            return True
    return False


def select_internal_runtime_command(runtime_dir: str | Path = JD_RUNTIME_DIR) -> tuple[str, ...]:
    runtime = Path(runtime_dir)
    jar = runtime / "JDownloader.jar"
    exe = runtime / "JDownloader2.exe"
    java = shutil.which("java")
    preflight = runtime_preflight(runtime)
    if preflight.ready_for_exe_launch and exe.is_file():
        return (str(exe),)
    if java and preflight.ready_for_jar_launch and jar.is_file():
        return (java, "-jar", str(jar))
    if preflight.ready_for_jar_launch and jar.is_file():
        return ("java", "-jar", str(jar))
    return ()


class JDownloaderInternalProcessManager:
    def __init__(
        self,
        *,
        runtime_dir: str | Path = JD_RUNTIME_DIR,
        log_dir: str | Path | None = None,
        popen_factory: PopenFactory = subprocess.Popen,
        cnl_probe: CnlProbe = cnl_jdcheck_responds,
    ) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.log_dir = Path(log_dir) if log_dir is not None else Path(tempfile.gettempdir()) / "ytce_jdownloader_internal_logs"
        self.popen_factory = popen_factory
        self.cnl_probe = cnl_probe
        self.process: subprocess.Popen[Any] | None = None
        self.started_at_utc = ""
        self.command_line: tuple[str, ...] = ()
        self.stdout_log_path = ""
        self.stderr_log_path = ""

    def status(self) -> JDownloaderProcessReport:
        if self.process is not None and self.process.poll() is None:
            return self._report("running", warm_job=True)
        if self.process is not None:
            return self._report("stopped", warnings=("Internal JDownloader process is no longer running.",))
        return self._report("not_started")

    def probe(self) -> JDownloaderProcessReport:
        if self.process is None or self.process.poll() is not None:
            if self.cnl_probe():
                if project_local_jdownloader_process_running(self.runtime_dir):
                    return self._report(
                        READY,
                        readiness_status=READY,
                        launch_state=READY,
                        warm_job=True,
                        warnings=("Existing CNL endpoint belongs to project-local JDownloader runtime.",),
                    )
                return self._report(
                    "external_cnl_port_in_use",
                    external_cnl_port_in_use=True,
                    errors=("CNL endpoint responded before YTCE started the project-local runtime.",),
                )
            return self._report("not_started")
        return self._report("running", warm_job=True, warnings=("CNL endpoint ready." if self.cnl_probe() else "Process running; CNL endpoint not ready yet.",))

    def start(self, *, allow_existing_project_local: bool = False) -> JDownloaderProcessReport:
        if not is_project_local_runtime(self.runtime_dir):
            return self._report("failed", errors=("Runtime directory is not under third_party/jdownloader/runtime.",))
        if not self.runtime_dir.is_dir():
            return self._report("failed", errors=("Project-local JDownloader runtime directory is missing.",))
        try:
            ensure_project_local_deprecated_api_config(self.runtime_dir)
        except Exception as exc:
            return self._report("failed", errors=(f"Could not enable project-local Deprecated API config: {type(exc).__name__}: {exc}",))
        preflight = runtime_preflight(self.runtime_dir)
        if not (preflight.ready_for_exe_launch or preflight.ready_for_jar_launch):
            return self._report(
                START_FAILED,
                launch_state=INSTALLATION_VALIDATING,
                preflight_missing=preflight.missing,
                warnings=preflight.warnings,
                errors=("Project-local JDownloader runtime failed preflight; run REPAIR_INTERNAL_JDOWNLOADER_RUNTIME.cmd.",),
            )
        if self.process is not None and self.process.poll() is None:
            return self._wait_for_ready(warm_job=True)
        if self.cnl_probe() and project_local_jdownloader_process_running(self.runtime_dir):
            return self._report(
                READY,
                launch_state=READY,
                readiness_status=READY,
                warm_job=True,
                warnings=("Reusing already-running project-local JDownloader runtime.",),
            )
        if self.cnl_probe() and allow_existing_project_local:
            return self._report(
                READY,
                launch_state=READY,
                readiness_status=READY,
                warm_job=True,
                warnings=("CNL endpoint was already ready; caller explicitly allowed existing project-local test runtime.",),
            )
        if self.cnl_probe() and not allow_existing_project_local:
            return self._report(
                "blocked_external_cnl_port",
                external_cnl_port_in_use=True,
                errors=("A CNL endpoint already responded on 127.0.0.1:9666; refusing to use a possibly external AppData JDownloader.",),
            )
        command = select_internal_runtime_command(self.runtime_dir)
        if not command:
            return self._report("failed", errors=("No project-local JDownloader.jar/JDownloader2.exe launch route was found.",))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        stdout_path = self.log_dir / f"jdownloader-internal-{stamp}.out.log"
        stderr_path = self.log_dir / f"jdownloader-internal-{stamp}.err.log"
        stdout_handle = stdout_path.open("ab")
        stderr_handle = stderr_path.open("ab")
        try:
            self.process = self.popen_factory(
                list(command),
                cwd=str(self.runtime_dir),
                stdout=stdout_handle,
                stderr=stderr_handle,
                stdin=subprocess.DEVNULL,
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
        self.started_at_utc = utc_now_text()
        self.command_line = tuple(command)
        self.stdout_log_path = str(stdout_path)
        self.stderr_log_path = str(stderr_path)
        return self._wait_for_ready()

    def _wait_for_ready(
        self,
        *,
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 1.0,
        warm_job: bool = False,
    ) -> JDownloaderProcessReport:
        start = time.monotonic()
        launcher_exited = False
        while True:
            if self.cnl_probe():
                warnings = ("Launcher process exited after spawning/restarting project-local JDownloader child.",) if launcher_exited else ()
                return self._report(
                    READY,
                    launch_state=READY,
                    readiness_status=READY,
                    ready_wait_ms=int((time.monotonic() - start) * 1000),
                    warm_job=warm_job,
                    warnings=warnings,
                )
            if self.process is not None and self.process.poll() is not None:
                launcher_exited = True
            if (time.monotonic() - start) >= timeout_seconds:
                status = START_FAILED if launcher_exited else READY_TIMEOUT
                return self._report(
                    status,
                    launch_state=status,
                    readiness_status=status,
                    ready_wait_ms=int((time.monotonic() - start) * 1000),
                    errors=("Internal JDownloader process exited before readiness endpoint responded." if launcher_exited else "Internal JDownloader process did not expose localhost CNL before timeout.",),
                )
            time.sleep(poll_interval_seconds)

    def stop(self, *, timeout_seconds: float = 10.0) -> JDownloaderProcessReport:
        if self.process is None:
            return self._report("not_started")
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout_seconds)
                return self._report("stopped", warnings=("Internal process required kill after terminate timeout.",))
        return self._report("stopped")

    def _report(
        self,
        status: str,
        *,
        external_cnl_port_in_use: bool = False,
        warm_job: bool = False,
        readiness_status: str = "",
        launch_state: str = "",
        ready_wait_ms: int = 0,
        preflight_missing: Sequence[str] = (),
        warnings: Sequence[str] = (),
        errors: Sequence[str] = (),
    ) -> JDownloaderProcessReport:
        command = self.command_line or select_internal_runtime_command(self.runtime_dir)
        executable = command[0] if command else ""
        pid = int(getattr(self.process, "pid", 0) or 0) if self.process is not None else 0
        return JDownloaderProcessReport(
            status=status,
            runtime_dir=str(self.runtime_dir),
            executable_path=executable,
            pid=pid,
            started_at_utc=self.started_at_utc,
            command_line=tuple(command),
            project_local_runtime=is_project_local_runtime(self.runtime_dir),
            external_appdata_used_as_primary=False,
            external_cnl_port_in_use=external_cnl_port_in_use,
            warm_job=warm_job,
            readiness_status=readiness_status or status,
            launch_state=launch_state or status,
            ready_wait_ms=int(ready_wait_ms or 0),
            cwd=str(self.runtime_dir),
            preflight_missing=tuple(preflight_missing),
            stdout_log_path=self.stdout_log_path,
            stderr_log_path=self.stderr_log_path,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )


_DEFAULT_MANAGER = JDownloaderInternalProcessManager()


def default_process_manager() -> JDownloaderInternalProcessManager:
    return _DEFAULT_MANAGER


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Manage the project-local internal JDownloader runtime.")
    parser.add_argument("action", choices=("start", "status", "stop", "probe", "preflight", "repair"))
    parser.add_argument("--allow-existing-project-local", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    manager = default_process_manager()
    if args.action == "start":
        report = manager.start(allow_existing_project_local=args.allow_existing_project_local)
    elif args.action == "preflight":
        report = runtime_preflight()
    elif args.action == "repair":
        report = repair_project_local_runtime()
    elif args.action == "stop":
        report = manager.stop()
    elif args.action == "probe":
        report = manager.probe()
    else:
        report = manager.status()
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if not report.errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
