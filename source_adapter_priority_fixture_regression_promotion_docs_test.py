from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION.md").read_text(encoding="utf-8")
    assert "Priority Fixture Regression Promotion" in doc
    assert "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_BUILT" in doc
    assert "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_QUEUE_READY" in doc
    assert "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITE_INSTALLATION_PLAN_READY" in doc
    assert "SOURCE_ADAPTER_NAMED_SITE_SMOKE_REMAINS_OPERATOR_APPROVAL_REQUIRED" in doc
    assert "SOURCE_ADAPTER_PRIORITY_FIXTURE_REGRESSION_PROMOTION_READY_FOR_REGRESSION_QUEUE_INSTALLATION" in doc
    assert "KEYS/ACCOUNTS" in doc
    assert "no live smoke" in doc
    assert "network calls" in doc
    assert "API calls" in doc
    assert "archive provider submission" in doc
    assert "release upload" in doc
    assert "file-library mutation" in doc
    assert "credential storage" in doc
    print("Source Adapter Priority Fixture Regression Promotion docs self-test passed.")


if __name__ == "__main__":
    main()
