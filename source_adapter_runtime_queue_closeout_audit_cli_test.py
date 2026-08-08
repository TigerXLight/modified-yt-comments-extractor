from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_runtime_queue_closeout_audit_cli import main


def main_test() -> None:
    with TemporaryDirectory() as tmp:
        assert main(["--output-dir", tmp, "--operator-id", "cli_tester"]) == 0
    assert main(["--closeout-note", "cli local closeout audit"]) == 0
    print("Source Adapter Runtime Queue Closeout Audit CLI self-test passed.")


if __name__ == "__main__":
    main_test()
