from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "third_party" / "jdownloader" / "bridge" / "src"
BUILD = ROOT / "third_party" / "jdownloader" / "bridge" / "build"
JDK21_JAVAC = Path(r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot\bin\javac.exe")


def _run_compile(javac: str, sources: list[str], args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [javac, *args, "-d", str(BUILD), *sources],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    javac = shutil.which("javac") or (str(JDK21_JAVAC) if JDK21_JAVAC.is_file() else "")
    BUILD.mkdir(parents=True, exist_ok=True)
    sources = [str(path) for path in SRC.rglob("*.java")]
    report = {
        "javac": javac or "",
        "source_dir": str(SRC),
        "build_dir": str(BUILD),
        "sources": sources,
        "compiled": False,
        "attempts": [],
    }
    if not javac:
        report["warning"] = "javac was not found on PATH"
        print(json.dumps(report, indent=2))
        return 2
    if not sources:
        report["warning"] = "No Java bridge sources were found"
        print(json.dumps(report, indent=2))
        return 3

    compile_attempts = [
        ["-encoding", "UTF-8", "--release", "8"],
        ["-encoding", "UTF-8", "-source", "8", "-target", "8"],
        ["-encoding", "UTF-8"],
    ]
    completed = None
    for args in compile_attempts:
        completed = _run_compile(javac, sources, args)
        report["attempts"].append(
            {
                "args": args,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        if completed.returncode == 0:
            report["compiled"] = True
            report["selected_args"] = args
            break

    assert completed is not None
    report["returncode"] = completed.returncode
    report["stdout"] = completed.stdout
    report["stderr"] = completed.stderr
    print(json.dumps(report, indent=2))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
