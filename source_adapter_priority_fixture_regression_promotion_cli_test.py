from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_priority_fixture_regression_promotion_cli import main


def main_test() -> None:
    with TemporaryDirectory() as tmp:
        assert main(["--output-dir", tmp, "--operator-id", "cli_tester"]) == 0
    assert main(["--promotion-note", "cli regular regression promotion"]) == 0
    print("Source Adapter Priority Fixture Regression Promotion CLI self-test passed.")


if __name__ == "__main__":
    main_test()
