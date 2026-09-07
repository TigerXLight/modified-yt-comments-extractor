#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
import zipfile

from profile_media_bounded_debug_zip_r42ef import build_bounded_debug_zip


def test_compact_zip_skips_large_and_uses_bounded_dirs():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "main.py").write_text("# fake\n", encoding="utf-8")
        tools = root / "tools" / "webview2_source_role_editor_native"
        tools.mkdir(parents=True)
        (tools / "make_r42ee_bounded_payload_scan_hotfix_debug_upload_zip.py").write_text("# fake\n", encoding="utf-8")
        matrix = root / "profile_media_live_captures" / "r42ee_bounded_payload_scan_hotfix" / "matrix_20260907_000000_test"
        matrix.mkdir(parents=True)
        (matrix / "r42ed_semantic_media_logic_adapter_matrix.json").write_text('{"ok":true}\n', encoding="utf-8")
        (matrix / "huge.html").write_bytes(b"x" * 20000)
        summary = build_bounded_debug_zip(root=root, label="r42ef_test", max_file_bytes=1024, max_total_bytes=100000, print_json=False)
        assert summary.verdict["ready_for_upload"] is True
        assert summary.verdict["console_audit_rows_dump_suppressed"] is True
        assert summary.verdict["unbounded_profile_media_live_captures_scan"] is False
        with zipfile.ZipFile(summary.zip_path, "r") as zf:
            names = set(zf.namelist())
        assert any(name.endswith("r42ed_semantic_media_logic_adapter_matrix.json") for name in names)
        assert not any(name.endswith("huge.html") for name in names)


def main() -> int:
    test_compact_zip_skips_large_and_uses_bounded_dirs()
    print("R42EF bounded debug zip tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
