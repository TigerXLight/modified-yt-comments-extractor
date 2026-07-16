from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ARCHIVEBOX_MODE_DOCKER_COMPOSE = "docker_compose"
ARCHIVEBOX_MODE_WSL2 = "wsl2"
ARCHIVEBOX_MODE_REMOTE = "remote"
ARCHIVEBOX_MODE_NATIVE_UNIX = "native_unix"
ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED = "native_windows_unsupported"

ARCHIVEBOX_SCOPE = (
    "ArchiveBox command planning only; no process execution, install, Docker/WSL launch, "
    "network call, archive submission, credential use, browser automation, or GUI behavior"
)


@dataclass(frozen=True)
class ArchiveBoxCommandPlan:
    mode: str
    url: str
    command: tuple[str, ...] = ()
    executable: bool = False
    warnings: tuple[str, ...] = ()
    scope: str = ARCHIVEBOX_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": list(self.command),
            "executable": self.executable,
            "mode": self.mode,
            "scope": self.scope,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def build_archivebox_command_plan(*, mode: str, url: str) -> ArchiveBoxCommandPlan:
    if mode == ARCHIVEBOX_MODE_DOCKER_COMPOSE:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            command=("docker", "compose", "run", "--rm", "archivebox", "add", url),
            executable=False,
            warnings=("Plan only: Docker Compose command is not executed by this helper.",),
        )
    if mode == ARCHIVEBOX_MODE_WSL2:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            command=("wsl", "archivebox", "add", url),
            executable=False,
            warnings=("Plan only: WSL2 command is not executed by this helper.",),
        )
    if mode == ARCHIVEBOX_MODE_REMOTE:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            command=(),
            executable=False,
            warnings=("Remote ArchiveBox API interaction remains separately gated.",),
        )
    if mode == ARCHIVEBOX_MODE_NATIVE_UNIX:
        return ArchiveBoxCommandPlan(
            mode=mode,
            url=url,
            command=("archivebox", "add", url),
            executable=False,
            warnings=("Plan only: native Unix ArchiveBox command is not executed by this helper.",),
        )
    return ArchiveBoxCommandPlan(
        mode=mode or ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED,
        url=url,
        command=(),
        executable=False,
        warnings=("Native Windows ArchiveBox execution is unsupported here; use Docker, WSL2, or remote mode after approval.",),
    )
