from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_ROADMAP_AUDIT_FINAL_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Roadmap Audit Final Closeout",
        "Operator Named Site Smoke Execution Closeout",
        "KEYS/ACCOUNTS",
        "regression promotion",
        "operator-monitored live execution",
        "source_adapter_roadmap_audit_final_closeout_v1",
    ]
    for phrase in required:
        assert phrase in text, phrase
    print("Source Adapter Roadmap Audit Final Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
