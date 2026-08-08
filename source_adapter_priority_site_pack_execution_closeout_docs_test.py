from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_PRIORITY_SITE_PACK_EXECUTION_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Priority Site Pack Execution Closeout",
        "named priority site fixture packs",
        "operator-approved manual smoke rows",
        "KEYS/ACCOUNTS",
        "credential references",
        "article/news pages",
        "social post or thread evidence",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    assert not missing, missing
    print("Source Adapter Priority Site Pack Execution Closeout docs self-test passed.")


if __name__ == "__main__":
    main()
