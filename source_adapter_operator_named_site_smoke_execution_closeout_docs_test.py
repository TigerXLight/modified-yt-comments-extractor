from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_OPERATOR_NAMED_SITE_SMOKE_EXECUTION_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Operator Named Site Smoke Execution Closeout",
        "named-site execution closeout",
        "local fixture execution rows",
        "operator-approved manual smoke execution rows",
        "KEYS/ACCOUNTS credential reference surface",
        "final source-adapter roadmap handoff",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing
    print("Source Adapter Operator Named Site Smoke Execution Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
