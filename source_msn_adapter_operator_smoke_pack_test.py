from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_operator_smoke_pack import create_operator_smoke_pack


def test_operator_smoke_pack_creates_expected_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "smoke"
        pack = create_operator_smoke_pack("https://www.msn.com/en-gb/news/example/ar-AAexample", out)
        expected = {
            "MSN_OPERATOR_SMOKE_STEPS.md",
            "MSN_MANUAL_VALIDATION_RESULT_TEMPLATE.json",
            "RUN_DONE_GATE_AFTER_MANUAL_REVIEW.cmd",
            "MSN_OPERATOR_SMOKE_PACK_INDEX.json",
        }
        assert expected.issubset({Path(path).name for path in pack.generated_files})
        md = (out / "MSN_OPERATOR_SMOKE_STEPS.md").read_text(encoding="utf-8")
        assert "The Independent" in md
        assert "Google Street View" in md
        template = json.loads((out / "MSN_MANUAL_VALIDATION_RESULT_TEMPLATE.json").read_text(encoding="utf-8"))
        assert template["source_role_notes"]["primary_source_status"] == "PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED"
        assert any(step["id"] == "comments" for step in template["steps"])


if __name__ == "__main__":
    test_operator_smoke_pack_creates_expected_files()
    print("MSN operator smoke-pack self-test passed.")
