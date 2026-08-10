from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_REPO = r"T:\References\to go\Media\tools\Modified YouTube comment extractor"


def _q(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def build_command_index(repo_root: Path, target_root: Path, out_dir: Path) -> str:
    py = r"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe"
    repo = str(repo_root)
    target = str(target_root)
    out = str(out_dir)
    lines = [
        "# MSN Source Adapter Final Command Index",
        "",
        "These commands are generated for the final MSN adapter operator workflow.",
        "They do not claim live completion without a positive manual/live evidence file.",
        "",
        "## 1. Check repo status",
        "",
        "```cmd",
        f"git -C {_q(repo)} status --short",
        "```",
        "",
        "## 2. Build operator health dashboard",
        "",
        "```cmd",
        f"{_q(py)} {_q(str(repo_root / 'source_msn_adapter_operator_health_dashboard.py'))} --repo-root {_q(repo)} --target-root {_q(target)} --out {_q(str(out_dir / 'operator_health'))}",
        "```",
        "",
        "## 3. Generate quickstart materials",
        "",
        "```cmd",
        f"{_q(py)} {_q(str(repo_root / 'source_msn_adapter_operator_quickstart.py'))} --help",
        "```",
        "",
        "## 4. Run final promotion only after live evidence exists",
        "",
        "```cmd",
        f"{_q(py)} {_q(str(repo_root / 'source_msn_adapter_release_promotion.py'))} --help",
        "```",
        "",
        "## 5. Run certification/archive after promotion gate",
        "",
        "```cmd",
        f"{_q(py)} {_q(str(repo_root / 'source_msn_adapter_certification_bundle.py'))} --help",
        f"{_q(py)} {_q(str(repo_root / 'source_msn_adapter_certification_archive.py'))} --help",
        "```",
        "",
        "## Locked wording",
        "",
        "Until positive manual/live evidence exists, the correct status is `READY_FOR_LIVE_EVIDENCE` or `RC_LOCKED_PENDING_LIVE_EVIDENCE`, not `COMPLETE`.",
        "",
    ]
    return "\n".join(lines)


def write_command_index(repo_root: Path, target_root: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "MSN_SOURCE_ADAPTER_FINAL_COMMAND_INDEX.generated.md"
    cmd = out_dir / "RUN_MSN_OPERATOR_HEALTH_DASHBOARD.cmd"
    md.write_text(build_command_index(repo_root, target_root, out_dir), encoding="utf-8")
    cmd.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        f"\"C:\\Users\\fahad\\AppData\\Local\\Programs\\Python\\Python311\\python.exe\" \"{repo_root / 'source_msn_adapter_operator_health_dashboard.py'}\" --repo-root \"{repo_root}\" --target-root \"{target_root}\" --out \"{out_dir / 'operator_health'}\"\r\n"
        "exit /b %ERRORLEVEL%\r\n",
        encoding="utf-8",
    )
    return {"markdown": str(md), "cmd": str(cmd)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an MSN final operator command index.")
    parser.add_argument("--repo-root", default=DEFAULT_REPO)
    parser.add_argument("--target-root", default=".")
    parser.add_argument("--out", default="msn_operator_command_index")
    args = parser.parse_args(argv)
    paths = write_command_index(Path(args.repo_root), Path(args.target_root), Path(args.out))
    print("MSN final command index written:")
    for key, value in paths.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
