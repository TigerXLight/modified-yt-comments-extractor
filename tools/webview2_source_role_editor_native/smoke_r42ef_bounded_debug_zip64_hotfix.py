#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    replacement = root / "tools" / "webview2_source_role_editor_native" / "make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py"
    helper = root / "profile_media_bounded_debug_zip_r42ef.py"
    repl_text = replacement.read_text(encoding="utf-8") if replacement.exists() else ""
    helper_text = helper.read_text(encoding="utf-8") if helper.exists() else ""
    checks = {
        "replacement_uses_helper": "build_bounded_debug_zip" in repl_text,
        "allow_zip64": "allowZip64=True" in helper_text,
        "console_dump_suppressed_marker": "console_audit_rows_dump_suppressed" in helper_text,
        "safe_iter_files_present": "def safe_iter_files" in helper_text,
        "old_verbose_probe_not_imported": "probe_r42ee_bounded_payload_scan_hotfix_no_gui" not in repl_text,
        "zip_size_caps_present": "DEFAULT_MAX_FILE_BYTES" in helper_text and "DEFAULT_MAX_TOTAL_BYTES" in helper_text,
    }
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
