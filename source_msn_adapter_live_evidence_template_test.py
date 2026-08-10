from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_msn_adapter_live_evidence_template import build_template, write_template


def test_template_contains_required_checks() -> None:
    template = build_template(target_url="https://www.msn.com/example")
    ids = {check.check_id for check in template.checks}
    assert "article_extracted" in ids
    assert "comments_exported" in ids
    assert "source_chain_separated" in ids
    assert "no_false_complete_claim" in ids
    assert all(check.status == "UNSET" for check in template.checks)


def test_write_template_round_trip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = write_template(Path(tmp), target_url="https://www.msn.com/example", operator="operator")
        json_path = Path(result["json"])
        md_path = Path(result["markdown"])
        assert json_path.exists()
        assert md_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["target_url"] == "https://www.msn.com/example"
        assert data["operator_signed"] is False
        assert len(data["checks"]) >= 10


if __name__ == "__main__":
    test_template_contains_required_checks()
    test_write_template_round_trip()
    print("MSN live evidence template self-test passed.")
