from capture_archivebox import (
    ARCHIVEBOX_MODE_DOCKER_COMPOSE,
    ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED,
    ARCHIVEBOX_MODE_REMOTE,
    ARCHIVEBOX_MODE_REMOTE_ARCHIVEBOX,
    ARCHIVEBOX_MODE_WINDOWS_DOCKER_COMPOSE,
    ARCHIVEBOX_MODE_WINDOWS_WSL2_DOCKER,
    ARCHIVEBOX_MODE_WSL2,
    ARCHIVEBOX_PROFILE_BALANCED,
    ARCHIVEBOX_PROFILE_FULL,
    ARCHIVEBOX_PROFILE_LIGHT,
    build_archivebox_command_plan,
)


def test_archivebox_docker_and_wsl_plans_are_command_arrays_not_executed() -> None:
    docker = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_DOCKER_COMPOSE,
        url="https://example.test/page",
    )
    wsl = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_WSL2,
        url="https://example.test/page",
    )

    assert docker.command == (
        "docker",
        "compose",
        "run",
        "--rm",
        "archivebox",
        "add",
        "https://example.test/page",
    )
    assert docker.executable is False
    assert docker.command_execution == "not executed"
    assert docker.profile == ARCHIVEBOX_PROFILE_LIGHT
    assert "not executed" in docker.warnings[0]
    assert wsl.command == ("wsl", "archivebox", "add", "https://example.test/page")
    assert wsl.executable is False


def test_archivebox_remote_and_windows_native_are_not_executable() -> None:
    remote = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_REMOTE,
        url="https://example.test/page",
    )
    windows = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_NATIVE_WINDOWS_UNSUPPORTED,
        url="https://example.test/page",
    )

    assert remote.command == ()
    assert remote.executable is False
    assert "separately gated" in remote.warnings[0]
    assert windows.command == ()
    assert windows.executable is False
    assert "unsupported" in windows.warnings[0]


def test_archivebox_unknown_mode_fails_closed() -> None:
    plan = build_archivebox_command_plan(mode="unknown", url="https://example.test/page")

    assert plan.mode == "unknown"
    assert plan.command == ()
    assert plan.executable is False
    assert "Docker, WSL2, or remote" in plan.warnings[0]
    assert "no process execution" in plan.scope


def test_archivebox_rev4_modes_and_profiles_are_planned_without_execution() -> None:
    docker = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_WINDOWS_DOCKER_COMPOSE,
        url="https://example.test/page",
        profile=ARCHIVEBOX_PROFILE_BALANCED,
    )
    wsl_docker = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_WINDOWS_WSL2_DOCKER,
        url="https://example.test/page",
        profile=ARCHIVEBOX_PROFILE_FULL,
    )
    remote = build_archivebox_command_plan(
        mode=ARCHIVEBOX_MODE_REMOTE_ARCHIVEBOX,
        url="https://example.test/page",
        profile=ARCHIVEBOX_PROFILE_FULL,
    )

    assert docker.profile_metadata["concurrency"] == 2
    assert docker.profile_metadata["expected_size"] == "medium"
    assert docker.executable is False
    assert wsl_docker.command[:3] == ("wsl", "docker", "compose")
    assert "warc" in wsl_docker.profile_metadata["extractors"]
    assert remote.command == ()
    assert remote.command_execution == "not executed"
    rendered = repr((docker.to_dict(), wsl_docker.to_dict(), remote.to_dict())).lower()
    assert "subprocess" not in rendered
    assert "shell=true" not in rendered
    assert "ssh " not in rendered


def run_self_test() -> None:
    test_archivebox_docker_and_wsl_plans_are_command_arrays_not_executed()
    test_archivebox_remote_and_windows_native_are_not_executable()
    test_archivebox_unknown_mode_fails_closed()
    test_archivebox_rev4_modes_and_profiles_are_planned_without_execution()


if __name__ == "__main__":
    run_self_test()
    print("Capture ArchiveBox self-test passed.")
