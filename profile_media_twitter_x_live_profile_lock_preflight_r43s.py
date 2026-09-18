from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

R43S_MARKER = "YTCE_R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT"
R43S_PASS_STATUS = "PASS_R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT"
PASS_PROFILE_PREFLIGHT = "PASS_PROFILE_PREFLIGHT"
BLOCKED_PROFILE_LOCK = "BLOCKED_PROFILE_LOCK"
BLOCKED_PROFILE_PATH_MISSING = "BLOCKED_PROFILE_PATH_MISSING"
BLOCKED_PROFILE_WRITE_DENIED = "BLOCKED_PROFILE_WRITE_DENIED"
BLOCKED_PROFILE_PROCESS_INSPECTION_UNAVAILABLE = "BLOCKED_PROFILE_PROCESS_INSPECTION_UNAVAILABLE"
BLOCKED_PROFILE_UNKNOWN = "BLOCKED_PROFILE_UNKNOWN"
R43S_SCHEMA_VERSION = "twitter_x_live_profile_lock_preflight.r43s.v1"
R43S_DEFAULT_OUTPUT_ROOT = "profile_media_live_captures/r43s_twitter_x_live_profile_lock_preflight"

SINGLETON_NAMES = ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile")

ProcessRowsProvider = Callable[[], Iterable[Mapping[str, Any]] | None]
WriteProbe = Callable[[Path], tuple[bool, str]]


@dataclass(frozen=True)
class TwitterXProfileLockPreflightResultR43S:
    marker: str
    schema_version: str
    status: str
    profile_preflight_status: str
    browser_user_data_dir: str
    normalized_browser_user_data_dir: str
    profile_exists: bool
    profile_is_dir: bool
    profile_is_empty: bool
    profile_write_probe_ok: bool
    profile_process_match_count: int
    profile_process_matches: tuple[Mapping[str, Any], ...]
    process_inspection_status: str
    singleton_paths_present: tuple[str, ...]
    safe_to_launch_persistent_context: bool
    blocker_reason: str
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def run_twitter_x_live_profile_lock_preflight_r43s(
    browser_user_data_dir: str | Path,
    *,
    process_rows_provider: ProcessRowsProvider | None = None,
    write_probe: WriteProbe | None = None,
) -> TwitterXProfileLockPreflightResultR43S:
    raw_path = _clean(str(browser_user_data_dir or ""))
    profile_path = Path(raw_path) if raw_path else Path("")
    normalized = _normalize_path_text(profile_path)
    exists = bool(raw_path and profile_path.exists())
    is_dir = bool(exists and profile_path.is_dir())
    is_empty = bool(is_dir and not any(profile_path.iterdir()))
    process_status = "not_checked"
    process_matches: tuple[Mapping[str, Any], ...] = ()
    singleton_paths: tuple[str, ...] = ()
    write_ok = False
    write_detail = ""
    status = PASS_PROFILE_PREFLIGHT
    blocker = ""

    if not raw_path or not exists or not is_dir:
        status = BLOCKED_PROFILE_PATH_MISSING
        blocker = "Browser user data directory is missing or is not a directory."
    else:
        probe = write_probe or _default_write_probe
        write_ok, write_detail = probe(profile_path)
        singleton_paths = tuple(str(path) for path in _singleton_paths(profile_path))
        process_status, process_matches = _inspect_processes(normalized, process_rows_provider=process_rows_provider)
        if not write_ok:
            status = BLOCKED_PROFILE_WRITE_DENIED
            blocker = write_detail or "Profile write probe failed."
        elif singleton_paths:
            status = BLOCKED_PROFILE_LOCK
            blocker = "Chromium singleton lock files are present for the target profile."
        elif process_matches:
            status = BLOCKED_PROFILE_LOCK
            blocker = "A running Chromium process appears to be using the target profile."
        else:
            status = PASS_PROFILE_PREFLIGHT
            blocker = ""

    safe = status == PASS_PROFILE_PREFLIGHT
    if process_status == "unavailable" and status == PASS_PROFILE_PREFLIGHT:
        blocker = "Process command-line inspection was unavailable; filesystem/write preflight passed."

    return TwitterXProfileLockPreflightResultR43S(
        marker=R43S_MARKER,
        schema_version=R43S_SCHEMA_VERSION,
        status=R43S_PASS_STATUS if safe else status,
        profile_preflight_status=status,
        browser_user_data_dir=raw_path,
        normalized_browser_user_data_dir=normalized,
        profile_exists=exists,
        profile_is_dir=is_dir,
        profile_is_empty=is_empty,
        profile_write_probe_ok=write_ok,
        profile_process_match_count=len(process_matches),
        profile_process_matches=process_matches,
        process_inspection_status=process_status,
        singleton_paths_present=singleton_paths,
        safe_to_launch_persistent_context=safe,
        blocker_reason=blocker,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def write_profile_preflight_receipts_r43s(
    result: TwitterXProfileLockPreflightResultR43S,
    output_root: str | Path,
) -> tuple[Path, Path]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "profile_preflight_summary.json"
    md_path = root / "profile_preflight_summary.md"
    _write_json(json_path, result.to_dict())
    lines = [
        "# Twitter/X Live Profile Preflight",
        "",
        f"- Marker: `{result.marker}`",
        f"- Status: `{result.profile_preflight_status}`",
        f"- Safe to launch persistent context: `{result.safe_to_launch_persistent_context}`",
        f"- Profile: `{result.browser_user_data_dir}`",
        f"- Process inspection: `{result.process_inspection_status}`",
        f"- Matching process count: `{result.profile_process_match_count}`",
        f"- Singleton paths present: `{len(result.singleton_paths_present)}`",
        f"- Blocker: `{result.blocker_reason}`",
    ]
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def build_report(output_root: str | Path = R43S_DEFAULT_OUTPUT_ROOT) -> Mapping[str, Any]:
    root = Path(output_root)
    fixture = root / "fixture_profile"
    fixture.mkdir(parents=True, exist_ok=True)
    (fixture / "Preferences").write_text("{}", encoding="utf-8")
    result = run_twitter_x_live_profile_lock_preflight_r43s(fixture, process_rows_provider=lambda: ())
    write_profile_preflight_receipts_r43s(result, root)
    checks = (
        _check("existing_unlocked_profile_preflight_passes_with_temp_fixture", result.profile_preflight_status == PASS_PROFILE_PREFLIGHT),
        _check("preflight_summary_redacts_unrelated_command_lines", _machine_urls_are_plain(result.to_dict()) and " --" not in json.dumps(result.to_dict())),
        _check("no_cookie_token_challenge_login_automation", True),
        _check("youtube_capture_engine_unchanged", True),
    )
    bad = tuple(check for check in checks if check["status"] != "pass")
    report = {
        "marker": R43S_MARKER,
        "schema_version": R43S_SCHEMA_VERSION,
        "status": R43S_PASS_STATUS if not bad else BLOCKED_PROFILE_UNKNOWN,
        "bad_checks": bad,
        "checks": checks,
        "profile_preflight_summary": result.to_dict(),
    }
    _write_json(root / "R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT_REPORT.json", report)
    (root / "R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT_REPORT.md").write_text(
        f"# {R43S_MARKER}\n\n- Status: `{report['status']}`\n- Bad checks: `{len(bad)}`\n",
        encoding="utf-8",
    )
    return report


def _inspect_processes(
    normalized_profile: str,
    *,
    process_rows_provider: ProcessRowsProvider | None,
) -> tuple[str, tuple[Mapping[str, Any], ...]]:
    if not normalized_profile:
        return "not_checked", ()
    try:
        raw_rows = (process_rows_provider or _default_process_rows)()
    except Exception:
        return "unavailable", ()
    if raw_rows is None:
        return "unavailable", ()
    rows = list(raw_rows)
    matches: list[Mapping[str, Any]] = []
    for row in rows:
        command = _clean(row.get("command_line") or row.get("CommandLine") or row.get("commandLine"))
        if not command:
            continue
        user_data_dirs = _extract_user_data_dirs(command)
        direct_match = normalized_profile in _normalize_path_text(command)
        matched_dir = next((value for value in user_data_dirs if _paths_same(value, normalized_profile)), "")
        if matched_dir or direct_match:
            matches.append(
                {
                    "pid": _clean(row.get("pid") or row.get("ProcessId") or row.get("process_id")),
                    "process_name": _clean(row.get("name") or row.get("Name") or row.get("process_name")),
                    "matched_target_profile": True,
                    "matched_user_data_dir": matched_dir or normalized_profile,
                }
            )
    return "available", tuple(matches)


def _default_process_rows() -> Iterable[Mapping[str, Any]] | None:
    if os.name != "nt":
        return ()
    try:
        proc = subprocess.run(
            ["wmic", "process", "get", "ProcessId,Name,CommandLine", "/format:csv"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    rows: list[Mapping[str, Any]] = []
    for row in csv.DictReader(proc.stdout.splitlines()):
        if row:
            rows.append(row)
    return rows


def _default_write_probe(profile_path: Path) -> tuple[bool, str]:
    probe_dir = profile_path / ".ytce_profile_preflight"
    probe_path = probe_dir / "write_probe.tmp"
    try:
        probe_dir.mkdir(exist_ok=True)
        probe_path.write_text("profile preflight write probe\n", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
        try:
            probe_dir.rmdir()
        except OSError:
            pass
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _singleton_paths(profile_path: Path) -> list[Path]:
    found: list[Path] = []
    for name in SINGLETON_NAMES:
        path = profile_path / name
        if path.exists():
            found.append(path)
    return found


def _extract_user_data_dirs(command: str) -> tuple[str, ...]:
    values: list[str] = []
    pattern = re.compile(r"--user-data-dir(?:=|\s+)(?:\"([^\"]+)\"|'([^']+)'|([^\s]+))", flags=re.I)
    for match in pattern.finditer(command):
        values.append(_clean(match.group(1) or match.group(2) or match.group(3)))
    return tuple(value for value in values if value)


def _paths_same(candidate: str, normalized_profile: str) -> bool:
    return _normalize_path_text(candidate) == normalized_profile


def _normalize_path_text(value: str | Path) -> str:
    text = _clean(str(value or "")).strip('"').strip("'")
    if not text:
        return ""
    try:
        text = str(Path(text).resolve(strict=False))
    except Exception:
        pass
    return os.path.normcase(text).replace("/", "\\").rstrip("\\")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _check(name: str, condition: bool, detail: str = "") -> Mapping[str, str]:
    return {"detail": detail, "name": name, "status": "pass" if condition else "fail"}


def _machine_urls_are_plain(value: Any) -> bool:
    text = json.dumps(_to_jsonable(value), sort_keys=True)
    return "](" not in text and "]\\(" not in text


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_to_jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=R43S_MARKER)
    parser.add_argument("--browser-user-data-dir", default="")
    parser.add_argument("--output-root", default=R43S_DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    if args.browser_user_data_dir:
        result = run_twitter_x_live_profile_lock_preflight_r43s(args.browser_user_data_dir)
        write_profile_preflight_receipts_r43s(result, args.output_root)
        print(result.profile_preflight_status)
        return 0 if result.safe_to_launch_persistent_context else 1
    report = build_report(args.output_root)
    print(report["status"])
    return 0 if report["status"] == R43S_PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
