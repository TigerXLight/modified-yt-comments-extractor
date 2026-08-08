from __future__ import annotations

import io
from contextlib import redirect_stdout

from source_adapter_smoke_receipt_review_integration_cli import main


def test_cli_text_and_json() -> None:
    text_buffer = io.StringIO()
    with redirect_stdout(text_buffer):
        assert main([]) == 0
    text = text_buffer.getvalue()
    assert "SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_BUILT" in text
    assert "smoke_receipt_review_decision_row_count=25" in text
    json_buffer = io.StringIO()
    with redirect_stdout(json_buffer):
        assert main(["--json"]) == 0
    assert "source_adapter_smoke_receipt_evidence_integration" in json_buffer.getvalue()


if __name__ == "__main__":
    test_cli_text_and_json()
    print("Source Adapter Smoke Receipt Review Integration CLI self-test passed.")
