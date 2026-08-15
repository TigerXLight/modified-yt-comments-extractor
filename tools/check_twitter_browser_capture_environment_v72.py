from __future__ import annotations

import json
import shutil
import sys


def main() -> int:
    result = {
        "python_executable": sys.executable,
        "playwright_python_package": False,
        "playwright_import_error": "",
        "playwright_cli": bool(shutil.which("playwright")),
        "ready_for_live_capture": False,
        "next_commands": [
            f'"{sys.executable}" -m pip install playwright',
            f'"{sys.executable}" -m playwright install chromium',
        ],
    }
    try:
        import playwright.sync_api  # noqa: F401
        result["playwright_python_package"] = True
    except Exception as exc:
        result["playwright_import_error"] = str(exc)
    result["ready_for_live_capture"] = bool(result["playwright_python_package"])
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ready_for_live_capture"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
