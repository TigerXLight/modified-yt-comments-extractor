from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING.md").read_text(encoding="utf-8")
    assert "Regression Queue Runtime Wiring" in doc
    assert "SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_BUILT" in doc
    assert "SOURCE_ADAPTER_LOCAL_REGRESSION_RUNNER_QUEUE_INSTALLED" in doc
    assert "SOURCE_ADAPTER_RUNTIME_CONTROLLER_PROVIDER_EXPANDED_BINDINGS_READY" in doc
    assert "SOURCE_ADAPTER_GUI_CONTROLLER_CALL_SITES_WIRED_FOR_LOCAL_DRY_RUN" in doc
    assert "SOURCE_ADAPTER_LOCAL_REGRESSION_ACCEPTANCE_RECEIPTS_READY" in doc
    assert "SOURCE_ADAPTER_NAMED_SITE_SMOKE_APPROVAL_GATE_CARRIED_FORWARD_UNEXECUTED" in doc
    assert "SOURCE_ADAPTER_REGRESSION_QUEUE_RUNTIME_WIRING_READY_FOR_CLOSEOUT_AUDIT" in doc
    assert "KEYS/ACCOUNTS" in doc
    assert "no live smoke" in doc
    assert "browser automation" in doc
    assert "network calls" in doc
    assert "API calls" in doc
    assert "archive provider submission" in doc
    assert "release upload" in doc
    assert "file-library mutation" in doc
    assert "credential storage" in doc
    assert "not GUI mutation" in doc
    print("Source Adapter Regression Queue Runtime Wiring docs self-test passed.")


if __name__ == "__main__":
    main()
