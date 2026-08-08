from __future__ import annotations

import io
from contextlib import redirect_stdout

from source_adapter_named_site_smoke_execution_cli import main


def test_cli_text_and_json() -> None:
    text_buffer = io.StringIO()
    with redirect_stdout(text_buffer):
        assert main([]) == 0
    text = text_buffer.getvalue()
    assert "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_BUILT" in text
    assert "named_site_provider_action_receipt_row_count=25" in text
    json_buffer = io.StringIO()
    with redirect_stdout(json_buffer):
        assert main(["--json"]) == 0
    assert "source_adapter_named_site_provider_action_receipt_batch" in json_buffer.getvalue()


if __name__ == "__main__":
    test_cli_text_and_json()
    print("Source Adapter Named-Site Smoke Execution CLI self-test passed.")
