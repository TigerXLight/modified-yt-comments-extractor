from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ARCHIVEBOX_MODE_DOCKER_COMPOSE = "docker_compose"
ARCHIVEBOX_MODE_WSL2 = "wsl2"
ARCHIVEBOX_MODE_REMOTE = "remote"
ARCHIVEBOX_MODE_NATIVE_UNIX = "native_unix"
ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED = "native_windows_unsupported"
ARCHIVEBOX_MODE_WINDOWS_DOCKER_COMPOSE = "WINDOWS_DOCKER_COMPOSE"
ARCHIVEBOX_MODE_WINDOWS_WSL2_CLI = "WINDOWS_WSL2_CLI"
ARCHIVEBOX_MODE_WINDOWS_WSL2_DOCKER = "WINDOWS_WSL2_DOCKER"
ARCHIVEBOX_MODE_REMOTE_ARCHIVEBOX = "REMOTE_ARCHIVEBOX"
ARCHIVEBOX_MODE_NATIVE_UNIX_REV4 = "NATIVE_UNIX"
ARCHIVEBOX_MODE_UNSUPPORTED_NATIVE_WINDOWS = "UNSUPPORTED_NATIVE_WINDOWS"

ARCHIVEBOX_PROFILE_LIGHT = "light"
ARCHIVEBOX_PROFILE_BALANCED = "balanced"
ARCHIVEBOX_PROFILE_FULL = "full"

ARCHIVEBOX_PROFILES: dict[str, dict[str, Any]] = {
    ARCHIVEBOX_PROFILE_LIGHT: {
        "concurrency": 1,
        "expected_size": "small",
        "expected_time": "short",
        "extractors": ("title", "favicon", "headers", "singlefile"),
    },
    ARCHIVEBOX_PROFILE_BALANCED: {
        "concurrency": 2,
        "expected_size": "medium",
        "expected_time": "moderate",
        "extractors": ("title", "favicon", "headers", "singlefile", "screenshot", "pdf"),
    },
    ARCHIVEBOX_PROFILE_FULL: {
        "concurrency": 1,
        "expected_size": "large",
        "expected_time": "long",
        "extractors": (
            "title",
            "favicon",
            "headers",
            "singlefile",
            "screenshot",
            "pdf",
            "dom",
            "media",
            "wget",
            "warc",
        ),
    },
}

ARCHIVEBOX_SCOPE = (
    "ArchiveBox command planning only; no process execution, install, Docker/WSL launch, "
    "network call, archive submission, credential use, browser automation, or GUI behavior"
)


@dataclass(frozen=True)
class ArchiveBoxCommandPlan:
    mode: str
    url: str
    profile: str = ARCHIVEBOX_PROFILE_LIGHT
    command: tuple[str, ...] = ()
    executable: bool = False
    command_execution: str = "not executed"
    safety_status: str = "plan_only"
    expected_output: str = ""
    profile_metadata: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    scope: str = ARCHIVEBOX_SCOPE

    def to_dict(self) -> dict[str, Any]:
        profile_metadata = {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in dict(self.profile_metadata or {}).items()
        }
        return {
            "command": list(self.command),
            "command_execution": self.command_execution,
            "executable": self.executable,
            "expected_output": self.expected_output,
            "mode": self.mode,
            "profile": self.profile,
            "profile_metadata": profile_metadata,
            "safety_status": self.safety_status,
            "scope": self.scope,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def _normalized_mode(mode: str) -> str:
    if mode == ARCHIVEBOX_MODE_DOCKER_COMPOSE:
        return ARCHIVEBOX_MODE_WINDOWS_DOCKER_COMPOSE
    if mode == ARCHIVEBOX_MODE_WSL2:
        return ARCHIVEBOX_MODE_WINDOWS_WSL2_CLI
    if mode == ARCHIVEBOX_MODE_REMOTE:
        return ARCHIVEBOX_MODE_REMOTE_ARCHIVEBOX
    if mode == ARCHIVEBOX_MODE_NATIVE_UNIX:
        return ARCHIVEBOX_MODE_NATIVE_UNIX_REV4
    if mode == ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED:
        return ARCHIVEBOX_MODE_UNSUPPORTED_NATIVE_WINDOWS
    return mode or ARCHIVEBOX_MODE_UNSUPPORTED_NATIVE_WINDOWS


def _profile_metadata(profile: str) -> dict[str, Any]:
    selected = profile if profile in ARCHIVEBOX_PROFILES else ARCHIVEBOX_PROFILE_LIGHT
    return dict(ARCHIVEBOX_PROFILES[selected])


def build_archivebox_command_plan(
    *,
    mode: str,
    url: str,
    profile: str = ARCHIVEBOX_PROFILE_LIGHT,
    expected_output: str = "archivebox/index.html",
) -> ArchiveBoxCommandPlan:
    normalized_mode = _normalized_mode(mode)
    selected_profile = profile if profile in ARCHIVEBOX_PROFILES else ARCHIVEBOX_PROFILE_LIGHT
    metadata = _profile_metadata(selected_profile)
    if normalized_mode == ARCHIVEBOX_MODE_WINDOWS_DOCKER_COMPOSE:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            profile=selected_profile,
            command=("docker", "compose", "run", "--rm", "archivebox", "add", url),
            executable=False,
            expected_output=expected_output,
            profile_metadata=metadata,
            warnings=("Plan only: Docker Compose command is not executed by this helper.",),
        )
    if normalized_mode == ARCHIVEBOX_MODE_WINDOWS_WSL2_CLI:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            profile=selected_profile,
            command=("wsl", "archivebox", "add", url),
            executable=False,
            expected_output=expected_output,
            profile_metadata=metadata,
            warnings=("Plan only: WSL2 command is not executed by this helper.",),
        )
    if normalized_mode == ARCHIVEBOX_MODE_WINDOWS_WSL2_DOCKER:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            profile=selected_profile,
            command=("wsl", "docker", "compose", "run", "--rm", "archivebox", "add", url),
            executable=False,
            expected_output=expected_output,
            profile_metadata=metadata,
            warnings=("Plan only: WSL2 Docker command is not executed by this helper.",),
        )
    if normalized_mode == ARCHIVEBOX_MODE_REMOTE_ARCHIVEBOX:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            command=(),
            executable=False,
            profile=selected_profile,
            expected_output=expected_output,
            profile_metadata=metadata,
            warnings=("Remote ArchiveBox API interaction remains separately gated and is not executed.",),
        )
    if normalized_mode == ARCHIVEBOX_MODE_NATIVE_UNIX_REV4:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            profile=selected_profile,
            command=("archivebox", "add", url),
            executable=False,
            expected_output=expected_output,
            profile_metadata=metadata,
            warnings=("Plan only: native Unix ArchiveBox command is not executed by this helper.",),
        )
    return ArchiveBoxCommandPlan(
        mode=mode or ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED,
        url=url,
        profile=selected_profile,
        command=(),
        executable=False,
        expected_output=expected_output,
        profile_metadata=metadata,
        warnings=("Native Windows ArchiveBox execution is unsupported here; use Docker, WSL2, or remote mode after approval.",),
    )
