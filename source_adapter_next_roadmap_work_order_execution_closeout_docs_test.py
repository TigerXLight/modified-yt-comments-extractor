from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_NEXT_ROADMAP_WORK_ORDER_EXECUTION_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "GUI/controller hardening",
        "provider execution activation",
        "priority fixture pack authoring",
        "operator-approved live smoke receipt capture",
        "regular regression promotion",
        "documentation/handoff refresh",
        "source_adapter_next_roadmap_execution_ready_handoff",
    ]
    for phrase in required:
        assert phrase in text, phrase
    print("Source Adapter Next Roadmap Work Order Execution Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
