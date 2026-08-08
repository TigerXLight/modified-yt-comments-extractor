from __future__ import annotations

import io
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory

from source_adapter_release_publish_receipt_runtime_cli import main


def test_release_publish_receipt_runtime_cli() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert main(["--operator-id", "cli_operator", "--json"]) == 0
    assert "verified" in buf.getvalue()
    with TemporaryDirectory() as tmp:
        buf = io.StringIO()
        with redirect_stdout(buf):
            assert main(["--operator-id", "cli_operator", "--output-dir", tmp, "--json"]) == 0
        assert "STORED" in buf.getvalue()


if __name__ == "__main__":
    test_release_publish_receipt_runtime_cli()
    print("Source Adapter Release Publish Receipt Runtime CLI self-test passed.")
