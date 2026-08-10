from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_regression_index import CATEGORIES, build_regression_index, write_regression_index


def test_regression_index_counts_present_modules() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        expected = 0
        for paths in CATEGORIES.values():
            for rel in paths:
                expected += 1
                (root / rel).write_text("placeholder\n", encoding="utf-8")
                (root / rel.replace(".py", "_test.py")).write_text("placeholder\n", encoding="utf-8")
        index = build_regression_index(root)
        assert index.status == "PASS"
        assert index.present_count == expected
        assert all(entry.companion_test_present for entry in index.entries)
        json_path, md_path = write_regression_index(index, root / "reports")
        assert json_path.exists()
        assert md_path.exists()


def main() -> int:
    test_regression_index_counts_present_modules()
    print("MSN regression index self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
